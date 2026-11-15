# BirdAhead agent instructions

BirdAhead teaches the birds a learner is likely to encounter, by sight and sound. Read PROJECT.md and docs/feasibility.md before changing scope.

## Current boundary

Phase 0.5 is authorized: official annual histogram import and ranking experiments; authenticated Xeno-canto acquisition; a local-only curation workbench; local BioCLIP/BioCLIP 2 and BirdNET benchmarks; and bounded expansion of the existing 25-species pilot toward five photo and three audio candidates per species. One supported-replacement pass may address observed gaps while keeping the experiment catalog below 240 total candidate files. Commit/push appropriate artifacts to the verified hmarquardt/birdahead remote. Do not build the production application, deploy infrastructure, acquire thousands of assets or make purchases. Domain registration is complete; do not repeat it. Stop at the Phase 0.5 review boundary.

## Working conventions

- Use Python and uv for acquisition; proposed runtime is TypeScript/React/Vite/Hono on Workers, D1 and R2.
- Keep third-party acquisition out of runtime learning sessions.
- Central local credential convention: `~/.config/secrets/shared.env`. Load programmatically only as needed, with existing environment variables taking precedence. eBird uses `EBIRD_API_KEY`. Never print values, dump environment/configuration, copy credentials into project files, logs or commits, or use client-side secrets. Do not use platform-specific credential managers. Use Cloudflare Worker secrets in Workers and GitHub Actions secrets in CI. Raw source data and authenticated responses stay in ignored private storage.
- Do not modify adjacent projects or shared Cloudflare resources. Patterns may be inspected read-only.
- Use explicit evidence labels: verified documentation, observed experiment, proposal, assumption, blocked/unavailable. Record date, source URL, request scope, counts and failures. An HTTP 200 challenge page is not a successful acquisition.
- Run bounded experiments explicitly. The discovery CLI defaults to offline analysis; cached captures live under ignored experiments/private/. Do not commit source datasets whose terms restrict redistribution, exact bird locations or private observation imports.
- No generated bird imagery, synthetic bird calls or unverified search images in the learning corpus. Specialized models may support automated acceptance when source evidence, rights/provenance, technical quality, calibrated species-aware thresholds, confusion-pair scrutiny and deduplication/diversity gates all pass. Model scores are not probabilities or sole identification authority. Record model versions, results and acceptance rationale. Prefer replacing uncertain assets.
- Every photo/recording has its own rights. An observation license does not license its media. Missing metadata stays null. Separate candidate, rejected, quarantined, deferred, automatically accepted, human-approved and expert-verified states. Rights and biological acceptance are independent. Human review is reserved for sampled audits, gaps and selected high-risk cases, with a two-hour TOTAL owner-review cap for the initial regional collection; reduce coverage rather than weaken gates. Never download restricted Cornell media.
- Preserve source taxonomy/version, crosswalk decisions and split/lump history. Never join only by common name.
- Keep historical reporting frequency, modeled occurrence/abundance and recent sightings separate; occurrence counts are not reporting frequency.
- For substantial changes run appropriate offline checks with `uv run python -m unittest discover -s tests`. Live checks need explicit bounded commands; do not repeat acquisition just to test formatting.
- No task-specific shared skill was applicable to this discovery run. Use an available skill when the actual task calls for it; avoid deployment/site creation skills during local-only validation.

## Review handoff

README.md indexes deliverables. docs/feasibility.md contains measured results and gates. docs/decisions records proposals and accepted boundaries. Production implementation/deployment authorization must be explicit. Add future in-app identification flagging to the product plan; do not build that production feature during this phase.
