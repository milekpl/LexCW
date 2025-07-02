import psycopg2
import os
from app.database.postgresql_connector import PostgreSQLConfig

config = PostgreSQLConfig(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
    username=os.getenv('POSTGRES_USER', 'dict_user'),
    password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
)

conn = psycopg2.connect(
    host=config.host,
    port=config.port,
    database=config.database,
    user=config.username,
    password=config.password
)

try:
    with conn.cursor() as cur:
        # Check all schemas
        cur.execute('SELECT schema_name FROM information_schema.schemata ORDER BY schema_name')
        schemas = cur.fetchall()
        print('Available schemas:')
        for schema in schemas:
            print(f'  {schema[0]}')
        
        print()
        # Check tables in all schemas
        cur.execute('''
            SELECT table_schema, table_name, 
                   (SELECT count(*) FROM information_schema.columns 
                    WHERE table_name = t.table_name AND table_schema = t.table_schema) as column_count
            FROM information_schema.tables t 
            WHERE table_name LIKE '%corpus%' OR table_name LIKE '%parallel%'
            ORDER BY table_schema, table_name
        ''')
        tables = cur.fetchall()
        print('Tables with "corpus" or "parallel" in name:')
        for table in tables:
            print(f'  {table[0]}.{table[1]} ({table[2]} columns)')
            
        print()
        # Check if old table has data
        cur.execute('SELECT COUNT(*) FROM parallel_corpus')
        old_count = cur.fetchone()[0]
        print(f'Records in public.parallel_corpus: {old_count:,}')
        
        # Check if new table has data  
        try:
            cur.execute('SELECT COUNT(*) FROM corpus.parallel_corpus')
            new_count = cur.fetchone()[0]
            print(f'Records in corpus.parallel_corpus: {new_count:,}')
        except Exception as e:
            print(f'corpus.parallel_corpus table error: {e}')
            
finally:
    conn.close()
