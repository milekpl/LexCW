#!/usr/bin/env python3
"""Fine-tune byT5 for G2P on (headword, POS, IPA) triples.

The point of the exercise. The previous model was trained on (headword, IPA) pairs, so
for every heterophonic homograph it was shown one input with two different targets —
*separate* as both ˈseprət and ˈsepəreɪt — and asked to learn both. It cannot. Worse, it
never sees the grammatical class at all, so it cannot represent the noun/verb stress
alternation that governs a whole productive class of English words (ˈrecord/reˈcord,
ˈpermit/perˈmit, ˈconduct/conˈduct) — including the many words where only one reading is
recorded and no contradiction is visible in the data.

Input format is `<POS> headword`, e.g. `<VERB> separate` -> `ˈsepəreɪt`.

The headline metric is the **homograph split**: headwords carrying more than one POS with
genuinely different pronunciations (~350). A pair-trained model is at chance there by
construction. If POS conditioning is doing anything at all, it shows up here. Those
headwords are held out of training *entirely* (all their rows), so the number is real and
not memorisation.

    python scripts/ipa_training/train_byt5_pos.py --data triples.json

    # sanity-check a trained model without the app:
    python scripts/ipa_training/train_byt5_pos.py --predict byt5_ipa_model/ipa_byt5_seh-fonipa \
        --words "record:NOUN" "record:VERB" "separate:ADJ" "separate:VERB"

NOTE FOR SERVING: `IPAByT5Service` currently does `text = source_prefix + headword`, i.e. a
*constant* prefix. This model needs a *per-request* prefix (`<NOUN> `), so `draft_ipa()`
must take a `pos` argument and build `f"<{pos}> {headword}"`. The metadata written below
records `input_format` so the service can tell the two model generations apart.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

DEFAULT_MODEL = "google/byt5-small"
IPA_WS = "seh-fonipa"


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

def source_text(headword: str, pos: str) -> str:
    return f"<{pos}> {headword}"


def load_triples(path: str) -> List[dict]:
    rows = json.load(open(path, encoding="utf-8"))
    return [
        r for r in rows
        if r.get("headword", "").strip() and r.get("ipa", "").strip() and r.get("pos")
    ]


def homograph_headwords(rows: List[dict]) -> set:
    """Headwords where POS genuinely separates different pronunciations."""
    by_word: Dict[str, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for r in rows:
        by_word[r["headword"]][r["pos"]].add(r["ipa"])

    words = set()
    for headword, by_pos in by_word.items():
        if len(by_pos) < 2:
            continue
        readings = [frozenset(v) for v in by_pos.values()]
        if any(a != b for a in readings for b in readings):
            words.add(headword)
    return words


def split_data(
    rows: List[dict], seed: int, homograph_train_frac: float = 0.80,
) -> Tuple[List[dict], List[dict], List[dict]]:
    """train / val / homograph-eval, split by *headword* so nothing leaks across.

    Homograph headwords are the only source of POS→stress alternation.  Holding
    them all out means the model never sees the pattern during training — it has
    to zero-shot the stress rule.  Splitting them lets the model learn from ~80%
    while measuring genuine generalisation on the held-out ~20%.
    """
    homographs = homograph_headwords(rows)
    rng = random.Random(seed)

    # ---- Homographs: split by headword -----------------------------------
    homograph_words = sorted(homographs)
    rng.shuffle(homograph_words)
    cut_hom = max(int(len(homograph_words) * homograph_train_frac), 1)
    train_hom_words = set(homograph_words[:cut_hom])
    homograph_eval_rows = [
        r for r in rows
        if r["headword"] in homographs and r["headword"] not in train_hom_words
    ]

    # ---- Non-homographs: split 98/2 --------------------------------------
    rest = [r for r in rows if r["headword"] not in homographs]
    words = sorted({r["headword"] for r in rest})
    rng.shuffle(words)
    cut = int(len(words) * 0.98)
    train_words = set(words[:cut])

    train = [r for r in rest if r["headword"] in train_words]
    val = [r for r in rest if r["headword"] not in train_words]

    # Add homograph training rows
    train += [r for r in rows if r["headword"] in train_hom_words]

    return train, val, homograph_eval_rows


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def edit_distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def cer(reference: str, hypothesis: str) -> float:
    return edit_distance(reference, hypothesis) / max(len(reference), 1)


def evaluate(model, tokenizer, rows: List[dict], device, max_len: int, batch_size: int = 64):
    """Exact match and CER. A row counts as correct if it matches ANY recorded variant.

    Several pronunciations of the same (headword, POS) are legitimate variants, not
    competing answers — penalising the model for choosing the second one would measure
    nothing useful.
    """
    import torch

    accepted: Dict[Tuple[str, str], set] = defaultdict(set)
    for r in rows:
        accepted[(r["headword"], r["pos"])].add(r["ipa"])

    items = sorted(accepted)
    exact = 0
    total_cer = 0.0
    predictions = []

    model.eval()
    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        sources = [source_text(hw, pos) for hw, pos in batch]
        encoded = tokenizer(sources, return_tensors="pt", padding=True, truncation=True,
                            max_length=max_len).to(device)
        with torch.no_grad():
            generated = model.generate(**encoded, max_length=max_len, num_beams=4,
                                       early_stopping=True)
        decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)

        for (headword, pos), prediction in zip(batch, decoded):
            prediction = prediction.strip()
            gold = accepted[(headword, pos)]
            if prediction in gold:
                exact += 1
            total_cer += min(cer(g, prediction) for g in gold)
            predictions.append((headword, pos, sorted(gold), prediction))

    n = max(len(items), 1)
    return exact / n, total_cer / n, predictions


# --------------------------------------------------------------------------- #
# Predict-only mode
# --------------------------------------------------------------------------- #

def predict(model_dir: str, words: List[str], max_len: int) -> None:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir, local_files_only=True).to(device)
    model.eval()

    for spec in words:
        headword, _, pos = spec.partition(":")
        pos = pos or "NOUN"
        encoded = tokenizer(source_text(headword, pos), return_tensors="pt").to(device)
        with torch.no_grad():
            generated = model.generate(**encoded, max_length=max_len, num_beams=4,
                                       early_stopping=True)
        ipa = tokenizer.decode(generated[0], skip_special_tokens=True).strip()
        print(f"  {headword:<16} {pos:<6} -> {ipa}")


# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="triples.json")
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    parser.add_argument("--output", default="byt5_ipa_model/ipa_byt5_seh-fonipa")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64,
                        help="64 fits the RTX 4060 with adafactor+bf16; larger silently spills VRAM")
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--max-len", type=int, default=64)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--predict", metavar="MODEL_DIR",
                        help="Skip training; generate for --words with an existing model")
    parser.add_argument("--words", nargs="*", default=["record:NOUN", "record:VERB",
                                                       "separate:ADJ", "separate:VERB",
                                                       "permit:NOUN", "permit:VERB"])
    args = parser.parse_args()

    if args.predict:
        predict(args.predict, args.words, args.max_len)
        return

    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
    )

    rows = load_triples(args.data)
    train_rows, val_rows, homograph_rows = split_data(rows, args.seed)

    print(f"triples          : {len(rows):,}")
    print(f"  train          : {len(train_rows):,}")
    print(f"  val            : {len(val_rows):,}")
    print(f"  homograph eval : {len(homograph_rows):,} rows "
          f"({len({r['headword'] for r in homograph_rows}):,} headwords, held out)")
    # How many homograph headwords are in train?
    homographs_all = homograph_headwords(rows)
    hom_train = {r["headword"] for r in train_rows if r["headword"] in homographs_all}
    hom_eval = {r["headword"] for r in homograph_rows}
    print(f"  homographs in train : {len(hom_train)}/{len(homographs_all)} headwords "
          f"({len(hom_train)/max(len(homographs_all),1):.0%})")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model_name).to(device)

    # bf16 on Ampere+ only: fp16 produces NaNs with the T5 family.
    use_bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8

    def encode(batch):
        model_inputs = tokenizer(batch["source"], max_length=args.max_len, truncation=True)
        model_inputs["labels"] = tokenizer(
            text_target=batch["target"], max_length=args.max_len, truncation=True
        )["input_ids"]
        return model_inputs

    def to_dataset(rows_):
        return Dataset.from_dict({
            "source": [source_text(r["headword"], r["pos"]) for r in rows_],
            "target": [r["ipa"] for r in rows_],
        }).map(encode, batched=True, remove_columns=["source", "target"])

    training_args = Seq2SeqTrainingArguments(
        output_dir="byt5_ipa_model",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        optim="adafactor",          # AdamW's optimiser state does not fit alongside this
        bf16=use_bf16,
        logging_steps=200,
        save_strategy="no",
        report_to=[],
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=to_dataset(train_rows),
        eval_dataset=to_dataset(val_rows),
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model, padding=True),
    )
    trainer.train()

    # ---- The numbers that matter ------------------------------------------ #
    print()
    print("evaluating…")
    val_exact, val_cer, _ = evaluate(model, tokenizer, val_rows, device, args.max_len)
    print(f"  held-out words   exact {val_exact:6.1%}   CER {val_cer:.4f}")

    hom_exact, hom_cer, hom_preds = evaluate(model, tokenizer, homograph_rows, device, args.max_len)
    print(f"  HOMOGRAPHS       exact {hom_exact:6.1%}   CER {hom_cer:.4f}   <- the headline")
    print()
    print("  (a pair-trained model is at chance here: it sees one input, two targets)")
    print()
    for headword, pos, gold, prediction in hom_preds[:15]:
        mark = "ok  " if prediction in gold else "MISS"
        print(f"    {mark} {headword:<14} {pos:<6} -> {prediction:<18} gold: {', '.join(gold)}")

    # ---- Save in the layout the service expects --------------------------- #
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out, safe_serialization=False)
    tokenizer.save_pretrained(out)

    (out / "metadata.json").write_text(json.dumps({
        "ipa_writing_system": IPA_WS,
        "base_model": args.model_name,
        "task": "grapheme-to-phoneme (headword + POS -> IPA)",
        # The old model took a constant source_prefix. This one needs the POS per request,
        # so the service must build the input itself; source_prefix stays empty to make a
        # service that ignores input_format fail loudly rather than silently mispronounce.
        "source_prefix": "",
        "input_format": "<POS> headword",
        "pos_tags": sorted({r["pos"] for r in rows}),
        "metrics": {
            "val_exact": round(val_exact, 4),
            "val_cer": round(val_cer, 4),
            "homograph_exact": round(hom_exact, 4),
            "homograph_cer": round(hom_cer, 4),
        },
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"saved -> {out}")
    print("Deploy: cp -r {out} instance/ipa_models/   (then restart the app)".format(out=out))


if __name__ == "__main__":
    main()
