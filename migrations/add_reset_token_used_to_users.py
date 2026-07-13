"""
Migration: Add reset_token_used column to users.

The User model declares reset_token_used (password-reset single-use flag) but
the column was never added to the users table, so every User query failed with
UndefinedColumn. That broke session authentication, which in turn made
@_require_auth endpoints (e.g. POST /api/pronunciation/draft) return 401.

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
    """Add reset_token_used column to users."""
    app = create_app('development')

    with app.app_context():
        try:
            print("Adding reset_token_used column to users...")
            db.session.execute(db.text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS reset_token_used BOOLEAN NOT NULL DEFAULT FALSE
            """))

            db.session.commit()
            print("✓ Migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            raise


if __name__ == '__main__':
    migrate()
