# BirdAhead agent instructions

BirdAhead teaches the birds a learner is likely to encounter, by sight and sound. Read PROJECT.md and docs/feasibility.md before changing scope.

## Current boundary

Phase Zero only: research, documentation and bounded local acquisition experiments. Do not implement the production app, deploy, create paid infrastructure, bulk-ingest media or purchase anything else. The specifically authorized birdahead.com registration is complete; do not submit it again. Stop for the owner's Phase Zero review before subsequent phases.

## Working conventions

- Use Python and uv for acquisition; proposed runtime is TypeScript/React/Vite/Hono on Workers, D1 and R2.
- Keep third-party acquisition out of runtime learning sessions.
- Central local credential convention: `~/.config/secrets/shared.env`. Load programmatically only as needed, with existing environment variables taking precedence. eBird uses `EBIRD_API_KEY`. Never print values, dump environment/configuration, copy credentials into project files, logs or commits, or use client-side secrets. Do not use platform-specific credential managers. Use Cloudflare Worker secrets in Workers and GitHub Actions secrets in CI. Raw source data and authenticated responses stay in ignored private storage.
- Do not modify adjacent projects or shared Cloudflare resources. Patterns may be inspected read-only.
- Use explicit evidence labels: verified documentation, observed experiment, proposal, assumption, blocked/unavailable. Record date, source URL, request scope, counts and failures. An HTTP 200 challenge page is not a successful acquisition.
- Run bounded experiments explicitly. The discovery CLI defaults to offline analysis; cached captures live under ignored experiments/private/. Do not commit source datasets whose terms restrict redistribution, exact bird locations or private observation imports.
- No generated bird imagery, synthetic bird calls or unverified search images. AI can triage but cannot verify identification or promote an asset.
- Every photo/recording has its own rights. An observation license does not license its media. Missing metadata stays null. Candidate, rejected, quarantined and approved are separate states; no auto-promotion. Never download restricted Cornell media.
- Preserve source taxonomy/version, crosswalk decisions and split/lump history. Never join only by common name.
- Keep historical reporting frequency, modeled occurrence/abundance and recent sightings separate; occurrence counts are not reporting frequency.
- For substantial changes run appropriate offline checks with `uv run python -m unittest discover -s tests`. Live checks need explicit bounded commands; do not repeat acquisition just to test formatting.
- No task-specific shared skill was applicable to this discovery run. Use an available skill when the actual task calls for it; avoid deployment/site creation skills during Phase Zero.

## Review handoff

README.md indexes deliverables. docs/feasibility.md contains measured results and gates. docs/decisions records proposals and accepted boundaries. Future implementation authorization must be explicit; do not infer it from the roadmap.
