"""Account bootstrap commands: the way in, and the way back in.

These exist because this project lost its way in. The sole admin account had a
placeholder email, so reset-by-email could never work, and login had to be restored
by hand from a shell. Under REQUIRE_AUTH that is a locked-out instance.

Runs against TestingConfig (in-memory SQLite), so no real account is touched.
"""

from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture
def app():
    application = create_app("testing")
    # No auto-seeded user: these tests are about bootstrapping accounts from nothing,
    # and one of them asserts a brand-new instance reports having no users at all.
    application._tests_anonymous = True
    return application


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def _login_works(app, username: str, password: str) -> bool:
    from app.services.auth_service import AuthenticationService

    with app.app_context():
        user, _error = AuthenticationService.authenticate_user(username, password)
        return user is not None


def test_create_admin_creates_a_usable_account(app, runner):
    """The account must actually be able to log in — not merely exist."""
    result = runner.invoke(
        args=[
            "create-admin",
            "--username", "boot",
            "--email", "boot@example.test",
            "--password", "s3cret-pw",
        ]
    )

    assert result.exit_code == 0, result.output
    assert "Created admin" in result.output
    assert _login_works(app, "boot", "s3cret-pw"), "created admin cannot log in"


def test_create_admin_is_an_admin(app, runner):
    runner.invoke(
        args=["create-admin", "--username", "boot", "--email", "b@example.test",
              "--password", "pw"]
    )

    with app.app_context():
        from app.models.project_settings import User

        user = User.query.filter_by(username="boot").first()
        assert user.is_admin is True
        assert user.is_active is True


def test_create_admin_refuses_to_clobber_an_existing_user(app, runner):
    args = ["create-admin", "--username", "boot", "--email", "b@example.test",
            "--password", "pw"]
    runner.invoke(args=args)

    result = runner.invoke(args=args)

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_reset_password_restores_access(app, runner):
    """The scenario that actually happened: the admin password is gone."""
    runner.invoke(
        args=["create-admin", "--username", "boot", "--email", "b@example.test",
              "--password", "forgotten"]
    )

    result = runner.invoke(
        args=["reset-password", "--username", "boot", "--password", "new-pw"]
    )

    assert result.exit_code == 0, result.output
    assert _login_works(app, "boot", "new-pw"), "reset password does not work"
    assert not _login_works(app, "boot", "forgotten"), "old password still works"


def test_reset_password_reactivates_a_disabled_account(app, runner):
    runner.invoke(
        args=["create-admin", "--username", "boot", "--email", "b@example.test",
              "--password", "pw"]
    )
    with app.app_context():
        from app.models.project_settings import User
        from app.models.workset_models import db

        User.query.filter_by(username="boot").first().is_active = False
        db.session.commit()

    runner.invoke(args=["reset-password", "--username", "boot", "--password", "pw2"])

    assert _login_works(app, "boot", "pw2")


def test_reset_password_on_unknown_user_fails_clearly(app, runner):
    result = runner.invoke(
        args=["reset-password", "--username", "nobody", "--password", "pw"]
    )

    assert result.exit_code != 0
    assert "No such user" in result.output


def test_list_users_reports_an_empty_instance(app, runner):
    result = runner.invoke(args=["list-users"])

    assert result.exit_code == 0
    assert "No users" in result.output
