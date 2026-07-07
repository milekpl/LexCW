#!/usr/bin/env python3
# encoding: UTF-8
"""
Train the LexCW IPA (G2P) model and detect anomalous pronunciations.

This is the published, server-side training entry point. It replaces the SIL
FieldWorks extraction step with a direct pull from the LexCW API, trains the
small CPU-capable ``G2PModel`` (see ``g2p/``), and optionally runs the
dual-method pronunciation anomaly detector over the extracted data.

Usage:
    # Train from a live LexCW instance:
    python train_ipa_model.py \
        --base-url http://localhost:5000 \
        --api-key sw_xxxxxxxx \
        --project-id 1 \
        --output-dir ./ipa_model

    # Train from a previously exported pairs file (no API call):
    python train_ipa_model.py --input pairs.json --output-dir ./ipa_model

    # Train without running anomaly detection afterwards:
    python train_ipa_model.py --input pairs.json --no-detect
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Make the sibling modules importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexcw_client import LexCWClient, LexCWPair, pairs_to_training_data  # noqa: E402
from g2p import (  # noqa: E402
    G2PModel,
    ModelConfig,
    G2PTokenizer,
    build_vocab_from_data,
    G2PPreprocessor,
    G2PTrainer,
    TrainingConfig,
    G2PDataset,
    create_anomaly_detector,
)  # noqa: E402


def build_model_and_tokenizer(
    training_data: List[Tuple[str, str]], output_dir: Path
) -> Tuple[G2PModel, G2PTokenizer, ModelConfig]:
    """
    Build vocabulary, tokenizer, and model from training pairs.

    Args:
        training_data: List of ``(grapheme, phoneme)`` tuples.
        output_dir: Directory where vocabularies/config will be persisted.

    Returns:
        Tuple of (model, tokenizer, config).
    """
    grapheme_vocab, phoneme_vocab = build_vocab_from_data(training_data)
    tokenizer = G2PTokenizer(
        grapheme_vocab=grapheme_vocab, phoneme_vocab=phoneme_vocab
    )
    config = ModelConfig(
        grapheme_vocab_size=len(grapheme_vocab),
        phoneme_vocab_size=len(phoneme_vocab),
        pad_token_id=tokenizer.PAD_ID,
        bos_token_id=tokenizer.BOS_ID,
        eos_token_id=tokenizer.EOS_ID,
    )
    model = G2PModel(config)

    tokenizer.save_vocab(
        str(output_dir / "grapheme_vocab.json"),
        str(output_dir / "phoneme_vocab.json"),
    )
    with open(output_dir / "model_config.json", "w", encoding="utf-8") as fh:
        json.dump(config.__dict__, fh, indent=2)

    return model, tokenizer, config


def train(
    training_data: List[Tuple[str, str]],
    model: G2PModel,
    tokenizer: G2PTokenizer,
    output_dir: Path,
    epochs: int,
    batch_size: int,
) -> G2PTrainer:
    """
    Train the G2P model and persist the best checkpoint.

    Args:
        training_data: List of ``(grapheme, phoneme)`` tuples.
        model: Model instance to train.
        tokenizer: Tokenizer instance.
        output_dir: Directory for checkpoints.
        epochs: Number of training epochs.
        batch_size: Training batch size.

    Returns:
        The configured trainer (with ``best_val_loss`` populated).
    """
    preprocessor = G2PPreprocessor()
    train_pairs, val_pairs = _split_train_val(training_data)
    train_dataset = G2PDataset(train_pairs, tokenizer, preprocessor)
    val_dataset = G2PDataset(val_pairs, tokenizer, preprocessor) if val_pairs else None

    train_config = TrainingConfig(
        batch_size=batch_size,
        num_epochs=epochs,
        learning_rate=1e-4,
        output_dir=str(output_dir / "checkpoints"),
        eval_interval=500,
        save_interval=500,
    )
    trainer = G2PTrainer(
        model=model,
        tokenizer=tokenizer,
        config=train_config,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
    )
    trainer.train()
    return trainer


def _split_train_val(
    training_data: List[Tuple[str, str]], val_fraction: float = 0.1
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """
    Split training pairs into train/validation sets (deterministic).

    Args:
        training_data: All ``(grapheme, phoneme)`` tuples.
        val_fraction: Fraction of data to hold out for validation.

    Returns:
        Tuple of (train_pairs, val_pairs).
    """
    if len(training_data) < 10:
        # Too small to split; train on everything, no validation set.
        return training_data, []
    split = max(1, int(len(training_data) * val_fraction))
    return training_data[:-split], training_data[-split:]


def detect_anomalies(
    pairs: List[LexCWPair],
    model_path: Path,
    config: ModelConfig,
    tokenizer: G2PTokenizer,
    confidence_threshold: float,
    output_dir: Path,
) -> dict:
    """
    Run the dual-method pronunciation anomaly detector over extracted pairs.

    Args:
        pairs: Extracted LexCW pairs.
        model_path: Path to the trained checkpoint.
        config: Model configuration.
        tokenizer: Tokenizer instance.
        confidence_threshold: Below this = anomaly (PER-based confidence).
        output_dir: Directory to write the report.

    Returns:
        Detection statistics dictionary.
    """
    detector = create_anomaly_detector(
        str(model_path),
        config,
        tokenizer,
        confidence_threshold=confidence_threshold,
    )
    entries = [
        {"lexeme": p.headword, "ipa": p.ipa, "location": p.pos} for p in pairs
    ]
    results = detector.detect_batch(entries, show_progress=True)
    stats = detector.get_anomaly_stats(results)

    report = {
        "confidence_threshold": confidence_threshold,
        "stats": stats,
        "anomalies": [
            {
                "lexeme": r.lexeme,
                "stored_ipa": r.stored_ipa,
                "predicted_ipa": r.predicted_ipa,
                "confidence_score": round(r.confidence_score, 3),
                "anomaly_type": r.anomaly_type,
            }
            for r in results
            if r.is_anomaly
        ],
    }

    with open(output_dir / "anomaly_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    lines = [
        "# Pronunciation Anomaly Report",
        "",
        f"- Confidence threshold: {confidence_threshold}",
        f"- Total checked: {stats['total_checked']}",
        f"- Anomalies found: {stats['anomalies_found']}",
        f"- Anomaly rate: {stats['anomaly_rate'] * 100:.1f}%",
        "",
        "## Anomalies",
        "",
    ]
    for r in results:
        if r.is_anomaly:
            lines.append(
                f"- **{r.lexeme}**: stored `{r.stored_ipa}` vs predicted "
                f"`{r.predicted_ipa}` (conf={r.confidence_score:.2f}, "
                f"type={r.anomaly_type})"
            )
    with open(output_dir / "anomaly_report.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return report


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Train LexCW IPA (G2P) model")
    parser.add_argument("--base-url", help="LexCW base URL (e.g. http://localhost:5000)")
    parser.add_argument("--api-key", help="LexCW API key (Bearer sw_...)")
    parser.add_argument("--project-id", type=int, help="LexCW project id")
    parser.add_argument(
        "--ipa-ws",
        default="seh-fonipa",
        help="Writing system code holding IPA pronunciations",
    )
    parser.add_argument("--input", help="Load pairs from a JSON file instead of the API")
    parser.add_argument("--output-dir", default="./ipa_model", help="Output directory")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Training batch size")
    parser.add_argument(
        "--min-samples", type=int, default=50, help="Minimum number of pairs required"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Anomaly confidence threshold (0-1)",
    )
    parser.add_argument(
        "--no-detect",
        action="store_true",
        help="Skip the pronunciation anomaly detection step",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    """Entry point. Returns a process exit code."""
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Acquire training pairs.
    if args.input:
        pairs = LexCWClient.load_pairs_from_file(args.input)
        source = args.input
    elif args.base_url:
        client = LexCWClient(
            base_url=args.base_url,
            api_key=args.api_key,
            project_id=args.project_id,
            ipa_writing_system=args.ipa_ws,
        )
        pairs = client.fetch_pairs()
        source = args.base_url
    else:
        print("ERROR: provide --input <pairs.json> or --base-url <url> [--api-key ...]")
        return 2

    print(f"Loaded {len(pairs)} (headword, IPA) pairs from {source}")

    training_data = [(h, ipa) for h, ipa in pairs_to_training_data(pairs) if h and ipa]
    print(f"Usable training pairs after filtering: {len(training_data)}")

    if len(training_data) < args.min_samples:
        print(
            f"ERROR: need at least {args.min_samples} pairs, got {len(training_data)}"
        )
        return 2

    # Persist the raw pairs for reproducibility.
    with open(output_dir / "pairs.json", "w", encoding="utf-8") as fh:
        json.dump(
            [p.__dict__ for p in pairs], fh, ensure_ascii=False, indent=2
        )

    # 2. Build model + tokenizer and train.
    model, tokenizer, config = build_model_and_tokenizer(training_data, output_dir)
    trainer = train(
        training_data, model, tokenizer, output_dir, args.epochs, args.batch_size
    )
    print(f"Training complete. Best val loss: {trainer.best_val_loss:.4f}")

    checkpoint = output_dir / "checkpoints" / "best_model.pt"
    if not checkpoint.exists():
        print("ERROR: training did not produce a checkpoint")
        return 1

    # 3. Optional pronunciation anomaly detection.
    if not args.no_detect:
        report = detect_anomalies(
            pairs,
            checkpoint,
            config,
            tokenizer,
            args.confidence_threshold,
            output_dir,
        )
        print(
            f"Anomaly detection: {report['stats']['anomalies_found']} anomalies "
            f"out of {report['stats']['total_checked']} checked"
        )

    # Emit the self-contained, server-discoverable sidecar bundle
    # (ipa_anomaly_<writing-system>.pt + .json) consumed by the application's
    # IPA anomaly detection validation rule (R4.3.1). Place this bundle in the
    # application's instance/ipa_models/ directory (or set IPA_MODEL_DIR).
    emit_discoverable_bundle(output_dir, args.ipa_ws, model, tokenizer, config)

    print(f"Artifacts written to: {output_dir}")
    return 0


def emit_discoverable_bundle(
    output_dir: Path,
    ipa_ws: str,
    model: G2PModel,
    tokenizer: G2PTokenizer,
    config: ModelConfig,
) -> None:
    """
    Write the self-contained sidecar bundle used by the live application.

    Produces two files in ``output_dir``:
      * ``ipa_anomaly_<ipa_ws>.pt``  -- model weights only (loaded with
        ``weights_only=True``, so it cannot execute arbitrary code).
      * ``ipa_anomaly_<ipa_ws>.json`` -- metadata: the trained writing system,
        model config, and vocabularies.

    The application's ``IPAAnomalyService`` discovers files matching
    ``ipa_anomaly_*.pt`` and selects the one whose ``ipa_writing_system``
    matches the entry's IPA writing system.

    Args:
        output_dir: Directory to write the bundle into.
        ipa_ws: IPA writing system code (e.g. ``seh-fonipa``) used as the
            bundle name suffix and stored in the metadata.
        model: Trained ``G2PModel``.
        tokenizer: Trained ``G2PTokenizer``.
        config: ``ModelConfig``.
    """
    import torch

    safe_ws = ipa_ws.replace(os.sep, "_")
    pt_path = output_dir / f"ipa_anomaly_{safe_ws}.pt"
    json_path = output_dir / f"ipa_anomaly_{safe_ws}.json"

    # Weights only -> safe to load with weights_only=True on the app side.
    torch.save({"model_state_dict": model.state_dict()}, str(pt_path))

    bundle = {
        "ipa_writing_system": ipa_ws,
        "model_config": config.__dict__,
        "grapheme_vocab": tokenizer.grapheme_vocab,
        "phoneme_vocab": tokenizer.phoneme_vocab,
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, indent=2)

    print(f"Discoverable bundle written: {pt_path.name} + {json_path.name}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
