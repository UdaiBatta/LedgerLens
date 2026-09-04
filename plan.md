# LedgerLens delivery plan

LedgerLens is an evidence-first reconciliation platform for payment processors, banks, fintechs, and any company that must explain why a financial record does not balance. The product can use AI heavily, but money calculations and state changes remain deterministic, validated, and auditable.

## Active build plan

This is the plan currently being followed, in strict phase order — no phase's remaining items start before every earlier phase's checklist is verified against the code, not just assumed done. `status.md` is updated after every phase-relevant change and must always agree with this document.

**Target:** a working end-to-end submission for the Razorpay AI Builders funnel.
**Stack:** Django + DRF backend, existing React frontend, Anthropic SDK for the agent layer.
**Principle that governs every decision below:** deterministic code computes the money; the AI only interprets and explains what the code already proved.

### 0. Current state — what exists and what doesn't

| Area | State | Notes |
|---|---|---|
| Concept / product doc | Done | Over-developed relative to code; trim before submitting |
| Landing page | Done | Good; hero mockup promises a connected graph the app now shows via Money Graph |
| Dashboard (Overview) | Done | Metrics, money-movement strip, AI briefing, exceptions table — all reading real API data |
| Case detail page | Done | Each case reads its own `:id` and renders distinct content |
| Money Graph | **Done** | Renders `/api/cases/<id>/evidence-graph/` as an SVG diagram; solid edges for exact matches, dashed for sub-1.0 confidence |
| Audit Log | **Done** | Synthesized from `AgentRun` + `EvidenceConnection` rows, no new model |
| AI Investigator (in-case) | Done | Ask form, history, citations, insufficient-evidence outcome all working |
| Rule Studio | Not started | Sidebar link is honestly disabled ("Planned after the investigation workflow") |
| Connections | Not started | Sidebar link is honestly disabled |
| Cross-case AI Investigator page | Not started | Sidebar link is honestly disabled |
| Backend | Done for the seeded MVP | Models, matcher, engine, agent, API, and tests all exist |

### 1. Gap inventory

Gaps still open, tagged with severity and which phase closes them. (Closed gaps from the original inventory are omitted here; see git history for the full original list.)

| # | Gap | Severity | Phase |
|---|---|---|---|
| B2 (partial) | 3 of 7 sidebar links still inert (Rule Studio, Connections, cross-case AI Investigator) | Critical → Medium | 8 |
| B7 | Top search bar is decorative — no results, no autocomplete | Medium | 8 |
| B8 | Profile avatar is decorative — no dropdown, no menu | Low | 8 |
| B9 | Dashboard money-movement strip lacks the connected-path visual the landing page promises | Medium | 8 |
| C1 | No README framing the problem, architecture, and how to run it | Critical | 9 |
| C2 | No architecture diagram | High | 9 |
| C3 | No demo recording | High | 9 |
| C4 | 15-section concept doc will read as filler to a technical reviewer | Medium | 9 |
| D4 | Batched settlements (many payments → one settlement) not yet supported by the matcher | Medium | Post-submission unless reprioritized |

### 2. Dependency map

```
Phase 1  ledger app          SourceRecord, NormalizedRecord                    ✅ done
             ↓
Phase 2  seed command        4–6 scenario chains of real records               ✅ done
             ↓
Phase 3  evidence app        matcher → Link rows  ─────────────┐               ✅ done
             ↓                                                  │
Phase 4  engine app          rules → CheckResult, Case          │              ✅ done
             ↓                                                  │
Phase 5  agent app           tool-use loop → AgentRun           │              ✅ done
             ↓                                                  │
Phase 6  api app + wiring    DRF endpoints, frontend reads real data           ✅ done
             ↓                                                  │
Phase 7  hardening           tests, error/empty/loading states  │              ✅ done
             ↓                                                  │
Phase 8  Money Graph  ←──────────────────────────────────────────┘            🔶 in progress
             ↓                (renders Link rows from Phase 3)      Money Graph + Audit Log done;
             ↓                                                      Connections + Rule Studio next
Phase 9  submission prep     README, diagram, recording, doc trim              ⬜ not started
```

