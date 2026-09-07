# LedgerLens project status

Updated: 2026-09-08.

## Current delivery

Functional reconciliation-control MVP on branch `feat/reconciliation-control-foundation`, under [pull request #1](https://github.com/UdaiBatta/LedgerLens/pull/1). This is a development milestone; the remaining production work is in [plan.md](plan.md).

## Implemented and tested

| Area | Current capability |
|---|---|
| Ingestion | Authenticated normalized JSON batches and bank CSV template adapter; duplicate/conflict checks, rejected rows and retained delivery payloads |
| Evidence | Immutable FinancialRecord fields, raw payload/hash and normalization version/hash; application and database mutation guards |
| Rules | Immutable source/currency/effective-date fee/tax/refund rules, tolerances for fee/tax comparisons and elapsed-hour deadlines |
| Matching | Type/org/scope/currency checks; explicit references; inferred or ambiguous candidates require evidence |
| Reconciliation | Payment, fee, tax, refund, settlement, bank and GL checks; unknown values distinguished from measured differences |
| Flow scope | One provider and currency per selected settlement scope; many captures into one settlement and multiple bank receipts |
| History | Immutable snapshots of inputs/rules/matches/calculations/results; current case remains a projection |
| Access | Session/token authentication, org memberships, write roles and manager-only closure; explicit local demo |
| Operations | Assignment and workflow APIs with persisted audit; connection freshness/rule/history read APIs |
| AI | Read-only tools bound to one snapshot, schema/citation checks, bounded calls, no-key rules summary, usage/latency metadata |
| UI | Overview, exceptions, case, source drawer, money graph and audit log; actual identity and unknown-amount labels |
| Development | Frontend fixed to 127.0.0.1:5173; PostgreSQL 16 and SQLite CI |

The Connections, Rule Studio and reconciliation history APIs do not yet have complete dedicated pages. Assignment works in the current UI; workflow closure remains an API operation. Global search remains unwired. AI does not yet aggregate cross-case incidents or propose rules.

## Executed verification

- 2026-09-08: 67 Django tests passed locally using Python 3.14 / Django 5.2.17.
- No pending model migrations detected.
- Frontend TypeScript/ESLint checks and Vite production build passed locally.
- Frontend, SQLite and PostgreSQL CI checks passed on revision 975fe55; final revision status is visible in PR checks.
- 2026-09-07: seed_control_scenarios --payments 500 created a matched INR 492,920 settlement plus separate missing-GL and INR 5 incorrect-GL cases. Combined local ingestion/reconciliation took 28.988 seconds. This is one measurement, not a throughput guarantee.
- Database backup was retained locally before upgrading; existing source evidence was not deleted.
- Browser verification found a SQLite expression-depth failure loading the large demo. The case list now skips graph prefetches, and detail queries join record sources. Regression tests cover summary and detail behavior.

- Browser verification passed in installed Edge using Playwright: overview → exceptions → missing-GL case → saved no-key rules summary. Checked 1440×1000 and 390×844 viewports, with no horizontal overflow or console errors; the existing operations layout is preserved.
- The running 500-payment detail endpoint returned matched with 2,002 evidence connections and INR 492,920 expected, after the query fix.

These checks cover a synthetic local operator workflow, not live provider connectivity or production load.

## Known limits

No live bank/processor/ERP connectors, signed webhooks, encrypted connection credentials, durable workers, full pagination, explicit many-to-many allocation, chargeback/reversal/reserve accounting, balanced journal/period model or production-scale benchmark.

No automatic external financial writes. No FX reconciliation. Missing or overlapping applicable rules block the scope. Percentage rules are not a general commercial pricing engine. Deadlines are elapsed hours, not banking calendars.

Immutable snapshots retain what was used; semantic correctness of arbitrary AI prose is not automatically proven. AI receives a bounded subset of checks. No paid-provider end-to-end request has been verified; provider behavior is tested with mocks. Token telemetry is not a billed-cost calculation.

Legacy upgrade snapshots are labeled as incomplete historical evidence. Source IDs and original execution details that were never retained cannot be recreated.

## Next work

Review and merge the current PR only after approval. Then deliver one bank + ERP export import workflow with reviewable mappings, rejected rows, explicit settlement scopes and a rerunnable evidence trail. Use sanitized fixtures before connecting a real company's data.
