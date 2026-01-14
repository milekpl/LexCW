"""
Migration: Add custom ranges tables for undefined SIL Fieldworks ranges.

This migration creates:
1. custom_ranges table for storing range definitions
2. custom_range_values table for storing range element values

Run this script to create the new database tables.
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
    """Create custom ranges tables."""
    app = create_app('development')
    
    with app.app_context():
        try:
            # Create custom_ranges table
            print("Creating custom_ranges table...")
            db.session.execute(db.text("""
                CREATE TABLE IF NOT EXISTS custom_ranges (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    range_type VARCHAR(50) NOT NULL CHECK (range_type IN ('relation', 'trait')),
                    range_name VARCHAR(255) NOT NULL,
                    element_id VARCHAR(255) NOT NULL,
                    element_label TEXT,
                    element_description TEXT,
                    parent_range VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create custom_range_values table
            print("Creating custom_range_values table...")
            db.session.execute(db.text("""
                CREATE TABLE IF NOT EXISTS custom_range_values (
                    id SERIAL PRIMARY KEY,
                    custom_range_id INTEGER NOT NULL,
                    value VARCHAR(255) NOT NULL,
                    label TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (custom_range_id) REFERENCES custom_ranges(id) ON DELETE CASCADE
                )
            """))
            
            # Create indexes for better performance
            print("Creating indexes...")
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_custom_ranges_project_id 
                ON custom_ranges(project_id)
            """))
            
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_custom_ranges_type_name 
                ON custom_ranges(range_type, range_name)
            """))
            
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_custom_range_values_range_id 
                ON custom_range_values(custom_range_id)
            """))
            
            db.session.commit()
            print("✓ Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            raise


def rollback():
    """Rollback the migration by dropping the tables."""
    app = create_app('development')
    
    with app.app_context():
        try:
            print("Rolling back migration - dropping custom ranges tables...")
            
            # Drop in reverse order due to foreign key constraints
            db.session.execute(db.text("DROP TABLE IF EXISTS custom_range_values"))
            db.session.execute(db.text("DROP TABLE IF EXISTS custom_ranges"))
            
            db.session.commit()
            print("✓ Rollback completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Rollback failed: {e}")
            raise


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback()
    else:
        migrate()