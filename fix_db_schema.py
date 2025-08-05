"""
Fix database schema for ProjectSettings
"""
from sqlalchemy import create_engine, text
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_schema():
    """Fix the database schema to ensure all columns exist."""
    # Use direct database connection string
    database_uri = "postgresql://dict_user:dict_pass@localhost/dictionary_analytics"
    
    # Create engine
    engine = create_engine(database_uri)
    
    # Connect to database
    with engine.connect() as conn:
        logger.info("Checking database schema...")
        
        # Ensure source_language column exists
        try:
            conn.execute(text("""
                ALTER TABLE project_settings 
                ADD COLUMN IF NOT EXISTS source_language JSONB 
                DEFAULT '{"code": "en", "name": "English"}'::jsonb
            """))
            logger.info("Added or confirmed source_language column exists")
        except Exception as e:
            logger.error(f"Error adding source_language column: {e}")
        
        # Ensure target_languages column exists
        try:
            conn.execute(text("""
                ALTER TABLE project_settings 
                ADD COLUMN IF NOT EXISTS target_languages JSONB 
                DEFAULT '[]'::jsonb
            """))
            logger.info("Added or confirmed target_languages column exists")
        except Exception as e:
            logger.error(f"Error adding target_languages column: {e}")
        
        # Insert default data if no records exist
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM project_settings"))
            count = result.scalar()
            
            if count == 0:
                logger.info("No records found, inserting default data")
                conn.execute(text("""
                    INSERT INTO project_settings (
                        project_name, 
                        basex_db_name, 
                        source_language, 
                        target_languages
                    ) VALUES (
                        'Lexicographic Curation Workbench',
                        'dictionary',
                        '{"code": "en", "name": "English"}'::jsonb,
                        '[{"code": "fr", "name": "French"}]'::jsonb
                    )
                """))
                logger.info("Default data inserted")
        except Exception as e:
            logger.error(f"Error checking or inserting default data: {e}")
            
        logger.info("Database schema fix completed")

if __name__ == "__main__":
    fix_schema()
