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
          <div className="trace-window__top"><span /><span /><span /><code>TRACE / PAY-33117890</code></div>
          <div className="trace-flow">
            <div><small>ORDER</small><strong>₹10,000.00</strong><code>ORD-88451234</code></div>
            <i aria-hidden="true" />
            <div><small>CAPTURED</small><strong>₹10,000.00</strong><code>PAY-33117890</code></div>
            <i aria-hidden="true" />
            <div><small>SETTLEMENT</small><strong>₹9,858.40</strong><code>SET-55667788</code></div>
            <i className="trace-flow__alert" aria-label="Mismatch detected" />
            <div className="trace-flow__mismatch"><small>BANK CREDIT</small><strong>₹9,855.00</strong><code>TXN-11223344</code></div>
            <i aria-hidden="true" />
            <div><small>LEDGER</small><strong>₹9,855.00</strong><code>JE-9088771</code></div>
          </div>
          <button onClick={onExplore}>Open evidence trail <span aria-hidden="true">→</span></button>
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
