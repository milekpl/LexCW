import logging
import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)

def create_workset_tables(conn_pool: pool.SimpleConnectionPool):
    """Create workset-related tables in the database.

    Mirrors the app's models (workset_models.py) plus the raw-SQL columns used
    by the worksets API (ai_review_*). ``CREATE TABLE IF NOT EXISTS`` alone
    cannot repair pre-existing tables created by an older schema, so every
    column is also ensured with an idempotent ``ADD COLUMN IF NOT EXISTS``.
    """
    try:
        with conn_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS worksets (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        query JSONB NOT NULL,
                        total_entries INTEGER DEFAULT 0,
                        ui_settings JSONB,
                        created_by_user_id INTEGER,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("ALTER TABLE worksets ADD COLUMN IF NOT EXISTS ui_settings JSONB")
                cur.execute("ALTER TABLE worksets ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER")
                cur.execute("ALTER TABLE worksets ADD COLUMN IF NOT EXISTS description TEXT")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS workset_entries (
                        id SERIAL PRIMARY KEY,
                        workset_id INTEGER NOT NULL REFERENCES worksets(id) ON DELETE CASCADE,
                        entry_id VARCHAR(255) NOT NULL,
                        status VARCHAR(50),
                        position INTEGER,
                        is_favorite BOOLEAN DEFAULT FALSE,
                        notes TEXT,
                        modified_at TIMESTAMP,
                        modified_by_user_id INTEGER,
                        notes_author_user_id INTEGER,
                        ai_review_status VARCHAR(50),
                        ai_reviewed_at TIMESTAMP,
                        ai_suggestions JSONB
                    );
                """)
                for col_ddl in (
                    "status VARCHAR(50)",
                    "position INTEGER",
                    "is_favorite BOOLEAN DEFAULT FALSE",
                    "notes TEXT",
                    "modified_at TIMESTAMP",
                    "modified_by_user_id INTEGER",
                    "notes_author_user_id INTEGER",
                    "ai_review_status VARCHAR(50)",
                    "ai_reviewed_at TIMESTAMP",
                    "ai_suggestions JSONB",
                ):
                    cur.execute(
                        f"ALTER TABLE workset_entries ADD COLUMN IF NOT EXISTS {col_ddl}"
                    )
                conn.commit()
                logger.info("Workset tables created successfully.")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error creating workset tables: {error}")
        raise
    finally:
        if 'conn' in locals() and conn is not None:
            conn_pool.putconn(conn)
