#!/usr/bin/env python3
"""
Migration script to add description column to worksets table.
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
    """Add description column to worksets table."""
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
            # Check if description column exists
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'worksets' AND column_name = 'description'
            """)
            if cur.fetchone():
                print("description column already exists, skipping.")
            else:
                print("Adding description column to worksets table...")
                cur.execute("""
                    ALTER TABLE worksets
                    ADD COLUMN description TEXT;
                """)
                print("description column added successfully.")

            conn.commit()
            print("\n✓ Migration completed successfully!")

    except psycopg2.Error as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    run_migration()
