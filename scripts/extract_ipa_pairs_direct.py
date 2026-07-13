#!/usr/bin/env python3
"""
Extract (headword, IPA) pairs directly from BaseX on disk.
Uses XQuery to output tab-separated pairs, one per line.
"""
import json
import subprocess
import sys
import re

BASEX_JAR = "/home/milek/flask-app/basex/BaseX.jar"
BASEX_DBPATH = "/home/milek/basex123/data"


def decompress(ipa: str) -> str:
    """Decompress parenthetical IPA notation to shortest variant."""
    while True:
        idx = ipa.find("(")
        if idx == -1:
            return ipa
        depth = 0
        close = -1
        for i in range(idx, len(ipa)):
            if ipa[i] == "(":
                depth += 1
            elif ipa[i] == ")":
                depth -= 1
                if depth == 0:
                    close = i
                    break
        if close == -1:
            return ipa  # unbalanced
        before = ipa[:idx]
        inside = ipa[idx+1:close]
        after = ipa[close+1:]
        # Choose the shorter variant (without the optional part)
        ipa = before + inside + after  # with
        alt = before + after  # without
        # Pick shortest
        candidates = [before + inside + after, before + after]
        # Recursively decompress
        decompressed = []
        for c in candidates:
            decompressed.append(decompress(c))
        return min(decompressed, key=lambda s: (len(s), s))


def basex(cmd: str) -> str:
    r = subprocess.run(
        ["java", f"-Dorg.basex.DBPATH={BASEX_DBPATH}", "-cp", BASEX_JAR,
         "org.basex.BaseX", "-c", cmd],
        capture_output=True, text=True, timeout=600,
    )
    return r.stdout


def main():
    out_file = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--output" else "pairs.json"

    # Count total
    total = basex("OPEN dictionary; XQUERY count(//entry)").strip()
    print(f"Total entries: {total}")

    # Pair headword and IPA inside each entry. Fetching headwords and IPA as
    # two separate lists and zipping them by index is broken: entries can have
    # several pronunciations, so the lists have different lengths and every
    # pair after the first multi-pronunciation entry is shifted.
    query = (
        "for $e in //entry[pronunciation/form/@lang='seh-fonipa'] "
        "let $hw := string($e/lexical-unit/form[@lang='en'][1]) "
        "for $ipa in $e/pronunciation/form[@lang='seh-fonipa']/string() "
        "where $hw != '' and $ipa != '' "
        "return concat($hw, codepoints-to-string(9), $ipa)"
    )
    result = basex(f"OPEN dictionary; XQUERY {query}")

    pairs = []
    seen = set()
    skipped = 0
    for line in result.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            skipped += 1
            continue
        hw, ipa_raw = parts[0].strip(), parts[1].split(",")[0].strip()
        if not hw or not ipa_raw:
            continue
        ipa = decompress(ipa_raw)
        key = (hw, ipa)
        if key not in seen:
            seen.add(key)
            pairs.append({"headword": hw, "ipa": ipa})
    if skipped:
        print(f"Skipped {skipped} malformed lines (embedded tab/newline)")

    print(f"Extracted {len(pairs)} unique pairs")
    print(f"First 3: {pairs[:3]}")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)
    print(f"Written to {out_file}")


if __name__ == "__main__":
    main()
