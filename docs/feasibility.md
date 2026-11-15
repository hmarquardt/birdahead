# Feasibility assessment and historical Phase Zero findings

**Current assessment:** Phase Zero architecture/findings are accepted. The [Phase 0.5 report](phase-05.md) and [automated media policy](media-policy.md) supersede the per-asset human-review assumptions below. BioCLIP/BioCLIP 2/BirdNET were benchmarked locally, authenticated audio acquisition works, and automated acceptance plus sampled audits is implemented. The owner-review limit is two hours total for the initial regional dataset. Annual official county exports and independent sampled audit findings remain unavailable; production stays on hold.

The remainder records Phase Zero evidence as of its original boundary. It does not impose mandatory human approval of every asset.

November 15, 2026. **Conditional go for a bounded validation extension; hold production implementation and regional-scale ingestion.** The current evidence supports affordable candidate discovery and a plausible architecture. It does not yet establish a lawful, human-verified, seasonally complete teaching corpus at the proposed scale.

## Domain registration

**Verified through live Cloudflare API:** birdahead.com was registrable at $11.17 USD registration and $11.17 renewal. A fresh check immediately preceded the authorized registration request. Submission returned HTTP 201 with succeeded/completed; a separate workflow-status request confirmed success and an independent resource GET returned `status=active`.

