# Changelog

All notable changes to ODGG will be documented in this file.

## [0.1.3.1] - 2026-03-30

### Changed
- Design principle #1 in `.impeccable.md` now documents the Brief Editor exception: "document is king" instead of "canvas is king" when in the brief editing view

## [0.1.3.0] - 2026-03-30

### Added
- You can now export any modeling brief as a polished Markdown document for stakeholder review via `GET /briefs/{id}/export`
- Export includes title, database metadata, typed section headers (Business Process, Grain, Dimensions, Measures, etc.), and ODGG footer
- 8 tests covering export endpoint: content-type, title, metadata, all section types, empty brief, 404

### Fixed
- Removed unused `title` variable in SSE cascade drafting code path

## [0.1.2.0] - 2026-03-29

### Added
- You can now measure prompt quality for all 4 Kimball modeling steps against TPC-H ground truth
- 9 structural tests (mock-based, always run) validate response shape and scoring logic
- 5 live LLM evals gated behind `--run-llm` pytest flag, including a full pipeline cascade test
- `llm` pytest marker and `--run-llm` conftest hook make it easy to separate fast CI from slow evals

## [0.1.1.0] - 2026-03-28

### Added
- Table selection UI for large schemas (500+ tables) with search, select all/none
- Auto-select first 50 tables when schema exceeds threshold, hidden for small schemas
- Server-side table filtering in `_build_metadata_context` via `selected_tables` parameter
- `selected_tables` field on Brief model (persisted as JSON)
- Input validation: `selected_tables` list capped at 500 entries

### Fixed
- Server-side enforcement of MAX_TABLES_FOR_LLM (50) prevents token overflow regardless of selection
- Prompt injection fallback now respects table selection filter instead of leaking all table names

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
