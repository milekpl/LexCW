"""
Migration: Add backup_settings column to project_settings table.

This migration adds the backup_settings JSON column to store backup configuration
including backup directory, schedule, retention policy, and compression settings.

Run this script to update the database schema.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.workset_models import db


def migrate():
    """Add backup_settings column to project_settings table."""
    app = create_app('development')

    with app.app_context():
        try:
            # Add backup_settings column to project_settings
            print("Adding backup_settings column to project_settings...")
            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS backup_settings JSONB
            """))

            # Commit the changes
            db.session.commit()

            print("✅ Migration completed successfully!")
            print("Added backup_settings JSONB column to project_settings table.")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("Starting migration: Add backup_settings to project_settings")
    migrate()
    print("Migration completed.")