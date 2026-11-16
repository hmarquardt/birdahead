# Comparative learning

The comparison explorer is public and mobile-first. It is reachable from the
main **Compare** tab, from a field-guide species card with a reviewed confusion
pair, and from an incorrect/revealed practice answer. Deep links use
`/?tab=compare&a=<code>&b=<code>`.

## What is shown

- Side-by-side accepted public photographs. Media still flows through the
  Worker's public eligibility gate; no private R2 path is exposed.
- Independently playable accepted recordings with creator, source and license.
- Cited reference summaries for relative size, shape, plumage, behavior,
  habitat and vocalizations. These are original concise summaries, not copied
  prose or illustrations, from the sources recorded in
  `app/public/comparisons.json`.
- Seasonal overlap for the selected county, calculated from the same 48
  historical bins used elsewhere. Current values remain **historical
  complete-checklist reporting frequency**, not encounter probability.
- Visible evidence gaps when either side lacks an accepted photo/recording or a
  trait is not supported. No acceptance threshold is lowered to fill a gap.

The catalog has `review_status: provisional_curated`. It is not a claim of
expert field verification, and it does not promote source annotations for age,
sex or plumage into verified facts. Human owner/expert review remains
outstanding for the cited summaries.

## Catalog and future additions

`app/public/comparisons.json` is versioned with a schema
(`birdahead-comparison-catalog-v1`), source IDs/URLs, pair IDs and explicit
gaps. Validate it against the accepted release with:

```sh
uv run python tooling/validate_comparison_catalog.py
```

Add or correct a pair by updating the JSON, adding source citations, and running
the validator. Automated discovery can propose candidates, but pairs should not
be published until source evidence and review status are recorded. The four
current pairs are the accepted release's reviewed confusion pairs.

## Comparative practice

Comparative practice is separate from scored identification and passive
listening. It:

- selects a different accepted example when one remains unseen in local
  comparative history;
- offers only the two reviewed species as choices;
- writes to the separate browser-local `comparative` IndexedDB store with the
  guest/profile identity;
- displays a result but never grants mastery, creates a scored `attempts` row,
  or feeds listening minutes.

Recommendations use authenticated progress confusion counts and local
comparative history when available; otherwise they fall back to catalog
priority. Anonymous and household learners both use their own local store.

## Offline behavior

`/comparisons.json` is part of the app shell cache. Downloaded accepted media
and narration remain in the separate pack cache, so a comparison can render its
catalog and any already-downloaded media offline. Missing downloaded assets
remain explicit gaps rather than silently substituting another bird.

## Boundaries

No new media acquisition, no paid inference, no age/sex/plumage inference and
no public R2 access were introduced. CFLab, Search Console and the existing
public analytics collector are unchanged by this feature.
