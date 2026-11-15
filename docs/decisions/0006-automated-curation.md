# ADR 0006 — Automated recreational-media acceptance

Date: 2026-11-15. Status: accepted direction from the Phase 0.5 amendment. Supersedes ADR 0004's mandatory per-asset human approval.

BirdAhead is a recreational, noncommercial learning product. Mandatory human review of every asset is rejected. Allow automated acceptance when credible source identification, exact rights/provenance, specialized-model agreement, species-aware operating thresholds, confusion-pair scrutiny, technical screening and deduplication/diversity conditions pass. Rights and biology are separate gates.

Use BioCLIP 2 as the primary image screen, with BioCLIP corroboration for high-risk pairs. Evaluate BirdNET for real recordings. Scores and source agreement are not calibrated biological probabilities. Retain checkpoint hashes, model/runtime versions, preprocessing, source labels, inference outputs, threshold version and acceptance reasons. Consider shared training data and correlated errors explicitly.

Prefer replacing uncertain examples. Humans audit statistical samples and selected gaps/high-risk cases, with no more than two TOTAL owner-review hours for the initial regional collection. Reduce scope instead of approving uncertain assets or exceeding that budget. A future production app must let learners flag potentially incorrect identification.

Current thresholds are preliminary operating points fitted to source-label proxies with held-out contributors/records and deliberate label corruption tests. They establish executable gates, not independent biological accuracy. A small sampled audit can revise or disable a species/tier without imposing per-asset review.

Noncommercial licenses are eligible for the initial lane; separately record commercially compatible media. A model's license and the media's license are independent. Production development/deployment remains on hold.
