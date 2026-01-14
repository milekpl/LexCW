#!/usr/bin/env python3
"""
Migration script to add curation columns to workset_entries table.
Adds: status, position, is_favorite, notes, modified_at
"""

import os
import sys
import psycopg2

# Get PostgreSQL connection params from environment
PG_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
PG_PORT = os.environ.get('POSTGRES_PORT', 5432)
PG_DB = os.environ.get('POSTGRES_DB', 'dictionary_analytics')
PG_USER = os.environ.get('POSTGRES_USER', 'dict_user')
PG_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'dict_pass')


def run_migration():
    """Add curation columns to workset_entries table."""
    conn = None
    try:
        print(f"Connecting to PostgreSQL at {PG_HOST}:{PG_PORT}...")
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        with conn.cursor() as cur:
            # Add status column with default 'pending'
            print("Adding status column...")
            cur.execute("""
                ALTER TABLE workset_entries
                ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending';
            """)

            # Add position column for ordered navigation
            print("Adding position column...")
            cur.execute("""
                ALTER TABLE workset_entries
                ADD COLUMN IF NOT EXISTS position INTEGER;
            """)

            # Add is_favorite column
            print("Adding is_favorite column...")
            cur.execute("""
                ALTER TABLE workset_entries
                ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT FALSE;
            """)

            # Add notes column for curator annotations
            print("Adding notes column...")
            cur.execute("""
                ALTER TABLE workset_entries
                ADD COLUMN IF NOT EXISTS notes TEXT;
            """)

            # Add modified_at column for tracking changes
            print("Adding modified_at column...")
            cur.execute("""
                ALTER TABLE workset_entries
                ADD COLUMN IF NOT EXISTS modified_at TIMESTAMP;
            """)

            # Create index for faster workset+status queries
            print("Creating status index...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workset_entries_status
                ON workset_entries(workset_id, status);
            """)

            # Create index for faster position-based queries
            print("Creating position index...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workset_entries_position
                ON workset_entries(workset_id, position);
            """)

            conn.commit()
            print("\n✓ Migration completed successfully!")
            print("  Added columns: status, position, is_favorite, notes, modified_at")
            print("  Created indexes: idx_workset_entries_status, idx_workset_entries_position")

    except psycopg2.Error as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    run_migration()
