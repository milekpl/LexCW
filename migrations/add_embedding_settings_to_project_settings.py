"""
Migration: Add embedding settings columns to project_settings table.

Adds embedding_model, embedding_device, embedding_last_built, and embedding_sense_count
columns for configuring semantic vector search and models from settings UI.

Run this script to update the database schema.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.workset_models import db


def migrate():
    app = create_app('development')

    with app.app_context():
        try:
            print("Adding embedding settings columns to project_settings...")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(200) DEFAULT 'jinaai/jina-embeddings-v3'
            """))
            print("  ✓ embedding_model")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS embedding_device VARCHAR(20) DEFAULT 'cpu'
            """))
            print("  ✓ embedding_device")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS embedding_last_built TIMESTAMP
            """))
            print("  ✓ embedding_last_built")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS embedding_sense_count INTEGER DEFAULT 0
            """))
            print("  ✓ embedding_sense_count")

            db.session.commit()

            print("")
            print("Migration completed successfully!")

        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("Starting migration: Add embedding settings to project_settings")
    migrate()
    print("Migration completed.")
