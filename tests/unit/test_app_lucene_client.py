"""
Unit tests for Flask app initialization with Lucene corpus client.
"""
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


class TestAppLuceneClient:
    """Tests for Lucene corpus client in Flask app."""

    def test_lucene_client_added_to_app(self):
        """Test that Lucene corpus client is added to Flask app."""
        with patch('app.services.lucene_corpus_client.requests.Session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get.return_value = MagicMock(
                json=MagicMock(return_value={"status": "ok"}),
                raise_for_status=MagicMock()
            )

            from app import create_app

            app = create_app('testing')

            assert hasattr(app, 'lucene_corpus_client')
            assert app.lucene_corpus_client is not None

    def test_lucene_client_uses_config_url(self):
        """Test that Lucene client uses URL from app config."""
        import os

        # Save original env var
        original_url = os.environ.get('LUCENE_CORPUS_URL')

        try:
            # Set a test URL
            os.environ['LUCENE_CORPUS_URL'] = 'http://test-server:8082'

            with patch('app.services.lucene_corpus_client.requests.Session') as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.get.return_value = MagicMock(
                    json=MagicMock(return_value={"status": "ok"}),
                    raise_for_status=MagicMock()
                )

                from app import create_app
                import importlib
                import config
                # Reload config to pick up the new env var
                importlib.reload(config)

                app = create_app('testing')

                # The client should use the configured URL
                assert app.lucene_corpus_client.base_url == 'http://test-server:8082'
        finally:
            # Restore original env var
            if original_url is not None:
                os.environ['LUCENE_CORPUS_URL'] = original_url
            elif 'LUCENE_CORPUS_URL' in os.environ:
                del os.environ['LUCENE_CORPUS_URL']

    def test_lucene_client_uses_default_when_no_config(self):
        """Test that Lucene client uses default URL when no config set."""
        # This test verifies the client has a valid URL
        from app.services.lucene_corpus_client import LuceneCorpusClient

        client = LuceneCorpusClient()
        assert client.base_url == 'http://localhost:8082'
