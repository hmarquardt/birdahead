# Phase Seven delivery

## Discovery is separate from teaching

The public **Migration** tab and `/migration` page expose 333 uniquely
reconciled species from the seven existing county histogram exports. This is a
derived-data catalog, not an expansion of the 100-species teaching/media
universe. Every species retains its 48 native annual bins and seven county
series; the teaching, field-guide media and practice-ready flags are displayed
separately.

No media was acquired for discovery. Of the 333 species, 100 have a field-guide
entry and 93 have enough accepted media for practice. The remaining records are
still usable for annual occurrence exploration.

## Explorer behavior

- Heatmaps, individual seasonal charts, a period slider, peak periods,
  within-year reporting rises/falls, active/missing bins, richness and
  year-round/seasonal/support classifications.
- Search, pattern filtering, sorting, media-only filtering and a selectable
  learning set.
- Side-by-side county comparison and a seven-county series calculated with
  checklist-sample weighting.
- Direct links to field-guide, comparison, practice, focused offline pack and
  Road Trip actions where accepted media exists.

Every view labels reporting frequency as historical complete-checklist
reporting. Missing/unsupported cells are not zero, and the aggregated annual
profile is not treated as a population trend or confirmed arrival/departure.

## Validation

`tooling/discovery_catalog.py` generates the catalog and checks dimensions,
calendar boundaries, null preservation and exact parity for all 100 teaching
profiles against the imported release. `tests/test_discovery_catalog.py` also
recomputes a sample-weighted regional value independently. Evidence is in
[`experiments/phase-seven-discovery.json`](../experiments/phase-seven-discovery.json).

Physical-device and owner/expert review remain outstanding. No additional
county downloads, EBD/SED data, paid infrastructure or geographic expansion was
introduced.
