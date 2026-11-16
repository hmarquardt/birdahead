# BirdAhead production operations

Status: private household production release, November 15, 2026. Canonical URL: **https://birdahead.com**. `www.birdahead.com` redirects with HTTP 308. Production is intentionally private, noncommercial and authenticated.

## Resource inventory

| Resource | Name / identity | Purpose |
| --- | --- | --- |
| Cloudflare Worker | `birdahead` | Hono API, session auth, authenticated media, static SPA |
| Worker version | recorded in [production evidence](../experiments/phase-three-inventory.json) | exact live revision/version |
| D1 | `birdahead` (`ce2302c9-988b-490c-9ad3-3035d0a57c8b`) | profiles, sessions, attempts, flags, release pointer |
| Private R2 | `birdahead-private` | 589 delivery media objects + versioned catalogs; public access/r2.dev disabled |
| Zone | `birdahead.com` (`03524416f9bc90b22119b587716866ef`) | apex and `www` custom domains, HTTPS |
| GitHub Actions | `ci.yml`, `deploy.yml` | validation; manually gated production provisioning/release |

No unrelated Worker, D1, R2 bucket, DNS record, shared service or billing plan was modified. No paid subscription or domain purchase was made.

## Authentication

Two household learner identities, **Hank** and **Heather**, authenticate with independently generated 256-bit access keys. The keys are held only in:

- the owner-only local file `~/.config/secrets/birdahead.env` (mode 0600), never printed or committed;
- Cloudflare Worker secrets `HANK_KEY` and `HEATHER_KEY`;
- GitHub Actions secrets `BIRDAHEAD_HANK_KEY` and `BIRDAHEAD_HEATHER_KEY` for release provisioning.

There is no registration, email recovery, password reset, public identity provider or default credential. Sign in selects the household learner and posts the key over HTTPS. The Worker stores only SHA-256 hashes of opaque 256-bit session tokens. Cookies are host-only `__Host-birdahead-session`, `HttpOnly`, `Secure`, `SameSite=Strict`, with a 30-day lifetime. Mutations require same-origin `Origin`/`Sec-Fetch-Site` checks and the custom `X-BirdAhead-Request` header. Login is rate-limited (10 attempts/minute/IP) and publish endpoints separately rate-limited.

To rotate a key: replace the relevant GitHub secret and the local private file, rerun the gated deployment (or update the Worker secret), and retain the new key in the owner password manager. Rotating either key does not delete learning history; existing sessions remain until expiry unless sessions are cleared.

## Publishing and content releases

The local publisher sends accepted bytes only to the authenticated Worker, which writes them to private R2 through its binding. No R2 credential is exposed locally or in the browser. The local ledger is ignored private state.

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

- **D1:** use Cloudflare D1 Time Travel plus a private export (`npx wrangler d1 export DB --remote --config <generated-config> --output <private-file>`). The export command was exercised against the local D1; a production export/restore drill remains deferred. Do not commit exports. Test restore in a separate database before treating it as disaster recovery.
- **Learning progress:** `uv run python -m tooling.learner_export` writes idempotent `INSERT OR IGNORE` SQL for attempts/flags to ignored private storage. Apply it only to the dedicated BirdAhead D1. Profiles are seeded by migration; active local sessions are intentionally not resumed.
- **R2:** catalogs are versioned; media keys are immutable. Keep a private backup of source media/manifests outside the repository. Do not enable public R2 access.
- **Worker:** retain prior Worker versions and roll back through the Cloudflare Workers dashboard/API after operator authorization. A Worker rollback does not undo D1 or R2 changes.
- **Content rollback:** activate a previous release id through the publisher/Worker admin endpoint. The same-release rollback pointer was exercised successfully; a future distinct release will exercise a true version switch. No application redeploy is required.

## Deployment gate and checks

GitHub Actions uses repository secret names `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` and variable `CLOUDFLARE_DEPLOY_ENABLED`; app-specific secrets are `BIRDAHEAD_HANK_KEY`, `BIRDAHEAD_HEATHER_KEY` and `BIRDAHEAD_PUBLISH_TOKEN`. The manual `provision=true` dispatch is the authorized first-release path. Set `CLOUDFLARE_DEPLOY_ENABLED=true` only after a verified release to enable push-to-main deployment.

```sh
uv run python -m unittest discover -s tests
npm test --prefix app
npm run build --prefix app
uv run python -m tooling.production_smoke --base https://birdahead.com --resolve-ip <edge-ip> --browser
uv run python tooling/repo_check.py
```

The smoke test checks HTTPS health/revision, unauthorized API/media rejection, CSRF/origin rejection, both household logins and independent identities, actual seasonal curriculum, authenticated photo bytes/ranges, PWA manifest/service worker and mobile browser image rendering. It never prints credentials or records private media.

## Known limitations and next improvements

- The Edge IP `--resolve-ip` is a local resolver workaround used because this workstation temporarily did not resolve the apex; normal clients use DNS.
- No scheduled D1 export, verified restore drill, R2 lifecycle/versioning policy or least-privilege token rotation has been executed. The repository token may be account-scoped; narrow it after operational validation.
- No offline media packs, hands-free road-trip mode, cloud sync across devices, additional regions or further media expansion are included.
- Automated acceptance remains preliminary source/model corroboration; owner/expert audit and the Mallard/American Black Duck risk remain documented. The two-hour owner-review cap is unchanged.
