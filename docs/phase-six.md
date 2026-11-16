# Phase Six delivery

## Narration remediation

Apple-generated Road Trip narration was removed from current delivery and
replaced with locally generated Kokoro-82M WAV files. The current version is
`kokoro-82m-af_heart-v1`; model/voice provenance, checksums and generation
commands are recorded in [narration remediation](narration-remediation.md) and
the public manifest. Old downloaded Phase Five packs are marked stale and their
legacy `.m4a` cache entries are removed; the shell cache advanced to v3. The Worker also explicitly denies legacy `/narration/*.m4a` paths because Cloudflare static storage can retain old immutable files.

The historical Git commit `4597eca` still contains the Apple files. It was not
rewritten without owner authorization; the exposure and coordinated rewrite
option are documented.

## Comparison explorer

The public **Compare** tab implements four reviewed confusion pairs from the
accepted release. It provides side-by-side accepted media, independent audio,
cited relative size/shape/plumage/behavior/habitat/call summaries, county
seasonal overlap, current historical reporting frequencies, attribution and
explicit media/evidence gaps. The catalog is versioned and provisional-curated;
it does not promote source annotations or infer age/sex/plumage labels.

Deep links use `/?tab=compare&a=<code>&b=<code>`. Links are available from the
field guide, `/birds/:code` pages and revealed/incorrect practice feedback.

## Adaptive comparative practice

Comparative practice is browser-local and profile-bound for signed-in
households, or guest-local for anonymous learners. It selects an unused accepted
example where possible, offers only the reviewed pair, and writes to a separate
`comparative` IndexedDB store. It creates no scored attempt, no mastery credit
and no listening record. Recommendations use existing confusion history and
local practice history.

## Verification

Local automated checks, catalog validation, TypeScript build, Wrangler dry run
and headless mobile comparison checks are recorded in
[`experiments/phase-six-comparison.json`](../experiments/phase-six-comparison.json).
Production `6b31cd6` passed the public and private smoke suites (26/26 and 23/23), the legacy `.m4a` URL returns `404`, and the deployed comparison UI passed a mobile-viewport browser check. Physical device/Bluetooth and owner/expert biological review remain outstanding.
