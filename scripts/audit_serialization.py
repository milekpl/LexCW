#!/usr/bin/env python3
"""Audit form-serialization call sites for the Alpine-migration bug class.

After the entry form was migrated to Alpine, the data lives in Alpine component state (no
`name=` inputs). Any code path that builds serializer input from the LEGACY DOM serializers
(`FormSerializer.serializeFormToJSON[Safe]`, or form-state-manager's `serializeToJSON`) WITHOUT
merging Alpine state via `MergeHarness.extractAlpineState()` will silently produce an empty /
stale entry (e.g. "Entry must have a lexicalUnit with at least one form"). Known offenders found
one at a time: submit, live-preview, and the XML preview button.

This script finds every relevant call site and flags the ones whose enclosing function does NOT
go through `extractAlpineState`, so they can be reviewed/fixed in one pass.

Usage:  python scripts/audit_serialization.py
Exit code 1 if any SUSPECT sites are found (useful as a CI guard).
"""
from __future__ import annotations

import os
import re
import sys

JS_ROOT = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js")

# Calls that PRODUCE serializer input or XML from the form.
SINK_PATTERNS = [
    r"\.serializeEntry\s*\(",            # XML generation — input must be Alpine-merged
    r"serializeFormToJSONSafe\s*\(",     # legacy async DOM serializer
    r"serializeFormToJSON\s*\(",         # legacy DOM serializer (FormSerializer or state-manager)
    r"\.serializeToJSON\s*\(",           # form-state-manager (auto-save / change detection)
]
# Evidence that a path correctly merges Alpine state. `buildSerializerInput` is the shared
# helper that internally does legacy-serialize + extractAlpineState + mergeSync (the fix that
# consolidates the duplicated merge dance — see scripts handoff).
ALPINE_MARKERS = [
    r"extractAlpineState\s*\(",
    r"MergeHarness",
    r"alpineState",
    r"buildSerializerInput\s*\(",
]
# Legacy sense post-processing that should NOT run on an Alpine-merged formData.
LEGACY_REDFLAGS = [r"applySenseRelationsFromDom\s*\(", r"normalizeIndexedArray\s*\("]

# Files that ARE the legacy serializer implementation or test harnesses — their internal calls
# are expected and not bugs. (They get fed correct data by the call sites we DO audit.)
EXCLUDED_FILES = {
    "form-serializer.js",          # the legacy serializer itself
    "form-serializer-worker.js",   # the worker that runs it
    "form-serializer-browser-test.js",
    "form-serializer.test.js",
}
# A call site that is itself the function DEFINITION (not a use) — skip.
DEF_RE = re.compile(r"(?:function\s+)?(?:serializeFormToJSON(?:Safe)?|serializeToJSON)\s*\([^)]*\)\s*\{")

FUNC_RE = re.compile(
    r"(?:function\s+([A-Za-z0-9_$]+)\s*\(|"
    r"([A-Za-z0-9_$]+)\s*[:=]\s*(?:async\s+)?function\b|"
    r"([A-Za-z0-9_$]+)\s*\([^)]*\)\s*\{)"
)


def enclosing_function(lines: list[str], idx: int) -> tuple[str, int, int]:
    """Best-effort: nearest preceding function header whose body (brace-matched) contains line idx.
    Returns (name, start_line0, end_line0)."""
    for start in range(idx, -1, -1):
        m = FUNC_RE.search(lines[start])
        if not m:
            continue
        name = next((g for g in m.groups() if g), "<anon>")
        # brace-match forward from this header
        depth = 0
        seen = False
        for j in range(start, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if "{" in lines[j]:
                seen = True
            if seen and depth <= 0:
                if start <= idx <= j:
                    return name, start, j
                break  # this function doesn't contain idx; keep scanning upward
    return "<module>", 0, len(lines) - 1


def audit_file(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    findings = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        if os.path.basename(path) in EXCLUDED_FILES:
            continue
        if DEF_RE.search(line):  # the definition of a serializer, not a use of it
            continue
        for pat in SINK_PATTERNS:
            if re.search(pat, line):
                fname, fstart, fend = enclosing_function(lines, i)
                body = "".join(lines[fstart : fend + 1])
                has_alpine = any(re.search(m, body) for m in ALPINE_MARKERS)
                redflags = [rf for rf in LEGACY_REDFLAGS if re.search(rf, body)]
                findings.append(
                    {
                        "file": os.path.relpath(path),
                        "line": i + 1,
                        "call": stripped[:80],
                        "func": fname,
                        "alpine_merged": has_alpine,
                        "redflags": redflags,
                    }
                )
                break
    return findings


def main() -> int:
    all_findings = []
    for root, _dirs, files in os.walk(JS_ROOT):
        for fn in files:
            if fn.endswith(".js") and not fn.endswith((".test.js", ".min.js")):
                all_findings.extend(audit_file(os.path.join(root, fn)))

    suspects = [f for f in all_findings if not f["alpine_merged"]]
    ok = [f for f in all_findings if f["alpine_merged"]]

    def show(items):
        for f in items:
            flag = "  ⚠ legacy sense post-proc: " + ",".join(f["redflags"]) if f["redflags"] else ""
            print(f"  {f['file']}:{f['line']}  in {f['func']}()  ::  {f['call']}{flag}")

    print(f"\n=== SUSPECT: serializes WITHOUT extractAlpineState ({len(suspects)}) ===")
    print("(review each: should it build formData via MergeHarness.extractAlpineState()?")
    print(" — legitimate exceptions: form-serializer.js internals, the legacy fallback branch,")
    print("   and form-state-manager.js if auto-save is intentionally deferred.)")
    show(sorted(suspects, key=lambda f: (f["file"], f["line"])))

    print(f"\n=== OK: enclosing function uses extractAlpineState/MergeHarness ({len(ok)}) ===")
    show(sorted(ok, key=lambda f: (f["file"], f["line"])))

    print(f"\nTotal call sites: {len(all_findings)}  |  suspects: {len(suspects)}")
    return 1 if suspects else 0


if __name__ == "__main__":
    sys.exit(main())
