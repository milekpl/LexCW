# CSRF Policy

## The rule

> **A state-changing request (POST/PUT/PATCH/DELETE) must carry a CSRF token,
> unless it authenticates with `Authorization: Bearer` (an API key).**

That is the whole policy. It applies to every route, in every blueprint. There
are **no exemptions** — not per-blueprint, not per-view, not per-method.

## Why Bearer requests are exempt

CSRF exists to defend **ambient** credentials. The browser attaches your session
cookie to a cross-site request whether you meant it or not, so the server cannot
tell "the user clicked a button on our page" from "the user visited evil.com,
which POSTed to our page in the background". The CSRF token is the proof of
intent that the cookie cannot provide.

A Bearer token is not ambient. A browser never attaches it automatically; a
script has to set the header deliberately. There is no confused-deputy problem to
solve, so the check buys no safety — while breaking API keys completely, because
a script has no CSRF token to send.

## How it is enforced

**Server** — one hook, in `create_app()` (`app/__init__.py`):

```python
app.config["WTF_CSRF_CHECK_DEFAULT"] = False   # we call protect() ourselves

@app.before_request
def _csrf_protect():
    if not app.config.get("WTF_CSRF_ENABLED", True):
        return
    if request.method not in app.config["WTF_CSRF_METHODS"]:
        return
    if not request.endpoint:
        return
    if request.headers.get("Authorization", "").startswith("Bearer "):
        return
    csrf.protect()
```

`WTF_CSRF_ENABLED` is false only in `TestingConfig`.

**Browser** — one interceptor, `app/static/js/csrf.js`, loaded from `base.html`
before any other script. It wraps `fetch` and `XMLHttpRequest` and attaches the
token (from the `csrf-token` `<meta>` tag) to every same-origin state-changing
request.

This is the important half. **No call site needs to remember the header.** A new
`fetch("/api/…", {method: "POST"})` in any script is protected the day it is
written, with no server-side change and no exemption.

## Do not add exemptions

`csrf.exempt(...)` is banned, and `tests/integration/test_csrf_policy.py` fails if
anyone adds one.

The rule exists because the previous policy was a patchwork of per-blueprint
exemptions, added one at a time whenever a frontend call turned out not to send a
token. It produced exactly the two failures you would predict:

- **29 session-authenticated write routes had no CSRF protection at all**
  (`validation`, `validation_service`, `validation_rules`, `embeddings`,
  `dashboard`, `revisions`, …) — a real vulnerability, since those are precisely
  the cookie-authenticated endpoints CSRF is meant to defend.
- **`csrf.exempt(api_bp)` did nothing** — nested blueprints report dotted names
  (`api.entries`), so the exemption never matched — but it was aimed at the whole
  `/api` tree and would have silently exempted **all 59 `/api/*` routes** the
  moment anyone flattened the blueprint nesting.

Both are the same mistake: an exemption is a blunt instrument aimed at a
*symptom* (a caller that forgot a header) rather than the cause. Fix the caller —
or better, rely on the interceptor, which fixes all callers at once.

If a request genuinely cannot send a token, it is a machine client, and it should
authenticate with an API key (`Authorization: Bearer sw_…`), which the policy
already exempts. See `specs/auth_overhaul/auth_matrix.md` for which endpoints
accept keys and under which scopes.

## Testing

`tests/integration/test_csrf_policy.py` pins all four properties:

| Property | Test |
|---|---|
| No blueprint or view is exempt | `test_no_endpoint_is_csrf_exempt` |
| Session write without a token → 400 | `test_session_write_requires_csrf_token` |
| Bearer write without a token → 200 | `test_bearer_write_is_exempt_without_a_token` |
| Skipping CSRF does not skip **auth** | `test_bearer_exemption_does_not_bypass_authentication` |

Unit and integration tests run with `WTF_CSRF_ENABLED = False` (`TestingConfig`);
the tests above build an app with the development config so the real policy is
exercised.
