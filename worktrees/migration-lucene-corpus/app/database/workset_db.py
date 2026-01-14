import logging
import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)

def create_workset_tables(conn_pool: pool.SimpleConnectionPool):
    """Create workset-related tables in the database."""
    try:
        with conn_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS worksets (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        query JSONB NOT NULL,
                        total_entries INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS workset_entries (
                        id SERIAL PRIMARY KEY,
                        workset_id INTEGER NOT NULL REFERENCES worksets(id) ON DELETE CASCADE,
                        entry_id VARCHAR(255) NOT NULL
                    );
                """)
                conn.commit()
                logger.info("Workset tables created successfully.")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error creating workset tables: {error}")
        raise
    finally:
        if 'conn' in locals() and conn is not None:
            conn_pool.putconn(conn)
