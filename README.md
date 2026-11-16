# BirdAhead

**Learn the birds you're about to meet.**

A local, mobile-first learning app for two recreational birders in southwestern Indiana. Prepare for an outing with seasonal priorities, photo and audio practice, recall reveals and independent progress.

**Status: Phase Two local content expansion delivered; production hosting remains off.** The local teaching universe now has **100 species** derived from all seven supplied 2016–2025 eBird county histograms. Media expansion, verified audio clips, the field-guide/coverage UI and flag-to-workbench reconciliation are implemented. No large EBD/SED or modeled-raster download was undertaken; no cloud resource was created.

## Try the local learner

Requires uv, Python 3.11+ and Node 22.13+ (verified here with Node 26). This checkout already has the private accepted media and imported profiles; a fresh clone deliberately does not contain them.

```sh
uv sync --locked
uv run python -m tooling.teaching_universe derive
uv run python -m tooling.histograms
uv run python -m tooling.local_release
uv run python -m tooling.expansion status
npm ci --prefix app --ignore-scripts
npm run local --prefix app
```

Open **http://127.0.0.1:8788** on this computer. Choose a county, outing date, learner and practice style. Here Now and Arriving Soon use separate rankings. The Phase Two collection supports a 100-species teaching universe with an accepted-media field guide, coverage view and explicit gaps. Two learner profiles, uncertainty answers, directed confusions, simple spaced reinforcement and identification flags persist locally. Flagged media is hidden from both learners and excluded from progress; `uv run python -m tooling.flag_sync --apply` sends reports to the local curation workbench without consuming owner-review time. No live third-party API is needed during practice. Stop with Ctrl-C.

The app binds only to loopback; this is not yet a phone-accessible hosted PWA, an authenticated multiuser service or a complete offline-pack implementation. [Local use, data, limitations and checks](docs/local-mvp.md).

## Current evidence

- Seven exports, 737,866 original bytes, 48 native month-subdivision bins, 79,868 total checklist samples. The derived teaching universe has 100 species across 333 reconciled candidates (25 pilot retained); 81 unresolved source names remain excluded. Source taxonomy version is not embedded and remains unknown. Imported rows: 100 species × 48 bins × 7 counties.
- Winter/spring/summer/fall priorities demonstrably change for the same county. A future migration rise is evaluated independently of current reporting frequency. Reporting frequency is **not** the probability of an encounter.
- Authenticated Status and Trends file listing works using `EBIRD_ST_API_KEY`; no raster was downloaded. EBD/SED delivery and unattended refresh entitlement remain unverified. Recurring manual county downloads are rejected.
- Python/DuckDB/partitioned Parquet are validated on the small imported bootstrap dataset and synthetic source-shaped checklist tests. Real bulk throughput and EBD-to-histogram parity are not claimed.
- Phase Two accepted coverage rose from **55 to 193 assets** (141 photographs, 52 recordings), with 30 species sight-ready and 16 sound-ready. Sixteen species meet the five-photo target and ten meet the three-recording target; four meet both. Sixty-eight teaching species remain explicit gaps. Media expansion stopped at a practical 23/100-species checkpoint; the bounded state is resumable.
- Verified audio clips are real intervals with parent provenance, never synthetic calls; 24 clips passed curation. Automated acceptance remains preliminary source/model corroboration, not biological certification. Owner/expert audits and biological-subtype coverage remain gaps; the two-hour total owner-review cap is unchanged and recorded owner-review time remains zero. The 40-asset sampled audit queue is not a completed audit.

See the [Phase Two report](docs/phase-two.md), [media coverage evidence](experiments/phase-two-media.json), [teaching universe](config/geography/teaching-universe.json), [acquisition checkpoint evidence](experiments/phase-two-acquisition.json), [geographic acquisition architecture](docs/geographic-acquisition.md) and [derived histogram evidence](experiments/histogram-validation.json).

## Project documents

| Document | Purpose |
| --- | --- |
| [PROJECT.md](PROJECT.md) | Canonical specification and current authorization |
| [AGENTS.md](AGENTS.md) | Operating boundary and credential convention |
| [ROADMAP.md](ROADMAP.md) | Delivered local scope and next acceptance gates |
| [Phase Two report](docs/phase-two.md) | Universe, expansion, acceptance, coverage and handoff |
| [Local MVP](docs/local-mvp.md) | Run, reset/export, flags and verification |
| [Teaching universe](config/geography/teaching-universe.json) | Priority ranks, selection inputs and unresolved counts |
| [Expansion command](tooling/expansion.py) | Bounded resumable acquisition and checkpoint state |
| [Acquisition evidence](experiments/phase-two-acquisition.json) | Budgets, checkpoint, failures and candidate counts |
| [Media coverage](experiments/phase-two-media.json) | Before/after acceptance, reasons, decks and storage |
| [Audio segments](experiments/audio-segments.json) | Verified interval extraction criteria and counts |
| [Flag reconciliation](experiments/flag-reconciliation.json) | Learner-report intake status and budget evidence |
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
uv run python -m unittest discover -s tests          # 48 tests
npm test --prefix app                                  # 9 tests
npm run build --prefix app
uv run --with playwright python -m tooling.learner_browser_smoke
uv run python tooling/repo_check.py
```

Run the separate curation workbench with `uv run python -m tooling.workbench.server` at http://127.0.0.1:8765. It is not the learner app.

Load local credentials programmatically from `~/.config/secrets/shared.env`, respecting environment overrides: `EBIRD_API_KEY`, `XENO_CANTO_API_KEY`, `EBIRD_ST_API_KEY`. Never copy values into this repository or client code. Future deployment environments use Worker secrets and GitHub Actions secrets. Raw data, media, models, compiled private releases, learning databases and source captures stay ignored; only appropriate code/docs/aggregate evidence are published to [hmarquardt/birdahead](https://github.com/hmarquardt/birdahead). [Third-party notices](NOTICE.md).

`birdahead.com` is registered and verified through November 15, 2027, at $11.17 registration/quoted renewal; auto-renew is off. No production deployment or paid infrastructure has been created.
