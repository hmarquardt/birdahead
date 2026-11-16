# Roadmap — local learner and scalable geography

The Phase One amendment authorizes the local MVP concurrently with geographic data research. It supersedes the earlier Phase 0.5 application hold. Production deployment, paid infrastructure and large data acquisitions remain outside the boundary.

## Delivered local increment

- Imported all seven owner-supplied 2016–2025 eBird county exports. Original bytes remain private. Validated 48 native bins, sample rows, all 25 pilot species and ambiguous `0.0015` handling. Actual winter/spring/summer/fall and approaching-window demonstrations are recorded.
- Built the local React/TypeScript/Vite learner with a Hono/Node loopback API and SQLite state. Implemented county/date preparation, Here Now/Arriving Soon/reinforcement, sight/audio multiple choice and recall, uncertainty, two independent profiles, session limits, persistent progress, directed confusion and identification flags with suppression/progress exclusion.
- Practice uses existing automatically accepted media with at least two examples per species/modality: 14 photo species and three audio species. Missing difficult-pair coverage remains explicit; no new bulk ingestion or weakened acceptance was used to fill it.
- Validated authenticated S&T listing with the distinct shared key, small real-data DuckDB/partitioned-Parquet processing and a bounded source-shaped EBD/SED denominator kernel. No real EBD/SED or modeled raster was downloaded.
- Retained automated recreational curation, independent rights/biology gates, private reproducible manifests and the two-hour TOTAL owner-review constraint. Human/expert audit findings are still unavailable; source/model evidence is preliminary corroboration.

Acceptance evidence: Python tests, Hono API tests, TypeScript/build checks and real-media Chrome desktop/mobile smoke tests pass. The browser uses a disposable learner database; no owner practice or review was fabricated. [Current report](docs/phase-one.md), [local use](docs/local-mvp.md).

## Delivered Phase Two increment

- Derived a deterministic 100-species teaching universe from all seven county references (333 reconciled species, 25 pilot retained, unresolved names preserved privately). Histogram import now carries 100 species × 48 native bins × 7 counties.
- Added checkpointed, budgeted acquisition with per-species deficits, contributor/rights/resolution/source-support filters and retry limits. The practical Phase Two batch processed 23/100 species and 186 new candidates; accepted coverage rose from 55 to 193 assets (141 photographs, 52 recordings). Candidate targets are not acceptance claims; 68 species remain explicit gaps.
- Improved target-clarity screening (192/296 photos passed) and added 32 verified source-interval audio clips for intermittent recordings; 24 clips passed curation and parents remain in the catalog with derivative provenance.
- Learner release v2 adds data vintage/sample support, coverage tiers and gaps, a browsable accepted-media field guide, richer feedback/session summaries, seasonal deck coverage, mobile/touch improvements and compatibility-preserving session continuation. Flags reconcile to the workbench without consuming owner-review time.
- Added regression tests for expanded taxonomy, interrupted acquisition/resume, release compilation/compatibility and flag reconciliation.

Acceptance evidence: Python tests, Hono tests and TypeScript/build checks pass; real-media browser smoke remains the local acceptance gate. [Phase Two report](docs/phase-two.md), [local use](docs/local-mvp.md).

## Delivered Phase 2.1 increment

- Resumed at species 23/100 and completed the breadth pass at **100/100** using successive checkpointed batches, incremental 5 GB media baseline, cached requests/predictions, bounded four-worker downloads and a targeted high-priority replacement pass.
- Accepted coverage rose from **193 to 589 assets** (384 photographs, 205 recordings), with **83 sight-ready / 57 sound-ready** species, 18 meeting both targets and only **7 explicit gaps**. Seasonal top-25 decks are now 19–21 sight-ready and 16–19 sound-ready.
- Added a compact **589-object / 0.406 GB** delivery manifest with checksums, attribution, source/license restrictions and projected R2 free-tier storage of $0. Added a concise **117-asset** risk-stratified audit queue (~56 minutes at stated assumptions) without recording any owner review or fabricating approval.
- New tests cover incremental media budgets, replacement selection, delivery-manifest checksums/private-path exclusion and the earlier taxonomy/acquisition/release/flag suites. Real-media browser smoke passes on the 589-asset release.

