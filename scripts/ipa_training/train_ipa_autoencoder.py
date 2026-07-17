#!/usr/bin/env python3
"""Train an IPA anomaly detector: a POS-conditioned density model over pronunciations.

It flags transcriptions the dictionary would be unlikely to contain. It complements the
byT5 G2P model: byT5 *proposes* a pronunciation from the headword, this *judges* the one
already stored.

The name says "autoencoder" because that is what the reference implementation uses
(flextools-main/FlexTools/Modules/Wielki/g2p/anomaly_detector.py) and what we set out to
improve. Both are implemented here (--model autoencoder|density) because the comparison
is the point, and it did not go the way it was expected to.

WHAT WAS TRIED, AND WHAT THE DATA SAID
--------------------------------------

1.  **Autoencoder with an autoregressive decoder** — the obvious "fix" for the reference
    model, whose decoder broadcasts one latent vector across every timestep and so cannot
    represent order at all. It made things *worse*: teacher forcing hands the decoder the
    ground-truth previous tokens, so it learns to copy its input instead of routing
    anything through the latent. Training loss fell to 0.03 and detection collapsed
    (3% of dropped stress marks). A model that reconstructs everything perfectly
    distinguishes nothing.

2.  **Autoencoder with a bottleneck decoder** (latent + POS + position, no teacher
    forcing) — order-aware without the leak. Still weak: ~4-7% on most corruptions. The
    flaw is inherent to reconstruction: the encoder *sees the string it is judging*, so it
    encodes the anomaly and rebuilds it. Error only rises when the bottleneck is too
    narrow to represent the input, which is a blunt instrument.

3.  **Density model** (--model density, the default) — a POS-conditioned character LM.
    It never sees the string it scores; it must predict each phoneme from the prefix
    alone, so the score is a real conditional density, -log p(IPA | POS). No encoder, no
    copy path. This is the one that works.

SCORING
-------
Two views, because neither alone suffices: dropping a stress mark shifts the likelihood of
the *whole* sequence (a mean sees it; a max does not), while one confused vowel spikes a
*single* position (a max sees it; a mean dilutes it away). Each is ranked against the clean
distribution and the worse of the two is taken, so the combined score is calibrated by
construction. The threshold is fitted on held-out clean data and the false-positive rate is
then measured on a *disjoint* clean split — calibrating and measuring on the same data
would return the target FPR by construction and prove nothing.

DOES POS CONDITIONING HELP? NO — AND THAT IS INFORMATIVE
--------------------------------------------------------
Run --no-pos and the detector is just as good (measured: 49.7% vs 46.1% on moved stress).
POS was expected to catch a *plausible* pronunciation filed under the wrong part of speech
— rɪˈkɔːd stored as the noun. It cannot, and neither can any IPA-only model: both ˈrekɔːd
and rɪˈkɔːd are unremarkable for a noun in general (compare ˈrecord and hoˈtel). The error
is only visible if you know the **headword**, which makes it the byT5 model's job —
generate from (headword, POS) and compare with what is stored. The `wrong_pos_stress` row
below is the standing demonstration: ~1% detected, at chance.

So POS conditioning is essential for **generation** (byT5, where it resolves the homograph
contradictions that made pair-training incoherent) and near-useless for **density**. The
two detectors are complementary, and this one owns phonotactics.

Usage:
    python scripts/ipa_training/train_ipa_autoencoder.py --data triples.json
    python scripts/ipa_training/train_ipa_autoencoder.py --data triples.json --no-pos
    python scripts/ipa_training/train_ipa_autoencoder.py --data triples.json --model autoencoder
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

PAD, BOS, EOS, UNK = 0, 1, 2, 3
SPECIALS = ["<pad>", "<bos>", "<eos>", "<unk>"]

STRESS_MARKS = ["ˈ", "ˌ"]

#: Phonemes that editors actually confuse, so corruptions look like real mistakes rather
#: than random noise (which any model would catch, telling us nothing).
CONFUSABLE = [
    ("ɪ", "iː"), ("æ", "ʌ"), ("ɒ", "ɔː"), ("ə", "ʌ"), ("e", "ɪ"),
    ("uː", "ʊ"), ("ɑː", "æ"), ("ɜː", "ə"), ("s", "z"), ("θ", "ð"),
]


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

class Vocab:
    def __init__(self, chars: List[str]):
        self.itos = SPECIALS + chars
        self.stoi = {ch: i for i, ch in enumerate(self.itos)}

    def __len__(self) -> int:
        return len(self.itos)

    def encode(self, text: str, max_len: int) -> List[int]:
        ids = [BOS] + [self.stoi.get(ch, UNK) for ch in text][: max_len - 2] + [EOS]
        return ids + [PAD] * (max_len - len(ids))

    @classmethod
    def build(cls, texts: List[str], min_count: int = 2) -> "Vocab":
        counts = Counter(ch for text in texts for ch in text)
        return cls(sorted(ch for ch, n in counts.items() if n >= min_count))


class TripleDataset(Dataset):
    def __init__(self, rows: List[dict], vocab: Vocab, pos_ids: Dict[str, int], max_len: int):
        self.rows = rows
        self.vocab = vocab
        self.pos_ids = pos_ids
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        ids = torch.tensor(self.vocab.encode(row["ipa"], self.max_len), dtype=torch.long)
        pos = torch.tensor(self.pos_ids.get(row["pos"], 0), dtype=torch.long)
        return ids, pos


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #

class IPAAutoencoder(nn.Module):
    """Bi-GRU encoder -> narrow latent (+ POS) -> decoder that never sees the answer.

    The decoder is deliberately **not** teacher-forced on the target tokens. That was
    tried first and it destroys the detector: given the ground-truth previous tokens, the
    decoder learns to copy its input rather than route information through the latent, so
    it reconstructs corrupted IPA just as happily as clean IPA. Training loss falls to
    0.03 and detection collapses (drop_stress 3%, wrong-POS 0.1%) — a model that
    reconstructs everything perfectly distinguishes nothing.

    So the only path from input to output is the latent bottleneck: the decoder is
    conditioned on (latent, POS, position) and must regenerate the sequence from that
    alone. Reconstruction error then measures what we actually want — "could this
    transcription be compressed into, and rebuilt from, the space of pronunciations the
    model has learned".

    Position embeddings are what keep it order-aware without leaking the target, which is
    the piece the reference model lacks (it broadcasts one vector across all timesteps, so
    it cannot represent order at all).
    """

    def __init__(
        self,
        vocab_size: int,
        n_pos: int,
        embed_dim: int = 96,
        hidden_dim: int = 256,
        latent_dim: int = 64,
        pos_dim: int = 16,
        max_len: int = 40,
        use_pos: bool = True,
    ):
        super().__init__()
        self.use_pos = use_pos

        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=PAD)
        self.encoder = nn.GRU(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.to_latent = nn.Linear(hidden_dim * 2, latent_dim)

        self.pos_embedding = nn.Embedding(n_pos, pos_dim) if use_pos else None
        condition_dim = latent_dim + (pos_dim if use_pos else 0)

        self.position = nn.Embedding(max_len, embed_dim)
        self.init_hidden = nn.Linear(condition_dim, hidden_dim)
        self.decoder = nn.GRU(embed_dim + condition_dim, hidden_dim, batch_first=True)
        self.output = nn.Linear(hidden_dim, vocab_size)

    def encode(self, ids: torch.Tensor) -> torch.Tensor:
        embedded = self.embedding(ids)
        _, hidden = self.encoder(embedded)
        hidden = torch.cat([hidden[0], hidden[1]], dim=1)
        return self.to_latent(hidden)

    def forward(self, ids: torch.Tensor, pos: torch.Tensor) -> torch.Tensor:
        latent = self.encode(ids)

        condition = latent
        if self.use_pos:
            condition = torch.cat([latent, self.pos_embedding(pos)], dim=1)

        steps = ids.size(1) - 1
        positions = torch.arange(steps, device=ids.device).unsqueeze(0).expand(ids.size(0), -1)
        decoder_input = torch.cat(
            [self.position(positions), condition.unsqueeze(1).expand(-1, steps, -1)], dim=2
        )

        hidden = torch.tanh(self.init_hidden(condition)).unsqueeze(0)
        output, _ = self.decoder(decoder_input, hidden)
        return self.output(output)

    def token_losses(self, ids: torch.Tensor, pos: torch.Tensor):
        """Per-token cross-entropy, plus the mask of real (non-padding) tokens."""
        logits = self.forward(ids, pos)
        targets = ids[:, 1:]

        losses = F.cross_entropy(
            logits.reshape(-1, logits.size(-1)),
            targets.reshape(-1),
            ignore_index=PAD,
            reduction="none",
        ).view(targets.shape)

        return losses, targets != PAD

    def scores(self, ids: torch.Tensor, pos: torch.Tensor, mode: str = "max") -> torch.Tensor:
        """Anomaly score per sequence.

        `max` — the surprise of the *worst* phoneme. A real transcription error is
        local: one wrong vowel in a fifteen-character word barely moves a mean, which is
        why mean-scoring detects only ~9% of confused phonemes while max-scoring detects
        far more. It also localises the error, so an editor can be shown *which* phoneme
        the model balked at.

        `mean` — the reference behaviour, kept for comparison. Note it is per token, not
        summed: the reference sums, so long words score high merely for being long.
        """
        losses, mask = self.token_losses(ids, pos)
        losses = losses * mask

        if mode == "mean":
            return losses.sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        return losses.max(dim=1).values


class IPADensityModel(nn.Module):
    """POS-conditioned character language model over IPA. The anomaly scorer that works.

    Reconstruction is the wrong objective for this problem. *Any* autoencoder feeds the
    string it is judging into its own encoder, so it encodes the anomaly and then happily
    rebuilds it; the error only rises when the bottleneck is too narrow to represent the
    input at all, which is a blunt and badly-calibrated instrument. Measured on the
    corruption suite, the autoencoder above catches ~4% of dropped stress marks.

    This model never sees the string it scores. It predicts each phoneme from the prefix
    and the POS alone, so the score is a proper conditional density: -log p(IPA | POS),
    per token. An implausible sequence is one the model would not have generated, and
    that is exactly the question worth asking.

    What it still cannot do — and neither can any IPA-only model — is catch a *plausible*
    pronunciation filed under the wrong POS. Both ˈrekɔːd and rɪˈkɔːd are unremarkable
    for a noun in general (compare ˈrecord and hoˈtel), so the error is only visible if
    you know the headword. That is the byT5 model's job: generate from (headword, POS) and
    compare. The two detectors are complementary, and the `wrong_pos_stress` row below is
    the honest demonstration that this one does not cover that class.
    """

    def __init__(
        self,
        vocab_size: int,
        n_pos: int,
        embed_dim: int = 96,
        hidden_dim: int = 384,
        pos_dim: int = 16,
        layers: int = 2,
        use_pos: bool = True,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.use_pos = use_pos

        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=PAD)
        self.pos_embedding = nn.Embedding(n_pos, pos_dim) if use_pos else None

        input_dim = embed_dim + (pos_dim if use_pos else 0)
        self.rnn = nn.GRU(
            input_dim, hidden_dim, num_layers=layers, batch_first=True,
            dropout=dropout if layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.output = nn.Linear(hidden_dim, vocab_size)

    def forward(self, ids: torch.Tensor, pos: torch.Tensor) -> torch.Tensor:
        inputs = ids[:, :-1]
        embedded = self.embedding(inputs)

        if self.use_pos:
            pos_emb = self.pos_embedding(pos).unsqueeze(1).expand(-1, embedded.size(1), -1)
            embedded = torch.cat([embedded, pos_emb], dim=2)

        output, _ = self.rnn(embedded)
        return self.output(self.dropout(output))

    #: Same scoring contract as the autoencoder, so the evaluation is shared.
    token_losses = IPAAutoencoder.token_losses
    scores = IPAAutoencoder.scores


# --------------------------------------------------------------------------- #
# Corruptions — the evaluation set we do not otherwise have
# --------------------------------------------------------------------------- #

def corrupt(ipa: str, kind: str, rng: random.Random) -> Optional[str]:
    """Introduce a realistic transcription error. Returns None if not applicable."""
    chars = list(ipa)

    if kind == "move_stress":
        positions = [i for i, ch in enumerate(chars) if ch in STRESS_MARKS]
        if not positions:
            return None
        i = rng.choice(positions)
        mark = chars.pop(i)
        targets = [j for j in range(len(chars)) if j != i]
        if not targets:
            return None
        chars.insert(rng.choice(targets), mark)

    elif kind == "drop_stress":
        positions = [i for i, ch in enumerate(chars) if ch in STRESS_MARKS]
        if not positions:
            return None
        chars.pop(rng.choice(positions))

    elif kind == "drop_schwa":
        positions = [i for i, ch in enumerate(chars) if ch == "ə"]
        if not positions:
            return None
        chars.pop(rng.choice(positions))

    elif kind == "confuse_phoneme":
        options = [(a, b) for a, b in CONFUSABLE if a in ipa or b in ipa]
        if not options:
            return None
        a, b = rng.choice(options)
        source, target = (a, b) if a in ipa else (b, a)
        return ipa.replace(source, target, 1)

    elif kind == "swap_adjacent":
        if len(chars) < 3:
            return None
        i = rng.randrange(len(chars) - 1)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]

    else:
        raise ValueError(kind)

    result = "".join(chars)
    return result if result != ipa else None


def build_wrong_pos_cases(rows: List[dict]) -> List[Tuple[dict, str]]:
    """Heterophonic homographs with the *other* POS's pronunciation attached.

    This is the corruption an unconditional model cannot possibly detect: both strings
    are perfectly well-formed IPA, and only the pairing with the POS is wrong. It is also
    the error a dictionary really contains — ˈrekɔːd filed under the verb.
    """
    by_headword: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_headword[row["headword"]][row["pos"]].append(row["ipa"])

    cases: List[Tuple[dict, str]] = []
    for headword, by_pos in by_headword.items():
        if len(by_pos) < 2:
            continue
        for pos, ipas in by_pos.items():
            others = {i for p, group in by_pos.items() if p != pos for i in group}
            others -= set(ipas)
            for other in others:
                cases.append(({"headword": headword, "pos": pos, "ipa": ipas[0]}, other))
    return cases


# --------------------------------------------------------------------------- #
# Train / evaluate
# --------------------------------------------------------------------------- #

def percentile_rank(values: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    """Where each value falls in the clean distribution (0 = typical, 1 = unheard of)."""
    ordered = torch.sort(reference).values
    index = torch.searchsorted(ordered, values.contiguous())
    return index.float() / len(ordered)


def combine(mean_scores, max_scores, clean_mean, clean_max) -> torch.Tensor:
    """One score from two views, each judged against its own clean distribution.

    `mean` and `max` catch different errors and neither dominates: dropping a stress mark
    shifts the whole sequence's likelihood (mean sees it, max largely does not), while a
    single confused vowel spikes one position (max sees it, mean dilutes it away). Ranking
    each against the clean data puts them on a common scale, and taking the worse of the
    two flags a transcription that is unusual in *either* respect.
    """
    return torch.maximum(
        percentile_rank(mean_scores, clean_mean),
        percentile_rank(max_scores, clean_max),
    )


def score_all(model, rows, vocab, pos_ids, max_len, device, mode="max", batch_size=512) -> torch.Tensor:
    model.eval()
    loader = DataLoader(TripleDataset(rows, vocab, pos_ids, max_len), batch_size=batch_size)
    out = []
    with torch.no_grad():
        for ids, pos in loader:
            out.append(model.scores(ids.to(device), pos.to(device), mode=mode).cpu())
    return torch.cat(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="triples.json")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--max-len", type=int, default=40)
    parser.add_argument("--no-pos", action="store_true", help="Ablation: unconditional model")
    parser.add_argument("--model", choices=["density", "autoencoder"], default="density",
                        help="density = POS-conditioned char LM (recommended); "
                             "autoencoder = reconstruction error (the reference approach)")
    parser.add_argument("--fpr", type=float, default=0.01, help="Target false-positive rate")
    parser.add_argument("--score", choices=["max", "mean"], default="max",
                        help="max = surprise of the worst phoneme (localises the error); "
                             "mean = reference behaviour")
    parser.add_argument("--output", default="ipa_autoencoder.pt")
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    rows = [r for r in json.load(open(args.data, encoding="utf-8")) if r["ipa"].strip()]
    rng.shuffle(rows)

    split = int(len(rows) * 0.9)
    train_rows, held_out = rows[:split], rows[split:]

    vocab = Vocab.build([r["ipa"] for r in train_rows])
    pos_ids = {pos: i for i, pos in enumerate(sorted({r["pos"] for r in rows}))}
    use_pos = not args.no_pos

    print(f"device={device}  train={len(train_rows):,}  held-out={len(held_out):,}")
    print(f"vocab={len(vocab)}  pos={len(pos_ids)}  model={args.model}  conditioned_on_pos={use_pos}")

    if args.model == "density":
        model = IPADensityModel(len(vocab), len(pos_ids), use_pos=use_pos).to(device)
    else:
        model = IPAAutoencoder(
            len(vocab), len(pos_ids), max_len=args.max_len, use_pos=use_pos
        ).to(device)
    optimiser = torch.optim.AdamW(model.parameters(), lr=2e-3)
    loader = DataLoader(
        TripleDataset(train_rows, vocab, pos_ids, args.max_len),
        batch_size=args.batch_size,
        shuffle=True,
        drop_last=True,
    )

    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for ids, pos in loader:
            ids, pos = ids.to(device), pos.to(device)
            logits = model(ids, pos)
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                ids[:, 1:].reshape(-1),
                ignore_index=PAD,
            )
            optimiser.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            total += loss.item()
        print(f"  epoch {epoch:>2}  loss {total / len(loader):.4f}")

    # ---- Calibrate on clean held-out data ---------------------------------- #
    # Split the held-out set: one half defines what "normal" looks like, the other
    # measures the false-positive rate. Calibrating and measuring on the same data would
    # hand back the target FPR by construction and tell us nothing.
    half = len(held_out) // 2
    calib_rows, fpr_rows = held_out[:half], held_out[half:]

    def scored(rows):
        return (
            score_all(model, rows, vocab, pos_ids, args.max_len, device, "mean"),
            score_all(model, rows, vocab, pos_ids, args.max_len, device, "max"),
        )

    clean_mean, clean_max = scored(calib_rows)

    def anomaly_score(rows):
        mean_s, max_s = scored(rows)
        return combine(mean_s, max_s, clean_mean, clean_max)

    threshold = torch.quantile(anomaly_score(calib_rows), 1.0 - args.fpr).item()
    measured_fpr = (anomaly_score(fpr_rows) > threshold).float().mean().item()

    print()
    print(f"threshold @ {args.fpr:.0%} target FPR : {threshold:.4f}")
    print(f"measured FPR on unseen clean : {measured_fpr:.2%}")

    # ---- Detection rate per corruption type, at that fixed FPR ------------- #
    print()
    print(f"{'corruption':<20}{'n':>7}{'detected':>10}")
    print("-" * 37)

    results = {}
    for kind in ["move_stress", "drop_stress", "drop_schwa", "confuse_phoneme", "swap_adjacent"]:
        cases = []
        for row in held_out:
            bad = corrupt(row["ipa"], kind, rng)
            if bad:
                cases.append({"headword": row["headword"], "pos": row["pos"], "ipa": bad})
        if not cases:
            continue
        rate = (anomaly_score(cases) > threshold).float().mean().item()
        results[kind] = rate
        print(f"{kind:<20}{len(cases):>7,}{rate:>9.1%}")

    # The corruption only a POS-conditioned model can see.
    wrong_pos = [
        {"headword": row["headword"], "pos": row["pos"], "ipa": other}
        for row, other in build_wrong_pos_cases(rows)
    ]
    if wrong_pos:
        rate = (anomaly_score(wrong_pos) > threshold).float().mean().item()
        results["wrong_pos_stress"] = rate
        print(f"{'wrong_pos_stress':<20}{len(wrong_pos):>7,}{rate:>9.1%}   <- needs POS")

    torch.save(
        {
            "state_dict": model.state_dict(),
            "vocab": vocab.itos,
            "pos_ids": pos_ids,
            "use_pos": use_pos,
            "threshold": threshold,
            "clean_mean": clean_mean.cpu(),
            "clean_max": clean_max.cpu(),
            "measured_fpr": measured_fpr,
            "max_len": args.max_len,
            "fpr": args.fpr,
            "score_mode": args.score,
            "detection_rates": results,
        },
        args.output,
    )
    print()
    print(f"saved -> {args.output}")


if __name__ == "__main__":
    main()
