import { Fragment } from "react"
import { Cpu, GitBranch, LockKeyhole, ScanSearch } from "lucide-react"

type FeaturesProps = {
  onExplore: () => void
}

const capabilities = [
  {
    icon: GitBranch,
    title: "Connected",
    copy: "One event chain across orders, gateways, banks, and ledgers.",
  },
  {
    icon: Cpu,
    title: "Deterministic",
    copy: "Amounts and matches come from rules with explicit tolerances.",
  },
  {
    icon: LockKeyhole,
    title: "Controlled",
    copy: "AI can investigate and explain, but it cannot move money.",
  },
  {
    icon: ScanSearch,
    title: "Explainable",
    copy: "Every finding names its evidence, confidence, and next action.",
  },
]

const traceStages = [
  { label: "Order", amount: "₹10,000.00", reference: "ORD-88451234", note: "Customer intent" },
  { label: "Captured", amount: "₹10,000.00", reference: "PAY-33117890", note: "Gateway confirmed" },
  { label: "Settlement", amount: "₹9,858.40", reference: "SET-55667788", note: "Net after fees + tax" },
  { label: "Bank credit", amount: "₹9,855.00", reference: "TXN-11223344", note: "First break", mismatch: true },
  { label: "Ledger", amount: "₹9,855.00", reference: "JE-9088771", note: "Posted amount" },
] as const

export function Features({ onExplore }: FeaturesProps) {
  return (
    <section className="feature-story" id="how-it-works">
      <div className="feature-story__heading">
        <h2>Follow the money.<br />Find the first break.</h2>
        <p>LedgerLens does not begin with a chatbot. It begins with the financial records your team already trusts, joins them into one trace, and lets AI investigate only after the facts are established.</p>
      </div>

      <div className="feature-story__visual" aria-label="A financial event trace from order to accounting ledger">
        <div className="feature-story__fade" aria-hidden="true" />
        <div className="trace-window">
          <div className="trace-window__top"><div className="trace-window__top-dots"><span /><span /><span /></div><code>TRACE / PAY-33117890</code><div className="trace-window__top-meta"><span>5 checkpoints</span><strong><i />1 divergence</strong></div></div>
          <div className="trace-window__summary"><div><span>Expected settlement</span><strong>₹9,858.40</strong></div><div><span>Bank credit</span><strong>₹9,855.00</strong></div><div className="trace-window__summary--variance"><span>Unexplained variance</span><strong>−₹3.40</strong></div></div>
          <div className="trace-flow" role="list" aria-label="Transaction money trail">
            {traceStages.map((stage, index) => (
              <Fragment key={stage.reference}>
                <div className={`trace-flow__stage ${"mismatch" in stage && stage.mismatch ? "trace-flow__mismatch" : ""}`} role="listitem">
                  <div className="trace-flow__stage-head"><small>{String(index + 1).padStart(2, "0")}</small><span>{stage.label}</span></div>
                  <strong>{stage.amount}</strong>
                  <code>{stage.reference}</code>
                  <em><i className={"mismatch" in stage && stage.mismatch ? "trace-flow__status-dot trace-flow__status-dot--break" : "trace-flow__status-dot"} />{stage.note}</em>
                </div>
                {index < traceStages.length - 1 ? <div className={`trace-flow__connector ${index === 2 ? "trace-flow__connector--break" : ""}`} aria-hidden="true"><i /><span>{index === 2 ? "−₹3.40" : "matched"}</span></div> : null}
              </Fragment>
            ))}
          </div>
          <div className="trace-window__finding"><span>FIRST BREAK</span><strong>Bank credit is ₹3.40 short.</strong><p>The settlement is verified. LedgerLens carries this exact break into the evidence trail for investigation.</p></div>
          <div className="trace-window__footer"><div className="trace-window__legend" aria-label="Trace legend"><span><i className="trace-dot trace-dot--verified" />Verified source</span><span><i className="trace-dot trace-dot--break" />First divergence</span><span>Every amount stays cited.</span></div><button onClick={onExplore}>Open evidence trail <span aria-hidden="true">→</span></button></div>
        </div>
      </div>

      <div className="feature-story__capabilities">
        {capabilities.map(({ icon: Icon, title, copy }) => (
          <div key={title}>
            <p><Icon aria-hidden="true" /><strong>{title}</strong></p>
            <span>{copy}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
