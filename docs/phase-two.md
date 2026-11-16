# Phase Two — automated content expansion and learner improvements

November 15, 2026. **Local Phase Two delivered; production deployment, paid infrastructure, new county downloads and large EBD/SED/modeled-product acquisition remain outside the boundary.** The 100-species list is a teaching/coverage objective. Automated acceptance remains preliminary source/model corroboration, not biological certification.

## Teaching universe

`tooling.teaching_universe` reads the seven private 2016–2025 county exports through the validated native parser, reconciles each source name uniquely against the cached 2026 eBird/Clements authority, and ranks candidates by explicit normalized components: year-round frequency/coverage (.35), current seasonal rate (.25), positive 14–28-day rise (.20), recreational/confusion-pair value (.12) and media availability at selection time (.08). The 25-species pilot is force-retained.

| Item | Result |
| --- | ---: |
| Reconciled source species | 333 |
| Selected teaching species | 100 |
| Pilot species retained | 25 |
| Unresolved/non-species source names (all counties) | 81 |
| Imported species × native bins × counties | 100 × 48 × 7 = 33,600 |
| Original export bytes / checklist samples | 737,866 / 79,868 |

The source taxonomy release is still not embedded; the crosswalk is exact unique common-name plus target scientific-name agreement, with split/lump ambiguity left unresolved. Full unresolved names stay in ignored private storage. The public [universe configuration](../config/geography/teaching-universe.json) records ranks, selection components, sample support, seasonal anchors and limitations; [histogram evidence](../experiments/histogram-validation.json) remains aggregate-only.

## Bounded acquisition and media results

`tooling.expansion` persists `experiments/private/phase05/expansion/state.json` after every asset and species. The run used explicit budgets of 450 API requests, 1.2 GB new media, 900 candidate assets and two retries per URL. It stopped at a **practical checkpoint: 23 of 100 species processed**, not because a budget was exhausted. This is a deliberate partial batch; the checkpoint is resumable and the remaining species are explicit gaps. Sixteen species have five-plus accepted photographs and ten have three-plus accepted recordings.

| Acquisition measure | Value |
| --- | ---: |
| New candidates / downloads | 186 / 186 |
| API requests / retries | 62 / 18 |
| New media bytes | 187,817,080 (~179 MB) |
| Elapsed acquisition seconds | 795.5 |
| Catalog after expansion | 481 candidates, 513,525,756 bytes |
| Media-transfer failures | 6 |
| Checkpoint | cursor 23/100, incomplete, resumable |

Selection before download used source-taxon lineage, concordant non-owner identifiers (two for confusion pairs), contributor caps, resolution, distinct observations, research grade, exact photo/recording license and duration/quality filters. Candidate volume was not treated as accepted coverage. The full acquisition aggregate is [here](../experiments/phase-two-acquisition.json).

## Inference, segment derivatives and curation

BioCLIP 2 and BioCLIP 1 evaluated all **296** photographs against the regional class set plus controls. BirdNET evaluated all **185** recordings (153 source recordings plus 32 verified clips) without a source-only class list or geographic prior. The target-clarity screen processed 296 photos: 176 had one detected bird, 42 multiple detections and 78 none; **192 passed**, including conservative single-source-consistent-crop and low-risk whole-image fallback handling. This is a screening result, not biological proof.

Verified source-interval extraction produced **32 clips** (368.2 seconds, 15.1 MB) from recordings where the source species dominated at least two adjacent windows. Each clip records the parent id/digest, interval, threshold, recipe version, output digest, attribution and modification notice; parents remain in the catalog. BirdNET was re-run on every clip. Twenty-four clips passed curation; eight did not.

| Curation measure | Value |
| --- | ---: |
| Candidates | 481 (296 photo, 185 audio) |
| Automatically accepted | **193** (141 photo, 52 audio) |
| Acceptance rate | photo 47.64%; audio 28.11% |
| Accepted derivative clips | 24 |
| Human-approved / expert-verified | 0 / 0 |
| Owner review seconds | 0 / 7,200 cap |
| Sampled audit queue | 40 |
| Mislabeled controls accepted | 0 / 11,544 photo; 0 / 7,030 audio |
| Confusion-pair mislabeled controls accepted | 0 / 64 photo; 0 / 25 audio |

