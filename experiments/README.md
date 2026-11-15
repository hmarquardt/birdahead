# Phase Zero experiments

Run date: 2026-11-15. These are bounded discovery tools and review evidence, not production ingestion or a licensed public dataset release.

## Evidence inventory

| Artifact | Meaning |
| --- | --- |
| `domain-registration.json` | Live price check, successful workflow and independent active-resource read; no contact/billing/credential details |
| `initial-probes.json` | Initial successful probes and access/challenge failures |
| `regional-species.json` | Derived iNaturalist all-time regional taxon counts, 294 entries/292 species; rectangle is a discovery envelope |
| `poc-species.json` | Exactly 25 selected taxa, actual regional counts, current eBird crosswalk and proposed test roles |
| `taxonomy-evidence.json` | Public authority versions; 2026 was latest at retrieval |
| `ebird-evidence.json` | Authenticated county union/hotspot/recent/historic aggregate results; no raw sightings or precise coordinates |
| `photo-candidates/` | Normalized asset metadata: 102 unique photos, all still unapproved; one quarantined by AI screening |
| `commons-candidates/` | Small Commons file/rights search snapshots; precise location/description metadata omitted |
| `sample-assets.json` | Three downloaded CC0 photo renditions with byte counts, SHA-256, dimensions and screening notes |
| `audio-samples.json` | Two Commons audio downloads, exact licenses/credits, source SHA-1 and local SHA-256, container metrics |
| `summary.json` | Offline candidate/metadata counts; download digests live in the separate sample manifests |
| `measurements.json` | Request metrics and sample byte totals, with explicit scope exclusions |
| `request-logs/` | URL, status, bytes and timing only; no request headers or credentials |
| `private/` (ignored) | Raw source captures and downloaded sample bytes, never an approved public asset store |

