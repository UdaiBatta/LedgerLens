import { lazy, Suspense, useEffect, useMemo, useState } from "react"
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BadgeIndianRupee,
  Banknote,
  BookOpenCheck,
  Bot,
  Building2,
  Check,
  ChevronRight,
  CircleDollarSign,
  CreditCard,
  ExternalLink,
  FileCheck2,
  Code2,
  Landmark,
  Link2,
  Menu,
  Network,
  ReceiptText,
  Search,
  Share2,
  ShieldCheck,
  ShoppingCart,
  SlidersHorizontal,
  UserPlus,
  X,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Features } from "@/components/ui/features-6"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  askInvestigator,
  assignCase,
  getAuditLog,
  getCase,
  getCases,
  getEvidenceGraph,
  getOverviewMetrics,
  type AuditLogEntry,
  type EvidenceGraph,
  type FinancialRecord,
  type OverviewMetrics,
  type ReconciliationCaseDetail,
  type ReconciliationCaseSummary,
} from "@/api"

const CRTWarp = lazy(() => import("@/components/CRTWarp"))

type Screen = "landing" | "dashboard" | "case" | "moneyGraph" | "auditLog"

function formatMoney(amountMinor: number, currency = "INR") {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(amountMinor / 100)
}

function readableLabel(value: string) {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase())
}

const appNav = [
  ["Overview", CircleDollarSign],
  ["Money Graph", Network],
  ["Exceptions", AlertTriangle],
  ["AI Investigator", Bot],
  ["Rule Studio", SlidersHorizontal],
  ["Connections", Link2],
  ["Audit Log", BookOpenCheck],
] as const

function useReducedMotion() {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setReduced(media.matches)
    update()
    media.addEventListener("change", update)
    return () => media.removeEventListener("change", update)
  }, [])

  return reduced
}

function Brand({ inverse = false }: { inverse?: boolean }) {
  return (
    <span className={`brand ${inverse ? "brand--inverse" : ""}`}>
      <span className="brand__mark" aria-hidden="true"><i /><i /><i /></span>
      LedgerLens
    </span>
  )
}

function Landing({ openDashboard }: { openDashboard: () => void }) {
  const reducedMotion = useReducedMotion()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <main className="landing">
      <a className="skip-link" href="#hero-copy">Skip to content</a>
      <section className="hero">
        <div className="hero__background" aria-hidden="true">
          {reducedMotion ? <div className="hero__fallback" /> : (
            <Suspense fallback={<div className="hero__fallback" />}>
              <CRTWarp
                color="#c755f7"
                backgroundColor="#07080c"
                speed={0.55}
                curvature={0.08}
                scanlineStrength={0.28}
                scanlineFrequency={130}
                waveAmplitude={0.29}
                waveFrequency={4.8}
                bloom={0.65}
                bloomRadius={1.8}
                noise={0.015}
                vignette={0}
                brightness={1.5}
                pixelation={1}
                rgbShift={0.023}
                mouseReact
                mouseStrength={1.05}
                dpr={0.75}
                fps={60}
              />
            </Suspense>
          )}
        </div>
        <div className="hero__veil" aria-hidden="true" />

        <nav className="marketing-nav" aria-label="Primary navigation">
          <Brand inverse />
          <div className="marketing-nav__links">
            <a href="#product">Product</a>
            <a href="#how-it-works">How it works</a>
            <a href="#safety">Safety</a>
            <a href="https://github.com/UdaiBatta/LedgerLens" target="_blank" rel="noreferrer">GitHub <ExternalLink aria-hidden="true" /></a>
          </div>
          <Button className="marketing-nav__action" onClick={openDashboard}>Open app</Button>
          <button className="menu-toggle" onClick={() => setMenuOpen((value) => !value)} aria-expanded={menuOpen} aria-label={menuOpen ? "Close navigation" : "Open navigation"}>{menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}</button>
          {menuOpen ? <div className="mobile-menu"><a href="#product">Product</a><a href="#how-it-works">How it works</a><a href="#safety">Safety</a><button onClick={openDashboard}>Open app</button></div> : null}
        </nav>

        <div className="hero__layout" id="hero-copy">
          <div className="hero__copy">
            <h1>Trace every rupee.<br /><span>Explain</span> every difference.</h1>
            <p>LedgerLens connects orders, gateways, settlements, bank credits, and ledgers—then shows where the story stops matching.</p>
            <div className="hero__actions">
              <Button size="lg" onClick={openDashboard}>Open the dashboard <ArrowRight data-icon="inline-end" aria-hidden="true" /></Button>
              <a href="#how-it-works">See how it works <ArrowRight aria-hidden="true" /></a>
            </div>
          </div>
          <HeroTrace openDashboard={openDashboard} />
        </div>
      </section>
      <div id="product"><Features onExplore={openDashboard} /></div>
      <section className="safety-band" id="safety"><ShieldCheck aria-hidden="true" /><div><h2>Evidence first. AI second.</h2><p>Rules calculate, compare, and verify. AI reads those results to explain the likely cause and suggest a safe next step.</p></div><Button variant="outline" onClick={openDashboard}>Inspect the demo</Button></section>
    </main>
  )
}

