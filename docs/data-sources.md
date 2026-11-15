# Data-source evaluation

Checked November 15, 2026. “Documented” means an official source describes a capability. “Observed” means a bounded request succeeded here. Neither establishes blanket reuse permission or production content quality. API quotas can change; internal pacing is not a provider guarantee.

## eBird API v2

**Observed:** public taxonomy and version requests returned JSON; latest authority version was 2026. All 25 pilot scientific names agree between the sampled iNaturalist taxonomy and current eBird taxonomy. Current names include `Astur cooperii` and `Leuconotopicus villosus`; preserve older genus aliases on historical media.

After loading `EBIRD_API_KEY` from the shared credential convention, seven county species-list queries, a Gibson County hotspot query, a recent query and a historical-date query succeeded. The union contained 382 reported taxon codes, of which 365 matched species-level taxonomy. All pilot species occur in the union. Gibson returned 29 hotspots, including Cane Ridge WMA (`L320465`), Gibson Lake Wildlife Habitat (`L1872968`) and Snakey Point Marsh (`L564337`). These IDs identify occurrence scopes, not land-access permission. See [derived evidence](../experiments/ebird-evidence.json).

| Function | Integration characteristics and limits |
| --- | --- |
| Taxonomy | `GET /v2/ref/taxonomy/ebird?fmt=json&cat=species`; version discovery at `/ref/taxonomy/versions`; CSV also documented. Snapshot codes and scientific names with authority release. |
| Region species list | `/product/spplist/{regionCode}` returns reported taxon codes, not a frequency curve or a list of regular residents. |
| Hotspots | `/ref/hotspot/{regionCode}?fmt=json`; region/nearby hotspot lookup and hotspot information support destination mapping. Confirm the actual site/unit rather than fuzzy-name merging. |
| Recent reports | `/data/obs/{regionCode}/recent`; geographic/hotspot and notable-report endpoints documented. Recent window is limited, not an annual occurrence archive. Tested `back=30`, cap 30; 30 rows returned. |
| Historical reports | `/data/obs/{regionCode}/historic/{year}/{month}/{day}`; tested Gibson on 2026-05-10, cap 25; 25 rows returned. A single-day presence output does not expose a denominator for all complete checklists. |
| Personal data | Owner-authorized “Download my data” spreadsheet is documented; no personal import was supplied/tested. Do not assume public API access to another person's full life list. |

Ordinary access uses `X-eBirdApiToken` in a server-side header. Never place it in a browser, logged command or URL. The current CLI's source captures stay private. No verified fixed numeric eBird rate allowance was established; use conservative pacing and halt/back off on errors.

