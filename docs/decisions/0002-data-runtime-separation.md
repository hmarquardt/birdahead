# ADR 0002 — Keep acquisition separate from runtime

Date: 2026-11-15. Status: proposed.

Use Python/uv source adapters and private portable captures for acquisition. Review media before building immutable releases. Proposed runtime is React/Vite plus Hono/Workers, D1 metadata/progress and R2 media with permitted rights. Learning sessions read only approved versioned data and assets.

This limits runtime API failures, protects credentials, supports offline use and permits source replacement. Start with local SQLite/JSON; avoid ingestion services or a production deployment before dataset validation. A Postgres service or native mobile application may be reconsidered if measured requirements justify added overhead.

Consequence: licensing needs to permit storage/delivery/offline derivatives. Embed-only Cornell media cannot silently become an offline pack.
