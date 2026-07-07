# IPA Pronunciation Anomaly Detection

This tutorial explains how the **pronunciation anomaly detection** validation
rule works, how its model is produced, and — importantly — how it is deployed
**securely** on the server.

## What it does

Validation rule **R4.3.1** (category `pronunciation`, priority `warning`) uses a
trained grapheme-to-phoneme (G2P) model to flag IPA pronunciations that diverge
sharply from the pronunciation the model predicts for the headword.

For each entry being validated:

1. The headword (`lexical_unit['en']`) and the IPA
   (`pronunciations['seh-fonipa']`) are read.
2. The **parenthetical IPA notation is decompressed** — e.g.
   `ˈskɒtɪˌsɪz(ə)m` becomes `ˈskɒtɪˌsɪzm` (and `ˈskɒtɪˌsɪzəm`). Every expansion is
   compared against the model's prediction, and the best-matching one is used,
   so optional segments never cause false positives.
3. The model predicts the expected IPA from the headword and compares it to the
   stored form. If the confidence (1 − phoneme-error-rate) is below the
   threshold, the pronunciation is flagged as an **anomaly**.

The rule is a **warning**, not a blocking error — it assists editors, it does
not prevent saving.

## The model is not shipped

The application does **not** contain a pre-trained model. Each deployment
trains its own model on its own dictionary, so the "expected" pronunciation
reflects the project's actual conventions.

Training is done by the published, server-side script in
`scripts/ipa_training/train_ipa_model.py`. See
[`scripts/ipa_training/README.md`](../scripts/ipa_training/README.md) for the
full reference.

## Training produces a self-contained sidecar bundle

After training, the script writes **two** files into `--output-dir`:

| File | Contents |
|------|----------|
| `ipa_anomaly_<ws>.pt` | Model **weights only** (tensors). |
| `ipa_anomaly_<ws>.json` | Metadata: `ipa_writing_system`, `model_config`, `grapheme_vocab`, `phoneme_vocab`. |

`<ws>` is the IPA writing system (default `seh-fonipa`). The `.pt` holds tensors
**only**, so it is loaded with PyTorch's `weights_only=True` and **cannot
execute arbitrary code** on load. All model structure and vocabularies live in
the plain-text `.json`.

## Deploying the model (server-side only)

Users never choose where the model lives. Discovery is entirely server-side:

1. **Train** the model (see the training README).
2. **Copy the two sidecar files** into the application's instance model
   directory:

   ```bash
   cp ipa_anomaly_seh-fonipa.pt ipa_anomaly_seh-fonipa.json \
      /path/to/app/instance/ipa_models/
   ```

   The directory `instance/ipa_models/` is the canonical discoverability
   location. It is not served over the web and is writable only by the server /
   administrator.

3. (Optional) Point elsewhere with the `IPA_MODEL_DIR` environment variable.
   This is an **admin/server** setting, never exposed through the API or UI.

At validation time the rule scans `instance/ipa_models/` for every
`ipa_anomaly_*.pt`, reads the companion `.json`, and selects the bundle whose
`ipa_writing_system` matches the entry's IPA writing system. If no model
matches, the rule is a **no-op** (it never blocks validation). Multiple
languages are supported by dropping in one bundle per writing system.

## Why this is safe

- **No user-controlled path.** The model location is fixed (or an admin env
  var). A request can never redirect loading to an arbitrary file.
- **Weights-only loading.** The `.pt` is pure tensors; even a maliciously
  crafted file cannot run code when loaded with `weights_only=True`.
- **Admin-only placement.** Placing a model requires the same server
  credentials an administrator already has — no new privilege surface.
- **Fail-open, not fail-closed.** If a model is missing or mismatched, the rule
  simply does nothing rather than erroring.

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
