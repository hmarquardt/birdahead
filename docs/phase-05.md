# Phase 0.5 validation findings — historical

**Historical Phase 0.5 record.** Current local media/learner results are in [Phase Two](phase-two.md).

**Superseded scope/status:** The [Phase One report](phase-one.md) records completed seven-county import, real seasonal demonstrations, authenticated S&T listing and the implemented local learner. The media/model measurements below remain historical evidence. The former local-application hold and annual-export blocker no longer apply; deployment and large downloads remain unauthorized.

November 15, 2026. **Local automated curation is feasible; hold production and broad regional ingestion. Annual occurrence validation remains blocked on official exports, and biological precision has not yet been independently audited.** The amendment rejects per-asset mandatory human review; the owner-review ceiling is two hours total for the initial regional collection.

## 1. Annual occurrence acquisition and parser

No actual annual histogram exports are present for the seven counties. The ordinary local Gibson chart request failed; earlier access returned a challenge. The API key is not a website login. [Actionable signed-in download instructions](manual-downloads.md) specify the same full-year scope, 2016–2025, for Gibson, Pike, Greene, Posey, Knox, Vanderburgh and Warrick. No EBD was acquired as a substitute.

`tooling/seasonal.py` provides a deterministic explicit long-format parser and ranking experiment. It rejects unit/taxonomy/scope mismatches, duplicate/gapped bins and invalid sample counts; preserves missingness and unknown denominators; and treats zero checklist support as unknown. The native eBird adapter awaits an actual file. No native bin definitions, sample sizes or missing-value semantics are claimed verified yet.

## 2. Seasonal curriculum demonstrations

**Not completed with actual annual data.** Offline fixtures test annual wraparound, missingness and an approaching window with zero current reporting frequency. They are synthetic software tests, not evidence of local winter/spring/summer/fall priorities. The ranking experiment separates present reporting frequency from the maximum increase 14–28 days ahead and labels its output as curriculum priority, never an absolute encounter probability. Seven consistent imports are required before a real demonstration can be reported.

## 3. Authenticated audio and bounded acquisition

