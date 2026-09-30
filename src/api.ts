export type CaseStatus = "matched" | "needs_review" | "insufficient_evidence" | "open"

export type FinancialRecord = {
  id: number
  external_record_id: string
  record_type: string
  entity_id: string
  amount_minor: number
  currency: string
  occurred_at: string
  status: string
  source_name: string
  reference: string
  batch_id: string
  ingested_at: string
  normalization_version: string
  content_hash: string
  normalized_hash: string
  raw_payload: Record<string, unknown>
}

export type ReconciliationCaseSummary = {
  public_id: string
  case_reference: string
  entity_id: string
  exception_type: string
  status: CaseStatus
  currency: string
  expected_amount_minor: number
  actual_amount_minor: number
  difference_minor: number
  amounts_known: boolean
  owner: string
  opened_at: string
}

export type CheckResult = {
  check_name: string
  result: "passed" | "failed" | "waiting"
  evidence: string[]
  details: string
  ran_at: string
}

export type EvidenceConnection = {
  sequence_number: number
  match_method: string
  confidence: string
  rationale: Record<string, unknown>
  is_verified: boolean
  source: FinancialRecord
  destination: FinancialRecord
}

export type AgentRun = {
  id: number
  question: string
  conclusion: string
  recommended_action: string
  confidence: string
  evidence_cited: string[]
  sufficient_evidence: boolean
  model_version: string
  created_at: string
}

export type ReconciliationCaseDetail = ReconciliationCaseSummary & {
  first_break_record: FinancialRecord | null
  check_results: CheckResult[]
  evidence_connections: EvidenceConnection[]
  agent_runs: AgentRun[]
}

export type EvidenceGraphEdge = {
  id: number
  source: number
  target: number
  method: string
  confidence: string
  rationale: Record<string, unknown>
  created_by: string
}

export type EvidenceGraph = {
  nodes: FinancialRecord[]
  edges: EvidenceGraphEdge[]
}

export type AuditLogEntry = {
  event_type: string
  occurred_at: string
  case_reference: string
  case_public_id: string
  actor: string
  summary: string
  details: Record<string, unknown>
}

export type OverviewMetrics = {
  currency: string
  source_count: number
  fresh_source_count: number
  captured_amount_minor: number
  case_count: number
  matched_case_count: number
  open_case_count: number
  unexplained_amount_minor: number
  movement: Array<{
    record_type: string
    label: string
    record_count: number
    amount_minor: number
  }>
}

const ORGANIZATION_SLUG = import.meta.env.VITE_ORGANIZATION_SLUG || "ledgerlens-demo"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const csrfToken = document.cookie.split("; ").find((cookie) => cookie.startsWith("csrftoken="))?.slice(10)
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Organization-Slug": ORGANIZATION_SLUG,
      ...(csrfToken ? { "X-CSRFToken": decodeURIComponent(csrfToken) } : {}),
      ...options?.headers,
    },
  })
  if (!response.ok) {
    if (response.status === 401) throw new Error("Sign in through /api/auth/login/ or enable the local demo explicitly.")
    throw new Error(`LedgerLens API request failed with status ${response.status}.`)
  }
  return response.json() as Promise<T>
}

export function getCases() {
  return request<ReconciliationCaseSummary[]>("/api/cases/")
}

export function getCase(publicId: string) {
  return request<ReconciliationCaseDetail>(`/api/cases/${publicId}/`)
}

export function getOverviewMetrics() {
  return request<OverviewMetrics>("/api/metrics/overview/")
}

export function getRecord(recordId: number) {
  return request<FinancialRecord>(`/api/records/${recordId}/`)
}

export function assignCase(publicId: string) {
  return request<ReconciliationCaseDetail>(`/api/cases/${publicId}/assign/`, {
    method: "POST",
    body: JSON.stringify({}),
  })
}

export function askInvestigator(publicId: string, question: string) {
  return request<AgentRun>(`/api/cases/${publicId}/ask/`, {
    method: "POST",
    body: JSON.stringify({ question }),
  })
}

export function getEvidenceGraph(publicId: string) {
  return request<EvidenceGraph>(`/api/cases/${publicId}/evidence-graph/`)
}

export function getAuditLog() {
  return request<AuditLogEntry[]>("/api/audit-log/")
}

export function getIdentity() {
  return request<{ organization: string; name: string; role: string }>("/api/identity/")
}
