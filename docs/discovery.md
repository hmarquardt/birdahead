# Annual discovery explorer

## Separation from learning

`/discovery.json` is a public derived-product catalog of **333 uniquely
reconciled species** from the seven existing county histogram exports. It is
separate from the **100-species teaching/media universe** in the release:

- Every discovery species has 48 native annual frequency bins for each of the
  seven counties, with nulls retained where the source has missing or
  unsupported values.
- `teaching` and `media` are flags, not filters. A species can be fully visible
  in discovery with no accepted field-guide media or practice coverage.
- No photographs, recordings or other media were acquired for discovery.
- Field-guide media is reused only where the existing release has an accepted
  public asset. Practice-ready means the existing accepted media meets the
  practice threshold.

The generated page summary is `app/public/discovery-page.json`; the interactive
catalog is `app/public/discovery.json`.

## Explorer

The **Migration** tab provides:

- a species-by-48-bin heatmap with missing/unsupported cells visually distinct
  from observed zero reporting;
- individual frequency charts and a date/period slider;
- seasonal peak bins, within-year reporting rises/falls, active-bin coverage,
  annual pattern classification and missing-support counts;
- seasonal richness for a county and the combined region;
- side-by-side county comparison and sample-weighted all-county summaries;
- search, pattern filter, media-only filter, sort and a learning selection;
- links to field-guide entries, comparison views and practice where accepted
  media exists;
- discovery selections that can create a practice session, a focused offline
  pack or a Road Trip audio session.

The public crawlable summary is `/migration`; it is included in the sitemap and
links to substantive `/birds/:code` pages.

## Calculation contract

- **Frequency** is the historical fraction of complete checklists reporting the
  species in a native bin. It is not abundance, encounter probability,
  detection probability or a recent sighting.
- **Regional frequency** is
  `sum(county frequency × county-bin sample size) / sum(sample size)` over
  counties with a supported numeric value. It is **not** an unweighted average
  of county percentages.
- **Support** is the sum of county-bin checklist samples. It is not a count of
  independent birding events or observers.
- **Null** means missing/unsupported, not zero or absence. Zero with positive
  support remains an observed zero-reporting bin.
- **Bins** are the existing 48 native eBird periods: days 1–7, 8–14, 15–21 and
  22–month-end. They are not ISO weeks or synthetic months.
- **Classification** is descriptive:
  - `insufficient`: fewer than 8 observed bins or fewer than 2 active bins;
  - `year_round`: at least 40 observed bins, at least 80% of bins active and minimum active frequency at
    least 0.05;
  - `strongly_seasonal`: at most 50% of bins active or maximum/minimum active
    ratio at least 4;
  - `seasonal`: otherwise.
  Missing bins are ignored, not counted as zero.
- **Rises/falls** are adjacent within-year reporting changes. The 2016–2025
  profiles are aggregated by calendar bin; they do not establish year-over-year
  population trends or individual arrival/departure dates.

## Integrity and limits

- The 100 teaching-species profiles are checked for exact equality with the
  imported release profiles.
- The catalog validator checks species/county/bin dimensions, null preservation,
  calendar boundaries and selected-profile parity.
- Source taxonomy release remains unknown; unresolved names and ambiguous
  split/lump concepts remain excluded (81 unresolved source names).
- The catalog is a public derived-product export; raw county files and precise
  observation records remain private.
- Owner/expert biological review of discovery classifications is not claimed.

## Commands

```sh
uv run python -m tooling.discovery_catalog
uv run python tooling/validate_comparison_catalog.py
uv run python -m unittest discover -s tests
npm test --prefix app
npm run build --prefix app
```
