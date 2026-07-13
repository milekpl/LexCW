# IPA Pronunciation Models: Anomaly Detection & ByT5 Drafting

This application ships **two machine-learning models** for IPA pronunciation —
each serves a different purpose and runs on different hardware.

| Model | Purpose | Architecture | Training hardware | 
|-------|---------|-------------|-------------------|
| **G2PModel** (anomaly) | Flag suspicious IPA during validation | Custom tiny encoder-decoder transformer (~256 hidden, 4 layers) | CPU (on-server) |
| **ByT5** (drafting) | Propose high-quality IPA from a headword | HuggingFace `google/byt5-small` (pretrained, 300M params) | GPU (Colab / offline) |

Both models live in the same server-side directory (`instance/ipa_models/`),
use the same strict writing-system matching, and are **fail-open** — if no
model is deployed, the feature is simply unavailable (it never blocks saving).

---

## Anomaly Detection (R4.3.1)

Validation rule **R4.3.1** (category `pronunciation`, priority `warning`) uses the
trained G2P model to flag IPA pronunciations that diverge sharply from the
pronunciation the model predicts for the headword.

### How it works

For each entry being validated:

1. The **headword** (`lexical_unit['en']`) and the **IPA**
   (`pronunciations['seh-fonipa']`) are read.
2. The **parenthetical IPA notation is decompressed** — e.g.
   `ˈskɒtɪˌsɪz(ə)m` becomes `ˈskɒtɪˌsɪzm` (and `ˈskɒtɪˌsɪzəm`). Every
   expansion is compared against the model's prediction, and the best-matching
   one is used, so optional segments never cause false positives.
3. The model predicts the expected IPA from the headword and compares it to the
   stored form. If the confidence (1 − phoneme-error-rate) is below the
   threshold, the pronunciation is flagged as an **anomaly**.

The rule is a **warning**, not a blocking error — it assists editors, it does
not prevent saving.

### Training

The G2PModel is trained by the published, server-side script:

```bash
python scripts/ipa_training/train_ipa_model.py \
    --base-url http://localhost:5000 \
    --api-key sw_xxxx \
    --project-id 1
```

See [`scripts/ipa_training/README.md`](../scripts/ipa_training/README.md) for
the full reference.

### Output

Training produces two **sidecar files** in `--output-dir`:

| File | Contents |
|------|----------|
| `ipa_anomaly_<ws>.pt` | Model **weights only** (tensors). |
| `ipa_anomaly_<ws>.json` | Metadata: `ipa_writing_system`, `model_config`, `grapheme_vocab`, `phoneme_vocab`. |

The `.pt` holds tensors **only**, so it is loaded with PyTorch's
`weights_only=True` and **cannot execute arbitrary code** on load. All model
structure and vocabularies live in the plain-text `.json`.

---

## ByT5 IPA Drafting

Anomaly detection only *flags* suspicious IPA. To actually **propose** a
high-quality pronunciation, fine-tune a pretrained **ByT5** model and deploy it
the same way.

### How it works

1. An editor clicks **Draft** next to the IPA field in the entry form (or sends
   `POST /api/pronunciation/draft`).
2. The server sends the headword to the fine-tuned ByT5 model.
3. The model returns 1–5 candidate IPA pronunciations.
4. The editor accepts a candidate, which fills the IPA field.

The endpoint returns `{"available": false}` with a 200 status if no model is
deployed — it never errors.

### Training (GPU / Colab)

ByT5 is too large for CPU training. Use the Colab notebook at
[`ipa_byt5_training.ipynb`](../ipa_byt5_training.ipynb):

1. Export pairs from your running LexCW instance:
   ```bash
   python scripts/ipa_training/export_ipa_pairs.py \
       --base-url http://localhost:5000 \
       --project-id 1 \
       --output pairs.json
   ```
