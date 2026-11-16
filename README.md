# BirdAhead

**Learn the birds you're about to meet.**

A public, mobile-first birding resource for southwestern Indiana. Prepare for an outing with seasonal priorities, a licensed field guide, photo/audio practice and independent progress; household sign-in is optional.

**Status: public, noncommercial educational release live at https://birdahead.com.** Seasonal exploration, Here Now/Arriving Soon, historical seasonal signals, the public field guide, eligible photos/recordings, photo/audio practice and guest summaries work without an account. Optional household sign-in preserves private D1 progress for Hank and Heather. The **589 accepted assets** remain behind the private R2 binding and public eligibility gate. No paid subscription, advertising, additional media acquisition or geographic expansion was undertaken.

## Try the local learner

Requires uv, Python 3.11+ and Node 22.13+ (verified here with Node 26). This checkout already has the private accepted media and imported profiles; a fresh clone deliberately does not contain them.

```sh
uv sync --locked
uv run python -m tooling.teaching_universe derive
uv run python -m tooling.histograms
uv run python -m tooling.local_release
uv run python -m tooling.expansion status
uv run python -m tooling.delivery_manifest
uv run python -m tooling.audit_queue
npm ci --prefix app --ignore-scripts
npm run local --prefix app
```

Open **http://127.0.0.1:8788** on this computer. Choose a county, outing date, learner and practice style. Here Now and Arriving Soon use separate rankings. The Phase 2.1 collection supports a 100-species teaching universe with an accepted-media field guide, coverage view and explicit gaps. Two learner profiles, uncertainty answers, directed confusions, simple spaced reinforcement and identification flags persist locally. Flagged media is hidden from both learners and excluded from progress; `uv run python -m tooling.flag_sync --apply` sends reports to the local curation workbench without consuming owner-review time. No live third-party API is needed during practice. Stop with Ctrl-C.

The local app binds only to loopback for development. The deployed PWA is at **https://birdahead.com**. Guests can explore and practice immediately; Hank/Heather sign-in is optional for server-backed progress. Selective offline learning packs, hands-free Road Trip mode, the public comparison explorer and the 333-species annual discovery explorer are available. [Local use](docs/local-mvp.md), [offline learning](docs/offline.md), [production operations](docs/production.md), [analytics](docs/analytics.md).

## Current evidence

- Seven exports, 737,866 original bytes, 48 native month-subdivision bins, 79,868 total checklist samples. The derived teaching universe has 100 species across 333 reconciled candidates (25 pilot retained); 81 unresolved source names remain excluded. Source taxonomy version is not embedded and remains unknown. Imported rows: 100 species × 48 bins × 7 counties.
- Discovery now exposes 333 reconciled species across seven counties and 48 native bins. The 100 teaching species retain separate media/practice coverage flags; regional values use checklist-sample weighting and missing bins remain null.
- Winter/spring/summer/fall priorities demonstrably change for the same county. A future migration rise is evaluated independently of current reporting frequency. Reporting frequency is **not** the probability of an encounter.
- Authenticated Status and Trends file listing works using `EBIRD_ST_API_KEY`; no raster was downloaded. EBD/SED delivery and unattended refresh entitlement remain unverified. Recurring manual county downloads are rejected.
- Python/DuckDB/partitioned Parquet are validated on the small imported bootstrap dataset and synthetic source-shaped checklist tests. Real bulk throughput and EBD-to-histogram parity are not claimed.
- Phase 2.1 completed the breadth pass: **100/100 species processed**, **589 accepted assets** (384 photographs, 205 recordings), **83 species sight-ready** and **57 sound-ready**. Forty-one species meet the five-photo target, 37 meet the three-recording target and 18 meet both. Only **7 explicit gaps** remain. The incremental 5 GB budget used ~640 MB; 116 GiB free was verified before acquisition.
- Verified audio clips are real intervals with parent provenance, never synthetic calls; 97 clips passed curation. Automated acceptance remains preliminary source/model corroboration, not biological certification. Owner/expert audits and biological-subtype coverage remain gaps; the two-hour total owner-review cap is unchanged and recorded owner-review time remains zero. The **117-asset sampled audit queue** (about 56 minutes at stated assumptions) is not a completed audit. The private delivery manifest covers 589 objects / 0.406 GB with R2 free-tier storage projected at $0; NC/SA licenses limit delivery to a private noncommercial household.

