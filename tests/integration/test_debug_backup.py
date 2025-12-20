
import pytest
import json
from pathlib import Path
from flask import Flask
from app.services.basex_backup_manager import BaseXBackupManager
from app.models.backup_models import Backup
from unittest.mock import Mock

def test_debug_get_backup_by_id(app):
    with app.app_context():
        from flask import current_app
        import os
        
        manager = current_app.injector.get(BaseXBackupManager)
        backup_dir = manager.get_backup_directory()
        print(f"\nDEBUG: Root path: {current_app.root_path}")
        print(f"DEBUG: Instance path: {current_app.instance_path}")
        print(f"DEBUG: Backup directory: {backup_dir}")
        print(f"DEBUG: Directory exists: {backup_dir.exists()}")
        
        # Ensure directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        filename = 'debug_db_backup_20251217_121212.lift'
        file_path = backup_dir / filename
        file_path.write_text('<lift/>', encoding='utf-8')
        
        meta = {
            'id': 'debug_db_20251217_121212',
            'db_name': 'debug_db',
            'file_path': str(file_path),
            'timestamp': '2025-12-17T12:12:12'
        }
        meta_path = backup_dir / (filename + '.meta.json')
        meta_path.write_text(json.dumps(meta), encoding='utf-8')
        print(f"DEBUG: Wrote meta to {meta_path}")
        print(f"DEBUG: Meta exists: {meta_path.exists()}")
        
        # Test retrieval
        try:
            retrieved = manager.get_backup_by_id(meta['id'])
            print(f"DEBUG: Successfully retrieved: {retrieved['id']}")
        except Exception as e:
            print(f"DEBUG: Failed to retrieve: {e}")
            # List all meta files in dir
            print("DEBUG: All .meta.json files in dir:")
            for f in backup_dir.glob("*.meta.json"):
                print(f"  - {f.name}")
            raise e
