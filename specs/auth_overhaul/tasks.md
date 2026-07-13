# Implementation Plan: Authentication Overhaul

This document outlines the implementation tasks for moving the application to a
**fully authenticated** posture (session auth for the UI, API keys for machine
callers), with the end-to-end test coverage that would have caught the class of
bugs described below.

## Background: why this exists

Authentication was never exercised end-to-end, and three independent latent
bugs had accumulated. They only surfaced when the first UI feature
(`POST /api/pronunciation/draft`, the ByT5 IPA draft button) actually depended
on auth:

1. **`users` table lacked `reset_token_used`.** The `User` model declared the
   column; the table never had it. Every `User` query raised `UndefinedColumn`,
   so `get_current_user()` could never succeed and **login was impossible** —
   which made all four `@_require_auth` pronunciation endpoints permanently
   unreachable from a browser.
2. **API keys could never be issued.** `ApiKey.key_prefix` was `VARCHAR(8)` but
   generated prefixes are 11 chars (`sw_` + 8), so every `POST /api/keys/` died
   with `StringDataRightTruncation`.
3. **API keys could never authenticate, even if issued.** `_generate_api_key()`
   hashed `raw`, but stored the prefix as `"sw_" + raw[:8]`, while
   `_check_api_key_auth()` requires the *raw key itself* to start with `sw_` and
   hashes-checks that same `sw_`-prefixed string. The hash covered a different
   string than the one clients present.

Compounding all three: the frontend reported any non-`available` response as a
*model* failure ("ByT5 model not available"), so a 401 was indistinguishable
from a missing ML model — the auth bug masqueraded as a machine-learning bug.

The existing `tests/unit/test_api_key_auth.py` passed throughout, because it
tests hashing and scope logic in isolation with hand-constructed prefixes: it
never calls `_generate_api_key()`, never inserts a row, and never issues an HTTP
request. **This is the coverage gap the plan closes.**

## Scale

- 456 routes across 47 blueprints (372 `/api/*`, 84 UI).
- 76 e2e files / 439 test functions, all currently running unauthenticated.

Two consequences drive the design:

- **Enforcement must be centralized.** Decorating 456 routes by hand is neither
  reviewable nor safe (a missed route is a silent hole). Use one global
  `before_request` gate with an explicit, audited allowlist — it fails *closed*:
  a new route is protected by default.
- **Test auth must be centralized too.** The `page` fixture
  (`tests/e2e/conftest.py:496`) is the single chokepoint through which nearly all
  439 tests obtain a browser. Authenticating there keeps the existing suite
  working without touching 76 files.

---

1.  [ ] **Foundations and safety nets**
    *   Land the guardrails first, so the rest of the rollout cannot silently regress.

    1.1. [x] **Repair the `users` schema**
        *   Add the missing `reset_token_used` column so session auth functions at all.
        *   Implemented: `migrations/add_reset_token_used_to_users.py`. Applied; `User.query` works and `/auth/login` returns 302 + a valid session.

    1.2. [x] **Repair the API key format**
        *   Make the `sw_` marker part of the raw key so the stored hash covers exactly the string clients send as `Authorization: Bearer <raw_key>`, and the prefix is a literal slice of it.
        *   Implemented: `app/api/api_keys.py::_generate_api_key`, `ApiKey.key_prefix` widened to `String(16)`, `migrations/widen_api_key_prefix.py`. Verified: create → 201; session-less Bearer call → 200; bogus key → 401; read-scoped key on a `:write` endpoint → rejected.

    1.3. [x] **Schema drift guard**
        *   Implemented: `tests/integration/test_schema_matches_models.py`. Four checks — mapped table exists; no model column missing from the DB (bug 1); no string column narrower in the DB than in the model (bug 2); no unmapped `NOT NULL` column without a default (which would break model inserts).
        *   Checks the **development** database on purpose: the integration `app` fixture builds its schema with `db.create_all()`, so models and tables match there by construction and the check would be vacuous. Drift only exists in the hand-migrated database the app actually runs against.
        *   Walks `app/models/` with `pkgutil` rather than trusting `app/models/__init__.py`, which does not import every model module — `ApiKey` is absent from it, so an `__init__`-based check would have missed bug 2 entirely.
        *   Verified by mutation, not just by passing: re-introducing the `VARCHAR(8)` prefix reproduced the exact failure, and a synthetic model-only column reproduced bug 1's failure.
        *   **Found a third instance of the same bug class**: `workset_entries.status` was `VARCHAR(20)` against a `String(50)` model. Latent (all current statuses fit), but the first longer status would have failed in production only. Fixed: `migrations/widen_workset_entry_status.py`.
        *   Audit result: with that fixed, all 25 models are clean against the live schema.

    1.4. [ ] **Admin bootstrap CLI**
        *   Add a `flask create-admin` / `flask reset-password` command so an unrecoverable admin account is never again a dead end.
        *   Motivation: the only admin account had a placeholder email (`admin@example.com`), so password recovery by email was structurally impossible; recovery required direct DB manipulation.