Xeno-canto authentication succeeded using the shared key, without printing/caching/logging it. A cardinal test confirmed page 1/2 disjoint IDs, 50-record pages, geographic bounds, quality metadata, vocalization strings and per-recording licenses. An identification-dispute query returned questioned/unconfirmed statuses. Official API/search pages were accessible through an ordinary local request. [Measured evidence](../experiments/xc-validation.json), [official API](https://xeno-canto.org/explore/api), [search syntax](https://xeno-canto.org/help/search).

Scientific-name searches and explicit old-genus aliases are used; a broad-epithet trial initially hid some desired species behind unrelated page-one results and was corrected. The experiment does not confuse an unhelpful query with biological absence. Media downloads use bounded sizes, source hosts and license checks; ND/unknown licenses are excluded from the derivative/offline lane.

The first pass retrieved 125 photos and 71 recordings for all 25 species; Turkey Vulture and Bufflehead had only one selected recording each under the chosen quality/region/duration/contributor filters. One supported-replacement pass added 38 photos for observed gaps. Final total: **163 photos + 71 recordings = 234 candidate files**, below the declared 240-file ceiling. Media bytes total 274.35 MB; no thousands-scale ingestion occurred.

## 4. Local inference benchmarks

Observed machine: Apple M2, 16 GB unified memory, macOS 27.0, arm64. Inference ran natively in an isolated Python 3.12 environment with locked dependencies. Models ran sequentially; no NVIDIA hardware, hosted inference or fine-tuning was used. Main data tools remain lightweight Python/uv.

| Model / recipe | Corpus | Measured throughput | Process peak RSS | MPS driver allocation | Source top-1 agreement |
| --- | --- | --- | --- | --- | --- |
| BioCLIP, fp32 MPS | 163 photos, 373 labels | 28.86 images/s | 1.25 GB | 1.64 GB | 112/163 |
| BioCLIP 2, fp32 MPS | 163 photos, 373 labels | 9.17 images/s | 2.11 GB | 2.25 GB | 144/163 |
| BirdNET-Analyzer 2.4.0 / V2.4, four-thread TFLite CPU | 71 recordings, 49.83 min, 6522 labels | 127.27 audio seconds/wall second | 1.24 GB | Not configured | Window/source agreement; no file accuracy claim |

RSS and MPS driver figures are separately observed counters in unified memory and must not be blindly added. Throughput is a single bounded warmed pass, including the recorded processing recipe; it excludes network acquisition and does not predict sustained application latency. BirdNET startup/import took 47.79 seconds in the first run and 3.04 seconds in the cached rerun; warmed processing excludes that setup. CPU comparison used eight photos per image model; exact versions, digests, class-list fingerprints, preprocessing and times are in the [benchmark artifacts](../experiments/benchmark-bioclip-2.json).

The initial latest-observation pass agreed with 93/125 source labels for BioCLIP and 116/125 for BioCLIP 2. Replacement selection changed the corpus and increased difficult/older examples; final rates are not a directly comparable randomized accuracy test. The recipe uses common/scientific-name prompt embeddings against a regional class list plus non-bird text-label controls; it does not reproduce the authors' full global-taxonomy evaluation. Source agreement is not ground-truth accuracy.

A lightweight torchvision SSDLite subject detector, followed by BioCLIP 2 inference on its proposed target region, screens target clarity. The screen can miss small/obscured birds, so no detection means defer/replace, not absence. Multiple birds without a clear eligible target are excluded from definitive-ID acceptance. The workbench can mark the eligible target without editing the original media pixels. [Detector documentation](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.detection.ssdlite320_mobilenet_v3_large.html).

BioCLIP and BioCLIP 2 cards specify MIT weights; pybioclip is MIT. BirdNET-Analyzer code is MIT while the tested model weights are CC BY-NC-SA 4.0. torchvision code is BSD-3-Clause; a separate commercial grant for its auxiliary detector weights was not established here. Do not infer model rights from media rights or code licensing. [BioCLIP card](https://huggingface.co/imageomics/bioclip), [BioCLIP 2 card](https://huggingface.co/imageomics/bioclip-2), [BirdNET licensing](https://github.com/birdnet-team/BirdNET-Analyzer#license), [torchvision license](https://github.com/pytorch/vision/blob/main/LICENSE).

## 5. Acceptance, rights and coverage

Current executable gates automatically accept **55 validation examples** (44 photos, 11 recordings). Human-approved: 0; expert-verified: 0. The 12-example audit queue is a statistical sample, not a per-asset approval requirement. The stricter target-clarity screen intentionally lowers yield. The supported replacement pass increased acceptance from 51 to 55 examples and broadened some basic-species coverage; it did not solve the difficult pairs.

All 234 candidates have automated exact-license/credit/source/digest completeness under the recreational policy. That is metadata/rights validation, not legal certification or biological truth. 32 media candidates have CC0/BY/BY-SA-compatible flags; most of this pilot is NC. The official iNaturalist license mapping resolved its short-code version gap. Source-supplied credit is retained. A commercial collection could select the open lane and directly licensed/owner-contributed replacements, but eBird data and BirdNET model-use permissions remain separate gates.

| Species | Photo candidates | Audio candidates | Auto photos | Auto audio | Photo/audio contributors |
| --- | ---: | ---: | ---: | ---: | --- |
| Cooper's Hawk | 8 | 3 | 0 | 1 | 8 / 3 |
| Sharp-shinned Hawk | 8 | 3 | 0 | 0 | 8 / 3 |
| Downy Woodpecker | 8 | 3 | 0 | 0 | 8 / 3 |
| Hairy Woodpecker | 8 | 3 | 0 | 0 | 8 / 3 |
| Turkey Vulture | 8 | 1 | 1 | 0 | 8 / 1 |
| Black Vulture | 8 | 3 | 1 | 0 | 8 / 3 |
| Greater Yellowlegs | 8 | 3 | 0 | 0 | 7 / 3 |
| Lesser Yellowlegs | 8 | 3 | 0 | 0 | 8 / 3 |
| Northern Cardinal | 7 | 3 | 2 | 0 | 7 / 3 |
| American Robin | 7 | 3 | 3 | 0 | 7 / 3 |
| American Goldfinch | 5 | 3 | 3 | 1 | 4 / 3 |
| Mallard | 5 | 3 | 3 | 0 | 5 / 3 |
| Wood Duck | 7 | 3 | 3 | 1 | 6 / 3 |
| Bufflehead | 7 | 1 | 2 | 0 | 7 / 1 |
| Snow Goose | 7 | 3 | 0 | 3 | 7 / 3 |
| Dark-eyed Junco | 5 | 3 | 3 | 0 | 5 / 3 |
| White-throated Sparrow | 5 | 3 | 3 | 3 | 5 / 3 |
| Indigo Bunting | 5 | 3 | 3 | 0 | 4 / 3 |
| Dickcissel | 5 | 3 | 4 | 0 | 5 / 3 |
| Prothonotary Warbler | 5 | 3 | 2 | 0 | 4 / 3 |
| Yellow-rumped Warbler | 5 | 3 | 2 | 0 | 5 / 3 |
| Blackpoll Warbler | 5 | 3 | 4 | 0 | 4 / 3 |
| Sandhill Crane | 7 | 3 | 1 | 0 | 7 / 3 |
| Red-winged Blackbird | 5 | 3 | 3 | 0 | 5 / 3 |
| Blue-winged Teal | 7 | 3 | 1 | 2 | 6 / 3 |

The source-asserted sex/age and vocalization distributions are preserved in [the coverage artifact](../experiments/phase05-results.json). Plumage/breeding/nonbreeding/flight/underside coverage has not been verified. Vocalization strings may contain several types or uncertainty; they do not certify every call subtype. Unknown biological tags remain unknown. Do not claim the target counts cover all biological variations.

## 6. Calibration, deliberate errors and correlated risks

The photo policy fits per-species source-proxy cosine cutoffs using contributor-separated fitting/held-out records within each species; the audio policy retains preliminary per-species cutoffs and a held-out recording where available. Small counts and shared contributors across species limit these splits. There are **zero independently adjudicated calibration labels**. Hard pairs require stronger source support, additional model corroboration and target/quality checks; failed gates remain deferred.

Deliberate source-label corruption tests: 3912 photo controls, including 64 required-pair swaps; 1320 photo controls use held-out images. Audio: 1704 wrong-label controls, including 22 pair swaps. The current gates accepted zero of these controls. They reuse 234 actual candidates and are not thousands of independent, blind biological judgments. They do not establish a general false-acceptance rate or prove either source label is correct.

Both image models disagree with the source on 15 final photos; 4 share the same non-source top label. Correlation is visible, so multiplying model probabilities or treating two agreeing CLIP variants as independent experts is invalid. A disagreement may indicate model error, a source error, a different visible bird or taxonomy/preprocessing mismatch.

BioCLIP training sources overlap with iNaturalist/GBIF-style material; BirdNET may have seen older Xeno-canto/Macaulay recordings. Initial photos were newly uploaded in 2026, reducing obvious direct overlap with earlier checkpoints, but reused images and source-label influence remain possible. Popular supported replacements include older uploads and strengthen source evidence while increasing overlap concerns. Upload-year distributions are recorded; exact training-membership exclusion was not established and no large training archive was downloaded. [BioCLIP 2 training card](https://huggingface.co/imageomics/bioclip-2), [TreeOfLife dataset](https://huggingface.co/datasets/imageomics/TreeOfLife-200M), [BirdNET model reference](https://zenodo.org/records/15050749).

## 7. Owner review budget and scaling costs

Actual owner review recorded: 0 seconds. No human-throughput or clean-audit result is manufactured. The workbench separately times reviews, enforces the 7,200-second total approval budget, persists hash-chained append-only events, binds approvals to evidence, and exports deterministic accepted manifests. Browser fixture actions are not owner review. [Workbench instructions](workbench.md).

Plan at most 60 minutes for stratified random audits, 30 for selected high-risk cases, 15 for unresolved coverage and 15 reserve. Assumed 20-second photo/45-second audio checks would support 90+40 random audits inside the first hour; actual rates must be measured. No per-asset human review is required. Reduce scope or improve automated selection if errors or time exceed the budget. Zero errors in 130 independent random audits would still give roughly a 2.3% one-sided 95% binomial upper bound; that hypothetical is not an achieved result.

Local inference creates no provider usage charge. The measured environment uses about 2.6 GB for inference packages and 2.7+ GB for private models/captures/media at this scale; future storage depends on retained variants. Steady-state inference can screen thousands of candidates in minutes to tens of minutes on this Mac under the measured recipe, while acquisition, selection and audit dominate elapsed work. Hosting remains approximately $0–$6/month under the [existing assumptions](architecture.md), plus domain renewal; nothing was deployed or provisioned. Future licensing/commercial model permission costs are unknown.

## 8. Minimum viable product recommendation

Start a later local learning MVP with the **10 species having at least three automatically accepted photo examples**, subject to the small sampled audit and actual seasonal profiles. An optional audio subset currently has 3 species with at least two accepted recordings. This is narrower than the 25-species validation corpus; it does not discard the retained benchmark or justify weak approvals.

Initial features should be five-minute sight/limited-audio sessions, two independent profiles, explicit uncertainty, transparent sources/credits and a possible-misidentification flag. Preserve corrected asset/release context and repair affected practice history. Delay comprehensive plumage/call-type, hard-pair mastery, life-list/offline/shared-road-trip complexity until coverage supports it. No production feature was implemented during this phase.

## 9. Review boundary and go/no-go

**Go:** continue bounded automated selection/audits and import the official annual exports when supplied. The local models run economically, rights gates and reproducible exports are practical, and per-asset manual review is unnecessary.

**Hold:** production development/deployment, full regional ingestion and claims of complete 25-species/biological coverage. Actual seven-county annual data, native export semantics, seasonal demonstrations and sampled biological precision remain unresolved. The hard comparison pairs currently have insufficient accepted examples; prefer different candidates/selection recipes or a smaller teaching scope within the same owner-time budget.

The GitHub remote was verified against owner `hmarquardt` (account ID 123969), public repository ID 1459189559, with push permission and an initially empty remote. Phase Zero was committed/pushed as `d0be563`; appropriate Phase 0.5 artifacts are committed separately. Raw media, source responses, model weights, review databases and credentials are excluded. No production infrastructure or application was deployed. [Roadmap](../ROADMAP.md).

Lower-cost coding agents can implement a native histogram adapter after actual-file inspection, structured reports, bounded alternative selection, deterministic manifests, workbench polish and tests. They can execute approved automated gates; they must not invent biological ground truth, human/expert approvals, calibration evidence or deployment authorization.
