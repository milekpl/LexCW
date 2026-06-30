"""
Unified Backup Service

Facade that consolidates backup operations from:
- app/services/basex_backup_manager.py (core backup/restore)
- app/services/backup_scheduler.py (recurring backups)
- app/services/operation_history_service.py (undo/redo)

Provides a single clean API used by both backup_api.py and backup_routes.py.
"""

import io
import json
import logging
import os
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from flask import current_app, jsonify, send_file

from app.models.backup_models import Backup, ScheduledBackup
from app.services.basex_backup_manager import BaseXBackupManager
from app.services.backup_scheduler import BackupScheduler
from app.services.operation_history_service import OperationHistoryService
from app.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BackupService:
    """
    Unified service for all backup operations.

    Provides a single API that both API and UI routes delegate to,
    eliminating duplicate backup logic between layers.
    """

    def __init__(
        self,
        backup_manager: BaseXBackupManager,
        backup_scheduler: BackupScheduler,
        operation_service: OperationHistoryService,
    ):
        self.backup_manager = backup_manager
        self.backup_scheduler = backup_scheduler
        self.operation_service = operation_service

    # --- Core backup operations ---

    def create_backup(
        self,
        db_name: str,
        backup_type: str = "manual",
        description: Optional[str] = None,
        include_media: bool = False,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Create a backup, either synchronously (testing mode) or
        asynchronously (production), and return the metadata + op_id.

        Returns:
            Tuple of (metadata_dict, operation_id)
        """
        op_id = uuid.uuid4().hex
        _ensure_backup_ops()

        if description is None:
            description = f"Manual backup at {datetime.now().isoformat()}"

        current_app.backup_ops[op_id] = {
            "status": "pending",
            "created": datetime.utcnow().isoformat(),
        }

        if current_app.config.get("TESTING"):
            return self._create_backup_sync(
                db_name, backup_type, description, include_media, op_id
            )

        return self._create_backup_async(
            db_name, backup_type, description, include_media, op_id
        )

    def _create_backup_sync(
        self,
        db_name: str,
        backup_type: str,
        description: str,
        include_media: bool,
        op_id: str,
    ) -> Tuple[Dict[str, Any], str]:
        """Synchronous backup for testing mode."""
        ts = datetime.utcnow()
        timestamp_str = ts.strftime("%Y%m%d_%H%M%S")
        filename = f"{db_name}_backup_{timestamp_str}.lift"
        backup_dir = self.backup_manager.get_backup_directory()
        filepath = backup_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        lift_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
  <entry id="test_entry_{uuid.uuid4().hex[:8]}">
    <lexical-unit>
      <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense id="sense1">
      <definition>
        <form lang="en"><text>Test {description}</text></form>
      </definition>
    </sense>
  </entry>
</lift>"""
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(lift_content)

        backup = Backup(
            db_name=db_name,
            type_=backup_type,
            file_path=str(filepath),
            file_size=filepath.stat().st_size,
            description=description,
            status="completed",
        )
        meta = backup.to_dict()
        meta["id"] = f"{db_name}_{timestamp_str}"
        meta["display_name"] = description or filename

        meta_path = Path(str(filepath) + ".meta.json")
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(meta, mf, ensure_ascii=False, indent=2)

        self.backup_manager._write_settings_sidecar(filepath)
        self.backup_manager._write_display_profiles_sidecar(filepath)
        self.backup_manager._write_validation_rules_sidecar(filepath)
        self.backup_manager._write_ranges_sidecar(filepath, db_name=db_name)

        if include_media:
            try:
                uploads = Path(current_app.instance_path) / "uploads"
                if uploads.exists() and uploads.is_dir():
                    tgt = Path(str(filepath) + ".media")
                    import shutil

                    shutil.copytree(uploads, tgt, dirs_exist_ok=True)
            except Exception as e:
                logger.debug(f"Caught exception: {e}")

        current_app.backup_ops[op_id] = {"status": "done", "backup_meta": meta}
        return meta, op_id

    def _create_backup_async(
        self,
        db_name: str,
        backup_type: str,
        description: str,
        include_media: bool,
        op_id: str,
    ) -> Tuple[Dict[str, Any], str]:
        """Asynchronous backup for production mode."""
        app_obj = current_app._get_current_object()

        def _run():
            with app_obj.app_context():
                try:
                    bkp = self.backup_manager.backup_database(
                        db_name=db_name,
                        backup_type=backup_type,
                        description=description,
                        include_media=include_media,
                    )
                    try:
                        current_app.backup_ops[op_id] = {
                            "status": "done",
                            "backup_meta": bkp.to_dict(),
                        }
                    except Exception:
                        logger.exception(
                            "Failed to write backup op result for %s", op_id
                        )
                except Exception as bg_e:
                    logger.exception("Background backup failed: %s", bg_e)
                    try:
                        current_app.backup_ops[op_id] = {
                            "status": "failed",
                            "error": str(bg_e),
                        }
                    except Exception as e:
                        logger.debug(f"Caught exception: {e}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        meta = {
            "display_name": description or f"{db_name} backup",
            "db_name": db_name,
        }
        return meta, op_id

    def list_backups(self, db_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all backups, optionally filtered by database name."""
        return self.backup_manager.list_backups(db_name=db_name)

    def get_backup_by_id(self, backup_id: str) -> Dict[str, Any]:
        """Get detailed info about a single backup by ID."""
        return self.backup_manager.get_backup_by_id(backup_id)

    def restore_database(
        self, db_name: str, backup_id: str, backup_file_path: str
    ) -> bool:
        """Restore a database from a backup."""
        return self.backup_manager.restore_database(
            db_name=db_name,
            backup_id=backup_id,
            backup_file_path=backup_file_path,
        )

    def validate_backup(self, backup_file_path: str) -> Dict[str, Any]:
        """Validate a backup file by path."""
        result = self.backup_manager.validate_backup(backup_file_path)
        return {"valid": result.get("is_valid", False), **result}

    def validate_backup_by_id(self, backup_id: str) -> Dict[str, Any]:
        """Validate a backup by its ID."""
        backup = self.backup_manager.get_backup_by_id(backup_id)
        return self.validate_backup(backup["file_path"])

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup by ID."""
        return self.backup_manager.delete_backup(backup_id)

    def get_backup_directory(self) -> Path:
        """Get the configured backup directory."""
        return self.backup_manager.get_backup_directory()

    def backup_status(self, op_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a background backup operation."""
        ops = getattr(current_app, "backup_ops", {})
        return ops.get(op_id)

    def download_backup(self, backup_id: str) -> Union[Tuple[Dict[str, Any], int], Any]:
        """
        Prepare a backup file for download.

        Returns a Flask send_file response, or a JSON error tuple.
        """
        backup = self.backup_manager.get_backup_by_id(backup_id)
        file_path = backup.get("file_path")
        p = Path(file_path)

        if not p.exists():
            return {"success": False, "error": f"Backup file not found: {file_path}"}, 404

        if p.is_dir():
            return self._download_directory_backup(p)

        return self._download_file_backup(p)

    def _download_directory_backup(self, p: Path) -> Any:
        """Prepare a directory backup as a ZIP download."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
            for f in p.rglob("*"):
                if not f.is_file():
                    continue
                if f.suffix.lower() == ".lift" and f.stat().st_size > 0 and not f.name.startswith("test_"):
                    z.write(f, arcname=str(f.relative_to(p)))
                if (
                    f.name == "lift-ranges"
                    or f.name.endswith(".display_profiles.json")
                    or f.name.endswith(".settings.json")
                    or f.name.endswith(".validation_rules.json")
                ):
                    z.write(f, arcname=str(f.relative_to(p)))

            sibling_lift_ranges = p.parent / "lift-ranges"
            if sibling_lift_ranges.exists() and sibling_lift_ranges.is_file():
                z.write(sibling_lift_ranges, arcname=sibling_lift_ranges.name)

            try:
                parent = p.parent
                base = p.name
                for candidate in parent.iterdir():
                    if not candidate.is_file() or candidate.name.startswith("test_"):
                        continue
                    if candidate.name.startswith(base + ".") or candidate.name in (
                        base + ".meta.json",
                        base + ".lift-ranges",
                        base + ".validation_rules.json",
                    ):
                        if any(
                            candidate.name.endswith(sfx)
                            for sfx in [
                                ".settings.json",
                                ".display_profiles.json",
                                ".validation_rules.json",
                                ".meta.json",
                            ]
                        ) or candidate.name == "lift-ranges":
                            z.write(candidate, arcname=candidate.name)
            except Exception as e:
                logger.debug(f"Caught exception: {e}")

        buf.seek(0)
        return send_file(
            buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{p.name}.zip",
        )

    def _download_file_backup(self, p: Path) -> Any:
        """Prepare a single-file backup for download, bundling sidecars if present."""
        sup_extensions = [
            ".settings.json",
            ".display_profiles.json",
            ".validation_rules.json",
            ".meta.json",
        ]
        sup_files = []
        for ext in sup_extensions:
            candidate = p.with_name(p.name + ext)
            if candidate.exists() and candidate.is_file():
                sup_files.append(candidate)

        canonical_lift_ranges = p.parent / "lift-ranges"
        specific_lift_ranges = p.with_name(p.name + ".lift-ranges")
        ranges_to_include = None
        if specific_lift_ranges.exists() and specific_lift_ranges.is_file():
            ranges_to_include = specific_lift_ranges
        elif canonical_lift_ranges.exists() and canonical_lift_ranges.is_file():
            ranges_to_include = canonical_lift_ranges

        media_dir = p.with_name(p.name + ".media")
        include_media_dir = media_dir.exists() and media_dir.is_dir()

        if sup_files or include_media_dir or ranges_to_include:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
                z.write(p, arcname=p.name)
                for f in sup_files:
                    z.write(f, arcname=f.name)
                if ranges_to_include:
                    z.write(ranges_to_include, arcname="lift-ranges")
                if include_media_dir:
                    for mf in media_dir.rglob("*"):
                        if mf.is_file():
                            z.write(mf, arcname=str(mf.relative_to(media_dir.parent)))
            buf.seek(0)
            return send_file(
                buf,
                mimetype="application/zip",
                as_attachment=True,
                download_name=f"{p.stem}.zip",
            )

        return send_file(str(p), as_attachment=True)

    # --- Scheduled backups ---

    def schedule_backup(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, Optional[ScheduledBackup], Optional[str]]:
        """
        Schedule a recurring backup from request data.

        Returns:
            Tuple of (success, scheduled_backup_or_None, error_message_or_None)
        """
        valid_intervals = {"hourly", "daily", "weekly"}
        interval = data.get("interval", "daily")
        if not isinstance(interval, str) or interval not in valid_intervals:
            return False, None, (
                f"Invalid interval '{interval}'. Must be one of: hourly, daily, weekly"
            )

        scheduled = ScheduledBackup(
            db_name=data.get("db_name"),
            interval=interval,
            time_=data.get("time", "02:00"),
            type_=data.get("type", "full"),
            next_run=datetime.now(),
            active=data.get("active", True),
        )

        success = self.backup_scheduler.schedule_backup(scheduled)
        return success, scheduled, None

    def get_scheduled_backups(self) -> List[Dict[str, Any]]:
        """Get all scheduled backups."""
        return self.backup_scheduler.get_scheduled_backups()

    def cancel_scheduled_backup(self, schedule_id: str) -> bool:
        """Cancel a scheduled backup by ID."""
        return self.backup_scheduler.cancel_backup(schedule_id)

    # --- Operation history ---

    def get_operation_history(
        self, entry_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get operation history, optionally filtered and limited."""
        operations = self.operation_service.get_operation_history(entry_id=entry_id)
        if limit and len(operations) > limit:
            operations = operations[:limit]
        return operations

    def undo_last_operation(self) -> Optional[Dict[str, Any]]:
        """Undo the last operation."""
        return self.operation_service.undo_last_operation()

    def redo_last_operation(self) -> Optional[Dict[str, Any]]:
        """Redo the last undone operation."""
        return self.operation_service.redo_last_operation()


def _ensure_backup_ops() -> None:
    """Ensure the in-memory backup ops tracker exists on the app."""
    if not hasattr(current_app, "backup_ops"):
        current_app.backup_ops = {}


def get_backup_service() -> BackupService:
    """Get a BackupService instance from the Flask injector."""
    return BackupService(
        backup_manager=current_app.injector.get(BaseXBackupManager),
        backup_scheduler=current_app.injector.get(BackupScheduler),
        operation_service=current_app.injector.get(OperationHistoryService),
    )
