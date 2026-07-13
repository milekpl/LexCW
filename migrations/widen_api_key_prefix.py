"""
Migration: Widen api_keys.key_prefix from VARCHAR(8) to VARCHAR(16).

API keys are prefixed "sw_" followed by 8 characters, i.e. 11 characters, but
the column only held 8 — so every key creation failed with
StringDataRightTruncation and no API key could ever be issued.

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
    """Widen key_prefix column on api_keys."""
    app = create_app('development')

    with app.app_context():
        try:
            print("Widening api_keys.key_prefix to VARCHAR(16)...")
            db.session.execute(db.text("""
                ALTER TABLE api_keys
                ALTER COLUMN key_prefix TYPE VARCHAR(16)
            """))

            db.session.commit()
            print("✓ Migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            raise


if __name__ == '__main__':
    migrate()