function HeroTrace({ openDashboard }: { openDashboard: () => void }) {
  const sources = [
    { label: "Order", reference: "ORD-88451234", amount: "₹10,000.00", time: "15 May 2025 10:21:33", Icon: ShoppingCart },
    { label: "Gateway", reference: "PAY-33117890", amount: "₹10,000.00", time: "15 May 2025 10:21:35", Icon: CreditCard },
    { label: "Settlement", reference: "SET-55667788", amount: "₹9,858.40", time: "15 May 2025 10:22:41", Icon: Landmark },
    { label: "Bank", reference: "TXN-11223344", amount: "₹9,855.00", time: "15 May 2025 10:45:12", Icon: Building2 },
    { label: "Ledger", reference: "JE-9088771", amount: "₹9,855.00", time: "15 May 2025 11:02:03", Icon: ReceiptText },
  ] as const
  const [selectedSource, setSelectedSource] = useState(3)
  const [copied, setCopied] = useState(false)

  async function copyTraceLink() {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/#app`)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="hero-trace" aria-label="LedgerLens transaction evidence preview">
      <header>
        <div><code>Investigation #INV-2025-05-19-0001</code><span className="hero-trace__open"><i aria-hidden="true" />Open</span></div>
        <button className="hero-trace__share" onClick={copyTraceLink}><Share2 aria-hidden="true" />{copied ? "Copied" : "Share"}</button>
      </header>
      <div className="hero-trace__body">
        <div className="hero-trace__sources">{sources.map(({ label, reference, amount, time, Icon }, index) => <button key={label} className={selectedSource === index ? "selected" : ""} onClick={() => setSelectedSource(index)} aria-pressed={selectedSource === index}><span className="hero-trace__source-icon"><Icon aria-hidden="true" /></span><span><strong>{label}</strong><code>{reference}</code><code>{amount}</code><small>{time}</small></span><b aria-hidden="true" /></button>)}</div>
        <div className="hero-trace__graph" aria-hidden="true">
          <svg viewBox="0 0 150 410" preserveAspectRatio="none">
            {[45, 125, 205, 285, 365].map((y, index) => <path key={y} className={selectedSource === index ? "selected" : ""} d={`M 0 ${y} C 70 ${y}, 62 205, 125 205`} />)}
            <path className="hero-trace__output" d="M 125 205 L 150 205" />
          </svg>
          <i className="hero-trace__node" />
        </div>
        <div className="hero-trace__finding">
          <header><strong>Evidence path</strong><span><AlertTriangle aria-hidden="true" />Difference found</span></header>
          <dl>
            <div><dt>Trace ID</dt><dd>TRC-7F3A9C2D</dd></div>
            <div><dt>Expected</dt><dd>₹9,858.40</dd></div>
            <div><dt>Bank credit</dt><dd>₹9,855.00</dd></div>
            <div><dt>First break</dt><dd>{sources[selectedSource].label}</dd></div>
            <div><dt>Difference</dt><dd className="hero-trace__difference">−₹3.40</dd></div>
            <div><dt>Status</dt><dd className="hero-trace__status">Needs review</dd></div>
          </dl>
          <p><span>AI note</span>No fee, tax, refund, or adjustment record explains the difference.</p>
          <button onClick={openDashboard}>View full timeline <ChevronRight aria-hidden="true" /></button>
        </div>
      </div>
    </div>
  )
}

function AppShell({ active, children, goLanding, goDashboard, goMoneyGraph, goAuditLog }: { active: string; children: React.ReactNode; goLanding: () => void; goDashboard: () => void; goMoneyGraph?: () => void; goAuditLog?: () => void }) {
  const enabledLabels = new Set([
    "Overview",
    "Exceptions",
    ...(goMoneyGraph ? ["Money Graph"] : []),
    ...(goAuditLog ? ["Audit Log"] : []),
  ])
  const navigationHandlers: Record<string, () => void> = {
    Overview: goDashboard,
    Exceptions: goDashboard,
    ...(goMoneyGraph ? { "Money Graph": goMoneyGraph } : {}),
    ...(goAuditLog ? { "Audit Log": goAuditLog } : {}),
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <aside className="app-sidebar">
        <button className="app-sidebar__brand" onClick={goLanding} aria-label="Go to LedgerLens landing page"><Brand inverse /></button>
        <div className="workspace-switcher"><small>Workspace</small><strong>Acme FinOps</strong><span>Demo data</span></div>
        <nav aria-label="Application navigation">{appNav.map(([label, Icon]) => { const enabled = enabledLabels.has(label); return <button key={label} className={label === active ? "active" : ""} aria-current={label === active ? "page" : undefined} aria-disabled={!enabled} title={enabled ? undefined : "Planned after the investigation workflow"} onClick={enabled ? navigationHandlers[label] : undefined}><Icon aria-hidden="true" />{label}</button> })}</nav>
        <a className="repo-link" href="https://github.com/UdaiBatta/LedgerLens" target="_blank" rel="noreferrer"><Code2 aria-hidden="true" />View repository</a>
      </aside>
      <div className="app-workspace">
        <header className="app-topbar"><button className="mobile-logo" onClick={goLanding}><Brand /></button><label className="search-box"><Search aria-hidden="true" /><span className="sr-only">Search</span><input type="search" placeholder="Search ID, amount, reference, or entity" /></label><div className="operator"><span>NS</span><div><strong>Neha Sharma</strong><small>Finance operator</small></div></div></header>
        {children}
      </div>
    </div>
  )
}

