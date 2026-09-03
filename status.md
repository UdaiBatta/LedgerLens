# LedgerLens project status

Last updated: 2026-09-04

## Current phase

**Phase 0 — product and frontend prototype complete; Phase 1 — canonical data model next.**

## Shipped

- React/TypeScript/Vite prototype with shadcn-compatible components.
- Landing page with CRTWarp background, product narrative, and responsive navigation.
- Interactive investigation preview showing order, gateway, settlement, bank credit, and ledger checkpoints.
- Reconciliation dashboard with summary metrics, money movement view, and exception table.
- Case investigation view with deterministic checks, cited evidence, confidence, and AI-investigator placeholder interaction.
- Responsive desktop/mobile styling and accessibility basics (semantic landmarks, labels, keyboard-focusable controls, reduced-motion fallback).
- Evidence-trail visual pass: full-viewport hero, restrained trace canvas, clear first-break treatment.
- GitHub main branch kept current through small commits.

## Not yet implemented

- Persistent database or tenant model.
- Real source adapters, webhooks, bank statement import, and accounting exports.
- Canonical money-event schema and evidence graph backend.
- Deterministic reconciliation service for partial refunds, fees, tax, batching, and tolerances.
- Real AI provider integration, structured output validation, prompt/version tracking, and cost controls.
- Authentication, RBAC, encryption, retention, audit persistence, and production observability.

## Next milestone: canonical model spike

1. Write the normalized TypeScript/domain schema and amount/currency rules.
2. Create a small PostgreSQL schema or local fixture store.
3. Convert the existing mock data into canonical records and evidence links.
4. Implement one deterministic trace builder and one mismatch fixture (`₹3.40` bank shortfall).
5. Add a test that proves the same input produces the same trace and first-break classification.

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

