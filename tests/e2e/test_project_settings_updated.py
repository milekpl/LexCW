from __future__ import annotations

from typing import Any


def test_project_settings_basex_db_updated(configured_flask_app: Any, test_database: str) -> None:
    """Verify that the autouse fixture `ensure_project_settings` sets/upates
    ProjectSettings.basex_db_name to the current `test_database` for each test.
    """
    app, _ = configured_flask_app

    with app.app_context():
        from app.models.project_settings import ProjectSettings

        settings = ProjectSettings.query.first()
        assert settings is not None, "ProjectSettings should exist after fixture"
        assert settings.basex_db_name == test_database, (
            f"Expected ProjectSettings.basex_db_name to be '{test_database}', got '{settings.basex_db_name}'"
        )
