# LedgerLens project status

Last updated: 2026-09-04

## Current phase

**Following the nine-phase build plan in strict order (see "Active build plan" in `plan.md`). Phases 1–7 are complete — Phase 7 was already satisfied (import-direction test, per-scenario engine tests, and empty/error/loading states all existed before this note) rather than genuinely outstanding. Phase 8 is in progress: Money Graph and Audit Log are shipped; Connections and Rule Studio remain, next in order. Phase 9 submission prep follows.**

## Shipped

- React/TypeScript/Vite prototype with shadcn-compatible components.
- Landing page with CRTWarp background, product narrative, and responsive navigation.
- Interactive investigation preview showing order, gateway, settlement, bank credit, and ledger checkpoints.
- Reconciliation dashboard with summary metrics, money movement view, and exception table.
- Case investigation view with deterministic checks, cited evidence, confidence, and AI-investigator placeholder interaction.
- Responsive desktop/mobile styling and accessibility basics (semantic landmarks, labels, keyboard-focusable controls, reduced-motion fallback).
- Evidence-trail visual pass: full-viewport hero, restrained trace canvas, clear first-break treatment.
- GitHub main branch kept current through small commits.
- Django backend scaffold with a health endpoint and admin registration.
- Canonical `Organization`, `FinancialDataSource`, `FinancialRecord`, `ReconciliationCase`, and `EvidenceConnection` models.
- Backend model and health-endpoint tests plus frontend/backend GitHub Actions checks.
- Idempotent `seed_demo_cases` command with six distinct scenarios and 216 records.
- Deterministic fee, tax, refund, settlement, bank-credit, and missing-evidence checks using integer paise.
- Persisted evidence connections with matching method, confidence, rationale, and non-AI authorship.
- DRF endpoints for cases, records, evidence graphs, assignment, investigator runs, and overview metrics.
- Optional Anthropic four-turn tool loop with structured-output and citation validation.
- No-key deterministic investigator fallback, including the explicit insufficient-evidence outcome.
- React dashboard and case pages connected to the Django API; no hardcoded case dataset remains.
- Clickable source-evidence drawer, persisted assignment, functional ask form, history, loading, empty, and error states.
- Money Graph page: renders `/api/cases/<id>/evidence-graph/` as an SVG node-edge diagram per case, reachable from the sidebar and from a case-detail link. Solid edges mark exact-reference matches; dashed edges mark sub-1.0-confidence fuzzy matches. Clicking a node opens the same evidence drawer used on case detail.
- Audit Log page and `/api/audit-log/` endpoint: synthesizes a single chronological feed from existing `AgentRun` and `EvidenceConnection` rows across all cases — no new model or migration. Filterable by "Investigator runs" / "Evidence links"; each entry links back to its case.

## Not yet implemented

- Production PostgreSQL configuration and database deployment.
- Real source adapters, webhooks, bank statement import, and accounting exports.
- Live source adapters, webhook endpoints, bank CSV/XLSX import, and accounting exports.
- Full one-to-many batched-settlement and ambiguous-match resolution beyond the seeded graph.
- Prompt version records, provider cost accounting, retry policy, and a model evaluation corpus.
- Authentication, RBAC, encryption, retention, audit persistence, and production observability.
- Cross-case AI Investigator, Connections, and Rule Studio pages (Money Graph and Audit Log are done; these three remain inert by design, labeled "planned").
- A persisted case-status-change event log — Audit Log currently derives its feed from `AgentRun` and `EvidenceConnection` timestamps only, not discrete status-transition events (case.status is visible on the case page itself; adding a dedicated activity model was deferred as unnecessary for now).
- Batched settlements (open decision D4 — many payments to one settlement) — the matcher currently only produces 1:1 sequential chains per case.
- Import-direction test (`engine` must not import `agent`) and expanded per-scenario engine test coverage (Phase 7).
- README, architecture diagram, demo recording, and concept-doc trim (Phase 9).

## Next milestone: finish Phase 8 in order, then Phase 9

Working strictly in plan order — nothing below is started until everything above it is done.

1. ~~Render `/api/cases/<id>/evidence-graph/` as the Money Graph page.~~ Done (Phase 8).
2. ~~Add an Audit Log page over `AgentRun` and evidence-connection data.~~ Done (Phase 8).
3. Add a Connections page: source systems with health status, read from `FinancialDataSource` + last `FinancialRecord.ingested_at` (Phase 8, next).
4. Add a read-only Rule Studio page listing the engine's checks and formulas (Phase 8).
5. Write the README, architecture diagram, and demo recording; trim the concept doc (Phase 9).
6. Add authentication, organization scoping, request limits, and production-safe error reporting (post-submission hardening — not required for the funnel submission).
7. Add a real adapter contract plus one bank CSV import path (post-submission).
8. Add batched-settlement matching per open decision D4 (post-submission, unless reprioritized).

## Definition of done for the MVP

- A user can import or connect at least two source systems.
- One transaction trace is reproducible from raw records.
- Every mismatch has a first-break reason and cited evidence.
- AI explanations are schema-validated, evidence-grounded, and marked insufficient when evidence is missing.
- No AI call can mutate source records or move money.

## Risks to watch

- Settlement batching and partial refunds can make naive one-to-one matching wrong.
- Bank narrations and exports vary by institution; adapters need explicit confidence and rejection paths.
- Sending raw financial data to a model creates privacy and cost risk; minimize context and measure AI value.
- A polished graph without a durable evidence model would be a demo, not a financial product.
