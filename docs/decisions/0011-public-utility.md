# ADR 0011 — public educational utility with private personalization

Date: 2026-11-16. Status: accepted by the Phase 3.1 request.

Personal use does not imply private-only access. BirdAhead is a free, noncommercial educational resource; general exploration, field-guide content, public media and guest practice should not require authentication. Authentication is reserved for personal data, persistent progress, household curriculum, publishing and administration.

Public delivery is a separate eligibility decision from biological acceptance. The existing per-asset licenses permit public noncommercial sharing for CC0/CC BY/CC BY-SA/CC BY-NC/CC BY-NC-SA, with attribution and share-alike/noncommercial notices. R2 stays private and the Worker enforces the public catalog. eBird-derived seasonal summaries remain under the eBird Data Access Terms; raw histograms stay private and a notification is prepared for owner review.

Guest history is browser-local. Household profiles remain independent and server-backed. Analytics is aggregate and privacy-preserving via the existing CFLab collector; Google Search Console reuses the existing service account through the reviewed CFLab property mapping, while sitemap submission remains an owner action.

Consequences: public pages and anonymized media become indexable and cacheable; private endpoints remain noindex/no-store and authenticated; the public/private boundary must be tested whenever a catalog or endpoint changes.