Registered at 2026-11-15T19:57:54Z; expires 2027-11-15T19:57:54Z. Auto-renew false, privacy redaction, registrar lock enabled. Existing account billing/contact defaults were used. No other domain or infrastructure purchase occurred. The quote is not a promise of future renewal rates or a separately audited invoice/tax receipt. [Sanitized transaction evidence](../experiments/domain-registration.json), [official workflow](https://developers.cloudflare.com/registrar/registrar-api/).

## Verified access and geographic scope

| Experiment | Observed result | What it establishes |
| --- | --- | --- |
| eBird taxonomy/version | JSON returned, latest authority 2026; 25/25 scientific-name crosswalks agree | Current canonical IDs/names are obtainable |
| eBird county lists | 7/7 succeeded after shared credential was supplied; union 382 taxon codes/365 species-level matches | Actual all-time Indiana pilot universe, including uncommon/exceptional records |
| eBird Gibson hotspots | 29 returned; named matches for Cane Ridge, Gibson Lake and Snakey Point | Destination lookup is feasible; exact groupings still need review |
| eBird recent / historical day | 30/30 capped recent rows; 25/25 capped rows on 2026-05-10 | Recent and historical presence access; neither cap means total sightings or complete checklists |
| eBird bar chart | HTTP 200 bot challenge | No usable annual histogram acquired |
| iNaturalist regional query | 294 taxon entries, 292 at species rank | Independent regional presence evidence; not checklist frequency |
| iNaturalist photo pilot | 25/25 successful species queries | Open-license candidate discovery is practical |
| Commons | 10 successful searches; next request returned 429 and stopped | Some photo/audio retrieval works; throughput needs slower testing |
| Xeno-canto | v3 unauthenticated request returned 401; official docs challenged | Current key requirement observed; authenticated integration untested |

See [eBird evidence](../experiments/ebird-evidence.json), [regional evidence](../experiments/regional-species.json), [request measurements](../experiments/measurements.json), [source evaluation and primary references](data-sources.md). No Status and Trends key, EBD archive, personal import or BirdCast integration was acquired.

The eBird union covers Gibson, Pike, Greene, Posey, Knox, Vanderburgh and Warrick counties. The iNaturalist discovery rectangle additionally includes adjoining Illinois/Kentucky portions; the scopes differ. The 365-species Indiana result is already above the proposed 300–350 target and still is not a final cross-border universe. An all-time species list includes exceptional birds and reporting/taxonomy issues; it is not a list to teach with equal priority. Indiana DNR's independent statement of more than 300 documented Goose Pond species supports the scale's plausibility. [DNR reference](https://www.in.gov/dnr/fish-and-wildlife/properties/goose-pond-fwa/).

## The 25-species pilot

All eight mandatory comparison species were retained. The remaining 17 were selected from actual regional Research Grade records to exercise residents, winter/breeding visitors, passage migrants, waterfowl, raptors, songbirds and strong seasonal plumage differences. All 25 also occur in the authenticated eBird county union. Seasonal role labels below are design hypotheses awaiting local annual profiles, not inferred reporting calendars.

<!-- Species table is generated from the captured selection, not live queries. -->

| Species | eBird code | Regional iNaturalist observations | Pilot challenge |
| --- | --- | ---: | --- |
| Cooper's Hawk | `coohaw` | 42 | required comparison; adult/immature; perched/flight |
| Sharp-shinned Hawk | `shshaw` | 3 | required comparison; size overlap and insufficient information |
| Downy Woodpecker | `dowwoo` | 203 | required comparison; bill proportions; calls |
| Hairy Woodpecker | `haiwoo` | 18 | required comparison; bill proportions; calls; taxonomy crosswalk |
| Turkey Vulture | `turvul` | 109 | required comparison; underside/silhouette |
| Black Vulture | `blkvul` | 11 | required comparison; wing pattern and flight |
| Greater Yellowlegs | `greyel` | 28 | required comparison; bill shape, calls and perspective |
| Lesser Yellowlegs | `lesyel` | 19 | required comparison; bill shape, calls and perspective |
| Northern Cardinal | `norcar` | 380 | resident test; sex differences; song/call |
| American Robin | `amerob` | 391 | resident test; juvenile spotting; song/call |
| American Goldfinch | `amegfi` | 161 | resident test; major seasonal and sex plumage differences |
| Mallard | `mallar3` | 222 | waterfowl; sex, eclipse and immature plumage |
| Wood Duck | `wooduc` | 64 | waterfowl; breeding visitor test; sex/eclipse |
| Bufflehead | `buffle` | 13 | winter visitor test; female/immature diving duck |
| Snow Goose | `snogoo` | 186 | winter visitor test; white/blue morph; flock audio |
| Dark-eyed Junco | `daejun` | 88 | winter visitor test; geographic variation |
| White-throated Sparrow | `whtspa` | 89 | winter visitor test; morphs and song |
| Indigo Bunting | `indbun` | 83 | breeding visitor test; male/female and nonbreeding |
| Dickcissel | `dickci` | 63 | breeding grassland visitor test; song |
| Prothonotary Warbler | `prowar` | 44 | breeding wet woodland visitor test; sex/song |
| Yellow-rumped Warbler | `yerwar` | 58 | winter/passage test; seasonal plumage and calls |
| Blackpoll Warbler | `bkpwar` | 5 | transient test; sharply different fall/spring plumage |
| Sandhill Crane | `sancra` | 82 | migration wetland test; flight and calls |
| Red-winged Blackbird | `rewbla` | 158 | resident/seasonal test; female/immature and song |
| Blue-winged Teal | `buwtea` | 39 | passage/breeding waterfowl test; sex/eclipse |

Regional counts are all-time positive observations in the discovery rectangle, not frequency or relative abundance. The small Sharp-shinned Hawk count is a warning about source sparsity, not evidence the bird is absent. [Selection and crosswalk](../experiments/poc-species.json).

## Media acquisition and metadata

The 25-species photo experiment sampled 75 Research Grade wild observations from eastern North America and produced **102 unique photo candidates**. Asset licenses: 75 CC BY, 5 CC BY-SA and 22 CC0. License filters were applied before sampling, so this cannot estimate what fraction of all source photos is reusable. Three latest observations/species cannot establish balanced sex/age/plumage/flight coverage.

| Measure | Result | Interpretation |
| --- | --- | --- |
| Species with photo candidates | 25/25 (100%) | Candidate availability under chosen filters |
| Candidate source URL, credit/attribution, license code, date | 102/102 each | Credit is source-supplied/owner-derived and still needs checking |
| Exact normalized license URL | 22/102 | CC0 is explicit; short BY/SA codes did not establish exact versions in this normalization |
| Normalized sex, age, plumage, pose | 0/102 each | Source annotations may contain hints; no normalized biological tags verified |
| Downloaded photo renditions | 3 CC0 JPEGs; 2,059,912 bytes | 768×1024 or 1024×683; 388,627–893,589 bytes each |
| Downloaded recordings | 2 Commons MP3s; 3,312,292 bytes | Downy/Hairy samples, 36.16/101.51 s, mono 44.1/48 kHz, 192 kbps |
| Total sample storage | 5,372,204 bytes (5.37 MB decimal) | File bytes only; excludes cached metadata |
| Human-verified/approved assets | 0 | Usable teaching coverage and approval rate are unknown |
| Candidate state after AI triage | 101 candidates, 1 quarantined | No automatic promotion; target ambiguity flagged in yellowlegs frame |

Sample photo weaknesses include soft detail, partial body/tail view and multiple birds without an explicit target. These are directly relevant to realistic field-condition exercises, but require reviewed answer sufficiency and appropriate targeting. AI screening is not the owner's human review or an authoritative species determination.

The Commons woodpecker samples are credited to Jonathon Jongsma with original XC IDs 118417 and 175244 and CC BY-SA 3.0/4.0 respectively. They were fetched from Commons under its file-specific rights evidence, not from a restricted Cornell archive or through an unauthenticated XC download workaround. Exact byte sizes and source SHA-1 matched; local SHA-256 and audio container properties were recorded. No audio identity or call-type listening assessment occurred. Broad eastern-US song, contact, alarm and flight-call coverage remains unmeasured. [Photo manifest](../experiments/sample-assets.json), [audio manifest](../experiments/audio-samples.json).

**Rights feasibility:** open photo and some audio storage is demonstrably possible. Macaulay may fill difficult gaps only under explicit permissions; an embed grant cannot support cached/offline files. NC/ND or unknown licenses are excluded from the default corpus. Commons adaptations require applicable ShareAlike compliance. Ordinary eBird access and Status and Trends have separate Cornell terms; public/commercial expansion is not pre-cleared. [Detailed policies](media-policy.md), [source terms](data-sources.md).

## Throughput, cost and review burden

Measured structured CLI logs contain 25 successful photo queries, approximately 4.00 MB of response data and 34.59 summed request-seconds (34.81 seconds wall span). This is about 2.9 candidate records/second for metadata retrieval, conditional on these small queries; it is not download, curation or production throughput. Commons logged 10 successes plus one 429. eBird logged 12 successful network requests including taxonomy/version discovery; cached taxonomy reuse made no new network call. Initial probes, the regional query, browser research, file transfers and domain calls are separately scoped and excluded from those totals.

No provider API usage charge was observed for the discovery probes. Domain registration was the only billable action. Human review minutes, accepted yield, taxonomic error rate and specialist escalation cost are **not measured**. A scenario of 5,600 assets × 1–3 minutes is 93–280 hours before rejections and expertise; it must not be presented as a forecast. This all-asset review approach was subsequently rejected; current review is sampled within a two-hour TOTAL owner budget.

The proposed 3,000–4,200 photographs and 900–1,400 recordings translate to approximately 8.2–11.5 photos and 2.5–3.8 recordings per species for the observed 365-species universe. Actual required quantities depend on plumage/vocalization coverage, duplicate encounters, uncommon species and rights. One generic song clip per species is inadequate for the full product. Derive a gap matrix before increasing counts.

Hosting scenario: delivery media approximately 1.2–8.0 GB under stated size assumptions, or 20–60 GB including retained permitted masters/derivatives. At current R2 rates the latter costs $0.30–$0.90/month before allowances. Target hosting $0–$1/month incrementally if free/existing plans suffice, or $5–$6/month with a new paid Workers subscription, plus about $0.93/month domain amortization. Shared account usage and licenses can change this. No paid infrastructure was provisioned. [Cost assumptions and official rates](architecture.md).

## Remaining blockers and decision gates

| Gap | Next bounded action | Gate for proceeding |
| --- | --- | --- |
| Annual local reporting profiles unavailable | Owner-authorized histogram exports for county and two destinations, or approved EBD+sampling-event subset | Inspect actual bins, support and missingness; validate weekly mapping/fallback |
| Xeno-canto current docs/key/rights untested | Obtain XC key through owner and confirm official current docs/terms | Small authenticated metadata/audio test; measured eastern-US coverage and exact licenses |
| Human verification absent | Owner/expert reviews easy/hard/ambiguous photo and audio strata | Diagnostic evidence, exact rights, acceptance yield and timed burden accepted |
| Required biological coverage unknown | Build 25-species sex/age/plumage/view/vocalization gap matrix | Accepted minimum set under current automated policy, sampled audits and explicit unfilled cells |
| Commons throttling | Respect cooldown and test lower pace in a later authorized experiment | No repeated 429s; do not infer unlimited API access |
| Taxonomy/hotspot edge cases | Review historical aliases, source-site grouping, Illinois/Kentucky scope and unusual species | Versioned mapping; regular/rare/exceptional criteria |
| Cornell intended-use/redistribution scope | Confirm household pilot and future public/commercial use against actual grants | No restricted raw data or media distributed; written permission where required |

Deep Cuts was not found in the inspected local project metadata, so no architecture claims are based on it. Road Naturalist was inspected read-only; its separation of evidence and immutable-manifest practices inform the proposal without sharing its resources. Git was already initialized locally with no commits or remote; this work did not invent a GitHub push or modify shared infrastructure.

## Recommendation and stop point

Approve only a bounded data/review validation phase if the owner wishes to continue. Preserve Python/uv acquisition and a portable reviewed catalog; the preferred eventual runtime remains React/Vite, Hono/Workers, D1 and R2. Delay application work until full-year seasonal evidence, exact rights and a timed human review yield make the intended product credible.

The [roadmap](../ROADMAP.md) defines proposed acceptance gates through a local prototype, authorized private production pilot and measured regional expansion. Lower-cost agents can implement format-confirmed parsers, manifests, checksums, deduplication reports, fixtures and bounded adapters. Owner/expert judgment remains necessary for identification, rights, seasonal calibration and authorization decisions.

**Phase Zero review boundary reached.** No production app, deployment, paid infrastructure creation or bulk ingestion was performed. This report documents unresolved feasibility rather than claiming the complete dataset is proven.
