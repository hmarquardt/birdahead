# Local curation workbench

This is internal local tooling, not the BirdAhead learning app. It binds only to loopback and does not deploy or upload anything.

```sh
uv sync --locked
uv run python -m tooling.workbench.server
```

Open http://127.0.0.1:8765. Candidate media and source captures live under ignored `experiments/private/phase05/`. A fresh clone contains tools and aggregate reports, not private media; acquisition must be run lawfully or existing captures supplied locally.

## Reviewing a sample

Filter by modality, species and sampled-audit/accepted/held status. View original images or play real recordings; inspect source links, source identification support, credit/license evidence, technical metrics and versioned model results. A yellow target box, when available, identifies the source-consistent subject established by the localization screen; original pixels are not modified. Missing localization is a real acceptance gap.

Enter a reviewer name and role, select a candidate and start its timer. Decide separately on **biological identification** and **rights/attribution**, or reject/quarantine/defer the whole asset. Record diagnostic/reference evidence for an approval and reasons for other outcomes. Finish/defer the session before leaving; the timer conservatively counts elapsed wall time. Only one session is active at once; reloading the page resumes its persistent timer. Expert status is self-declared and stored with reviewer evidence; it is not an external credential or certification.

There is no requirement to inspect every accepted asset. Automated decisions are distinct from human/expert decisions. Prefer stronger replacements for uncertain cases. The server enforces a total 7,200-second owner-review budget for the initial regional collection; it blocks further approvals after the cap but permits deferral/quarantine.

## Persistence and export

Review state resides in `experiments/private/phase05/reviews.sqlite`. Events are append-only with a hash chain. Approval evidence binds to media checksum, taxon and rights context, preventing old approvals from silently carrying to changed media/licenses. Re-running acquisition/inference does not erase review events or rejection/quarantine decisions.

“Export accepted manifest” writes `experiments/private/phase05/approved-media.json`. It includes only records passing both gates and excludes rejected, quarantined and deferred examples. Export verifies media hashes and audit integrity. Identical inputs yield identical manifest bytes and digest; timestamps in existing evidence are retained, but exporting does not add a new clock-dependent field.

The manifest keeps source/rights evidence, canonical/source taxonomy, model revisions/checkpoint digests, inference results, threshold digest, acceptance rationale, technical/duplicate flags and human/expert audit events. Keep it and its media private unless every included source permits the intended redistribution. No browser route returns source API credentials.

## Local security and validation

The server accepts state-changing JSON requests only from its own loopback origin, validates media paths against private project storage and supports audio range requests. Source strings are displayed as text; HTML-bearing source credit is never trusted markup. Requests/bodies/credentials are not logged. This is intended for one owner's local computer, not network exposure.

Run the offline policy, parser and review-store checks with:

```sh
uv run python -m unittest discover -s tests
```

The browser smoke check uses a separate fixture database, so simulated test actions do not count as actual owner review. Desktop/mobile rendering, image decode and audio metadata loading were checked in Chrome. A browser/UI test is not a biological audit or a human-throughput measurement.
