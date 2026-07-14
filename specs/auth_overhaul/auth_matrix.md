# Auth Matrix

The authorization policy for every blueprint in the application. This is the
review artifact for the central `before_request` gate (task 3.1): the gate's
public allowlist is derived from this document, and **every entry in that
allowlist must be justified here**.

Current state: 47 blueprints, 456 routes. Only 8 modules carry any auth
decorator at all — roughly **42 of 456 routes are protected; ~414 are open**.

## Classes

| Class | Meaning | Enforced by |
|---|---|---|
| **PUBLIC** | Reachable with no identity. The allowlist. | Nothing — explicitly exempted from the gate |
| **SESSION** | Requires a logged-in browser session. Not reachable with an API key. | Gate (identity) |
| **SESSION+KEY** | Session *or* `Authorization: Bearer sw_…`, subject to scopes. | Gate + per-route scope decorator |
| **ADMIN** | Logged-in session **and** `is_admin`. Never reachable with an API key. | Gate + `@admin_required` |

## Design rules

1. **An API key can never reach identity or management endpoints.** A key may
   read and write dictionary *data*; it may not mint another key, create a user,
   change project settings, or alter validation policy. This is what keeps a
   leaked key from escalating into permanent control of the instance.
2. **The gate establishes identity; decorators enforce scope.** The gate answers
   "who are you"; `@require_scope("entries:write")` answers "may you do this".
   Keeping them separate is what makes the gate reviewable as a single list.
3. **Scopes are `domain:action`**, extending the existing
   `pronunciation:read` / `pronunciation:write` convention already in `ApiKey.scopes`.
4. **Mixed blueprints are classified per route, not per blueprint** (see `main`).
5. **Fail closed.** A route in no class is SESSION by default. A new blueprint is
   protected the day it is added, without anyone remembering to protect it.

---

## PUBLIC — the allowlist

This is the complete set. Anything not on this list requires identity.

| Route | Methods | Why it must be public |
|---|---|---|
| `/health` | GET | Liveness/readiness probes run before any credential exists. Returns `{"status": "ok"}` only — no data. |
| `/auth/login` | GET, POST | The credential-granting endpoint itself. |
| `/auth/forgot-password` | GET, POST | Recovery must work when you cannot log in. |
| `/auth/reset-password/<token>` | GET, POST | Ditto; authorization is the single-use token (`reset_token_used`). |
| `/api/auth/login` | POST | JSON equivalent of `/auth/login`. |
| `/api/auth/reset-password` | POST | JSON equivalent of forgot-password. |
| `/api/auth/reset-password/complete` | POST | JSON equivalent of reset-with-token. |
| `/api/auth/check` | GET | Must be callable while unauthenticated — its entire job is to answer "am I logged in?" Returns a boolean, never user data. |
| `/auth/register`, `/api/auth/register` | GET, POST | **Conditional — see open decision D1.** Public only if open registration is the chosen policy. |
| `/static/*` | GET | Assets. |

Everything else in the application requires identity.

---

## SESSION — UI and self-service (no API key access)

| Blueprint | Module | Routes | Notes |
|---|---|---|---|
| `main` (UI routes) | `app.views` | `/`, `/activity-log`, entry/search pages, … | **Mixed blueprint** — its `/api/*` routes are classified below. |
| `index` | `app` | `/` | Redirects to login when anonymous. |
| `workbench` | `app.views` | 7 | Analytics/workbench pages. |
| `word_sketch_browser` | `app.routes.word_sketch_routes` | 1 | `/browser` UI. |
| `backup` | `app.routes.backup_routes` | 2 | `/backup/download` — serves dictionary data; must not be anonymous. |
| `auth` | `app.routes.auth_routes` | 8 | Non-public members: `/auth/logout`, `/auth/profile`, `/auth/profile/edit`, `/auth/change-password`. |
| `auth_api` | `app.api.auth_api` | 8 | Non-public members: `/api/auth/me`, `/api/auth/logout`, `/api/auth/change-password`. |
| `user_preferences` | `app.api.user_preferences_api` | 5 | Self-service; already fully decorated (8/8). |
| `messages_api` | `app.api.messages_api` | 9 | Already fully decorated (9/9). |
| `flasgger` | `flask.scaffold` | 5 | `/apidocs` — **see open decision D2.** Currently exposes the full API surface anonymously. |

