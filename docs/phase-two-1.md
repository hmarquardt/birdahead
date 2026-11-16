# Phase 2.1 — completing the initial collection

November 15, 2026. Local-only continuation of Phase Two. No production deployment, paid inference, additional county download, large geographic dataset or cloud resource was created.

## Resume and resource bounds

Resumed `experiments/private/phase05/expansion/state.json` at species **23/100** with 481 catalog candidates and 193 accepted assets. Verified **116 GiB free** before acquisition. Phase 2.1 used a separate **5 GB incremental media baseline** (`media_bytes_baseline = 187,817,080`), 900 total API requests, two retries per URL, 1,800 maximum catalog assets and four bounded media-download workers. API metadata requests remained sequential under provider pacing; only media transfers used concurrency, caching and backoff. Predictions were reused incrementally while model/preprocessing versions were unchanged.

Acquisition ran as successive checkpointed batches. The breadth pass processed the remaining **77 species** and completed at **100/100**. A bounded high-priority/confusion-pair replacement pass then added 147 candidates before its planned checkpoint.

| Acquisition measure | Phase 2.1 result |
| --- | ---: |
| Checkpoint | 100/100 species, complete |
| New assets this increment | 696 |
| Catalog candidates after expansion | 1,281 (including clips) |
| API requests / downloads / retries | 352 / 876 / 114 |
| Incremental media | **639,799,511 bytes (~640 MB)** |
| 5 GB increment used | ~12.8% |
| Main batch elapsed | 2,639 seconds |
| Free disk before start | 116 GiB |

The 5 GB cap was not approached, so storage was not a limiting factor. No rejected URL was re-downloaded; replacement queries started on later result pages.

## Collection result

| Measure | Phase Two | Phase 2.1 |
| --- | ---: | ---: |
| Checkpoint cursor | 23/100 | **100/100** |
| Catalog candidates | 481 | **1,281** |
| Accepted assets | 193 | **589** |
| Accepted photographs | 141 | **384** |
| Accepted recordings | 52 | **205** |
| Species sight-ready (≥2) | 30 | **83** |
| Species sound-ready (≥2) | 16 | **57** |
| Species with 5+ photos | 16 | **41** |
| Species with 3+ recordings | 10 | **37** |
| Species meeting both targets | 4 | **18** |
| Species with any accepted photo | 33 | **94** |
| Species with any accepted recording | 20 | **69** |
| Explicit practice gaps | 68 | **7** |

Coverage tiers: 18 both-target, 23 photo-only target, 52 practice-partial and 7 gap. The remaining gaps are the difficult Cooper's/Sharp-shinned Hawk, Downy Woodpecker, Red-tailed Hawk, Greater/Lesser Yellowlegs and Savannah Sparrow cells; weak media was not promoted to fill them.

Acceptance rates: **52.46% photographs** (384/732) and **37.34% audio** (205/549). A further 104 verified clips were extracted from intermittent recordings; 136 derivative candidates existed in total and **97 clips passed curation**.

Leading rejection reasons: no two adjacent dominant audio windows (304), no source-consistent localized photo target (241), target not dominant across enough of the recording (219), BioCLIP 2 threshold/margin failure (195), BioCLIP top-five corroboration (99), confusion-pair corroboration/margin (55), insufficient independent source identifiers (33), localized margin below risk threshold (11), audio calibration support (8), duplicates (7) and high-risk bird-seen evidence (6).

## Seasonal deck coverage

Reference county top-25 decks after Phase 2.1:

| Deck | Sight-ready | Sound-ready | Both targets |
| --- | ---: | ---: | ---: |
| Winter | 21 | 16 | 8 |
| Spring migration | 20 | 19 | 8 |
| Summer | 20 | 18 | 8 |
| Fall migration | 19 | 16 | 6 |
| Requested date (2026-11-15) | 21 | 16 | 8 |
| Arriving Soon now | 20 | 11 | 4 |

## Replacement and diversity

The bounded replacement pass prioritized the pilot, top-ranked species and confusion pairs with accepted-coverage gaps, using a 12-photo/8-recording candidate target and later result pages. It added **147** candidates before the bounded checkpoint. Contributor caps and source/rights/technical/model gates still applied. Accepted photographs come from 268 distinct contributors; accepted audio from 42 recordists. Contributor buckets include 219 photographers with one accepted image and 24 with three or more; audio includes 18 recordists with three or more accepted recordings. No source-asserted plumage/age label was turned into a verified label.

## Delivery manifest and R2 projection

`experiments/phase-two-delivery-manifest.json` contains **589 delivery objects / 436,400,934 bytes (0.406 GB)** with key, content type, bytes, SHA-256, creator, license, attribution, source, derivative notice, share-alike and commercial flags. Local paths, private captures, model weights and exact locations are excluded. `tooling.delivery_manifest` verifies every media checksum before writing it.

Projected R2 Standard object storage is **$0/month** under the 10 GB-month free allowance; at $0.015/GB-month the raw storage estimate is about **$0.006/month** before allowances. Class A/B operations and future egress are separate. No bucket or deployment was created.

Rights distribution: 318 iNaturalist CC BY-NC photos, 33 CC BY photos, 9 CC BY-NC-SA photos, 2 CC BY-SA photos and 22 CC0 photos; Xeno-canto recordings include 70 CC BY-NC-SA, 68 CC BY-NC-SA derivatives, 34 CC BY-SA, 28 CC BY-SA derivatives, 1 CC BY-NC, 1 CC BY-NC derivative and 3 CC0. **NC/SA assets restrict delivery to private household noncommercial use**, require attribution, and require share-alike for adaptations. Source-specific notes are retained in the manifest; no Cornell-restricted media is included.

## Audit queue

`experiments/phase-two-audit-queue.json` contains a concise **117-asset** stratified queue: 77 photographs (10 high-risk pair) and 40 recordings (6 high-risk pair), estimated at **55.7 minutes** at 20s/photo and 45s/audio. The workbench `audit` filter uses the same persistent `audit_selected` flags. This is a sample, not per-asset approval; owner review time remains **0 / 7,200 seconds** and no human/expert approval was fabricated.

## Verification, limitations and handoff

- **52 Python tests** pass, including universe derivation, interrupted/resumed acquisition, incremental media budgets, replacement selection, release validation/compatibility, flag reconciliation, delivery manifest checksums and private-path exclusion.
- **9 Hono tests** and TypeScript/Vite build pass. Real Chrome desktop/mobile smoke passes with the final 589-asset release, including field-guide search/gallery, coverage view, image decode, muted audio/ranges, flags, recall and no mobile overflow.
- One adversarial audio control (an American Black Duck source deliberately labelled Mallard) passed the counterfactual check; it is not an accepted production asset and highlights a real dabbling-duck confusion risk. All 72,468 deliberately wrong photo controls were rejected; the other 53,252 audio controls were rejected. Automatic acceptance remains preliminary source/model corroboration, not calibrated biological probability.
- The seven gaps, 52 practice-partial species and difficult comparison pairs remain explicit. Source taxonomy release is unknown. NC/SA licenses limit any future delivery to a private noncommercial household. No production deployment, paid infrastructure or additional manual county download occurred.

This is the Phase 2.1 review boundary.