These artifacts include third-party metadata with source-specific rights. Cornell-derived crosswalks and summaries remain subject to [eBird data terms](https://www.birds.cornell.edu/home/ebird-data-access-terms-of-use/); original API datasets are not included in public files. Commons credit/license excerpts retain their source attribution and applicable [metadata/content terms](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia). No blanket software/media license is assigned to third-party material.

## Commands

```sh
uv sync --locked
uv run python -m unittest discover -s tests
uv run python tooling/discover.py summarize  # offline
```

The following commands use live sources only when their cached inputs/results are absent:

```sh
uv run python tooling/discover.py regional       # one regional iNaturalist metadata query
uv run python tooling/discover.py taxonomy       # public taxonomy and version metadata
uv run python tooling/discover.py ebird          # shared EBIRD_API_KEY; 7 county lists + 3 bounded probes
uv run python tooling/discover.py photos         # at most 25 iNaturalist queries, 3 observations/species
uv run python tooling/discover.py commons        # up to 12 two-result searches; prior run stopped on 429
uv run python tooling/discover.py samples        # at most 4 selected CC0 photo species; 3 had eligible samples
uv run python tooling/discover.py audio-samples  # at most 2 previously captured Commons candidates
```

No registration command is included: the purchase is complete and must not be replayed. Do not clear caches or restart source acquisition merely to reproduce a report. The failed Commons query was not retried in this run. Future runs must respect throttling/Retry-After; five-second pacing is a conservative local policy, not a verified quota.

Every Client-based command has a hard 40-request budget per invocation, no automatic retries, timeouts and response-size bounds. API calls are serial; iNaturalist requests are spaced by at least 1.1 seconds between starts. Commons future calls use five seconds. Photo candidates and sample manifests checkpoint completion; cached source responses are keyed by request URL. Cache files are private. File transfers use explicit source-host allowlists, bounded file sizes and manifest checksums. Commands do not approve or publish assets.

Local credentials: environment variable first, then programmatic parsing of `~/.config/secrets/shared.env`. `EBIRD_API_KEY` is sent only in the eBird header. The shared file supports literal `KEY=value`, quoted values, comments and optional `export`; it is parsed as data without shell execution/expansion. No platform-specific credential manager is used. Never print or copy values into this repository. No credential example value is needed to run offline checks. A later Worker uses Worker secrets; CI uses GitHub Actions secrets.

The cache freezes the first capture for its query; refreshing intentionally requires a separately identified capture/run and retained old evidence. Queries returning “latest” are reproducible from the retained capture, not guaranteed to return identical results from the live service later. A new checkout without ignored captures cannot reproduce authenticated/raw analyses offline; public summaries and manifests permit review, while an authorized recapture supplies inputs. The CLI is deliberately not a production scheduler or historical-data parser.

## Sampling limits

Photo queries use current species IDs, eastern North America (24–52 N, 100–60 W), Research Grade, wild observations and photo-license filters for CC0/CC BY/CC BY-SA. Take the latest three observations per species and up to two photos from each. This favors currently uploaded material and does not stratify sex, age, season or quality. Counts are conditional on those filters; they are not an overall open-license yield or a human approval rate.

Commons searches retrieve only two files per query, keyed by scientific name and media type; synonym-bearing historical results need taxonomy review. A search hit has no production identity guarantee. HTML-bearing credit fields are source evidence, not trusted UI markup.

The three CC0 photo samples were inspected by the assistant for visual issues only. A yellowlegs frame has multiple birds without a designated target and is quarantined. The other samples remain candidates. The two MP3s were verified against Commons byte size/SHA-1 and inspected with the local `afinfo` utility for container properties; this is not a listening/identity review. `afinfo` is not a required cross-platform dependency of the discovery CLI.

Manual owner/expert review was not performed. Its duration, usable yield, error rate and full-year seasonal coverage remain unknown. No assets have a production-approved state.

## Phase 0.5 commands and artifact handling

The earlier sections describe historical Phase Zero sampling, not the current acceptance policy. The amendment allows noncommercial licenses, specialized model gates and automatic acceptance with sampled audits. Candidate metadata/sample manifests/request logs are now also excluded from Git; aggregate reports remain reviewable. A fresh clone does not include those ignored files.

```sh
# Bounded local acquisition; each command checkpoints and keeps source captures private.
uv run python -m tooling.acquire xc-validate
uv run python -m tooling.acquire photos
uv run python -m tooling.acquire audio
# Optional supported replacements for observed gaps; total candidate-file ceiling 240.
uv run python -m tooling.acquire photo-alternates

# Isolated local inference. Weights stay private; no fine-tuning.
uv sync --project tooling/inference --locked
uv run --project tooling/inference python tooling/inference/download_models.py
uv run --project tooling/inference python tooling/inference/download_birdnet.py
uv run --project tooling/inference python tooling/inference/benchmark_images.py bioclip
uv run --project tooling/inference python tooling/inference/benchmark_images.py bioclip-2
uv run --project tooling/inference python tooling/inference/benchmark_audio.py
uv run --project tooling/inference python tooling/inference/screen_subjects.py

# Recompute automated gates, metadata-only accepted export and aggregate findings.
uv run python -m tooling.curation
uv run python -m tooling.workbench.server
uv run python -m tooling.seasonal status
```

Do not rerun acquisition simply to regenerate a report. The inference environment is locked separately; ordinary offline tests do not install Torch/TensorFlow. BioCLIP snapshots pin revisions/digests in private provenance files; BirdNET 2.4.0 bootstrap is version checked. Model packages and licenses are documented in the benchmark report. Object detection/localized classification is an additional target-clarity screen, not a biological authority.

The initial pass targeted five photo/three audio candidates per species. One capped replacement pass used supported, popular observations for failed comparisons/basic coverage; it deliberately changes the sampling distribution and may increase training-data overlap. Record both initial and expanded benchmark summaries; do not present the selected replacement pass as an unbiased accuracy estimate. No more than 240 candidate files may enter this experiment catalog.

Private artifacts include `phase05/catalog.json`, per-source caches, media, checkpoint weights, per-asset inference/threshold/control records, `reviews.sqlite` and `approved-media.json`. Public `benchmark-*.json`, `xc-validation.json` and `phase05-results.json` contain aggregate evidence only. The initial benchmark snapshots are labeled separately from the replacement pass. Full original Cornell exports and normalized annual profiles remain private.

Approved export does not certify biological truth. Automated/human/expert states and rights/biology gates stay separate. Artificially corrupted labels are private validation controls and never overwrite source records or enter accepted manifests. Human throughput is measured only from actual owner sessions; browser tests use an isolated fixture database and cannot be counted as owner review.
