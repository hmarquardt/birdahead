# Automated media curation policy

November 15, 2026. The Phase 0.5 amendment supersedes the original per-asset human-review requirement. BirdAhead aims for practical reliability and enjoyable recreational learning; it is not a scientifically certified reference collection.

## Acceptance tiers

| State/evidence | Meaning |
| --- | --- |
| Candidate | Lawfully discovered media with an original record and asset identifier |
| Source-verified | The source identifies the species with recorded supporting evidence; this is not independent ground truth |
| Machine-screened | Technical checks and versioned specialized-model inference were run |
| Automatically accepted | Both rights and biological gates passed the configured risk tier; no individual human approval required |
| Human-approved | A person recorded evidence and an approval, separately from automated acceptance |
| Expert-verified | A named reviewer asserted an expert role and recorded identification evidence; not institutional certification |
| Deferred / quarantined / rejected | Excluded from accepted export until resolved; retain reasons and avoid repeated acquisition |

An asset can carry several evidence labels. Never relabel an automated decision as a human or expert decision. Unknown sex, age, plumage, exact location or vocalization stays unknown. Source-asserted traits and machine suggestions remain distinguishable from verified traits.

## Automated gates

1. **Credible source identification.** For iNaturalist, retain Research Grade, current community taxon, disagreements/flags and concordant identifiers other than the owner. For Xeno-canto, retain identified status, quality, recordist, bird-seen assertion, method and background species. A source filename, Research Grade or model result alone is insufficient.
2. **Rights/provenance.** Validate each asset's own license, exact version/link, creator/credit, source ID/URL, file digest and permitted use. Observation licenses do not license photos. Rights acceptance is independent of biological acceptance.
3. **Specialized model agreement.** BioCLIP 2 must agree with the source against a broad regional class set plus controls. BioCLIP supplies additional corroboration; the known hawk/woodpecker/vulture/yellowlegs pairs receive stronger gates. BirdNET evaluates all supported classes without a source-only class list or geographic prior. Preserve complete inference evidence privately.
4. **Species-aware operating thresholds.** Fit and evaluate thresholds using separate contributors/records where possible. Keep sample sizes, false-label controls and checkpoint/preprocessing hashes. Current local thresholds use source-label proxies and are explicitly preliminary; they are not calibrated probabilities or a measured biological error rate. Insufficient support limits the acceptance tier or coverage.
5. **Technical suitability and target clarity.** Decode media; measure resolution, exposure/detail, clipping/silence and audio window dominance. Subject detection/localization is a conservative image screen. Several birds without a clear source-consistent target can make an exercise ambiguous even when its source label is correct. Replace or defer such examples. Global sharpness and detector scores do not guarantee diagnostic detail.
6. **Duplicates/diversity.** Check source IDs, exact file digests, perceptual image hashes and conservative acoustic fingerprints. A near-duplicate flag is not proof of identical content. Avoid counting repeated views of the same encounter as independent examples. Prefer independent contributors and several useful vocalizations/plumages; never invent a missing subtype to fill a coverage cell.

Uncertain assets should generally be replaced with stronger candidates. Do not send every model disagreement to the owners. Do not lower gates to achieve a count target. An ambiguous example may later become an explicitly designed insufficient-information exercise; it is excluded from definitive-ID training meanwhile.

## Noncommercial and commercial lanes

| License/evidence | Initial noncommercial lane | Commercial compatibility |
| --- | --- | --- |
| CC0 | Eligible with provenance | Eligible, subject to other applicable rights |
| CC BY, exact version | Eligible with credit, license link and change notice | Media eligible under its conditions |
| CC BY-SA, exact version | Eligible; preserve applicable ShareAlike terms | Media eligible; adaptations retain compatible terms |
| CC BY-NC / BY-NC-SA | Eligible for this recreational scope | Exclude unless separately licensed |
| ND, rights reserved, unclear rights | Exclude from the default derivative/offline workflow | No assumed permission |
| Macaulay embed-only access | Official permitted embed only; no implied file acquisition | Obtain a scoped agreement |
| Written license / public domain | Validate asset-specific terms/evidence | Evaluate actual grant/jurisdiction |

