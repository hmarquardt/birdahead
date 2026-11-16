# BirdAhead agent instructions

BirdAhead teaches the birds a learner is likely to encounter, by sight and sound. Read PROJECT.md and docs/feasibility.md before changing scope.

## Current boundary

Phase Two authorizes the local 100-species teaching universe derived from the seven owner-supplied 2016–2025 histogram exports, bounded resumable media expansion, verified audio-segment derivatives, and learner improvements. The established rights/biology gates and the **two-hour TOTAL owner-review cap** remain unchanged; 100 species and five-photo/three-recording targets are coverage objectives, never permission to accept questionable examples. No new paid inference service, production deployment, purchase, large EBD/SED acquisition or modeled-raster download is authorized. Reuse the seven county datasets; do not request recurring county downloads. The earlier Phase One boundary remains superseded only for this local work. Commit/push appropriate artifacts to the verified hmarquardt/birdahead remote. Stop at the Phase Two review boundary. Domain registration is complete; do not repeat it.

## Working conventions

- Use Python and uv for acquisition; proposed runtime is TypeScript/React/Vite/Hono on Workers, D1 and R2.
- Keep third-party acquisition out of runtime learning sessions.
- Central local credential convention: `~/.config/secrets/shared.env`. Load programmatically only as needed, with existing environment variables taking precedence. eBird uses `EBIRD_API_KEY`; modeled products use the separate `EBIRD_ST_API_KEY`; Xeno-canto uses `XENO_CANTO_API_KEY`. Never print values, dump environment/configuration, copy credentials into project files, logs or commits, or use client-side secrets. Do not use platform-specific credential managers. Use Cloudflare Worker secrets in Workers and GitHub Actions secrets in CI. Raw source data and authenticated responses stay in ignored private storage.
- Do not modify adjacent projects or shared Cloudflare resources. Patterns may be inspected read-only.
- Use explicit evidence labels: verified documentation, observed experiment, proposal, assumption, blocked/unavailable. Record date, source URL, request scope, counts and failures. An HTTP 200 challenge page is not a successful acquisition.
- Run bounded experiments explicitly. The discovery CLI defaults to offline analysis; cached captures live under ignored experiments/private/. Do not commit source datasets whose terms restrict redistribution, exact bird locations or private observation imports.
- Phase Two acquisition checkpoints live in ignored `experiments/private/phase05/expansion/state.json`; request, byte and retry budgets are explicit and resumable. Candidate targets allow for curation rejection and are not accepted-coverage claims. Never raise a budget merely to fill a quota.
- Accepted audio clips are source-interval derivatives, never synthetic calls. Preserve parent digest, interval, tool/model version, threshold, rights and attribution; the parent remains in the catalog.
- Learner flags are reconciled to the workbench with `uv run python -m tooling.flag_sync --apply`. A report appends a deferral for triage; it is not automatic biological proof and consumes no owner-review time.
- No generated bird imagery, synthetic bird calls or unverified search images in the learning corpus. Specialized models may support automated acceptance when source evidence, rights/provenance, technical quality, calibrated species-aware thresholds, confusion-pair scrutiny and deduplication/diversity gates all pass. Model scores are not probabilities or sole identification authority. Record model versions, results and acceptance rationale. Prefer replacing uncertain assets.
- Every photo/recording has its own rights. An observation license does not license its media. Missing metadata stays null. Separate candidate, rejected, quarantined, deferred, automatically accepted, human-approved and expert-verified states. Rights and biological acceptance are independent. Human review is reserved for sampled audits, gaps and selected high-risk cases, with a two-hour TOTAL owner-review cap for the initial regional collection; reduce coverage rather than weaken gates. Never download restricted Cornell media.
- Preserve source taxonomy/version, crosswalk decisions and split/lump history. Never silently infer concept equivalence from common names. Name-only histogram formats require a recorded provisional crosswalk constrained to the existing versioned pilot, scientific-name agreement against the target authority and an explicitly unknown source version; ambiguous/split/lump cases stay unresolved.
- Keep historical reporting frequency, modeled occurrence/abundance and recent sightings separate; occurrence counts are not reporting frequency.
- For substantial changes run appropriate offline checks with `uv run python -m unittest discover -s tests`; learner changes also require `npm test --prefix app` and `npm run build --prefix app`. Live checks need explicit bounded commands; do not repeat acquisition just to test formatting.
- No task-specific shared skill was applicable to this discovery run. Use an available skill when the actual task calls for it; follow local-only branches of applicable skills; never register or publish a hosted Site.

## Review handoff

README.md indexes deliverables. docs/feasibility.md contains measured results and gates. docs/decisions records proposals and accepted boundaries. Production implementation/deployment authorization must be explicit. The local MVP may implement identification flags, learning profiles and practice; cloud deployment remains separately authorized.
