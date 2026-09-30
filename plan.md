# LedgerLens delivery plan

Updated: 2026-09-08. This replaces the obsolete submission-phase checklist; earlier versions remain in Git history. Actual verification is recorded in [status.md](status.md).

## Product outcome

A controller imports processor, settlement, bank and ERP records. LedgerLens applies the agreed commercial rules, finds the first supported financial difference, shows the precise inputs and calculations, and records the operator's follow-up. AI helps investigate those recorded facts. The authoritative accounting system remains outside LedgerLens.

## Completed foundation

- [x] Canonical evidence, retained ingestion outcomes and normalized hash/version.
- [x] Membership authentication and server-side role checks.
- [x] Immutable rules and reconciliation snapshots.
- [x] Mandatory payment/deduction/settlement/bank/GL receipt checks.
- [x] Candidate versus confirmed relationships; ambiguous evidence blocks matching.
- [x] Processed partial/multiple refunds, many-payments-to-one-settlement, multiple bank receipts.
- [x] Elapsed-hour waiting/overdue states and currency exponents.
- [x] Persisted assignment/workflow audit and immutable AI investigations.
- [x] Snapshot-bound AI tools, structured validation, citation validation and no-key fallback.
- [x] Realistic 500-payment, missing-GL and incorrect-GL demonstration.
- [x] SQLite and PostgreSQL CI path.
- [x] Honest UI amount/identity labels and a strict frontend port.

## Next milestone: one reviewable company import

1. Agree a narrow pilot contract: one processor report, one bank CSV and one ERP export, one currency and explicitly identified settlement scopes.
2. Add a versioned ERP export adapter and bank-format mapping with sanitized fixtures. Preserve original rows, source references, normalization version and rejected-row reasons.
3. Add an authenticated import preview/confirmation flow using the existing batch service. Show accepted, duplicate and rejected counts, then the resulting exceptions.
4. Expose source freshness, run history and read-only rule versions in the existing operations UI.
5. Complete operator workflow UI with owner, reason, state and persisted audit events.

Exit condition: the same source exports can be imported twice without double counting; a missing bank/ERP record is visible; a corrected follow-up import creates a new result while retaining the previous investigation.

## P0 before a company pilot

- Require unambiguous settlement allocation for every supported workflow. Add explicit allocation records before enabling split payments, multiple settlements per bank receipt or cross-provider scopes.
- Validate authoritative relationships before reporting monetary divergence; expand golden fixtures for ambiguous/missing scope membership and identifier collisions.
- Extend commercial-rule dimensions only for the pilot's actual contracts. Add rounding, business calendars and fee-refund rules with finance-approved examples.
- Define source identity immutability, application/database roles, credential encryption/rotation, retention, backup and restore procedures.
- Add production settings checks and scoped integration credentials. Current DRF user tokens and local-memory throttles need an operational deployment policy.

## P1 reliability and operations

- Move expensive import/reconciliation to a durable worker, with idempotent jobs, retries, correlation IDs and failed-job visibility.
- Add provider-specific signed webhooks plus backfill/replay only after reviewing official provider contracts.
- Paginate lists and large evidence views; measure query count, ingestion/reconciliation latency, freshness and rejection rates.
- Record started/failed reconciliation jobs, comments and manual match confirmation/rejection as audited operations.
- Provide reproducible evidence export and safe rule approval/testing workflows.

## P2 after the pilot path works

- Balanced shadow journals, reversals, reserves, chargebacks and accounting periods when the agreed use cases require them.
- Deterministic cross-case incident aggregates, then AI summaries of those aggregates.
- Model evaluation corpus, PII controls, context pagination, cost budgets and operator feedback.
- Larger synthetic benchmarks (10k, 100k, 1m events) after worker/query changes. Report measured ceilings.

## Delivery rules

Use focused commits on pull-request branches, keep main reviewable, and verify the final PR revision in CI before requesting merge review. Do not automatically merge a PR without user authorization. Update the status and integration contract whenever behavior changes.

Keep the current UI language and layout consistent. Feature pages must expose real operational data or remain clearly marked as pending. No fabricated confidence, connected-source status, recovered-money metric or claim of production readiness.

## Pilot acceptance example

The requested example contains an arithmetic discrepancy: INR 12.31 crore expected versus 12.309 crore reported is INR 10,000; bank receipt of 12.3087 crore adds INR 3,000. Total is INR 13,000, not INR 30,000. The test records both stage differences and confirms the ERP equals the bank.

Completing that fixture demonstrates a supported calculation, not complete lifecycle or production readiness.
