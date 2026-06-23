# API Ecosystem & External Tools — Design Spec

**Status**: Draft  
**Date**: 2026-06-23  
**Drives**: Removal of importlib-based plugin system; introduction of API-key auth for external tools

---

## 1. Motivation

The current `PluginManager` uses `importlib` to load and execute `plugin.py` files from `instance/plugins/` inside the Flask process. This has proven problematic:

- **Security**: Any plugin runs as trusted code with full app access (DB, secrets, filesystem).
- **Fragility**: A buggy plugin crashes the entire app.
- **Language lock-in**: Plugins must be Python.
- **Distribution friction**: Users must copy files to a server directory.
- **Maintenance burden**: The hard-coded endpoint mapping in `get_exporters()` (now improved but still a sign of friction).

**Replace with**: An API-first ecosystem where external tools — scripts, CLIs, WASM runners, Postman collections — interact with the dictionary through authenticated HTTP endpoints. The app exposes endpoints; the ecosystem grows outside it.

---

## 2. Design Tenets

1. **The app is a data server, not a code host.** It exposes data via authenticated endpoints. It does not import, execute, or trust external code.
2. **API keys, not sessions, for machine clients.** Human users still use session auth. Machine-to-machine calls use bearer tokens scoped to a project.
3. **Existing endpoints stay.** Every current `/api/*` endpoint works with API key auth in addition to session auth.
4. **Plugin system is removed.** No `importlib`, no `plugin.py`, no `PluginManager`. The export card UI in templates becomes a static list of endpoints that the user can call externally.
5. **Async for expensive operations.** Batch IPA validation and large exports get a job-based async pattern (POST to create, GET `/status/{id}` to poll, GET `/result/{id}` to fetch).

---

## 3. API Key Authentication

### 3.1 Model

```python
# New model: app/models/api_key.py

class ApiKey(db.Model):
    __tablename__ = "api_keys"

    id            = Column(Integer, primary_key=True)
    project_id    = Column(Integer, ForeignKey("project_settings.id"), nullable=False)
    label         = Column(String(100), nullable=False)        # User-facing name: "my script"
    key_hash      = Column(String(255), nullable=False)         # werkzeug hashed key
    key_prefix    = Column(String(8), nullable=False, unique=True)  # First 8 chars for identification
    scopes        = Column(JSON, nullable=False, default=list)   # ["read", "export", "pronunciation:validate"]
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=func.now())
    last_used_at  = Column(DateTime, nullable=True)
```

- The raw key is shown **once** at creation, hashed immediately (same scheme as passwords: `generate_password_hash`).
- `key_prefix` is stored in plaintext so logs can say "request by key `sw_abc12...`" without exposing the full key.
- Scopes are an allowlist; an empty list means full access.

### 3.2 Key Format

```
sw_abc123def456ghijklmno   (prefix "sw_" + 32 chars of secrets.token_urlsafe)
```

- Prefix `sw_` = "slownik wielki" / "service worker" — human-readable origin.
- 32 chars of `token_urlsafe` = ~192 bits of entropy.
- Total: ~35 chars. Shown once: `sw_abc123def456...`

### 3.3 Auth Middleware

```python
# app/utils/api_key_auth.py

def require_api_key(scope: Optional[str] = None):
    """Decorator that accepts either session auth or a valid API key.

    If `scope` is given, the key must have that scope (or full access).
    Falls back to session-based login_required if no API key header.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                raw_key = auth_header[7:]
                # Look up by prefix (first 8 chars after "sw_")
                prefix = raw_key[:11]  # "sw_" + 8 chars
                key_record = ApiKey.query.filter_by(
                    key_prefix=prefix, is_active=True
                ).first()
                if key_record and check_password_hash(key_record.key_hash, raw_key):
                    if scope and scope not in key_record.scopes and key_record.scopes:
                        return jsonify({"error": "Scope not allowed"}), 403
                    key_record.last_used_at = datetime.now(timezone.utc)
                    db.session.commit()
                    g.api_key = key_record
                    return f(*args, **kwargs)
                return jsonify({"error": "Invalid API key"}), 401
            # Fall back to session auth
            return login_required(f)(*args, **kwargs)
        return wrapper
    return decorator
```