**Cut line:** if time runs short, Phases 1–6 plus 9 constitute a complete, honest submission. Phases 7–8 are what make it good. (Phase 7 is now done; only Connections and Rule Studio remain in Phase 8.)

### 3. Phase-by-phase plan

#### Phase 1 — `ledger` app: canonical data layer — DONE

Implemented as `Organization`, `FinancialDataSource`, `FinancialRecord`, `ReconciliationCase`, `EvidenceConnection` in `backend/reconciliation/models.py`. Immutable source records: `FinancialRecord.raw_payload` cannot be mutated after ingest (enforced in `save()`, tested). Money stored as integer minor units (`amount_minor`, paise). `unique_together` on `(source, record_type, external_record_id)` makes re-ingestion idempotent.

**Exit condition:** met — `python manage.py migrate` succeeds; model tests pass.

#### Phase 2 — demo dataset — DONE

`python manage.py seed_demo_cases` seeds six scenario chains (clean match ×2, settlement short/insufficient-evidence, fee mismatch, bank credit delayed, settlement mismatch) plus a duplicate-payment idempotency check, totaling 216 records. Idempotent — re-running the command does not create duplicate records (tested).

**Exit condition:** met — the DB holds six distinct, inspectable case chains.

#### Phase 3 — evidence matcher and the `EvidenceConnection` table — DONE

`backend/reconciliation/matcher.py`'s `EvidenceMatcher` links records sequentially with exact-reference matching first, then shared-reference matching, then amount-and-time fuzzy matching with an explicit tolerance and confidence < 1.0 — every connection records `rationale` (matched fields, tolerances). `created_by` has no `'ai'` choice (`EvidenceCreatedBy`: `rules_engine` | `human`) — enforced at the model layer.

**Exit condition:** met — the settlement-short scenario has a fuzzy (0.75 confidence) link with rationale (tested).

#### Phase 4 — `ReconciliationEngine`: deterministic reconciliation — DONE

`backend/reconciliation/engine.py`. Seven rule checks per case (order-capture match, fee calculation, tax-on-fee calculation, settlement calculation, bank acknowledgement, bank-credit-equals-settlement, reconciliation-note-present), each pure and returning `passed` / `failed` / `waiting`. `waiting` is a first-class distinct state from `failed`, producing the `insufficient_evidence` case status. Unit tests assert exact variances and statuses for all six seeded scenarios.

**Exit condition:** met — engine tests pass for every seeded scenario.

#### Phase 5 — `InvestigationAgent`: the tool-use loop — DONE

`backend/reconciliation/agent.py`. Anthropic SDK tool-use loop (`get_transaction`/`get_bank_statement_line`/`get_settlement_report`/`get_check_results`), capped at 4 turns, structured JSON output validated against a schema (conclusion, confidence, evidence_cited, sufficient_evidence, recommended_action). Citations are validated against what tools actually returned — the model cannot cite records it never looked up. A deterministic, no-API-key fallback exists so the demo works without a live key, including the explicit insufficient-evidence outcome for the settlement-short case. Every run is logged to `AgentRun`.

**Exit condition:** met — asking about the settlement-short case returns `sufficient_evidence: false` with cited records (tested).

#### Phase 6 — `api` app + frontend wiring — DONE

DRF endpoints: `/api/cases/`, `/api/cases/<id>/`, `/api/cases/<id>/evidence-graph/`, `/api/records/<id>/`, `/api/cases/<id>/assign/`, `/api/cases/<id>/ask/`, `/api/cases/<id>/runs/`, `/api/metrics/overview/`. Frontend (`src/App.tsx`, `src/api.ts`) has zero hardcoded case data — every page fetches from the API. Evidence chips open a drawer with the raw source payload. Assignment POSTs and re-fetches. The ask box clears on submit, submits on Enter, shows history and a loading state.

**Exit condition:** met.

#### Phase 7 — hardening — DONE

- Empty/error/loading states: present on Dashboard, CaseDetail, MoneyGraphPage, AuditLogPage, and Exceptions (`api-state` class, 10 usages).
- Import-direction test: `test_money_engine_does_not_import_the_agent_layer` in `backend/reconciliation/tests.py` asserts `engine.py` contains no `from .agent` / `import agent`.
- Engine tests expanded to cover every seeded scenario: `test_every_seeded_scenario_has_the_expected_outcome` asserts `(exception_type, status)` for all six cases.

