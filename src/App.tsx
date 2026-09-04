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
  getCase,
  getCases,
  getOverviewMetrics,
  type FinancialRecord,
  type OverviewMetrics,
  type ReconciliationCaseDetail,
  type ReconciliationCaseSummary,
} from "@/api"

const CRTWarp = lazy(() => import("@/components/CRTWarp"))

type Screen = "landing" | "dashboard" | "case"

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

function AppShell({ active, children, goLanding, goDashboard }: { active: string; children: React.ReactNode; goLanding: () => void; goDashboard: () => void }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <aside className="app-sidebar">
        <button className="app-sidebar__brand" onClick={goLanding} aria-label="Go to LedgerLens landing page"><Brand inverse /></button>
        <div className="workspace-switcher"><small>Workspace</small><strong>Acme FinOps</strong><span>Demo data</span></div>
        <nav aria-label="Application navigation">{appNav.map(([label, Icon]) => <button key={label} className={label === active ? "active" : ""} aria-current={label === active ? "page" : undefined} aria-disabled={label !== "Overview" && label !== "Exceptions"} title={label !== "Overview" && label !== "Exceptions" ? "Planned after the investigation workflow" : undefined} onClick={label === "Overview" ? goDashboard : undefined}><Icon aria-hidden="true" />{label}</button>)}</nav>
        <a className="repo-link" href="https://github.com/UdaiBatta/LedgerLens" target="_blank" rel="noreferrer"><Code2 aria-hidden="true" />View repository</a>
      </aside>
      <div className="app-workspace">
        <header className="app-topbar"><button className="mobile-logo" onClick={goLanding}><Brand /></button><label className="search-box"><Search aria-hidden="true" /><span className="sr-only">Search</span><input type="search" placeholder="Search ID, amount, reference, or entity" /></label><div className="operator"><span>NS</span><div><strong>Neha Sharma</strong><small>Finance operator</small></div></div></header>
        {children}
      </div>
    </div>
  )
}

function Dashboard({ goLanding, openCase }: { goLanding: () => void; openCase: (publicId: string) => void }) {
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
    <AppShell active="Overview" goLanding={goLanding} goDashboard={() => undefined}>
      <main className="dashboard" id="main-content">
        <header className="dashboard__heading"><div><p>Reconciliation overview</p><h1>Financial truth, in one place.</h1><span>Live data from the Django reconciliation API</span></div><Button onClick={() => firstCaseId && openCase(firstCaseId)} disabled={!firstCaseId}>Review exceptions <ArrowRight data-icon="inline-end" aria-hidden="true" /></Button></header>
        {loading ? <p className="api-state" role="status">Loading reconciliation data…</p> : null}
        {error ? <p className="api-state api-state--error" role="alert">{error} Start Django on port 8000 and seed the demo cases.</p> : null}
        {metrics ? <section className="metric-rail" aria-label="Reconciliation summary"><div><span>Captured value</span><strong>{formatMoney(metrics.captured_amount_minor)}</strong><small>{metrics.movement.find((stage) => stage.record_type === "payment")?.record_count ?? 0} payment records</small></div><div><span>Unexplained value</span><strong>{formatMoney(metrics.unexplained_amount_minor)}</strong><small>Across {metrics.open_case_count} open cases</small></div><div><span>Matched cases</span><strong>{metrics.matched_case_count} / {metrics.case_count}</strong><small>Generated by deterministic rules</small></div><div><span>Source health</span><strong>4 / 4</strong><small>Demo sources connected</small></div></section> : null}
        <section className="dashboard-grid">
          <MoneyMovement metrics={metrics} openCase={() => firstCaseId && openCase(firstCaseId)} />
          <Briefing cases={cases} openCase={() => firstCaseId && openCase(firstCaseId)} />
        </section>
        <Exceptions rows={filteredCases} filter={filter} setFilter={setFilter} openCase={openCase} />
      </main>
    </AppShell>
  )
}

