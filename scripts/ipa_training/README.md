# LexCW IPA Training Script (G2P)

This directory contains a **published, server-side training script** for the
LexCW **English IPA** (grapheme-to-phoneme) model and pronunciation anomaly
detector. It trains an **English-headword → English-pronunciation** mapping:
the headword is read from `lexical_unit['en']` and the IPA from
`pronunciations['seh-fonipa']`.

It trains directly from the LexCW API
(`scripts/ipa_training/lexcw_client.py`), pulling `(headword, IPA)` pairs
without any third-party export step, so you can train on your live dictionary.

## What it does

1. **Extract** `(headword, IPA)` pairs from LexCW via `GET /api/entries/`
   (headword is read from `lexical_unit`, IPA from
   `pronunciations['seh-fonipa']`).
2. **Train** a small encoder-decoder transformer (`G2PModel`) that predicts IPA
   from a headword. The model is deliberately tiny (~256 hidden, 4 layers) and
   **trains on CPU** — no GPU required.
3. **Detect anomalous pronunciations** with `G2PAnomalyDetector` (predicts the
   expected IPA and flags stored pronunciations whose phoneme-error-rate
   confidence falls below a threshold), writing `anomaly_report.json` /
   `anomaly_report.md`.

> This script targets a deliberately small, **CPU-capable** custom
> `G2PModel` so it can be trained on the server without a GPU.

## Requirements

```
pip install torch transformers tqdm
```

(`torch` is always required; `transformers` is needed only for training, not
for loading a trained checkpoint.)

## Usage

Train from a live LexCW instance:

```bash
python train_ipa_model.py \
    --base-url http://localhost:5000 \
    --api-key sw_xxxxxxxxxxxxxxxx \
    --project-id 1 \
    --output-dir ./ipa_model
```

Train from a previously exported pairs file (no API call):

```bash
python train_ipa_model.py --input pairs.json --output-dir ./ipa_model
```

Skip anomaly detection:

```bash
python train_ipa_model.py --input pairs.json --no-detect
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--base-url` | – | LexCW base URL (e.g. `http://localhost:5000`). |
| `--api-key` | – | LexCW API key sent as `Authorization: Bearer sw_...`. |
| `--project-id` | – | Project whose entries are read. |
| `--ipa-ws` | `seh-fonipa` | Writing-system code holding IPA. |
| `--input` | – | Load pairs from a JSON file instead of the API. |
| `--output-dir` | `./ipa_model` | Where artifacts are written. |
| `--epochs` | `10` | Training epochs. |
| `--batch-size` | `8` | Training batch size. |
| `--min-samples` | `50` | Minimum number of pairs required to train. |
| `--confidence-threshold` | `0.5` | Anomaly confidence threshold (0–1). |
| `--no-detect` | – | Skip pronunciation anomaly detection. |

## Outputs (in `--output-dir`)

- `ipa_anomaly_<ws>.pt` — **self-contained model weights only** (loaded with
  `weights_only=True`, so it cannot execute arbitrary code). `<ws>` is the IPA
  writing system from `--ipa-ws` (default `seh-fonipa`).
- `ipa_anomaly_<ws>.json` — companion metadata (`ipa_writing_system`,
  `model_config`, `grapheme_vocab`, `phoneme_vocab`).
- `checkpoints/best_model.pt`, `grapheme_vocab.json`, `phoneme_vocab.json`,
  `model_config.json` — legacy four-file layout (kept for manual loading).
- `pairs.json` — the exact pairs used (reproducibility).
- `anomaly_report.json` / `anomaly_report.md` — anomaly detection results.

## Deploying the model for live anomaly detection

The application loads the trained model **automatically** — there is no need to
point anything at it from the UI, and **users cannot choose the model path**.
All discovery is server-side:

1. Copy **only** the two sidecar files produced above into the application's
   instance model directory:

   ```bash
   # From the training --output-dir:
   cp ipa_anomaly_seh-fonipa.pt ipa_anomaly_seh-fonipa.json \
      /path/to/app/instance/ipa_models/
   ```

   (If you prefer a different directory, set the `IPA_MODEL_DIR` environment
   variable to it. This is an **admin/server** setting, never user-facing.)

2. The validation rule **R4.3.1** (pronunciation anomaly detection) discovers
   every `ipa_anomaly_*.pt` in that directory, reads the companion `.json`, and
   uses the bundle whose `ipa_writing_system` matches the entry's IPA writing
   system. Nothing is loaded if no model matches.

3. Parenthetical IPA notation (e.g. `ˈskɒtɪˌsɪz(ə)m`) is decompressed
   automatically before comparison, so optional segments never cause false
   positives.

> **Security:** the `.pt` contains tensors only and is loaded with
> `weights_only=True`; the config/vocab live in a plain `.json`. Because the
> path is never user-controlled and the model is loaded defensively, placing a
> model requires only the same server credentials an administrator already
> has. A full tutorial is available in
> [`docs/IPA_ANOMALY_DETECTION.md`](../docs/IPA_ANOMALY_DETECTION.md).

## High-quality IPA with ByT5 (drafting)

For much better IPA than the tiny CPU model, fine-tune a pretrained
**ByT5** sequence-to-sequence model with
[`train_byt5_g2p.py`](train_byt5_g2p.py). This is the GPU/offline path; the
resulting HuggingFace model is deployed on the server and used to **draft**
high-quality IPA for a headword (not just flag anomalies).

The script saves a model directory named `ipa_byt5_<ws>/` (containing the
HuggingFace weights, tokenizer, and a `metadata.json`). Copy that whole
directory into `instance/ipa_models/` on the server, and the application's
`IPAByT5Service` discovers it automatically and exposes drafting via
`POST /api/pronunciation/draft`.

See [`docs/IPA_ANOMALY_DETECTION.md`](../docs/IPA_ANOMALY_DETECTION.md) for the
deployment and security model (discovery is server-side only; models load with
`local_files_only=True` and `trust_remote_code=False`).

## Loading a trained model elsewhere

```python
from g2p import G2PAnomalyDetector, create_anomaly_detector_from_bundle

detector = create_anomaly_detector_from_bundle(
    "ipa_anomaly_seh-fonipa.pt", "ipa_anomaly_seh-fonipa.json"
)
```

For the legacy four-file layout:

```python
from g2p import G2PModel, G2PAnomalyDetector, create_anomaly_detector
from g2p import G2PTokenizer

tokenizer = G2PTokenizer.load_vocab("grapheme_vocab.json", "phoneme_vocab.json")
import json
config = ModelConfig(**json.load(open("model_config.json")))
detector = create_anomaly_detector("checkpoints/best_model.pt", config, tokenizer)
```

## Tests

```bash
python -m pytest scripts/ipa_training/tests/ -q
```

(Requires `torch` + `transformers`.)

## Known limitations

- The IPA validator in `g2p/preprocessor.py` rejects **combining marks**
  (e.g. affricate tie-bars `t͡ʃ`, nasal tilde, palatalization `ʲ`). Pairs whose
  IPA contains such marks are filtered out by `G2PDataset` before training.
  Feed the script IPA without combining marks if your data uses them.
- Training is intentionally lightweight; for high-accuracy IPA generation on
  large corpora, use the ByT5 path on a GPU instead.
