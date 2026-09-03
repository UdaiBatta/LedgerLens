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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { checks, exceptionRows, pathEvents } from "@/data"

const CRTWarp = lazy(() => import("@/components/CRTWarp"))

type Screen = "landing" | "dashboard" | "case"

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
      await navigator.clipboard.writeText(`${window.location.origin}/#case`)
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

function Dashboard({ goLanding, openCase }: { goLanding: () => void; openCase: () => void }) {
  const [filter, setFilter] = useState("All")
  const filteredRows = useMemo(() => filter === "All" ? exceptionRows : exceptionRows.filter((row) => row.status === filter), [filter])

  return (
    <AppShell active="Overview" goLanding={goLanding} goDashboard={() => undefined}>
      <main className="dashboard" id="main-content">
        <header className="dashboard__heading"><div><p>Reconciliation overview</p><h1>Financial truth, in one place.</h1><span>May 01–31, 2025 · Updated 2 minutes ago</span></div><Button onClick={openCase}>Review exceptions <ArrowRight data-icon="inline-end" aria-hidden="true" /></Button></header>
        <section className="metric-rail" aria-label="Reconciliation summary"><div><span>Reconciled value</span><strong>₹14.2L</strong><small>99.72% of records</small></div><div><span>Unexplained value</span><strong>₹42,863</strong><small>Across 18 open cases</small></div><div><span>Oldest open case</span><strong>2d 4h</strong><small>Settlement short</small></div><div><span>Source health</span><strong>6 / 7</strong><small>Bank import delayed</small></div></section>

        <section className="dashboard-grid">
          <MoneyMovement openCase={openCase} />
          <Briefing openCase={openCase} />
        </section>
        <Exceptions rows={filteredRows} filter={filter} setFilter={setFilter} openCase={openCase} />
      </main>
    </AppShell>
  )
}

function MoneyMovement({ openCase }: { openCase: () => void }) {
  const stages = [
    ["Orders", "1,248", "₹14.2L", "complete"],
    ["Captured", "1,221", "₹14.0L", "complete"],
    ["Fees + tax", "1,221", "−₹31.8K", "complete"],
    ["Settled", "1,204", "₹13.7L", "complete"],
    ["Bank", "1,203", "₹13.7L", "warning"],
    ["Ledger", "1,203", "₹13.7L", "complete"],
  ]
  return (
    <article className="movement-panel">
      <header><div><span>Money movement</span><h2>Where every rupee landed</h2></div><button onClick={openCase}>Open graph <ArrowRight aria-hidden="true" /></button></header>
      <div className="movement-flow">{stages.map(([label, records, amount, state], index) => <div className={`movement-stage ${state}`} key={label}><div><small>{String(index + 1).padStart(2, "0")}</small><i aria-hidden="true" /></div><strong>{label}</strong><b>{amount}</b><span>{records} records</span>{state === "warning" ? <button onClick={openCase}><AlertTriangle aria-hidden="true" />1 mismatch</button> : <em><Check aria-hidden="true" />Matched</em>}</div>)}</div>
      <footer><span><i className="ok" />Matched</span><span><i className="warn" />Needs investigation</span><p>Select any stage to inspect its records and evidence.</p></footer>
    </article>
  )
}

function Briefing({ openCase }: { openCase: () => void }) {
  return (
    <aside className="briefing">
      <header><div><Bot aria-hidden="true" /><span>AI briefing</span></div><Badge>Evidence grounded</Badge></header>
      <h2>Three items need a human decision.</h2>
      <p>Rules completed the checks. AI grouped the remaining exceptions by likely next action.</p>
      <ol><li><span>12</span><div><strong>Bank credits are delayed</strong><p>Latest statement import is 4h behind.</p></div></li><li><span>5</span><div><strong>Fee evidence is incomplete</strong><p>Provider invoices have not arrived.</p></div></li><li><span>1</span><div><strong>Amount differs after settlement</strong><p>₹3.40 cannot be explained by current evidence.</p></div></li></ol>
      <button onClick={openCase}>Review the highest-risk case <ArrowRight aria-hidden="true" /></button>
      <small><ShieldCheck aria-hidden="true" />No actions or money movements were performed.</small>
    </aside>
  )
}

function Exceptions({ rows, filter, setFilter, openCase }: { rows: readonly (typeof exceptionRows)[number][]; filter: string; setFilter: (value: string) => void; openCase: () => void }) {
  return (
    <section className="exceptions-panel">
      <header><div><h2>Exceptions</h2><span>Prioritized by financial impact and age</span></div><div className="filters" aria-label="Filter exception status">{["All", "Needs review", "Investigating", "Closed"].map((item) => <button key={item} onClick={() => setFilter(item)} className={filter === item ? "active" : ""} aria-pressed={filter === item}>{item}</button>)}</div></header>
      <Table><TableHeader><TableRow><TableHead>Case</TableHead><TableHead>Type</TableHead><TableHead>Entity</TableHead><TableHead>Captured</TableHead><TableHead>Variance</TableHead><TableHead>Status</TableHead><TableHead>Owner</TableHead><TableHead><span className="sr-only">Open</span></TableHead></TableRow></TableHeader><TableBody>{rows.map((row, index) => <TableRow key={row.id} className={index === 0 ? "priority-row" : ""}><TableCell><button className="case-id" onClick={openCase}>{row.id}</button></TableCell><TableCell>{row.type}</TableCell><TableCell>{row.entity}</TableCell><TableCell className="money">{row.captured}</TableCell><TableCell className="money">{row.variance}</TableCell><TableCell><span className={`status status--${row.status.toLowerCase().replace(" ", "-")}`}>{row.status}</span></TableCell><TableCell>{row.owner}</TableCell><TableCell><button className="row-open" onClick={openCase} aria-label={`Open ${row.id}`}><ChevronRight aria-hidden="true" /></button></TableCell></TableRow>)}</TableBody></Table>
    </section>
  )
}