function Dashboard({ goLanding, openCase, goMoneyGraph, goAuditLog }: { goLanding: () => void; openCase: (publicId: string) => void; goMoneyGraph: (publicId: string) => void; goAuditLog: () => void }) {
  const [filter, setFilter] = useState("All")
  const [cases, setCases] = useState<ReconciliationCaseSummary[]>([])
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    Promise.all([getCases(), getOverviewMetrics()])
      .then(([loadedCases, loadedMetrics]) => {
        setCases(loadedCases)
        setMetrics(loadedMetrics)
      })
      .catch((requestError: Error) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  const filteredCases = useMemo(() => {
    if (filter === "All") return cases
    return cases.filter((item) => readableLabel(item.status) === filter)
  }, [cases, filter])
  const firstCaseId = cases.find((item) => item.status !== "matched")?.public_id

  return (
    <AppShell active="Overview" goLanding={goLanding} goDashboard={() => undefined} goMoneyGraph={firstCaseId ? () => goMoneyGraph(firstCaseId) : undefined} goAuditLog={goAuditLog}>
      <main className="dashboard" id="main-content">
        <header className="dashboard__heading"><div><p>Reconciliation overview</p><h1>Financial truth, in one place.</h1><span>Live data from the Django reconciliation API</span></div><Button onClick={() => firstCaseId && openCase(firstCaseId)} disabled={!firstCaseId}>Review exceptions <ArrowRight data-icon="inline-end" aria-hidden="true" /></Button></header>
        {loading ? <p className="api-state" role="status">Loading reconciliation data…</p> : null}
        {error ? <p className="api-state api-state--error" role="alert">{error} Start Django on port 8000 and seed the demo cases.</p> : null}
        {metrics ? <section className="metric-rail" aria-label="Reconciliation summary"><div><span>Captured value</span><strong>{formatMoney(metrics.captured_amount_minor)}</strong><small>{metrics.movement.find((stage) => stage.record_type === "payment")?.record_count ?? 0} payment records</small></div><div><span>Unexplained value</span><strong>{formatMoney(metrics.unexplained_amount_minor)}</strong><small>Across {metrics.open_case_count} open cases</small></div><div><span>Matched cases</span><strong>{metrics.matched_case_count} / {metrics.case_count}</strong><small>Generated by deterministic rules</small></div><div><span>Source health</span><strong>4 / 4</strong><small>Demo sources connected</small></div></section> : null}
        <section className="dashboard-grid">
          <EvidenceTrail publicId={firstCaseId} casesLoading={loading} openCase={() => firstCaseId && openCase(firstCaseId)} openGraph={() => firstCaseId && goMoneyGraph(firstCaseId)} />
          <Briefing cases={cases} openCase={() => firstCaseId && openCase(firstCaseId)} />
        </section>
        <Exceptions rows={filteredCases} filter={filter} setFilter={setFilter} openCase={openCase} />
      </main>
    </AppShell>
  )
}

const TRAIL_CHECKPOINT_LABELS: Record<string, string> = {
  order: "Customer intent",
  payment: "Gateway confirmed",
  fee: "Processing fee",
  tax: "Tax on fee",
  refund: "Refund issued",
  settlement: "Net after fees + tax",
  bank_credit: "Bank credit",
  ledger_entry: "Posted amount",
}

function EvidenceTrail({ publicId, casesLoading, openCase, openGraph }: { publicId?: string; casesLoading: boolean; openCase: () => void; openGraph: () => void }) {
  const [reconciliationCase, setReconciliationCase] = useState<ReconciliationCaseDetail | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!publicId) return
    setError("")
    getCase(publicId)
      .then(setReconciliationCase)
      .catch((requestError: Error) => setError(requestError.message))
  }, [publicId])

  const checkpoints = useMemo(() => {
    if (!reconciliationCase?.evidence_connections.length) return []
    const uniqueRecordsById = new Map<number, FinancialRecord>()
    for (const connection of reconciliationCase.evidence_connections) {
      uniqueRecordsById.set(connection.source.id, connection.source)
      uniqueRecordsById.set(connection.destination.id, connection.destination)
    }
    return [...uniqueRecordsById.values()]
      .filter((record) => !["fee", "tax"].includes(record.record_type))
      .sort((first, second) => new Date(first.occurred_at).getTime() - new Date(second.occurred_at).getTime())
  }, [reconciliationCase])

  const breakRecordId = reconciliationCase?.first_break_record?.id
  const breakIndex = checkpoints.findIndex((record) => record.id === breakRecordId)
  const difference = reconciliationCase?.difference_minor ?? 0
  const currency = reconciliationCase?.currency ?? "INR"

  return (
    <article className="trace-panel">
      <header className="trace-panel__bar">
        <div className="trace-panel__id"><i aria-hidden="true" /><i aria-hidden="true" /><i aria-hidden="true" /><span>TRACE</span>{reconciliationCase ? <code>{reconciliationCase.entity_id}</code> : null}</div>
        <div className="trace-panel__meta">{checkpoints.length ? <span>{checkpoints.length} checkpoints</span> : null}{breakIndex >= 0 ? <span className="trace-panel__flag"><i aria-hidden="true" />1 divergence</span> : null}</div>
      </header>
      {error ? <p className="api-state api-state--error" role="alert">{error}</p> : null}
      {casesLoading || (publicId && !reconciliationCase && !error) ? <p className="api-state" role="status">Loading evidence trail…</p> : null}
      {!casesLoading && !publicId && !error ? <p className="api-state">Every case is matched. No divergence to trace.</p> : null}
      {reconciliationCase ? <>
        <div className="trace-summary">
          <div><span>Expected settlement</span><strong>{formatMoney(reconciliationCase.expected_amount_minor, currency)}</strong></div>
          <div><span>{readableLabel(reconciliationCase.first_break_record?.record_type ?? "actual")}</span><strong>{formatMoney(reconciliationCase.actual_amount_minor, currency)}</strong></div>
          <div className="trace-summary__variance"><span>Unexplained variance</span><strong>{difference < 0 ? "−" : "+"}{formatMoney(Math.abs(difference), currency)}</strong></div>
        </div>
        <ol className="trace-flow">
          {checkpoints.map((record, index) => {
            const isBreak = record.id === breakRecordId
            const previous = checkpoints[index - 1]
            const linkIsBreak = isBreak && previous
            return (
              <li key={record.id}>
                {previous ? <span className={`trace-link ${linkIsBreak ? "trace-link--broken" : ""}`} aria-hidden="true"><b>{linkIsBreak ? `${difference < 0 ? "−" : "+"}${formatMoney(Math.abs(difference), currency)}` : "MATCHED"}</b></span> : null}
                <button className={`trace-card ${isBreak ? "trace-card--break" : ""}`} onClick={openCase}>
                  <header><small>{String(index + 1).padStart(2, "0")}</small><span>{readableLabel(record.record_type)}</span></header>
                  <strong>{formatMoney(record.amount_minor, record.currency)}</strong>
                  <code>{record.external_record_id}</code>
                  <em><i aria-hidden="true" />{isBreak ? "First break" : TRAIL_CHECKPOINT_LABELS[record.record_type] ?? "Verified source"}</em>
                </button>
              </li>
            )
          })}
        </ol>
        {breakIndex >= 0 ? (
          <div className="trace-break">
            <span>First break</span>
            <div>
              <strong>{readableLabel(reconciliationCase.first_break_record?.record_type ?? "Record")} is {formatMoney(Math.abs(difference), currency)} short.</strong>
              <p>The settlement is verified. LedgerLens carries this exact break into the evidence trail for investigation.</p>
            </div>
          </div>
        ) : null}
        <footer className="trace-panel__footer">
          <span><i className="ok" />Verified source</span>
          <span><i className="warn" />First divergence</span>
          <button onClick={openGraph}>Open evidence trail <ArrowRight aria-hidden="true" /></button>
        </footer>
      </> : null}
    </article>
  )
}

