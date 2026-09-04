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
- `ReconciliationEngine` now supports batched settlements: one or more payment records per case instead of exactly one. Each payment's fee/tax is matched to that specific payment (not just "the first fee in the trace"), expected fees/taxes are summed across all payments, and per-payment checks get a disambiguating suffix when there is more than one payment. Single-payment cases are byte-identical to before (same check names, same math) — verified with the full existing test suite plus a browser check of a live single-payment case.
- `EvidenceMatcher` now recognizes a settlement's `raw_payload["contributing_references"]` list, so a batched settlement fed by multiple payment chains gets one evidence edge per contributing chain — a real converging graph, not a chain that only captures the last contributor. Verified with an explicit edge-set assertion in `test_engine_batches_two_payments_into_one_settlement`.
- Case-detail page: the "Transaction path" timeline now detects a batched case (more than one payment) and shows a notice pointing at the Money Graph page instead of rendering a broken linear list; ordinary single-payment cases are unchanged (verified in the browser). The underlying `pathRecords` also now deduplicates by record id instead of assuming a strict single chain.
- Every API view now requires an `X-Organization-Slug` header and scopes its queryset to that organization: cases, records, overview metrics, audit log, and listing ingestion batches. A second organization sees an empty case list, gets a 404 on any cross-org case detail lookup, and sees zero metrics — verified with dedicated tests, not just "existing tests still pass." Ingesting still allows creating a brand-new organization on first use, but the header must match the payload's `organization_slug` or the request is rejected with 403. The frontend sends the header on every request already.
- Fixed the "Money Graph" sidebar link showing as disabled from the dashboard even though the page works — `Dashboard` now passes a handler using the same highest-priority case it already computes for its "Review exceptions" button.
- Backend coverage is now 30 tests, including ingestion replay/conflict/rejection behavior, reconciliation preconditions, guards against unrelated or ambiguous evidence, the fee-variance regression, the bank-statement adapter, the batched-settlement engine/matcher behavior, and organization-scoping isolation.

## Not yet implemented

- Production PostgreSQL configuration and database deployment.
- Live webhook endpoints and accounting-export adapters (bank CSV import is now real; other source types still seed-only).
- Ambiguous-match resolution beyond the seeded graph (batched settlement matching itself is now implemented).
- Prompt version records, provider cost accounting, retry policy, and a model evaluation corpus.
- Real user login/session authentication, RBAC, encryption, retention, and production observability. (Organization-level data isolation is done; this is about individual user identity, which plan decision D5 still says isn't needed for this submission.)
- Cross-case AI Investigator, Connections, and Rule Studio pages (Money Graph and Audit Log are done; these three remain inert by design, labeled "planned"). Next up.
- A persisted case-status-change event log — Audit Log currently derives its feed from `AgentRun` and `EvidenceConnection` timestamps only, not discrete status-transition events (case.status is visible on the case page itself; adding a dedicated activity model was deferred as unnecessary for now).
- No seeded demo scenario currently exercises batched settlement (all six seeded cases are single-payment); the capability is implemented and tested but not yet visible in the default demo data.
- Demo recording and concept-doc trim (Phase 9); the README and architecture diagram already exist.
- A raw/normalized provenance table split — deliberately skipped; see `plan.md` for the rationale (the current single-table design already gives the same immutability guarantee, tested).

## Next milestone: strengthen the backend architecture

1. ~~Route the first real bank CSV adapter through the ingestion service.~~ Done.
2. ~~Support many-payments-to-one-settlement matching and reconciliation.~~ Done.
3. ~~Add organization-scoped data isolation to every API queryset and write endpoint.~~ Done (header-based, not full user auth — see plan.md item 6).
4. Build the remaining Phase 8 sidebar pages: Connections (source health), Rule Studio (read-only check catalog), and cross-case AI Investigator.
5. Add persisted reconciliation-run and case-status activity events.
6. Move realistic pilots to PostgreSQL with background ingestion, retries, rate limits, secret management, and observability.

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
