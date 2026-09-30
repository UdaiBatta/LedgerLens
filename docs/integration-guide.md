# Integrating source records

This is the implemented contract for a supervised import. It is not a live provider connection or an authorization to query a company's bank account.

## Provision and map

Create the organization and memberships through trusted Django administration. For the payment source, create an immutable ReconciliationRuleVersion before reconciling: source, version, currency, effective_from/effective_until, fee_basis_points, tax_basis_points, refund_policy, bank_wait_hours, settlement_wait_hours and tolerance_minor. Exactly one source/currency rule must apply at each payment's occurrence time.

Use one `entity_id` for an explicitly selected settlement scope. Do not combine all of a merchant's records under one entity. Preserve external IDs and explicit relationships. Imports from a bank and ERP must share the scope ID and currency with the relevant processor records.

| Record | Explicit predecessor | Default direction |
|---|---|---|
| order | None | credit |
| payment | order ID | credit |
| fee | payment ID | debit |
| tax | fee ID | debit |
| refund | captured payment ID | debit |
| settlement | contributing payment/deduction IDs | credit |
| bank_credit | settlement ID | credit |
| ledger_entry | bank credit ID | credit |

These are reconciliation evidence directions, not balanced accounting journal legs. FinancialRecord does not represent a complete double-entry ledger. Final statuses currently accepted by reconciliation are processed, captured, posted or settled; pending/failed/reversed lifecycle records must not be relabeled as final just to make a scope pass.

## JSON ingestion

POST `/api/ingestion/batches/` with a session/CSRF token or administrator-provisioned DRF token and `X-Organization-Slug`. The organization must already exist and the caller must have a write membership. The API may create the named source inside that organization.

```json
{
  "organization_slug": "acme-finops",
  "organization_name": "Acme FinOps",
  "source_name": "Processor export",
  "source_type": "payment_gateway",
  "batch_reference": "processor-20260908-001",
  "records": [
    {
      "external_record_id": "PAY-1001",
      "record_type": "payment",
      "entity_id": "SETTLEMENT-SCOPE-1001",
      "amount_minor": 100000,
      "currency": "INR",
      "occurred_at": "2026-09-08T10:00:00Z",
      "status": "captured",
      "reference": "ORD-1001",
      "normalization_version": "acme-export-v1",
      "raw_payload": {"payment_id": "PAY-1001", "amount": 100000}
    }
  ]
}
```

This example ingests a payment only. It cannot prove a complete settlement. Import the order, fee, tax, settlement, bank and ERP evidence through their respective sources as well. Source types are order_system, payment_gateway, bank_account, general_ledger and tax_system.

For a batch containing multiple payments, a settlement can include `raw_payload.contributing_references` listing the contributing chain endpoints (for example each tax-record ID). Every capture and deduction must be traceable to the settlement. Caller-selected scope membership alone is not proof of allocation; true split/many-to-many allocation is unsupported.

The optional top-level field below requests reconciliation from stored records after import:

```json
{
  "reconcile": {
    "case_reference": "CASE-SETTLEMENT-1001",
    "entity_id": "SETTLEMENT-SCOPE-1001"
  }
}
```

An identical batch replay returns 200 with `replayed: true`; new imports return 201. The original batch result remains, and delivery history records the replay. Changed data under the same batch reference returns 409. A conflicting record under a different batch is rejected at row level; inspect `batch.rejected_count` and `batch.errors` even when HTTP status is 201. Valid rows may still import.

If reconciliation itself cannot run, the response is 422 and includes the persisted ingestion result plus `reconciliation_error`. Do not assume the ingestion was rolled back. Missing evidence inside a supported scope can instead produce a successful API response whose case has `insufficient_evidence`.

Ingestion is bounded to 1–10,000 records and the HTTP body limit is 5 MB. Use smaller batches. Reconciliation is still synchronous, so do not deploy it behind high-volume webhook traffic yet.

## Bank CSV template

```csv
transaction_reference,amount_minor,value_date,entity_id,settlement_reference,currency,narration
BANK-1001,98584,2026-09-08T12:00:00Z,SETTLEMENT-SCOPE-1001,SET-1001,INR,Settlement receipt
```

Run with the virtual-environment Python from the repository root:

```powershell
.\.venv\Scripts\python.exe backend/manage.py import_bank_statement bank.csv --organization-slug acme-finops --source-name "Bank export" --batch-reference bank-20260908-001 --reconcile-entity SETTLEMENT-SCOPE-1001
```

The trusted CLI can provision the organization/source and uses the batch reference as the case reference when reconciliation is requested. For stable case history through the API, keep a consistent explicit `case_reference` on reruns.

`entity_id` must be present and populated for successful row ingestion. The parser validates the three required header names transaction_reference, amount_minor and value_date; missing entity_id is subsequently rejected by ingestion. Extra columns are retained in raw_payload. Nonnumeric amounts are retained and rejected per row; malformed column counts or duplicate headers reject parsing. Original parsed rows are retained, not the byte-for-byte source file. Native bank column mapping, decimal-to-minor conversion and file retention need an adapter for that bank.

## Review and follow-up

1. GET `/api/ingestion/batches/` to inspect outcomes and row errors.
2. GET `/api/cases/` and `/api/cases/<public_id>/` for current status and checks. Always inspect `amounts_known`; legacy expected/actual fields can contain compatibility zeroes when the difference is unknown.
3. GET `/api/cases/<public_id>/reconciliation-runs/` for up to 100 immutable snapshots, newest first. Each contains exact inputs, rule versions, matching decisions, check amounts, as_of time and watermarks.
4. POST `/api/cases/<public_id>/assign/` with `{}` to assign yourself.
5. POST `/api/cases/<public_id>/workflow/` with `{"status":"waiting_for_bank","reason":"Requested transfer confirmation"}`. Supported states: investigating, waiting_for_source, waiting_for_bank, resolved, accepted_variance and false_positive. Closing requires a manager/administrator. Workflow state does not change the financial result.
6. POST `/api/cases/<public_id>/ask/` with `{"question":"Which evidence should I request?"}`. The saved answer records which reconciliation snapshot it inspected.
7. Import later evidence with a new batch reference and reconcile using the original case reference. Earlier run snapshots and investigations remain.

GET `/api/connections/` reports freshness from last received records, not live provider connectivity. GET `/api/rule-versions/` lists rules. GET `/api/audit-log/` returns persisted case operations. These endpoints are subject to the same membership boundary.

## Before using real records

Agree a source contract and approved data fields with the company. Establish least-privilege credentials, retention, credential encryption, source authenticity checks and an operational owner. Do not send raw exports to an AI model. Start with anonymized fixtures proving clean matches, wrong fees, duplicate IDs, missing bank receipts and missing/wrong GL postings. Validate supported cases with finance before allowing operators to rely on classifications.

For PostgreSQL set POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT and POSTGRES_SSLMODE (defaults to require). Production also requires DJANGO_DEBUG=false, a non-default DJANGO_SECRET_KEY, appropriate DJANGO_ALLOWED_HOSTS and demo mode disabled. Deployment, proxy/TLS configuration, distributed throttling, service-token rotation, backups and restore testing remain required pilot work.
