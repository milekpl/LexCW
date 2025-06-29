#!/usr/bin/env python3
"""
Check PostgreSQL table structure for debugging corpus stats issue.
"""
import os
from app.database.postgresql_connector import PostgreSQLConfig
from app.database.corpus_migrator import CorpusMigrator

def main():
    # Create PostgreSQL config using the same parameters as in views.py
    config = PostgreSQLConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'dictionary_test'),
        username=os.getenv('POSTGRES_USER', 'dict_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
    )

    print(f'Config: host={config.host}, port={config.port}, database={config.database}, username={config.username}')

    try:
        migrator = CorpusMigrator(config)
        
        # Try to connect and list tables
        conn = migrator._get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cur.fetchall()]
            print(f'Available tables: {tables}')
            
            # Check if parallel_corpus exists specifically
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'parallel_corpus'
                )
            """)
            exists = cur.fetchone()[0]
            print(f'parallel_corpus table exists: {exists}')
            
            if exists:
                # If table exists, check its structure
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'parallel_corpus'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                print(f'parallel_corpus columns: {columns}')
                
                # Try to count records
                cur.execute("SELECT COUNT(*) FROM parallel_corpus")
                count = cur.fetchone()[0]
                print(f'parallel_corpus record count: {count}')
        
        conn.close()
        
        # Now try the actual get_corpus_stats method
        print("\nTesting get_corpus_stats method:")
        try:
            stats = migrator.get_corpus_stats()
            print(f'Stats: {stats}')
        except Exception as e:
            print(f'Error getting stats: {e}')
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f'Connection Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
