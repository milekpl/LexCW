"""
Migration: Add field_visibility_defaults column to project_settings table.

This migration adds the field_visibility_defaults JSON column to store
project-level defaults for field visibility settings. This allows admins
to configure what sections and fields are visible by default for all users.

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
    """Add field_visibility_defaults column to project_settings table."""
    app = create_app('development')

    with app.app_context():
        try:
            # Add field_visibility_defaults column to project_settings
            print("Adding field_visibility_defaults column to project_settings...")
            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS field_visibility_defaults JSONB
            """))

            # Commit the changes
            db.session.commit()

            print("Migration completed successfully!")
            print("Added field_visibility_defaults JSONB column to project_settings table.")

        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("Starting migration: Add field_visibility_defaults to project_settings")
    migrate()
    print("Migration completed.")
