"""
Migration: Add number_senses_if_multiple to display profiles.

This migration adds the number_senses_if_multiple boolean field to the DisplayProfile model,
which controls whether sense numbering should only be applied when an entry has multiple senses.

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
    """Add number_senses_if_multiple column to display_profiles."""
    app = create_app('development')
    
    with app.app_context():
        try:
            # Add number_senses_if_multiple column to display_profiles
            print("Adding number_senses_if_multiple column to display_profiles...")
            db.session.execute(db.text("""
                ALTER TABLE display_profiles 
                ADD COLUMN IF NOT EXISTS number_senses_if_multiple BOOLEAN DEFAULT FALSE NOT NULL
            """))
            
            db.session.commit()
            print("✓ Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            raise


if __name__ == '__main__':
    migrate()
