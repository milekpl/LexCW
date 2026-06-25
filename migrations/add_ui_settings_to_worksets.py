#!/usr/bin/env python3
"""
Migration script to add ui_settings column to worksets table.
This column stores AI quality control settings and other UI configurations.
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
    """Add ui_settings column to worksets table."""
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
            # Add ui_settings column as JSONB for flexibility
            print("Adding ui_settings column to worksets table...")
            cur.execute("""
                ALTER TABLE worksets
                ADD COLUMN IF NOT EXISTS ui_settings JSONB DEFAULT '{}';
            """)

            conn.commit()
            print("\n✓ Migration completed successfully!")
            print("  Added column: ui_settings (JSONB)")

    except psycopg2.Error as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    run_migration()
