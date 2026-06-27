"""
Migration: Add external service URL columns to project_settings table.

Adds languagetool_url, corpus_url, and wordsketch_url columns
for configuring LanguageTool, corpus search, and word sketch services
from the settings UI.

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
            print("Adding external service URL columns to project_settings...")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS languagetool_url VARCHAR(500) DEFAULT 'http://localhost:8081'
            """))
            print("  ✓ languagetool_url")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS corpus_url VARCHAR(500) DEFAULT 'http://localhost:8082'
            """))
            print("  ✓ corpus_url")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS wordsketch_url VARCHAR(500) DEFAULT 'http://localhost:8083'
            """))
            print("  ✓ wordsketch_url")

            db.session.commit()

            print("")
            print("Migration completed successfully!")
            print("Added 3 columns to project_settings table:")
            print("  - languagetool_url (VARCHAR(500), default http://localhost:8081)")
            print("  - corpus_url (VARCHAR(500), default http://localhost:8082)")
            print("  - wordsketch_url (VARCHAR(500), default http://localhost:8083)")

        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("Starting migration: Add external service URLs to project_settings")
    migrate()
    print("Migration completed.")
