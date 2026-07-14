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

    1.4. [x] **Admin bootstrap CLI**
        *   Implemented: `app/cli.py` — `flask create-admin`, `flask reset-password`, `flask list-users`. 7 tests in `tests/integration/test_cli_accounts.py`, which assert the created account can actually *log in*, not merely that a row exists.
        *   Motivation: the only admin account had a placeholder email (`admin@example.com`), so recovery by email was structurally impossible and login had to be restored by hand from a shell. Under `REQUIRE_AUTH` that is a locked-out instance.
        *   **Found a real bug while testing it.** `create-admin` failed with `no such table: project_roles` on a fresh database: `authenticate_user` writes an `ActivityLog` and reads project roles, but `app/models/__init__.py` does not import every model module — and a model that is never imported gets no table from `db.create_all()`. Fixed in `create_app()` by walking `app/models/` with `pkgutil` (the same fix the schema-drift guard needed, and the same root cause that hid `ApiKey`). Any fresh database now gets all of its tables.

    1.5. [ ] **Deferred: make the drift guard a CI gate**
        *   `tests/integration/test_schema_matches_models.py` reads the **development** database, so on any machine where that database is unreachable it `skips` rather than fails. Today that is fine — there is no CI/CD pipeline, and the guard runs against the database that actually matters.
        *   When CI/CD lands, this must be revisited or the guard becomes a silent no-op in the pipeline: point it at the deployed/staging schema (or a database built by replaying `migrations/`), and treat a `skip` as a failure there.
        *   Natural companion to the `REQUIRE_AUTH` rollout (3.4) — both need a real deployed environment to be meaningful.

    1.6. [x] **Close the two pre-rollout holes**
        *   `POST /api/setup` was unauthenticated and rewrote project settings (name, languages, ranges) — anyone reaching the app could reconfigure the project. Now `@admin_required`: anonymous → 401, non-admin → 403, Swagger unaffected.
        *   Removed 15 dead duplicate routes (456 → 441): the nested `validation_rules` registration publishing `/api/api/projects/...` (referenced nowhere), and the standalone `discovery` registration publishing `/discovery/*` (the frontend uses the nested `/api/discovery/*`). No `url_for()` referenced either. Fixing this *before* scoping means the scope map is written once, not twice.

