# BirdAhead

**Learn the birds you're about to meet.**

BirdAhead is a proposed mobile-first bird identification learning platform for two recreational birders in southwestern Indiana. It prepares learners for likely encounters by sight and sound, using geography, weekly seasonality and individual learning history.

**Status: Phase Zero discovery — production development is on hold for owner review.** Research and bounded local experiments were completed on November 15, 2026. Open photo candidate retrieval works; human verification, broad audio coverage and local weekly occurrence acquisition remain review gates. No production application or infrastructure has been deployed.

`birdahead.com` was registered through Cloudflare for $11.17 USD. A separate API read verified active status and expiry on November 15, 2027. Quoted renewal: $11.17; auto-renew off. See [registration evidence](experiments/domain-registration.json).

## Review documents

| Document | Purpose |
| --- | --- |
| [PROJECT.md](PROJECT.md) | Canonical product specification |
| [AGENTS.md](AGENTS.md) | Agent scope, credential convention and operating rules |
| [ROADMAP.md](ROADMAP.md) | Phases, acceptance criteria and delegation |
| [Feasibility](docs/feasibility.md) | Measurements, uncertainties and recommendation |
| [Data sources](docs/data-sources.md) | Verified capabilities, access and rights constraints |
| [Media policy](docs/media-policy.md) | Provenance, licenses, verification and review workflow |
| [Seasonal model](docs/seasonal-model.md) | Weekly geographic occurrence and curriculum design |
| [Architecture](docs/architecture.md) | Proposed runtime, pipeline and costs |
| [Decisions](docs/decisions/README.md) | Accepted boundaries and proposed technical choices |
| [Experiments](experiments/README.md) | Commands, evidence and limits of reproducibility |

## Local discovery tooling

Requires Python 3.11+ and uv. Pillow is the only Python dependency. No Node application is initialized.

```sh
uv sync --locked
uv run python -m unittest discover -s tests
uv run python tooling/discover.py summarize
```

The summary command is offline. Other commands explicitly contact named sources; consult [the experiment instructions](experiments/README.md) before running them. Samples and raw captures remain in ignored `experiments/private/`; public metadata and aggregate measurements are review evidence, not an approved production dataset.

Local credentials live in `~/.config/secrets/shared.env`, with environment variables taking precedence. eBird uses `EBIRD_API_KEY`. Do not copy that file into this repository. Worker secrets and GitHub Actions secrets are the deployment equivalents if a later phase is authorized.

The initial checkout had no commits or Git remote. Work is local; no GitHub push is claimed. No other project's code or infrastructure was modified.
