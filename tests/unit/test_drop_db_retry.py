"""
Tests for the _drop_db_with_retry and _kill_blocking_sessions helpers.

These tests run BEFORE the refactoring to ensure the extracted helpers
behave identically to the inline retry logic they replace.
"""

from __future__ import annotations

import logging
from unittest.mock import Mock, call, patch

import pytest

from app.services.dictionary_service import (
    _drop_db_with_retry,
    _kill_blocking_sessions,
)


# ---------------------------------------------------------------------------
# _kill_blocking_sessions tests
# ---------------------------------------------------------------------------


class TestKillBlockingSessions:
    """Test session-parsing and KILL logic."""

    def test_kills_single_user(self):
        """Parse a single-session output and KILL that user."""
        connector = Mock()
        connector.execute_command.return_value = (
            "- admin [127.0.0.1:48156]"
        )

        _kill_blocking_sessions(connector)

        connector.execute_command.assert_any_call("KILL admin")
        assert connector.execute_command.call_count == 2  # SHOW SESSIONS + KILL

    def test_kills_multiple_users(self):
        """Parse multi-line output and KILL each user."""
        connector = Mock()
        connector.execute_command.return_value = (
            "- admin [127.0.0.1:48156]\n"
            "- reader [127.0.0.1:48200]"
        )

        _kill_blocking_sessions(connector)

        assert connector.execute_command.call_count == 3  # SHOW + 2x KILL
        connector.execute_command.assert_any_call("KILL admin")
        connector.execute_command.assert_any_call("KILL reader")

    def test_skips_header_lines(self):
        """Lines like 'username' or 'session' are skipped."""
        connector = Mock()
        connector.execute_command.return_value = (
            "username\n"
            "- admin [127.0.0.1:48156]"
        )

        _kill_blocking_sessions(connector)

        connector.execute_command.assert_any_call("KILL admin")
        # SHOW SESSIONS + 1 KILL (username skipped)
        assert connector.execute_command.call_count == 2

    def test_swallows_show_sessions_failure(self):
        """If SHOW SESSIONS itself fails, no KILL is attempted."""
        connector = Mock()
        connector.execute_command.side_effect = Exception("connection lost")

        # Should not raise
        _kill_blocking_sessions(connector)

        # Only SHOW SESSIONS was attempted, no KILL
        connector.execute_command.assert_called_once_with("SHOW SESSIONS")

    def test_swallows_individual_kill_failure(self):
        """If one KILL fails, remaining users are still attempted."""
        connector = Mock()
        connector.execute_command.side_effect = [
            "- admin [127.0.0.1:48156]\n- reader [127.0.0.1:48200]",
            Exception("kill failed"),
            None,  # second KILL succeeds
        ]

        _kill_blocking_sessions(connector)

        assert connector.execute_command.call_count == 3
        connector.execute_command.assert_any_call("KILL admin")
        connector.execute_command.assert_any_call("KILL reader")

    def test_empty_sessions_output(self):
        """Empty string from SHOW SESSIONS — no KILLs."""
        connector = Mock()
        connector.execute_command.return_value = ""

        _kill_blocking_sessions(connector)

        connector.execute_command.assert_called_once_with("SHOW SESSIONS")


# ---------------------------------------------------------------------------
# _drop_db_with_retry tests
# ---------------------------------------------------------------------------


