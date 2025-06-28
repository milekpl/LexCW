"""
Run the full migration directly using the existing table.
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

# Run the migration using the existing table
sqlite_path = Path(r'd:\Dokumenty\para_crawl.db')
print(f'Starting migration from {sqlite_path}')
print('Expected ~74.7M records...')

start_time = time.time()

try:
    # Export to CSV first
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False, encoding='utf-8') as temp_csv:
        csv_path = Path(temp_csv.name)
    
    print(f'Exporting to CSV: {csv_path}')
    exported_count = migrator.export_sqlite_to_csv(sqlite_path, csv_path)
    print(f'Exported {exported_count:,} records to CSV')
    
    # Import from CSV
    print('Importing CSV to PostgreSQL...')
    imported_count = migrator.import_csv_to_postgres(csv_path)
    print(f'Imported {imported_count:,} records')
    
    # Create indexes
    print('Creating indexes...')
    migrator.create_indexes()
    print('Indexes created successfully!')
    
    # Clean up CSV
    csv_path.unlink()
    print('Temporary CSV cleaned up')
    
    end_time = time.time()
    duration = end_time - start_time
    
    print('\\nMigration completed successfully!')
    print(f'Records processed: {imported_count:,}')
    print(f'Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)')
    print(f'Rate: {imported_count/duration:,.0f} records/second')
    
    # Get final stats
    final_stats = migrator.get_corpus_stats()
    print('\\nFinal corpus statistics:')
    for key, value in final_stats.items():
        print(f'  {key}: {value}')

except Exception as e:
    print(f'Migration failed: {e}')
    raise

print('Migration complete!')
