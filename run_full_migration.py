"""
Run the full migration with the new high-performance approach.
"""
import sys
sys.path.append('.')

from app.database.corpus_migrator import CorpusMigrator
from app.database.postgresql_connector import PostgreSQLConfig
from pathlib import Path
import os
import tempfile
import time
from dotenv import load_dotenv

load_dotenv('.env.local')

# Use existing database
postgres_config = PostgreSQLConfig(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
    username=os.getenv('POSTGRES_USER', 'dict_user'),
    password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
)

migrator = CorpusMigrator(postgres_config)

# Clear existing data and recreate schema
print('Creating schema...')
migrator.create_schema()
print('Schema created successfully!')

# Run the full migration
sqlite_path = Path(r'd:\Dokumenty\para_crawl.db')
print(f'Starting migration from {sqlite_path}')
print('Expected ~74.7M records...')

start_time = time.time()

try:
    # Use the optimized workflow: SQLite -> CSV -> PostgreSQL COPY
    stats = migrator.migrate_sqlite_corpus(sqlite_path, cleanup_temp=True)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f'\nMigration completed successfully!')
    print(f'Records processed: {stats.records_processed:,}')
    print(f'Records exported: {stats.records_exported:,}')
    print(f'Records imported: {stats.records_imported:,}')
    print(f'Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)')
    
    if stats.records_per_second:
        print(f'Rate: {stats.records_per_second:,.0f} records/second')
    
    # Get final stats
    final_stats = migrator.get_corpus_stats()
    print(f'\nFinal corpus statistics:')
    for key, value in final_stats.items():
        print(f'  {key}: {value}')

except Exception as e:
    print(f'Migration failed: {e}')
    raise

print('Migration complete!')