2. Upload `ipa_byt5_training.ipynb` and `pairs.json` to
   [Google Colab](https://colab.research.google.com/).
3. Run the notebook — it fine-tunes `google/byt5-small` and downloads a
   zip of the model directory.
4. Unzip into the application's model directory:
   ```bash
   unzip ipa_byt5_seh-fonipa.zip -d instance/ipa_models/
   ```

The notebook is self-contained — the training script is embedded inline, no
separate files needed.

Alternatively, run from the command line on a GPU machine:

```bash
python scripts/ipa_training/train_byt5_g2p.py \
    --input pairs.json \
    --output-dir ./byt5_model
```

### Output

Training produces a HuggingFace model directory named `ipa_byt5_<ws>/`:

```
ipa_byt5_seh-fonipa/
├── config.json
├── pytorch_model.bin
├── tokenizer.json
├── tokenizer_config.json
├── special_tokens_map.json
└── metadata.json      # {ipa_writing_system, base_model, source_prefix}
```

Copy the whole directory into `instance/ipa_models/` for auto-discovery.

### Endpoint

```
POST /api/pronunciation/draft
Authorization: Bearer <api-key>

{"headword": "scotsism", "writing_system": "seh-fonipa", "num_candidates": 3}
```

Response:

```json
{"available": true, "writing_system": "seh-fonipa", "candidates": ["ˈskɒtɪˌsɪzm", ...]}
```

Requires `pronunciation:read` scope (or a login session).

---

## Deploying Models (server-side only)

Users never choose where the model lives. Discovery is entirely server-side:

1. **Train** the model (see sections above).
2. **Copy the artifact** into the application's instance model directory:

   **Anomaly model** (sidecar bundle):
   ```bash
   cp ipa_anomaly_seh-fonipa.pt ipa_anomaly_seh-fonipa.json \
      instance/ipa_models/
   ```

   **ByT5 model** (HuggingFace directory):
   ```bash
   cp -r ipa_byt5_seh-fonipa instance/ipa_models/
   ```

3. (Optional) Point elsewhere with the `IPA_MODEL_DIR` environment variable.
   This is an **admin/server** setting, never exposed through the API or UI.

At validation/draft time the service scans `instance/ipa_models/` for the
relevant prefix (`ipa_anomaly_*` or `ipa_byt5_*`), reads the companion
metadata, and selects the bundle whose `ipa_writing_system` matches the entry's
IPA writing system. If no model matches, the feature is a **no-op** (it never
blocks validation). Multiple writing systems are supported by dropping in one
bundle per system.

### Why this is safe

- **No user-controlled path.** The model location is fixed (or an admin env
  var). A request can never redirect loading to an arbitrary file.
- **Weights-only loading.** The anomaly `.pt` is pure tensors; even a
  maliciously crafted file cannot run code when loaded with
  `weights_only=True`. The ByT5 model is loaded with `local_files_only=True`
  and `trust_remote_code=False` so it never downloads anything or executes
  custom code.
- **Admin-only placement.** Placing a model requires the same server
  credentials an administrator already has — no new privilege surface.
- **Fail-open, not fail-closed.** If a model is missing or mismatched, the
  feature simply does nothing rather than erroring.

---

## Troubleshooting

- *Rule never flags anything, even for obviously wrong IPA.*
  Check that the bundle is in `instance/ipa_models/` (or `IPA_MODEL_DIR`) and
  that its `ipa_writing_system` matches the entry's IPA writing system. A small
  or under-trained model will produce weak predictions; train on more data and
  for more epochs.
- *Low confidence everywhere.*
  The model is under-fitted, or the training pairs contained IPA the
  preprocessor rejected. Review `pairs.json` and the training report.
- *Parenthetical IPA not recognized.*
  Decompression is automatic; ensure the parentheses are balanced
  (`(ə)` not `(ə`).
- *Draft endpoint returns `available: false`.*
  The ByT5 model directory (`ipa_byt5_seh-fonipa/`) is not present in
  `instance/ipa_models/` or its `metadata.json` is missing/invalid.
- *ByT5 candidates are low quality.*
  The model was under-trained. Train for more epochs or with a larger batch
  size on a GPU.
