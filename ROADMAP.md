# Phased roadmap

All phases after Phase Zero are proposals. This roadmap does not authorize implementation or deployment.

## Phase Zero — discovery and owner review

Delivered: source research, domain verification, 25-species selection backed by regional presence evidence, limited API/media experiments, operating instructions and architecture/media/seasonality plans. Measured findings and gaps are in [feasibility](docs/feasibility.md).

Acceptance: evidence has dates, source links, real outputs and honest limits; domain state independently verified; credentials excluded; sample assets have provenance and checksums; no application/deployment/bulk ingestion. **Review gate:** owner decides whether to authorize a bounded validation extension. Dataset feasibility is not yet fully established.

## Phase One — close data and review gates

Obtain an authorized Gibson County histogram download and at least two destination exports spanning a full annual cycle, or an approved historical eBird extract with sampling events. Inspect actual time-bin format, denominator and missing-value behavior before implementing a parser. Obtain Xeno-canto access and confirm current official API/search/license documentation. Recheck site terms and rights against intended use; resolve exact media license versions and credits.

Extend the 25-species pilot to an explicitly bounded review set: target 6–10 photographs and 2–3 recordings per species, with a gap matrix for required biological/field conditions. These quantities require new authorization. Include each mandatory pair in both modalities where meaningful. Record where a species rarely vocalizes; do not fabricate coverage to satisfy a numeric quota.

Acceptance proposals:

- All 25 species have traceable regional presence and confirmed taxonomy crosswalks; regional regular/rare/exceptional classes are independently reviewed.
- Full-year weekly evidence is available for the county and at least two destinations, with documented bins, effort support or explicit “denominator unknown,” and tested geographic fallback.
- At least three useful photo examples per species and two useful recordings for each audibly relevant species are approved by humans; all uncovered sex/age/season/flight/vocalization cells remain visibly incomplete.
- Every approved asset passes rights, creator, provenance and identification gates; all hard pairs receive independent second review or expert review. Blind re-review samples detect systematic labeling issues.
- Time at least 30 reviews across easy and hard strata. Record approval/rejection rates, escalation frequency and median/p90 minutes. Owner accepts extrapolated effort and the remaining coverage gaps.
- Resolve all critical ambiguous identities and rights before local learning tests. A single unaddressed disputed asset blocks that asset, not the whole research process.

If annual frequency or legal audio access cannot be secured economically, reduce scope or stop. Do not substitute recent counts for seasonality or restricted media for open media.

## Phase Two — local learning prototype

Only after Phase One review. Build a local 25-species React/Vite/Hono prototype backed by reviewed immutable content; two independent learner profiles; sight/audio quizzes; separate mastery and confusion tracking; explicit uncertainty answer; source attribution and progress export. Start with an inspectable spaced-repetition rule, then tune from use rather than adding opaque learning models.

Acceptance: the two owners can finish daily sessions and an outing deck; no external media calls during a session; learner histories remain independent; unseen examples test transfer; review/rights failures prevent content inclusion. Automated tests cover scheduling, profiles, content gates and ambiguity scoring. No deployment is implicit.

## Phase Three — authorized private production pilot

After a separate deployment/cost decision, provision isolated BirdAhead Workers/D1/R2 resources and secrets. Add authentication, migrations/backups, operational limits, versioned packs and selective offline support. Validate synchronization and profile isolation on the owners' actual phones. Test interrupted downloads, storage eviction, stale/revoked packs and progress retry without duplicate attempts.

Acceptance: clear rollback/recovery path, secret/attribution audit, restored database export, bounded spend and independent deploy verification. Measure actual usage before expanding.

## Phase Four — regional coverage and refinement

Derive the geographic union from approved regional data. Separate regular teaching species from uncommon/exceptional records. Expand only to fill demonstrated curriculum gaps, with incremental ingestion and review. Validate arrival/departure priorities across spring and fall, waterfowl periods and habitats. Add life-list import, comparison practice and mastery maps as user needs justify them.

Acceptance: stratified content audits, documented review cost, species-universe reconciliation and calibrated seasonal recommendations. Geographic expansion is configuration plus data and expert review.

## Delegation after authorization

Lower-cost coding agents can implement tightly specified tasks with fixtures and acceptance checks: histogram parser after format inspection; source-specific normalization; manifest/checksum validation; export/import utilities; duplicate clustering; license allowlist tests; a static coverage report; migration scaffolding and documented UI components after architecture approval. They can prepare candidate metadata and flag unknowns, never approve identification or rights.

Keep source-access/terms decisions, taxonomy split/lump resolution, difficult identification, human review adjudication, seasonal-model calibration, purchases and deployment authorization with the owner and suitable reviewers. Give each delegated task a fixed input, output, request budget, fixture and prohibition on secret logging or automatic production promotion. No sub-agents were used in this discovery run.