The official iNaturalist [license implementation](https://github.com/inaturalist/inaturalist/blob/main/app/models/shared/license_module.rb), captured blob `0fba8c7870f89a84f3d0f021a4706c7742ef9761`, maps its CC short codes to 4.0 and CC0 to 1.0. This resolves the Phase Zero version gap without inventing per-photo terms. Retain the asset's returned license code and the mapping evidence. Source-supplied attribution is retained; do not discard a photographer's stated credit in favor of an uploader guess.

[CC BY](https://creativecommons.org/licenses/by/4.0/) and [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/) require their own notices and attribution behavior. A commercially compatible photo does not make the entire collection or workflow commercial-ready. BioCLIP checkpoints are MIT; the tested BirdNET weights are CC BY-NC-SA 4.0, independently of its MIT code. Commercial model use requires separate permission or a suitable alternative. Cornell occurrence products retain their separate data restrictions.

## Provenance and reproducibility

Each asset retains canonical/source taxonomy and versions; source/asset IDs and original URLs; creator and credit; exact license and mapping/grant evidence; storage/modification/delivery/offline scope; available dates/locality with sensitive locations excluded; source-asserted biological tags; file digest and technical metrics; model/checkpoint/runtime/preprocessing versions; inference outputs; threshold/calibration digest; acceptance reasons; duplicates and contributor identity; and any human/expert review events.

Keep original downloaded bytes immutable. A permitted derivative records parent digest, crop/clip interval, transformation/tool version, output digest, attribution and change notice. Never generate bird anatomy or synthetic bird vocalizations. Image-model preprocessing is inference-only and does not create a replacement “photograph.” Spectrograms derive from real recordings. No model fine-tuning or commercial AI training is authorized.

Approved-manifest exports are deterministic, hash-identified and confined to accepted records. Restricted media, raw Cornell exports, private observations, model weights, local review databases and full per-asset inference artifacts remain outside Git. Do not redistribute source data in violation of its terms.

## Two-hour owner-review constraint

The hard budget is **7,200 total owner-review seconds for the initial regional collection**, not two hours per species, source or batch. The local workbench records timed sessions and refuses further approvals after the cap. Its wall-clock timer is conservative; finish/defer a session before leaving the workbench.

A regional planning allocation is 60 minutes of stratified random audits, 30 minutes for selected high-risk cases, 15 minutes for coverage gaps and 15 minutes reserve. At assumed 20-second photo and 45-second audio audits, the random-audit allocation could cover 90 photos plus 40 recordings. Those are planning assumptions, not measured throughput. Pilot audit selection samples 20% of automatically accepted media, capped by those quantities, using a stable hash order separately by modality. No individual review is required for the rest.

Record observed audit errors and durations by species/source/risk tier. Zero errors in 130 independent random audits would still leave an approximately 2.3% one-sided 95% binomial upper bound; correlated or selective audits provide less assurance. No such clean audit outcome is claimed. The deliberate-label controls are repeated tests on a small source-labeled corpus, not thousands of independent biological judgments. If audits reveal systematic errors, disable affected tiers/species, replace candidates and reduce initial scope within the same time budget.

## Verified audio-segment derivatives

Phase Two may extract a clip from a real recording when the source species dominates at least two adjacent BirdNET windows but not enough of the full recording. The clip is a byte-faithful source interval, not a synthetic call or a replacement identification. Extraction requires a license that permits derivatives, preserves the parent asset and digest, records the interval, model/checkpoint, threshold, margin and recipe version, carries the original attribution/license and a modification notice, and re-runs BirdNET on the clip before curation. The parent remains in the catalog, usually deferred. A clip is accepted only through the same rights/biology/technical/deduplication gates. No model scores are treated as probabilities, and no clips are created for ND/unknown-license material.

Candidate selection is improved from measured failure reasons: source-taxon lineage support, concordant non-owner identifiers, high-risk two-identifier requirement, contributor caps, resolution preflight, distinct observations, quality/duration filters and a target-clarity screen that can select one source-consistent crop among several detector boxes. A whole-image fallback is conservative and unavailable for confusion pairs. Candidate volume never substitutes for these gates.

## Phase 2.1 throughput and replacement rules

Successive bounded batches may reuse the checkpoint, catalog, source caches and model predictions. API metadata requests remain sequential under provider pacing; only media transfers use bounded concurrency (four workers in the measured run) with retry/backoff and a per-run asset/request/byte ceiling. A cumulative **5 GB new-media budget** applies to Phase 2.1; disk free space must exceed the budget plus a reserve before a batch starts. Existing rejected URLs and catalog assets are not downloaded again, and cached inference is reused while model/preprocessing versions remain unchanged.

Targeted replacement passes are allowed for high-priority species, the versioned pilot and confusion pairs with accepted-coverage gaps. Replacement queries begin on later result pages so they seek new observations/recordings rather than re-evaluating the same rejected files. Contributor caps, source evidence, rights, resolution, duration and target-clarity screens remain in force; replacement volume never becomes acceptance authority. Contributor, month/season, source-asserted age/sex and vocalization-type diversity are preferred where the source provides evidence; unknown traits remain unknown.

A sampled audit queue is stratified across modality and risk (including confusion pairs), not a per-asset approval requirement. The workbench timer and the 7,200-second total cap still govern any actual owner review.

## Flags and corrections

The learning app must offer “Flag possible misidentification” from an exercise/reveal. Save asset/release/variant IDs, reason, optional suggested species and audio interval. Triage flags, suppress disputed examples from new sessions where warranted, revalidate or replace them, publish an erratum and repair affected progress. User reports are evidence, not automatic proof of the proposed replacement identification.

The local learner captures flags with asset/release/session context, suppresses the example for both learners and excludes affected attempts. `tooling.flag_sync --apply` reconciles each new report into the workbench as one append-only deferral event for triage, preserving the report/release/session context. It is idempotent by flag id, never consumes timed owner-review seconds and never turns a report into biological proof. The workbench shows learner-report intake and supports quarantine/reject/defer and persistent evidence. Audio-interval capture remains future work. Audit events are append-only with a hash chain. Approvals bind to media/taxonomy/rights evidence, so a changed asset or license cannot silently inherit an older approval.
