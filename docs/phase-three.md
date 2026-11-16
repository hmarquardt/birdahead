# Phase 3.1 — public utility, private personalization

November 16, 2026. BirdAhead is deployed at **https://birdahead.com** as a free, noncommercial public birding resource with optional household profiles for Hank and Heather. Public exploration, the field guide, eligible media and guest practice require no account; server-backed progress, identities, publishing and administration remain protected. No paid infrastructure, advertising, additional media acquisition, expanded geography or comprehensive biological audit was undertaken.

## Delivered

- React/Vite PWA served through the Cloudflare Worker with Hono API, dedicated D1 and private R2.
- Public guest exploration, field-guide, eligible photo/recording practice and browser-local summaries with no registration or account.
- 589 accepted delivery objects / 436,400,934 bytes, including real photos, recordings and verified clips, published under the existing licenses and attribution.
- Actual seven-county seasonal curriculum and 100-species field-guide/coverage views using the imported 2016–2025 profiles.
- Public eligible media streaming through the Worker with byte ranges and private R2 binding; no public R2 URL or r2.dev endpoint.
- Versioned release catalogs in R2, atomic D1 release activation/rollback, resumable publishing and checksum verification.
- Optional two independent learner identities, Hank and Heather, using separately generated household access keys, opaque revocable sessions and server-backed progress.
- Public species/county landing pages, canonical/OG metadata, JSON-LD, sitemap, robots, privacy/source pages and selective noindex.
- Inline, data-URI SVG favicon on the homepage and every public page, with the existing PNG PWA icons and manifest preserved; no new raster or ICO assets.
- Standardized public tagline: **Learn the birds you're about to meet.**
- Existing CFLab Search Console collector mapping integrated for the verified `sc-domain:birdahead.com` Domain property; the production collector wrote 120 daily rows (zero search traffic so far) with `siteRestrictedUser` access, and the collector remains server-to-server and read-only.
- **Phase Four offline learning:** selective County outing, Here Now, Arriving Soon, photo, audio and complete eligible-collection packs; shared-media deduplication, resumable asset downloads, SHA-256 integrity, local guest practice, and profile-bound offline attempt sync. See [offline learning](offline.md). Hands-free road-trip mode remains deferred.

- CFLab analytics registration and verified aggregate event ingestion.
- GitHub Actions validation and a manually gated provisioning/release workflow using the established Cloudflare secret names.

## Public/private boundary

Public endpoints use `/api/public/*` and `/media/public/*` and only expose objects with an explicit `public_delivery` decision in the active release catalog. The R2 bucket has no public access. Guest practice is generated from public-eligible questions and scored in the browser; no guest account or server-side guest history exists. Authenticated household endpoints retain independent D1 progress, sessions, flags and private collection views. Publishing and release activation remain token-authenticated operator actions. eBird-derived seasonal summaries are public under the eBird Data Access Terms; raw exports stay private.

## Production verification

See [production operations](production.md), the [resource inventory](../experiments/phase-three-inventory.json), the [public smoke evidence](../experiments/phase-three-public.json) and the [private smoke evidence](../experiments/phase-three-production.json). The latest non-browser release smoke passes **18/18** public and **23/23** private checks; the earlier browser-inclusive run passed **19/19** public and **25/25** private checks, including mobile media decode and guest-history persistence. The live health endpoint reports the exact deployed revision and active release. HTTPS serves the canonical apex; `www` returns 308; `workers_dev` and preview URLs are disabled in the production config; the Worker rejects non-canonical hosts. Unauthenticated public exploration works; private API/media/admin requests remain rejected. Both profiles have independent D1 progress namespaces. Real photograph and audio bytes/ranges were fetched through the authenticated endpoint, and the mobile browser decoded the actual media. A same-release rollback pointer was exercised successfully. A private production D1 export was taken and recorded; a production restore drill remains deferred. Aggregate analytics pageviews were observed for the BirdAhead Site. The CFLab Search Console mapping is integrated; sitemap submission and the eBird derived-product notification remain owner actions.

## Resource and cost summary

| Item | Provisioned | Incremental cost |
| --- | --- | --- |
| Worker `birdahead` | yes, custom apex/www domains, public rate limit and edge cache | $0 under free dynamic/static allowance; public traffic and egress are not claimed as zero beyond the allowance |
| D1 `birdahead` | yes, 6 tables/indexes via reviewed additive migration | $0 under free tier; no paid plan changed |
| R2 `birdahead-private` | yes, private bucket; 0.406 GB delivery objects | $0 under 10 GB-month free allowance; raw storage at $0.015/GB-month ≈ $0.006/month if billed |
| Domain `birdahead.com` | already registered through 2027-11-15 | $11.17 registration already paid; auto-renew off |
| GitHub Actions | validation/deploy workflows | existing repository allowance |

Class A/B operations and future egress are separate and not measured as a bill. No paid subscription, additional domain or unrelated resource was created.

## Security and rights

Public exploration, public eligible media and guest practice are intentionally anonymous. Private APIs, private media, household progress, publishing and administration remain behind Worker-enforced sessions and token authorization. Cookies are host-only, Secure, HttpOnly and SameSite=Strict. Login and publish endpoints have rate limits, origin/header checks and sanitized errors. Secrets live only in Worker/GitHub secrets and owner-only local files. R2 remains private; no public object URL is issued. The delivery scope is public noncommercial; most assets are CC BY-NC/CC BY-NC-SA, so attribution and share-alike notices are retained and commercial use remains prohibited. No restricted Cornell media, raw eBird exports, rejected media, local databases, model weights or captures are published.

## Media-quality review boundary

The existing automated acceptance policy remains unchanged. The existing 117-item audit queue is available but was not a mandatory pre-deployment checklist; owner review remains **0 of 7,200 seconds**. The earlier counterfactual Mallard/American Black Duck audio control remains a documented local risk. This release does not create human or expert approval. The in-app flag workflow remains available.

## Deferred

Hands-free road-trip mode, additional geographic acquisition, further media expansion, commercial licensing, scheduled backup/restore drills and least-privilege token rotation remain subsequent work.
