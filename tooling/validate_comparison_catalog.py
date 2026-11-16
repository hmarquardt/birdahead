#!/usr/bin/env python3
"""Validate the public comparison catalog against the accepted release."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "app/public/comparisons.json"
RELEASE = ROOT / "experiments/private/local-mvp/release.json"

def main() -> int:
    catalog = json.loads(CATALOG.read_text())
    release = json.loads(RELEASE.read_text()) if RELEASE.exists() else None
    errors: list[str] = []
    if catalog.get("schema") != "birdahead-comparison-catalog-v1": errors.append("unexpected schema")
    if not catalog.get("version") or not catalog.get("review_status"): errors.append("version/review_status required")
    sources = catalog.get("sources", {})
    species = {row["ebird_species_code"]: row for row in (release or {}).get("species", [])}
    pairs = catalog.get("pairs", [])
    seen = set()
    for pair in pairs:
        pid = pair.get("id", "")
        if pid in seen: errors.append(f"duplicate pair {pid}")
        seen.add(pid)
        for side in ("left", "right"):
            code = pair.get(side, {}).get("code", "")
            if code not in species: errors.append(f"{pid}: unknown {side} species {code}")
        for trait in pair.get("traits", []):
            for source_id in trait.get("source_ids", []):
                if source_id not in sources: errors.append(f"{pid}: unknown source {source_id}")
        if not pair.get("gaps"): errors.append(f"{pid}: gaps must be explicit")
    if release:
        expected = {tuple(sorted((row["left"], row["right"]))) for row in release.get("confusion_pairs", [])}
        actual = {tuple(sorted((pair["left"]["name"], pair["right"]["name"]))) for pair in pairs}
        if expected != actual: errors.append(f"confusion pair coverage mismatch: expected={sorted(expected)} actual={sorted(actual)}")
    if errors:
        print("\n".join(errors)); return 1
    print(f"comparison catalog OK: {len(pairs)} pairs, {len(sources)} sources")
    return 0

if __name__ == "__main__":
    sys.exit(main())
