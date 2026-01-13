from __future__ import annotations

import pytest
from flask import current_app


class _FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def execute(self, *_, **__):
        return None

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def cursor(self):
        return _FakeCursor()

    def commit(self):
        return None


class _FakePool:
    def __init__(self, maxconn=5):
        self._max = maxconn
        self._in_use = 0

    def getconn(self):
        if self._in_use >= self._max:
            raise RuntimeError('connection pool exhausted')
        self._in_use += 1
        return _FakeConn()

    def putconn(self, conn):
        # In our fake pool, we just decrement counter
        self._in_use = max(0, self._in_use - 1)


def test_pg_pool_returns_connections_after_repeated_calls(app) -> None:
    """Call list_worksets repeatedly to ensure connections are returned to the pool
    and we don't exhaust available connections. Uses a fake pool to simulate exhaustion.
    """
    from app.services.workset_service import WorksetService

    with app.app_context():
        current_app.pg_pool = _FakePool(maxconn=5)
        svc = WorksetService()

        # Call list_worksets many times; if connections are not returned, we'll hit exhaustion
        for i in range(40):
            try:
                res = svc.list_worksets()
                assert isinstance(res, list)
            except Exception as e:
                pytest.fail(f"list_worksets failed on iteration {i}: {e}")
