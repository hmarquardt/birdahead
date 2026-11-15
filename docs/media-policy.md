# Media integrity, rights and review policy

Established November 15, 2026. This is the proposed production policy implementing the owner's integrity requirements; no production assets are approved yet.

## Admission rules

Only real photographs and real bird recordings with traceable provenance may enter production. No generated birds, synthetic bird vocalizations or unverified general search imagery. AI may discover candidates, flag duplicates, propose annotations and prioritize review; AI never supplies the sole species identification or final approval.

A source license and a verified taxonomic label are independent requirements. A beautiful photograph may be mislabeled, and a correctly identified recording may have unusable rights. “Research Grade,” a Commons filename, source quality score or API search match is candidate evidence. Preserve contrary identifications and uncertainty.

## Rights matrix

| Rights evidence | Candidate storage | Production delivery/offline | Modification |
| --- | --- | --- | --- |
| CC0, exact dedication recorded | Permitted subject to provenance review | Eligible after identity review | Eligible; preserve lineage |
| CC BY, exact version/creator/link | Permitted under its terms | Eligible with attribution and change notices | Eligible with required notices |
| CC BY-SA, exact version/creator/link | Permitted under its terms | Eligible with attribution and compatible terms | Adaptations retain appropriate ShareAlike license; review exact version |
| CC BY-NC variants | Only in a separately scoped noncommercial lane after review | Excluded from default corpus; future scope needs explicit rights decision | Check all conditions including SA/ND |
| ND or ambiguous derivative permission | Exclude from transformation workflow | Do not assume cropping/clipping/annotation is allowed | Hold pending explicit permission |
| All rights reserved / missing license | Metadata discovery/link only | Excluded | Excluded |
| Macaulay embed permission only | No file capture | Official allowed embed only; unsuitable for offline packs | No implied file/derivative permission |
| Explicit written license | Only specified behavior/term | Enforce delivery, offline, scope and expiry limits | Only specified modifications |
| Public-domain government work | Verify file-specific status, creator and jurisdiction | Eligible after evidence/identity review | Preserve provenance and notices |

These are project gates, not a claim every license has identical obligations. Record the actual deed/version. CC BY requires attribution, license links and notices of changes; CC BY-SA adds conditions on adaptations. Do not add incompatible DRM. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Macaulay has separate permission and credit rules. [Macaulay usage](https://support.ebird.org/en/support/solutions/articles/48001064551).

The iNaturalist API's short `cc-by`/`cc-by-sa` codes alone do not establish the exact version in this experiment. License URL/version stays unknown unless supplied/checked. Observation owners are proposed credit sources; verify the asset's photographer credit rather than equating uploader and creator. Source credit text may contain HTML and must be sanitized safely for display.

## Required provenance contract

| Group | Required record |
| --- | --- |
| Identity | BirdAhead taxon ID; source taxonomy/ID/name; canonical authority/version; mapping evidence; identification status |
| Source | Provider; record/asset ID; original record URL and media URL; capture date; source response/revision digest where available |
| Authorship/rights | Photographer/recordist; original credit; exact license/version/URL or written grant; attribution text; storage/modification/delivery/offline permissions; expiry and restrictions |
| Biological context | Known age, sex, plumage, breeding relevance, pose/view, target individual, vocalization type/background species; label author/evidence/confidence |
| Place/time | Source date/time precision, region/locality and privacy rules; never reverse-engineer obscured/sensitive coordinates |
| Technical/lineage | Actual dimensions or duration/codec/sample rate; byte count; checksum; derivative parent/recipe/tool version; quality flags |
| Review | State; reviewer; evidence/reference; decision/reason; review time; dispute status and audit events |

Use null for unavailable values; source assertions and reviewer-confirmed attributes are separate fields. A month or adult-looking plumage does not justify inventing age, sex, exact locality or breeding status. A source's “call” label is not a verified specific alarm/contact/flight-call label.

## Review states and workflow

1. **Candidate:** metadata acquired under an allowed discovery policy. Gather rights evidence before file acquisition. Deduplicate source IDs and checksums; cluster similar images/audio from the same encounter to avoid counting duplicates as variety.
2. **Technical/rights triage:** confirm media type, decodability, resolution/duration and required metadata. Flag blur, clipping, noise, background species, uncertain target, missing marks, sensitive places and rights gaps. Automated checks may quarantine or reject, never approve.
3. **Human identification review:** show the source record, current community IDs/disputes, original media and field-guide references together. Record visible/audible diagnostic evidence and whether it supports species-level identification. For hard pairs require an independent second reviewer or an appropriately qualified expert. Shared agreement without diagnostic evidence is insufficient.
4. **Teaching review:** mark which individual/interval is the target; suitability for recognition vs recall, evidence sufficiency, field marks and challenge tags. Independent people validate annotations and vocalization labels. Some ambiguous examples may become expressly approved insufficient-information exercises; they are never normal definitive-ID cards.
5. **Approved:** only after rights, identity, teaching metadata and technical checks are complete. A release builder accepts approved records with unambiguous lineage and complete attribution. **Rejected** records retain reasons and IDs to avoid re-fetching; **quarantined** records remain unavailable until an explicit resolution event.

Run batching locally: prioritize coverage gaps and one best candidate per encounter/creator; present a concise review queue with source links and suggested tags. Sample easy species for second review and require it for hard pairs. Track duration, reject reasons and escalation separately by source/species/challenge. Human review cannot be replaced by a global “approve all Research Grade” action.

The three sample images received AI visual triage only. Multi-individual yellowlegs imagery is quarantined for target ambiguity in the sample manifest. No biological tag or definitive identity was approved from that screening. The two audio samples passed byte/checksum and container inspection; no expert listening review occurred.

## Derivatives, updates and privacy

Keep permitted source renditions immutable. Derivatives record input digest, crop/clip bounds, resampling, normalization/filtering, annotation data and output digest. Never generatively fill bird anatomy, remove diagnostic marks or fabricate calls. Separate pedagogical annotations from biological source pixels when possible. Spectrograms derive from real audio and inherit applicable rights considerations; generated speech may reveal an answer but cannot mimic a bird as training evidence.

Do not train commercial AI models on iNaturalist data; its current platform terms expressly restrict this. Automated candidate screening in this project is not a license to train a new classifier. [iNaturalist terms](https://www.inaturalist.org/pages/terms).

Periodically recheck source identity disputes, removed records and rights evidence. Preserve the acquisition-time license evidence; valid open-license permissions and a later source-license change require careful handling rather than silent overwrite. Disable disputed assets pending resolution, retain an audit trail and publish updated manifests. Purge sensitive location data from public exports, logs, EXIF and derivatives; private source captures have restricted local access. Offline packs must retain credits and support expiry/revocation checks on reconnection.