function CaseDetail({ goLanding, goDashboard }: { goLanding: () => void; goDashboard: () => void }) {
  const [assigned, setAssigned] = useState(false)
  const [selected, setSelected] = useState(pathEvents.length - 1)
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")

  function ask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!question.trim()) return
    setAnswer("The first unsupported difference is between settlement SET-55667788 and bank credit TXN-11223344. The bank credit is ₹3.40 lower; no fee, tax, refund, or adjustment record explains it.")
  }

  return (
    <AppShell active="Exceptions" goLanding={goLanding} goDashboard={goDashboard}>
      <main className="case-page" id="main-content">
        <button className="back-button" onClick={goDashboard}><ArrowLeft aria-hidden="true" />Back to overview</button>
        <header className="case-heading"><div><div><h1>Settlement short by ₹3.40</h1><span className="status status--needs-review">Needs review</span></div><p><code>EXC-2025-05-000145</code> · Stellar Electronics Pvt. Ltd.</p></div><Button onClick={() => setAssigned(true)} disabled={assigned}>{assigned ? <Check data-icon="inline-start" aria-hidden="true" /> : <UserPlus data-icon="inline-start" aria-hidden="true" />}{assigned ? "Assigned to you" : "Assign case"}</Button></header>

        <section className="case-layout">
          <article className="case-path"><header><span>Transaction path</span><Badge variant="secondary">Rule verified</Badge></header><ol>{pathEvents.map((event, index) => { const Icon = [FileCheck2, BadgeIndianRupee, Banknote, BadgeIndianRupee, Landmark, Building2][index]; return <li className={`case-path__step case-path__step--${event.state}`} key={event.reference}><button className={`${event.state} ${selected === index ? "selected" : ""}`} onClick={() => setSelected(index)} aria-pressed={selected === index}><span><Icon aria-hidden="true" /></span><div><strong>{event.label}</strong><code>{event.reference}</code>{event.detail ? <small>{event.detail}</small> : null}<em>{event.state === "mismatch" ? "First divergence" : event.state === "fee" ? "Derived adjustment" : "Verified source"}</em></div><b>{event.amount}</b></button></li>})}</ol><div className="case-path__alert"><AlertTriangle aria-hidden="true" /><p><strong>First divergence</strong>The actual bank credit is ₹3.40 below the expected settlement.</p></div></article>

          <article className="case-finding"><header><div><Bot aria-hidden="true" /><span>AI Investigator</span></div><Badge>92% confidence</Badge></header><p className="case-finding__meta">Based on 7 deterministic checks and 3 cited records</p><h2>The mismatch begins after the bank acknowledges settlement.</h2><p>The expected settlement is <strong>₹9,858.40</strong>. The imported bank credit is <strong>₹9,855.00</strong>. Fees and tax are already verified, and no adjustment record explains the <strong>₹3.40</strong> difference.</p><div className="citations"><code>SET-55667788</code><code>TXN-11223344</code><code>ACK-77889900</code></div><section><h3>Recommended next action</h3><p>Check the bank narration for an unreported charge, then request clarification from the banking partner using the cited references.</p></section><form onSubmit={ask}><label htmlFor="investigator-question">Ask about this case</label><div><input id="investigator-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Why is the case still open?" /><button type="submit" aria-label="Ask AI Investigator"><ArrowRight aria-hidden="true" /></button></div></form>{answer ? <p className="case-answer" role="status">{answer}</p> : null}<small><ShieldCheck aria-hidden="true" />Analysis only. No source records or money movements were changed.</small></article>
        </section>

        <section className="checks-section"><header><div><h2>Checks and evidence</h2><span>Deterministic output supplied to the AI investigator</span></div><Badge variant="outline">6 passed · 1 waiting</Badge></header><Table><TableHeader><TableRow><TableHead>Check</TableHead><TableHead>Result</TableHead><TableHead>Evidence</TableHead></TableRow></TableHeader><TableBody>{checks.map((item) => <TableRow key={item.check}><TableCell>{item.check}</TableCell><TableCell><span className={`check check--${item.result.toLowerCase()}`}>{item.result === "Passed" ? <Check aria-hidden="true" /> : <AlertTriangle aria-hidden="true" />}{item.result}</span></TableCell><TableCell><code>{item.evidence}</code></TableCell></TableRow>)}</TableBody></Table></section>
      </main>
    </AppShell>
  )
}

export default function App() {
  const [screen, setScreen] = useState<Screen>(() => window.location.hash === "#case" ? "case" : window.location.hash === "#app" ? "dashboard" : "landing")

  function navigate(next: Screen) {
    setScreen(next)
    window.location.hash = next === "dashboard" ? "app" : next === "case" ? "case" : ""
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  if (screen === "dashboard") return <Dashboard goLanding={() => navigate("landing")} openCase={() => navigate("case")} />
  if (screen === "case") return <CaseDetail goLanding={() => navigate("landing")} goDashboard={() => navigate("dashboard")} />
  return <Landing openDashboard={() => navigate("dashboard")} />
}