The [official API reference](https://documenter.getpostman.com/view/664302/S1ENwy59) is JavaScript-rendered and yielded no readable body to the research browser; endpoint claims above are limited to observed requests or the scope described by Cornell's [download help](https://support.ebird.org/en/support/solutions/articles/48000838205-download-ebird-data). Do not treat unofficial client code as Cornell's license.

**Rights:** API access is noncommercial under the published terms; commercial use needs prior written permission, with a broad definition covering work for a for-profit entity. Attribute eBird and link where practical. Source datasets cannot be publicly redistributed in original format; derived datasets carry the same data terms. Keep original responses private and review the intended household/public-app use before distributing content packs. An API key does not grant media or other Cornell-product rights. [API terms](https://www.birds.cornell.edu/home/ebird-api-terms-of-use/), [data terms](https://www.birds.cornell.edu/home/ebird-data-access-terms-of-use/).

## Historical reporting frequency and eBird Basic Dataset

Cornell documents a “Download Histogram Data” link on regional/hotspot bar charts. Frequency is the fraction of complete checklists reporting a species. That is a promising low-volume pilot source. The actual Gibson chart request here returned HTTP 200 with a bot challenge, not data. No histogram file, time-bin schema or checklist denominator was acquired. Use a normal authorized manual export; do not scrape internal endpoints or bypass challenges. [Bar-chart explanation](https://support.ebird.org/en/support/solutions/articles/48001255130-ebird-bar-charts-and-graphs).

For reproducible effort-aware analysis, an approved EBD plus sampling-event data is the stronger path. Species rows alone omit nondetections; complete checklist events are needed for denominators. Access requires a project request and applicable terms, independently of API v2. Cornell describes monthly updates, effort fields and a separate checklist-event download; acquisition was not performed. EOD/GBIF occurrence-only data is insufficient for checklist reporting frequency. [Download help](https://support.ebird.org/en/support/solutions/articles/48000838205-download-ebird-data).

## Status and Trends

Documented products include 52-layer weekly GeoTIFF occurrence/count/relative-abundance estimates at 3, 9 and 27 km resolutions, seasonal ranges as GeoPackage and regional summaries as CSV. Estimates standardize observer/effort conditions; their units differ from reporting frequency. Model quality and unsupported/NA areas matter. Do not load global cubes into D1. [Product guide](https://ebird.github.io/ebirdst/articles/status.html).

Programmatic access is possible directly from Python, without adding R to the main pipeline: the official API lists available species/version objects and downloads requested files. It requires a distinct Status and Trends access key obtained through the product-access form. No product key or raster was tested. Products have separate noncommercial/commercial and derivative-use terms; check the actual release and required notices before redistribution. [API guide](https://ebird.github.io/ebirdst/articles/api.html), [access instructions](https://ebird.github.io/ebirdst/), [product terms](https://is-ebird-wordpress-prod-s3.s3.amazonaws.com/wp-content/uploads/sites/55/2021/07/eBird-Status-Trends-Terms-of-Use-2023-Updates_20231115_FINAL.pdf).

## Macaulay Library

Gold-standard reference and possible permission-based gap filler. Official guidance permits noncommercial sharing through the supplied embed interface, with credits; personal downloading of others' media is unavailable. Some research/educational requests may be free; other educational and commercial uses require licensing. No broad public file-acquisition API or entitlement was established. No media were scraped or downloaded.

BirdAhead's stored media, crop/annotation/audio derivatives and offline packs require explicit permission for those behaviors. Embedding alone cannot meet the offline/runtime-independence requirement. Seek specific asset IDs and a scoped license if needed; this engagement did not send a request. [Usage/request instructions](https://support.ebird.org/en/support/solutions/articles/48001064551), [credit requirements](https://support.ebird.org/en/support/solutions/articles/48001064570-crediting-media).

## iNaturalist

**Observed:** unauthenticated v1 JSON queries support taxon, Research Grade, wild/captive, photo-license and rectangular geographic filtering. A regional all-time query returned 294 taxon entries, including 292 species-level entries. Twenty-five media queries sampled three recent eastern North American observations per pilot species; see measured coverage in feasibility.

Photo licenses are independent of observation licenses. The sampled responses expose photo IDs, owner-derived credit, attribution, dimensions, dates, community taxon, agreement/disagreement counts and annotations. Research Grade is consensus evidence, not a guarantee of species correctness. Inspect disputes, current community ID and diagnostic media separately. [Official API](https://api.inaturalist.org/v1/docs/), [platform terms](https://www.inaturalist.org/pages/terms), [consensus research](https://academic.oup.com/bioscience/advance-article/doi/10.1093/biosci/biag135/8820383).

Use asset-level CC0/CC BY/CC BY-SA filters for discovery and resolve exact version/credit before release. Do not infer rights solely from a host name. The API returns small square URLs; documented size substitution provides 500 px medium, 1024 px large and up to 2048 px “original,” bounded by the uploaded image. Three CC0 large JPEGs were downloaded and decoded. [Official API implementation/schema](https://github.com/inaturalist/iNaturalistAPI/blob/main/lib/views/swagger_v1.yml.ejs), [photo download help](https://help.inaturalist.org/en/support/solutions/articles/151000233085-how-to-download-a-photo-from-inaturalist).

Published guidance asks for about one request/second and about 10,000/day, prefers exports/GBIF for bulk work and warns about 5 GB/hour or 24 GB/day media download limits. The pilot used small queries, caching and delays. No authenticated/private coordinates were requested. [Recommended practices](https://www.inaturalist.org/pages/api+recommended+practices). Later bulk acquisition requires a fresh scope/terms decision; the open-data project documents an alternative snapshot path with its own per-photo rights. [Open-data documentation](https://github.com/inaturalist/inaturalist-open-data).

## Wikimedia Commons

**Observed:** unauthenticated MediaWiki Action API search plus `imageinfo` returned file IDs, source URLs, sizes, SHA-1, credit and license metadata. Eight two-result photo searches succeeded. Two two-result audio searches succeeded; the next audio query returned 429, so execution stopped. Conservative future pacing was increased to five seconds; it has not been revalidated and is not a promised quota.

`extmetadata` is HTML-bearing and potentially incomplete; sanitize before displaying it. Request only small batches because the property is expensive. File descriptions/structured taxon statements and original provenance need review; neither filenames nor search relevance certify identification. Commons can contain illustrations and generated media, so enforce photographic/real-recording checks. [Imageinfo API](https://www.mediawiki.org/wiki/API:Imageinfo), [machine-readable metadata](https://commons.wikimedia.org/wiki/Commons:Machine-readable_data).

Each file's license and authorship govern reuse. Two mirrored Xeno-canto recordings carried CC BY-SA 3.0/4.0 evidence on Commons and were downloaded from Commons, preserving recordist, original XC IDs and rights. This verifies those files' retrievability, not the current Xeno-canto API or its full catalog. [Reuse policy](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia), [Hairy Woodpecker example](https://commons.wikimedia.org/wiki/File:Picoides_villosus_-_Hairy_Woodpecker_XC175244.mp3).

## Xeno-canto

**Observed:** `https://xeno-canto.org/api/3/recordings` returned HTTP 401 and a message requiring a valid `key` parameter. No XC credential was found/supplied. The official [API page](https://xeno-canto.org/explore/api), [search help](https://xeno-canto.org/help/search) and [terms page](https://xeno-canto.org/about/terms) returned access challenges to the research browser. No challenge was bypassed.

**Pending official confirmation and authenticated testing:** exact v3 query grammar, pagination/max page size, rate limits, quality grades, identification-dispute indicators and current license options. Grade A/B selection, eastern-North-American locality filters, song/call classification and exclusion of identity-disputed recordings are proposed selection criteria. Quality ratings cannot substitute for identity review. Preserve recordist, source ID, locality/date precision, vocalization labels, background species, edits and exact per-recording license where returned. Redact query credentials from logs if the API requires them in URLs; the present generic client intentionally refuses credential query parameters. Do not claim keyless v2 tutorials are current.

The two Commons mirrors demonstrate one legal acquisition route for representative audio, but do not establish 25-species song/call coverage. No blanket recording license, API throughput or eastern-US usable yield is verified.

## BirdCast and reference sources

BirdCast's current site is birdcast.org. Official materials describe radar-derived migration intensity and forecasts; the FAQ says radar alone does not determine species, and birds passing overhead need not stop locally. Citation instructions exist for maps and dashboards. No authorized general-purpose machine API, export grant, fixed quota or redistribution license was established. Keep BirdCast optional, initially as a link/reference; require explicit access/rights confirmation before ingesting forecasts. Never treat aggregate migration intensity as species occurrence. [FAQ](https://birdcast.org/faq/), [citation](https://birdcast.org/how-to-cite/).

Indiana DNR reports more than 300 documented species at Goose Pond and provides a bird checklist. It is an independent plausibility check and habitat/destination reference, not weekly occurrence data or a blanket photo license. [Goose Pond](https://www.in.gov/dnr/fish-and-wildlife/properties/goose-pond-fwa/), [checklist](https://www.in.gov/dnr/fish-and-wildlife/files/fw-GoosePond_BirdList.pdf).

USFWS media are a possible vetted photographic gap filler, but the agency warns that not all site content is public domain; inspect each file's credit/rights. Museum specimens may help taxonomy and reference identification but often fail realistic field-photo needs; no museum batch/API was tested. [USFWS copyright](https://www.fws.gov/disclaimer).

All About Birds can support manual reference checking and links. Its general educational provisions do not grant unrestricted copying/rehosting into a public training app. Write original learning explanations backed by references, or obtain explicit permission. [Cornell terms](https://www.birds.cornell.edu/home/terms-of-use/).
