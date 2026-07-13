"""Guard against drift between the SQLAlchemy models and the real database.

Schema drift has repeatedly shipped undetected and broken auth outright:

  * ``users`` lacked ``reset_token_used`` while the model declared it, so every
    ``User`` query raised ``UndefinedColumn`` and login was impossible.
  * ``api_keys.key_prefix`` was ``VARCHAR(8)`` while keys are 11 chars, so no
    API key could ever be created.

Both are trivially detectable by comparing mapped columns against the live
table definitions, which is what this module does.

Deliberately checks the **development** database rather than the test database:
the integration ``app`` fixture builds its schema with ``db.create_all()``
(tests/integration/conftest.py), i.e. straight from the models, so models and
tables match there by construction and a drift check would be vacuous. Drift
only exists in databases created once and migrated by hand — which is the one
the application actually runs against.

Read-only: reflects the schema, never writes.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest
from sqlalchemy import inspect

import app.models
from app import create_app
from app.models.workset_models import db


def _load_all_models() -> None:
    """Import every module in app.models so all mappers are registered.

    Walks the package rather than relying on ``app.models.__init__``, which does
    not import every model module (``ApiKey`` among them) — the coverage hole
    that let the api_keys drift through.
    """
    for module in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module.name}")


@pytest.fixture(scope="module")
def live_schema():
    """Yield (inspector, mapped_tables) for the database the app really uses."""
    _load_all_models()

    application = create_app("development")
    with application.app_context():
        try:
            inspector = inspect(db.engine)
            inspector.get_table_names()
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"development database not reachable: {exc}")

        mapped = {
            mapper.local_table.name: mapper.local_table
            for mapper in db.Model.registry.mappers
            if mapper.local_table is not None
        }
        assert mapped, "no SQLAlchemy models were registered"
        yield inspector, mapped


def _db_columns(inspector, table_name):
    return {col["name"]: col for col in inspector.get_columns(table_name)}


def test_every_mapped_table_exists(live_schema):
    """A model whose table is missing fails on first use."""
    inspector, mapped = live_schema
    existing = set(inspector.get_table_names())

    missing = sorted(name for name in mapped if name not in existing)
    assert not missing, f"models mapped to tables that do not exist: {missing}"


def test_no_columns_missing_from_database(live_schema):
    """Model declares a column the table lacks -> every SELECT raises UndefinedColumn.

    This is the `users.reset_token_used` bug that made login impossible.
    """
    inspector, mapped = live_schema
    existing = set(inspector.get_table_names())

    problems = []
    for table_name, table in mapped.items():
        if table_name not in existing:
            continue
        db_cols = _db_columns(inspector, table_name)
        for column in table.columns:
            if column.name not in db_cols:
                problems.append(f"{table_name}.{column.name}")

    assert not problems, (
        "columns declared on models but missing from the database "
        f"(queries on these tables will fail): {sorted(problems)}"
    )


def test_string_columns_are_wide_enough(live_schema):
    """A column narrower in the DB than in the model -> INSERT truncation errors.

    This is the `api_keys.key_prefix` VARCHAR(8)-vs-11-chars bug that made it
    impossible to issue an API key.
    """
    inspector, mapped = live_schema
    existing = set(inspector.get_table_names())

    problems = []
    for table_name, table in mapped.items():
        if table_name not in existing:
            continue
        db_cols = _db_columns(inspector, table_name)
        for column in table.columns:
            db_col = db_cols.get(column.name)
            if db_col is None:
                continue  # reported by test_no_columns_missing_from_database
            model_len = getattr(column.type, "length", None)
            db_len = getattr(db_col["type"], "length", None)
            if model_len is None or db_len is None:
                continue
            if db_len < model_len:
                problems.append(
                    f"{table_name}.{column.name}: model allows {model_len} chars, "
                    f"database column holds {db_len}"
                )

    assert not problems, f"columns too narrow in the database: {sorted(problems)}"


def test_no_unmapped_required_columns(live_schema):
    """A NOT NULL column the model doesn't know about -> every model INSERT fails.

    Extra *nullable* columns are fine: they are legacy leftovers (e.g.
    users.full_name, users.updated_at) and the ORM simply ignores them.
    """
    inspector, mapped = live_schema
    existing = set(inspector.get_table_names())

    problems = []
    for table_name, table in mapped.items():
        if table_name not in existing:
            continue
        model_cols = {column.name for column in table.columns}
        for name, db_col in _db_columns(inspector, table_name).items():
            if name in model_cols:
                continue
            if not db_col["nullable"] and db_col.get("default") is None:
                problems.append(f"{table_name}.{name}")

    assert not problems, (
        "NOT NULL columns without a default that no model maps "
        f"(inserts will fail): {sorted(problems)}"
    )
