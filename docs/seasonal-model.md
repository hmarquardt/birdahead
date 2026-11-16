# Geographic and seasonal occurrence strategy

November 15, 2026. All seven supplied annual county exports are imported and used in the local learner. The bulk EBD/SED and modeled-product lanes remain independently scoped validation work. See [current results](phase-one.md) and [scalable acquisition](geographic-acquisition.md).

## Geography and evidence

Use stable region and destination IDs independent of a particular source. Regions have parent relationships and versioned boundaries. Destinations may contain several source hotspots; named sites and management units must be reconciled by a human. Wabash River corridor is a geographic area, not a single interchangeable eBird hotspot. Habitat observations and access restrictions have their own provenance.

The pilot rectangle (37.7–39.2 N, 88.3–86.7 W) samples southwestern Indiana and adjoining Illinois/Kentucky. It is a discovery envelope, not a final service-area boundary. Authenticated eBird county lists establish a separate seven-county Indiana union; do not merge the two scopes without labeling them. [Regional evidence](../experiments/regional-species.json), [eBird evidence](../experiments/ebird-evidence.json).

Initial destination work:

| Destination | Observed or proposed mapping |
| --- | --- |
| Gibson County | Observed eBird `US-IN-051`, 29 hotspots |
| Cane Ridge | Observed Cane Ridge WMA `L320465`; verify specific outing unit/access |
| Gibson Lake | Observed Wildlife Habitat `L1872968` plus several perimeter/power-station hotspots; do not substitute one for the whole lake |
| Snakey Point | Observed Patoka River NWR–Snakey Point Marsh `L564337` |
| Sugar Ridge | Pike County fallback available; exact source hotspot grouping not yet verified |
| Goose Pond | Greene County fallback available; exact destination grouping/export not yet verified |
| Wabash/Illinois/Kentucky | Boundary/habitat definition and additional source-region reconciliation pending |

## Preserve different signals

| Signal | Meaning | Important limitation |
| --- | --- | --- |
| Historical reporting frequency | Complete checklists reporting species / eligible complete checklists in geographic/time scope | Observer effort, access, habitat and detection bias; not abundance |
| Modeled occurrence | Standardized model encounter estimate for stated conditions | Model assumptions, resolution/quality and unsupported cells |
| Modeled relative abundance | Model expected count with standardized effort/conditions | Different units from frequency or actual local population |
| Recent reports | Recent accepted/published presence evidence, dated and scoped | Positive and reporting-biased; absence from results is not absence from site |
| Migration activity | Aggregate aloft movement/forecast where authorized | Does not identify species or guarantee local stopover |
| Personal mastery | Learner difficulty by species/modality/challenge | Learning priority, not ecological likelihood |

