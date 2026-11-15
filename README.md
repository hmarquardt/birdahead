# BirdAhead

**Learn the birds you're about to meet.**

A local, mobile-first learning app for two recreational birders in southwestern Indiana. Prepare for an outing with seasonal priorities, photo and audio practice, recall reveals and independent progress.

**Status: local MVP delivered; geographic expansion research continues independently.** All seven supplied 2016–2025 eBird county histograms are imported, with actual seasonal demonstrations. Production hosting remains off. No large EBD or modeled-raster download was undertaken.

## Try the local learner

Requires uv, Python 3.11+ and Node 22.13+ (verified here with Node 26). This checkout already has the private accepted media and imported profiles; a fresh clone deliberately does not contain them.

```sh
uv sync --locked
uv run python -m tooling.histograms
uv run python -m tooling.local_release
npm ci --prefix app --ignore-scripts
npm run local --prefix app
```

Open **http://127.0.0.1:8788** on this computer. Choose a county, outing date, learner and practice style. Here Now and Arriving Soon use separate rankings. The current accepted collection supports multiple-example practice for **14 species by sight and three by sound**. The full 25-species pilot remains visible in seasonal preparation; missing media coverage is explicit. Two learner profiles, uncertainty answers, directed confusions, simple spaced reinforcement and identification flags persist locally. Flagged media is hidden from both learners and excluded from progress. No live third-party API is needed during practice. Stop with Ctrl-C.

The app binds only to loopback; this is not yet a phone-accessible hosted PWA, an authenticated multiuser service or a complete offline-pack implementation. [Local use, data, limitations and checks](docs/local-mvp.md).

## Current evidence

- Seven exports, 737,866 original bytes, 48 native month-subdivision bins, 79,868 total checklist samples. All 25 pilot species matched in each county; source taxonomy version is not embedded and remains unknown.
- Winter/spring/summer/fall priorities demonstrably change for the same county. A future migration rise is evaluated independently of current reporting frequency. Reporting frequency is **not** the probability of an encounter.
- Authenticated Status and Trends file listing works using `EBIRD_ST_API_KEY`; no raster was downloaded. EBD/SED delivery and unattended refresh entitlement remain unverified. Recurring manual county downloads are rejected.
- Python/DuckDB/partitioned Parquet are validated on the small imported bootstrap dataset and synthetic source-shaped checklist tests. Real bulk throughput and EBD-to-histogram parity are not claimed.
- Existing automated media acceptance remains preliminary source/model corroboration, not independently calibrated biological certainty. Owner/expert audit findings and biological-subtype coverage remain gaps; the two-hour total owner-review cap remains in force.

See the [Phase One report](docs/phase-one.md), [geographic acquisition architecture](docs/geographic-acquisition.md) and [derived histogram evidence](experiments/histogram-validation.json).

## Project documents

| Document | Purpose |
| --- | --- |
| [PROJECT.md](PROJECT.md) | Canonical specification and current authorization |
| [AGENTS.md](AGENTS.md) | Operating boundary and credential convention |
| [ROADMAP.md](ROADMAP.md) | Delivered local scope and next acceptance gates |
| [Local MVP](docs/local-mvp.md) | Run, reset/export, flags and verification |
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
uv run python tooling/repo_check.py
```

Run the separate curation workbench with `uv run python -m tooling.workbench.server` at http://127.0.0.1:8765. It is not the learner app.

Load local credentials programmatically from `~/.config/secrets/shared.env`, respecting environment overrides: `EBIRD_API_KEY`, `XENO_CANTO_API_KEY`, `EBIRD_ST_API_KEY`. Never copy values into this repository or client code. Future deployment environments use Worker secrets and GitHub Actions secrets. Raw data, media, models, compiled private releases, learning databases and source captures stay ignored; only appropriate code/docs/aggregate evidence are published to [hmarquardt/birdahead](https://github.com/hmarquardt/birdahead). [Third-party notices](NOTICE.md).

`birdahead.com` is registered and verified through November 15, 2027, at $11.17 registration/quoted renewal; auto-renew is off. No production deployment or paid infrastructure has been created.
