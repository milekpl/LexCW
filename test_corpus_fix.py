#!/usr/bin/env python3
"""
Test the corpus management view directly to see if it works now.
"""
import os
from app.database.postgresql_connector import PostgreSQLConfig
from app.database.corpus_migrator import CorpusMigrator
from datetime import datetime

def test_corpus_management_fixed():
    """Test corpus management with the correct analytics database."""
    corpus_stats = {}
    postgres_status = {'connected': False, 'error': None}
    
    try:
        # Create PostgreSQL config from environment (using same logic as views.py after fix)
        config = PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),  # Use analytics database
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
        )
        
        print(f'Connecting to: {config.database}')
        
        migrator = CorpusMigrator(config)
        
        # Test connection by attempting to get stats
        try:
            stats = migrator.get_corpus_stats()
            postgres_status['connected'] = True
            
            # Format stats for template (same logic as views.py)
            corpus_stats['total_records'] = stats.get('total_records', 0)
            
            avg_source_length = stats.get('avg_source_length')
            corpus_stats['avg_source_length'] = f"{avg_source_length:.2f}" if avg_source_length else "0.00"
            
            avg_target_length = stats.get('avg_target_length')
            corpus_stats['avg_target_length'] = f"{avg_target_length:.2f}" if avg_target_length else "0.00"

            last_record = stats.get('last_record')
            if isinstance(last_record, datetime):
                corpus_stats['last_updated'] = last_record.strftime('%Y-%m-%d %H:%M:%S')
            elif last_record:
                corpus_stats['last_updated'] = str(last_record)
            else:
                corpus_stats['last_updated'] = 'N/A'

            print('SUCCESS! Corpus stats retrieved:')
            print(f'  PostgreSQL Status: {"Connected" if postgres_status["connected"] else "Not Connected"}')
            print(f'  Total Records: {corpus_stats["total_records"]:,}')
            print(f'  Avg Source Length: {corpus_stats["avg_source_length"]}')
            print(f'  Avg Target Length: {corpus_stats["avg_target_length"]}')
            print(f'  Last Updated: {corpus_stats["last_updated"]}')
            print(f'  Error: {postgres_status.get("error", "None")}')

        except Exception as e:
            print(f"Could not fetch corpus statistics: {e}")
            postgres_status['connected'] = False
            postgres_status['error'] = f"Could not fetch stats: {e}"
            
    except Exception as e:
        print(f"PostgreSQL connection error: {e}")
        postgres_status['error'] = str(e)
    
    return corpus_stats, postgres_status

if __name__ == '__main__':
    test_corpus_management_fixed()
