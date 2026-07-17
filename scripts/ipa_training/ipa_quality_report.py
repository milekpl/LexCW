#!/usr/bin/env python3
"""Comprehensive IPA quality report for triples.json.
Outputs: ipa_quality_report.txt (summary) + dedicated files per category.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

rows = json.loads(Path("triples.json").read_text(encoding="utf-8"))
N = len(rows)

# Standard IPA phoneme set for English
STD_PHONEMES = set("ɪˈətnslkːerɪdmæpbʌɡzhəʊaːɔːfɡwvjʃuːŋθðʒɒɜˈˌ̃")

# Helper: count syllables in IPA
def ipa_syllables(ipa: str) -> int:
    vowels = set("aeiouəɑɔɛɪʊʌɜɒæə")
    return sum(1 for c in ipa if c in vowels)

# Helper: count syllables in headword (crude — vowel letters)
def hw_syllables(hw: str) -> int:
    vowel_letters = set("aeiouy")
    return sum(1 for c in hw.lower() if c in vowel_letters)

# ========================================================================== #
# 6.  -ate SUFFIX /ɪt/ vs /ət/  (write to file)
# ========================================================================== #
ate_rows = []
for r in rows:
    if r["pos"] in ("ADJ", "NOUN") and r["ipa"].endswith("ɪt"):
        if r["headword"].endswith("ate"):
            ate_rows.append(r)
    if r["pos"] in ("ADJ", "NOUN") and r["ipa"].endswith("ət"):
        if r["headword"].endswith("ate"):
            ate_rows.append(r)

# Separate into /ɪt/ (suspect) and /ət/ (expected)
ate_suspect = [r for r in ate_rows if r["ipa"].endswith("ɪt")]
ate_expected = [r for r in ate_rows if r["ipa"].endswith("ət")]

Path("ipa_report_ate_suspect.txt").write_text(
    "\n".join(f"{r['headword']:<45} {r['pos']:<6} {r['ipa']}" for r in ate_suspect),
    encoding="utf-8"
)
Path("ipa_report_ate_expected.txt").write_text(
    "\n".join(f"{r['headword']:<45} {r['pos']:<6} {r['ipa']}" for r in ate_expected),
    encoding="utf-8"
)

# ========================================================================== #
# 7.  FOREIGN / NON-STANDARD IPA CHARACTERS  (write to file)
# ========================================================================== #
# Characters that are NOT part of standard English IPA
NON_ENGLISH = set("øœɥ«»")
NASAL_TILDE = "̃"

foreign_entries = []
for r in rows:
    has_non_english = any(c in NON_ENGLISH for c in r["ipa"])
    has_nasal = NASAL_TILDE in r["ipa"]
    if has_non_english or has_nasal:
        foreign_entries.append(r)

foreign_entries.sort(key=lambda r: r["headword"])

# Group by character
by_char: dict[str, list[dict]] = defaultdict(list)
for r in foreign_entries:
    for c in r["ipa"]:
        if c in NON_ENGLISH or c == NASAL_TILDE:
            label = c if c != NASAL_TILDE else "tilde (nasal vowel)"
            by_char[label].append(r)

lines = [f"Foreign characters found in {len(foreign_entries)} entries:\n"]
for char, entries in sorted(by_char.items()):
    lines.append(f"\n--- {char!r} ({len(entries)} entries) ---")
    for r in entries[:50]:
        lines.append(f"  {r['headword']:<45} {r['pos']:<6} {r['ipa']}")
    if len(entries) > 50:
        lines.append(f"  ... and {len(entries)-50} more")

Path("ipa_report_foreign_chars.txt").write_text("\n".join(lines), encoding="utf-8")

# ========================================================================== #
# 8.  UNK entries — with suggested POS from extraction logic  (write to file)
# ========================================================================== #
unk_rows = [r for r in rows if r["pos"] == "UNK"]

# Try to infer the correct POS by looking at the same headword with a known POS
unk_by_word: dict[str, list[dict]] = defaultdict(list)
for r in unk_rows:
    unk_by_word[r["headword"]].append(r)

# For each UNK, check if the same headword appears with a known POS
all_by_word: dict[str, list[dict]] = defaultdict(list)
for r in rows:
    all_by_word[r["headword"]].append(r)

unk_analysis = []
for hw, entries in sorted(unk_by_word.items()):
    all_entries = all_by_word[hw]
    known_pos = set(r["pos"] for r in all_entries if r["pos"] != "UNK")
    suggestion = "unknown"
    if known_pos:
        suggestion = ", ".join(sorted(known_pos))
    unk_analysis.append((hw, suggestion, entries))

lines = [f"Total UNK entries: {len(unk_rows)}  Unique headwords: {len(unk_by_word)}\n"]
lines.append(f"{'HEADWORD':<40} {'SUGGESTED POS':<20} {'IPAs'}")
lines.append("-" * 80)
for hw, suggestion, entries in unk_analysis:
    ipas = "; ".join(sorted(set(r["ipa"] for r in entries)))
    lines.append(f"{hw:<40} {suggestion:<20} {ipas}")

Path("ipa_report_unk_entries.txt").write_text("\n".join(lines), encoding="utf-8")

# ========================================================================== #
# MAIN SUMMARY (stdout + ipa_quality_report.txt)
# ========================================================================== #
report: list[str] = []

report.append("=" * 72)
report.append("IPA QUALITY REPORT — triples.json")
report.append("=" * 72)
report.append("")

# ── 1. Character set ───────────────────────────────────────────────────── #
char_counts: Counter = Counter()
for r in rows:
    for c in r["ipa"]:
        char_counts[c] += 1
total_chars = sum(char_counts.values())
all_chars = sorted(char_counts)

report.append("1.  CHARACTER SET")
report.append("-" * 72)
report.append(f"    Unique characters       : {len(all_chars)}")
report.append(f"    Standard IPA phonemes   : {len(STD_PHONEMES)}")

unexpected = sorted(c for c in all_chars if c not in STD_PHONEMES)
if unexpected:
    report.append(f"    Characters outside standard set:")
    for c in unexpected:
        pct = char_counts[c] / total_chars * 100
        report.append(f"      U+{ord(c):04X}  {char_counts[c]:>8} ({pct:.2f}%)  {repr(c)}")
report.append("")

report.append(f"    Top 10 most common IPA tokens:")
for c, n in char_counts.most_common(10):
    pct = n / total_chars * 100
    report.append(f"      U+{ord(c):04X}  {n:>8} ({pct:.2f}%)  {repr(c)}")
report.append("")

# ── 2. IPA string length ───────────────────────────────────────────────── #
report.append("2.  IPA STRING LENGTH")
report.append("-" * 72)
lengths = Counter(len(r["ipa"]) for r in rows)
report.append(f"    Min : {min(lengths)}   Max : {max(lengths)}   Mean : {sum(k*v for k,v in lengths.items())/N:.1f}   Median : {sorted(lengths.elements())[N//2]}")
report.append("")

# ── 3. Stress markers ──────────────────────────────────────────────────── #
report.append("3.  STRESS MARKERS")
report.append("-" * 72)
has_primary = sum(1 for r in rows if "ˈ" in r["ipa"])
has_secondary = sum(1 for r in rows if "ˌ" in r["ipa"])
has_both = sum(1 for r in rows if "ˈ" in r["ipa"] and "ˌ" in r["ipa"])
has_neither_sum = sum(1 for r in rows if "ˈ" not in r["ipa"] and "ˌ" not in r["ipa"])

# Break down missing stress by syllable count
no_stress = [r for r in rows if "ˈ" not in r["ipa"] and "ˌ" not in r["ipa"]]
single_syll_no_stress = [r for r in no_stress if ipa_syllables(r["ipa"]) <= 1]
multi_syll_no_stress = [r for r in no_stress if ipa_syllables(r["ipa"]) > 1]

report.append(f"    With primary ˈ       : {has_primary:>8} ({has_primary/N*100:.1f}%)")
report.append(f"    With secondary ˌ     : {has_secondary:>8} ({has_secondary/N*100:.1f}%)")
report.append(f"    With both            : {has_both:>8} ({has_both/N*100:.1f}%)")
report.append(f"    No stress            : {has_neither_sum:>8} ({has_neither_sum/N*100:.1f}%)")
report.append(f"      — single-syllable  : {len(single_syll_no_stress):>8} ({len(single_syll_no_stress)/max(has_neither_sum,1)*100:.0f}% of no-stress)")
report.append(f"      — multi-syllable   : {len(multi_syll_no_stress):>8} ({len(multi_syll_no_stress)/max(has_neither_sum,1)*100:.0f}% of no-stress)")
report.append("")

# Multi-syllable no stress: MWEs vs single words
mwe_no_stress = [r for r in multi_syll_no_stress if " " in r["headword"]]
single_no_stress = [r for r in multi_syll_no_stress if " " not in r["headword"]]
report.append(f"    Multi-syllable no-stress breakdown:")
report.append(f"      — MWEs (compound) : {len(mwe_no_stress):>8}")
report.append(f"      — single words    : {len(single_no_stress):>8}")
report.append("")

# Of the MWEs without stress, how many are single-syllable components?
mwe_1syll = 0
mwe_multi = 0
for r in mwe_no_stress:
    parts = r["headword"].split()
    component_syllables = [hw_syllables(p) for p in parts]
    if all(s <= 2 for s in component_syllables):
        mwe_1syll += 1
    else:
        mwe_multi += 1
report.append(f"    MWE no-stress breakdown:")
report.append(f"      — short components (≤2 vowel letters each): {mwe_1syll}")
report.append(f"      — longer components                     : {mwe_multi}")
report.append("")

if single_no_stress:
    report.append(f"    Single-word multi-syllable without stress (examples — these are likely errors):")
    for r in single_no_stress[:15]:
        report.append(f"      {r['headword']:<35} {r['ipa']}")
report.append("")

# ── 4. Stress placement anomalies ───────────────────────────────────────── #
report.append("4.  STRESS PLACEMENT ANOMALIES")
report.append("-" * 72)
double_at_start = [r for r in rows if r["ipa"].startswith("ˈˌ") or r["ipa"].startswith("ˌˈ")]
trailing = [r for r in rows if r["ipa"].endswith("ˈ") or r["ipa"].endswith("ˌ")]
report.append(f"    Double stress at start : {len(double_at_start)}")
for r in double_at_start[:5]:
    report.append(f"      {r['headword']:<40} [{r['pos']:5}] {r['ipa']}")
report.append(f"    Trailing stress        : {len(trailing)}")
for r in trailing[:10]:
    report.append(f"      {r['headword']:<40} [{r['pos']:5}] {r['ipa']}")
report.append("")

# ── 5. POS distribution ────────────────────────────────────────────────── #
report.append("5.  POS TAG DISTRIBUTION")
report.append("-" * 72)
pos_counts = Counter(r["pos"] for r in rows)
for pos, n in sorted(pos_counts.items(), key=lambda x: x[1], reverse=True):
    report.append(f"    {pos:<8}  {n:>8}  ({n/N*100:.1f}%)")
report.append("")

# ── 6. -ate suffix ─────────────────────────────────────────────────────── #
report.append("6.  -ate ADJ/NOUN: /ɪt/ (suspect) vs /ət/ (expected)")
report.append("-" * 72)
report.append(f"    Entries with /ɪt/ suffix  : {len(ate_suspect)}  → ipa_report_ate_suspect.txt")
report.append(f"    Entries with /ət/ suffix  : {len(ate_expected)}  → ipa_report_ate_expected.txt")
report.append("")

# ── 7. Foreign characters ──────────────────────────────────────────────── #
report.append("7.  FOREIGN / NON-STANDARD IPA CHARACTERS")
report.append("-" * 72)
report.append(f"    Entries with non-English IPA: {len(foreign_entries)}  → ipa_report_foreign_chars.txt")
report.append("")

# ── 8. UNK entries ───────────────────────────────────────────────────────── #
report.append("8.  UNK TAGGED ENTRIES (script quality issue — extraction doesn't propagate parent POS)")
report.append("-" * 72)
report.append(f"    Total UNK entries     : {len(unk_rows)}")
report.append(f"    Unique headwords      : {len(unk_by_word)}")
# How many could be rescued?
rescuable = sum(1 for _, suggestion, _ in unk_analysis if suggestion != "unknown")
report.append(f"    Could be rescued      : {rescuable}  (same headword has known POS elsewhere in data)")
report.append(f"    → ipa_report_unk_entries.txt")
report.append("")

# ── 9. Summary ───────────────────────────────────────────────────────────── #
report.append("9.  SUMMARY")
report.append("-" * 72)
report.append(f"    Total entries                   : {N:,}")
report.append(f"    No stress markers               : {has_neither_sum:,} ({has_neither_sum/N*100:.1f}%)")
# Subtract intentional single-syllable and short-component MWEs
intentional_no_stress = len(single_syll_no_stress) + mwe_1syll
genuine_missing = has_neither_sum - intentional_no_stress
report.append(f"      (intentional: single-syllable + short MWE components: {intentional_no_stress})")
report.append(f"      (likely genuine errors: {genuine_missing})")
report.append(f"    Double stress at start          : {len(double_at_start)}")
report.append(f"    Trailing stress                 : {len(trailing)}")
report.append(f"    -ate ADJ/NOUN with /ɪt/         : {len(ate_suspect)}  → ipa_report_ate_suspect.txt")
report.append(f"    -ate ADJ/NOUN with /ət/         : {len(ate_expected)}  → ipa_report_ate_expected.txt")
report.append(f"    Foreign IPA characters          : {len(foreign_entries)}  → ipa_report_foreign_chars.txt")
report.append(f"    UNK entries                     : {len(unk_rows):,}  → ipa_report_unk_entries.txt")
report.append(f"    Rescuable UNK → known POS       : {rescuable}")
report.append("")
report.append("Files written:")
report.append("  ipa_quality_report.txt       (this summary)")
report.append("  ipa_report_ate_suspect.txt   (-ate ADJ/NOUN entries with /ɪt/)")
report.append("  ipa_report_ate_expected.txt  (-ate ADJ/NOUN entries with /ət/)")
report.append("  ipa_report_foreign_chars.txt (entries with non-English IPA)")
report.append("  ipa_report_unk_entries.txt   (UNK entries with suggested POS)")

Path("ipa_quality_report.txt").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report))
