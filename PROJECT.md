# BirdAhead product specification

Status: canonical scope, established November 15, 2026. Product capabilities below are requirements for future phases, not implemented behavior. Feasibility evidence belongs in docs/feasibility.md.

## Mission and audience

**Learn the birds you're about to meet.** BirdAhead proactively prepares birders for upcoming encounters. Initial users are two active recreational birders in Gibson County and southwestern Indiana. The application should make a five-minute practice session feel useful and engaging, with clear progress and manageable challenges.

Initial destinations include Gibson Lake, Cane Ridge, Snakey Point, the Wabash River corridor, Sugar Ridge and Goose Pond Fish and Wildlife Area. Nearby Illinois and Kentucky belong in the geographic design. Destination-specific decks should use the outing date, habitats and available evidence. Expansion must add regions and data, rather than require a new architecture.

## Learning requirements

Visual practice includes photo flashcards, multiple-choice and unassisted recall, several photographs per species, sexes, juvenile/immature plumages, breeding/nonbreeding plumages, flight, silhouettes, undersides, distance and partial obstruction. Field-mark annotations must describe evidence actually visible in the example. Comparisons should explicitly train commonly confused pairs.

Audio practice includes audio-only identification, song, contact/alarm/flight calls and other relevant sounds, multiple recordists and examples, regional/seasonal relevance and vocal confusion pairs. Spectrograms are optional representations of real recordings. Never synthesize bird sounds or generate bird imagery for the training corpus.

Two independent profiles track mastery by species × modality × challenge type, including plumage or vocalization. Track directed confusion pairs and the example that elicited the confusion. Spaced repetition must preferentially reinforce weaknesses while periodically testing stronger skills on unseen examples. Separate recognition from recall and avoid mastery inflation from memorizing one photograph or recording.

Exercises support “insufficient information” when a reviewer determines the media cannot support a definite species answer. Unknown, incorrect, ambiguous and defective examples are distinct outcomes. Learner confidence can be recorded and calibrated; guessing must not create false confidence. Ambiguous examples cannot silently count as normal species-identification successes or failures.

## Geographic and seasonal requirements

Geography and time are inputs to curriculum construction. Store region, hotspot, habitat, source-native time bins, week/date alignment, historical reporting frequency with effort support, modeled occurrence/relative abundance where available, recent observations and migration context as distinct signals.

Curriculum surfaces are Always Around, Here Now, Arriving Soon (two to four weeks ahead), Passing Through and Personal Weaknesses. Overlap is allowed; explanations should identify the source, geography, dates, uncertainty and freshness behind a recommendation. A notable sighting must not dominate a deck merely because it is unusual.

Do not label raw sighting counts as frequency, frequency as abundance, or modeled relative abundance as a guaranteed local count. Sparse hotspots need an explicit fallback to a supported parent region. Handle reporting effort, observer behavior, habitat sampling bias, old data, unusual sightings, absences and source coverage gaps.

## Integrity and rights

Every asset requires canonical taxon and source identifiers, source URL, creator/recordist, exact rights and attribution, storage/modification/delivery permissions, verification state, available time/geography, biological attributes, technical metadata, checksum and derivative lineage. Unknowns remain unknown. Sensitive locations stay protected.

Separate candidates, rejected assets, quarantined assets and approved assets. Research Grade, a source filename or an AI classification is never sufficient on its own for production approval. Use efficient human review with automated triage and evidence capture; resolve difficult or disputed examples with suitable expertise. Respect Cornell media restrictions and per-asset open licenses.

## Technical direction and UX horizons

Preferred stack: Python/uv ingestion; TypeScript/React/Vite PWA; Hono/Workers API; D1 relational metadata and learning progress; R2 approved media; IndexedDB plus service workers for selective offline packs. Runtime learning uses versioned approved content and does not depend on third-party media APIs. Favor low cost, reproducible exports and source-specific adapters.

Future UX includes daily sessions, seasonal preparation, outing decks, personal life lists, offline packs, hands-free road-trip audio with spoken reveals, independent/shared two-person sessions, dashboards/mastery maps and confusion practice. These are design constraints; none is authorized for implementation during discovery. Audio playback must avoid encouraging unsafe interaction while driving.

## Phase Zero contract

Discover APIs, access, licensing and regional seasonality; design a representative 25-species pilot; run limited compliant experiments; measure retrieval, coverage, metadata, confidence, review effort, storage, throughput and costs. Required pilot pairs: Cooper's/Sharp-shinned Hawks, Downy/Hairy Woodpeckers, Turkey/Black Vultures and Greater/Lesser Yellowlegs. Choose the other 17 using observed regional evidence and stress seasonal/plumage/audio requirements.

The expanded 300–350 species, 3,000–4,200 photographs and 900–1,400 recordings are planning hypotheses. Distinguish an all-time recorded universe from a prioritized teaching set. Do not force results to match those estimates.

Authorized now: repository initialization, research, documentation, minimal local tooling, bounded lawful acquisition, and the completed birdahead.com purchase. Excluded: production deployment, paid infrastructure creation, bulk ingestion, other purchases and application implementation. Subsequent phases require owner authorization at the Phase Zero review boundary.
