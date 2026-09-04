# LedgerLens project status

Last updated: 2026-09-04

## Current phase

**Phases 1–6 complete for the seeded end-to-end MVP. Phase 7 hardening and Phase 8 product expansion are next.**

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

## Not yet implemented

- Production PostgreSQL configuration and database deployment.
- Real source adapters, webhooks, bank statement import, and accounting exports.
- Live source adapters, webhook endpoints, bank CSV/XLSX import, and accounting exports.
- Full one-to-many batched-settlement and ambiguous-match resolution beyond the seeded graph.
- Prompt version records, provider cost accounting, retry policy, and a model evaluation corpus.
- Authentication, RBAC, encryption, retention, audit persistence, and production observability.
- Money Graph, cross-case AI Investigator, Connections, Rule Studio, and Audit Log pages.

## Next milestone: operations graph and hardening

1. Render `/api/cases/<id>/evidence-graph/` as the Money Graph page.
2. Add a persisted case-activity audit model and Audit Log page.
3. Add source-connection health and read-only rule-catalog pages.
4. Add authentication, organization scoping, request limits, and production-safe error reporting.
5. Add a real adapter contract plus one bank CSV import path.

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
