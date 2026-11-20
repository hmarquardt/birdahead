# Phase Eight continuation — approval evidence and delivery gate

November 20, 2026. **Blocked/unavailable: approval scope and regional source delivery.** The owner reports eBird approval. The actual approval and submitted project description were unavailable in the inspected local locations, so no service entitlement, date/geographic scope or public eligibility has been inferred. This is a continuation from `1d45aab` on `main` at `c542a48`, retaining all six subsequent commits. Fetch confirmed local and remote main agreed before this work.

## Approval scope

| Question | Established evidence | Remaining evidence |
| --- | --- | --- |
| EBD access and regional extracts | Owner reports approval; official documentation supports project requests/direct regional delivery | Actual approval, submitted intended use and delivery instructions |
| Matching Sampling Event Data | Official download guide offers checklist-level SED separately | Confirmation that the delivered pair shares release, scope and population |
| Dates and geography | Requested pilot is seven Indiana counties, all species/months, 2016–2025 | Approved dates/counties and whether complete Indiana is covered |
| Public noncommercial historical derivatives | General EBD terms permit derived distribution with the same terms, require dataset citation and restrict use to the requested purpose | Actual submitted public educational purpose, grant conditions and dataset-specific citation |
| S&T website/PWA and offline use | Separate 2023 terms require prior written consent for website/app data products and redistribution of modified products | Any specific written S&T consent; EBD approval does not establish it |
| Conditions and attribution | General terms require reading supporting metadata, acknowledgement and sending published products to Cornell | Grant-specific limits, metadata, citations, refresh/expiry and any additional obligations |

**Verified documentation, retrieved November 20:** [official download guide](https://support.ebird.org/en/support/solutions/articles/48000838205-download-ebird-data), [EBD terms, last updated November 9, 2020](https://www.birds.cornell.edu/home/ebird-data-access-terms-of-use/), and [S&T terms dated November 15, 2023, sections 2 and 3(d)](https://is-ebird-wordpress-prod-s3.s3.amazonaws.com/wp-content/uploads/sites/55/2021/07/eBird-Status-Trends-Terms-of-Use-2023-Updates_20231115_FINAL.pdf). The current S&T terms landing page was unavailable to the research browser; the older readable PDF is not proof that the owner's grant incorporates that version. General documentation cannot identify an account's actual approval. No authenticated portal was inspected or scraped, no endpoint guessed, and no message sent to Cornell.

The [approval handoff checklist](phase-eight-owner-request.md#approval-handoff--november-20-2026) specifies exactly what the owner must supply. Reuse the approved request and any existing delivery rather than resubmitting the historical request.

## Local inspection and resource measurements

**Observed experiment:** recursive filename/metadata inspection covered all 31 files under `experiments/private/geography/` and 4,721 files under Downloads. No relevant approval or regional EBD/SED pair was found. Documents returned a permission error before any files could be inspected; its contents remain **unavailable**, not confirmed absent. Project-cache inspection also found no source snapshot/acquisition plan. No eBird account session or unrelated private document was read. These searches cannot exclude an approval email, an unrecognized filename or another owner-chosen storage location.

The fresh [sanitized evidence](../experiments/phase-eight-continuation.json) records **132,869,361,664 bytes free (132.87 GB decimal)**, 16 GiB physical memory and eight logical CPUs. Existing ceilings remain 64 MB transfer/run, 500 MB combined expanded input, 20 GB free-disk reserve, DuckDB 2,048 MB/two threads and 4 GB spill. EBD/SED compressed/expanded sizes, expected processing time and peak memory remain unknown. Free disk alone does not authorize a transfer or establish that Indiana fits. No ceiling was increased.

No new bulk bytes were transferred. The six existing modeled raster/calendar hashes and seven raw histogram hashes were inventoried offline; no S&T data were fetched again. Approval documents and signed delivery instructions, when supplied, belong in ignored private storage. No reproducible EBD source manifest can be completed until the actual pair and release metadata exist; the existing snapshot template remains unfilled.

## Validation and publication candidate

**Observed experiment:** the existing validation module was run without a build and reported `blocked_source_unavailable`. All seven private reference profiles were independently inventoried and hashed: 48 native periods each, 2016–2025, 79,868 summed reference sample counts. Current teaching-reference projections contain 100 species per county; this is reference inventory, not measured statewide EBD species coverage.

| County | Code | Sum of reference sample counts |
| --- | --- | ---: |
| Gibson | US-IN-051 | 14,238 |
| Greene | US-IN-055 | 21,947 |
| Knox | US-IN-083 | 3,074 |
| Pike | US-IN-125 | 2,584 |
| Posey | US-IN-129 | 2,842 |
| Vanderburgh | US-IN-163 | 22,222 |
| Warrick | US-IN-173 | 12,961 |

Actual EBD/SED ingestion, DuckDB/Parquet aggregation, denominator comparisons and subsequent frequency comparisons **could not run**. Discrepancies are unmeasured, rather than zero. Synthetic integration checks do not establish reference parity. Once delivery is available, use the [existing runbook](phase-eight.md#operations-and-rollout): pilot build first, denominator-first validation across all seven counties, investigate mismatches, then configure Indiana only if the source covers it. Retain taxonomy holds, native calendars, sample support and explicit parent fallback. Discovery remains independent of teaching/media, and modeled estimates remain a separate signal.

| Publication gate | Current result |
| --- | --- |
| New historical geographic/species coverage | None generated; Indiana coverage and species count unmeasured |
| Real-source validation | Unavailable; seven references intact, no parity claim |
| Dataset size and processing cost | No EBD/SED acquired, normalized or published; size/time/memory unavailable; no paid services used |
| Public-use permission | Actual historical grant scope unverified; S&T written web/app consent unavailable |
| Validated publication candidate | Unavailable; no build, validation acceptance or eligible package |
| Indiana ready for release authorization | **No**; approval/delivery, measured validation and public eligibility remain blockers |

**Observed local verification:** 87 Python tests, 28 application tests and the TypeScript/Vite production build passed. The build reported two existing CSS minifier warnings about unexpected `@media`; no styles were changed in this continuation. These checks exercise ingestion/aggregation fixtures and existing public, private-progress, offline and Road Trip behavior; they are not real-source validation or a physical-device test. Runtime code, learner data, accepted media and active catalog were not changed. The GitHub repository variable `CLOUDFLARE_DEPLOY_ENABLED` was observed `false` before and after the handoff; no deployment, publication, workflow dispatch, resource change, rollback, backup change or token-scope change was performed.

Reproduce the offline status and compatibility checks without source downloads:

```sh
uv run python -m tooling.geographic_validation --output experiments/private/geography/continuation-validation.json
uv run python -c 'import json; from tooling.geographic_sources import preflight; print(json.dumps(preflight(), indent=2))'
uv run python -m unittest discover -s tests
npm test --prefix app
npm run build --prefix app
gh variable get CLOUDFLARE_DEPLOY_ENABLED --repo hmarquardt/birdahead
```