function Briefing({ cases, openCase }: { cases: ReconciliationCaseSummary[]; openCase: () => void }) {
  const exceptionCounts = cases.reduce<Record<string, number>>((counts, item) => {
    if (item.status !== "matched") counts[item.exception_type] = (counts[item.exception_type] ?? 0) + 1
    return counts
  }, {})
  return (
    <aside className="briefing">
      <header><div><Bot aria-hidden="true" /><span>Evidence briefing</span></div><Badge>Rule grounded</Badge></header>
      <h2>{cases.filter((item) => item.status !== "matched").length} cases need a human decision.</h2>
      <p>Deterministic rules grouped the exceptions by their first divergence.</p>
      <ol>{Object.entries(exceptionCounts).slice(0, 3).map(([exceptionType, count]) => <li key={exceptionType}><span>{count}</span><div><strong>{readableLabel(exceptionType)}</strong><p>Open the case to inspect checks and source evidence.</p></div></li>)}</ol>
      <button onClick={openCase}>Review the highest-risk case <ArrowRight aria-hidden="true" /></button>
      <small><ShieldCheck aria-hidden="true" />No actions or money movements were performed.</small>
    </aside>
  )
}

function Exceptions({ rows, filter, setFilter, openCase }: { rows: ReconciliationCaseSummary[]; filter: string; setFilter: (value: string) => void; openCase: (publicId: string) => void }) {
  return (
    <section className="exceptions-panel">
      <header><div><h2>Exceptions</h2><span>Generated from records and deterministic checks</span></div><div className="filters" aria-label="Filter exception status">{["All", "Needs review", "Insufficient evidence", "Matched"].map((item) => <button key={item} onClick={() => setFilter(item)} className={filter === item ? "active" : ""} aria-pressed={filter === item}>{item}</button>)}</div></header>
      {rows.length === 0 ? <p className="api-state">No reconciliation cases match this filter.</p> : <Table><TableHeader><TableRow><TableHead>Case</TableHead><TableHead>Type</TableHead><TableHead>Entity</TableHead><TableHead>Expected</TableHead><TableHead>Variance</TableHead><TableHead>Status</TableHead><TableHead>Owner</TableHead><TableHead><span className="sr-only">Open</span></TableHead></TableRow></TableHeader><TableBody>{rows.map((row, index) => <TableRow key={row.public_id} className={index === 0 ? "priority-row" : ""}><TableCell><button className="case-id" onClick={() => openCase(row.public_id)}>{row.case_reference}</button></TableCell><TableCell>{readableLabel(row.exception_type)}</TableCell><TableCell>{row.entity_id}</TableCell><TableCell className="money">{formatMoney(row.expected_amount_minor, row.currency)}</TableCell><TableCell className="money">{formatMoney(row.difference_minor, row.currency)}</TableCell><TableCell><span className={`status status--${readableLabel(row.status).toLowerCase().replace(" ", "-")}`}>{readableLabel(row.status)}</span></TableCell><TableCell>{row.owner || "Unassigned"}</TableCell><TableCell><button className="row-open" onClick={() => openCase(row.public_id)} aria-label={`Open ${row.case_reference}`}><ChevronRight aria-hidden="true" /></button></TableCell></TableRow>)}</TableBody></Table>}
    </section>
  )
}