2.  [ ] **Auth contract**
    *   Make "who may call what, and what does failure look like" explicit and uniform before enforcing it everywhere.

    2.1. [x] **Unify the two auth decorators**
        *   Implemented: `require_auth(scope)` now lives in `app/utils/auth_decorators.py` and accepts a session **or** an API key. The private copy in `app/api/pronunciation.py` (`_check_api_key_auth` + `_require_auth`) is deleted; the four pronunciation endpoints use the shared decorator.
        *   `login_required` / `admin_required` stay session-only on purpose — an API key must never reach identity or management endpoints (matrix rule 1). Pinned by `test_api_key_cannot_reach_management_endpoints`.

    2.2. [x] **Fix the 401/403 conflation**
        *   Implemented: one error contract, `{"error": ..., "code": ...}` — `authentication_required` (401, no credential), `invalid_api_key` (401, unknown/revoked/malformed key), `insufficient_scope` (403, valid key without the scope), `admin_required` (403). 401 means "I don't know who you are"; 403 means "I know, and no". The old code returned 401 for a scope failure, telling callers to retry with credentials that were never the problem.
        *   HTML vs JSON is negotiated on path + `X-Requested-With` + `Accept`, so browser navigations get `redirect(/auth/login?next=…)` (deep link preserved — this is also task 3.2's mechanism) while XHR/API callers get JSON.

    2.3. [x] **Stop the frontend misreporting auth failures as feature failures**
        *   Implemented: `app/static/js/alpine/pronunciation.js` now checks HTTP status first; 401/403 says "Not signed in", and "model not available" only fires on a genuine `available: false`.

    2.4. [x] **Auth failures are handled centrally, not per call site**
        *   Audit result: **7 files / 36 `fetch()` call sites** parse `.json()` with no status check at all (`discovery-dashboard`, `word-sketch-integration`, `quality-dashboard`, `alpine/revision-history`, `alpine/range-elements`, `query-builder`, `entry/entry-form-init`). The draft button was not special.
        *   Rather than patch 36 call sites (which rots — see 2.8), fixed the class of bug once: `app/static/js/auth.js` intercepts 401/403 for every request. **401** → redirect to `/auth/login?next=…`, preserving the deep link. **403** → surface the server's own message from the error contract. In both cases the promise *rejects*, so a handler that skips the status check can no longer parse an error body as data.
        *   Verified in a browser against a live CSRF+auth-enforcing server, using the exact bug shape (`fetch(...).then(r => r.json())`, no status check): it now rejects with "Authentication required" and lands on `/auth/login?next=%2F`, instead of reporting a fictitious domain failure. Also verified: no redirect loop on the login page, a 403 rejects with the scope message *without* navigating away, and successful responses pass through untouched.
        *   Removed the bespoke 401/403 branch added to `alpine/pronunciation.js` in 2.3 — with the global handler it is unreachable, and two sources of truth is the drift this task exists to end. The `!r.ok` check stays for genuine draft failures.
        *   `tests/unit/js_node_shim.js` gained `XMLHttpRequest` and `window.location` stubs: the repo's JS check *executes* each file under Node, and both interceptors wrap XHR at import time. (`csrf.js` only escaped this because it returns early when no token exists.)
        *   **Still open:** non-auth errors (400/500) are handled per call site, and those same 36 sites still parse error bodies on a 4xx/5xx. `makeApiRequest` in `api-utils.js` already does this correctly; migrating the raw `fetch` sites to it is a separate, mechanical task.

    2.5. [x] **Write the auth matrix**
        *   Implemented: `specs/auth_overhaul/auth_matrix.md`. All 47 blueprints classified PUBLIC / SESSION / SESSION+KEY (scoped) / ADMIN, with the public allowlist justified route by route.
        *   Baseline measured: only 8 modules carry any auth decorator — **~42 of 456 routes are protected, ~414 are open**.
        *   Key policy rule: **an API key can never reach identity or management endpoints** (it may not mint keys, create users, or change project/validation settings). This is what stops a leaked key escalating into permanent control.
        *   `main` is a *mixed* blueprint (UI pages + `/api/*`), so the gate must classify per route, not per blueprint.
        *   Three open decisions raised for review: registration policy (D1), `/apidocs` exposure (D2), whether keys should be write-capable at all (D3).
        *   Surfaced `POST /api/setup`: **unauthenticated, and it rewrites project settings** (name, languages, ranges). Worth fixing before the rollout, not as part of it.

    2.6. [x] **Make CSRF and Bearer auth coexist — unblocks every write-capable key**
        *   Implemented in `app/__init__.py`: `WTF_CSRF_CHECK_DEFAULT = False` plus a `before_request` that runs `csrf.protect()` for every request **except** those authenticating with `Authorization: Bearer`. CSRF defends *ambient* credentials (the browser attaches the session cookie whether the user meant to or not); a Bearer token is not ambient, so the check adds no safety there while breaking API keys outright.
        *   The hook mirrors Flask-WTF's own exemption checks (`_exempt_blueprints` / `_exempt_views`), because `protect()` does not consult them — without that, switching to a manual call would have silently started enforcing CSRF on the 29 write-routes that are currently exempt.
        *   Removed the dead `csrf.exempt(api_bp)`. It exempted nothing (api_bp has no routes of its own; its children report dotted names like `api.entries`, which never matched), **but it would have exempted all 59 `/api/*` routes the moment anyone flattened the nesting.** The other 8 exemptions are live and were left untouched — see 2.8.
        *   Regression-tested in `tests/integration/test_csrf_bearer_auth.py`: Bearer write with no CSRF token → 200; session write with no token → still 400; invalid Bearer → still 401 (skipping CSRF did not weaken auth); `/api/entries/` still CSRF-protected after the exemption removal.
        *   Verified no regression: full unit suite 2217 passed / 2 failed, and the same 2 failures (POS-tagger order-dependent pollution, unrelated files) reproduce on a baseline with these changes stashed.

    2.8. [x] **One CSRF rule, no exemptions — documented in `docs/CSRF_POLICY.md`**
        *   Removed **all 8** remaining `csrf.exempt(...)` calls, closing the **29 session-authenticated write-routes that had no CSRF protection at all** (`validation`, `validation_service`, `validation_rules`, `embeddings`, `dashboard`, `revisions`, …) — a real vulnerability, since those are exactly the cookie-authenticated endpoints CSRF exists to defend.
        *   The policy is now a single rule, stated once and applied everywhere: **a state-changing request must carry a CSRF token unless it authenticates with `Authorization: Bearer`.** One `before_request` in `create_app()`; zero per-endpoint special cases.
        *   The reason exemptions accumulated was that individual callers forgot the header, and each was patched at the *server*. Fixed at the cause instead: `app/static/js/csrf.js` wraps `fetch` and `XMLHttpRequest` once, attaching the token to every same-origin state-changing request. **No call site has to remember, and no endpoint needs an exemption** — including scripts not yet written. (27 of 30 mutating JS files set the header by hand; 3 did not, and 3 used raw XHR.)
        *   Verified in a real browser against a CSRF-enabled server: a token-less `fetch` and a raw `XMLHttpRequest` both reach previously-exempt endpoints, while an identical non-browser POST is still refused with "The CSRF token is missing".
        *   Guarded by `tests/integration/test_csrf_policy.py`, which **fails if anyone adds an exemption** (`_exempt_blueprints`/`_exempt_views` must stay empty), and pins: session write without a token → 400; Bearer write without a token → 200; invalid Bearer → still 401.
        *   Note: the existing e2e CSRF suite runs under `TestingConfig`, where `WTF_CSRF_ENABLED = False` — so it only ever asserted the meta tag exists and never exercised enforcement. The new integration tests build a development-config app so the real policy is tested.

    2.7. [x] **Empty scopes no longer mean "full access"**
        *   A key now grants exactly the scopes it was issued: an empty list grants **nothing** (403 `insufficient_scope`). Previously `if key_scopes and required_scope not in key_scopes` made a scope-less key omnipotent — the inherited "empty list means full access" convention, and the opposite of least privilege.
        *   Least privilege starts at issuance: `POST /api/keys/` now rejects a create with no scopes (400), so a key cannot be minted into that state.
        *   Removed the unit tests that asserted the old semantics. They were the tell: `test_scopes_allow_full_access_when_empty` and `test_scope_check_logic` re-implemented the decorator's expression inline and asserted against the *copy*, so they stayed green the whole time no key could authenticate at all. Scope decisions are now tested over real HTTP in `tests/integration/test_auth_contract.py`.

3.  [ ] **Full authentication rollout**
    *   Target posture: every route requires authentication unless explicitly allowlisted.

    3.1. [x] **Central `before_request` gate**
        *   Implemented: `app/auth_gate.py`, installed after every blueprint is registered so it covers the whole URL map. One hook, one allowlist — the entire security boundary for 441 routes is a single readable list, justified entry by entry against the matrix (2.5).
        *   **Fails closed**, which is the point: a route that is not on the allowlist requires identity from the day it is written, with nobody deciding anything. Pinned by `test_gate_fails_closed_for_a_route_nobody_protected`, which registers a brand-new undecorated route and asserts it is still shut.
        *   The gate establishes *identity* only; scopes stay with each route's `@require_auth(scope)`, and admin stays with `@admin_required`. Separating them is what keeps the allowlist reviewable.
        *   **API keys reach only routes that opted in.** `require_auth` marks its views `_accepts_api_key`; the gate refuses a Bearer credential anywhere else with 403 `api_key_not_permitted`. This makes matrix rule 1 structural rather than a convention — a leaked key cannot wander into the ~400 endpoints nobody meant to expose to machines.
        *   Allowlist exactness matters: `settings.health_check` and `validation_api.health_check` are *not* the health probe. Exact endpoint names only; `test_allowlisted_endpoints_all_exist` fails on a typo or a stale name.
        *   13 tests in `tests/integration/test_auth_gate.py`.

    3.2. [x] **Preserve deep links**
        *   Falls out of the 2.2 error contract: `auth_error()` redirects HTML navigations to `/auth/login?next=<url>` and returns JSON to `/api/*`, XHR (`X-Requested-With`), and JSON-preferring `Accept` headers. No silent redirects for XHR.

    3.3. [x] **Registration policy — closed by default (decision D1)**
        *   `/auth/register` and `/api/auth/register` are on the allowlist **only** when `ALLOW_REGISTRATION` is set. Default off, i.e. admin-created accounts — the recommendation in the matrix, and the safe default for a dictionary tool with a known editor set: it removes the one public *write* endpoint from the boundary entirely.
        *   Reversible by config, so this is a default rather than a verdict. If open registration is ever wanted, the endpoint needs rate limiting too.

    3.4. [x] **Roll out behind a config flag**
        *   `REQUIRE_AUTH`: on in production, off in development/testing for now, overridable by env var so the rollout can be *rehearsed* before it becomes the default.
        *   **Rehearsed, and it works**: the full e2e suite with `REQUIRE_AUTH=true` gives **408 passed / 7 failed** — byte-identical to the run with the gate off, and those 7 were independently confirmed pre-existing (they fail on a baseline with all of this session's changes stashed). Enforcing authentication across 441 routes causes **zero** new failures.
    3.5. [x] **Rollout: authentication is on by default**
        *   `REQUIRE_AUTH` now defaults to **true in every environment**. `REQUIRE_AUTH=false` opens the app back up; `flask create-admin` / `flask reset-password` get you in.
        *   Integration suite migrated the same way as e2e, at the chokepoint: every test client is signed in automatically (`tests/integration/conftest.py`), with `anonymous_client` — and `app._tests_anonymous = True` — as the opt-out for the modules that assert the door is locked.
        *   Two things the migration had to get right, both found by running it rather than by reasoning about it:
            *   **29 of the integration modules build their own app and client**, so patching the shared `client` fixture alone would have left most of the suite anonymous. The patch hangs off `Flask.test_client` and seeds a user lazily per app.
            *   It must be **session-scoped**: several modules build their client in a *module*-scoped fixture, which pytest instantiates before any function-scoped one — a function-scoped patch installs too late and those clients stay anonymous. That is what the first attempt got wrong, and the tests said so.
        *   Verified chunk by chunk against a gate-off baseline: **every chunk matches** (a–c: 5 failed/1 error; d–g: 1 failed; h–p: 2 failed; q–z: 2 failed — all identical with the gate on and off, all pre-existing). Turning authentication on across 441 routes causes **zero** new failures in unit, integration, or e2e.

4.  [ ] **Test coverage: the actual point of this overhaul**

    4.1. [x] **Authenticate the e2e suite at the fixture chokepoint**
        *   Implemented in `tests/e2e/conftest.py`: the `page` fixture now builds its browser context from `storage_state` captured after a **real `/auth/login` round-trip**, performed once per session. The existing e2e tests keep passing unchanged — no edits across 76 files — and they will already be signed in when the gate (3.1) lands.
        *   The session is established by driving the actual login form, not by forging a session cookie. A forged cookie would be faster and would also keep passing if login itself broke — which is precisely what happened for months (the `users` table was missing a column, so login was impossible and nothing noticed).
        *   `e2e_user` seeds the account: `TestingConfig` points SQLAlchemy at in-memory SQLite, so the app starts with no users at all.
        *   `anonymous_page` is the opt-out, for tests asserting unauthenticated behaviour (redirects, 401s).
        *   The browser is not the only client: 38 e2e files make **147 bare `requests.*` calls** straight at the app, all anonymous. Rather than add credentials to 147 call sites (147 things to remember forever — how the CSRF exemptions rotted), the `authenticated_requests` fixture patches `Session.request`, the funnel every `requests.*` helper passes through, and attaches the logged-in cookie to calls aimed at the app's base URL. Other hosts (BaseX, external services) are untouched; a test wanting an anonymous call passes `cookies=` explicitly. Found by the 3.4 rehearsal, not by guesswork.
        *   `tests/e2e/test_auth_fixture.py` asserts the property directly — that `page` is authenticated and `anonymous_page` is not. Without it, a fixture that silently degraded to anonymous would keep passing today (the app does not require auth yet) and collapse the moment the gate lands, with no clue why.
        *   Worth recording, because the fixture nearly shipped broken: `page.click('button[type="submit"]')` matched the **navbar search button** that `base.html` renders before the login form, so the "login" navigated to `/search?q=` without ever authenticating — and the obvious assertion (*"we are no longer on /auth/login"*) passed happily. The fixture now scopes the click to the login form and asserts on `/api/auth/check` (i.e. on the session), not on the URL.

    4.2. [x] **Real login e2e (the flow no fixture may fake)**
        *   Implemented: `tests/e2e/test_auth_login_e2e.py` — 7 tests driving the actual form: success, wrong password, unknown user, disabled account, logout, `next=` deep-link round-trip, and session expiry (cookie cleared).
        *   **Found two real bugs that had never been exercised**, both invisible for the same reason as everything else here — nobody could log in, so nobody could log *out* or follow a deep link either:
            *   **Logout was broken.** It constructed `ActivityLog(resource_type=…, details=…)`, but the model has `entity_type`/`entity_id` and neither of those fields. Every logout raised `TypeError`, 500'd, and **left the session intact** — you could not log out. Fixed to match the model (and login's own correct usage).
            *   **The deep link was dropped.** The login form posts to a bare `url_for('auth.login')`, so `?next=` was gone from `request.args` by the time the handler looked for it, and every login landed on the home page. Now carried through as a hidden field. Hardened while there: `next` must be a relative path (`//evil.example` is protocol-relative, i.e. an open redirect), and `auth_error()` now issues a *relative* `next` rather than the absolute `request.url` it was building.

    4.3. [x] **API key integration tests over HTTP**
        *   Implemented: `tests/integration/test_api_key_flow.py` — the full lifecycle through the real endpoints: mint → 201 with the raw key shown exactly once → authenticate from a session-less client → `last_used_at` recorded → revoke → 401 → reactivate → 200. Plus a tampered key (right prefix, wrong secret) → 401.
        *   This is the path all three original API-key bugs lived in, and that `tests/unit/test_api_key_auth.py` never touched (it hand-built prefixes and asserted against a copy of the decorator's logic).
        *   **Found another real bug:** `list_keys` had no admin bypass, while `create`/`revoke`/`reactivate` all did. An admin could mint a key and then not see it in the listing — so could never find its id to revoke it through the UI. Fixed.

    4.4. [x] **Keep the pronunciation/ByT5 endpoints as the worked example**
        *   Implemented: `tests/e2e/test_ipa_draft_e2e.py`. Signed in, the draft endpoint returns an IPA. Signed out, a caller using the *exact shape of the original bug* (`fetch(...).then(r => r.json())`, no status check) gets a **rejected** promise carrying "Authentication required" — not a parseable body it can misread — and the browser is sent to the login page.
        *   Asserts the message never mentions the model, so `available: false` can only ever mean one thing: there is genuinely no model deployed.

5.  [x] **Account lifecycle and hardening**

    5.1. [x] **Password reset**
        *   The flow was already written (token + 1h expiry + single-use via `reset_token_used`, email through the SMTP settings in `ProjectSettings`) and, like everything else here, had never run. Now covered end to end in `tests/integration/test_account_lifecycle.py`: a token sets a new password and invalidates the old one, works exactly once, expires, and an unknown address is answered identically to a known one (no user enumeration).
        *   **Found a bug:** `reset_password()` issued a new token without clearing `reset_token_used`. If a reset was interrupted between marking the token used and clearing the flag, every *future* token would be refused as "already used" — locking that account out of password reset permanently, recoverable only from the database. Fixed, and pinned by `test_a_second_reset_works_after_the_first_was_used`.

    5.2. [x] **Session hardening**
        *   `config.py` set **none** of the cookie flags, so the session cookie was readable by JavaScript (any XSS became account takeover), sent cross-site, and valid forever. Now: `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE='Lax'`, `PERMANENT_SESSION_LIFETIME=14 days`, and `SESSION_COOKIE_SECURE` on in production.
        *   `ProductionConfig` now states `WTF_CSRF_ENABLED = True` explicitly rather than inheriting it — `TestingConfig` turns CSRF off, and config classes get copied. Both are asserted in tests.

    5.3. [x] **API key management UI**
        *   The page existed and encoded the *old* semantics: it offered "leave empty for full access" (which the API now rejects) and displayed a scope-less key as **"all"** — the exact inverse of what the server does. Rewritten: a real form (no `prompt()` chains), explicit scope checkboxes, at least one required, and a scope-less key shown as "none".
        *   The scope list is now read off the routes themselves via `GET /api/keys/scopes`, which collects `_required_scope` from every `@require_auth` view. The old hand-kept list advertised `read`, `export` and `pronunciation:validate` — **none of which any endpoint has ever checked**, so a key granted them could do precisely nothing. A test asserts the offered scopes equal the enforced ones.
        *   `/settings/api-keys` had **no auth decorator at all**. It mints credentials; it is now `@login_required` and session-only.

    5.4. [x] **Activity logging**
        *   Added the events that were missing: **failed logins** (with the username and IP, and a null user_id when the account does not exist — a successful login is the least interesting thing in an audit trail), and API key **created / revoked / reactivated** (a key outlives the session that made it; if one leaks, the questions are when it was issued, by whom, and whether it was revoked). The raw key is never logged — the prefix identifies it.

---

## Suggested sequencing

Land **1.3** (schema drift guard) and **2.5** (auth matrix) first — they are cheap
and they de-risk everything after them. Then **2.1/2.2** (contract), then **4.1**
(fixture auth) *before* **3.1** (the gate), so that the moment the gate turns on,
the 439-test suite is already able to authenticate and will tell you what broke.
Enforcement (3.1) behind the `REQUIRE_AUTH` flag is the point of no return; do
not reach it without 4.1 in place.
