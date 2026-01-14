"""
Database migration script to update ProjectSettings schema.
Changes:
- Convert source_language from STRING to JSON
- Ensure target_languages is JSON type
"""
from __future__ import annotations
import logging
from sqlalchemy import text
from app import create_app
from app.models.project_settings import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the database migration to update the ProjectSettings table schema."""
    app = create_app()
    
    with app.app_context():
        logger.info("Starting database migration for ProjectSettings schema...")
        
        # Check if the columns exist
        conn = db.engine.connect()
        
        # Check if project_settings table exists
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'project_settings'
                )
            """))
            table_exists = result.scalar()
            if not table_exists:
                logger.info("Creating project_settings table as it doesn't exist")
                conn.execute(text("""
                    CREATE TABLE project_settings (
                        id SERIAL PRIMARY KEY,
                        project_name VARCHAR(255) NOT NULL,
                        basex_db_name VARCHAR(255) NOT NULL,
                        source_language JSONB DEFAULT '{"code": "en", "name": "English"}',
                        target_languages JSONB DEFAULT '[]',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        owner_id INTEGER NULL
                    )
                """))
                logger.info("Project_settings table created")
                settings_data = []
                return
        except Exception as e:
            logger.error(f"Error checking if table exists: {e}")
            return
            
        # Get column information
        try:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'project_settings'
            """))
            columns = {row[0]: row[1] for row in result}
            logger.info(f"Found columns: {columns}")
        except Exception as e:
            logger.error(f"Error retrieving column information: {e}")
            return
            
        # Get existing data to preserve it
        settings_data = []
        try:
            # Build query dynamically based on existing columns
            query_columns = ["id", "project_name", "basex_db_name"]
            if "source_language" in columns:
                query_columns.append("source_language")
            if "target_language" in columns:
                query_columns.append("target_language")
            elif "target_languages" in columns:
                query_columns.append("target_languages")
                
            query = f"SELECT {', '.join(query_columns)} FROM project_settings"
            logger.info(f"Data query: {query}")
            result = conn.execute(text(query))
            settings_data = result.fetchall()
            logger.info(f"Retrieved {len(settings_data)} project settings records")
        except Exception as e:
            logger.error(f"Error retrieving existing data: {e}")
            settings_data = []
        
        # Backup data if we have any
        if settings_data:
            logger.info("Creating temporary backup table...")
            try:
                conn.execute(text("""
                    CREATE TABLE project_settings_backup AS
                    SELECT * FROM project_settings
                """))
                logger.info("Backup table created successfully")
            except Exception as e:
                logger.error(f"Error creating backup table: {e}")
                return
        
        # Modify columns
        try:
            # Convert or add source_language as JSON
            logger.info("Modifying source_language column to JSON type...")
            
            if "source_language" in columns:
                # Column exists, convert it to JSON if it's not already
                if columns["source_language"].lower() != 'jsonb':
                    try:
                        conn.execute(text("""
                            ALTER TABLE project_settings 
                            ALTER COLUMN source_language TYPE jsonb USING 
                            json_build_object('code', source_language, 'name', source_language)
                        """))
                        logger.info("Converted source_language column to JSON")
                    except Exception as e:
                        logger.error(f"Error converting source_language column: {e}")
                        try:
                            conn.execute(text("ALTER TABLE project_settings DROP COLUMN source_language"))
                            conn.execute(text("ALTER TABLE project_settings ADD COLUMN source_language jsonb DEFAULT '{\"code\": \"en\", \"name\": \"English\"}'"))
                            logger.info("Recreated source_language column as JSON")
                        except Exception as e:
                            logger.error(f"Error recreating source_language column: {e}")
            else:
                # Column doesn't exist, add it
                try:
                    conn.execute(text("ALTER TABLE project_settings ADD COLUMN source_language jsonb DEFAULT '{\"code\": \"en\", \"name\": \"English\"}'"))
                    logger.info("Added source_language column as JSON")
                except Exception as e:
                    logger.error(f"Error adding source_language column: {e}")
            
            # Handle target_languages column
            logger.info("Ensuring target_languages column is JSON type...")
            
            if "target_languages" in columns:
                # Column exists, make sure it's JSON
                if columns["target_languages"].lower() != 'jsonb':
                    try:
                        conn.execute(text("""
                            ALTER TABLE project_settings 
                            ALTER COLUMN target_languages TYPE jsonb 
                            USING '[]'::jsonb
                        """))
                        logger.info("Converted target_languages column to JSON")
                    except Exception as e:
                        logger.error(f"Error converting target_languages column: {e}")
            elif "target_language" in columns:
                # Old single target_language exists, convert to target_languages array
                try:
                    # Add the target_languages column
                    conn.execute(text("ALTER TABLE project_settings ADD COLUMN target_languages jsonb DEFAULT '[]'"))
                    
                    # Convert old single values to array
                    conn.execute(text("""
                        UPDATE project_settings
                        SET target_languages = json_build_array(
                            json_build_object('code', target_language, 'name', target_language)
                        )
                    """))
                    logger.info("Converted target_language to target_languages array")
                except Exception as e:
                    logger.error(f"Error converting target_language to target_languages: {e}")
            else:
                # Neither column exists, add target_languages
                try:
                    conn.execute(text("ALTER TABLE project_settings ADD COLUMN target_languages jsonb DEFAULT '[]'"))
                    logger.info("Added target_languages column as JSON")
                except Exception as e:
                    logger.error(f"Error adding target_languages column: {e}")
                    return
            
            # Insert default data if needed
            result = conn.execute(text("SELECT COUNT(*) FROM project_settings"))
            count = result.scalar()
            
            if count == 0:
                logger.info("No data found, inserting default project settings")
                conn.execute(text("""
                    INSERT INTO project_settings (
                        project_name, 
                        basex_db_name, 
                        source_language, 
                        target_languages
                    ) VALUES (
                        'Lexicographic Curation Workbench',
                        'dictionary',
                        '{"code": "en", "name": "English"}',
                        '[{"code": "fr", "name": "French"}]'
                    )
                """))
                logger.info("Default project settings inserted")
            
            logger.info("Database migration completed successfully!")
        
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # If we have a backup, restore it
            if settings_data:
                try:
                    conn.execute(text("""
                        DROP TABLE IF EXISTS project_settings;
                        ALTER TABLE project_settings_backup RENAME TO project_settings;
                    """))
                    logger.info("Restored from backup table")
                except Exception as e:
                    logger.error(f"Error restoring from backup: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    run_migration()
