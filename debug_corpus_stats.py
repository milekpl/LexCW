#!/usr/bin/env python3

"""Debug script to check actual corpus stats vs cached values."""

import os
import json
from app.database.postgresql_connector import PostgreSQLConfig
from app.database.corpus_migrator import CorpusMigrator
from app.services.cache_service import CacheService

def main():
    """Check corpus stats and cache status."""
    print("=== Debugging Corpus Stats ===")
    
    # Check cache
    cache = CacheService()
    if cache.is_available():
        cached_stats = cache.get('corpus_stats')
        if cached_stats:
            print(f"Cached stats found: {cached_stats}")
            try:
                parsed = json.loads(cached_stats)
                print(f"Parsed cached stats: {parsed}")
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in cache: {e}")
        else:
            print("No cached stats found")
    else:
        print("Cache not available")
    
    # Get actual stats
    print("\n=== Getting Fresh Stats ===")
    try:
        config = PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
        )
        
        migrator = CorpusMigrator(config)
        stats = migrator.get_corpus_stats()
        print(f"Fresh stats: {stats}")
        
        # Check what database we're actually connected to
        import psycopg2
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.username,
            password=config.password
        )
        cursor = conn.cursor()
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        print(f"Connected to database: {current_db}")
        
        cursor.execute("SELECT COUNT(*) FROM parallel_corpus;")
        count = cursor.fetchone()[0]
        print(f"Direct count from parallel_corpus: {count:,}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error getting fresh stats: {e}")
    
    # Clear cache
    print("\n=== Clearing Cache ===")
    if cache.is_available():
        cache.delete('corpus_stats')
        print("Cache cleared")

if __name__ == '__main__':
    main()
