"""
Additional fixtures for integration tests.
"""

from __future__ import annotations

import pytest
from flask import Flask

@pytest.fixture(scope="function", autouse=True)
def cleanup_display_profiles_db(app: Flask):
    """Clean up display profiles from database before each test.

    This fixture is autouse - it will run before each test.
    """
    with app.app_context():
        from app.models.display_profile import DisplayProfile, ProfileElement
        from app.models.workset_models import db

        # Clear all elements first (foreign key dependencies)
        try:
            ProfileElement.query.delete()
            db.session.commit()

            # Clear all profiles
            DisplayProfile.query.delete()
            db.session.commit()
        except Exception:
            # If tables don't exist or app doesn't have proper DB, skip cleanup
            pass

        yield

        # Clean up after test
        try:
            ProfileElement.query.delete()
            db.session.commit()

            DisplayProfile.query.delete()
            db.session.commit()
        except Exception:
            pass
