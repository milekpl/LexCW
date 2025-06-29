"""
Test for corpus management view using the correct database name.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.views import corpus_management
from app.database.postgresql_connector import PostgreSQLConfig


def test_corpus_management_uses_analytics_database():
    """Test that corpus management uses the analytics database for corpus stats."""
    with patch('app.views.CorpusMigrator') as mock_migrator_class, \
         patch('app.views.PostgreSQLConfig') as mock_config_class, \
         patch('app.views.os.getenv') as mock_getenv:
        
        # Mock environment variables to return analytics database
        def mock_env_side_effect(key, default):
            env_vars = {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_PORT': '5432',
                'POSTGRES_DB': 'dictionary_analytics',  # This should be analytics, not test
                'POSTGRES_USER': 'dict_user',
                'POSTGRES_PASSWORD': 'dict_pass'
            }
            return env_vars.get(key, default)
        
        mock_getenv.side_effect = mock_env_side_effect
        
        # Mock PostgreSQL config
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        # Mock migrator
        mock_migrator = MagicMock()
        mock_migrator_class.return_value = mock_migrator
        mock_migrator.get_corpus_stats.return_value = {
            'total_records': 74723856,
            'avg_source_length': 67.23,
            'avg_target_length': 68.58,
            'last_record': None
        }
        
        # Mock render_template
        with patch('app.views.render_template') as mock_render:
            mock_render.return_value = 'rendered_template'
            
            result = corpus_management()
            
            # Verify PostgreSQLConfig was called with analytics database
            mock_config_class.assert_called_once_with(
                host='localhost',
                port=5432,
                database='dictionary_analytics',  # Should use analytics database
                username='dict_user',
                password='dict_pass'
            )
            
            # Verify the template was rendered with correct stats
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            assert args[0] == 'corpus_management.html'
            
            corpus_stats = kwargs['corpus_stats']
            postgres_status = kwargs['postgres_status']
            
            assert corpus_stats['total_records'] == 74723856
            assert postgres_status['connected'] is True
            assert postgres_status['error'] is None


if __name__ == '__main__':
    test_corpus_management_uses_analytics_database()
    print("Test passed!")
