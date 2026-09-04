# LedgerLens delivery plan

LedgerLens is an evidence-first reconciliation platform for payment processors, banks, fintechs, and any company that must explain why a financial record does not balance. The product can use AI heavily, but money calculations and state changes remain deterministic, validated, and auditable.

## Chosen backend

- Django 5.2 LTS and the Django ORM.
- SQLite for local development; PostgreSQL for production and realistic pilots.
- Django REST Framework for case, record, evidence-graph, assignment, investigator, and overview endpoints.
- Descriptive PascalCase class names such as `FinancialRecord`, `ReconciliationCase`, and `EvidenceConnection`; avoid shortened domain names that hide meaning.

## Product outcome

Given records from an order or invoice, payment gateway, refunds, fees, tax, settlement, bank statement, and accounting ledger, LedgerLens builds one traceable transaction story. It identifies the first unexplained break, shows the evidence, and uses AI to explain likely causes and recommend a safe next step.

## Implementation sequence

### 1. Canonical financial model — implemented for the seeded MVP

- Define normalized Django models for organizations, financial data sources, financial records, reconciliation cases, and evidence connections.
- Store all amounts as integer minor units with currency and source timestamps.
- Preserve original payloads, source identifiers, ingestion time, and source-system metadata.

**Exit condition:** the same payment can be represented consistently whether it came from Razorpay, Stripe, a bank CSV, an ERP, or a custom API.

### 2. Ingestion and source adapters

- Add adapters for REST APIs, webhooks, CSV/XLSX bank statements, and accounting exports.
- Make ingestion idempotent using source plus external ID plus version/hash.
- Record rejected rows and insufficient evidence instead of silently dropping them.

**Exit condition:** a replayed webhook or imported statement cannot duplicate money events.

### 3. Evidence graph — implemented for seeded cases

- Link records into a directed graph: order → payment → fee/refund → settlement → bank credit → ledger entry.
- Keep every edge explainable with the matching key, timestamp window, amount tolerance, and confidence.
- Support partial refunds, split settlements, batching, delayed events, and one-to-many matches.

**Exit condition:** an investigator can open any transaction and see the complete, auditable path plus missing links.

### 4. Deterministic reconciliation engine — implemented for six scenarios

- Match by exact references first, then constrained fallbacks such as amount, currency, account, date window, and narration.
- Calculate expected amounts, fees, tax, refunds, settlement deductions, and tolerances in code—not in an LLM.
- Classify outcomes: matched, mismatch, duplicate, missing source, ambiguous, or awaiting evidence.

**Exit condition:** historical fixtures produce repeatable results and every mismatch has a machine-readable reason.

### 5. Investigation API and operations UI — core workflow implemented

- Expose Django endpoints for traces, exceptions, evidence, source health, and reviews.
- Add filters, assignment, notes, evidence requests, and an immutable activity log.
- Make the landing page explain the product; make the dashboard useful for daily operations.

**Exit condition:** an operator can go from an exception list to a cited resolution without spreadsheets.

### 6. AI investigation layer — auditable tool loop implemented

- Send only the normalized result, relevant evidence, and allowed metadata to a model through a provider adapter.
- Require structured JSON: finding, confidence, cited record IDs, missing evidence, and recommended next action.
- Use AI for explanation, clustering, anomaly prioritization, narration parsing, and draft communications—not amount calculation or money movement.
- Validate model output against a schema; reject unsupported claims and show “insufficient evidence” when necessary.

**Exit condition:** every AI statement is traceable to deterministic checks and source records.

### 7. Production hardening — not started

- Add tenant isolation, encryption, secret management, retention policies, rate limits, and role-based access.
- Add replayable fixtures, contract tests for adapters, reconciliation golden tests, and model evaluation cases.
- Add observability for ingestion lag, match rate, unresolved value, AI cost, and human correction rate.

**Exit condition:** the service can be piloted with a real company without losing auditability or exposing financial data.

## Deliberate boundaries

- The evidence graph is the product foundation; the frontend graph is only a view of it.
- AI can explain and prioritize, but deterministic code owns balances, match decisions, permissions, and writes.
- No real payment movement is part of the first release.
