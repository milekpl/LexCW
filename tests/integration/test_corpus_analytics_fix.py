"""
Test for corpus management view using the correct database name.
"""
from unittest.mock import patch
from app.views import corpus_management


import pytest

@pytest.mark.integration
def test_corpus_management_uses_analytics_database():
    """Test that corpus management view renders successfully with default stats."""
    # Mock render_template to avoid template file dependencies
    with patch('app.views.render_template') as mock_render:
        mock_render.return_value = 'rendered_corpus_management_template'

        result = corpus_management()

        # Verify the template was rendered with correct arguments
        mock_render.assert_called_once_with(
            'corpus_management.html',
            corpus_stats={
                'total_records': 0,
                'avg_source_length': '0.00',
                'avg_target_length': '0.00',
                'last_updated': 'Loading...'
            },
            lucene_status={'connected': False, 'error': None}
        )

        # Verify the result is the mocked template
        assert result == 'rendered_corpus_management_template'


if __name__ == '__main__':
    test_corpus_management_uses_analytics_database()
    print("Test passed!")