### 3.4 Management UI

- **Settings → API Keys** section: list keys, create new (show once), revoke.
- No edit (key is hashed). Revoke sets `is_active = False`.

### 3.5 Migration

Add `api_keys` table. Single migration script, same pattern as existing ones.

---

## 4. Plugin System Removal

### 4.1 What goes away

| File | Action |
|---|---|
| `app/services/plugin_manager.py` | Delete entirely (no more `PluginManager` class) |
| `app/__init__.py` — plugin loading block | Remove `from app.services.plugin_manager import ...` block |
| `instance/plugins/{kindle_exporter,stardict_exporter}/` | Move to `examples/` or a new `tools/` directory at repo root |
| Export options template's "Plugin Exporters" card section | Replace with a static "Available API Endpoints" help card |

### 4.2 What stays (adapted)

- **`get_exporters()` method** — gone with the class. The frontend export page instead lists hard-coded known export endpoints (which are just API routes the app already registers).
- **Template `export_options.html`** — the "Plugin Exporters" section becomes a static reference showing: "Want to export? Use the buttons above, or call the API directly:"

```html
<div class="card">
  <div class="card-body">
    <h5>API Access</h5>
    <p>Generate an API key in Settings, then:</p>
    <pre><code>curl -H "Authorization: Bearer $KEY" \
  {{ url_for('main.export_lift', _external=True) }}</code></pre>
  </div>
</div>
```

### 4.3 Plugin manifests → Example tools

The actual plugin code (kindle, stardict, sqlite exporters) moves to `tools/` at the repo root. Each gets:

```
tools/kindle-export/
├── README.md          # "Call the API, then post-process..."
├── export.sh          # Simple bash script wrapping curl
├── export.py          # More featured Python script
└── requirements.txt   # (optional) extra deps beyond stdlib
```

These are **reference implementations** — not installed, not auto-loaded. Users run them from their own machine, pointing at their instance's API.

---

## 5. New Async Endpoint: `/api/pronunciation/batch-validate`

### 5.1 Purpose

Accept a list of `{lexeme, ipa}` pairs, run ByT5 + autoencoder inference, return anomaly scores. Designed for the flextools-trained models.

### 5.2 Request

```http
POST /api/pronunciation/batch-validate
Authorization: Bearer sw_abc123def456...
Content-Type: application/json

{
  "entries": [
    {"lexeme": "tree", "ipa": "triː"},
    {"lexeme": "sea", "ipa": "siː"},
    {"lexeme": "thought", "ipa": "θɔːt"}
  ],
  "threshold_cer": 0.20,
  "threshold_recon": 3.5
}
```

### 5.3 Response (sync, for ≤500 entries)

```json
{
  "job_id": null,
  "sync": true,
  "results": [
    {"lexeme": "tree",  "ipa": "triː",     "cer": 0.0,  "recon_error": 1.2, "anomaly": false},
    {"lexeme": "sea",   "ipa": "siː",      "cer": 0.0,  "recon_error": 0.9, "anomaly": false},
    {"lexeme": "thought", "ipa": "θɔːt",   "cer": 0.0,  "recon_error": 1.1, "anomaly": false}
  ]
}
```

For >500 entries, response switches to async:

```json
{
  "job_id": "pron-val-a1b2c3d4",
  "sync": false,
  "total": 90000,
  "results": []
}
```

### 5.4 Async Status & Result

```http
GET /api/jobs/pron-val-a1b2c3d4
→ {"status": "processing", "progress": 45000/90000}

GET /api/jobs/pron-val-a1b2c3d4/result
→ {"results": [...], "export_url": "/api/jobs/pron-val-a1b2c3d4/result.csv"}
```

### 5.5 Background Job Model

