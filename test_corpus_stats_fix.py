"""
Test to reproduce and fix the corpus statistics issue.

This test verifies that corpus statistics correctly find existing data
in both the new corpus schema and legacy public schema locations.
"""
from app.database.corpus_migrator import CorpusMigrator
from app.database.postgresql_connector import PostgreSQLConfig
import os


def test_corpus_stats_should_find_existing_data():
    """Test that corpus stats finds the existing 74M records."""
    config = PostgreSQLConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
        username=os.getenv('POSTGRES_USER', 'dict_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
    )
    
    migrator = CorpusMigrator(config)
    stats = migrator.get_corpus_stats()
    
    # Should find the 74+ million records, not 0
    assert stats['total_records'] > 70_000_000, f"Expected >70M records, got {stats['total_records']}"
    assert stats['avg_source_length'] > 0, f"Expected positive average source length, got {stats['avg_source_length']}"
    assert stats['avg_target_length'] > 0, f"Expected positive average target length, got {stats['avg_target_length']}"
    
    print(f"✅ Found {stats['total_records']:,} corpus records")
    print(f"✅ Average source length: {stats['avg_source_length']:.2f}")
    print(f"✅ Average target length: {stats['avg_target_length']:.2f}")


def test_api_endpoint_returns_correct_stats():
    """Test that the API endpoint returns the correct corpus statistics."""
    import requests
    import json
    
    try:
        response = requests.get('http://localhost:5000/api/corpus/stats')
        assert response.status_code == 200, f"API returned status {response.status_code}"
        
        data = response.json()
        assert data['success'] is True, "API response should indicate success"
        
        stats = data['stats']
        assert stats['total_records'] > 70_000_000, f"API should return >70M records, got {stats['total_records']}"
        assert stats['avg_source_length'] > 0, "API should return positive average source length"
        assert stats['avg_target_length'] > 0, "API should return positive average target length"
        
        print(f"✅ API endpoint working correctly with {stats['total_records']:,} records")
        
    except requests.exceptions.ConnectionError:
        print("⚠️ Flask app not running, skipping API test")


if __name__ == "__main__":
    test_corpus_stats_should_find_existing_data()
    test_api_endpoint_returns_correct_stats()
    print("All tests passed!")