- Production: HTTPS at birdahead.com, `www` 308 redirect, dedicated D1/private R2 and an installable PWA. Public exploration, eligible media and guest practice work anonymously; private APIs/media/admin remain rejected without authentication. Both household identities are independent, real media/ranges were verified, public pages are crawlable and CFLab analytics ingestion was observed. Incremental infrastructure cost is $0 under current free allowances; public traffic/egress beyond those allowances is not claimed as zero; domain renewal remains $11.17/year.

See the [Phase Three report](docs/phase-three.md), [production operations](docs/production.md), [Phase 2.1 report](docs/phase-two-1.md), [Phase Two report](docs/phase-two.md), [media coverage evidence](experiments/phase-two-media.json), [teaching universe](config/geography/teaching-universe.json), [acquisition checkpoint evidence](experiments/phase-two-acquisition.json), [geographic acquisition architecture](docs/geographic-acquisition.md) and [derived histogram evidence](experiments/histogram-validation.json).

## Project documents

| Document | Purpose |
| --- | --- |
| [PROJECT.md](PROJECT.md) | Canonical specification and current authorization |
| [AGENTS.md](AGENTS.md) | Operating boundary and credential convention |
| [ROADMAP.md](ROADMAP.md) | Delivered local scope and next acceptance gates |
| [Phase Three report](docs/phase-three.md) | Public/private release, auth, verification and deferred work |
| [Analytics](docs/analytics.md) | CFLab registration, events, privacy and verification |
| [Offline learning](docs/offline.md) | Packs, storage, resume/integrity, offline practice and profile-bound sync |
| [Offline evidence](experiments/phase-four-offline.json) | Automated browser offline/reload/resume/reclamation checks |
| [Road Trip](docs/roadtrip.md) | Hands-free audio sessions, narration, Media Session and device checklist |
| [Road Trip evidence](experiments/phase-five-roadtrip.json) | Automated narration/timing/recovery checks |
| [Phase Six delivery](docs/phase-six.md) | Narration remediation, comparison explorer, adaptive practice and verification |
| [Phase Seven delivery](docs/phase-seven.md) | Discovery separation, explorer behavior and verification |
| [Annual discovery](docs/discovery.md) | 333-species occurrence explorer, weighted regions, calendar bins and learning integration |
| [Discovery evidence](experiments/phase-seven-discovery.json) | Automated browser/catalog validation evidence |
| [Comparative learning](docs/comparison.md) | Public comparison explorer, cited catalog, adaptive practice and offline notes |
| [Narration remediation](docs/narration-remediation.md) | Kokoro replacement provenance and historical exposure |
| [Comparison evidence](experiments/phase-six-comparison.json) | Automated comparison/catalog/practice checks |
| [Search Console](docs/search-console.md) | CFLab GSC mapping, sitemap and owner verification handoff |
| [eBird notification](docs/ebird-public-notice.md) | Prepared derived-product notification for owner review |
| [Production operations](docs/production.md) | Resources, auth, publishing, backup/rollback and gates |
| [Public evidence](experiments/phase-three-public.json) | Anonymous exploration, guest practice, SEO and private-boundary checks |
| [Production evidence](experiments/phase-three-production.json) | Authenticated household smoke results and deployed health/release |
| [Production inventory](experiments/phase-three-inventory.json) | Dedicated resources, release, costs, security and backups |
| [Rollback check](experiments/phase-three-rollback.json) | Same-release D1 pointer rollback evidence |
| [Phase 2.1 report](docs/phase-two-1.md) | Breadth/replacement completion, delivery, R2 and audit queue |
| [Phase Two report](docs/phase-two.md) | Universe, expansion, acceptance, coverage and handoff |
| [Local MVP](docs/local-mvp.md) | Run, reset/export, flags and verification |
| [Teaching universe](config/geography/teaching-universe.json) | Priority ranks, selection inputs and unresolved counts |
| [Expansion command](tooling/expansion.py) | Bounded resumable acquisition and checkpoint state |
| [Acquisition evidence](experiments/phase-two-acquisition.json) | Budgets, checkpoint, failures and candidate counts |
| [Media coverage](experiments/phase-two-media.json) | Before/after acceptance, reasons, decks and storage |
| [Audio segments](experiments/audio-segments.json) | Verified interval extraction criteria and counts |
| [Flag reconciliation](experiments/flag-reconciliation.json) | Learner-report intake status and budget evidence |
| [Delivery manifest](experiments/phase-two-delivery-manifest.json) | R2 object keys, rights, attribution and projected storage |
| [Audit queue](experiments/phase-two-audit-queue.json) | Concise risk-stratified sampled owner-audit queue |
| [Phase Eight report](docs/phase-eight.md) | Measured source/resource access, reproducible pipeline, destinations and publication runbook |
| [Regional source request](docs/phase-eight-owner-request.md) | One consolidated EBD/SED access, refresh and public S&T permission action |
| [Geographic expansion manifest](config/geography/expansion.json) | Indiana → Illinois → Kentucky order, source schemas and release gates |
| [Historical processing engine](tooling/geographic_engine.py) | Private typed ingestion, shared denominators, native profiles and content-addressed Parquet |
| [Geographic validation](experiments/phase-eight-validation.json) | Seven real references; EBD comparison explicitly blocked until source delivery |
| [Modeled experiment](experiments/phase-eight-modeled.json) | Actual authenticated inventories, sizes, transfers and coarse spatial extraction |
| [Geographic acquisition](docs/geographic-acquisition.md) | EBD/SED, S&T, caching, sizes and access limits |
| [Seasonal model](docs/seasonal-model.md) | Native bins, missingness and ranking |
| [Architecture](docs/architecture.md) | Runtime/data separation and costs |
| [Data sources](docs/data-sources.md) | Verified APIs and source terms |
| [Media policy](docs/media-policy.md) | Automated acceptance, rights and sampled audits |
| [Phase 0.5 report](docs/phase-05.md) | Historical media/model benchmarks and coverage |
| [Workbench](docs/workbench.md) | Local curation, review budget and manifests |
| [Bootstrap download record](docs/manual-downloads.md) | Completed one-time import; no recurring owner downloads |
| [Feasibility](docs/feasibility.md) | Current recommendation and historical Phase Zero evidence |
| [Decisions](docs/decisions/README.md) | Architectural decision records |

