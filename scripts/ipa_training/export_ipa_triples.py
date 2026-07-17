#!/usr/bin/env python3
"""Export (headword, POS, IPA) triples from BaseX for G2P / anomaly-detection training.

Replaces the (headword, IPA) pair export. English pronunciation depends on grammatical
function — *separate* is ˈsepərət as an adjective and ˈsepəreɪt as a verb — so a
pair-only dataset asks the model to map one input to two different targets and cannot
teach it the noun/verb stress alternation at all. 98% of IPA-bearing entries already
carry POS; it was simply being thrown away.

Alignment is the delicate part. In LIFT, **pronunciation hangs off the entry** while
**POS hangs off the sense**, so within one entry there is no link between a particular
IPA and a particular POS. This script therefore never guesses:

  * one distinct POS in the entry  -> every IPA belongs to that POS.          (88,601 entries)
  * several POS but a single IPA   -> that IPA belongs to each of them.       (72 entries)
  * several POS *and* several IPA  -> unalignable; emitted to a separate file
                                      for review, never into the training set. (2 entries)

Taking the cross-product in that last case would invent (POS, IPA) combinations that do
not exist — reintroducing exactly the contradictory supervision this export is meant to
remove.

Usage:
    python scripts/ipa_training/export_ipa_triples.py --output triples.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from typing import Dict, List, Optional

BASEX_JAR = "/home/milek/flask-app/basex/BaseX.jar"
# The real dictionary (153K entries). NOT ~/basex/data, which the server defaults to and
# which holds a 316-entry test remnant.
BASEX_DBPATH = "/home/milek/basex123/data"

SEP = "\t"

#: Raw LIFT grammatical-info values -> compact tagset. Anything not listed becomes UNK:
#: a wrong tag is worse than an honest "unknown", and the tail is tiny.
POS_MAP: Dict[str, str] = {
    "Noun": "NOUN",
    "Countable Noun": "NOUN",
    "Uncountable Noun": "NOUN",
    "Countable or Uncountable Noun": "NOUN",
    "Verb": "VERB",
    "Phrasal Verb": "VERB",
    "Adjective": "ADJ",
    "adj": "ADJ",
    "Adverb": "ADV",
    "Pronoun": "PRON",
    "Personal pronoun": "PRON",
    "Possessive pronoun": "PRON",
    "Reflexive pronoun": "PRON",
    "Relative pronoun": "PRON",
    "Demonstrative pronoun": "PRON",
    "Interrogative pro-form": "PRON",
    "Determiner": "DET",
    "Possessive Determiner": "DET",
    "Article": "DET",
    "Quantifier": "DET",
    "Cardinal numeral": "NUM",
    "Ordinal numeral": "NUM",
    "Preposition": "PREP",
    "Connective": "CONJ",
    "Interjection": "INTJ",
    "int": "INTJ",
    "Abbreviation": "ABBR",
    "Acronym": "ABBR",
    "Contraction": "ABBR",
    "Prefix": "AFFIX",
    "pref": "AFFIX",
    "Suffix": "AFFIX",
    "Idiom": "IDIOM",
    # Deliberately unmapped (ambiguous or junk): "su", "c", "pre", "".
}

QUERY = (
    "for $e in //entry[pronunciation/form[@lang='seh-fonipa']/text] "
    "let $hw := string(($e/lexical-unit/form[@lang='en']/text)[1]) "
    "let $pos := string-join(distinct-values($e/sense/grammatical-info/@value), '|') "
    "for $ipa in $e/pronunciation/form[@lang='seh-fonipa']/text/string() "
    "where $hw != '' and normalize-space($ipa) != '' "
    "return string-join(($hw, $pos, $ipa), codepoints-to-string(9))"
)


def basex(command: str, query_file: Optional[str] = None) -> str:
    args = [
        "java",
        f"-Dorg.basex.DBPATH={BASEX_DBPATH}",
        "-cp",
        BASEX_JAR,
        "org.basex.BaseX",
        "-c",
        command,
    ]
    if query_file:
        args.append(query_file)
    result = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        sys.exit(f"BaseX failed: {result.stderr[:500]}")
    return result.stdout


def decompress(ipa: str) -> str:
    """Expand parenthesised optional sounds, keeping the shortest reading.

    ˈskɒtɪˌsɪz(ə)m -> ˈskɒtɪˌsɪzm
    """
    start = ipa.find("(")
    if start == -1:
        return ipa

    depth = 0
    close = -1
    for i in range(start, len(ipa)):
        if ipa[i] == "(":
            depth += 1
        elif ipa[i] == ")":
            depth -= 1
            if depth == 0:
                close = i
                break
    if close == -1:
        return ipa  # unbalanced: leave it alone

    before, inside, after = ipa[:start], ipa[start + 1 : close], ipa[close + 1 :]
    candidates = [decompress(before + inside + after), decompress(before + after)]
    return min(candidates, key=lambda s: (len(s), s))


def normalise_pos(raw_values: str) -> List[str]:
    """Map the entry's raw POS values onto the compact tagset (deduplicated)."""
    tags: List[str] = []
    for raw in (value.strip() for value in raw_values.split("|")):
        if not raw:
            continue
        tag = POS_MAP.get(raw)
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="triples.json")
    parser.add_argument(
        "--ambiguous-output",
        default=None,
        help="Where to write entries whose POS and IPA cannot be aligned "
        "(default: <output>.ambiguous.json)",
    )
    args = parser.parse_args()
    ambiguous_path = args.ambiguous_output or args.output.replace(".json", "") + ".ambiguous.json"

    print(f"Reading {BASEX_DBPATH} (dictionary)…")
    raw = basex(f"OPEN dictionary; XQUERY {QUERY}")

    # Regroup the flat rows by entry. The query emits one line per IPA field, repeating
    # the headword and the entry's POS set, so rows sharing (headword, pos-set) that
    # arrive consecutively belong to the same entry.
    entries: Dict[tuple, List[str]] = {}
    order: List[tuple] = []
    malformed = 0

    for line in raw.split("\n"):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        parts = line.split(SEP)
        if len(parts) != 3:
            malformed += 1
            continue
        headword, pos_raw, ipa_field = (part.strip() for part in parts)
        if not headword or not ipa_field:
            continue
        key = (headword, pos_raw)
        if key not in entries:
            entries[key] = []
            order.append(key)
        entries[key].append(ipa_field)

    triples: List[dict] = []
    ambiguous: List[dict] = []
    seen = set()
    stats = Counter()
    pos_counts = Counter()

    for key in order:
        headword, pos_raw = key
        ipa_fields = entries[key]

        # A field may hold several comma-separated variants:
        #   "ˈhektəˌɡræf, ˈhektəɡrɑːf, ˈhektəʊɡrɑːf"
        # Each is a legitimate pronunciation of the same word; the old export kept only
        # the first and discarded 7,136 fields' worth of the rest.
        variants: List[str] = []
        for field in ipa_fields:
            for variant in field.split(","):
                variant = decompress(variant.strip())
                if variant and variant not in variants:
                    variants.append(variant)

        if not variants:
            continue

        tags = normalise_pos(pos_raw)
        if not tags:
            tags = ["UNK"]
            stats["entries_without_pos"] += 1

        # Several POS *and* several distinct pronunciations: nothing in the LIFT says
        # which reading goes with which POS. Guessing would manufacture false pairs.
        if len(tags) > 1 and len(variants) > 1:
            ambiguous.append(
                {"headword": headword, "pos": tags, "ipa": variants, "raw_pos": pos_raw}
            )
            stats["entries_ambiguous_skipped"] += 1
            continue

        for tag in tags:
            for index, ipa in enumerate(variants):
                dedup_key = (headword, tag, ipa)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                triples.append(
                    {
                        "headword": headword,
                        "pos": tag,
                        "ipa": ipa,
                        "primary": index == 0,
                    }
                )
                pos_counts[tag] += 1

        stats["entries_exported"] += 1

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(triples, handle, ensure_ascii=False, indent=2)

    if ambiguous:
        with open(ambiguous_path, "w", encoding="utf-8") as handle:
            json.dump(ambiguous, handle, ensure_ascii=False, indent=2)

    print()
    print(f"triples written      : {len(triples):>7,}  -> {args.output}")
    print(f"  primary only       : {sum(1 for t in triples if t['primary']):>7,}")
    print(f"entries exported     : {stats['entries_exported']:>7,}")
    print(f"  without POS (UNK)  : {stats['entries_without_pos']:>7,}")
    print(f"entries skipped      : {stats['entries_ambiguous_skipped']:>7,}  -> {ambiguous_path}")
    print(f"malformed lines      : {malformed:>7,}")
    print()
    print("POS distribution:")
    for tag, count in pos_counts.most_common():
        print(f"  {tag:<6} {count:>7,}")


if __name__ == "__main__":
    main()
