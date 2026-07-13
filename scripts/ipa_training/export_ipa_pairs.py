#!/usr/bin/env python3
"""
Export (headword, IPA) pairs from a running LexCW instance to a JSON file.

Usage:
    python export_ipa_pairs.py \\
        --base-url http://localhost:5000 \\
        --api-key sw_xxxxxxxx \\
        --project-id 1 \\
        --output pairs.json

Then upload pairs.json to Colab and train with:
    python train_byt5_g2p.py --input pairs.json --output-dir ./byt5_model
"""

from __future__ import annotations

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexcw_client import LexCWClient, pairs_to_training_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Export IPA pairs to JSON")
    parser.add_argument("--base-url", required=True, help="LexCW base URL")
    parser.add_argument("--api-key", help="LexCW API key (Bearer sw_...)")
    parser.add_argument("--project-id", type=int, required=True, help="Project ID")
    parser.add_argument("--ipa-ws", default="seh-fonipa", help="IPA writing system")
    parser.add_argument("--output", default="pairs.json", help="Output JSON file")
    args = parser.parse_args()

    client = LexCWClient(
        base_url=args.base_url,
        api_key=args.api_key,
        project_id=args.project_id,
        ipa_writing_system=args.ipa_ws,
    )

    print(f"Fetching pairs from {args.base_url} ...")
    pairs = client.fetch_pairs()
    print(f"Got {len(pairs)} pairs")

    # Save in the format train_byt5_g2p.py expects
    data = [{"headword": p.headword, "ipa": p.ipa} for p in pairs]
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
