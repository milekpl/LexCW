#!/usr/bin/env python3
"""
Simple database schema fix script to add missing columns to project_settings table.
"""
import psycopg2
from config import Config

def fix_database_schema():
    """Fix the database schema by adding missing columns."""
    config = Config()
    
    # Database connection parameters
    conn_params = {
        'host': config.PG_HOST,
        'port': config.PG_PORT,
        'database': config.PG_DATABASE,
        'user': config.PG_USER,
        'password': config.PG_PASSWORD
    }
    
    print(f"Connecting to database: {conn_params['database']} at {conn_params['host']}:{conn_params['port']}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected successfully!")
        
        # Check if project_settings table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'project_settings'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("project_settings table doesn't exist. Creating it...")
            cursor.execute("""
                CREATE TABLE project_settings (
                    id SERIAL PRIMARY KEY,
                    project_name VARCHAR(255) NOT NULL,
                    basex_db_name VARCHAR(255) NOT NULL,
                    source_language JSONB DEFAULT '{"code": "en", "name": "English"}'::jsonb,
                    target_languages JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    owner_id INTEGER NULL
                )
            """)
            print("Created project_settings table")
            
            # Insert default data
            cursor.execute("""
                INSERT INTO project_settings (
                    project_name, 
                    basex_db_name, 
                    source_language, 
                    target_languages
                ) VALUES (
                    'Dictionary Writing System',
                    'dictionary',
                    '{"code": "en", "name": "English"}'::jsonb,
                    '[{"code": "fr", "name": "French"}]'::jsonb
                )
            """)
            print("Inserted default project settings")
        else:
            print("project_settings table exists. Checking columns...")
            
            # Check existing columns
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'project_settings'
                ORDER BY ordinal_position
            """)
            columns = {row[0]: row[1] for row in cursor.fetchall()}
            print(f"Existing columns: {list(columns.keys())}")
            
            # Add source_language column if missing
            if 'source_language' not in columns:
                print("Adding source_language column...")
                cursor.execute("""
                    ALTER TABLE project_settings 
                    ADD COLUMN source_language JSONB DEFAULT '{"code": "en", "name": "English"}'::jsonb
                """)
                print("Added source_language column")
            else:
                print("source_language column already exists")
            
            # Add target_languages column if missing
            if 'target_languages' not in columns:
                print("Adding target_languages column...")
                cursor.execute("""
                    ALTER TABLE project_settings 
                    ADD COLUMN target_languages JSONB DEFAULT '[]'::jsonb
                """)
                print("Added target_languages column")
            else:
                print("target_languages column already exists")
            
            # Check if there's any data in the table
            cursor.execute("SELECT COUNT(*) FROM project_settings")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("No data found. Inserting default project settings...")
                cursor.execute("""
                    INSERT INTO project_settings (
                        project_name, 
                        basex_db_name, 
                        source_language, 
                        target_languages
                    ) VALUES (
                        'Dictionary Writing System',
                        'dictionary',
                        '{"code": "en", "name": "English"}'::jsonb,
                        '[{"code": "fr", "name": "French"}]'::jsonb
                    )
                """)
                print("Inserted default project settings")
            else:
                print(f"Found {count} existing records")
                
                # Update existing records to have proper JSON values if they're NULL
                cursor.execute("""
                    UPDATE project_settings 
                    SET source_language = '{"code": "en", "name": "English"}'::jsonb
                    WHERE source_language IS NULL
                """)
                
                cursor.execute("""
                    UPDATE project_settings 
                    SET target_languages = '[{"code": "fr", "name": "French"}]'::jsonb
                    WHERE target_languages IS NULL
                """)
                print("Updated NULL values with defaults")
        
        # Verify the final state
        cursor.execute("SELECT * FROM project_settings LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"Sample record: {row}")
        
        print("Database schema fix completed successfully!")
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
    
    return True

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n✓ Database schema has been fixed!")
        print("You can now restart your Flask application.")
    else:
        print("\n✗ Failed to fix database schema.")
        print("Please check the error messages above.")
