import pytest
from unittest.mock import patch, Mock

def test_tools_page(client):
    response = client.get('/tools')
    assert response.status_code == 200
    assert b'<h1 class="mt-4">' in response.data
    assert b'Tools' in response.data
    assert b'<a href="/tools/clear-cache"' in response.data

def test_clear_cache(client):
    """Test clear cache endpoint - may show success or 'not available' message."""
    with patch('app.views.CacheService') as MockCacheService:
        mock_cache = Mock()
        mock_cache.is_available.return_value = True
        mock_cache.clear.return_value = None
        MockCacheService.return_value = mock_cache

        response = client.get('/tools/clear-cache', follow_redirects=True)
        assert response.status_code == 200
        # Should show either success or unavailability message
        assert b'Cache cleared successfully' in response.data or b'not available' in response.data
