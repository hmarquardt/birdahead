# BirdAhead analytics

BirdAhead uses the existing CFLab analytics collector, not a paid service and not a second analytics system.

| Item | Value |
| --- | --- |
| CFLab Site | `BirdAhead` (site id 10) |
| Public tracking ID | `as_Bq4kGnf2EkSW3dS0HZAddF` |
| Domains | `birdahead.com` primary; `www.birdahead.com` alias |
| Script | `https://analytics.aismallbizguru.com/script.js` |
| Collector | `https://analytics.aismallbizguru.com/collect` |
| Timezone | `America/Indiana/Indianapolis` |
| Retention | 90 days raw (CFLab policy) |
| DNT/GPC | honored |

## Registration

BirdAhead was registered as an additive CFLab Analytics Site on November 16, 2026, using the established Site/Domain model. The Time Travel bookmark before the write was `00000949-00000000-00005125-60e20eaf755bd64cc8d27669079febde`; after the write it was `00000949-00000006-00005125-df75984ec470b3cdc4d5f6f4c87624bd`. The change added only the BirdAhead Site, its two domains and the global-admin owner membership. No existing Site, domain, event, aggregate or CFLab code was changed.

## Collection and privacy

The canonical CFLab client is loaded with the BirdAhead public tracking ID. It sets no cookies and no persistent visitor ID, uses only a random `sessionStorage` session identifier for 30 minutes of inactivity, honors DNT/GPC, and stores only coarse derived browser/OS/device/country data. BirdAhead's CSP allows only the CFLab analytics script and collector in addition to self.

BirdAhead may send aggregate pageviews and public feature events such as `practice_start`, `practice_complete` and `species_view`. It must never send access keys, household identity, private progress, individual quiz answers, precise locations, email addresses or raw media. Guest quiz answers remain in browser localStorage. Household practice events do not include learner identity.

## Verification

A production-origin collection probe to `/collect` returned HTTP 204 and the corresponding row was observed in `analytics_events` for the BirdAhead Site. Evidence is in [the analytics verification](../experiments/phase-three-analytics.json). The browser script remains subject to CFLab bot filtering and DNT/GPC; local development origins are not registered and are intentionally not counted.

Google Search Console is integrated through the existing CFLab collector: `sc-domain:birdahead.com` is in the reviewed property list and maps to the `birdahead` Site (site id 10). The Analytics Worker uses the existing service account; no second collector or credential was created. See [Search Console](search-console.md); sitemap submission remains an owner action because the read-only service account does not have Full/Owner permission.
