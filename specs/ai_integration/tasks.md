# Implementation Plan: AI Integration

This document outlines the implementation tasks for the AI Integration feature, based on the requirements in `specification.md`.

1.  [x] **AI Infrastructure**
    *   This epic covers the implementation of the basic infrastructure for integrating AI into the application.

    1.1. [x] **LLM Integration Framework**
        *   Set up an integration framework for Large Language Models (LLMs).
        *   Implemented: `AIService` in `app/services/ai_service.py` with OpenAI-compatible chat completion client. Supports OpenAI API and GitHub Models. BYOK (Bring Your Own Key) — API key stored per project or passed per request.
        *   **Requirements**: `2.2.1`, `8.2`, `18.2`

    1.2. [x] **Content Generation Pipeline**
        *   Build a pipeline for generating content using AI, such as example sentences and definitions.
        *   Implemented: `draft_entry()` method generates complete dictionary entries from descriptions. Entries serialized to YAML with meaningful markers for LLM readability. Customizable prompt templates.
        *   **Requirements**: `3.2.2`, `8.2.1`, `18.2`

2.  [x] **Machine Learning Models**
    *   This epic covers the integration of machine learning models into the application.

    2.1. [x] **POS Tagging Integration**
        *   Integrate a Part-of-Speech (POS) tagger, such as spaCy, into the application.
        *   Implemented: `POSTaggerService` (`app/services/pos_tagger_service.py`) — spaCy tagging with rule-based fallback, configurable Penn/UD tagset mappings (`config/pos_tagset_mappings.json`), entry/headword POS prediction, per-sense batch tagging, and definition phrase-category coherence analysis. Exposed via `app/api/pos_api.py` (`/pos/tag-entry`, `/pos/batch-tag`, `/pos/apply-tags`, `/pos/validate-definition-coherence`, `/pos/mappings`). Entry-form UI in `app/static/js/ai-service.js` (`btn-pos-tagger`). ML anomaly detector `POSCoherenceService` (`app/services/pos_coherence_service.py`) surfaced on the dashboard (`/api/dashboard/anomalies`).
        *   **Requirements**: `3.2.3`, `18.2`

    2.2. [x] **Pronunciation Systems (IPA Prediction — server-side transformer + LexCW API)**
        *   Implement a system for automatically generating IPA pronunciations / detecting
            anomalous pronunciations from text.
        *   **Confirmed approach (2026-07-07):**
            - The IPA predictor is a *transformer* G2P model. Two implementations exist in
              `flextools-main`:
              - **Custom `G2PModel`** (`FlexTools/Modules/Wielki/g2p/model.py` + `trainer.py`):
                a small encoder-decoder transformer (~256 hidden, 4 layers). **CPU-trainable**
                (`device = cuda if available else cpu`, batch=4 on CPU) → can train **on the server**.
                Consumed by `G2PAnomalyDetector` (dual method: predict-vs-stored PER confidence +
                optional `IPAutoencoder` reconstruction error) for pronunciation anomaly detection.
              - **ByT5** (`FlexTools/scripts/train_byt5_g2p.py`): HuggingFace `google/byt5-*`,
                GPU-intensive → **local/offline training only** (Colab), not on the server.
            - We publish a **training + anomaly-detection script** at `scripts/ipa_training/`
              (self-contained copy/adaptation of the `g2p/` modules + a new `lexcw_client.py`
              that replaces the SIL FieldWorks extractor). It pulls `(headword, IPA)` pairs
              **directly from the LexCW API** instead of a FLEx CSV export, trains the custom
              `G2PModel` (CPU-capable), and runs pronunciation anomaly detection, writing a report.
            - **LexCW data source:** `GET /api/entries/` (paginated `page`/`per_page`), auth via
              `Authorization: Bearer sw_...` API key + `project_id`. Headword is derived from
              `lexical_unit` (prefer `en`), IPA from `pronunciations['seh-fonipa']`.
            - **Scope of this change:** training script + anomaly detection only (published in
              `scripts/`). flask-app-side inference wiring ("Predict IPA" button consuming the
              artifact) is deferred to a later step.
            - **Published artifacts:** `scripts/ipa_training/` — `lexcw_client.py` (LexCW API
              extractor, stdlib-only), `g2p/` (adapted model/tokenizer/preprocessor/trainer/
              generator/anomaly_detector), `train_ipa_model.py` (CLI), `tests/`, `README.md`.
            - **Caveat:** the G2P IPA validator in `g2p/preprocessor.py` rejects combining marks
              (affricate tie-bars, nasal tilde, palatalization `ʲ`); such pairs are filtered
              before training. Feed IPA without combining marks.
        *   **Requirements**: `3.2.4`, `3.5.1`, `8.2.1`, `18.2`

