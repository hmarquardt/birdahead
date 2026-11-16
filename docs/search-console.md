# Search Console handoff

BirdAhead publishes an indexable homepage, public species and county landing pages, `sitemap.xml`, `robots.txt`, canonical URLs, Open Graph metadata and JSON-LD. Public pages carry `index,follow`; APIs, private media and administrative paths carry `noindex` or are disallowed in `robots.txt`.

## Current status

The existing CFLab Search Console collector has seven reviewed properties and does **not** include `sc-domain:birdahead.com`. The existing service account has no verified BirdAhead property, and no verification credential for BirdAhead is available in this workspace. Therefore the site has not been registered or submitted to Google Search Console, and no owner-reviewable verification token has been invented.

## Owner actions

1. Add `birdahead.com` as a **Domain property** in Google Search Console using a DNS TXT verification record. Domain verification is preferable because it covers apex and `www`.
2. Grant the existing CFLab Search Console service account at least `siteRestrictedUser` read access to the property.
3. In the adjacent CFLab project, add `sc-domain:birdahead.com` to the reviewed `GSC_PROPERTIES` list with `siteSlug: 'birdahead'`; redeploy CFLab Analytics through its existing gated pipeline.
4. Submit `https://birdahead.com/sitemap.xml` with an account holding Full/Owner permission. The current read-only service account previously received `403` for sitemap writes.
5. Verify Search Console reports indexed public pages and no private API/media URLs.

These are tracked as owner actions, not completed work. BirdAhead itself does not claim Search Console registration.
