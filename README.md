# LedgerLens

LedgerLens is an evidence-first financial reconciliation workspace. It joins records from order systems, payment gateways, settlements, bank statements, and accounting ledgers into a traceable graph; deterministic rules locate the first break, while an optional AI investigator explains only the evidence those rules produced.

The core principle is simple: **code verifies the money; AI investigates and explains it.** The AI cannot create evidence links, change source records, alter a reconciliation result, or move money.

## Run locally

Frontend:

```bash
npm install
npm run dev
```

Backend:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py seed_demo_cases
python manage.py runserver
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to Django at `http://127.0.0.1:8000`.

The investigator works without an API key by returning a deterministic, evidence-cited fallback. To exercise the optional Anthropic tool-use loop, set both variables before starting Django:

```powershell
$env:ANTHROPIC_API_KEY="your-key"
$env:ANTHROPIC_MODEL="a-model-available-to-your-Anthropic-account"
```

The model is deliberately configured by environment variable so the repository does not assume a paid account or hard-code a model version.

## Working demonstration

- `POST /api/ingestion/batches/` accepts real normalized financial records, records the batch result, rejects conflicting immutable evidence, and can optionally trigger reconciliation for an entity.
- `seed_demo_cases` creates 216 records across six scenarios: clean match, unexplained ₹3.40 shortfall, fee mismatch, delayed bank credit, missing refund deduction, and idempotent duplicate delivery.
- The deterministic engine calculates expected fees, tax, refunds, settlements, and bank differences in integer paise.
- The matcher persists explainable graph edges with method, confidence, and rationale.
- The DRF API serves real overview metrics, distinct cases, evidence graphs, assignment, record details, and investigator history.
- The React dashboard opens each real case, renders its actual transaction path and checks, persists assignment, and opens immutable source payloads in an evidence drawer.
- The investigator uses an auditable four-turn tool loop when configured, validates structured output and citations, and falls back safely when no paid key is available.

No external payment account or paid AI key is required for the demo.

## Ingestion contract

Send one source batch at a time to `POST /api/ingestion/batches/`. A batch reference is idempotent: replaying identical data is a no-op, while reusing it for changed data returns a conflict. Invalid rows are retained in the batch's `errors` list instead of being silently discarded.

```json
{
  "organization_slug": "acme-finops",
  "organization_name": "Acme FinOps",
  "source_name": "Payment Gateway",
  "source_type": "payment_gateway",
  "batch_reference": "gateway-2026-09-04-001",
  "records": [{
    "external_record_id": "PAY-1001",
    "record_type": "payment",
    "entity_id": "ORDER-1001",
    "amount_minor": 100000,
    "currency": "INR",
    "occurred_at": "2026-09-04T10:00:00Z",
    "reference": "ORD-1001",
    "raw_payload": {"gateway_payment_id": "PAY-1001"}
  }],
  "reconcile": {
    "case_reference": "CASE-1001",
    "entity_id": "ORDER-1001"
  }
}
```

Use `GET /api/ingestion/batches/` to inspect the latest 100 batch outcomes. Reconciliation is deliberately optional: evidence ingestion remains durable even if the requested reconciliation cannot run yet because a payment or another required record is missing.

## Architecture

```text
Source payloads ──► IngestionBatch audit
     │ immutable raw evidence + idempotency key
     ▼
FinancialRecord ──► EvidenceMatcher ──► EvidenceConnection graph
     │                                      │
     └────────────► ReconciliationEngine ◄──┘
                          │
                          ├──► ReconciliationCase + CheckResult
                          │           │
                          │           ▼ read-only evidence
                          │     InvestigationAgent ──► AgentRun audit
                          │
                          ▼
                     DRF endpoints ──► React operations UI
```

All amounts use integer minor units. Raw payloads and content hashes are immutable after ingestion. Evidence edges may be created only by the rules engine or a human—there is intentionally no `ai` value in `EvidenceCreatedBy`.

## Product boundary

The reconciliation engine—not an LLM—must calculate amounts, apply tolerances, and decide whether records match. AI receives that verified result to explain the likely cause, cite the supporting records, group similar exceptions, and recommend a safe next action; it never moves money or rewrites source records.

## Stack

React 19, TypeScript, Vite, Tailwind CSS v4, shadcn-compatible Base UI components, Lucide icons, Three.js, React Bits CRTWarp, Django 5.2 LTS, Django REST Framework, and the optional Anthropic SDK. SQLite is used locally; PostgreSQL is the production target.

## Verification

```bash
npm run check
npm run build
cd backend
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Honest scope

This is a working ingestion and reconciliation MVP, not a production banking deployment. Live Razorpay/bank/ERP adapters, authentication and role-based access, tenant-scoped API authorization, encrypted secret storage, background ingestion, PostgreSQL deployment, model-cost telemetry, and the remaining operations pages are tracked in [`status.md`](status.md).