function MoneyMovement({ metrics, openCase }: { metrics: OverviewMetrics | null; openCase: () => void }) {
  const stages = metrics?.movement.filter((stage) => stage.record_type !== "tax") ?? []
  return (
    <article className="movement-panel">
      <header><div><span>Money movement</span><h2>Where every rupee landed</h2></div><button onClick={openCase}>Inspect highest-risk case <ArrowRight aria-hidden="true" /></button></header>
      <div className="movement-flow">{stages.map((stage, index) => { const warning = stage.record_type === "bank_credit"; return <div className={`movement-stage ${warning ? "warning" : "complete"}`} key={stage.record_type}><div><small>{String(index + 1).padStart(2, "0")}</small><i aria-hidden="true" /></div><strong>{stage.label}</strong><b>{formatMoney(stage.amount_minor)}</b><span>{stage.record_count} records</span>{warning ? <button onClick={openCase}><AlertTriangle aria-hidden="true" />Inspect variance</button> : <em><Check aria-hidden="true" />Verified</em>}</div> })}</div>
      <footer><span><i className="ok" />Matched</span><span><i className="warn" />Needs investigation</span><p>Select a case to inspect its records and evidence.</p></footer>
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

function CaseDetail({ publicId, goLanding, goDashboard }: { publicId: string; goLanding: () => void; goDashboard: () => void }) {
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
    const [firstConnection] = reconciliationCase.evidence_connections
    return [
      firstConnection.source,
      ...reconciliationCase.evidence_connections.map((connection) => connection.destination),
    ]
  }, [reconciliationCase])

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
    <AppShell active="Exceptions" goLanding={goLanding} goDashboard={goDashboard}>
      <main className="case-page" id="main-content">
        <button className="back-button" onClick={goDashboard}><ArrowLeft aria-hidden="true" />Back to overview</button>
        {loading ? <p className="api-state" role="status">Loading investigation…</p> : null}
        {error ? <p className="api-state api-state--error" role="alert">{error}</p> : null}
        {reconciliationCase ? <>
          <header className="case-heading"><div><div><h1>{readableLabel(reconciliationCase.exception_type)} · {formatMoney(Math.abs(reconciliationCase.difference_minor), reconciliationCase.currency)}</h1><span className={`status status--${readableLabel(reconciliationCase.status).toLowerCase().replace(" ", "-")}`}>{readableLabel(reconciliationCase.status)}</span></div><p><code>{reconciliationCase.case_reference}</code> · {reconciliationCase.entity_id}</p></div><Button onClick={assignToMe} disabled={reconciliationCase.owner === "Neha Sharma"}>{reconciliationCase.owner === "Neha Sharma" ? <Check data-icon="inline-start" aria-hidden="true" /> : <UserPlus data-icon="inline-start" aria-hidden="true" />}{reconciliationCase.owner === "Neha Sharma" ? "Assigned to you" : "Assign case"}</Button></header>
          <section className="case-layout">
            <article className="case-path"><header><span>Transaction path</span><Badge variant="secondary">Rule generated</Badge></header><ol>{pathRecords.map((record, index) => { const icons = [FileCheck2, BadgeIndianRupee, Banknote, BadgeIndianRupee, Landmark, Building2, ReceiptText]; const Icon = icons[index % icons.length]; const isBreak = record.id === reconciliationCase.first_break_record?.id; const isAdjustment = ["fee", "tax", "refund"].includes(record.record_type); const state = isBreak ? "mismatch" : isAdjustment ? "fee" : "verified"; return <li className={`case-path__step case-path__step--${state}`} key={record.id}><button className={state} onClick={() => setSelectedRecord(record)}><span><Icon aria-hidden="true" /></span><div><strong>{readableLabel(record.record_type)}</strong><code>{record.external_record_id}</code><small>{new Date(record.occurred_at).toLocaleString("en-IN")}</small><em>{isBreak ? "First divergence" : isAdjustment ? "Derived adjustment" : "Verified source"}</em></div><b>{formatMoney(record.amount_minor, record.currency)}</b></button></li>})}</ol>{reconciliationCase.first_break_record ? <div className="case-path__alert"><AlertTriangle aria-hidden="true" /><p><strong>First divergence</strong>Actual differs from expected by {formatMoney(Math.abs(reconciliationCase.difference_minor), reconciliationCase.currency)}. Select any record to inspect its source payload.</p></div> : null}</article>
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

export default function App() {
  const initialCaseId = window.location.hash.startsWith("#case/") ? window.location.hash.slice(6) : ""
  const [screen, setScreen] = useState<Screen>(() => initialCaseId ? "case" : window.location.hash === "#app" ? "dashboard" : "landing")
  const [selectedCaseId, setSelectedCaseId] = useState(initialCaseId)

  function navigate(next: Screen, publicId = "") {
    setScreen(next)
    setSelectedCaseId(publicId)
    window.location.hash = next === "dashboard" ? "app" : next === "case" ? `case/${publicId}` : ""
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  if (screen === "dashboard") return <Dashboard goLanding={() => navigate("landing")} openCase={(publicId) => navigate("case", publicId)} />
  if (screen === "case") return <CaseDetail publicId={selectedCaseId} goLanding={() => navigate("landing")} goDashboard={() => navigate("dashboard")} />
  return <Landing openDashboard={() => navigate("dashboard")} />
}