function CaseDetail({ publicId, goLanding, goDashboard, goMoneyGraph, goAuditLog }: { publicId: string; goLanding: () => void; goDashboard: () => void; goMoneyGraph: (publicId: string) => void; goAuditLog: () => void }) {
  const [reconciliationCase, setReconciliationCase] = useState<ReconciliationCaseDetail | null>(null)
  const [selectedRecord, setSelectedRecord] = useState<FinancialRecord | null>(null)
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(Boolean(publicId))
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState(publicId ? "" : "No reconciliation case was selected.")

  useEffect(() => {
    if (!publicId) {
      return
    }
    getCase(publicId)
      .then(setReconciliationCase)
      .catch((requestError: Error) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [publicId])

  const pathRecords = useMemo(() => {
    if (!reconciliationCase?.evidence_connections.length) return []
    const uniqueRecordsById = new Map<number, FinancialRecord>()
    for (const connection of reconciliationCase.evidence_connections) {
      uniqueRecordsById.set(connection.source.id, connection.source)
      uniqueRecordsById.set(connection.destination.id, connection.destination)
    }
    return [...uniqueRecordsById.values()].sort(
      (first, second) => new Date(first.occurred_at).getTime() - new Date(second.occurred_at).getTime(),
    )
  }, [reconciliationCase])

  const paymentCount = useMemo(
    () => pathRecords.filter((record) => record.record_type === "payment").length,
    [pathRecords],
  )
  const isBatchedCase = paymentCount > 1

  async function assignToMe() {
    if (!reconciliationCase) return
    try {
      setReconciliationCase(await assignCase(reconciliationCase.public_id, "Neha Sharma"))
    } catch (requestError) {
      setError((requestError as Error).message)
    }
  }

  async function ask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const submittedQuestion = question.trim()
    if (!submittedQuestion || !reconciliationCase || asking) return
    setQuestion("")
    setAsking(true)
    try {
      const agentRun = await askInvestigator(reconciliationCase.public_id, submittedQuestion)
      setReconciliationCase({
        ...reconciliationCase,
        agent_runs: [...reconciliationCase.agent_runs, agentRun],
      })
    } catch (requestError) {
      setError((requestError as Error).message)
    } finally {
      setAsking(false)
    }
  }

  const latestRun = reconciliationCase?.agent_runs[reconciliationCase.agent_runs.length - 1]
  const passedChecks = reconciliationCase?.check_results.filter((check) => check.result === "passed").length ?? 0

  return (
    <AppShell active="Exceptions" goLanding={goLanding} goDashboard={goDashboard} goMoneyGraph={() => goMoneyGraph(publicId)} goAuditLog={goAuditLog}>
      <main className="case-page" id="main-content">
        <button className="back-button" onClick={goDashboard}><ArrowLeft aria-hidden="true" />Back to overview</button>
        {loading ? <p className="api-state" role="status">Loading investigation…</p> : null}
        {error ? <p className="api-state api-state--error" role="alert">{error}</p> : null}
        {reconciliationCase ? <>
          <header className="case-heading"><div><div><h1>{readableLabel(reconciliationCase.exception_type)} · {formatMoney(Math.abs(reconciliationCase.difference_minor), reconciliationCase.currency)}</h1><span className={`status status--${readableLabel(reconciliationCase.status).toLowerCase().replace(" ", "-")}`}>{readableLabel(reconciliationCase.status)}</span></div><p><code>{reconciliationCase.case_reference}</code> · {reconciliationCase.entity_id}</p></div><Button onClick={assignToMe} disabled={reconciliationCase.owner === "Neha Sharma"}>{reconciliationCase.owner === "Neha Sharma" ? <Check data-icon="inline-start" aria-hidden="true" /> : <UserPlus data-icon="inline-start" aria-hidden="true" />}{reconciliationCase.owner === "Neha Sharma" ? "Assigned to you" : "Assign case"}</Button></header>
          <section className="case-layout">
            <article className="case-path"><header><span>Transaction path</span><button className="open-graph-link" onClick={() => goMoneyGraph(publicId)}><Network aria-hidden="true" />Open money graph</button></header>{isBatchedCase ? <div className="case-path__batched-notice"><Network aria-hidden="true" /><p><strong>This case has {paymentCount} payments settling together.</strong>Its evidence forms a graph, not a single line — open the money graph to see how every record connects.</p><button onClick={() => goMoneyGraph(publicId)}>Open money graph<ArrowRight aria-hidden="true" /></button></div> : <ol>{pathRecords.map((record, index) => { const icons = [FileCheck2, BadgeIndianRupee, Banknote, BadgeIndianRupee, Landmark, Building2, ReceiptText]; const Icon = icons[index % icons.length]; const isBreak = record.id === reconciliationCase.first_break_record?.id; const isAdjustment = ["fee", "tax", "refund"].includes(record.record_type); const state = isBreak ? "mismatch" : isAdjustment ? "fee" : "verified"; return <li className={`case-path__step case-path__step--${state}`} key={record.id}><button className={state} onClick={() => setSelectedRecord(record)}><span><Icon aria-hidden="true" /></span><div><strong>{readableLabel(record.record_type)}</strong><code>{record.external_record_id}</code><small>{new Date(record.occurred_at).toLocaleString("en-IN")}</small><em>{isBreak ? "First divergence" : isAdjustment ? "Derived adjustment" : "Verified source"}</em></div><b>{formatMoney(record.amount_minor, record.currency)}</b></button></li>})}</ol>}{reconciliationCase.first_break_record ? <div className="case-path__alert"><AlertTriangle aria-hidden="true" /><p><strong>First divergence</strong>Actual differs from expected by {formatMoney(Math.abs(reconciliationCase.difference_minor), reconciliationCase.currency)}. Select any record to inspect its source payload.</p></div> : null}</article>
            <article className="case-finding"><header><div><Bot aria-hidden="true" /><span>AI Investigator</span></div><Badge>{latestRun ? `${Math.round(Number(latestRun.confidence) * 100)}% confidence` : "Ready"}</Badge></header><p className="case-finding__meta">Based on {reconciliationCase.check_results.length} deterministic checks and cited source records</p><h2>{latestRun?.conclusion ?? "Ask a question after reviewing the deterministic evidence."}</h2>{latestRun ? <><div className="citations">{latestRun.evidence_cited.map((reference) => <button key={reference} onClick={() => setSelectedRecord(pathRecords.find((record) => record.external_record_id === reference) ?? null)}>{reference}</button>)}</div><section><h3>Recommended next action</h3><p>{latestRun.recommended_action}</p></section></> : null}<div className="agent-history">{reconciliationCase.agent_runs.map((run) => <article key={run.id}><strong>{run.question}</strong><p>{run.conclusion}</p><small>{run.model_version}</small></article>)}</div><form onSubmit={ask}><label htmlFor="investigator-question">Ask about this case</label><div><input id="investigator-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Why is this case still open?" disabled={asking} /><button type="submit" aria-label="Ask AI Investigator" disabled={asking}>{asking ? "…" : <ArrowRight aria-hidden="true" />}</button></div></form><small><ShieldCheck aria-hidden="true" />Analysis only. No source records or money movements were changed.</small></article>
          </section>
          <section className="checks-section"><header><div><h2>Checks and evidence</h2><span>Deterministic output supplied to the AI investigator</span></div><Badge variant="outline">{passedChecks} passed · {reconciliationCase.check_results.length - passedChecks} unresolved</Badge></header><Table><TableHeader><TableRow><TableHead>Check</TableHead><TableHead>Result</TableHead><TableHead>Evidence</TableHead></TableRow></TableHeader><TableBody>{reconciliationCase.check_results.map((item) => <TableRow key={item.check_name}><TableCell>{item.check_name}</TableCell><TableCell><span className={`check check--${item.result}`}>{item.result === "passed" ? <Check aria-hidden="true" /> : <AlertTriangle aria-hidden="true" />}{readableLabel(item.result)}</span></TableCell><TableCell><div className="evidence-buttons">{item.evidence.map((reference) => <button key={reference} onClick={() => setSelectedRecord(pathRecords.find((record) => record.external_record_id === reference) ?? null)}>{reference}</button>)}</div></TableCell></TableRow>)}</TableBody></Table></section>
        </> : null}
      </main>
      <Sheet open={Boolean(selectedRecord)} onOpenChange={(open) => { if (!open) setSelectedRecord(null) }}>
        <SheetContent className="evidence-sheet">
          <SheetHeader><SheetTitle>Source evidence</SheetTitle><SheetDescription>Immutable record received from {selectedRecord?.source_name}.</SheetDescription></SheetHeader>
          {selectedRecord ? <div className="evidence-sheet__body"><dl><div><dt>Reference</dt><dd>{selectedRecord.external_record_id}</dd></div><div><dt>Type</dt><dd>{readableLabel(selectedRecord.record_type)}</dd></div><div><dt>Amount</dt><dd>{formatMoney(selectedRecord.amount_minor, selectedRecord.currency)}</dd></div><div><dt>Occurred</dt><dd>{new Date(selectedRecord.occurred_at).toLocaleString("en-IN")}</dd></div></dl><h3>Raw source payload</h3><pre>{JSON.stringify(selectedRecord.raw_payload, null, 2)}</pre></div> : null}
        </SheetContent>
      </Sheet>
    </AppShell>
  )
}

const GRAPH_NODE_WIDTH = 168
const GRAPH_NODE_HEIGHT = 104
const GRAPH_SPACING = 232
const GRAPH_PADDING = 96
const GRAPH_ROW_Y = 92
const GRAPH_HEIGHT = 184

function MoneyGraphPage({ publicId, goLanding, goDashboard, goCase, goAuditLog }: { publicId: string; goLanding: () => void; goDashboard: () => void; goCase: (publicId: string) => void; goAuditLog: () => void }) {
  const [evidenceGraph, setEvidenceGraph] = useState<EvidenceGraph | null>(null)
  const [reconciliationCase, setReconciliationCase] = useState<ReconciliationCaseDetail | null>(null)
  const [selectedRecord, setSelectedRecord] = useState<FinancialRecord | null>(null)
  const [loading, setLoading] = useState(Boolean(publicId))
  const [error, setError] = useState(publicId ? "" : "No reconciliation case was selected.")

  useEffect(() => {
    if (!publicId) {
      return
    }
    Promise.all([getEvidenceGraph(publicId), getCase(publicId)])
      .then(([loadedGraph, loadedCase]) => {
        setEvidenceGraph(loadedGraph)
        setReconciliationCase(loadedCase)
      })
      .catch((requestError: Error) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [publicId])

  const firstBreakRecordId = reconciliationCase?.first_break_record?.id

  const orderedNodes = useMemo(() => {
    if (!evidenceGraph) return []
    return [...evidenceGraph.nodes].sort(
      (first, second) => new Date(first.occurred_at).getTime() - new Date(second.occurred_at).getTime(),
    )
  }, [evidenceGraph])

  const nodePositionById = useMemo(() => {
    const positions = new Map<number, { x: number; y: number }>()
    orderedNodes.forEach((node, index) => {
      positions.set(node.id, { x: GRAPH_PADDING + index * GRAPH_SPACING, y: GRAPH_ROW_Y })
    })
    return positions
  }, [orderedNodes])

  const diagramWidth = Math.max(
    720,
    GRAPH_PADDING * 2 + Math.max(orderedNodes.length - 1, 0) * GRAPH_SPACING + GRAPH_NODE_WIDTH,
  )

  return (
    <AppShell active="Money Graph" goLanding={goLanding} goDashboard={goDashboard} goAuditLog={goAuditLog}>
      <main className="money-graph-page" id="main-content">
        <button className="back-button" onClick={() => goCase(publicId)}><ArrowLeft aria-hidden="true" />Back to case</button>
        {loading ? <p className="api-state" role="status">Loading evidence graph…</p> : null}
        {error ? <p className="api-state api-state--error" role="alert">{error}</p> : null}
        {evidenceGraph ? <>
          <header className="money-graph-page__heading">
            <div><span>Money graph</span><h1>How this case's records connect</h1><p>Every link was produced by the deterministic evidence matcher, never invented by the AI investigator.</p></div>
            {reconciliationCase ? <dl className="money-graph-page__facts"><div><dt>Case</dt><dd>{reconciliationCase.case_reference}</dd></div><div><dt>Entity</dt><dd>{reconciliationCase.entity_id}</dd></div><div><dt>Records</dt><dd>{evidenceGraph.nodes.length}</dd></div><div><dt>Links</dt><dd>{evidenceGraph.edges.length}</dd></div></dl> : null}
          </header>
          <div className="money-graph-legend"><span><i className="exact" />Exact reference match</span><span><i className="inferred" />Inferred match, below full confidence</span><span><i className="break" />First divergence</span></div>
          <div className="money-graph-diagram" role="img" aria-label="Diagram of financial records connected by evidence matches">
            <svg width={diagramWidth} height={GRAPH_HEIGHT} viewBox={`0 0 ${diagramWidth} ${GRAPH_HEIGHT}`}>
              <defs>
                <marker id="graph-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                  <path d="M 0 1 L 7 4 L 0 7" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                </marker>
              </defs>
              {evidenceGraph.edges.map((edge) => {
                const from = nodePositionById.get(edge.source)
                const to = nodePositionById.get(edge.target)
                if (!from || !to) return null
                const isExactMatch = Number(edge.confidence) >= 1
                const startX = from.x + GRAPH_NODE_WIDTH / 2
                const endX = to.x - GRAPH_NODE_WIDTH / 2
                const midX = (startX + endX) / 2
                const startY = from.y
                const endY = to.y
                const path = `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`
                return (
                  <g key={edge.id} className={`money-graph-edge ${isExactMatch ? "" : "money-graph-edge--inferred"}`}>
                    <path d={path} markerEnd="url(#graph-arrow)" />
                    <rect x={midX - 20} y={(startY + endY) / 2 - 9} width={40} height={18} rx={9} className="money-graph-edge__chip" />
                    <text x={midX} y={(startY + endY) / 2 + 3.5} textAnchor="middle" className="money-graph-edge__label">{Math.round(Number(edge.confidence) * 100)}%</text>
                  </g>
                )
              })}
              {orderedNodes.map((node, index) => {
                const position = nodePositionById.get(node.id)
                if (!position) return null
                const isBreak = node.id === firstBreakRecordId
                const left = position.x - GRAPH_NODE_WIDTH / 2
                const top = position.y - GRAPH_NODE_HEIGHT / 2
                return (
                  <g key={node.id} className={`money-graph-node ${isBreak ? "money-graph-node--break" : ""}`} onClick={() => setSelectedRecord(node)} role="button" tabIndex={0} aria-label={`${readableLabel(node.record_type)} ${node.external_record_id}`} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedRecord(node) } }}>
                    <rect x={left} y={top} width={GRAPH_NODE_WIDTH} height={GRAPH_NODE_HEIGHT} rx={12} className="money-graph-node__card" />
                    <rect x={left} y={top} width={GRAPH_NODE_WIDTH} height={3} rx={1.5} className="money-graph-node__accent" />
                    <text x={left + 14} y={top + 24} className="money-graph-node__index">{String(index + 1).padStart(2, "0")}</text>
                    <text x={left + GRAPH_NODE_WIDTH - 14} y={top + 24} textAnchor="end" className="money-graph-node__type">{readableLabel(node.record_type).toUpperCase()}</text>
                    <text x={left + 14} y={top + 50} className="money-graph-node__amount">{formatMoney(node.amount_minor, node.currency)}</text>
                    <text x={left + 14} y={top + 68} className="money-graph-node__reference">{node.external_record_id}</text>
                    <text x={left + 14} y={top + 86} className="money-graph-node__state">{isBreak ? "First break" : "Verified source"}</text>
                  </g>
                )
              })}
            </svg>
          </div>
          <section className="money-graph-edge-list">
            <header><h2>Evidence connections</h2><span>Method, confidence, and rationale behind every link</span></header>
            <Table><TableHeader><TableRow><TableHead>From</TableHead><TableHead>To</TableHead><TableHead>Method</TableHead><TableHead>Confidence</TableHead><TableHead>Created by</TableHead></TableRow></TableHeader><TableBody>{evidenceGraph.edges.map((edge) => { const sourceRecord = evidenceGraph.nodes.find((node) => node.id === edge.source); const targetRecord = evidenceGraph.nodes.find((node) => node.id === edge.target); return <TableRow key={edge.id}><TableCell>{sourceRecord?.external_record_id}</TableCell><TableCell>{targetRecord?.external_record_id}</TableCell><TableCell>{readableLabel(edge.method)}</TableCell><TableCell>{Math.round(Number(edge.confidence) * 100)}%</TableCell><TableCell>{readableLabel(edge.created_by)}</TableCell></TableRow> })}</TableBody></Table>
          </section>
        </> : null}
      </main>
      <Sheet open={Boolean(selectedRecord)} onOpenChange={(open) => { if (!open) setSelectedRecord(null) }}>
        <SheetContent className="evidence-sheet">
          <SheetHeader><SheetTitle>Source evidence</SheetTitle><SheetDescription>Immutable record received from {selectedRecord?.source_name}.</SheetDescription></SheetHeader>
          {selectedRecord ? <div className="evidence-sheet__body"><dl><div><dt>Reference</dt><dd>{selectedRecord.external_record_id}</dd></div><div><dt>Type</dt><dd>{readableLabel(selectedRecord.record_type)}</dd></div><div><dt>Amount</dt><dd>{formatMoney(selectedRecord.amount_minor, selectedRecord.currency)}</dd></div><div><dt>Occurred</dt><dd>{new Date(selectedRecord.occurred_at).toLocaleString("en-IN")}</dd></div></dl><h3>Raw source payload</h3><pre>{JSON.stringify(selectedRecord.raw_payload, null, 2)}</pre></div> : null}
        </SheetContent>
      </Sheet>
    </AppShell>
  )
}

