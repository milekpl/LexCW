"""
Test the new high-performance corpus migrator with a small sample.
"""
import sys
sys.path.append('.')

from app.database.corpus_migrator import CorpusMigrator
from app.database.postgresql_connector import PostgreSQLConfig
from pathlib import Path
import os
import tempfile
import sqlite3
from dotenv import load_dotenv

load_dotenv('.env.local')

# Use existing database instead of creating new one
postgres_config = PostgreSQLConfig(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
    username=os.getenv('POSTGRES_USER', 'dict_user'),
    password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
)

migrator = CorpusMigrator(postgres_config)

# Create schema first
migrator.create_schema()
print('Schema created successfully!')

# Test with small CSV export first
sqlite_path = Path(r'd:\Dokumenty\para_crawl.db')

with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False, encoding='utf-8') as temp_csv:
    csv_path = Path(temp_csv.name)

print(f'Exporting to temporary CSV: {csv_path}')

try:
    # Test exporting just a few records
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        import csv
        writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
        writer.writerow(['source_text', 'target_text'])
        
        cursor = conn.execute("SELECT c0en, c1pl FROM tmdata_content LIMIT 1000")
        for row in cursor:
            if row['c0en'] and row['c1pl']:
                writer.writerow([row['c0en'], row['c1pl']])
    
    conn.close()
    
    print('Sample CSV created, testing import...')
    
    # Test import
    imported_count = migrator.import_csv_to_postgres(csv_path)
    print(f'Successfully imported {imported_count} records')
    
    # Create indexes
    print('Creating indexes...')
    migrator.create_indexes()
    print('Indexes created successfully!')
    
    # Get stats
    stats = migrator.get_corpus_stats()
    print('Corpus statistics:')
    for key, value in stats.items():
        print(f'  {key}: {value}')

finally:
    # Clean up
    if csv_path.exists():
        csv_path.unlink()
        print('Temporary CSV cleaned up')

print('Test completed successfully!')