**Exit condition:** met — 12/12 backend tests pass, including both of the above.

#### Phase 8 — Money Graph and remaining pages — IN PROGRESS

Priority order within the phase, per the original plan:

1. **Money Graph** — DONE. Hand-rolled SVG (no new dependency) rendering `/api/cases/<id>/evidence-graph/` per case, reachable from the sidebar and a case-detail link. Solid edges = exact match; dashed = sub-1.0 confidence. Clicking a node opens the evidence drawer.
2. **Audit Log** — DONE. `/api/audit-log/` merges `AgentRun` and `EvidenceConnection` rows into one chronological, filterable feed — no new model, per the plan's "almost free" framing.
3. **Connections** — NEXT. A page listing source systems with health status, reading `FinancialDataSource` + last `FinancialRecord.ingested_at` per source.
4. **Rule Studio** — after Connections. Read-only list of the engine's checks with their formulas (no rule editing).
5. **AI Investigator (cross-case)** — after Rule Studio. A cross-case view of `AgentRun` history.
6. **Search (B7) / avatar (B8)** — wire minimally or remove, last in the phase.

The dashboard money-movement strip (B9) folding in the connected-path visual is deferred within this phase until the above are done, per the plan's stated priority order.

**If time runs out:** Money Graph and Audit Log are already built; the rest can stay labelled "planned" rather than becoming inert — this is already true today.

#### Phase 9 — submission prep — NOT STARTED

- **README** — problem in 3–4 sentences, architecture diagram, the code-verifies/AI-explains principle, how to run (clone → migrate → seed → runserver), honest "what's stubbed vs real" section.
- **Architecture diagram** — the layer/dependency diagram from section 2.
- **Demo recording** — 60–90 seconds: dashboard → open the settlement-short case → click an evidence chip to show the source record → ask the agent → it says the evidence is insufficient → Money Graph. End on the insufficient-evidence moment.
- **Trim the concept doc** — cut to a half-page in the README. Drop pitch-filler sections and the expansion roadmap.

### 4. Open decisions

| # | Decision | Chosen |
|---|---|---|
| D1 | Multi-tenancy — `tenant_id` on SourceRecord/Case now, or single-merchant? | Included — `Organization` foreign key on every relevant model |
| D2 | Demo volume — ~200 seeded records, or match the mockup's 1,248? | ~200 (216 seeded) |
| D3 | CSV upload in the UI, or seed-command only? | Seed command; upload button not built |
| D4 | Batched settlements (many payments → one settlement)? | Not yet implemented — matcher is 1:1 sequential only |
| D5 | Real Django auth or hardcoded demo user? | Hardcoded demo user ("Neha Sharma") |
| D6 | Money storage — rupees with 4 decimals, or integer paise? | Integer paise (`amount_minor` fields) |

### 5. Sequencing summary

| Phase | Output | Status |
|---|---|---|
| 1 | Canonical models | Done |
| 2 | Six seeded scenarios | Done |
| 3 | Link table + matcher | Done |
| 4 | Engine + Cases + tests | Done |
| 5 | Agent loop + AgentRun | Done |
| 6 | API + frontend wired to real data | Done |
| 7 | Tests, error/empty/loading states | Done |
| 8 | Money Graph + remaining pages | In progress (Money Graph, Audit Log done; Connections, Rule Studio, cross-case AI Investigator, search/avatar remain) |
| 9 | README, diagram, recording | Not started |

**Minimum credible submission:** Phases 1–6 + 9 — 1–6 already true; Phase 9 is the fastest remaining path to a submittable state.
**Strong submission:** all nine phases.
**Working order:** phases are followed in numeric sequence — do not start a later phase's remaining items before an earlier phase's checklist is fully verified against the code, not just assumed done.

---

## Background: target-system architecture narrative

The sections below describe the long-run target system in prose form. They predate the active build plan above and are not the day-to-day tracker — `status.md` and the "Active build plan" section are the source of truth for what's actually being worked on next.

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
- Validate model output against a schema; reject unsupported claims and show "insufficient evidence" when necessary.

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
