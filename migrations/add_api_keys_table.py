"""
Migration: Add api_keys table for machine-to-machine API authentication.

This migration creates the api_keys table and adds the initial API key
scopes infrastructure. Each key is tied to a project and has a label,
hashed key, and optional scope restrictions.

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
    """Create the api_keys table."""
    app = create_app("development")

    with app.app_context():
        try:
            print("Creating api_keys table...")

            db.session.execute(
                db.text(
                    """
                CREATE TABLE IF NOT EXISTS api_keys (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES project_settings(id) ON DELETE CASCADE,
                    label VARCHAR(100) NOT NULL,
                    key_hash VARCHAR(255) NOT NULL,
                    key_prefix VARCHAR(8) NOT NULL,
                    scopes JSONB NOT NULL DEFAULT '[]',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP WITH TIME ZONE
                )
            """
                )
            )

            # Unique index on key_prefix for fast lookup
            db.session.execute(
                db.text(
                    """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_prefix
                ON api_keys (key_prefix)
            """
                )
            )

            db.session.commit()

            print("✅ Migration completed successfully!")
            print("Created api_keys table with columns:")
            print("  - id (SERIAL PRIMARY KEY)")
            print("  - project_id (FK → project_settings.id)")
            print("  - label (VARCHAR(100))")
            print("  - key_hash (VARCHAR(255))")
            print("  - key_prefix (VARCHAR(8), UNIQUE INDEX)")
            print("  - scopes (JSONB)")
            print("  - is_active (BOOLEAN, DEFAULT TRUE)")
            print("  - created_at (TIMESTAMP WITH TIME ZONE)")
            print("  - last_used_at (TIMESTAMP WITH TIME ZONE)")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("Starting migration: Add api_keys table")
    migrate()
    print("Migration completed.")
