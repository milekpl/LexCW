"""
Migration: Add CSS styles and language-specific configuration to display profiles.

This migration adds:
1. CSS styles storage to DisplayProfile (custom CSS rules for the profile)
2. Language filter to ProfileElement (e.g., 'en', 'pl', '*' for all languages)
3. Subentry configuration to ProfileElement

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
    """Add new columns to display profile tables."""
    app = create_app('development')
    
    with app.app_context():
        try:
            # Add custom_css column to display_profiles
            print("Adding custom_css column to display_profiles...")
            db.session.execute(db.text("""
                ALTER TABLE display_profiles 
                ADD COLUMN IF NOT EXISTS custom_css TEXT
            """))
            
            # Add language_filter column to profile_elements
            print("Adding language_filter column to profile_elements...")
            db.session.execute(db.text("""
                ALTER TABLE profile_elements 
                ADD COLUMN IF NOT EXISTS language_filter VARCHAR(10) DEFAULT '*'
            """))
            
            # Add show_subentries column to profile_elements
            print("Adding show_subentries column to profile_elements...")
            db.session.execute(db.text("""
                ALTER TABLE profile_elements 
                ADD COLUMN IF NOT EXISTS show_subentries BOOLEAN DEFAULT FALSE
            """))
            
            db.session.commit()
            print("✓ Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            raise


if __name__ == '__main__':
    migrate()
