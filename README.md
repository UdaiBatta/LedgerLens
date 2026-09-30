# LedgerLens

LedgerLens compares payment, settlement, bank and accounting records so a finance team can find a difference, inspect its evidence, and track the follow-up. It is a **financial evidence, reconciliation and ledger-control layer**. A company's processor and accounting system remain authoritative.

Deterministic code checks money and relationships. An optional AI investigator explains the recorded checks through read-only tools. It cannot approve a match, change evidence, post a journal or move funds.

## Run locally (PowerShell)

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe backend/manage.py migrate
.\.venv\Scripts\python.exe backend/manage.py seed_demo_cases
.\.venv\Scripts\python.exe backend/manage.py seed_control_scenarios --payments 500
$env:LEDGERLENS_DEMO_MODE="true"
.\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000
```

In a second terminal at the repository root:

```powershell
npm ci
npm run dev
```

Open http://127.0.0.1:5173/#app. Vite uses port 5173 with strictPort: it fails if occupied rather than silently opening another port. Django serves the API on 8000. An ECONNREFUSED proxy error means that backend address is unavailable; start the backend and check http://127.0.0.1:8000/api/health/.

Demo mode is off by default. It permits local anonymous reads and demo assignment/investigation only for `ledgerlens-demo`; it does not permit ingestion or workflow changes. Never expose the demo server through a public proxy.

## Authentication and onboarding

For authenticated use, disable demo mode and run `backend/manage.py createsuperuser` with the virtual-environment Python. Open http://127.0.0.1:8000/admin/ to create the organization, data sources, effective-dated rule and user memberships. Superuser status alone does not bypass API membership checks.

Set `VITE_ORGANIZATION_SLUG` before starting Vite to select the organization. Sign in through http://127.0.0.1:5173/api/auth/login/?next=/%23app. Session-authenticated writes send the CSRF cookie token. Service clients may use a DRF token provisioned by a trusted administrator:

```http
Authorization: Token <secret-token>
X-Organization-Slug: acme-finops
```

The organization header selects a membership; changing it cannot grant access. Viewer and auditor memberships are read-only. Analysts, managers and administrators can ingest, investigate and assign themselves. Only managers/administrators can close a case through the workflow API. A user needs a membership in each organization they access.

## What works

- JSON batch ingestion and a versioned bank CSV template adapter; duplicates and rejected rows retain delivery evidence.
- Explicit-reference matching; inferred and ambiguous candidates never become verified automatically.
- Source/currency/effective-date rule selection for percentage fees, tax on fees, processed-refund policy and elapsed-hour deadlines.
- Captured payment, fee, tax, refund, settlement, bank and GL receipt comparisons using integer minor units.
- Many payments into one settlement and multiple bank credits for that settlement, with a receipt check for each bank credit.
- Distinct missing-evidence, not-yet-due, overdue and measured-difference classifications.
- Immutable run snapshots containing inputs, rules, decisions, checks, results, as-of time and source watermarks.
- Authenticated assignment and reasoned workflow transitions with persisted audit events.
- API-backed overview, exception list, case investigation, evidence drawer, money graph and audit log.
- Read-only connection freshness, rule version and reconciliation history APIs. Their dedicated UI pages are still pending.

Supported currencies are INR, USD, JPY and KWD. A reconciliation scope must contain one currency. FX and full accounting balances are not implemented.

## Connecting a company's records

Start with exports from a processor, one bank account and the company's ERP. Map them to the canonical contract described in [the integration guide](docs/integration-guide.md), retaining the provider's identifiers and original payload. Treat `entity_id` as an explicitly selected reconciliation scope, usually a settlement batch—not a merchant-wide bucket.

The currently implemented bank adapter expects a defined CSV template. It does not automatically understand every bank's native statement format. Live provider APIs, signed webhook receivers, OAuth and MCP connectors are not implemented. MCP is not required for ingestion: a connector calls the same authenticated API after normalization.

## AI configuration and boundaries

With no key, investigations use a deterministic rules summary and make no model request. To enable the existing Anthropic integration, set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in the backend process environment. Billing and model availability depend on that provider account; the code does not provide a free API tier. No key belongs in browser code or source control.

Each investigation selects one immutable reconciliation run at its start. Subsequent tools and the saved answer use that snapshot even if new evidence causes the case to be reconciled again. Tools expose selected normalized fields and up to 30 checks, with unresolved checks first; they exclude raw payloads. Questions and reference identifiers can still contain sensitive text, so data minimization remains necessary.

The loop permits at most four model requests and twelve tool calls, with 900 output tokens per request, a 20-second SDK timeout and one SDK retry. Persisted telemetry includes returned input/output tokens, logical model-request count, elapsed time and fallback reason. It does not estimate billed cost or count transport retries separately.

Schema and citation checks reject unsupported record references and overstated evidence sufficiency. They do not prove every sentence of model prose is correct. Operators must review the checks and source records. Cross-case clustering and AI-generated rule proposals remain planned.

## Data and architecture

```text
Processor / bank / ERP exports
  -> adapter or normalized JSON
  -> IngestionBatch + retained IngestionDelivery
  -> immutable FinancialRecord (raw payload, normalized hash/version)
  -> candidate/confirmed evidence relationships + effective rules
  -> immutable ReconciliationRun (inputs, decisions, calculations, result)
  -> current ReconciliationCase / checks / graph
  -> operator assignment and workflow + AuditEvent
  -> read-only InvestigationAgent -> immutable AgentRun
```

FinancialRecord is source evidence, not a balanced journal. Expected control totals currently suffice for the supported receipt comparisons. A shadow ledger with accounts and balanced postings is a future requirement for reversals, reserves and accounting-period controls.

Evidence, rules, runs, deliveries and investigations have application mutation guards and SQLite/PostgreSQL update/delete triggers. Database administrators can still bypass database controls; deployment roles, backups and retention must be designed before a pilot. Hashes detect content changes; they do not authenticate a bank's original statement.

Case/check/graph rows are current projections. Earlier snapshots remain. The legacy migration preserves an upgrade-time snapshot where possible, explicitly marking it `legacy-snapshot`; it cannot reconstruct rules or source inputs that were never recorded.

## Verification

```powershell
npm run check
npm run build
.\.venv\Scripts\python.exe backend/manage.py check
.\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend/manage.py test
```

GitHub Actions checks the frontend, SQLite backend and PostgreSQL 16 backend. [status.md](status.md) records executed results. [plan.md](plan.md) records remaining work; [the original audit](docs/architecture-audit.md) explains the operational use cases and baseline risks.

## Production limits

This is a working control MVP, not an approved production deployment. Remaining work includes reliable live adapters, encrypted connection credentials, durable workers/replay, large-list pagination, complete operational UI, explicit allocations, accounting lifecycle support, observability, backups and restore drills.

Current reconciliation and ingestion are synchronous and capped at 10,000 records per scope/batch. Matching still scans candidates in memory. A local 500-payment demonstration is a functional check, not evidence of million-transaction throughput. Commercial rules currently cover source/currency percentage contracts, not payment-method/network tiers, fixed/minimum fees or business-day calendars. Read [the delivery plan](plan.md) before selecting a pilot scope.