class TestDropDbWithRetry:
    """Test the retry-with-kill loop."""

    def test_drops_on_first_attempt(self):
        """Happy path: DROP succeeds immediately."""
        connector = Mock()
        connector.execute_command.return_value = None  # DROP succeeds

        _drop_db_with_retry(connector, "testdb", max_retries=5)

        connector.execute_command.assert_called_once_with("DROP DB testdb")

    def test_retries_on_opened_by_another_process(self):
        """Retry when 'opened by another process' is in the error."""
        connector = Mock()
        connector.execute_command.side_effect = [
            Exception("DB testdb opened by another process"),  # first DROP fails
            "- admin [127.0.0.1:48156]",                     # SHOW SESSIONS
            None,                                              # KILL admin
            None,                                              # second DROP succeeds
        ]

        with patch("app.services.dictionary_service.time") as mock_time:
            _drop_db_with_retry(connector, "testdb", max_retries=5, sleep_seconds=1.0)

        # SHOW SESSIONS + KILL + second DROP
        assert connector.execute_command.call_count == 4
        connector.execute_command.assert_any_call("SHOW SESSIONS")
        mock_time.sleep.assert_called_once_with(1.0)

    def test_raises_on_non_matching_error(self):
        """Non-matching errors propagate immediately (no retry)."""
        connector = Mock()
        connector.execute_command.side_effect = Exception("some other error")

        with pytest.raises(Exception, match="some other error"):
            _drop_db_with_retry(connector, "testdb", max_retries=5)

        connector.execute_command.assert_called_once_with("DROP DB testdb")

    def test_raises_after_max_retries_exhausted(self):
        """After max_retries failures, the last exception is raised."""
        connector = Mock()
        connector.execute_command.side_effect = Exception(
            "DB testdb opened by another process"
        )

        with patch("app.services.dictionary_service.time"):
            with pytest.raises(Exception, match="opened by another process"):
                _drop_db_with_retry(connector, "testdb", max_retries=3, sleep_seconds=1.0)

        # 3 DROP attempts + 2 SHOW SESSIONS (no kill on last attempt)
        drop_calls = [
            c for c in connector.execute_command.call_args_list
            if c == call("DROP DB testdb")
        ]
        assert len(drop_calls) == 3

    def test_exponential_backoff(self):
        """With backoff=True, sleep times double each retry."""
        connector = Mock()
        connector.execute_command.side_effect = [
            Exception("DB opened by another process"),  # DROP 1
            "- admin [127.0.0.1:1234]",                 # SHOW SESSIONS
            None,                                        # KILL admin
            Exception("DB opened by another process"),  # DROP 2
            "- admin [127.0.0.1:1234]",                 # SHOW SESSIONS
            None,                                        # KILL admin
            None,                                        # DROP 3 succeeds
        ]

        with patch("app.services.dictionary_service.time") as mock_time:
            _drop_db_with_retry(
                connector, "testdb", max_retries=5, sleep_seconds=1.0, backoff=True
            )

        sleep_calls = [c.args[0] for c in mock_time.sleep.call_args_list]
        assert sleep_calls == [1.0, 2.0]

    def test_fixed_sleep(self):
        """With backoff=False, sleep time is constant."""
        connector = Mock()
        connector.execute_command.side_effect = [
            Exception("DB opened by another process"),  # DROP 1
            "- admin [127.0.0.1:1234]",                 # SHOW SESSIONS
            None,                                        # KILL admin
            Exception("DB opened by another process"),  # DROP 2
            "- admin [127.0.0.1:1234]",                 # SHOW SESSIONS
            None,                                        # KILL admin
            None,                                        # DROP 3 succeeds
        ]

        with patch("app.services.dictionary_service.time") as mock_time:
            _drop_db_with_retry(
                connector, "testdb", max_retries=5, sleep_seconds=1.0, backoff=False
            )

        sleep_calls = [c.args[0] for c in mock_time.sleep.call_args_list]
        assert sleep_calls == [1.0, 1.0]

    def test_kill_sessions_called_before_each_sleep(self):
        """SHOW SESSIONS + KILL happen before every sleep."""
        connector = Mock()
        connector.execute_command.side_effect = [
            Exception("DB opened by another process"),  # DROP 1
            "- admin [127.0.0.1:1234]",                 # SHOW SESSIONS
            None,                                        # KILL admin
            Exception("DB opened by another process"),  # DROP 2
            "- reader [127.0.0.1:5678]",                # SHOW SESSIONS
            None,                                        # KILL reader
            None,                                        # DROP 3 succeeds
        ]

        with patch("app.services.dictionary_service.time"):
            _drop_db_with_retry(
                connector, "testdb", max_retries=5, sleep_seconds=1.0
            )

        calls = [c.args[0] for c in connector.execute_command.call_args_list]
        # Verify ordering: SHOW SESSIONS always before KILL
        show_indices = [i for i, c in enumerate(calls) if c == "SHOW SESSIONS"]
        kill_indices = [i for i, c in enumerate(calls) if c.startswith("KILL")]
        for si, ki in zip(show_indices, kill_indices):
            assert si < ki

    def test_logs_warning_on_retry(self):
        """Warning is logged on each retryable failure."""
        connector = Mock()
        connector.execute_command.side_effect = [
            Exception("DB testdb opened by another process"),  # DROP 1
            "- admin [127.0.0.1:1234]",                       # SHOW SESSIONS
            None,                                              # KILL admin
            None,                                              # DROP 2 succeeds
        ]

        with patch("app.services.dictionary_service.time"):
            with patch("app.services.dictionary_service.logger") as mock_logger:
                _drop_db_with_retry(
                    connector, "testdb", max_retries=5, sleep_seconds=1.0
                )

        warning_calls = [
            c for c in mock_logger.warning.call_args_list
            if "killing sessions" in str(c)
        ]
        assert len(warning_calls) >= 1