```python
# app/models/job.py

class Job(db.Model):
    __tablename__ = "jobs"

    id          = Column(String(32), primary_key=True)   # token_urlsafe(24)
    type        = Column(String(50), nullable=False)      # "pronunciation_validation", "export"
    project_id  = Column(Integer, ForeignKey("project_settings.id"))
    status      = Column(String(20), default="queued")    # queued → processing → completed / failed
    progress    = Column(Integer, default=0)
    total       = Column(Integer, default=0)
    params      = Column(JSON)
    result_path = Column(String(500), nullable=True)      # Path to output file
    error       = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
```

Processing via a thread pool or Redis queue (simple first: `threading.Thread` for background, swap to Celery if needed).

---

## 6. Endpoint Map for External Tools

| Endpoint | Method | Scope | Purpose |
|---|---|---|---|
| `/api/entries/` | GET | `read` | List/search entries |
| `/api/export/lift` | GET | `export` | Download LIFT |
| `/api/export/html` | GET | `export` | Download HTML |
| `/api/pronunciation/batch-validate` | POST | `pronunciation:validate` | IPA anomaly check |
| `/api/pronunciation/compress` | POST | `pronunciation:read` | Expand parenthesized IPA variants |
| `/api/pronunciation/deduplicate` | POST | `pronunciation:read` | Find duplicate/near-duplicate pronunciations |
| `/api/pronunciation/deduplicate/apply` | POST | `pronunciation:write` | Apply dedup removal/merge actions |
| `/api/jobs/{id}` | GET | `read` | Check job status |
| `/api/jobs/{id}/result` | GET | `read` | Download job result |

All scopes are optional in the decorator — omitted means fallback to session auth.

---

## 7. External Tool Examples (to live in `tools/`)

### 7.1 Bash: Bulk CSV export

```bash
#!/usr/bin/env bash
# tools/export-csv/export.sh
KEY="${1:?Usage: $0 <api-key>}"
URL="${2:-http://localhost:5000}"

curl -s -H "Authorization: Bearer $KEY" \
  "$URL/api/entries/?limit=100000" \
  | jq -r '.entries[] | [.id, .lexical_unit.en, .pronunciations["seh-fonipa"]] | @csv' \
  > entries.csv
```

### 7.2 Python: Batch pronunciation validation

```python
#!/usr/bin/env python3
# tools/pronunciation-validate/validate.py
"""Read a CSV of lexeme,ipa pairs, send to API, print anomalies."""

import csv, sys, requests

API_KEY = sys.argv[1]
API_URL = sys.argv[2]  # e.g. https://myapp.com

entries = []
with open(sys.argv[3]) as f:
    for row in csv.DictReader(f):
        entries.append({"lexeme": row["lexeme"], "ipa": row["ipa"]})

resp = requests.post(
    f"{API_URL}/api/pronunciation/batch-validate",
    json={"entries": entries},
    headers={"Authorization": f"Bearer {API_KEY}"},
)

for r in resp.json()["results"]:
    if r["anomaly"]:
        print(f"ANOMALY: {r['lexeme']:20s} {r['ipa']:20s} CER={r['cer']:.2%}")
```

### 7.3 Python: Full dictionary audit (combines export + validate)

```python
# tools/dictionary-audit/audit.py
"""Export all entries, validate pronunciations, produce a report."""
```

### 7.4 WASM note

A Python script running in WASM (via Pyodide or similar) could present a web UI that calls the API directly from the user's browser — no local Python install needed. The API key would still be required. This is a natural next step but out of scope for this spec.

---

## 8. Migration Path

| Step | What |
|---|---|
| **1. API key model + middleware** | Add `ApiKey` model, migration, `require_api_key` decorator |
| **2. API key management UI** | Settings page section to create/revoke keys |
| **3. Add scope checks to existing endpoints** | Decorate `/api/export/*`, `/api/entries/*`, etc. |
| **4. Build `/api/pronunciation/batch-validate`** | Sync for ≤500, async for larger |
| **5. Build generic job model** | `Job` model + status/result endpoints |
| **6. Remove PluginManager** | Delete `plugin_manager.py`, remove load block from `create_app()` |
| **7. Move plugin code → `tools/`** | Repo restructure, write READMEs |
| **8. Update export options template** | Replace plugin cards with API reference section |
| **9. Write example tools** | Bash + Python scripts in `tools/` |
| **10. Document** | Add "API Access" page to help system |

