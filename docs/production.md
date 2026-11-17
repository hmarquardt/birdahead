# BirdAhead production operations

Status: public noncommercial educational release with optional private household profiles, November 16, 2026. Canonical URL: **https://birdahead.com**. `www.birdahead.com` redirects with HTTP 308. Public exploration, field guide, eligible media and guest practice require no account; private progress, identities and administration remain authenticated.

**Header layout revision, November 16, 2026:** revision `a24e8dd044879ea02128b3661e67e2cb8e637ced` corrects only the header authentication layout so the household identity/status and the Sign out control share one vertically centered flex row; the anonymous `Household sign in` control keeps the same behavior. Verified in the local Worker at 1280×900, 390×844 and 320×700 for both states (0px vertical center delta, no header overflow, long identity truncates without moving the control) and in production at 1280×900 and 390×844 for both states. Production smoke passed 25/25 including the browser check. Deployment used the manual gated dispatch; `CLOUDFLARE_DEPLOY_ENABLED` remained `false`, the active content release stayed `5604f5690467b2d362cfb75da1aa8a1536902dc15db77f9c42afe08b8950834a`, and no catalog, media or geographic publication changed.

**UI quality and accessibility revision, November 16, 2026:** revision `66e662a6ae4e830b1b7fccd5916c092730fafbd9` deploys the [UI audit](ui-audit.md) corrections: the Field Guide segmented control (reported at 1.08:1), shared muted/eyebrow contrast, a 10 px informational text floor, consistent button/target sizing, dialog focus handling, chart/label semantics and the 390 px Road Trip/Migration overflow. The browser sweep rendered 165 states across 15 views and six widths in anonymous and signed-in modes with **zero** contrast, target-size, accessibility, sub-10 px or unintended-overflow findings; static token/contrast checks run in the Python suite. Production verification after release `43998303489`: the deployed CSS is `index-DSz50zYS.css` with `--muted: #5b655d` and `--eyebrow: #586649`; the unselected Photos/Sounds controls render forest text on `#fffdf8` with `aria-pressed="false"`; document overflow is 0 px at 360/390/768 for Migration, Road Trip, Downloads and Compare; the crawlable Sources page is styled and shows a 3 px focus ring; the header centers coincide at 768/1440 (the profile occupies its own row at ≤480 by design); production smoke passed 25/25. Deployment used the manual gated dispatch; `CLOUDFLARE_DEPLOY_ENABLED` remained `false`, the active content release stayed `5604f5690467b2d362cfb75da1aa8a1536902dc15db77f9c42afe08b8950834a`, and no catalog, media, progress, privacy or geographic publication changed.

**Phase Eight gate, November 16, 2026:** `CLOUDFLARE_DEPLOY_ENABLED` was observed enabled and reset to `false` before pushing the geographic architecture. No geographic code/content deployment was performed. The live accepted release remains in place. [Geographic release prerequisites, staging and rollback strategy](phase-eight.md). No backup, rollback or token-scope change occurred.

## Resource inventory

| Resource | Name / identity | Purpose |
| --- | --- | --- |
| Cloudflare Worker | `birdahead` | Hono API, public eligibility-gated content/media, optional session auth, static PWA |
| Worker version | recorded in [production evidence](../experiments/phase-three-inventory.json) | exact live revision/version |
| D1 | `birdahead` (`ce2302c9-988b-490c-9ad3-3035d0a57c8b`) | profiles, sessions, attempts, flags, release pointer |
| Private R2 | `birdahead-private` | 589 delivery media objects + versioned catalogs; public access/r2.dev disabled |
| Zone | `birdahead.com` (`03524416f9bc90b22119b587716866ef`) | apex and `www` custom domains, HTTPS |
| GitHub Actions | `ci.yml`, `deploy.yml` | validation; manually gated production provisioning/release |

No unrelated Worker, D1, R2 bucket, DNS record, shared service or billing plan was modified. No paid subscription or domain purchase was made.

## Authentication

Public visitors require no account. Two optional household learner identities, **Hank** and **Heather**, authenticate with independently generated 256-bit access keys for persistent progress and cross-device continuity. The keys are held only in:

- the owner-only local file `~/.config/secrets/birdahead.env` (mode 0600), never printed or committed;
- Cloudflare Worker secrets `HANK_KEY` and `HEATHER_KEY`;
- GitHub Actions secrets `BIRDAHEAD_HANK_KEY` and `BIRDAHEAD_HEATHER_KEY` for release provisioning.

There is no public registration, email recovery, password reset, public identity provider, guest server account or default credential. The optional household sign-in selects the learner and posts the key over HTTPS. The Worker stores only SHA-256 hashes of opaque 256-bit session tokens. Cookies are host-only `__Host-birdahead-session`, `HttpOnly`, `Secure`, `SameSite=Strict`, with a 30-day lifetime. Mutations require same-origin `Origin`/`Sec-Fetch-Site` checks and the custom `X-BirdAhead-Request` header. Login is rate-limited (10 attempts/minute/IP) and publish endpoints separately rate-limited.

To rotate a key: replace the relevant GitHub secret and the local private file, rerun the gated deployment (or update the Worker secret), and retain the new key in the owner password manager. Rotating either key does not delete learning history; existing sessions remain until expiry unless sessions are cleared.

## Publishing and content releases

The public catalog contains only assets with an explicit public-noncommercial eligibility decision. The local publisher sends accepted bytes only to the authenticated Worker, which writes them to private R2 through its binding. Public media is served by `/media/public/:id`; private household media remains `/media/:id`. No R2 credential is exposed locally or in the browser. The local ledger is ignored private state.

