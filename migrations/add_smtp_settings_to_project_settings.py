"""
Migration: Add SMTP settings columns to project_settings table.

This migration adds SMTP configuration columns to support password reset
and other email notifications from the application.

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
    """Add SMTP columns to project_settings table."""
    app = create_app('development')

    with app.app_context():
        try:
            # Add SMTP columns to project_settings
            print("Adding SMTP columns to project_settings...")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS smtp_host VARCHAR(255)
            """))
            print("  ✓ smtp_host")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS smtp_port INTEGER DEFAULT 587
            """))
            print("  ✓ smtp_port")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS smtp_username VARCHAR(255)
            """))
            print("  ✓ smtp_username")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS smtp_password VARCHAR(255)
            """))
            print("  ✓ smtp_password")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS smtp_use_tls BOOLEAN DEFAULT TRUE
            """))
            print("  ✓ smtp_use_tls")

            db.session.execute(db.text("""
                ALTER TABLE project_settings
                ADD COLUMN IF NOT EXISTS smtp_sender_email VARCHAR(255)
            """))
            print("  ✓ smtp_sender_email")

            # Commit the changes
            db.session.commit()

            print("")
            print("✅ Migration completed successfully!")
            print("Added 6 SMTP columns to project_settings table:")
            print("  - smtp_host (VARCHAR(255))")
            print("  - smtp_port (INTEGER, default 587)")
            print("  - smtp_username (VARCHAR(255))")
            print("  - smtp_password (VARCHAR(255))")
            print("  - smtp_use_tls (BOOLEAN, default TRUE)")
            print("  - smtp_sender_email (VARCHAR(255))")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("Starting migration: Add SMTP settings to project_settings")
    migrate()
    print("Migration completed.")