2.  [ ] **Auth contract**
    *   Make "who may call what, and what does failure look like" explicit and uniform before enforcing it everywhere.

    2.1. [ ] **Unify the two auth decorators**
        *   There are currently two mechanisms: `@login_required` (`app/utils/auth_decorators.py`, session-only, redirects HTML / 401 JSON) and `@_require_auth(scope)` (private to `app/api/pronunciation.py`, session **or** API key + scopes).
        *   Promote the API-key-capable decorator to a shared `app/utils/auth_decorators.py` export, so any endpoint can opt into machine access, and delete the private copy.

    2.2. [ ] **Fix the 401/403 conflation**
        *   `_check_api_key_auth()` returns `False` for a *scope* mismatch, so an authenticated key with insufficient scope gets **401 Authentication required** instead of **403 Forbidden** (verified). The `403` branch in `_require_auth` is currently unreachable for Bearer callers.
        *   Standardize a single JSON error contract (`{"error": ..., "code": ...}`) across auth failures, and make HTML vs JSON negotiation depend on `Accept`/path rather than ad-hoc checks.

    2.3. [x] **Stop the frontend misreporting auth failures as feature failures**
        *   Implemented: `app/static/js/alpine/pronunciation.js` now checks HTTP status first; 401/403 says "Not signed in", and "model not available" only fires on a genuine `available: false`.

    2.4. [ ] **Audit every other `fetch()` for the same bug**
        *   The draft button was not special — sweep `app/static/js/` for handlers that call `.json()` without checking `r.ok`, and give them a shared helper (`app/static/js/api-utils.js` already exists and is the natural home).
        *   Add a global 401 handler that redirects to `/auth/login?next=…` instead of showing a misleading domain-specific error.

    2.5. [ ] **Write the auth matrix**
        *   Enumerate the 47 blueprints and classify each: *public* (login, static, health), *session-only* (UI pages), *session-or-key* (machine-callable APIs, with required scopes).
        *   This document is the review artifact for task 3.1 — the allowlist must be justified line by line.

3.  [ ] **Full authentication rollout**
    *   Target posture: every route requires authentication unless explicitly allowlisted.

    3.1. [ ] **Central `before_request` gate**
        *   Enforce auth in one place in `app/__init__.py` against the matrix from 2.5, rather than decorating 456 routes.
        *   Fails closed: an unlisted new route is protected by default.
        *   Allowlist must contain only: `/auth/login`, `/auth/register` (if enabled), `/auth/forgot-password`, `/auth/reset-password/<token>`, static assets, and any health/readiness probe.
        *   Keep per-route decorators for *scope* requirements; the gate only establishes identity.

    3.2. [ ] **Preserve deep links**
        *   Unauthenticated HTML requests redirect to `/auth/login?next=<path>`; unauthenticated `/api/*` requests get the 2.2 JSON contract. No silent redirects for XHR.

    3.3. [ ] **Registration policy**
        *   Decide and enforce: open registration, invite-only, or admin-created accounts. `/auth/register` is currently live and unauthenticated — under "full auth everywhere" it is the one intentional public write endpoint and needs a deliberate decision plus rate limiting.

    3.4. [ ] **Roll out behind a config flag**
        *   `REQUIRE_AUTH` (default on in production, on in testing) so the gate can be landed and exercised before it becomes irreversible, and so the 439-test suite can be migrated in one controlled step (task 4.1).

