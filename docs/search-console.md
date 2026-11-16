# Search Console handoff

BirdAhead publishes an indexable homepage, public species and county landing pages, `sitemap.xml`, `robots.txt`, canonical URLs, Open Graph metadata and JSON-LD. Public pages carry `index,follow`; APIs, private media and administrative paths carry `noindex` or are disallowed in `robots.txt`.

## Current status

The owner verified `sc-domain:birdahead.com` as a Domain property and granted the existing CFLab Search Console service account read access. The adjacent CFLab project now includes the reviewed mapping `sc-domain:birdahead.com` → `birdahead` (commit `2a6d74c`), and the Analytics Worker was released at that revision with all 10 read-only production checks passing. The production collector runs in the existing hourly cron; its first BirdAhead result is recorded in [production evidence](../experiments/phase-three-production.json). No second collector, service account or credential was created.

## Remaining owner actions

1. Submit `https://birdahead.com/sitemap.xml` with an account holding Full/Owner permission. The read-only service account previously received `403` for sitemap writes.
2. Verify Search Console reports indexed public pages and no private API/media URLs.

These are tracked as owner actions, not completed work. BirdAhead itself does not substitute first-party analytics for Search Console.
