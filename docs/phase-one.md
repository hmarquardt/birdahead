# Phase One — bootstrap import, local learner and scalable geography

November 15, 2026. **Go for local recreational use now. Continue bulk/geographic validation independently. Hold cloud deployment, large downloads and claims of complete regional or biologically certified coverage.** The owner-supplied files removed the seasonal bootstrap blocker; long-term delivery uncertainty is not a local-app blocker.

## Annual import results

All seven original TXT files were discovered in the project root and moved byte-for-byte into ignored `experiments/private/occurrence/incoming/` before staging. Original total: **737,866 bytes**. Native importer: `tooling/histograms.py`; private full profiles/crosswalks; [derived results](../experiments/histogram-validation.json).

| County | Source taxon rows | Checklist sample sum | Sample-size range per bin |
| --- | ---: | ---: | ---: |
| Gibson | 370 | 14,238 | 105–790 |
| Greene | 357 | 21,947 | 132–977 |
| Knox | 291 | 3,074 | 22–265 |
| Pike | 309 | 2,584 | 13–169 |
| Posey | 292 | 2,842 | 23–154 |
| Vanderburgh | 329 | 22,222 | 202–1,226 |
| Warrick | 330 | 12,961 | 85–730 |

Every file has 48 bins and the same filename year/month scope, 2016–2025, January–December. Bins are days 1–7, 8–14, 15–21 and 22–month-end, confirmed against the primary [auk format description](https://docs.ropensci.org/auk/reference/process_barcharts.html). Sample values are integer counts. The **79,868** total is a sum of exported checklist sample counts, not independently reconstructed events. No county/bin sample size is zero, but some are sparse. [Cornell's frequency definition](https://support.ebird.org/en/support/solutions/articles/48001255130-ebird-bar-charts-and-graphs) describes complete-checklist proportions; these are not absolute encounter probabilities.

All 25 pilot species matched in each county: **8,400** imported species/bin rows. Exact unique common-name matches use the cached 2026 eBird authority and existing scientific-name crosswalk. Original bodies do not embed scientific names, taxonomy release, geography or years; source taxonomy remains **unknown**, scope comes from owner context/filenames. Unresolved/non-species labels are retained privately. The seven-export union contains 333 unique current species-name matches, including unusual species; it is not a validated regular teaching universe.

The importer found **72 pilot cells with literal `0.0015`**, often incompatible with any integer detection count at the supplied denominator. Their values and sample support remain preserved; numeric frequency becomes unknown with a possible-presence-marker flag. The marker's undocumented semantics are not asserted as verified. Other pilot values are consistent with integer numerators at source rounding precision, but histogram-derived detection counts are not manufactured. Missing cells/rows/zero denominators stay distinct from supported zero reporting.

## Actual seasonal demonstration

At the same location, Gibson County, the top eight scored species share only three members between winter and summer. These are descriptive historical patterns, with changing support and habitat/observer bias:

| Date | Examples among leading priorities | Selected native reporting fractions |
| --- | --- | --- |
| January 15 | Mallard, Snow Goose, Bufflehead, Dark-eyed Junco | Mallard 0.4654; Snow Goose 0.2987; Bufflehead 0.2421 |
| May 5 | Red-winged Blackbird, Indigo Bunting, Dickcissel | Indigo Bunting 0.3884; Dickcissel 0.2798 |
| July 15 | Indigo Bunting, Red-winged Blackbird, Dickcissel; yellowlegs also relevant | Indigo Bunting 0.6441; Dickcissel 0.4407 |
| September 10 | Mallard, yellowlegs, Blue-winged Teal, Turkey Vulture | Greater Yellowlegs 0.3821; Blue-winged Teal 0.3780 |

On **April 1**, Indigo Bunting has current fraction **0** but a 14–28-day maximum of **0.2151899**; Prothonotary Warbler rises from **0.0076531** to **0.3037975**. The independent Arriving Soon sort finds both without requiring current presence. Ranking uses a transparent current/rise heuristic, not a forecast probability. December/year wrap and leap-date mapping are deterministic. Full four-scenario demonstrations for all seven counties are retained in the evidence. No habitat-adjusted or held-out-year forecast skill is claimed.

## Scalable acquisition and processing

The recommended path is **approved coherent regional EBD + matching SED → Python/uv + DuckDB → private partitioned Parquet → configuration-defined profiles → compact runtime release**. SED defines complete-checklist denominators, including lists with no target detections; selected detections are joined afterward. Shared events, taxonomy rollup, effort selection, missingness and location precision must be explicit. County and hotspot aggregation are implemented in a bounded prototype kernel; arbitrary polygons/rolling calendars are designed but not implemented or validated. [Architecture, official references and one-time access steps](geographic-acquisition.md).

`tooling.checklists` is not a production bulk downloader. Its default 50 MB input ceiling prevents accidental large processing. Synthetic source-shaped tests verify zero-detection lists, shared-event deduplication, completeness conflicts, vetted detections, unknown bins, taxonomy ambiguity and separate county/hotspot support. **No real EBD/SED extract was acquired, so EBD-to-histogram parity remains unmeasured.** The seven histograms provide the reference denominators/rates for the next comparison; parsing them is not a substitute for that comparison.

Measured small-data experiment: DuckDB **1.5.6** wrote/read **8,400 actual imported profile rows** as seven county-partitioned Parquet outputs, **93,414 bytes** versus **2,285,483-byte JSON**, in **0.0305 seconds** for the measured operation. This is a tiny bootstrap demonstration, not a claim about million-row or spatial throughput. [Measurement](../experiments/duckdb-validation.json).

`EBIRD_ST_API_KEY` was present and worked for two official documented-2023 listing requests: Northern Cardinal 157 objects; Blackpoll Warbler 183; **23,028 response bytes**, zero rasters. Listing exposes relevant weekly occurrence/abundance and band-date paths. Latest release, raster sizes and local extraction quality are unverified. S&T modeled occurrence/abundance, descriptive historical reporting frequency and recent API presence remain separate; the current learner uses only the bootstrap historical lane.

Official references describe EBD request/download flows, but this work did not establish a public automated EBD download API or unattended regional refresh entitlement. No site was scraped or challenge bypassed. One broad approved snapshot supports many automatically configured locations. Provider-supported refresh needs clarification; if unavailable, keep a labeled cached historical vintage, not recurring county downloads. This does not delay the local learner.

## Local delivery and media integrity

Implemented React/TypeScript/Vite + Hono local learner: county/outing date, distinct Here Now/Arriving Soon/reinforcement, photo/audio choices and recall, uncertainty, two profiles, bounded sessions, persistent progress, directed confusions, simple spaced reinforcement and identification flags. Flags retain content/session context, suppress the example globally from practice and exclude affected attempts. Workbench triage integration remains future work. See [run instructions and limits](local-mvp.md).

The existing release has **55 automatically accepted assets**. Practice requires at least two examples: **40 photographs / 14 species**, **eight recordings / three species** before date/focus selection. The full 25-species benchmark remains; singleton or missing difficult-pair coverage is not promoted into adequate practice. No additional media acquisition, models or inference were needed for this increment. Source-verified, model-screened, automatically accepted, human-approved and expert-verified remain distinct. No human/expert approval or biological audit was fabricated. Source/model agreement and preliminary thresholds do not establish independently calibrated accuracy; correlated errors and training overlap remain risks. Owner review remains at the prior measured zero; the initial total cap remains two hours.

Rights evidence and attribution are preserved from the existing approved manifest; source/license links are visible before answers, full credits on reveal. No restricted Cornell media, raw exports, model weights, media binaries or local state are in public artifacts. Independent rights/biology gates and content checksums remain enforced. The initial collection is personal/recreational/noncommercial; the separate commercially compatible lane and model license constraints from Phase 0.5 still apply. No new commercial-use permission is inferred.

## Verification, costs and next steps

32 Python tests cover import/seasonal mechanics, credentials/media policy, review records and the new denominator kernel. Six Hono tests cover independent state, confusion, idempotency, expiry, flags/progress exclusion, recall, mutation security, media byte ranges and checksums. TypeScript/build checks pass. Real Chrome desktop/mobile checks use the actual accepted media and a **disposable** learning database, including image decode, muted real-audio playback, ranges, seasonal change, recall, flags and profiles. [Browser evidence](../experiments/local-mvp-browser.json). Owner learning/review databases were not populated by these tests.

Current incremental hosting/API subscription cost: **$0**; local disk/electricity not priced. Domain registration and quoted annual renewal remain $11.17. No cloud resources were created. A comparable seven-county raw historical extract is a planning estimate of roughly **0.8–4 GB TSV** based on 20–50 taxon rows/checklist and 500–1,000 bytes/row; incomplete lists and broader coverage can increase it. Size and decompression must be inspected before acquisition. Global S&T cubes may be large even for a tiny requested county; sizes remain unknown. The existing future Cloudflare estimate remains $0–$1/month incremental on available free/existing tiers, or roughly $5–$6 if a paid Worker plan becomes necessary, plus domain; not a deployment quote or new authorization.

Recommended order: **use the local learner**, improve flags/low-support UX and sampled biological quality within the owner time cap; independently establish a coherent EBD/SED grant and supported delivery, then compare all seven reference denominators; preflight one small/coarse modeled-product experiment. Cloud sync/PWA/offline packs, broader media coverage and precise habitat/hotspot/polygon products follow validated use and separate scope approval. Fixed-contract adapters, export tools, UI components and regression fixtures are suitable lower-cost coding-agent tasks. Rights decisions, access-grant scope and biological audit judgments require accountable review.
