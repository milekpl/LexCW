"""
Migration: Add default_language column to display profiles.

This migration adds the default_language field to the DisplayProfile model,
which controls the default language for all elements in a profile.

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
    """Add default_language column to display_profiles."""
    app = create_app('development')

    with app.app_context():
        try:
            # Add default_language column to display_profiles
            print("Adding default_language column to display_profiles...")
            db.session.execute(db.text("""
                ALTER TABLE display_profiles
                ADD COLUMN IF NOT EXISTS default_language VARCHAR(10) DEFAULT '*'
            """))

            db.session.commit()
            print("✓ Migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            raise


if __name__ == '__main__':
    migrate()