# Phase Three — private household production release

November 15, 2026. BirdAhead is deployed at **https://birdahead.com** for two authenticated household learners. This is a private, noncommercial recreational release; no paid infrastructure, additional media acquisition, expanded geography or comprehensive biological audit was undertaken.

## Delivered

- React/Vite PWA served through the Cloudflare Worker with Hono API, dedicated D1 and private R2.
- Two independent learner identities, Hank and Heather, using separately generated household access keys and opaque revocable sessions.
- 589 accepted delivery objects / 436,400,934 bytes, including real photos, recordings and verified clips, published under the existing licenses and attribution.
- Actual seven-county seasonal curriculum and 100-species field-guide/coverage views using the imported 2016–2025 profiles.
- Authenticated media streaming with byte ranges; no public R2 URL, r2.dev endpoint or unauthenticated media route.
- Versioned release catalogs in R2, atomic D1 release activation/rollback, resumable publishing and checksum verification.
- PWA manifest, abstract BirdAhead icons, theme, service-worker app-shell caching, canonical host redirect, mobile navigation and connection/auth status.
- GitHub Actions validation and a manually gated provisioning/release workflow using the established Cloudflare secret names.

## Production verification

See [production operations](production.md), the [resource inventory](../experiments/phase-three-inventory.json) and the [smoke evidence](../experiments/phase-three-production.json). The live health endpoint reports the exact deployed revision and active release. HTTPS serves the canonical apex; `www` returns 308; `workers_dev` and preview URLs are disabled in the production config; the Worker rejects non-canonical hosts. Unauthenticated API and media requests return 401. Both profiles have independent D1 progress namespaces. Real photograph bytes and ranges were fetched through the authenticated endpoint, and the mobile browser decoded the actual media. A same-release rollback pointer was exercised successfully; a local D1 export was exercised, while a production restore drill remains deferred.

## Resource and cost summary

| Item | Provisioned | Incremental cost |
| --- | --- | --- |
| Worker `birdahead` | yes, custom apex/www domains | $0 under free dynamic/static allowance for two users |
| D1 `birdahead` | yes, 6 tables/indexes via reviewed additive migration | $0 under free tier; no paid plan changed |
| R2 `birdahead-private` | yes, private bucket; 0.406 GB delivery objects | $0 under 10 GB-month free allowance; raw storage at $0.015/GB-month ≈ $0.006/month if billed |
| Domain `birdahead.com` | already registered through 2027-11-15 | $11.17 registration already paid; auto-renew off |
| GitHub Actions | validation/deploy workflows | existing repository allowance |

Class A/B operations and future egress are separate and not measured as a bill. No paid subscription, additional domain or unrelated resource was created.

## Security and rights

All protected APIs, media and content are behind Worker-enforced sessions. Cookies are host-only, Secure, HttpOnly and SameSite=Strict. Login and publish endpoints have rate limits, origin/header checks and sanitized errors. Secrets live only in Worker/GitHub secrets and owner-only local files. R2 remains private; no public object URL is issued. The delivery scope remains private household noncommercial because most assets are CC BY-NC/CC BY-NC-SA; attribution and share-alike notices are retained. No restricted Cornell media, raw eBird exports, rejected media, local databases, model weights or captures are published.

## Media-quality review boundary

The existing automated acceptance policy remains unchanged. The existing 117-item audit queue is available but was not a mandatory pre-deployment checklist; owner review remains **0 of 7,200 seconds**. The earlier counterfactual Mallard/American Black Duck audio control remains a documented local risk. This release does not create human or expert approval. The in-app flag workflow remains available.

## Deferred

Full offline media packs, hands-free road-trip mode, additional geographic acquisition, further media expansion, commercial licensing, scheduled backup/restore drills and least-privilege token rotation remain subsequent work.