## ADMIN — management (no API key access)

Rule 1 lives here: a leaked key must not be able to reach any of these.

| Blueprint | Module | Routes | Current state | Notes |
|---|---|---|---|---|
| `users_api` | `app.api.users_api` | 7 | 7/7 decorated | Account management. |
| `api_keys` | `app.api.api_keys` | 4 | 4/4 decorated | **Keys must never mint keys.** Session-only, permanently. |
| `project_members_api` | `app.api.project_members_api` | 6 | 3/6 decorated | 3 routes currently open — audit. |
| `settings` | `app.routes.settings_routes_clean` | 9 | **0/9** | Project settings UI, fully open today. |
| `setup` | `app.api.setup` | 1 | **0/1** | **`POST /api/setup` rewrites project settings — name, languages, ranges — with no authentication at all.** Anyone who can reach the app can reconfigure the project. Highest-severity finding in this audit. |
| `field_visibility` | `app.routes.field_visibility_routes` | 1 | **0/1** | Project-level display policy. |
| `validation_rules` | `app.api.validation_rules_api` | 11 | **0/11** | Validation *policy* is configuration, not data — admin, not key-accessible. |

## SESSION+KEY — dictionary data (scoped)

Machine-callable. Each needs a scope decorator; the scope column is the proposed
taxonomy.

| Blueprint | Module | Routes (mut) | Proposed scope |
|---|---|---|---|
| `entries` | `app.api.entries` | 11 (7) | `entries:read` / `entries:write` |
| `api` | `app.api.entries` | 70 (38) | Per-route; mostly `entries:*` and `bulk:write`. **Largest single surface — needs its own pass.** See finding F1. |
| `additional_api` | `app.routes.api_routes` | 5 (0) | `entries:read`, `ranges:read` |
| `xml_entries` | `app.api.xml_entries` | 6 (3) | `entries:read` / `entries:write` |
| `autosave` | `app.api.entry_autosave_working` | 2 (1) | `entries:write` |
| `revisions`, `revision_stats` | `app.api.revisions_api` | 4 (1) | `entries:read` |
| `worksets_api` | `app.api.worksets` | 27 (19) | `worksets:read` / `worksets:write` |
| `ranges` | `app.api.ranges` | 14 (3) | `ranges:read` / `ranges:write` |
| `ranges_editor` | `app.api.ranges_editor` | 17 (9) | `ranges:write` |
| `lift_registry` | `app.api.lift_registry` | 9 (0) | `ranges:read` |
| `pronunciation` | `app.api.pronunciation` | 7 (6) | `pronunciation:read` / `pronunciation:write` — **already implemented; the reference example.** |
| `display_profiles`, `display` | `app.api.display_profiles`, `app.api.display` | 26 (16) | `profiles:read` / `profiles:write` |
| `dictionaries` | `app.api.dictionary_api` | 13 (8) | `dictionaries:read` / `dictionaries:write` |
| `merge_split` | `app.api.merge_split` | 9 (3) | `entries:write` |
| `validation_bp`, `validation_service`, `validation_api` | `app.api.validation*` | 24 (14) | `validation:read` / `validation:write` (running checks — distinct from *authoring rules*, which is ADMIN) |
| `query_builder` | `app.api.query_builder` | 6 (4) | `entries:read` |
| `corpus`, `corpus_search` | `app.routes.corpus_routes`, `app.api.corpus_search` | 7 (3) | `corpus:read` |
| `word_sketch` | `app.api.word_sketch_api` | 14 (4) | `corpus:read` |
| `ai` | `app.api.ai_api` | 8 (6) | `ai:write` — spends money/quota; scope it tightly. |
| `embedding_api` | `app.api.embedding_api` | 8 (3) | `ai:write` |
| `illustration` | `app.api.illustration` | 3 (2) | `ai:write` |
| `discovery_api` | `app.api.discovery` | 4 (3) | `ai:write` |
| `backup_api` | `app.api.backup_api` | 17 (8) | `backup:read` / `backup:write` — **exports the whole dictionary; treat as sensitive.** |
| `main` (`/api/*` routes) | `app.views` | ~16 | `/api/stats` → `entries:read`; `/api/live-preview`, `/api/pronunciations/generate` → `entries:read`; import-mappings → `entries:write` |
| `project_defaults` | `app.api.user_preferences_api` | 3 (2) | `profiles:write` |

