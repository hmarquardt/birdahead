# BirdAhead

**Learn the birds you're about to meet.**

A proposed mobile-first learning platform for two recreational birders in southwestern Indiana, combining sight/sound practice, local annual occurrence and individual learning history.

**Status: Phase 0.5 local validation. Production development and deployment remain on hold.** Phase Zero findings and architecture are accepted. The automated-curation amendment replaces mandatory human approval of every asset with evidence-backed automated gates and sampled audits, within a two-hour total owner-review budget.

The current tools retrieve bounded candidates, benchmark BioCLIP/BioCLIP 2 and BirdNET locally, record independent rights/biology decisions and export reproducible accepted-media manifests. Per-species thresholds are preliminary source-proxy operating points, not calibrated biological probabilities. Annual eBird exports are still required before a real seasonal curriculum demonstration can be claimed. See [current findings](docs/phase-05.md) and [aggregate results](experiments/phase05-results.json).

`birdahead.com` is registered through Cloudflare, verified active through November 15, 2027; registration and quoted renewal were $11.17 USD. Auto-renew is off. [Evidence](experiments/domain-registration.json).

## Documents

| Document | Purpose |
| --- | --- |
| [PROJECT.md](PROJECT.md) | Canonical specification, including automated acceptance and future identification flags |
| [AGENTS.md](AGENTS.md) | Authorized boundary and shared credential convention |
| [ROADMAP.md](ROADMAP.md) | Validation gates, two-hour review constraint and proposed MVP |
| [Phase 0.5 findings](docs/phase-05.md) | Acquisition, models, calibration, coverage, costs and remaining blockers |
| [Media policy](docs/media-policy.md) | Automated tiers, separate rights/biology gates and sampled audits |
| [Workbench](docs/workbench.md) | Run the local review interface and export accepted media |
| [Manual downloads](docs/manual-downloads.md) | Seven consistent official eBird county histogram exports |
| [Seasonal model](docs/seasonal-model.md) | Geographic/temporal signals and parser status |
| [Architecture](docs/architecture.md) | Proposed runtime/data separation and costs |
| [Data sources](docs/data-sources.md) | Source access, terms and updated authenticated findings |
| [Historical Phase Zero findings](docs/feasibility.md) | Original evidence, with superseded assumptions identified |
| [Decision records](docs/decisions/README.md) | Accepted scope and policy changes |

## Run local tools

Requires Python 3.11+ and uv; the inference environment separately uses Python 3.12.

```sh
uv sync --locked
uv run python -m unittest discover -s tests
uv run python -m tooling.workbench.server
```

Open http://127.0.0.1:8765 for the local workbench. No source credentials reach the browser. Original media, full source captures, inference evidence and review databases remain in ignored private storage and are not part of a fresh clone.

[Experiment instructions](experiments/README.md) describe bounded acquisition, inference reproduction and exports. Local credentials are read programmatically from `~/.config/secrets/shared.env`, respecting environment overrides. Use `EBIRD_API_KEY` and `XENO_CANTO_API_KEY`; never copy their values into the project. Future Workers/CI use Worker secrets/GitHub Actions secrets.

The verified remote is [hmarquardt/birdahead](https://github.com/hmarquardt/birdahead). Documentation, code, locks and aggregate evidence may be committed after `uv run python tooling/repo_check.py`; restricted media and raw authenticated exports must not be pushed. See [third-party notices](NOTICE.md).
