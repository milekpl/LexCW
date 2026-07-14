"""Account bootstrap commands.

An instance that requires authentication needs a way to create the first account,
and a way back in when the only admin password is lost. Without these the recovery
path is editing the database by hand — which is exactly where this project ended
up: the sole admin account carried a placeholder email (`admin@example.com`), so
password reset by email was structurally impossible, and login had to be restored
from a shell.

    flask create-admin --username milek --email me@example.com
    flask reset-password --username milek
    flask list-users
"""

from __future__ import annotations

import click
from flask import Flask
from flask.cli import with_appcontext


def _get_user(username: str):
    from app.models.project_settings import User

    return User.query.filter_by(username=username).first()


@click.command("create-admin")
@click.option("--username", prompt=True, help="Login name for the new admin.")
@click.option("--email", prompt=True, help="Contact address (used for password reset).")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password. Prompted for (hidden) if omitted.",
)
@with_appcontext
def create_admin_command(username: str, email: str, password: str) -> None:
    """Create an administrator account."""
    from app.models.project_settings import User
    from app.models.workset_models import db
    from app.services.auth_service import AuthenticationService

    if _get_user(username) is not None:
        raise click.ClickException(
            f"User {username!r} already exists. Use `flask reset-password` to change "
            "its password."
        )

    user = User(
        username=username,
        email=email,
        password_hash=AuthenticationService.hash_password(password),
        is_active=True,
        is_admin=True,
    )
    db.session.add(user)
    db.session.commit()

    click.echo(f"Created admin {username!r} <{email}>.")


@click.command("reset-password")
@click.option("--username", prompt=True, help="Account to reset.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="New password. Prompted for (hidden) if omitted.",
)
@with_appcontext
def reset_password_command(username: str, password: str) -> None:
    """Set a new password for an existing account (the way back in)."""
    from app.models.workset_models import db
    from app.services.auth_service import AuthenticationService

    user = _get_user(username)
    if user is None:
        raise click.ClickException(f"No such user: {username!r}")

    user.password_hash = AuthenticationService.hash_password(password)
    user.is_active = True
    db.session.commit()

    click.echo(f"Password reset for {username!r}.")


@click.command("list-users")
@with_appcontext
def list_users_command() -> None:
    """List accounts, so you can see who can actually get in."""
    from app.models.project_settings import User

    users = User.query.order_by(User.id).all()
    if not users:
        click.echo("No users. Create one with `flask create-admin`.")
        return

    for user in users:
        role = "admin" if user.is_admin else "user"
        state = "active" if user.is_active else "disabled"
        click.echo(f"{user.id:>4}  {user.username:<20} {user.email:<32} {role:<6} {state}")


def register_cli(app: Flask) -> None:
    app.cli.add_command(create_admin_command)
    app.cli.add_command(reset_password_command)
    app.cli.add_command(list_users_command)