---

## Open decisions

- **D1 — Registration policy.** `/auth/register` and `/api/auth/register` are live
  and unauthenticated. Under "full auth everywhere" this is the one intentional
  public *write* endpoint. Options: (a) open registration + rate limiting,
  (b) invite-only, (c) admin-created accounts only (remove the public route).
  Recommendation: **(c)** for a dictionary editing tool with a known editor set —
  it removes the endpoint from the allowlist entirely.
- **D2 — `/apidocs` (flasgger).** Currently anonymous, and it documents the entire
  API surface. Recommendation: **SESSION** in all environments, or disabled in
  production.
- **D3 — Should keys ever be write-capable? — RESOLVED: yes.** The write-back case
  is already shipped, not hypothetical:
  - `tools/scripts/api_client.py` exposes `create_entry` (POST), `update_entry`
    (PUT) and `delete_entry` (DELETE), with `entries create|update|delete` CLI
    subcommands. `tools/README.md` documents
    `python api_client.py entries create --file new_entry.json`.
  - `docs/plans/2026-06-23-api-ecosystem-and-external-tools.md` design tenet 3:
    "Every current `/api/*` endpoint works with API key auth in addition to
    session auth", and it explicitly resolves the writeback question — the dedup
    `apply` endpoint "modifies project data. It needs a separate scope
    (`pronunciation:write`)" for CI/scheduled-batch use.

  Keep `:write` scopes, but least-privilege: scopes must be chosen explicitly at
  creation, keys default to read-only in the UI, and no key ever reaches ADMIN
  endpoints (rule 1). See F4 — write keys do not actually function today.

## Findings (not auth policy, but surfaced by this audit)

- **F1 — Double prefix. FIXED.** `validation_rules_bp` declares
  `url_prefix="/api/projects"` *and* was registered twice: nested inside `api_bp`
  (`/api` → `/api/api/projects/...`, 11 rules) and standalone (`/api/projects/...`,
  11 rules). `discovery_bp` had the mirror problem: the frontend calls the nested
  `/api/discovery/*`, while a standalone registration published an unused
  `/discovery/*`. Nothing in the codebase referenced `/api/api/*` (0 hits) or bare
  `/discovery/*`, and no `url_for()` pointed at either. Removed both dead
  registrations — **15 dead routes gone, 456 → 441**, no live route affected.
- **F2 — Shadowed routes.** `additional_api` serves `/api/entries` and `/api/ranges`,
  which the `entries` and `ranges` blueprints also serve. Determine which
  actually wins in the URL map before assigning scopes. *Still open.*
- **F3 — `POST /api/setup` unauthenticated. FIXED.** It rewrote project settings
  (name, languages, ranges) with no authentication. Now `@admin_required`:
  anonymous → 401, non-admin session → 403. Swagger still lists it.
- **F4 — API keys cannot write, at all, in production. OPEN — blocks D3.**
  CSRF protection applies to every `/api/*` POST/PUT/DELETE, and a Bearer request
  from a script carries no CSRF token, so it is rejected with `400 CSRF token is
  missing` before auth is even considered. Verified: a valid key with
  `pronunciation:write` is blocked on `POST /api/pronunciation/draft` under
  production CSRF settings. **The shipped `api_client.py entries create/update/delete`
  commands therefore cannot work against a real deployment.**
  - The existing `csrf.exempt(api_bp)` calls in `app/__init__.py` do *not* take
    effect: nested blueprints report dotted names (`api.entries`), so exemption by
    blueprint name never matches. Harmless today (no CSRF hole), but they are dead
    code that would silently *become* a hole if the nesting were ever flattened —
    delete them.
  - Fix (canonical): set `WTF_CSRF_CHECK_DEFAULT = False` and call `csrf.protect()`
    from a `before_request` only when the request is *cookie*-authenticated. CSRF
    exists to defend ambient credentials; a Bearer token is not ambient, so it needs
    no CSRF check. This keeps every session/XHR request protected exactly as today.
