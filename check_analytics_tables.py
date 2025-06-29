#!/usr/bin/env python3
"""
Check what tables exist in the dictionary_analytics PostgreSQL database.
"""
import os
import psycopg2
import psycopg2.extras
from app.database.postgresql_connector import PostgreSQLConfig

def check_analytics_postgres_tables():
    """Check what tables exist in PostgreSQL analytics database."""
    
    # Create PostgreSQL config for analytics database
    config = PostgreSQLConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),  # This is the key difference!
        username=os.getenv('POSTGRES_USER', 'dict_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
    )

    print(f'Connecting to ANALYTICS DB: host={config.host}, port={config.port}, database={config.database}, username={config.username}')

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.username,
            password=config.password
        )
        
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # List all tables
            cur.execute("""
                SELECT table_name, table_type
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cur.fetchall()
            print(f'\nAvailable tables in dictionary_analytics:')
            for table in tables:
                print(f'  - {table[0]} ({table[1]})')
            
            # Check if parallel_corpus exists specifically
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'parallel_corpus'
                )
            """)
            exists = cur.fetchone()[0]
            print(f'\nparallel_corpus table exists: {exists}')
            
            if exists:
                # Get row count
                cur.execute("SELECT COUNT(*) FROM parallel_corpus")
                count = cur.fetchone()[0]
                print(f'parallel_corpus row count: {count}')
                
                # Test the get_corpus_stats query
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_records,
                        AVG(LENGTH(source_text)) as avg_source_length,
                        AVG(LENGTH(target_text)) as avg_target_length,
                        MIN(created_at) as first_record,
                        MAX(created_at) as last_record
                    FROM parallel_corpus
                """)
                
                result = cur.fetchone()
                print(f'\nCorpus stats:')
                print(f'  Total records: {result[0]}')
                print(f'  Avg source length: {result[1]}')
                print(f'  Avg target length: {result[2]}')
                print(f'  First record: {result[3]}')
                print(f'  Last record: {result[4]}')
        
        conn.close()
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_analytics_postgres_tables()
