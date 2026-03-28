# Changelog

All notable changes to ODGG will be documented in this file.

## [0.1.0.0] - 2026-03-28

### Added
- Modeling Brief Editor: document-style interface for dimensional modeling with AI-assisted drafting
- Brief CRUD API with SQLite persistence (create, list, get, update, delete)
- SSE cascade drafting: 2-stage AI pipeline (BP → Grain → Dimensions + Measures in parallel)
- Protocol-based ModelSource bridge enabling code generation from brief sections
- Brief Editor frontend: section cards, sidebar navigation, shimmer loading, dark mode
- Brief list page with card-based overview (status, DB name, section count)
- Database connection dialog with metadata snapshot storage per brief
- Code generation from briefs: DDL, ETL, dbt models, and data dictionary
- Markdown content parsing for dimensions and measures extraction

### Changed
- Decoupled modeling_engine from SessionState to accept plain arguments via ModelSource protocol
- Database pool configuration: increased pool_size to 5 with max_overflow=2 for SSE concurrency

### Fixed
- SSE draft endpoint supports GET (required for EventSource) with duplicate section prevention
- SQLite pool exhaustion during concurrent SSE streams
- Dimension/measure parsing from markdown-formatted AI content
- Redacted LLM error details from client-visible responses
- Fixed mutable default argument in draft section content function
- Improved metadata snapshot guard for empty dict edge case
