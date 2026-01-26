import logging
from unittest.mock import patch, MagicMock
from app import create_app


def test_per_request_basex_logging(monkeypatch, caplog):
    """Test that BaseX status is logged at request start."""
    caplog.set_level(logging.DEBUG)
    app = create_app('testing')

    # Store original methods
    original_info = app.logger.info
    original_debug = app.logger.debug
    logged_messages = []

    def mock_info(msg, *args, **kwargs):
        logged_messages.append(('INFO', msg % args if args else msg))
        # Call original to preserve other handlers
        original_info(msg, *args, **kwargs)

    def mock_debug(msg, *args, **kwargs):
        logged_messages.append(('DEBUG', msg % args if args else msg))
        original_debug(msg, *args, **kwargs)

    # Replace methods
    app.logger.info = mock_info
    app.logger.debug = mock_debug

    try:
        with app.test_client() as client:
            client.get('/health')

        # Verify that a BaseX status log entry was emitted
        info_messages = [msg for level, msg in logged_messages if level == 'INFO']
        assert any('BaseX status at request start' in msg for msg in info_messages), \
            f"Expected 'BaseX status at request start' in log messages: {info_messages}"
    finally:
        # Restore original methods
        app.logger.info = original_info
        app.logger.debug = original_debug