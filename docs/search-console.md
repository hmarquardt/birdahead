# Search Console handoff

BirdAhead publishes an indexable homepage, public species and county landing pages, `sitemap.xml`, `robots.txt`, canonical URLs, Open Graph metadata and JSON-LD. Public pages carry `index,follow`; APIs, private media and administrative paths carry `noindex` or are disallowed in `robots.txt`.

## Current status

The owner verified `sc-domain:birdahead.com` as a Domain property and granted the existing CFLab Search Console service account read access. The adjacent CFLab project now includes the reviewed mapping `sc-domain:birdahead.com` → `birdahead` (mapping commit `2a6d74c`; final Analytics revision `472d922`), and the Analytics Worker passed all 10 read-only production checks. The production collector recorded the BirdAhead property with `siteRestrictedUser` access and 120 daily totals through 2026-11-08; there is no Search Console search traffic yet. Details are in the [GSC evidence](../experiments/phase-three-gsc.json). No second collector, service account or credential was created.

## Remaining owner actions

1. Submit `https://birdahead.com/sitemap.xml` with an account holding Full/Owner permission. The read-only service account previously received `403` for sitemap writes.
2. Verify Search Console reports indexed public pages and no private API/media URLs.

These are tracked as owner actions, not completed work. BirdAhead itself does not substitute first-party analytics for Search Console.
