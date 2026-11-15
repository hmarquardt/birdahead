# ADR 0008 — Deliver the learner locally while bulk access is investigated

Date: November 15, 2026. Status: implemented within the owner's Phase One authorization.

Use the seven supplied annual references and existing accepted-media collection to deliver useful local learning now. Geographic bulk delivery is an independent research track, not another application gate. Keep the full 25-species benchmark but require multiple accepted examples per species/modality for practice. Do not acquire weak media or relax rights/biological gates to force coverage.

Implement React/TypeScript/Vite with a Hono API using the Node adapter and local SQLite. This provides the preferred UI/API framework without creating cloud infrastructure. A Python builder verifies the curation export and compiles a private, hash-identified content release. Acquisition, inference, original media, model artifacts and credentials remain outside runtime/bundles. Source APIs are not contacted during learning. Future Workers/D1/R2 migration will replace the local storage adapter; this decision does not imply that migration is already implemented.

Bound sessions, retain independent learner state, recognition/recall and modality, record directed confusions and uncertain answers, and avoid mastery certification. Flags preserve asset/release/session context, suppress disputed media for both learners and exclude affected practice; no source identification is changed merely because a report was filed. Workbench triage, per-interval flags and versioned corrections remain subsequent work.

The server binds to loopback and enforces local Host/same-origin writes, bounded JSON, content checksums and private media paths. There is no authentication, cloud sync, phone hosting or complete offline pack. API/browser tests use isolated databases; no owner learning or review is fabricated. [Local operation and verification](../local-mvp.md), [current findings](../phase-one.md).
