from app.database.corpus_migrator import CorpusMigrator
from app.database.postgresql_connector import PostgreSQLConfig
import os

config = PostgreSQLConfig(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
    username=os.getenv('POSTGRES_USER', 'dict_user'),
    password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
)

migrator = CorpusMigrator(config)
stats = migrator.get_corpus_stats()

print("Corpus Statistics Fixed!")
print(f"Total Records: {stats['total_records']:,}")
print(f"Avg Source Length: {stats['avg_source_length']:.2f}")
print(f"Avg Target Length: {stats['avg_target_length']:.2f}")

assert stats['total_records'] > 70_000_000
print("✅ All assertions passed!")