function AuditLogPage({ goLanding, goDashboard, goCase }: { goLanding: () => void; goDashboard: () => void; goCase: (publicId: string) => void }) {
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [filter, setFilter] = useState<"All" | "Investigator runs" | "Evidence links">("All")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    getAuditLog()
      .then(setEntries)
      .catch((requestError: Error) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  const filteredEntries = useMemo(() => {
    if (filter === "Investigator runs") return entries.filter((entry) => entry.event_type === "agent_run")
    if (filter === "Evidence links") return entries.filter((entry) => entry.event_type === "evidence_connection")
    return entries
  }, [entries, filter])

  return (
    <AppShell active="Audit Log" goLanding={goLanding} goDashboard={goDashboard} goAuditLog={() => undefined}>
      <main className="audit-log-page" id="main-content">
        <header className="audit-log-page__heading">
          <div><span>Audit log</span><h1>Every AI action and evidence link, in order</h1><p>Generated directly from stored investigator runs and evidence connections — nothing here is summarized or reconstructed after the fact.</p></div>
          <div className="filters" aria-label="Filter audit log">{(["All", "Investigator runs", "Evidence links"] as const).map((item) => <button key={item} onClick={() => setFilter(item)} className={filter === item ? "active" : ""} aria-pressed={filter === item}>{item}</button>)}</div>
        </header>
        {loading ? <p className="api-state" role="status">Loading audit log…</p> : null}
        {error ? <p className="api-state api-state--error" role="alert">{error}</p> : null}
        {!loading && !error ? (
          filteredEntries.length === 0 ? <p className="api-state">No audit entries match this filter.</p> : (
            <ol className="audit-log-list">
              {filteredEntries.map((entry, index) => (
                <li key={`${entry.event_type}-${entry.case_public_id}-${index}`} className={`audit-log-list__item audit-log-list__item--${entry.event_type}`}>
                  <div className="audit-log-list__marker" aria-hidden="true">{entry.event_type === "agent_run" ? <Bot /> : <Link2 />}</div>
                  <div className="audit-log-list__body">
                    <header><strong>{entry.summary}</strong><time dateTime={entry.occurred_at}>{new Date(entry.occurred_at).toLocaleString("en-IN")}</time></header>
                    <p><button className="case-id" onClick={() => goCase(entry.case_public_id)}>{entry.case_reference}</button> · {entry.actor}</p>
                  </div>
                </li>
              ))}
            </ol>
          )
        ) : null}
      </main>
    </AppShell>
  )
}

export default function App() {
  const initialCaseId = window.location.hash.startsWith("#case/")
    ? window.location.hash.slice(6)
    : window.location.hash.startsWith("#money-graph/")
      ? window.location.hash.slice(13)
      : ""
  const [screen, setScreen] = useState<Screen>(() => {
    if (window.location.hash.startsWith("#money-graph/")) return "moneyGraph"
    if (window.location.hash === "#audit-log") return "auditLog"
    if (initialCaseId) return "case"
    return window.location.hash === "#app" ? "dashboard" : "landing"
  })
  const [selectedCaseId, setSelectedCaseId] = useState(initialCaseId)

  function navigate(next: Screen, publicId = "") {
    setScreen(next)
    setSelectedCaseId(publicId)
    window.location.hash =
      next === "dashboard" ? "app"
      : next === "case" ? `case/${publicId}`
      : next === "moneyGraph" ? `money-graph/${publicId}`
      : next === "auditLog" ? "audit-log"
      : ""
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  if (screen === "dashboard") return <Dashboard goLanding={() => navigate("landing")} openCase={(publicId) => navigate("case", publicId)} goMoneyGraph={(publicId) => navigate("moneyGraph", publicId)} goAuditLog={() => navigate("auditLog")} />
  if (screen === "case") return <CaseDetail publicId={selectedCaseId} goLanding={() => navigate("landing")} goDashboard={() => navigate("dashboard")} goMoneyGraph={(publicId) => navigate("moneyGraph", publicId)} goAuditLog={() => navigate("auditLog")} />
  if (screen === "moneyGraph") return <MoneyGraphPage publicId={selectedCaseId} goLanding={() => navigate("landing")} goDashboard={() => navigate("dashboard")} goCase={(publicId) => navigate("case", publicId)} goAuditLog={() => navigate("auditLog")} />
  if (screen === "auditLog") return <AuditLogPage goLanding={() => navigate("landing")} goDashboard={() => navigate("dashboard")} goCase={(publicId) => navigate("case", publicId)} />
  return <Landing openDashboard={() => navigate("dashboard")} />
}
