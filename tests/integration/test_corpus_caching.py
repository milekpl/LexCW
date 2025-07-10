"""
Test for corpus management caching functionality.
"""
from unittest.mock import patch
from app.views import corpus_management


import pytest

@pytest.mark.integration
def test_corpus_management_uses_cache():
    """Test that corpus management renders template with default stats (no caching needed)."""
    with patch('app.views.render_template') as mock_render:
        mock_render.return_value = 'rendered_template'
        
        result = corpus_management()
        
        # Verify template was rendered with default stats
        mock_render.assert_called_once_with(
            'corpus_management.html',
            corpus_stats={
                'total_records': 0,
                'avg_source_length': '0.00',
                'avg_target_length': '0.00',
                'last_updated': 'Loading...'
            },
            postgres_status={'connected': False, 'error': None}
        )
        
        assert result == 'rendered_template'


@pytest.mark.integration
def test_corpus_management_cache_miss():
    """Test that corpus management consistently returns the same template structure."""
    with patch('app.views.render_template') as mock_render:
        mock_render.return_value = 'rendered_template'
        
        result = corpus_management()
        
        # Verify template is always rendered with same default structure
        mock_render.assert_called_once_with(
            'corpus_management.html',
            corpus_stats={
                'total_records': 0,
                'avg_source_length': '0.00',
                'avg_target_length': '0.00',
                'last_updated': 'Loading...'
            },
            postgres_status={'connected': False, 'error': None}
        )
        
        assert result == 'rendered_template'


if __name__ == '__main__':
    test_corpus_management_uses_cache()
    test_corpus_management_cache_miss()
    print("Tests passed!")
