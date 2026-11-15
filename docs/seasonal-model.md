# Geographic and seasonal occurrence strategy

November 15, 2026. This is a proposed model. Presence access is observed; an annual local reporting-frequency curve has not yet been acquired or validated.

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

Start with owner-authorized histogram exports for Gibson County and two contrasting destinations. Inspect file encoding, taxon naming, native bin edges, date scope and denominator information. Published bar charts describe frequency, but this run did not inspect the export format. Do not assume 52 equally spaced weeks: some historical chart formats use month subdivisions. Preserve those native bins and map by actual dates before any weekly interpolation.

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

## Pilot validation still required

Obtain full-year frequency exports with support information or explicit denominator unknown; compare resident/winter/breeding/transient curves across county, wetland and woodland sites; test sparse-week fallback and wraparound; verify spring/fall plumage/call applicability; assess unusual-sighting caps against historical examples. Until then, pilot seasonal roles are test hypotheses, not validated local calendars.

## Phase 0.5 parser and current acquisition status

`tooling/seasonal.py` implements a strict deterministic long-format interchange parser and date-based ranking experiment. Its metadata requires source URL/digest, location, consistent years/taxonomy, explicit bin definition, units and missing-data semantics. Rows retain species code/scientific name, native start/end, reporting fraction and optional checklist count. Reject percent/fraction confusion, taxonomy mismatch, duplicate/gapped/overlapping bins and inconsistent scopes. Zero sample support becomes unknown rather than absence; blank/NA remains missing.

Approaching-window priority uses the rise to the maximum reporting fraction 14, 21 and 28 days ahead, independently of whether the current fraction is zero. The combined demonstration score is explicitly a curriculum priority, never an absolute encounter probability. Calendar wraparound is deterministic; source-native boundaries must be established before normalization.

The offline fixtures verify mechanics only. **No actual annual county exports have been imported, and no winter/spring/summer/fall demonstration with real frequencies is claimed.** A native eBird export adapter must be completed against the actual owner-supplied file format; the code does not guess its schema or convert an assumed 48-bin layout into ISO weeks. [Manual acquisition instructions](manual-downloads.md) select January–December 2016–2025 consistently for seven counties and optional hotspots. [Phase 0.5 status](phase-05.md).
