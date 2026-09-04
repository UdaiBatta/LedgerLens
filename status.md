# LedgerLens project status

Last updated: 2026-09-04

## Current phase

**Architecture-first functional MVP.** UI expansion is paused while the real pipeline—ingest → match → reconcile → investigate—is made credible and testable.

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

## Architecture milestone in this change

- `IngestionBatch` persists source, content hash, processing outcome, record counts, rejected-row reasons, and completion time.
- `POST /api/ingestion/batches/` accepts real records and can optionally trigger deterministic reconciliation from stored evidence.
- Identical batch replays are no-ops; changed data under the same batch reference returns a conflict.
- A later batch cannot overwrite an existing record's immutable raw evidence.
- The matcher now follows explicit record references first and applies bounded amount/time fallback matching only to valid predecessor types. It no longer links unrelated adjacent records merely because they arrived in sequence.
- `ReconciliationCase.expected_amount_minor`/`actual_amount_minor` now reflect whichever check actually broke first (fee, tax, settlement, or bank credit), not always the settlement totals — fixes a real UI inconsistency where fee/tax-mismatch cases showed a misleading ₹0.00 variance next to a "Needs review" status.
- `python manage.py import_bank_statement <csv> --organization-slug=... --source-name=... --batch-reference=... [--reconcile-entity=...]` — the first real source adapter. Parses a bank statement CSV into the same record shape the ingestion service already accepts, so it shares the tested path rather than a parallel one. Replay-safe and partial-batch-safe (verified against a live import: good rows import, bad rows reject with a reason, a second run of the same batch reference is a no-op).
- Backend coverage is now 27 tests, including ingestion replay/conflict/rejection behavior, reconciliation preconditions, guards against unrelated or ambiguous evidence, the fee-variance regression, and the bank-statement adapter (parser unit tests + a command integration test that resolves a real `bank_credit_delayed` seeded case to `matched`).

## Not yet implemented

- Production PostgreSQL configuration and database deployment.
- Live webhook endpoints and accounting-export adapters (bank CSV import is now real; other source types still seed-only).
- Full one-to-many batched-settlement and ambiguous-match resolution beyond the seeded graph.
- Prompt version records, provider cost accounting, retry policy, and a model evaluation corpus.
- Authentication, RBAC, encryption, retention, audit persistence, and production observability.
- Cross-case AI Investigator, Connections, and Rule Studio pages (Money Graph and Audit Log are done; these three remain inert by design, labeled "planned").
- A persisted case-status-change event log — Audit Log currently derives its feed from `AgentRun` and `EvidenceConnection` timestamps only, not discrete status-transition events (case.status is visible on the case page itself; adding a dedicated activity model was deferred as unnecessary for now).
- Batched settlements (open decision D4 — many payments to one settlement) — the matcher currently selects one valid predecessor for each destination record.
- Demo recording and concept-doc trim (Phase 9); the README and architecture diagram already exist.
- A raw/normalized provenance table split — deliberately skipped; see `plan.md` for the rationale (the current single-table design already gives the same immutability guarantee, tested).

## Next milestone: strengthen the backend architecture

1. ~~Route the first real bank CSV adapter through the ingestion service.~~ Done.
2. Support many-payments-to-one-settlement matching and reconciliation.
3. Add organization-scoped authentication and authorization to every API queryset and write endpoint.
4. Add persisted reconciliation-run and case-status activity events.
5. Move realistic pilots to PostgreSQL with background ingestion, retries, rate limits, secret management, and observability.

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
