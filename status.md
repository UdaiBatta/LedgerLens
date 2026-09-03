# LedgerLens project status

Last updated: 2026-09-04

## Current phase

**Phase 1 — Django canonical data-model foundation in progress.**

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

## Not yet implemented

- Production PostgreSQL configuration and database deployment.
- Real source adapters, webhooks, bank statement import, and accounting exports.
- Canonical money-event schema and evidence graph backend.
- Deterministic reconciliation service for partial refunds, fees, tax, batching, and tolerances.
- Real AI provider integration, structured output validation, prompt/version tracking, and cost controls.
- Authentication, RBAC, encryption, retention, audit persistence, and production observability.

## Next milestone: canonical model spike

1. Generate and review the first Django migration.
2. Convert the existing mock data into Django records and evidence connections.
3. Implement one deterministic trace builder and the `₹3.40` bank-shortfall fixture.
4. Add JSON endpoints for the dashboard and case investigation views.
5. Connect the React prototype to those endpoints.

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
