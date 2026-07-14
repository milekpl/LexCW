"""The authentication gate: everything requires identity unless it is on the allowlist.

Enforced in one `before_request` hook rather than by decorating 441 routes. That is
not a shortcut — it is the only version that can be reviewed. A decorator has to be
remembered on every new route, and the one you forget is a silent hole; this list
is the whole security boundary, and it **fails closed**: a route that is not on it
requires identity from the day it is written, without anyone deciding anything.

Two things the gate does *not* do:

* **Scopes.** The gate answers "who are you". A route's own `@require_auth(scope)`
  answers "may you do this". Keeping them apart is what lets the allowlist stay a
  single readable list.
* **Admin.** `@admin_required` still guards management routes.

API keys are accepted **only** on routes that explicitly opted in with
`@require_auth`. Every other route is session-only, so a leaked key cannot wander
into endpoints nobody meant to expose to machines (auth matrix, rule 1).

The allowlist is derived from specs/auth_overhaul/auth_matrix.md; each entry is
justified there.
"""

from __future__ import annotations

from flask import Flask, request

# Imported as a module, not as bare names: binding `get_current_user` at import time
# would freeze the reference, so anything that patches the function (tests, and any
# future swap of the identity source) would be ignored by the gate while the
# decorators honoured it — the two would disagree about who you are.
from app.utils import auth_decorators


#: Reachable with no identity at all. Nothing else is.
PUBLIC_ENDPOINTS: frozenset[str] = frozenset(
    {
        "static",
        # Liveness/readiness probes run before any credential exists. Returns
        # {"status": "ok"} and nothing else. NB: `settings.health_check` and
        # `validation_api.health_check` are different endpoints and are NOT public.
        "health_check",
        # The credential-granting endpoints themselves.
        "auth.login",
        "auth_api.login",
        # Recovery has to work precisely when you cannot log in. Authorization is
        # the single-use token (reset_token_used).
        "auth.forgot_password",
        "auth.reset_password_with_token",
        "auth_api.reset_password",
        "auth_api.complete_password_reset",
        # Answers "am I logged in?" — must be callable when the answer is "no".
        # Returns a boolean, never user data.
        "auth_api.check_auth",
    }
)

#: Public only when self-service registration is enabled (config ALLOW_REGISTRATION).
REGISTRATION_ENDPOINTS: frozenset[str] = frozenset({"auth.register", "auth_api.register"})


def public_endpoints(app: Flask) -> frozenset[str]:
    """The effective allowlist for this app's configuration."""
    if app.config.get("ALLOW_REGISTRATION"):
        return PUBLIC_ENDPOINTS | REGISTRATION_ENDPOINTS
    return PUBLIC_ENDPOINTS


def init_auth_gate(app: Flask) -> None:
    """Install the gate. No-op unless REQUIRE_AUTH is set."""

    @app.before_request
    def _require_identity():
        if not app.config.get("REQUIRE_AUTH"):
            return None

        endpoint = request.endpoint
        if endpoint is None:
            return None  # Unrouted: let Flask answer 404/405.

        if endpoint in public_endpoints(app):
            return None

        if request.headers.get("Authorization", "").startswith("Bearer "):
            view = app.view_functions.get(endpoint)
            if not getattr(view, "_accepts_api_key", False):
                return auth_decorators.auth_error(
                    "API keys are not accepted on this endpoint",
                    403,
                    "api_key_not_permitted",
                )
            # The route's own @require_auth validates the key and its scope.
            return None

        if auth_decorators.get_current_user() is None:
            return auth_decorators.auth_error("Authentication required", 401, "authentication_required")

        return None
