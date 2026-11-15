# ADR 0003 — Preserve independent seasonal signals

Date: 2026-11-15. Status: proposed.

Store historical checklist reporting frequency, modeled occurrence, modeled relative abundance, recent presence and aggregate migration activity as distinct metrics with geography, native dates/bins, source release, support and uncertainty. Do not flatten them into a purported encounter probability.

Use periodic weekly modeling and two-to-four-week forward comparisons for curriculum relevance. Keep source-native histogram bins until inspected; a bar chart with 48 subdivisions cannot be treated as 52 ISO weeks. Sparse locations fall back to a documented parent region, with the change in geography visible.

Consequence: seasonality is foundational, but unavailable annual data blocks claims of a validated seasonal curriculum. Recent API presence alone is inadequate.