3.  [x] **AI-Augmented Workflows**
    *   This epic covers the implementation of AI-augmented workflows.

    3.1. [x] **Content Review Workbench**
        *   Build a workbench for reviewing AI-generated content.
        *   Implemented: Interactive proofreading from entry form (`btn-ai-proofread`). Results panel shows issues with severity, field, message, and suggestions. Batch proofreading endpoint processes multiple entries at once.
        *   **Requirements**: `3.2.2`, `18.2`

    3.2. [ ] **Quality Control Automation**
        *   Implement a system for automatically checking the quality of the dictionary data.
        *   **Requirements**: `3.2.2`, `17.3.2`, `18.2`

4.  [ ] **Advanced Linguistic Analysis**
    *   This epic covers the implementation of advanced linguistic analysis features.

    4.1. [ ] **Semantic Relationship Management**
        *   Build a system for managing semantic relationships between entries.
        *   **Requirements**: `3.2.2`, `13.3.2`, `18.2`

    4.2. [ ] **Example-Sense Association**
        *   Implement a system for automatically associating examples with the correct sense.
        *   **Requirements**: `3.2.4`, `11.3`, `18.2`


## AI Integration — Implemented Components

### Architecture
```
Entry Form UI → AIServiceUI (JS) → /api/ai/proofread|draft|batch-proofread
                                   → AIService (Python) → OpenAI API
                                   → Entry ↔ YAML serializer
```

### Files Created
| File | Purpose |
|------|---------|
| `app/services/ai_service.py` | Core: entry→YAML serializer, OpenAI chat client, proofread/draft/batch methods, prompt template CRUD |
| `app/api/ai_api.py` | 7 REST endpoints: proofread, draft, batch-proofread, prompt-template CRUD, models list |
| `config/prompt_templates.json` | 4 default prompt templates (proofreading-default, proofreading-strict, drafting-default, drafting-quick) |
| `app/static/js/ai-service.js` | Frontend: AIServiceUI class with proofread button, draft modal, result display |
| `app/templates/entry_form_partials/_ai_actions.html` | AI assistant card in entry form with proofread + draft buttons |

### Files Modified
| File | Change |
|------|--------|
| `app/__init__.py` | Registered `ai_bp` blueprint, bound `AIService` in injector |
| `app/models/project_settings.py` | Added `openai_api_key` and `ai_model` columns for BYOK |
| `app/templates/entry_form.html` | Included `_ai_actions.html` partial, loaded `ai-service.js` |
| `app/static/js/entry/entry-form-init.js` | Initialize `AIServiceUI` |

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/ai/proofread` | Proofread a single entry |
| POST | `/api/ai/draft` | Draft a new entry from description |
| POST | `/api/ai/batch-proofread` | Batch proofread multiple entries |
| GET | `/api/ai/prompt-templates` | List available prompt templates |
| POST | `/api/ai/prompt-templates` | Create/update a prompt template |
| DELETE | `/api/ai/prompt-templates/{id}` | Delete a prompt template |
| GET | `/api/ai/models` | List available AI models |

### YAML Entry Format
Entries are serialized to human-readable YAML with section markers (`# ====== ENTRY: ... ======`), field labels (`# --- Lexical Unit ---`), and proper nesting. The YAML is round-trippable: `yaml_to_entry(entry_to_yaml(data))` preserves data structure.

### Prompt Customization
Prompt templates are stored in `config/prompt_templates.json` and editable via API. Each template has:
- `system_prompt` — LLM role instructions
- `user_prompt_template` — Task template with `{entry_yaml}` (proofread) or `{description}` (draft) placeholders
- Default templates for proofreading (standard + strict academic) and drafting (full + quick)

## Future: Auto-generated IPA Dictionaries

Instead of requiring linguists to manually create Hunspell `.dic` files for IPA validation, the system could auto-generate them from the dictionary corpus itself:

1. **Extract** all pronunciation values from BaseX (`//pronunciation/form/text`)
2. **Tokenize** into character n-grams (unigrams for allowed characters, bigrams/trigrams for valid sequences like `tʃ`, `dʒ`, `aʊ`)
3. **Filter** by frequency threshold to exclude rare/erroneous sequences
4. **Generate** a `.dic` file from surviving n-grams, with `/X` flags (no affix rules)

This follows László Németh's approach for bootstrapping Hunspell dictionaries for languages without existing resources. The generated dictionary would then be uploadable in Settings → IPA Dictionary and used by R4.1.2 for per-project character validation.