---

## 9. Open Questions

- **Rate limiting?** — Not needed initially; the API key is tied to one project, and the user is rate-limiting themselves. Add if abuse surfaces.
- **CORS for WASM browsers?** — The app already serves its own API on the same origin, so WASM from the same domain works. Cross-origin WASM needs CORS headers.
- **Model loading for ByT5?** — The trained model is ~350MB. Loading it on every request is wasteful. Options: (a) pre-load at app startup and keep in memory, (b) run inference in a separate worker process, (c) skip local model and use a lighter IPA regex check for the synchronous path, with the full model only in the async path. **Recommendation**: start with a lightweight IPA regex validator (the `IPAHelper` logic ported from flextools) for the sync path, and only load ByT5 for the async background job.

---

---

## 9. IPA Compression & Deduplication Endpoints

In addition to batch validation, two common pronunciation hygiene operations should be available as API endpoints. Both leverage logic already implemented in the flextools codebase.

### 9.1 Parentheses Compression (`/api/pronunciation/compress`)

IPA transcriptions frequently use parentheses to mark optional sounds:
```
ˈskɒtɪˌsɪz(ə)m         →  ["ˈskɒtɪˌsɪzm", "ˈskɒtɪˌsɪzəm"]
(ˌ)lækˈteɪʃ(ə)n        →  ["lækˈteɪʃn", "lækˈteɪʃən", "ˌlækˈteɪʃn", "ˌlækˈteɪʃən"]
a(b)c(d)e              →  ["abce", "ace", "acde", "abcde"]
```

**Purpose**: Two entries with `ˈskɒtɪˌsɪzm` and `ˈskɒtɪˌsɪzəm` are really the same word with an optional schwa. Compression normalizes them by expanding all parenthesized variants, enabling accurate deduplication and comparison.

**Request**:
```http
POST /api/pronunciation/compress
Authorization: Bearer sw_abc123...
Content-Type: application/json

{
  "entries": [
    {"lexeme": "Scottishism", "ipa": "ˈskɒtɪˌsɪz(ə)m"},
    {"lexeme": "lactation", "ipa": "(ˌ)lækˈteɪʃ(ə)n"}
  ]
}
```

**Response**:
```json
{
  "results": [
    {
      "lexeme": "Scottishism",
      "ipa_raw": "ˈskɒtɪˌsɪz(ə)m",
      "variants": ["ˈskɒtɪˌsɪzm", "ˈskɒtɪˌsɪzəm"]
    },
    {
      "lexeme": "lactation",
      "ipa_raw": "(ˌ)lækˈteɪʃ(ə)n",
      "variants": ["lækˈteɪʃn", "lækˈteɪʃən", "ˌlækˈteɪʃn", "ˌlækˈteɪʃən"]
    }
  ]
}
```

**Implementation**: Port `IPAHelper.process_parentheses()` and `process_and_split()` from `flextools/pronunciation_tools.py` into `app/services/ipa_service.py`. Pure string manipulation — no model needed, synchronous, fast.

### 9.2 Pronunciation Deduplication (`/api/pronunciation/deduplicate`)

Detects entries that have duplicate or near-duplicate pronunciations.

**Types detected** (ported from `Find_Duplicate_Pronunciations.py`):

| Type | Example | Detection |
|---|---|---|
| **Exact duplicate** | `triː, triː` | Identical strings within same entry |
| **Stress-only variant** | `ˈrekɔːd` vs `ˌrekɔːd` | Same phonemes, stress on same syllable, different stress marker |
| **Optional-sound equivalent** | `ˈskɒtɪˌsɪzm` vs `ˈskɒtɪˌsɪzəm` | Same after parentheses expansion (uses compress first) |
| **Cross-entry duplicate** | Two different entries share the same IPA | Same expanded variant, different lexemes |

