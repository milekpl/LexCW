"""
Tests for the IOError/OSError retry logic in BaseXConnector.

Covers execute_command and execute_update retry behavior:
- Success on first attempt (no retry)
- IOError triggers retry, succeeds on 2nd attempt
- All attempts exhausted → DatabaseError
- Non-IOError exception → immediate DatabaseError (no retry)
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

from app.database.basex_connector import BaseXConnector
from app.utils.exceptions import DatabaseError


def _make_connector():
    """Create a BaseXConnector with mocked pool internals."""
    with patch.object(BaseXConnector, '_make_connection'):
        conn = BaseXConnector('localhost', 1984, 'admin', 'admin', 'testdb')
    conn._acquire = MagicMock()
    conn._release = MagicMock()
    conn._discard = MagicMock()
    conn.logger = MagicMock()
    return conn


def _mock_conn(session_execute_return="OK"):
    """Create a mock connection whose session.execute returns a value."""
    conn = MagicMock()
    conn.current_db = "testdb"
    conn.session.execute.return_value = session_execute_return
    return conn


def _mock_conn_query(execute_return="OK"):
    """Create a mock connection for query-based execution."""
    conn = MagicMock()
    conn.current_db = "testdb"
    query_obj = MagicMock()
    query_obj.execute.return_value = execute_return
    conn.session.query.return_value = query_obj
    return conn


# ======================================================================
# execute_command tests
# ======================================================================


class TestExecuteCommandRetry:
    def test_success_first_try(self):
        conn = _mock_conn("result")
        c = _make_connector()
        c._acquire.return_value = conn

        result = c.execute_command("LIST")

        assert result == "result"
        c._release.assert_called_once_with(conn)
        c._discard.assert_not_called()

    def test_retry_on_ioerror_succeeds_second(self):
        conn_fail = _mock_conn()
        conn_fail.session.execute.side_effect = IOError("broken pipe")
        conn_ok = _mock_conn("recovered")

        c = _make_connector()
        c._acquire.side_effect = [conn_fail, conn_ok]

        result = c.execute_command("LIST")

        assert result == "recovered"
        c._discard.assert_called_once_with(conn_fail)
        # Second conn should be released
        assert c._release.call_args[0][0] is conn_ok

    def test_all_attempts_fail_raises_database_error(self):
        conn1 = _mock_conn()
        conn1.session.execute.side_effect = IOError("pipe broken")
        conn2 = _mock_conn()
        conn2.session.execute.side_effect = IOError("pipe broken")
        conn3 = _mock_conn()
        conn3.session.execute.side_effect = IOError("pipe broken")

        c = _make_connector()
        c._acquire.side_effect = [conn1, conn2, conn3]

        with pytest.raises(DatabaseError, match="command failed after 3 attempts"):
            c.execute_command("LIST")

        assert c._discard.call_count == 3

    def test_non_ioerror_raises_immediately_no_retry(self):
        conn = _mock_conn()
        conn.session.execute.side_effect = ValueError("bad command")

        c = _make_connector()
        c._acquire.return_value = conn

        with pytest.raises(DatabaseError, match="Command execution failed"):
            c.execute_command("INVALID")

        c._discard.assert_not_called()
        c._release.assert_called_once_with(conn)


# ======================================================================
# execute_update tests
# ======================================================================


class TestExecuteUpdateRetry:
    def test_success_first_try(self):
        conn = _mock_conn_query("done")
        c = _make_connector()
        c._acquire.return_value = conn

        c.execute_update("xquery insert node <t>data</t>")

        c._release.assert_called_once_with(conn)
        c._discard.assert_not_called()

    def test_retry_on_ioerror_succeeds_second(self):
        conn_fail = _mock_conn_query()
        conn_fail.session.query.return_value.execute.side_effect = IOError("connection reset")
        conn_ok = _mock_conn_query("done")

        c = _make_connector()
        c._acquire.side_effect = [conn_fail, conn_ok]

        c.execute_update("xquery insert node <t>data</t>")

        c._discard.assert_called_once_with(conn_fail)
        assert c._release.call_args[0][0] is conn_ok

    def test_all_attempts_fail_raises_database_error(self):
        conns = []
        for _ in range(3):
            conn = _mock_conn_query()
            conn.session.query.return_value.execute.side_effect = IOError("broken")
            conns.append(conn)

        c = _make_connector()
        c._acquire.side_effect = conns

        with pytest.raises(DatabaseError, match="failed after 3 attempts"):
            c.execute_update("xquery insert node <t>data</t>")

        assert c._discard.call_count == 3

    def test_non_ioerror_raises_immediately_no_retry(self):
        conn = _mock_conn_query()
        conn.session.query.return_value.execute.side_effect = RuntimeError("unexpected")

        c = _make_connector()
        c._acquire.return_value = conn

        with pytest.raises(DatabaseError, match="Update execution failed"):
            c.execute_update("xquery bad query")

        c._discard.assert_not_called()

    def test_query_closed_on_success(self):
        conn = _mock_conn_query("done")
        c = _make_connector()
        c._acquire.return_value = conn

        c.execute_update("xquery insert node <t>data</t>")

        conn.session.query.return_value.close.assert_called_once()
