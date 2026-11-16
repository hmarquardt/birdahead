# ADR 0007 — Configuration-driven geographic profiles

Date: November 15, 2026. Status: accepted direction under the owner's Phase One amendment; bulk delivery and measured processing remain proposed/unverified.

**Phase Eight update (November 16, 2026):** the configuration-driven local processing and selective publication path are implemented, including a real bounded coarse S&T experiment. Historical EBD source access/validation and public S&T web/app consent remain gates. [Measured report](../phase-eight.md).

## Decision

The seven owner-supplied 2016–2025 county histograms are bootstrap inputs and validation references. They are not a recurring acquisition workflow. Continue the local MVP with these data while building an independent path to automated profiles from regional EBD **plus matching Sampling Event Data**. Use Python/uv, DuckDB and private partitioned Parquet; compile small, versioned runtime summaries. Configure counties, hotspot IDs and supported polygons rather than adding per-location manual downloads.

Maintain three separate signal families: historical complete-checklist reporting frequency with numerator/denominator, standardized Status and Trends modeled occurrence/abundance, and recent API v2 presence. Preserve native calendars, missingness, sample support, taxonomy/crosswalk versions, geography and source provenance. Frequency is not an absolute encounter probability.

## Evidence and consequences

Two bounded authenticated official S&T list requests succeeded with `EBIRD_ST_API_KEY`; no raster was downloaded. EBD approval, current archive sizes, a supported unattended refresh route and EBD/reference parity remain unverified. Official references document regional request/download workflows, not a general public EBD download API. Do not scrape the portal or invent that API. Request one coherent regional snapshot and clarify supported recurring delivery. Cached historical data with explicit vintage is acceptable for local use while that is resolved; repetitive county downloads are rejected.

Proper historical denominators come from the eligible SED population, including complete lists that did not report the target species. Shared event deduplication, taxonomic rollup, effort selection and geography must be consistent between detections and denominator. Bulk originals, exact locations, authenticated responses, model cubes and spills stay private/ignored. No cloud deployment, paid infrastructure or large acquisition is introduced by this decision.

See [architecture, operational constraints, validation plan and primary references](../geographic-acquisition.md), [safe access evidence](../../experiments/geographic-access.json). The local MVP's delivery is explicitly independent of resolving long-term bulk access.
