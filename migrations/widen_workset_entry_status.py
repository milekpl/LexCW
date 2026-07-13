"""
Migration: Widen workset_entries.status from VARCHAR(20) to VARCHAR(50).

The WorksetEntry model declares status as String(50) but the column was created
as VARCHAR(20). Current status values ('approved', 'completed', 'rejected',
'failed', 'running') all fit, so nothing fails today — but any status longer
than 20 characters would raise StringDataRightTruncation at runtime, exactly as
api_keys.key_prefix did.

Found by tests/integration/test_schema_matches_models.py.

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
    """Widen status column on workset_entries."""
    app = create_app('development')

    with app.app_context():
        try:
            print("Widening workset_entries.status to VARCHAR(50)...")
            db.session.execute(db.text("""
                ALTER TABLE workset_entries
                ALTER COLUMN status TYPE VARCHAR(50)
            """))

            db.session.commit()
            print("✓ Migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            raise


if __name__ == '__main__':
    migrate()