Store all values with source/release, native interval, units, geography, effort support, quality, freshness and missingness. A UI may explain several signals together without presenting a false combined probability. [Cornell frequency description](https://support.ebird.org/en/support/solutions/articles/48001255130-ebird-bar-charts-and-graphs), [modeled products](https://ebird.github.io/ebirdst/articles/status.html), [BirdCast limits](https://birdcast.org/faq/).

## Annual data acquisition choices

The seven owner-supplied 2016–2025 exports are bootstrap references only, not a recurring workflow. `tooling.histograms` preserves all original bytes privately, validates the 48-column calendar and sample row, and creates 8,400 pilot species/bin rows. Native bins are days 1–7, 8–14, 15–21 and 22–month-end; they are not ISO weeks. See the primary [auk format documentation](https://docs.ropensci.org/auk/reference/process_barcharts.html).

All 25 pilot species match unique current authority common names, with scientific-name agreement against the existing versioned pilot crosswalk. The source body has no scientific names or taxonomy-release field: source version stays null, and the cached authority is 2026. Do not claim a source-version guarantee from a common-name match. Raw unmatched/non-species taxa remain private and excluded from numeric species joins. The exports contain 333 unique species-name matches across the seven counties, including uncommon records; this is not a final regular teaching universe.

The 79,868 sample-size sum is a reference aggregate, not an independently reconstructed count of birding events. Zero frequency with positive support is a reported non-detection. Missing row/value or zero support becomes unknown. Repeated literal `0.0015` cells can be smaller than one possible complete-checklist detection. All 72 such pilot cells retain their source value but have null numeric frequency and `possible_presence_marker` status. This is conservative ambiguity handling, not a verified undocumented sentinel decoding. Other fractions are checked for consistency with integer numerators at source rounding precision; no pilot cells fail that check. No detection counts are manufactured for these histogram rows. Full reference metadata, source hashes and scope assertions are retained.

Geography/year scope is asserted by the owner download context and filenames, not independently embedded in the bodies. The parser enforces all seven filenames, January–December and consistent 2016–2025 scope. [Import evidence and demonstrations](../experiments/histogram-validation.json).
An approved EBD plus sampling-event extract is preferable for explicit effort-aware denominators. Filter complete, valid protocols with declared effort bounds; document exclusions. Deduplicate checklist sampling events and handle shared group checklists according to source metadata. Include eligible checklists where the species was not detected in the denominator, never just positive species rows. Source sensitivity/privacy exclusions remain in force. For personal imports, never infer an exhaustive life list from recent public API sightings.

Status and Trends can supplement weak areas if access, product quality and terms support it. Clip and summarize authorized weekly rasters offline; store compact region summaries and model units. A model's predicted zero and a missing/unsupported value must remain distinct. Do not silently replace histogram frequency with modeled abundance. Current API v2 historical-date observations were tested, but they do not supply the annual denominator needed here.

## Proposed weekly model

Represent an annual cycle by explicit week midpoint/date intervals, using a defined periodic calendar rather than assuming ISO week numbering equals phenological week. Document leap-day and year-end behavior. Source-native bin mapping is versioned; 52-layer modeled products use their documented midpoints. Keep habitat and geographic scale attached to every summary.

For checklist data, begin with a circular kernel over nearby weeks and a recent multi-year window (proposal: five years). Estimate a smoothed reporting rate with numerator/denominator support. A possible sparse-data estimator is `(k + alpha*p_parent) / (n + alpha)`, where `k/n` are eligible reports/checklists and `alpha` is a calibrated parent pseudo-count. Never apply this formula to counts lacking `n`. Store raw support and label the result as a smoothed estimate. Effective sample size/interval estimates should account for repeat locations/observers, not assume every checklist is independent.

Provisional policy: below 30 eligible checklists in a seasonal window, show low support and fall back or blend toward a supported parent; calibrate this threshold using real coverage. A high report rate from one heavily visited habitat is not general county prevalence. Compare within similar habitats/effort strata and monitor destination sampling concentration. Avoid treating no checklists as zero occurrence.

Keep year/release windows to detect drift; test stable residents, early/late arrivals and major migration peaks against held-out years or destinations. Use expert review to validate plumage/vocalization relevance. No fitted weights, coverage calibration or arrival performance are claimed yet.

## Curriculum proposal

Use transparent relevance components: present seasonal rate, positive change over the next two-to-four weeks, narrow-window urgency, habitat/destination compatibility, learner weakness and a bounded recent-report modifier. Only combine comparable standardized components into a *learning priority score*, never label it an encounter probability. Cap unusual-report effects and preserve support warnings.

- **Always Around:** broad annual support and meaningful frequency across the year; requires enough observed weeks, not merely reports in January and July.
- **Here Now:** adequate current seasonal support for the chosen place/habitat, with fresh recent evidence shown separately.
- **Arriving Soon:** robust future prevalence and increasing seasonal rate over 14–28 days; suppress small noisy rises.
- **Passing Through:** concentrated annual window and evidence that local breeding/winter residency does not explain it; include both spring and fall windows where supported.
- **Personal Weaknesses:** due species/modality/challenge and directed confusions, bounded by outing relevance while retaining some long-term review.

Category overlap is useful. A migrant can be Here Now and Passing Through; a resident can also be a Personal Weakness. Show anticipated departures where a well-supported current window is closing. A destination deck freezes trip date, habitats, source versions and approved content; refresh before travel and expose stale/missing inputs.

## Phase Two teaching universe

`tooling.teaching_universe` reconciles every uniquely named source taxon against the cached target authority, then ranks candidates with explicit normalized components: year-round frequency/coverage, current seasonal rate, positive 14–28-day rise, recreational/confusion-pair value and media availability at selection time. The 25-species pilot is force-retained. The first 100-species universe contains 333 reconciled candidates, 100 selected and 81 unresolved or non-species source names across the seven exports; unresolved names remain excluded and are retained privately. This is a deterministic curriculum shortlist, not a claim of complete regional biodiversity.

The learner exposes the historical vintage (2016–2025), native-bin definition, per-species sample size and period, source-taxonomy unknown status and explicit media gaps. Additive content releases with the same taxonomy authority/version and source scope share a compatibility key, so learner progress and active sessions survive media expansion. A change to source scope or taxonomy requires a fresh session rather than silently reusing attempts.

The imported profiles now hold 100 species × 48 native bins × seven counties. Values retain source anomalies (including `0.0015`), zero-support missingness and unresolved rows. Copying the same 25 species into a larger universe does not change their definitions or imply split/lump equivalence.

## Implemented ranking and remaining validation

`tooling.seasonal.rank` maps a requested date onto native boundaries, including December-to-January wraparound. February 29 uses February 28 in the nonleap annual template. It evaluates the maximum available frequency at +14, +21 and +28 days, then a positive rise from current support. A zero current rate does not prevent arrival priority; unknown current support remains unknown. The demonstration score is `0.6 × current + 0.4 × positive rise`, a relative practice heuristic. Sampling support is retained, but the current score is not statistically adjusted for uneven effort, contributor dependence or low support. In the learner, Here Now excludes zero/unknown current rates, Arriving Soon independently orders positive rises, and reinforcement also uses personal history. Biological subtype and habitat are not yet scored.

Actual Gibson examples: winter January 15 favors Mallard, Snow Goose and Bufflehead; May 5 brings Indigo Bunting and Dickcissel into the leading set; July 15 emphasizes Indigo Bunting, Red-winged Blackbird and Dickcissel; September 10 increases shorebird and teal relevance. On April 1, Indigo Bunting has current frequency **0**, but the next 14–28-day maximum rises to **0.2151899**; Prothonotary Warbler rises from **0.0076531** to **0.3037975**. These are historical submitted-checklist patterns, not arrival forecasts or encounter probabilities. The [derived report](../experiments/histogram-validation.json) preserves all seven counties and four actual scenarios.

The strict earlier long-format parser remains available as an explicit interchange. `tooling.histograms` is the native adapter; `tooling.local_release` compiles the private runtime inputs. Synthetic parser and checklist tests validate mechanics; the real histograms validate parsing and seasonal changes. They do not establish EBD parity, learned weights or independent biological accuracy.

Remaining work: match EBD-derived county/bin denominators before rate comparisons; diagnose filters/snapshot/taxonomy differences; validate sparse-bin parent fallback, rolling windows, destination boundaries, habitat concentration, plumage/call relevance and held-out-year arrivals. One approved broad EBD/SED snapshot and provider-supported refresh clarification replace recurring owner exports. The local MVP is already usable without waiting for those tasks.