Acceptance evidence: [Phase 2.1 report](docs/phase-two-1.md), [acquisition evidence](experiments/phase-two-acquisition.json), [delivery manifest](experiments/phase-two-delivery-manifest.json) and [audit queue](experiments/phase-two-audit-queue.json).

## Next local usability and reliability pass

The owners can use this local collection immediately; their field/use feedback will determine the next improvement. No access negotiation blocks use.

Acceptance criteria:

- Complete useful short sessions and county/date preparation with both learners; measure actual enjoyment, confusion and example repetition without calling this a mastery validation.
- Audit a statistical sample and selected high-risk examples, record actual time/findings, staying within 7,200 total owner-review seconds for the initial regional collection. Prefer replacement or smaller coverage over mandatory per-asset review or weaker gates.
- Connect learner flags to curation triage and versioned corrections. Preserve reports, revoke disputed examples, re-export content and exclude/repair affected attempts; flags are not automatic truth judgments.
- Improve explicit low-support indicators and supported parent fallback, directed-confusion scheduling, diversity and held-out example evaluation. Keep unverified sex/age/plumage labels unknown.

## Independent geographic acquisition track

Do not request recurring county/hotspot downloads. Use the seven exports only as bootstrap/reference data. [Scalable architecture and one-time access steps](docs/geographic-acquisition.md).

Acceptance criteria:

- Establish one approved broad regional EBD **and matching SED** grant/snapshot, terms and file size/decompression preflight before a separately authorized large acquisition. Clarify provider-supported unattended refresh; do not assume an undocumented download API or scrape a portal.
- Pin source/taxonomy/boundaries/filter configurations. Project raw columns into private year/coarse-region Parquet; deduplicate shared events consistently, retain valid zero-detection complete lists, record effort/coverage and retain integer numerators/denominators.
- Compare 2016–2025 county/native-bin denominators against all seven references before comparing species rates. Diagnose scope/snapshot/protocol/group/taxonomy and ambiguous marker differences. Publish discrepancy metrics; no parity claim from synthetic tests.
- Expand the bounded county/hotspot kernel into measured production ingestion only when a real source snapshot is available. Validate polygon precision, spatial adapter installation, sensitive locations, rolling calendars, sparse support and incremental snapshot reconciliation.
- Use the authenticated official S&T API for a pinned-version inventory, size preflight and one budgeted coarse-product extraction after intended-use terms are established. Keep standardized modeled values, historical frequencies and API v2 recent presence separate. Do not turn listing success into a raster-processing claim.
- Add regions through configuration/cache processing. A cached historical vintage is acceptable locally while provider delivery is unresolved; repetitive owner intervention is not.

## Private production pilot — separately authorized

After separate deployment approval, create isolated BirdAhead Workers/D1/R2 resources, authentication, migrations/backups and bounded usage. Validate on the owners' phones, then add selective offline packs. Test interrupted downloads, retry/idempotent progress, independent profiles, stale/revoked content and restored exports. Measure costs, verify deployed release and rollback. Local `vite build` is a compilation check, not a deployment authorization.

## Regional product expansion

Derive the regular teaching universe from supported annual geography and habitat, separating unusual/exotic historical records. The current histogram union has 333 unique current species-name matches; the earlier all-time API list has a different scope. Neither automatically becomes a teaching target. Expand media through lawful automation, calibrated operating points, deduplication and contributor diversity while preserving the two-hour total initial owner-review cap.

Add precise destination preparation, life-list import, offline packs, shared sessions, hands-free audio and mastery/confusion maps only after the core learning loop proves useful. Keep specialized model scores separate from calibrated probabilities; avoid claims of scientific certification.

## Suitable lower-cost coding tasks

Well-specified source adapters after actual header inspection, fixed-budget API clients with credential-redaction tests, deterministic manifest/crosswalk validators, local progress/flag exports, accessible UI components, low-support indicators and fixture-based regression tests are suitable. Keep policy/rights interpretation, biological audit judgments, access-grant scope, purchases and deployment decisions with the owner/lead. One bounded research agent assisted the current geographic investigation under the local Sites workflow; no independent agents acquired bulk data or changed infrastructure.