**Request**:
```http
POST /api/pronunciation/deduplicate
Authorization: Bearer sw_abc123...
Content-Type: application/json

{
  "entries": [
    {"lexeme": "record", "ipa": "ˈrekɔːd, rɪˈkɔːd"},
    {"lexeme": "record", "ipa": "ˈrekɔːd"},
    {"lexeme": "Scottishism", "ipa": "ˈskɒtɪˌsɪz(ə)m"},
    {"lexeme": "Scottishism", "ipa": "ˈskɒtɪˌsɪzəm"}
  ]
}
```

**Response**:
```json
{
  "duplicates": [
    {
      "type": "exact",
      "lexeme": "record",
      "ipa": "ˈrekɔːd",
      "locations": ["entry_123", "entry_123"],
      "recommendation": "Remove duplicate"
    },
    {
      "type": "optional_sound_equivalent",
      "lexeme": "Scottishism",
      "ipa_a": "ˈskɒtɪˌsɪz(ə)m",
      "ipa_b": "ˈskɒtɪˌsɪzəm",
      "recommendation": "Merge into compressed form ˈskɒtɪˌsɪz(ə)m"
    }
  ],
  "stats": {
    "total_entries": 4,
    "duplicate_groups": 2,
    "entries_with_duplicates": 3
  }
}
```

**Implementation**: Port the dedup logic from `Find_Duplicate_Pronunciations.py`. The compression endpoint feeds it — run `compress` first, then compare expanded variant sets.

### 9.3 Deduplication Action (`POST /api/pronunciation/deduplicate/apply`)

For automated use (e.g., in a CI pipeline or scheduled batch): applies the recommended actions from deduplication.

**Request**:
```json
{
  "actions": [
    {"type": "remove", "entry_id": "entry_123", "ipa": "ˈrekɔːd"},
    {"type": "merge_to_compressed", "entry_id": "entry_456", "ipa": "ˈskɒtɪˌsɪz(ə)m"}
  ]
}
```

**Response**: `{"applied": 2, "errors": []}`

---

## 10. Implementation Order

| Phase | Steps |
|---|---|
| **Phase 1: Auth foundation** | ApiKey model + migration + `require_api_key` decorator + Settings UI |
| **Phase 2: IPA service** | Port `IPAHelper` logic to `app/services/ipa_service.py` + compress endpoint |
| **Phase 3: Deduplication** | Port dedup logic + `/deduplicate` endpoint + `/deduplicate/apply` |
| **Phase 4: Batch validation** | ByT5/autoencoder async endpoint + Job model |
| **Phase 5: Plugin removal** | Delete `PluginManager`, move plugin code to `tools/`, update templates |
| **Phase 6: Example tools** | Bash + Python reference scripts in `tools/` + WASM proof-of-concept |

---

## 11. Open Questions

- **Rate limiting?** — Not needed initially; the API key is tied to one project, and the user is rate-limiting themselves. Add if abuse surfaces.
- **CORS for WASM browsers?** — The app already serves its own API on the same origin, so WASM from the same domain works. Cross-origin WASM needs CORS headers.
- **Model loading for ByT5?** — The trained model is ~350MB. Loading it on every request is wasteful. Start with a lightweight IPA regex validator (the `IPAHelper` logic ported from flextools) for the sync path, and only load ByT5 for the async background job.
- **Dedup writeback scope?** — The `apply` endpoint modifies project data. It needs a separate scope (`pronunciation:write`) distinct from the read-only validation scopes.

---

## 12. Summary

| Before | After |
|---|---|
| Plugins run inside app (importlib) | Tools run outside (HTTP) |
| Plugin code must be Python | Any language / shell / WASM |
| Plugin dir must exist on server | Only needs the public API URL |
| Plugin manager needs allowlist, discovery, loading | No manager; endpoints are self-documenting |
| Hard to debug, easy to crash | Tool fails independently; server logs key prefix |
| `instance/plugins/` is a security concern | API key auth gives audit trail and revocation |
