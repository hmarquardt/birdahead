#!/usr/bin/env python3
"""Build the public annual discovery catalog from the existing reconciled profiles.

This is a derived-product export: it contains no raw county exports, local paths,
credentials or observation records. Discovery covers the 333 uniquely reconciled
species while the 100-species teaching/media universe remains separate.
"""
from __future__ import annotations
import argparse, json, statistics
from pathlib import Path
from tooling.histograms import native_bin
from tooling.seasonal import COUNTIES

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "experiments/private/occurrence/teaching-universe-candidates.json"
RELEASE = ROOT / "experiments/private/local-mvp/release.json"
OUT = ROOT / "app/public/discovery.json"
PAGE = ROOT / "app/public/discovery-page.json"
SCHEMA = "birdahead-discovery-v1"
VERSION = "2026-11-16.1"
BINS = 48
YEAR_ROUND_SHARE = 0.80
STRONG_SEASONAL_SHARE = 0.50
MIN_OBSERVED = 8
BIN_ROWS = {i: native_bin(i // 4 + 1, i % 4 + 1) for i in range(BINS)}


def _regional(values_by_county, sizes_by_county):
    frequencies, support, counties_used = [], [], []
    for i in range(BINS):
        weighted = []
        for county in COUNTIES:
            value = values_by_county.get(county, [None] * BINS)[i]
            size = sizes_by_county.get(county, [0] * BINS)[i]
            if value is not None and size and size > 0:
                weighted.append((value, size))
        total = sum(size for _, size in weighted)
        frequencies.append(round(sum(value * size for value, size in weighted) / total, 7) if total else None)
        support.append(total or None)
        counties_used.append(len(weighted))
    return {"frequency": frequencies, "support": support, "counties_used": counties_used, "metrics": _metrics(frequencies)}


def _species_assets(release_assets):
    counts = {}
    public_licenses = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
    for asset in release_assets:
        if asset.get("kind") not in {"photo", "audio"}:
            continue
        explicit = asset.get("public_delivery")
        if explicit is not True and not (explicit is None and str(asset.get("license_code") or "").lower() in public_licenses
                                         and asset.get("creator") and asset.get("license_url") and asset.get("source_url") and asset.get("attribution")):
            continue
        row = counts.setdefault(asset["species_code"], {"photos": 0, "audio": 0})
        row["photos" if asset["kind"] == "photo" else "audio"] += 1
    return counts



def _num(value):
    if value is None:
        return None
    value = float(value)
    if not 0 <= value <= 1:
        raise ValueError("frequency outside [0,1]")
    return round(value, 7)


def _metrics(values):
    observed = [i for i, value in enumerate(values) if value is not None]
    active = [i for i, value in enumerate(values) if value is not None and value > 0]
    known = [values[i] for i in observed]
    active_values = [values[i] for i in active]
    peak_indices = sorted(active, key=lambda i: (values[i], -i), reverse=True)[:3]
    peak = [{"index": i, **BIN_ROWS[i], "frequency": values[i]} for i in peak_indices]
    rises, falls = [], []
    for i in range(1, len(values)):
        before, after = values[i - 1], values[i]
        if before is None or after is None:
            continue
        delta = after - before
        if delta > 0:
            rises.append({"from_index": i - 1, "to_index": i, "delta": round(delta, 7)})
        elif delta < 0:
            falls.append({"from_index": i - 1, "to_index": i, "delta": round(delta, 7)})
    largest_rise = max(rises, key=lambda row: (row["delta"], -row["to_index"])) if rises else None
    largest_fall = min(falls, key=lambda row: (row["delta"], row["to_index"])) if falls else None
    active_share = len(active) / BINS
    maximum = max(known) if known else None
    minimum_active = min(active_values) if active_values else None
    if len(observed) < MIN_OBSERVED or len(active) < 2:
        classification = "insufficient"
    elif len(observed) >= 40 and active_share >= YEAR_ROUND_SHARE and (minimum_active or 0) >= 0.05:
        classification = "year_round"
    elif active_share <= STRONG_SEASONAL_SHARE or (maximum and minimum_active and maximum / minimum_active >= 4):
        classification = "strongly_seasonal"
    else:
        classification = "seasonal"
    return {
        "observed_bins": len(observed), "active_bins": len(active), "missing_bins": BINS - len(observed),
        "annual_mean": round(statistics.fmean(known), 7) if known else None,
        "max_frequency": maximum, "min_active_frequency": minimum_active,
        "peak_bins": peak, "largest_rise": largest_rise, "largest_fall": largest_fall,
        "classification": classification,
        "classification_rule": "insufficient if <8 observed or <2 active bins; year_round if >=40 observed and >=80% bins active and min active >=0.05; strongly_seasonal if <=50% bins active or max/min-active >=4; otherwise seasonal",
    }

def validate(catalog, release, candidates):
    errors = []
    species = catalog["species"]
    if len(species) != len(candidates):
        errors.append("species count does not match reconciled candidates")
    if len({row["code"] for row in species}) != len(species):
        errors.append("duplicate species code")
    for row in species:
        if set(row["counties"]) != set(COUNTIES):
            errors.append(f"{row['code']}: county coverage mismatch")
        for county, values in row["counties"].items():
            if len(values) != BINS:
                errors.append(f"{row['code']}/{county}: not 48 bins")
            if any(value is not None and not 0 <= value <= 1 for value in values):
                errors.append(f"{row['code']}/{county}: invalid frequency")
    selected = {row["ebird_species_code"]: row for row in release["species"]}
    for code, row in selected.items():
        public = next((x for x in species if x["code"] == code), None)
        if not public:
            errors.append(f"selected species missing from discovery: {code}")
            continue
        if not public["teaching"]:
            errors.append(f"selected species not marked teaching: {code}")
        for county in COUNTIES:
            profile = [r for r in release["profiles"][county]["rows"] if r["species_code"] == code]
            expected = [r["frequency"] for r in profile]
            actual = public["counties"][county]
            if len(expected) != BINS or any((a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9) for a, b in zip(expected, actual)):
                errors.append(f"selected profile mismatch: {code}/{county}")
    if sum(row["teaching"] for row in species) != len(selected):
        errors.append("teaching count mismatch")
    if len(catalog["bins"]) != BINS:
        errors.append("bin metadata mismatch")
    for i, row in enumerate(catalog["bins"]):
        expected = native_bin(i // 4 + 1, i % 4 + 1)
        if row["start"] != expected["start"] or row["end"] != expected["end"]:
            errors.append(f"calendar boundary mismatch at {i}")
    if errors:
        raise ValueError("; ".join(errors[:20]))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--release", type=Path, default=RELEASE)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--page", type=Path, default=PAGE)
    args = parser.parse_args()
    candidates = json.loads(args.candidates.read_text())["candidates"]
    release = json.loads(args.release.read_text())
    release_species = {row["ebird_species_code"]: row for row in release["species"]}
    assets = _species_assets(release["assets"])
    sizes_by_county = {county: release["profiles"][county]["metadata"]["sample_sizes"] for county in COUNTIES}
    species = []
    for row in sorted(candidates, key=lambda item: (item["common_name"], item["ebird_species_code"])):
        code = row["ebird_species_code"]
        if code in {item["code"] for item in species}:
            raise ValueError(f"duplicate candidate {code}")
        extra = set(row["county_values"]) - set(COUNTIES)
        if extra:
            raise ValueError(f"{code}: unsupported county values {sorted(extra)}")
        counties = {}
        for county in COUNTIES:
            raw = row["county_values"].get(county, [None] * BINS)
            values = [_num(value) for value in raw]
            sizes = row.get("county_sizes", {}).get(county) or sizes_by_county[county]
            if len(values) != BINS or len(sizes) != BINS:
                raise ValueError(f"{code}/{county}: invalid array length")
            if sizes != sizes_by_county[county]:
                raise ValueError(f"{code}/{county}: sample sizes differ from profile metadata")
            counties[county] = values
        selected = release_species.get(code)
        counts = assets.get(code, {"photos": 0, "audio": 0})
        species.append({
            "code": code, "name": row["common_name"], "scientific_name": row["scientific_name"], "taxon_id": row.get("taxon_id"),
            "teaching": selected is not None,
            "media": {"photos": counts["photos"], "audio": counts["audio"],
                      "field_guide": selected is not None, "photo_practice_ready": counts["photos"] >= 2,
                      "audio_practice_ready": counts["audio"] >= 2},
            "practice_ready": bool(selected and (counts["photos"] >= 2 or counts["audio"] >= 2)),
            "confusion_pair": selected.get("confusion_pair") if selected else None,
            "counties": counties,
        })
    for row in species:
        regional = _regional(row["counties"], sizes_by_county)
        regional.pop("metrics", None)
        row["regional"] = regional
    richness = {"by_county": {}, "regional": []}
    for county in COUNTIES:
        richness["by_county"][county] = [sum(1 for row in species if (row["counties"][county][i] or 0) > 0) for i in range(BINS)]
    richness["regional"] = [sum(1 for row in species if (row["regional"]["frequency"][i] or 0) > 0) for i in range(BINS)]
    page_species = sorted(species, key=lambda row: (_metrics(row["regional"]["frequency"])["max_frequency"] or 0, row["name"]), reverse=True)[:16]
    catalog = {
        "schema": SCHEMA, "version": VERSION, "generated_from_release": release.get("id"),
        "data_vintage": release.get("data_vintage"), "taxonomy": release.get("universe", {}).get("taxonomy"),
        "source_scope": release.get("universe", {}).get("source_scope"),
        "candidate_counts": release.get("universe", {}).get("candidate_counts"),
        "counties": {code: {"name": name, "sample_sizes": sizes_by_county[code], "checklist_total": sum(sizes_by_county[code])} for code, name in COUNTIES.items()},
        "bins": [{"index": i, **native_bin(i // 4 + 1, i % 4 + 1)} for i in range(BINS)],
        "richness": richness, "species": species,
        "regional_method": {
            "method": "checklist-sample weighted mean of available county-bin frequencies",
            "formula": "sum(frequency_county_bin * sample_size_county_bin) / sum(sample_size_county_bin)",
            "support_meaning": "sum of county-bin checklist samples; not a count of independent birding events",
            "missing_policy": "null frequencies and zero-support bins are excluded from the weighted mean; null is not absence",
            "calendar": "48 native eBird calendar bins, retained exactly; 2001 is a non-leap display template",
        },
        "classification_thresholds": {"minimum_observed_bins": MIN_OBSERVED, "year_round_active_share": YEAR_ROUND_SHARE, "strongly_seasonal_active_share": STRONG_SEASONAL_SHARE},
        "limitations": release.get("limitations", []) + [
            "Annual profiles are aggregated 2016–2025 reporting fractions, not year-by-year population trends.",
            "Historical reporting frequency is not abundance, encounter probability or a recent-sighting count.",
            "Missing values and zero-support bins remain distinct from observed zero reporting.",
            "Unresolved, non-species and split/lump-ambiguous source names remain excluded.",
        ],
    }
    validate(catalog, release, candidates)
    args.output.write_text(json.dumps(catalog, separators=(",", ":")) + "\n")
    page = {
        "schema": "birdahead-discovery-page-v1", "version": VERSION,
        "counts": {"species": len(species), "teaching": sum(row["teaching"] for row in species),
                   "with_field_guide_media": sum(row["media"]["field_guide"] for row in species),
                   "practice_ready": sum(row["practice_ready"] for row in species)},
        "featured": [{"code": row["code"], "name": row["name"], "peak": _metrics(row["regional"]["frequency"])["peak_bins"][:1], "classification": _metrics(row["regional"]["frequency"])["classification"]} for row in page_species],
        "richness": {"counties": {code: max(values) if values else 0 for code, values in richness["by_county"].items()}, "regional_max": max(richness["regional"]) if richness["regional"] else 0},
        "method": catalog["regional_method"],
    }
    args.page.write_text(json.dumps(page, indent=2) + "\n")
    print(json.dumps({"species": len(species), "teaching": sum(row["teaching"] for row in species), "bytes": args.output.stat().st_size, "page_bytes": args.page.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
