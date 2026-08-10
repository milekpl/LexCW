"""
Service for managing BaseX database backups and restores.
"""

import os
import json
import logging
import re
import shutil
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.database.basex_connector import BaseXConnector
from app.models.backup_models import Backup, OperationHistory
from app.utils.exceptions import DatabaseError, ValidationError


class BaseXBackupManager:
    """
    Service for managing BaseX database backups and restores.
    
    This service handles creating full database backups, validating backup integrity,
    and restoring databases from backups. It uses BaseX's built-in EXPORT command
    to create LIFT XML backups of the database.
    """

    def __init__(self, basex_connector: BaseXConnector, config_manager=None, backup_directory: str = "instance/backups"):
        """
        Initialize the BaseX backup manager.

        Args:
            basex_connector: BaseXConnector instance for database operations
            config_manager: Optional config manager instance
            backup_directory: Directory to store backup files
        """
        self.basex_connector = basex_connector
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Validate and set backup directory
        validated_backup_dir = self._validate_backup_directory(backup_directory)
        self.backup_directory = Path(validated_backup_dir)
        
        # Ensure backup directory exists
        self.backup_directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_db_name(db_name: str) -> None:
        """Reject database names that could break out of BaseX command syntax.

        ``db_name`` is interpolated into OPEN/collection/DROP/ALTER commands;
        BaseX itself only allows a restricted character set, so anything else
        is either invalid or an injection attempt.
        """
        if not db_name or not re.fullmatch(r'[A-Za-z0-9_\-]+', str(db_name)):
            raise ValidationError(f"Invalid database name: {db_name!r}")

    def recover_orphaned_restore_databases(self) -> List[str]:
        """Recover databases stranded by a crash during restore.

        ``restore_database`` swaps databases with ``DROP DB <name>`` followed by
        ``ALTER DB <tmp> <name>``. A hard crash between those two commands leaves
        the recovered data under a ``<name>_restore_<ts>_<rand>`` temporary
        database with no live database. This sweep renames such orphans back to
        their base name — but only when the live database is absent (never
        clobbering newer data).

        Returns:
            List of database names that were recovered.
        """
        recovered: List[str] = []
        try:
            raw = self.basex_connector.execute_query("xquery db:list()")
            dbs = [d.strip() for d in (raw or "").split() if d.strip()]
        except Exception as e:
            self.logger.error(f"Failed to list databases for orphan recovery: {e}")
            return recovered

        pattern = re.compile(r'^(.+)_restore_\d{8}_\d{6}_[0-9a-f]{6}$')
        for db in dbs:
            match = pattern.match(db)
            if not match:
                continue
            base_name = match.group(1)
            try:
                self._validate_db_name(base_name)
            except ValidationError:
                self.logger.warning(
                    f"Skipping orphan '{db}': derived base name {base_name!r} "
                    f"is not a valid database name"
                )
                continue
            if base_name in dbs:
                # Live DB exists — the orphan is a leftover from a failed
                # restore attempt; leave both for manual inspection.
                self.logger.warning(
                    f"Orphaned restore temp DB '{db}' found, but live DB "
                    f"'{base_name}' exists — leaving both untouched"
                )
                continue
            try:
                self.basex_connector.execute_command(f"ALTER DB {db} {base_name}")
                self.logger.info(
                    f"Recovered orphaned restore temp DB '{db}' -> '{base_name}'"
                )
                recovered.append(base_name)
            except Exception as e:
                self.logger.error(
                    f"Failed to recover orphaned restore temp DB '{db}': {e}"
                )
        return recovered

    def _validate_backup_directory(self, backup_dir: str) -> str:
        """
        Validate the backup directory to prevent directory traversal attacks.

        Uses :meth:`pathlib.Path.resolve` to collapse ``..`` segments and
        symlinks before comparing against a trusted base, rather than a
        fragile ``".." in backup_dir`` string check that can be bypassed
        with URL-encoded or symlink-based traversal.

        Args:
            backup_dir: The backup directory path to validate.

        Returns:
            Validated backup directory path.

        Raises:
            ValidationError: If validation fails.
        """
        if not backup_dir:
            return "instance/backups"

        path = Path(backup_dir)

        # Resolve the path to collapse '..', symlinks, etc.
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError):
            resolved = path

        # For relative paths: check they don't escape the CWD via '..'
        if not path.is_absolute():
            try:
                # This raises ValueError if resolved is not under cwd
                resolved.relative_to(Path.cwd().resolve())
            except ValueError:
                self.logger.warning(
                    f"Backup path rejected — resolves outside working directory: "
                    f"{backup_dir} -> {resolved}. Using default instance/backups instead."
                )
                return "instance/backups"
            return backup_dir

        # ---- Absolute path handling -----------------------------------
        # Absolute paths are an explicit, legitimate configuration — e.g. a
        # dedicated backup disk/mount, which keeps backups off the same disk
        # as the database (true disaster recovery). The working-directory
        # confinement above still protects against relative-path '..' escapes.
        try:
            path.mkdir(parents=True, exist_ok=True)
            return backup_dir
        except Exception:
            self.logger.warning(
                f"Absolute backup path not usable: {backup_dir} -> {resolved}. "
                f"Using default instance/backups instead."
            )
            return "instance/backups"

    def get_backup_directory(self) -> Path:
        """
        Get the configured backup directory.

        Returns:
            Path to the backup directory.
        """
        return self.backup_directory

    def get_backup_by_id(self, backup_id: str) -> Dict[str, Any]:
        """
        Get information about a backup by its ID.

        Args:
            backup_id: ID of the backup (e.g., test_db_20250101_120000)

        Returns:
            Dictionary with backup details.
        """
        # First, try to find a .meta.json file that matches this ID
        for meta_file in self.backup_directory.glob("*.meta.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    if meta.get('id') == backup_id:
                        # Ensure file_path is set correctly
                        if 'file_path' not in meta or not meta['file_path']:
                            # Try to infer file_path from meta file name
                            if meta_file.name.endswith('.lift.meta.json'):
                                lift_filename = meta_file.name.replace('.lift.meta.json', '.lift')
                            elif meta_file.name.endswith('.meta.json'):
                                lift_filename = meta_file.name.replace('.meta.json', '')
                                # Check if it's a directory backup
                                dir_path = self.backup_directory / lift_filename
                                if dir_path.exists() and dir_path.is_dir():
                                    meta['file_path'] = str(dir_path)
                                    return meta
                                else:
                                    lift_filename += '.lift'
                            
                            lift_path = self.backup_directory / lift_filename
                            if lift_path.exists():
                                meta['file_path'] = str(lift_path)
                        return meta
            except Exception:
                continue

        # If no meta file found, try to infer from filename format: {db_name}_backup_{timestamp}.lift
        # backup_id might look like {db_name}_{timestamp}
        parts = backup_id.split('_')
        if len(parts) >= 3:
            timestamp_part = '_'.join(parts[-2:])
            db_name = '_'.join(parts[:-2])
            filename = f"{db_name}_backup_{timestamp_part}.lift"
            filepath = self.backup_directory / filename
            
            if filepath.exists():
                # Reconstruct information from filename
                try:
                    timestamp = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
                    timestamp_str = timestamp.isoformat()
                except ValueError:
                    timestamp_str = datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
                
                return {
                    'id': backup_id,
                    'db_name': db_name,
                    'file_path': str(filepath),
                    'file_size': filepath.stat().st_size,
                    'timestamp': timestamp_str,
                    'status': 'completed',
                    'type': 'manual'
                }
            
            # Also check for directory-based backups
            dir_path = self.backup_directory / filename
            if dir_path.exists() and dir_path.is_dir():
                # Reconstruct information from directory name
                try:
                    timestamp = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
                    timestamp_str = timestamp.isoformat()
                except ValueError:
                    timestamp_str = datetime.fromtimestamp(dir_path.stat().st_mtime).isoformat()
                
                return {
                    'id': backup_id,
                    'db_name': db_name,
                    'file_path': str(dir_path),
                    'file_size': sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file()),
                    'timestamp': timestamp_str,
                    'status': 'completed',
                    'type': 'manual'
                }

        raise ValidationError(f"Backup with ID {backup_id} not found")

    def backup_database(self, db_name: str, backup_type: str = 'full', description: Optional[str] = None, include_media: bool = False) -> Backup:
        """
        Create a backup of the specified BaseX database.

        Args:
            db_name: Name of the database to backup
            backup_type: Type of backup ('full', 'incremental', 'manual')
            description: Optional description of the backup

        Returns:
            Backup model instance with backup details
        """
        if backup_type not in ['full', 'incremental', 'manual']:
            raise ValidationError(f"Invalid backup type: {backup_type}")
        self._validate_db_name(db_name)

        timestamp = datetime.utcnow()
        filename = f"{db_name}_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.lift"
        filepath = self.backup_directory / filename
        # Track whether a backup file was actually created/found in any of the codepaths
        file_found = False

        try:
            self.logger.info(f"Creating backup using query approach for database: {db_name}")

            # Use the same approach as the dictionary service export_lift method to get full content
            # Query the entire database content properly
            try:
                # Ensure we're working with the right database
                self.basex_connector.execute_command(f"OPEN {db_name}")

                # Serialize the ENTIRE database as ONE well-formed XML document so the
                # backup file can be re-imported (CREATE DB / restore). Each resource
                # document becomes a child of a single <lift> root; the app queries
                # entries and ranges with //-based selectors, so functional layout is
                # preserved. Previously the query concatenated every resource root as
                # sibling elements, producing a MULTI-ROOT file ("junk after document
                # element") that BaseX could not parse back — restore would DROP the
                # live database and then fail to recreate it (data loss).
                query = (
                    f"<lift version=\"0.13\">"
                    f"{{ for $doc in collection('{db_name}') return $doc/node() }}"
                    f"</lift>"
                )
                db_content = self.basex_connector.execute_query(query)

                # If the result is empty, try alternative approach
                if not db_content or (isinstance(db_content, str) and db_content.strip() == ''):
                    # Try to get all documents in the collection more explicitly
                    alt_query = f"collection('{db_name}')"
                    try:
                        db_content = self.basex_connector.execute_query(alt_query)
                    except Exception:
                        db_content = None

                # If db_content is present but not a string, coerce to string so it can be written
                if db_content is not None and not isinstance(db_content, str):
                    try:
                        db_content = str(db_content)
                    except Exception:
                        db_content = None
            except Exception as e:
                self.logger.warning(f"Query approach failed, falling back to export: {e}")
                # BaseX's EXPORT writes each resource as a file into a
                # DIRECTORY and resolves paths RELATIVE TO ITS OWN CWD
                # (absolute paths are silently ignored). Export to a bare
                # directory name, locate it in the server's CWD (the same
                # filesystem in a single-machine deployment), and reassemble
                # the resources into ONE well-formed <lift> document.
                export_name = filepath.name + ".export_tmp"
                try:
                    # NB: BaseX EXPORT does NOT accept quoted paths (quotes are
                    # treated literally and the export silently no-ops).
                    # export_name is derived from the validated db name, so it
                    # only contains safe characters (alnum, _ - .).
                    self.basex_connector.execute_command(f"EXPORT {export_name}")
                except Exception as export_err:
                    self.logger.debug(f"EXPORT command failed: {export_err}")

                export_dir = Path.cwd() / export_name
                if not export_dir.is_dir():
                    raise DatabaseError(
                        f"Backup via EXPORT failed (no export dir written by "
                        f"the server); query serialization failed earlier: {e}"
                    )
                try:
                    pieces = []
                    for res in sorted(export_dir.iterdir()):
                        if res.is_file():
                            pieces.append(res.read_text(encoding="utf-8"))
                    if not pieces:
                        raise DatabaseError("EXPORT produced no files")

                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(
                        '<lift version="0.13">' + "".join(pieces) + "</lift>",
                        encoding="utf-8",
                    )
                    file_found = True
                    self.logger.info(
                        f"Backup created via export (reassembled): {filepath}"
                    )
                finally:
                    shutil.rmtree(export_dir, ignore_errors=True)

                if not file_found:
                    raise DatabaseError(f"Backup file was not created at {filepath}")
            else:
                # Content was retrieved successfully via query
                # Write the content to our backup file
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(db_content)

                self.logger.info(f"Backup created successfully using query approach: {filepath}")
                file_found = True
                
            # Get file size
            file_size = filepath.stat().st_size
            
            # Write sidecar files with real data
            self._write_ranges_sidecar(filepath, db_name=db_name)
            self._write_display_profiles_sidecar(filepath)
            self._write_validation_rules_sidecar(filepath)
            self._write_settings_sidecar(filepath)

            # Copy media if requested
            if include_media:
                try:
                    from flask import current_app
                    uploads_dir = Path(current_app.instance_path) / 'uploads'
                    if uploads_dir.exists() and uploads_dir.is_dir():
                        media_target = Path(str(filepath) + '.media')
                        media_target.mkdir(parents=True, exist_ok=True)
                        for src in uploads_dir.iterdir():
                            if src.is_file():
                                shutil.copy2(src, media_target / src.name)
                        self.logger.info(f"Copied media files to {media_target}")
                except Exception as e:
                    self.logger.warning(f"Failed to copy media files: {e}")

            # Create backup record
            backup = Backup(
                db_name=db_name,
                type_=backup_type,
                file_path=str(filepath),
                file_size=file_size,
                description=description,
                status='completed'
            )
            
            # Write metadata file for easier discovery
            try:
                meta_path = filepath.with_name(filepath.name + '.meta.json')
                meta_data = backup.to_dict()
                # Ensure id is present in meta
                if 'id' not in meta_data:
                    meta_data['id'] = f"{db_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta_data, f, ensure_ascii=False, indent=2)
            except Exception as meta_e:
                self.logger.warning(f"Failed to write metadata for backup {filepath}: {meta_e}")

            self.logger.info(f"Database '{db_name}' backed up successfully to {filepath}")
            return backup
            
        except Exception as e:
            error_msg = f"Failed to backup database '{db_name}': {str(e)}"
            self.logger.error(error_msg)
            
            # Create backup record with failed status
            backup = Backup(
                db_name=db_name,
                type_=backup_type,
                file_path=str(filepath),
                file_size=0,
                description=description,
                status='failed'
            )
            
            raise DatabaseError(error_msg) from e

    def restore_database(self, db_name: str, backup_id: str, backup_file_path: str) -> bool:
        """
        Restore a database from a backup file, including supplementary artifacts.

        Args:
            db_name: Name of the database to restore
            backup_id: ID of the backup record
            backup_file_path: Path to the backup file to restore from

        Returns:
            True if restore was successful, False otherwise
        """
        backup_path = Path(backup_file_path)
        if not backup_path.exists():
            raise ValidationError(f"Backup file does not exist: {backup_path}")
        self._validate_db_name(db_name)

        # Check for invalid validation rules before doing anything
        vr_path = backup_path.with_name(backup_path.name + '.validation_rules.json')
        if vr_path.exists():
            try:
                content = vr_path.read_text(encoding='utf-8')
                json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid validation rules in backup: {e}")
                raise ValidationError(f"Invalid validation rules in backup: {e}")

        try:
            # ---- Atomic restore: import into a temp DB, validate, then swap ----
            # The live database is only dropped AFTER the backup file has been
            # successfully imported and verified, so a bad/corrupt/old backup file
            # can never destroy the current data.
            if backup_path.is_dir():
                # Directory-style backup (legacy EXPORT fallback): use the newest
                # non-test .lift file inside it as the content source.
                lift_files = [
                    f for f in backup_path.rglob('*.lift')
                    if f.is_file() and not f.name.startswith('test_')
                ]
                if not lift_files:
                    raise ValidationError(
                        f"Backup directory contains no .lift file: {backup_path}"
                    )
                content_path = max(lift_files, key=lambda p: p.stat().st_mtime)
            else:
                content_path = backup_path

            backup_content = content_path.read_text(encoding='utf-8')

            # 1. The backup must be a single well-formed XML document. Backups
            #    written before the multi-root fix are rejected here — safely,
            #    before anything is dropped.
            try:
                ET.fromstring(backup_content)
            except ET.ParseError as pe:
                raise ValidationError(
                    f"Backup file is not a well-formed XML document and cannot be "
                    f"restored (it may be an old multi-root backup): {pe}"
                ) from pe

            temp_db = (
                f"{db_name}_restore_"
                f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            )

            # 2. Import into a temporary database (in-process add_resource, so the
            #    file is read by the app, not by BaseX's own filesystem).
            self.basex_connector.create_database(temp_db)
            self.basex_connector.add_resource('lift.xml', backup_content, db_name=temp_db)

            # 3. Verify the temp DB is queryable before touching the live DB.
            probe = self.basex_connector.execute_query(
                f"xquery count(collection('{temp_db}')//entry)"
            )
            if probe is None or str(probe).strip() == '':
                raise DatabaseError(
                    f"Restored database is empty or unqueryable: {temp_db}"
                )

            # 4. Swap: drop the live DB, then rename the validated temp DB into place.
            preserve_temp = False
            try:
                self.basex_connector.execute_command(f"DROP DB {db_name}")
            except Exception as e:
                # Database might not exist, which is fine
                self.logger.debug(f"DROP DB failed (expected if DB doesn't exist): {e}")
            try:
                self.basex_connector.execute_command(f"ALTER DB {temp_db} {db_name}")
            except Exception as e:
                # Recovery: recreate the live DB directly from the file content.
                self.logger.error(f"ALTER DB failed, attempting direct recreation: {e}")
                try:
                    self.basex_connector.create_database(db_name)
                    self.basex_connector.add_resource(
                        'lift.xml', backup_content, db_name=db_name
                    )
                except Exception as r2:
                    preserve_temp = True
                    # Never leave an empty live DB behind if the recovery
                    # partially succeeded (create_database OK but add_resource
                    # failed) — drop it so the app doesn't silently serve an
                    # empty dictionary.
                    try:
                        self.basex_connector.execute_command(f"DROP DB {db_name}")
                    except Exception:
                        pass
                    raise DatabaseError(
                        f"Restore failed after dropping the live database. The "
                        f"recovered data is preserved in temporary database "
                        f"'{temp_db}': {r2}"
                    ) from r2
            finally:
                # Clean up the temp DB unless it was preserved as the recovery copy.
                if not preserve_temp:
                    try:
                        self.basex_connector.execute_command(f"DROP DB {temp_db}")
                    except Exception:
                        pass
            
            # Restore supplementary files
            try:
                from flask import current_app
                instance_path = Path(current_app.instance_path)
            except RuntimeError:
                # Working outside of application context (e.g., in unit tests)
                # Skip supplementary file restoration
                self.logger.warning("Cannot restore supplementary files outside of application context")
                return True

            # 1. Settings
            settings_path = backup_path.with_name(backup_path.name + '.settings.json')
            if settings_path.exists():
                try:
                    settings_data = json.loads(settings_path.read_text(encoding='utf-8'))
                    if hasattr(current_app, 'config_manager') and current_app.config_manager:
                        # Assuming settings_data is a list of projects or a single project dict
                        if isinstance(settings_data, list) and len(settings_data) > 0:
                            current_app.config_manager.update_current_settings(settings_data[0])
                        elif isinstance(settings_data, dict):
                            current_app.config_manager.update_current_settings(settings_data)
                        self.logger.info("Restored project settings from backup")
                except Exception as se:
                    self.logger.warning(f"Failed to restore settings: {se}")

            # 2. Display Profiles
            # NOTE: intentionally NOT copied back to instance/display_profiles.json.
            # CSSMappingService cannot load the serialized DisplayProfile shape
            # (the 'elements' relationship dicts crash _load_profiles), so writing
            # the sidecar there breaks app startup on the next boot. Profiles are
            # preserved in the backup artifact and the display_profiles DB table.
            dp_backup = backup_path.with_name(backup_path.name + '.display_profiles.json')
            if dp_backup.exists():
                self.logger.warning(
                    "Skipping display-profiles restore: sidecar format is "
                    "incompatible with CSSMappingService storage and would "
                    "corrupt instance/display_profiles.json"
                )

            # 3. Validation Rules
            if vr_path.exists():
                try:
                    shutil.copy2(vr_path, instance_path / 'validation_rules.json')
                    self.logger.info("Restored validation rules from backup")
                except Exception as vre:
                    self.logger.warning(f"Failed to restore validation rules: {vre}")

            # 4. Media
            media_backup = backup_path.with_name(backup_path.name + '.media')
            if media_backup.exists() and media_backup.is_dir():
                try:
                    uploads_dir = instance_path / 'uploads'
                    uploads_dir.mkdir(parents=True, exist_ok=True)
                    # Use copytree with dirs_exist_ok=True
                    shutil.copytree(media_backup, uploads_dir, dirs_exist_ok=True)
                    self.logger.info("Restored media files from backup")
                except Exception as me:
                    self.logger.warning(f"Failed to restore media files: {me}")

            self.logger.info(f"Database '{db_name}' restored successfully from {backup_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to restore database '{db_name}' from {backup_path}: {str(e)}"
            self.logger.error(error_msg)
            if isinstance(e, ValidationError):
                raise
            raise DatabaseError(error_msg) from e

    def validate_backup(self, backup_file_path: str) -> Dict[str, Any]:
        """
        Validate the integrity of a backup file.

        Args:
            backup_file_path: Path to the backup file to validate

        Returns:
            Dictionary containing validation results
        """
        backup_path = Path(backup_file_path)
        if not backup_path.exists():
            raise ValidationError(f"Backup file does not exist: {backup_path}")

        # Directories are not valid backup files
        if backup_path.is_dir():
            raise ValidationError(f"Backup path is a directory, not a file: {backup_path}")

        try:
            # Get file information
            file_stat = backup_path.stat()
            file_size = file_stat.st_size
            
            # Check if the file is a valid LIFT XML file by looking for essential tags
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # Read first 1KB to check format
                
            is_valid_lift = '<lift' in content and 'version=' in content
            is_not_empty = file_size > 0
            
            validation_result = {
                'file_exists': True,
                'file_size': file_size,
                'is_valid_lift': is_valid_lift,
                'is_not_empty': is_not_empty,
                'is_valid': is_valid_lift and is_not_empty
            }
            
            if not is_valid_lift:
                validation_result['errors'] = ['File does not contain valid LIFT XML structure']
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating backup file {backup_path}: {str(e)}")
            return {
                'file_exists': True,
                'file_size': 0,
                'is_valid_lift': False,
                'is_not_empty': False,
                'is_valid': False,
                'error': str(e)
            }

    def get_backup_info(self, backup_file_path: str) -> Dict[str, Any]:
        """
        Get information about a specific backup file.

        Args:
            backup_file_path: Path to the backup file

        Returns:
            Dictionary containing backup information
        """
        backup_path = Path(backup_file_path)
        if not backup_path.exists():
            raise ValidationError(f"Backup file does not exist: {backup_path}")

        try:
            file_stat = backup_path.stat()
            
            info = {
                'file_path': str(backup_path),
                'file_size': file_stat.st_size,
                'created_time': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'backup_name': backup_path.name,
                'is_valid': self.validate_backup(backup_file_path)['is_valid']
            }
            
            return info
        except Exception as e:
            raise DatabaseError(f"Failed to get backup info: {str(e)}") from e

    def list_backups(self, db_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available backups, optionally filtered by database name.

        Args:
            db_name: Optional database name to filter backups

        Returns:
            List of backup dictionaries
        """
        backups = []
        found_ids = set()
        found_paths = set()

        # Phase 1: Scan for .meta.json files
        for meta_file in self.backup_directory.glob("*.lift.meta.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)

                    # Extract info
                    extracted_db_name = meta.get('db_name')
                    if db_name and extracted_db_name != db_name:
                        continue

                    # Try to find the associated lift file
                    file_path = None
                    if 'file_path' in meta:
                        file_path = Path(meta['file_path'])
                        if not file_path.exists():
                            # Maybe it was moved, check current directory
                            file_path = self.backup_directory / file_path.name

                    # From meta filename (meta_file is {filename}.meta.json)
                    if not file_path or not file_path.exists():
                        filename = meta_file.name.replace('.meta.json', '')
                        file_path = self.backup_directory / filename

                    if not file_path.exists():
                        continue

                    # Normalize canonical path to avoid duplicates
                    canonical = str(file_path.resolve())
                    if canonical in found_paths:
                        # Another meta/file entry already registered for this exact backup file.
                        # Attempt to merge/choose the most complete metadata rather than silently skipping.
                        existing = None
                        for b in backups:
                            try:
                                if str(Path(b.get('file_path')).resolve()) == canonical:
                                    existing = b
                                    break
                            except Exception:
                                continue

                        # If existing found, prefer the metadata that has a description or a newer timestamp
                        if existing:
                            prefers_new = False
                            # If existing lacks description and new meta has it, prefer new
                            if (not existing.get('description')) and meta.get('description'):
                                prefers_new = True
                            else:
                                # Try to compare timestamps
                                try:
                                    existing_ts = datetime.fromisoformat(existing.get('timestamp')) if existing.get('timestamp') else None
                                except Exception:
                                    existing_ts = None
                                try:
                                    meta_ts = None
                                    if 'timestamp' in meta:
                                        meta_ts = datetime.fromisoformat(meta.get('timestamp'))
                                    else:
                                        if '_backup_' in file_path.name:
                                            ts_part = file_path.name.split('_backup_')[1].replace('.lift','')
                                            meta_ts = datetime.strptime(ts_part, "%Y%m%d_%H%M%S")
                                except Exception:
                                    meta_ts = None

                                if existing_ts and meta_ts and meta_ts > existing_ts:
                                    prefers_new = True

                            if prefers_new:
                                # Replace the existing list entry with the new metadata (merge important fields)
                                try:
                                    old_id = existing.get('id')
                                    if old_id in found_ids:
                                        found_ids.discard(old_id)
                                except Exception as e:
                                    self.logger.debug(f"Could not discard backup ID: {e}")

                                # Ensure meta has id and timestamp set (same code as normal path)
                                if not meta.get('id'):
                                    if '_backup_' in file_path.name:
                                        try:
                                            parts = file_path.name.split('_backup_')
                                            db = parts[0]
                                            ts_part = parts[1].replace('.lift', '')
                                            meta['id'] = f"{db}_{ts_part}"
                                        except Exception:
                                            meta['id'] = file_path.name
                                    else:
                                        meta['id'] = file_path.name

                                if 'timestamp' not in meta:
                                    timestamp_str = None
                                    if '_backup_' in file_path.name:
                                        try:
                                            ts_part = file_path.name.split('_backup_')[1].replace('.lift', '')
                                            timestamp_str = datetime.strptime(ts_part, "%Y%m%d_%H%M%S").isoformat()
                                        except Exception as e:
                                            self.logger.debug(f"Caught exception: {e}")
                                    if not timestamp_str:
                                        timestamp_str = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                                    meta['timestamp'] = timestamp_str

                                if 'is_valid' not in meta:
                                    validation = self.validate_backup(str(file_path))
                                    meta['is_valid'] = validation['is_valid']

                                if 'display_name' not in meta or not meta['display_name']:
                                    if meta.get('description') and str(meta['description']).strip():
                                        meta['display_name'] = str(meta['description']).strip()
                                    elif file_path.name:
                                        meta['display_name'] = file_path.name
                                    else:
                                        meta['display_name'] = meta.get('timestamp') or ''

                                # Replace in backups list
                                try:
                                    idx = backups.index(existing)
                                    backups[idx] = meta
                                except Exception:
                                    # fallback: append if replace fails
                                    backups.append(meta)

                                # Record new id and path
                                found_ids.add(meta.get('id'))
                                found_paths.add(canonical)

                            # In any case, skip adding a new entry in order to avoid duplicates
                        # Whether we replaced or not, skip to next meta file
                        continue

                    # Update meta with current values
                    meta['file_path'] = str(file_path)
                    meta['filename'] = file_path.name

                    # Ensure metadata has an id (otherwise dedup logic can fail)
                    if not meta.get('id'):
                        if '_backup_' in file_path.name:
                            try:
                                parts = file_path.name.split('_backup_')
                                db = parts[0]
                                ts_part = parts[1].replace('.lift', '')
                                meta['id'] = f"{db}_{ts_part}"
                            except Exception:
                                meta['id'] = file_path.name
                        else:
                            meta['id'] = file_path.name

                    # Ensure timestamp exists
                    if 'timestamp' not in meta:
                        timestamp_str = None
                        # Try to extract from filename
                        if '_backup_' in file_path.name:
                            try:
                                ts_part = file_path.name.split('_backup_')[1].replace('.lift', '')
                                timestamp_str = datetime.strptime(ts_part, "%Y%m%d_%H%M%S").isoformat()
                            except Exception as e:
                                self.logger.debug(f"Caught exception: {e}")
                        if not timestamp_str:
                            timestamp_str = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        meta['timestamp'] = timestamp_str

                    # Add is_valid flag
                    if 'is_valid' not in meta:
                        validation = self.validate_backup(str(file_path))
                        meta['is_valid'] = validation['is_valid']

                    # Ensure display_name is set (similar to Backup.to_dict() logic)
                    if 'display_name' not in meta or not meta['display_name']:
                        if meta.get('description') and str(meta['description']).strip():
                            meta['display_name'] = str(meta['description']).strip()
                        elif file_path.name:
                            meta['display_name'] = file_path.name
                        else:
                            meta['display_name'] = meta.get('timestamp') or ''

                    backups.append(meta)
                    found_ids.add(meta.get('id'))
                    found_paths.add(canonical)
            except Exception:
                continue

        # Phase 2: Scan for .lift files not covered by meta
        for file_path in self.backup_directory.glob("*.lift"):
            filename = file_path.name
            # Expected format: {db_name}_backup_{timestamp}.lift
            if "_backup_" not in filename:
                continue

            parts = filename.split("_backup_")
            if len(parts) != 2:
                continue

            extracted_db_name = parts[0]
            timestamp_part = parts[1].replace(".lift", "")
            backup_id = f"{extracted_db_name}_{timestamp_part}"

            # If this exact file is already processed via metadata, skip it
            canonical = str(file_path.resolve())
            if canonical in found_paths:
                continue

            if backup_id in found_ids:
                # already handled by metadata
                continue

            # If filtering by database name, skip if it doesn't match
            if db_name and extracted_db_name != db_name:
                continue

            # Try to parse timestamp
            try:
                # Format is YYYYMMDD_HHMMSS
                timestamp = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
                timestamp_str = timestamp.isoformat()
            except ValueError:
                # If timestamp parsing fails, use file modification time
                file_stat = file_path.stat()
                timestamp_str = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

            # Validate backup
            try:
                validation = self.validate_backup(str(file_path))
            except ValidationError:
                # Skip directories and other invalid backup paths gracefully
                continue

            # Skip empty files (size 0) without metadata
            if file_path.stat().st_size == 0:
                continue

            backup_info = {
                'id': backup_id,
                'db_name': extracted_db_name,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'timestamp': timestamp_str,
                'is_valid': validation['is_valid'],
                'filename': filename,
                'status': 'completed',
                'type': 'manual'
            }
            backups.append(backup_info)
            found_ids.add(backup_id)
            found_paths.add(canonical)

        # Sort by timestamp, newest first
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return backups

    def cleanup_old_backups(self, db_name: str, keep_count: int = 10) -> int:
        """
        Remove old backups, keeping only the most recent ones.

        Args:
            db_name: Name of the database
            keep_count: Number of recent backups to keep

        Returns:
            Number of backups deleted
        """
        all_backups = self.list_backups(db_name)

        if len(all_backups) <= keep_count:
            return 0  # Nothing to delete

        # Keep the most recent backups and delete the rest
        backups_to_delete = all_backups[keep_count:]
        deleted_count = 0

        for backup in backups_to_delete:
            try:
                # delete_backup removes the file AND its sidecars/metadata, so
                # pruned backups don't linger as ghost entries in history.
                if self.delete_backup(backup['id']):
                    deleted_count += 1
                    self.logger.info(f"Deleted old backup: {backup['file_path']}")
            except Exception as e:
                self.logger.error(f"Failed to delete backup {backup['file_path']}: {str(e)}")

        return deleted_count

    def _write_ranges_sidecar(self, lift_path: Path, db_name: str) -> None:
        """Write ranges sidecar file with real range data."""
        if lift_path.is_dir():
            canonical = lift_path / 'lift-ranges'
        else:
            canonical = lift_path.parent / 'lift-ranges'

        # Specific lift-ranges file for this backup to avoid collision
        specific_ranges = lift_path.with_name(lift_path.name + '.lift-ranges')

        # Also create legacy .ranges.xml for test compatibility
        legacy_xml = Path(str(lift_path) + '.ranges.xml')

        # Remove stale artifacts
        for stale in [
            canonical.parent / 'lift-ranges.xml',
            canonical.parent / '.lift-ranges.xml',
            Path(str(lift_path) + '.ranges.xml'),
            Path(str(lift_path) + '.lift-ranges.xml'),
            Path(str(lift_path) + '.lift-ranges'),
        ]:
            try:
                if stale.exists():
                    # SECURITY: Ensure we only delete within backup directory
                    try:
                        stale.resolve().relative_to(self.backup_directory.resolve())
                    except ValueError:
                        # Path is outside backup_directory, skip deletion
                        self.logger.warning(
                            f"Skipped deletion of file outside backup directory: {stale}"
                        )
                        continue
                    
                    if stale.is_dir():
                        shutil.rmtree(stale, ignore_errors=True)
                    else:
                        stale.unlink()
            except Exception as e:
                self.logger.debug(f"Caught exception: {e}")

        # Generate ranges using real data from database or sample file
        try:
            # We don't want to change the global database state of the connector permanently
            # but we need it for this operation
            original_db = self.basex_connector.database
            self.basex_connector.database = db_name
            try:
                self.basex_connector.execute_command(f"OPEN {db_name}")
            except Exception as e:
                self.logger.debug(f"Caught exception: {e}")
            
            # Try to get ranges from database
            from app.services.ranges_service import RangesService
            ranges_service = RangesService(self.basex_connector)
            ranges_data = ranges_service.get_all_ranges()
            
            # Restore original db name
            self.basex_connector.database = original_db

            if ranges_data:
                # Use real ranges from database
                from app.services.lift_export_service import LIFTExportService
                export_service = LIFTExportService(self.basex_connector, ranges_service)
                # Write to all formats
                export_service._write_ranges_xml(ranges_data, str(canonical))
                export_service._write_ranges_xml(ranges_data, str(specific_ranges))
                export_service._write_ranges_xml(ranges_data, str(legacy_xml))
                self.logger.info(f"Exported {len(ranges_data)} real ranges from database")
                return
        except Exception as e:
            self.logger.warning(f"Failed to export ranges from database: {e}")

        # Fallback to sample ranges file if available
        try:
            sample_ranges = Path(__file__).parent.parent / 'sample-lift-file' / 'sample-lift-file.lift-ranges'
            if sample_ranges.exists():
                shutil.copy2(sample_ranges, canonical)
                shutil.copy2(sample_ranges, specific_ranges)
                shutil.copy2(sample_ranges, legacy_xml)
                self.logger.info("Used sample ranges file as fallback")
                return
        except Exception as e:
            self.logger.warning(f"Failed to copy sample ranges: {e}")

        # Final fallback - generate minimal but real ranges
        self._generate_minimal_ranges(specific_ranges)
        # Also copy to other locations
        if specific_ranges.exists():
            shutil.copy2(specific_ranges, canonical)
            shutil.copy2(specific_ranges, legacy_xml)

    def _generate_minimal_ranges(self, output_path: Path) -> None:
        """Generate minimal but meaningful ranges when no data is available."""
        import xml.etree.ElementTree as ET
        from xml.dom import minidom
        
        root = ET.Element('lift-ranges')
        
        # Add essential ranges with real values
        essential_ranges = {
            'grammatical-info': [
                {'id': 'Noun', 'label': 'Noun', 'abbrev': 'n'},
                {'id': 'Verb', 'label': 'Verb', 'abbrev': 'v'},
                {'id': 'Adjective', 'label': 'Adjective', 'abbrev': 'adj'},
                {'id': 'Adverb', 'label': 'Adverb', 'abbrev': 'adv'}
            ],
            'semantic-domain-ddp4': [
                {'id': '1', 'label': 'Universe', 'abbrev': '1'},
                {'id': '2', 'label': 'Earth', 'abbrev': '2'}
            ],
            'status': [
                {'id': 'Draft', 'label': 'Draft', 'abbrev': 'draft'},
                {'id': 'Reviewed', 'label': 'Reviewed', 'abbrev': 'rev'},
                {'id': 'Approved', 'label': 'Approved', 'abbrev': 'app'}
            ]
        }
        
        for range_id, elements in essential_ranges.items():
            range_elem = ET.SubElement(root, 'range')
            range_elem.set('id', range_id)
            
            for element in elements:
                elem = ET.SubElement(range_elem, 'range-element')
                elem.set('id', element['id'])
                
                label = ET.SubElement(elem, 'label')
                form = ET.SubElement(label, 'form')
                form.set('lang', 'en')
                text = ET.SubElement(form, 'text')
                text.text = element['label']
                
                if 'abbrev' in element:
                    abbrev = ET.SubElement(elem, 'abbrev')
                    form = ET.SubElement(abbrev, 'form')
                    form.set('lang', 'en')
                    text = ET.SubElement(form, 'text')
                    text.text = element['abbrev']
        
        # Write with pretty formatting
        from xml.dom import minidom
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # Remove empty lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        output_path.write_text('\n'.join(lines), encoding='utf-8')
        self.logger.info("Generated minimal ranges with real values")

    def _write_display_profiles_sidecar(self, lift_path: Path) -> None:
        """Write display profiles sidecar with real profile data."""
        dp_path = Path(str(lift_path) + '.display_profiles.json')
        
        # Try to get real display profiles from database
        try:
            from flask import current_app
            with current_app.app_context():
                from app.models.display_profile import DisplayProfile
                from app.models.workset_models import db
                
                profiles = db.session.query(DisplayProfile).all()
                if profiles:
                    # Export real profiles data
                    profiles_data = [profile.to_dict() for profile in profiles]
                    dp_path.write_text(json.dumps({'profiles': profiles_data}, ensure_ascii=False), encoding='utf-8')
                    self.logger.info(f"Exported {len(profiles)} real display profiles to backup")
                    return
        except Exception as e:
            self.logger.warning(f"Failed to export display profiles from database: {e}")
        
        # Fallback to instance file
        try:
            from flask import current_app
            src = Path(current_app.instance_path) / 'display_profiles.json'
            if src.exists() and src.is_file():
                content = src.read_text(encoding='utf-8')
                # Validate it's not just stub data. The instance file is stored
                # as a plain LIST of profile dicts (CSSMappingService._save_profiles),
                # but older writers also produced {'profiles': [...]} — accept both.
                try:
                    data = json.loads(content)
                    profiles_list = data.get('profiles') if isinstance(data, dict) else data
                    if (
                        isinstance(profiles_list, list)
                        and len(profiles_list) > 0
                        and all(isinstance(p, dict) for p in profiles_list)
                        and not (len(profiles_list) == 1
                                 and profiles_list[0].get('name') == 'default')
                    ):
                        dp_path.write_text(content, encoding='utf-8')
                        self.logger.info("Used display profiles from instance file")
                        return
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            self.logger.warning(f"Failed to load display profiles from instance file: {e}")

        # Create a reasonable default profile with actual structure
        default_profile = {
            'id': 1,
            'name': 'Default Profile',
            'description': 'Default display profile for entry rendering',
            'custom_css': '',
            'show_subentries': False,
            'number_senses': True,
            'number_senses_if_multiple': False,
            'is_default': True,
            'is_system': True,
            'created_at': '2025-01-01T00:00:00Z',
            'updated_at': '2025-01-01T00:00:00Z',
            'elements': [
                {
                    'id': 1,
                    'profile_id': 1,
                    'lift_element': 'lexical-unit',
                    'css_class': 'lexical-unit',
                    'visibility': 'always',
                    'display_order': 1,
                    'language_filter': '*',
                    'prefix': '',
                    'suffix': '',
                    'config': None
                },
                {
                    'id': 2,
                    'profile_id': 1,
                    'lift_element': 'sense',
                    'css_class': 'sense',
                    'visibility': 'always',
                    'display_order': 2,
                    'language_filter': '*',
                    'prefix': '',
                    'suffix': '',
                    'config': None
                },
                {
                    'id': 3,
                    'profile_id': 1,
                    'lift_element': 'definition',
                    'css_class': 'definition',
                    'visibility': 'if-content',
                    'display_order': 3,
                    'language_filter': '*',
                    'prefix': '',
                    'suffix': '',
                    'config': None
                }
            ]
        }
        
        dp_path.write_text(
            json.dumps({'profiles': [default_profile]}, ensure_ascii=False),
            encoding='utf-8',
        )
        self.logger.info("Created comprehensive default display profile for backup")

    def _write_validation_rules_sidecar(self, lift_path: Path) -> None:
        """Write validation rules sidecar with real validation rules."""
        rules_path = Path(str(lift_path) + '.validation_rules.json')
        
        # Try to get real validation rules from the main validation_rules.json file
        try:
            # Try app root first
            app_root = Path(__file__).parent.parent
            validation_file = app_root / 'validation_rules.json'
            
            if validation_file.exists():
                content = validation_file.read_text(encoding='utf-8')
                # Validate it's not empty stub data
                try:
                    data = json.loads(content)
                    if data and data.get('rules') and len(data['rules']) > 0:
                        rules_path.write_text(content, encoding='utf-8')
                        self.logger.info(f"Used real validation rules with {len(data['rules'])} rules")
                        return
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            self.logger.warning(f"Failed to load validation rules from app root: {e}")
        
        # Try instance path
        try:
            from flask import current_app
            instance_candidate = Path(current_app.instance_path) / 'validation_rules.json'
            if instance_candidate.exists() and instance_candidate.is_file():
                content = instance_candidate.read_text(encoding='utf-8')
                try:
                    data = json.loads(content)
                    if data and data.get('rules') and len(data['rules']) > 0:
                        rules_path.write_text(content, encoding='utf-8')
                        self.logger.info("Used validation rules from instance path")
                        return
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            self.logger.warning(f"Failed to load validation rules from instance: {e}")

        # Create minimal but functional validation rules
        minimal_rules = {
            "version": "1.0",
            "description": "Essential validation rules for dictionary entries",
            "rules": {
                "R1.1.1": {
                    "name": "entry_id_required",
                    "description": "Entry ID is required and must be non-empty",
                    "category": "entry_level",
                    "priority": "critical",
                    "path": "$.id",
                    "condition": "required",
                    "validation": {
                        "type": "string",
                        "minLength": 1
                    },
                    "error_message": "Entry ID is required and must be non-empty",
                    "client_side": True
                },
                "R1.1.2": {
                    "name": "lexical_unit_required",
                    "description": "Lexical unit is required and must contain at least one language entry",
                    "category": "entry_level",
                    "priority": "critical",
                    "path": "$.lexical_unit",
                    "condition": "required",
                    "validation": {
                        "type": "object",
                        "minProperties": 1
                    },
                    "error_message": "Lexical unit is required and must contain at least one language entry",
                    "client_side": True
                },
                "R2.1.1": {
                    "name": "sense_id_required",
                    "description": "Sense ID is required and must be non-empty",
                    "category": "sense_level",
                    "priority": "critical",
                    "path": "$.senses[*].id",
                    "condition": "required",
                    "validation": {
                        "type": "string",
                        "minLength": 1
                    },
                    "error_message": "Sense ID is required and must be non-empty",
                    "client_side": True
                }
            }
        }
        
        rules_path.write_text(json.dumps(minimal_rules, ensure_ascii=False, indent=2), encoding='utf-8')
        self.logger.info("Created minimal validation rules for backup")

    def _write_settings_sidecar(self, lift_path: Path) -> None:
        """Write settings sidecar with real project settings."""
        settings_path = Path(str(lift_path) + '.settings.json')

        cfg = None
        try:
            from flask import current_app
            # Try to get config_manager - this raises RuntimeError if outside app context
            cfg = getattr(current_app, 'config_manager', None)
        except RuntimeError:
            # No application context - skip settings export silently
            cfg = None

        if cfg is not None:
            try:
                # Export all known projects for safety (multi-project installs)
                projects = []
                try:
                    projects = [p.settings_json for p in cfg.get_all_settings()]
                except Exception:
                    # fallback to current settings only
                    cur = cfg.update_current_settings({})
                    if cur is not None:
                        projects = [cur.settings_json]

                if not projects:
                    try:
                        cur = cfg.update_current_settings({})
                        if cur is not None:
                            projects = [cur.settings_json]
                    except Exception:
                        projects = []

                if projects:
                    settings_path.write_text(json.dumps(projects, ensure_ascii=False), encoding='utf-8')
                    self.logger.info(f"Exported {len(projects)} project settings")
                    return
            except Exception as e:
                self.logger.warning(f"Failed to export settings: {e}")

        # Create minimal settings
        minimal_settings = [{
            "project_id": 1,
            "project_name": "Default Project",
            "source_language": "en",
            "target_languages": ["pl"],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }]
        
        settings_path.write_text(json.dumps(minimal_settings, ensure_ascii=False, indent=2), encoding='utf-8')
        self.logger.info("Created minimal settings for backup")

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup by ID.

        Resolves the backup via its metadata file (handles any id format,
        including the UUID ids produced by real backups) and removes the
        backup file (or directory) together with its sidecar files.

        Args:
            backup_id: ID of the backup to delete.

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            info = self.get_backup_by_id(backup_id)
            if not info or not info.get('file_path'):
                return False
            file_path = Path(info['file_path'])

            deleted_any = False

            # Remove main backup file or directory
            if file_path.exists():
                if file_path.is_dir():
                    shutil.rmtree(file_path, ignore_errors=True)
                else:
                    file_path.unlink()
                deleted_any = True

            # Remove sidecar files
            sidecars = [
                Path(str(file_path) + '.ranges.xml'),
                Path(str(file_path) + '.lift-ranges'),
                Path(str(file_path) + '.display_profiles.json'),
                Path(str(file_path) + '.validation_rules.json'),
                Path(str(file_path) + '.settings.json'),
                Path(str(file_path) + '.meta.json'),
                Path(str(file_path) + '.media'),
            ]

            for sidecar in sidecars:
                try:
                    if sidecar.exists():
                        if sidecar.is_dir():
                            shutil.rmtree(sidecar, ignore_errors=True)
                        else:
                            sidecar.unlink()
                        deleted_any = True
                except Exception as e:
                    self.logger.debug(f"Caught exception: {e}")

            # Note: We do NOT delete the shared 'self.backup_directory / "lift-ranges"'
            # as it might be used by other backups or the system.

            return deleted_any
        except Exception:
            return False