## Development and credentials

```sh
uv run python -m unittest discover -s tests
npm test --prefix app
npm run build --prefix app
uv run --with playwright python -m tooling.learner_browser_smoke
uv run --with playwright python -m tooling.production_smoke --base https://birdahead.com --browser
uv run --with playwright python -m tooling.public_smoke --base https://birdahead.com --browser
uv run python tooling/repo_check.py
```

Run the separate curation workbench with `uv run python -m tooling.workbench.server` at http://127.0.0.1:8765. It is not the learner app.

Load local credentials programmatically from `~/.config/secrets/shared.env`, respecting environment overrides: `EBIRD_API_KEY`, `XENO_CANTO_API_KEY`, `EBIRD_ST_API_KEY`. Never copy values into this repository or client code. Future deployment environments use Worker secrets and GitHub Actions secrets. Raw data, media, models, compiled private releases, learning databases and source captures stay ignored; only appropriate code/docs/aggregate evidence are published to [hmarquardt/birdahead](https://github.com/hmarquardt/birdahead). [Third-party notices](NOTICE.md).

`birdahead.com` is registered and verified through November 15, 2027, at $11.17 registration/quoted renewal; auto-renew is off. The private Worker/D1/R2 release is deployed; no paid subscription or additional paid infrastructure was created.
