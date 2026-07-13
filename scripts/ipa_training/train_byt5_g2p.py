#!/usr/bin/env python3
# encoding: UTF-8
"""
Train a ByT5 G2P model to generate high-quality IPA from headwords.

Unlike the tiny, CPU-only custom ``G2PModel`` (``train_ipa_model.py``), which is
used for lightweight *anomaly detection*, ByT5 is a pretrained
sequence-to-sequence transformer that produces much higher-quality IPA. It is
intended for GPU/offline training (e.g. Colab). The resulting HuggingFace
model is then deployed on the server for runtime IPA *drafting* (see
``app/services/ipa_byt5_service.py``).

The fine-tuned model is saved as a HuggingFace model directory named
``ipa_byt5_<writing-system>`` (e.g. ``ipa_byt5_seh-fonipa``). Copy that whole
directory into the application's ``instance/ipa_models/`` (the same
discoverability directory used by the anomaly detector) to enable drafting.

Usage:
    # Train from a live LexCW instance:
    python train_byt5_g2p.py \
        --base-url http://localhost:5000 --api-key sw_xxxx --project-id 1 \
        --output-dir ./byt5_ipa_model

    # Train from a previously exported pairs file:
    python train_byt5_g2p.py --input pairs.json --output-dir ./byt5_ipa_model
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Make sibling modules importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexcw_client import LexCWClient, pairs_to_training_data  # noqa: E402


def build_model_name(default: str = "google/byt5-small") -> str:
    return default


def train(
    training_data: List[Tuple[str, str]],
    model_name: str,
    output_dir: Path,
    ipa_ws: str,
    source_prefix: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    max_samples: int,
    num_beams: int,
    optim: str = "adafactor",
) -> Path:
    """Fine-tune a ByT5 model on (headword, IPA) pairs.

    Returns the path to the saved HuggingFace model directory.
    """
    import torch
    import numpy as np
    from datasets import Dataset
    from transformers import (  # noqa: F401
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        Seq2SeqTrainingArguments,
        Seq2SeqTrainer,
        DataCollatorForSeq2Seq,
        EarlyStoppingCallback,
    )

    if max_samples and max_samples > 0:
        training_data = training_data[:max_samples]

    sources = [(source_prefix + h) for h, _ in training_data]
    targets = [ipa for _, ipa in training_data]

    dataset = Dataset.from_dict({"source": sources, "target": targets})
    dataset = dataset.train_test_split(test_size=0.05, seed=42)

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    # ByT5 is byte-level: sequence length = UTF-8 bytes + 1 (</s>). Size the
    # budget from the actual data instead of a fixed 128 — padding is pure
    # wasted compute here.
    max_len = min(
        128,
        max(
            max(len(s.encode("utf-8")) for s in sources),
            max(len(t.encode("utf-8")) for t in targets),
        ) + 2,
    )
    print(f"Max sequence length (bytes): {max_len}")

    # Ampere+ GPUs: bf16 is stable for T5-family models; fp16 is not (NaN
    # losses), so it is never used. tf32 speeds up any remaining fp32 matmuls.
    use_bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

    def preprocess(batch):
        model_inputs = tokenizer(
            batch["source"], max_length=max_len, truncation=True,
        )
        labels = tokenizer(
            text_target=batch["target"], max_length=max_len, truncation=True,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized = dataset.map(
        preprocess, batched=True, remove_columns=["source", "target"],
    )

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)

    # Eval uses loss only (predict_with_generate would run autoregressive
    # decoding over the whole eval split every epoch — by far the slowest part
    # of the old configuration). Sample generations run once after training.
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        optim=optim,
        warmup_ratio=0.05,
        weight_decay=0.01,
        logging_steps=100,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        save_only_model=True,
        predict_with_generate=False,
        bf16=use_bf16,
        fp16=False,
        group_by_length=True,
        dataloader_num_workers=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        data_collator=data_collator,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    print(f"Training on {len(tokenized['train'])} examples, "
          f"eval on {len(tokenized['test'])}")
    trainer.train()

    # Greedy sample check (no gradients).
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    sample = sources[0]
    with torch.no_grad():
        ids = tokenizer(sample, return_tensors="pt").to(device)
        generated = model.generate(
            **ids, num_beams=num_beams, max_length=max_len, early_stopping=True,
        )
        pred = tokenizer.decode(generated[0], skip_special_tokens=True)
    print(f"Sample: '{sample}' -> '{pred}'")

    out_dir = output_dir / f"ipa_byt5_{ipa_ws}"
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))

    metadata = {
        "ipa_writing_system": ipa_ws,
        "base_model": model_name,
        "source_prefix": source_prefix,
        "task": "grapheme-to-phoneme (headword -> IPA)",
    }
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    print(f"ByT5 model written to: {out_dir}")
    return out_dir


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a ByT5 IPA (G2P) model")
    parser.add_argument("--base-url", help="LexCW base URL (e.g. http://localhost:5000)")
    parser.add_argument("--api-key", help="LexCW API key (Bearer sw_...)")
    parser.add_argument("--project-id", type=int, help="LexCW project id")
    parser.add_argument("--ipa-ws", default="seh-fonipa", help="IPA writing system code")
    parser.add_argument("--input", help="Load pairs from a JSON file instead of the API")
    parser.add_argument("--model-name", default="google/byt5-small",
                        help="Base ByT5 model (HuggingFace hub id or local path)")
    parser.add_argument("--source-prefix", default="",
                        help="Optional text prefixed to each headword at train/eval time")
    parser.add_argument("--output-dir", default="./byt5_ipa_model", help="Output directory")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Training batch size")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--max-samples", type=int, default=0,
                        help="Cap training pairs (0 = use all)")
    parser.add_argument("--num-beams", type=int, default=4,
                        help="Beams for the sample/eval generation")
    parser.add_argument("--max-pair-bytes", type=int, default=64,
                        help="Drop pairs whose headword or IPA exceeds this "
                             "many UTF-8 bytes (0 = keep all)")
    parser.add_argument("--optim", default="adafactor",
                        help="Optimizer (adafactor saves ~2.4 GB of state vs "
                             "adamw_torch on byt5-small; T5 was pretrained with it)")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.input:
        pairs = LexCWClient.load_pairs_from_file(args.input)
    elif args.base_url:
        client = LexCWClient(
            base_url=args.base_url, api_key=args.api_key,
            project_id=args.project_id, ipa_writing_system=args.ipa_ws,
        )
        pairs = client.fetch_pairs()
    else:
        print("ERROR: provide --input <pairs.json> or --base-url <url> [--api-key ...]")
        return 2

    print(f"Loaded {len(pairs)} (headword, IPA) pairs")
    training_data = [(h, ipa) for h, ipa in pairs_to_training_data(pairs) if h and ipa]
    if args.max_pair_bytes > 0:
        # Byte-length outliers set the padded sequence budget for the whole
        # run; dropping the long tail (<1% of pairs) is much cheaper than
        # training with a budget sized for the longest entry.
        before = len(training_data)
        training_data = [
            (h, ipa) for h, ipa in training_data
            if len(h.encode("utf-8")) <= args.max_pair_bytes
            and len(ipa.encode("utf-8")) <= args.max_pair_bytes
        ]
        print(f"Length filter (<= {args.max_pair_bytes} bytes): "
              f"dropped {before - len(training_data)} pairs")
    print(f"Usable training pairs after filtering: {len(training_data)}")

    if len(training_data) < 10:
        print(f"ERROR: need at least 10 pairs, got {len(training_data)}")
        return 2

    train(
        training_data=training_data,
        model_name=args.model_name,
        output_dir=output_dir,
        ipa_ws=args.ipa_ws,
        source_prefix=args.source_prefix,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_samples=args.max_samples,
        num_beams=args.num_beams,
        optim=args.optim,
    )
    print(f"Done. Copy '{output_dir / ('ipa_byt5_' + args.ipa_ws)}' into the "
          f"application's instance/ipa_models/ directory to enable IPA drafting.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