4.  [ ] **Test coverage: the actual point of this overhaul**

    4.1. [ ] **Authenticate the e2e suite at the fixture chokepoint**
        *   Extend the `page` fixture (`tests/e2e/conftest.py:496`) to log in by default via Playwright `storage_state`, seeded once per session — so the existing 439 tests keep passing under `REQUIRE_AUTH` without editing 76 files.
        *   Provide an explicit `anonymous_page` fixture for tests that must assert the *unauthenticated* behavior (redirects, 401s).

    4.2. [ ] **Real login e2e (the flow no fixture may fake)**
        *   Drive the actual `/auth/login` form in the browser: success, wrong password, inactive user, logout, `next=` deep-link round-trip, and session expiry.
        *   This is the test whose absence let bug 1 (login broken by schema drift) sit undetected.
        *   Suggested: `tests/e2e/test_auth_login_e2e.py`.

    4.3. [ ] **API key integration tests over HTTP**
        *   Cover the full path that unit tests skip: `_generate_api_key()` → DB insert → `Authorization: Bearer` → protected endpoint.
        *   Cases: create → 201 and raw key returned exactly once; Bearer call from a session-less client → 200; revoked key → 401; bogus/malformed key → 401; scope mismatch → 403 (after 2.2); `last_used_at` updated.
        *   This is the test that would have caught bugs 2 and 3.
        *   Suggested: `tests/integration/test_api_key_flow.py`.

    4.4. [ ] **Keep the pronunciation/ByT5 endpoints as the worked example**
        *   e2e: the IPA draft button drafts an IPA when signed in, and reports *"not signed in"* — not *"model unavailable"* — when the session is gone (regression test for 2.3).
        *   Assert `available: false` only ever means a genuinely absent model.

5.  [ ] **Account lifecycle and hardening**

    5.1. [ ] **Password reset via existing SMTP settings**
        *   `/auth/forgot-password` and `/auth/reset-password/<token>` exist and were dead for the same reason as login (they are what `reset_token_used` was for). SMTP settings already exist in `ProjectSettings` (`migrations/add_smtp_settings_to_project_settings.py`).
        *   Wire them up, enforce single-use tokens via `reset_token_used`, expire via `reset_token_expires`, and cover with tests.

    5.2. [ ] **Session hardening**
        *   `config.py` sets no `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`, or `PERMANENT_SESSION_LIFETIME`. Set them per environment (`ProductionConfig` strictest).
        *   Confirm CSRF stays enabled outside tests — `WTF_CSRF_ENABLED = False` is correctly scoped to `TestingConfig` today; add a test asserting it is **not** disabled in `ProductionConfig`.

    5.3. [ ] **API key management UI**
        *   `/settings/api-keys` is routed and `/api/keys/*` CRUD exists and now works. Build/verify the UI: create with label + scopes, show the raw key exactly once, revoke, reactivate, show `last_used_at`.

    5.4. [ ] **Activity logging**
        *   `ActivityLog` is already written on login (`app/routes/auth_routes.py`). Extend to logout, failed login, password reset, and API key create/revoke; surface in the admin view.

---

## Suggested sequencing

Land **1.3** (schema drift guard) and **2.5** (auth matrix) first — they are cheap
and they de-risk everything after them. Then **2.1/2.2** (contract), then **4.1**
(fixture auth) *before* **3.1** (the gate), so that the moment the gate turns on,
the 439-test suite is already able to authenticate and will tell you what broke.
Enforcement (3.1) behind the `REQUIRE_AUTH` flag is the point of no return; do
not reach it without 4.1 in place.
