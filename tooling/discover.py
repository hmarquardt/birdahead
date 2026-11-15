"""Bounded public-source discovery. No deployment or production approval path."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "experiments/private"
UA = "BirdAhead-PhaseZero/0.1 (personal educational feasibility; birdahead.com)"
ALLOWED = {"cc0", "cc-by", "cc-by-sa"}
BBOX = {"swlat": 37.7, "swlng": -88.3, "nelat": 39.2, "nelng": -86.7}


def now():
    return datetime.now(timezone.utc).isoformat()


def credential(name):
    """Cross-platform shared file, environment overrides; never log values."""
    if name in os.environ:
        return os.environ[name]
    path = Path.home() / ".config/secrets/shared.env"
    if path.exists():
        for line in path.read_text().splitlines():
            parts = shlex.split(line, comments=True)
            if parts and parts[0] == "export":
                parts = parts[1:]
            if len(parts) == 1 and "=" in parts[0]:
                key, value = parts[0].split("=", 1)
                if key == name:
                    return value
    return None


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


class Client:
    def __init__(self, budget=40):
        self.budget, self.requests, self.last = budget, 0, 0.0
        self.log = []

    def get(self, base, params, *, header=None):
        # Only public, non-sensitive queries may be cached. Never put keys in URLs.
        if any(k.lower() in {"key", "token", "api_key"} for k in params):
            raise ValueError("Credential query parameters are not supported")
        url = base + "?" + urllib.parse.urlencode(params)
        cache = PRIVATE / "cache" / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if cache.exists():
            return json.loads(cache.read_text())
        if self.requests >= self.budget:
            raise RuntimeError("Request budget exhausted")
        interval = 5.0 if "wikimedia.org" in base else 1.1
        time.sleep(max(0, interval - (time.monotonic() - self.last)))
        start = time.monotonic()
        self.last = start
        self.requests += 1
        req = urllib.request.Request(url, headers={"User-Agent": UA, **(header or {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read(12_000_001)
                if len(raw) > 12_000_000:
                    raise ValueError("Response exceeds bounded size")
                data = json.loads(raw)
                status = response.status
        except urllib.error.HTTPError as exc:
            self.log.append({"url": url, "http_status": exc.code, "at": now()})
            # Stop, including on 429. No challenge bypass or retry loop.
            raise RuntimeError(f"HTTP {exc.code} from {urllib.parse.urlsplit(base).hostname}") from None
        self.log.append({"url": url, "http_status": status, "bytes": len(raw),
                         "seconds": round(time.monotonic()-start, 3), "at": now()})
        save(cache, data)
        return data


def license_url(code):
    if code == "cc0":
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    if code in {"cc-by", "cc-by-sa"}:
        # iNaturalist codes do not encode a version. Do not invent one.
        return None
    return None


def photo_candidate(obs, photo, target):
    code = photo.get("license_code")
    taxon = obs.get("taxon") or {}
    eligible = (code in ALLOWED and not photo.get("hidden") and not photo.get("flags")
                and not obs.get("flags") and obs.get("quality_grade") == "research"
                and taxon.get("id") == target["taxon_id"]
                and obs.get("community_taxon_id") == target["taxon_id"])
    original_url = photo.get("url")
    large_url = original_url.replace("/square.", "/large.") if original_url else None
    return {
        "source": "inaturalist", "source_record_id": obs["id"], "asset_id": photo["id"],
        "source_url": obs["uri"], "asset_page_url": f"https://www.inaturalist.org/photos/{photo['id']}",
        "media_url": large_url, "source_taxon_id": taxon.get("id"),
        "source_scientific_name": taxon.get("name"), "ebird_species_code": target.get("ebird_species_code"),
        "creator": obs.get("user", {}).get("name") or obs.get("user", {}).get("login"),
        "creator_basis": "observation owner; confirm photo credit at asset page",
        "attribution": photo.get("attribution"), "license_code": code, "license_url": license_url(code),
        "license_version": "1.0" if code == "cc0" else None,
        "rights_status": "open-license candidate; verify asset page and credit before publication" if eligible else "hold",
        "permitted_storage": True if eligible else None, "permitted_modification": True if eligible else None,
        "permitted_delivery": True if eligible else None, "share_alike": code == "cc-by-sa",
        "observation_license_code": obs.get("license_code"),
        "source_quality_grade": obs.get("quality_grade"), "community_taxon_id": obs.get("community_taxon_id"),
        "identification_agreements": obs.get("num_identification_agreements"),
        "identification_disagreements": obs.get("num_identification_disagreements"),
        "observed_on": obs.get("observed_on"), "geography": None,
        "location_policy": "exact coordinates intentionally excluded; eastern North America query envelope only",
        "source_obscured": obs.get("obscured"), "sex": None, "age": None, "plumage": None,
        "pose": None, "vocalization": None, "source_annotations": obs.get("annotations", []),
        "original_dimensions": photo.get("original_dimensions"), "technical_metrics": None,
        "sha256": None, "derivative_of": None, "derivative_recipe": None,
        "review_state": "candidate" if eligible else "quarantined",
        "identification_verified": False, "reviewer": None, "review_seconds": None,
        "retrieved_at": now(),
    }


def regional(client):
    params = {"taxon_id": 3, "quality_grade": "research", "captive": "false", **BBOX, "per_page": 500}
    data = client.get("https://api.inaturalist.org/v1/observations/species_counts", params)
    rows = [{"taxon_id": x["taxon"]["id"], "scientific_name": x["taxon"]["name"],
             "common_name": x["taxon"].get("preferred_common_name"), "rank": x["taxon"]["rank"],
             "observation_count": x["count"]} for x in data["results"]]
    save(ROOT / "experiments/regional-species.json", {"retrieved_at": now(), "parameters": params,
         "total_results": data["total_results"], "scope": "all-time Research Grade wild bird observations; rectangular study envelope, not regional frequency", "rows": rows})


def taxonomy(client):
    data = client.get("https://api.ebird.org/v2/ref/taxonomy/ebird", {"fmt": "json", "cat": "species"})
    versions = client.get("https://api.ebird.org/v2/ref/taxonomy/versions", {})
    selected = json.loads((ROOT / "experiments/poc-species.json").read_text())
    for row in selected:
        # Common names propose a crosswalk; persist scientific comparison for review.
        matches = [x for x in data if x["comName"] == row["common_name"]]
        if len(matches) != 1:
            raise ValueError(f"Crosswalk requires review: {row['common_name']}")
        m = matches[0]
        row.update(ebird_species_code=m["speciesCode"], ebird_scientific_name=m["sciName"],
                   taxonomy_authority="eBird/Clements", taxonomy_version=str(next(v["authorityVer"] for v in versions if v["latest"])),
                   crosswalk_status="name match; scientific identity requires review" if m["sciName"] != row["scientific_name"] else "scientific name agrees")
    save(ROOT / "experiments/poc-species.json", selected)
    save(ROOT / "experiments/taxonomy-evidence.json", {"retrieved_at": now(), "versions": versions,
          "selected_species": len(selected), "scope": "public taxonomy endpoint; full source response remains private"})


def ebird(client):
    key = credential("EBIRD_API_KEY")
    if not key:
        raise RuntimeError("EBIRD_API_KEY unavailable; set environment or shared.env")
    header = {"X-eBirdApiToken": key}
    counties = {"US-IN-051": "Gibson", "US-IN-125": "Pike", "US-IN-055": "Greene",
                "US-IN-129": "Posey", "US-IN-083": "Knox", "US-IN-163": "Vanderburgh", "US-IN-173": "Warrick"}
    universe = set()
    counts = {}
    for code, name in counties.items():
        codes = client.get(f"https://api.ebird.org/v2/product/spplist/{code}", {}, header=header)
        universe.update(codes)
        counts[code] = {"name": name, "reported_taxa": len(codes)}
    # Already captured public taxonomy; preserve only derived aggregate counts.
    taxonomy_data = client.get("https://api.ebird.org/v2/ref/taxonomy/ebird", {"fmt": "json", "cat": "species"})
    species_codes = {r["speciesCode"] for r in taxonomy_data}
    hotspots = client.get("https://api.ebird.org/v2/ref/hotspot/US-IN-051", {"fmt": "json"}, header=header)
    recent = client.get("https://api.ebird.org/v2/data/obs/US-IN-051/recent", {"back": 30, "maxResults": 30, "includeProvisional": "false"}, header=header)
    historic = client.get("https://api.ebird.org/v2/data/obs/US-IN-051/historic/2026/5/10", {"maxResults": 25}, header=header)
    selected = json.loads((ROOT / "experiments/poc-species.json").read_text())
    save(ROOT / "experiments/ebird-evidence.json", {"retrieved_at": now(), "county_counts": counts,
         "union_reported_taxa": len(universe), "union_species_only": len(universe & species_codes),
         "poc_species_in_union": sum(r["ebird_species_code"] in universe for r in selected),
         "gibson_hotspot_count": len(hotspots), "recent_records_returned": len(recent),
         "recent_request_cap": 30, "historic_date": "2026-05-10", "historic_records_returned": len(historic),
         "historic_request_cap": 25, "weekly_frequency_acquired": False,
         "scope": "all-time county species lists; recent and historic presence samples, not complete checklists or reporting frequency",
         "target_hotspot_name_matches": [{"name": h["locName"], "id": h["locId"]} for h in hotspots if any(t in h["locName"].lower() for t in ["gibson", "cane", "snakey"])],
         "sensitive_location_policy": "raw responses private; precise coordinates excluded from derived evidence"})
    print("eBird checks complete; public evidence contains aggregate counts only")


def photos(client):
    species = json.loads((ROOT / "experiments/poc-species.json").read_text())
    east = {"swlat": 24, "swlng": -100, "nelat": 52, "nelng": -60}
    for row in species:
        out = ROOT / f"experiments/photo-candidates/{row['taxon_id']}.json"
        if out.exists():
            continue
        data = client.get("https://api.inaturalist.org/v1/observations", {
            "taxon_id": row["taxon_id"], "quality_grade": "research", "captive": "false",
            "photo_license": ",".join(sorted(ALLOWED)), "per_page": 3,
            "order_by": "id", "order": "desc", **east})
        candidates = [photo_candidate(obs, p, row) for obs in data["results"] for p in obs.get("photos", [])[:2]]
        save(out, {"retrieved_at": now(), "taxon_id": row["taxon_id"], "common_name": row["common_name"],
             "query_observation_total": data["total_results"], "observations_sampled": len(data["results"]),
             "scope": "eastern North America; latest 3 observations, up to 2 photos each", "candidates": candidates})
        print(row["common_name"], len(candidates), "photo candidates", flush=True)


def commons(client):
    species = json.loads((ROOT / "experiments/poc-species.json").read_text())
    queries = [(r, "bitmap") for r in species[:8]] + [(r, "audio") for r in species if r["common_name"] in {"Northern Cardinal", "American Robin", "Downy Woodpecker", "Hairy Woodpecker"}]
    for row, kind in queries:
        out = ROOT / f"experiments/commons-candidates/{row['taxon_id']}-{kind}.json"
        if out.exists():
            continue
        data = client.get("https://commons.wikimedia.org/w/api.php", {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"filetype:{kind} {row['scientific_name']}", "gsrnamespace": 6, "gsrlimit": 2,
            "prop": "imageinfo", "iiprop": "url|size|sha1|extmetadata"})
        # File metadata only; no production identification inferred from search text.
        pages = list(data.get("query", {}).get("pages", {}).values())
        for page in pages:
            info = page["imageinfo"][0]
            info["extmetadata"] = {k: v for k, v in info.get("extmetadata", {}).items()
                if k in {"Artist", "Credit", "License", "LicenseShortName", "LicenseUrl",
                         "UsageTerms", "AttributionRequired", "Copyrighted", "Restrictions", "DateTimeOriginal"}}
        save(out, {"retrieved_at": now(), "requested_species": row["common_name"], "kind": kind,
             "review_state": "candidate", "identification_verified": False, "pages": pages})
        print(row["common_name"],kind,len(pages),"search candidates",flush=True)


def samples():
    from PIL import Image
    selected = {"Northern Cardinal", "Cooper's Hawk", "Downy Woodpecker", "Greater Yellowlegs"}
    manifest_path = ROOT / "experiments/sample-assets.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    existing = {x["asset_id"] for x in manifest}
    for path in sorted((ROOT / "experiments/photo-candidates").glob("*.json")):
        group = json.loads(path.read_text())
        if group["common_name"] not in selected:
            continue
        eligible = [x for x in group["candidates"] if x["review_state"] == "candidate" and x["license_code"] == "cc0"]
        if not eligible:
            continue
        asset = eligible[0].copy()
        if asset["asset_id"] in existing:
            continue
        url = asset["media_url"]
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "inaturalist-open-data.s3.amazonaws.com":
            raise ValueError("Unapproved sample host")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read(5_000_001)
            if len(raw) > 5_000_000 or not r.headers.get("Content-Type", "").startswith("image/"):
                raise ValueError("Sample rejected: size or media type")
        dest = PRIVATE / "samples" / f"inat-{asset['asset_id']}-large{Path(parsed.path).suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        with Image.open(dest) as im:
            im.verify()
        with Image.open(dest) as im:
            asset["technical_metrics"] = {"width": im.width, "height": im.height, "format": im.format,
                "bytes": len(raw), "fetch_seconds": round(time.monotonic()-start, 3)}
        asset.update(sha256=hashlib.sha256(raw).hexdigest(), local_path=str(dest.relative_to(ROOT)),
            downloaded_at=now(), transfer_note="source-hosted large rendition; no local edits")
        manifest.append(asset)
        save(manifest_path, manifest)
        time.sleep(1.1)
    print("Sample assets:",len(manifest))


def audio_samples():
    """At most two files, using previously captured Commons metadata."""
    import html
    import re
    manifest_path = ROOT / "experiments/audio-samples.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    existing = {x["source_record_id"] for x in manifest}
    for path in sorted((ROOT / "experiments/commons-candidates").glob("*-audio.json"))[:2]:
        group = json.loads(path.read_text())
        if not group["pages"]:
            continue
        page = group["pages"][0]
        if page["pageid"] in existing:
            continue
        info = page["imageinfo"][0]
        meta = info.get("extmetadata", {})
        license_name = meta.get("LicenseShortName", {}).get("value")
        license_link = meta.get("LicenseUrl", {}).get("value")
        artist = html.unescape(re.sub("<[^>]*>", "", meta.get("Artist", {}).get("value", "")))
        if license_name not in {"CC BY-SA 3.0", "CC BY-SA 4.0"} or not license_link or not artist:
            raise ValueError("Audio rights evidence incomplete")
        url = info["url"]
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org" or not parsed.path.endswith(".mp3"):
            raise ValueError("Unapproved audio sample host/type")
        start = time.monotonic()
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            raw = r.read(5_000_001)
        if len(raw) > 5_000_000 or len(raw) != info["size"] or hashlib.sha1(raw).hexdigest() != info["sha1"]:
            raise ValueError("Audio failed source byte count/checksum verification")
        dest = PRIVATE / "samples" / f"commons-{page['pageid']}.mp3"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        manifest.append({"source": "wikimedia_commons", "source_record_id": page["pageid"],
            "title": page["title"], "source_url": info["descriptionurl"], "media_url": url,
            "requested_species": group["requested_species"], "creator": artist,
            "license": license_name, "license_url": license_link,
            "attribution": f"{artist}, {page['title']}, {license_name}; source: {info['descriptionurl']}",
            "permitted_storage": True, "permitted_modification": True, "permitted_delivery": True,
            "share_alike": True, "review_state": "candidate", "identification_verified": False,
            "local_path": str(dest.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(),
            "source_sha1": info["sha1"], "bytes": len(raw), "fetch_seconds": round(time.monotonic()-start, 3),
            "downloaded_at": now(), "derivative_of": None, "derivative_recipe": None,
            "vocalization": None, "age": None, "sex": None, "quality_grade": None,
            "geography": "Minnesota, United States; source description; exact coordinates omitted",
            "reviewer": None, "review_seconds": None})
        save(manifest_path, manifest)
        time.sleep(1.1)
    print("Audio sample files:", len(manifest))


def summarize():
    groups = [json.loads(p.read_text()) for p in (ROOT / "experiments/photo-candidates").glob("*.json")]
    candidates = [c for g in groups for c in g["candidates"]]
    fields = ["creator", "attribution", "license_code", "license_url", "observed_on", "sex", "age", "plumage", "pose", "sha256"]
    species = json.loads((ROOT / "experiments/regional-species.json").read_text())
    summary = {"generated_at": now(), "species_count_results": species["total_results"],
        "species_rank_only": sum(r["rank"] == "species" for r in species["rows"]),
        "photo_species_queried": len(groups), "photo_species_with_candidates": sum(bool(g["candidates"]) for g in groups),
        "sampled_observations": sum(g["observations_sampled"] for g in groups), "photo_candidates": len(candidates),
        "eligible_candidates": sum(c["review_state"] == "candidate" for c in candidates),
        "quarantined_candidates": sum(c["review_state"] == "quarantined" for c in candidates),
        "license_counts": {k: sum(c["license_code"] == k for c in candidates) for k in sorted(ALLOWED)},
        "metadata_present": {k: sum(c.get(k) is not None and c.get(k) != "" for c in candidates) for k in fields},
        "human_verified_assets": sum(c["identification_verified"] for c in candidates),
        "audio_coverage": "not established; Xeno-canto unauthenticated request returned 401"}
    save(ROOT / "experiments/summary.json",summary)
    print(json.dumps(summary,indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["regional", "taxonomy", "ebird", "photos", "commons", "samples", "audio-samples", "summarize"], nargs="?", default="summarize")
    args = parser.parse_args()
    client = Client()
    try:
        if args.command == "audio-samples":
            audio_samples()
        elif args.command in {"samples", "summarize"}:
            globals()[args.command]()
        else:
            globals()[args.command](client)
    finally:
        if client.log:
            dest = ROOT / "experiments/request-logs" / f"{args.command}-{time.time_ns()}.json"
            save(dest, client.log)


if __name__ == "__main__":
    main()