Leading rejection reasons: no two adjacent dominant audio windows (116), no source-consistent localized photo target (104), target not dominant enough in the full recording (84), BioCLIP 2 threshold/margin failure (83), confusion-pair corroboration/margin (39), BioCLIP top-five corroboration (34), insufficient independent source identifiers (33), localized margin below risk threshold (11), high-risk bird-seen evidence (6), audio calibration support (5), duplicates (3), and isolated technical/vocalization issues. Full counts are in [the media report](../experiments/phase-two-media.json).

## Coverage before and after

| Measure | Phase One | Phase Two |
| --- | ---: | ---: |
| Automatically accepted assets | 55 | **193** |
| Accepted photographs | 44 | **141** |
| Accepted recordings | 11 | **52** |
| Species sight-ready (≥2) | 14 | **30** |
| Species sound-ready (≥2) | 3 | **16** |
| Species with 5+ photos | 0 | **16** |
| Species with 3+ recordings | 2 | **10** |
| Species with both targets | 0 | **4** |

The 100-species universe currently has 33 species with at least one accepted photograph, 20 with at least one recording, 4 meeting both targets, 28 additional practice-partial species and **68 explicit gaps**. No weak examples were promoted to reduce the gap count. Seasonal top-25 deck coverage at the reference county:

| Deck | Sight-ready | Sound-ready | Both targets |
| --- | ---: | ---: | ---: |
| Winter | 14 | 10 | 2 |
| Spring migration | 12 | 7 | 1 |
| Summer | 14 | 10 | 2 |
| Fall migration | 15 | 11 | 2 |
| Requested date (2026-11-15) | 16 | 11 | 2 |
| Arriving Soon now | 7 | 3 | 2 |

## Learner improvements

Release v2 carries the 100-species universe, data vintage (2016–2025; unknown source taxonomy), native-bin definition, per-species sample support, priority ranks, coverage tiers/gaps and a compatibility key. The learner now shows a coverage strip, vintage/support tags, explicit gap labels, a searchable accepted-media field guide, seasonal deck coverage, richer answer feedback with collection coverage/comparison context, and session summaries listing missed and uncertain species. Mobile styles add larger touch targets, scrollable sticky tabs, safe-area padding, full-width audio and single-column galleries.

Sessions continue across additive releases with the same taxonomy/source-scope compatibility key; removed media are skipped. Attempts and progress remain independent. Flags still hide disputed media for both learners and exclude affected attempts; `tooling.flag_sync --apply` now reconciles each new report into the workbench as an append-only deferral for triage, idempotently and without consuming owner-review seconds. This run had no owner flags to reconcile; the path is covered by regression tests.

## Verification and costs

- **48 Python tests** pass, including teaching-universe selection/unresolved handling, interrupted acquisition/resume, release validation/compatibility and flag reconciliation.
- **9 Hono tests** pass, including independent profiles/confusions, idempotency, expiry, flags/progress exclusion, media ranges/integrity, field-guide/coverage endpoints, feedback context and compatible-release session continuation.
- TypeScript/build checks pass. Real Chrome desktop/mobile smoke passes with the actual accepted release, including image decode, muted audio playback/ranges, flags, field-guide search/gallery, coverage view, recall and no mobile horizontal overflow. It uses a disposable learner database; no owner practice/review was fabricated. Evidence: [browser report](../experiments/local-mvp-browser.json).
- Incremental inference took about 31 seconds for 82 new source recordings and 4.8 seconds for 32 clips on the measured Apple M2; model weights were already cached. No provider inference charge or cloud resource was created. The domain registration/quoted renewal remains $11.17; hosting is still $0 locally.

## Limitations and next steps

- Acquisition covered 23/100 species before the practical checkpoint; 68 species have no practice-ready media. Resume the same checkpoint with a new explicit batch rather than raising budgets to fill a quota.
- Automated acceptance is preliminary source-proxy/model corroboration. It is not a calibrated biological error rate, and source/model errors can correlate. The 40-asset sampled audit remains unperformed; the two-hour total owner-review cap is untouched.
- Source taxonomy release is unknown; unresolved/split-lump names stay excluded. Reporting frequency is historical complete-checklist frequency, not encounter probability or abundance.
- Audio clips are real intervals with model evidence, not independent identification. Biological subtype/plumage/vocalization coverage remains uneven.
- Next: sampled audits, replacement of high-risk subject-screen/audio failures, contributor and biological-variation review, resumed acquisition for high-priority gaps, then separately authorized deployment/authentication work.

This is the Phase Two review boundary. No production deployment, paid infrastructure, new county download, large EBD/SED or modeled-raster acquisition, or commercial-use claim was made.