```sh
# Publish/activate the current accepted release (production)
uv run python -m tooling.cloud_publish --origin https://birdahead.com --resolve-ip <current-edge-ip>

# Re-publish only the versioned catalog after a content correction
uv run python -m tooling.cloud_publish --origin https://birdahead.com --resolve-ip <current-edge-ip> --catalog-only

# Verify all ledger objects against remote metadata
uv run python -m tooling.cloud_publish --origin https://birdahead.com --resolve-ip <current-edge-ip> --verify
```

The publisher validates local SHA-256/size, skips unchanged ledger objects, resumes interrupted transfers, verifies every upload through the Worker, uploads `releases/<release-id>/catalog.json`, and activates only after all media are available. `--rollback-id <release-id>` atomically changes the active D1 pointer. Media objects are immutable content-addressed keys; old releases remain available for rollback. Only accepted, delivery-permitted assets are in the manifest. Revoked or quarantined assets are omitted from the next catalog; do not delete old objects until a separately reviewed retention action.

## Backups and rollback

- **D1:** use Cloudflare D1 Time Travel plus a private export (`npx wrangler d1 export DB --remote --config <generated-config> --output <private-file>`). A production export was taken on 2026-11-16; see [backup evidence](../experiments/phase-three-backup.json). A production restore drill remains deferred. Do not commit exports. Test restore in a separate database before treating it as disaster recovery.
- **Learning progress:** `uv run python -m tooling.learner_export` writes idempotent `INSERT OR IGNORE` SQL for attempts/flags to ignored private storage. Apply it only to the dedicated BirdAhead D1. Profiles are seeded by migration; active local sessions are intentionally not resumed.
- **R2:** catalogs are versioned; media keys are immutable. Keep a private backup of source media/manifests outside the repository. Do not enable public R2 access.
- **Worker:** retain prior Worker versions and roll back through the Cloudflare Workers dashboard/API after operator authorization. A Worker rollback does not undo D1 or R2 changes.
- **Content rollback:** activate a previous release id through the publisher/Worker admin endpoint. The same-release rollback pointer was exercised successfully; a future distinct release will exercise a true version switch. No application redeploy is required.

## Deployment gate and checks

GitHub Actions uses repository secret names `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` and variable `CLOUDFLARE_DEPLOY_ENABLED`; app-specific secrets are `BIRDAHEAD_HANK_KEY`, `BIRDAHEAD_HEATHER_KEY` and `BIRDAHEAD_PUBLISH_TOKEN`. The manual `provision=true` dispatch is the authorized first-release path and also carries later authorized code-only releases without touching content catalogs. Set `CLOUDFLARE_DEPLOY_ENABLED=true` only after a verified release to enable push-to-main deployment.

```sh
uv run python -m unittest discover -s tests
npm test --prefix app
npm run build --prefix app
uv run python -m tooling.production_smoke --base https://birdahead.com --resolve-ip <edge-ip> --browser
uv run python tooling/repo_check.py
```

The production smoke checks HTTPS health/revision, unauthorized private API/media/admin rejection, CSRF/origin rejection, both household logins and independent identities, actual seasonal curriculum, authenticated photo/audio ranges, PWA assets and mobile browser rendering. A separate public smoke checks anonymous exploration, public field-guide media, guest practice, SEO pages, robots/sitemap and private endpoint rejection. It never prints credentials or records private media.

## Analytics and Search Console

BirdAhead is registered in the existing CFLab analytics Site model as `as_Bq4kGnf2EkSW3dS0HZAddF` with apex/`www` domains. Aggregate public pageviews and feature events are verified; the client honors DNT/GPC, stores no cookies or persistent visitor ID, and never receives household identities, access keys, individual quiz responses, precise locations or private progress. See [analytics](analytics.md).

Google Search Console registration is now integrated with the existing CFLab collector. The reviewed property list includes `sc-domain:birdahead.com` mapped to the `birdahead` Site; the Analytics Worker passed all 10 read-only production checks at CFLab revision `ea30561` (mapping commit `2a6d74c`). The collector stored 120 daily totals with zero search traffic so far, confirming real read access to the new property. Sitemap submission still requires an account with Full/Owner permission; the collector itself only needs read access. See [Search Console](search-console.md) and [GSC evidence](../experiments/phase-three-gsc.json).

## Backup evidence

A private production D1 export was taken on November 16, 2026, with Time Travel bookmark `00000006-00000000-00005125-3b796d5251939d4f3e4b4b64ef4a0595`. The SQL export, digest and private path are recorded in [backup evidence](../experiments/phase-three-backup.json) and remain ignored private storage. A production restore drill was not performed.

## Known limitations and next improvements

- The Edge IP `--resolve-ip` is a local resolver workaround used because this workstation temporarily did not resolve the apex; normal clients use DNS. The public site remains hosted privately on R2 behind the Worker; no R2 public domain exists.
- The production D1 backup has no automated schedule or verified restore drill. The deployment token is likely account-scoped; least-privilege rotation remains an owner action ([evaluation](../experiments/phase-three-token-evaluation.json)). Sitemap submission and the eBird derived-product notification are also owner actions.
- Selective offline learning packs and profile-bound offline sync are included, and Road Trip mode is delivered. Phase Seven deployed revision `6ee6d122e44445f138a2045e7083c4937758b7a4` with the 333-species annual discovery explorer; public/private smoke passed 28/28 and 23/23. Phase Six deployed revision `a8ed0dc9ef2cb78aa30c08c1653e9314f958e40f` with the public comparison explorer, Kokoro narration replacement and explicit legacy `.m4a` denial; public/private smoke passed 26/26 and 23/23. Future hands-free refinements, cloud sync across devices, additional regions or further media expansion are not included.
- Automated acceptance remains preliminary source/model corroboration; owner/expert audit and the Mallard/American Black Duck risk remain documented. The two-hour owner-review cap is unchanged.
