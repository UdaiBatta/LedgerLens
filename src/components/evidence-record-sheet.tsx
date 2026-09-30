import { ArrowRight, Check, Link2 } from "lucide-react"
import type { FinancialRecord, ReconciliationCaseDetail } from "@/api"
import { formatMoney, readableLabel } from "@/lib/financial-format"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"

type EvidenceRecordSheetProps = {
  record: FinancialRecord | null
  reconciliationCase: ReconciliationCaseDetail | null | undefined
  onSelectRecord: (record: FinancialRecord) => void
  onClose: () => void
  onOpenCase?: () => void
}

function displayTime(value?: string) {
  return value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "Not recorded"
}

function displayCheckDetails(details: string, currency: string) {
  // Format only known engine messages; retain all other source explanations verbatim.
  const current = /^Expected (-?\d+); observed (-?\d+); tolerance (\d+) minor units\.$/.exec(details)
  if (current) return `Expected ${formatMoney(Number(current[1]), currency)}; observed ${formatMoney(Number(current[2]), currency)}; allowed tolerance ${formatMoney(Number(current[3]), currency)}.`
  const legacy = /^Expected (-?\d+) minor units; received (-?\d+)\.$/.exec(details)
  if (legacy) return `Expected ${formatMoney(Number(legacy[1]), currency)}; received ${formatMoney(Number(legacy[2]), currency)}.`
  return details || "No explanation was recorded for this check."
}

export function EvidenceRecordSheet({ record, reconciliationCase, onSelectRecord, onClose, onOpenCase }: EvidenceRecordSheetProps) {
  const connections = reconciliationCase?.evidence_connections ?? []
  const relatedLinks = record ? connections.filter(link => link.source.id === record.id || link.destination.id === record.id) : []
  // Older checks cite external IDs, which can collide between sources. Do not silently attribute them.
  const citedRecordIds = new Set(connections.flatMap(link => [link.source, link.destination])
    .filter(candidate => candidate.external_record_id === record?.external_record_id).map(candidate => candidate.id))
  const ambiguousCitation = citedRecordIds.size > 1
  const checks = record ? (reconciliationCase?.check_results ?? [])
    .filter(check => check.evidence.includes(record.external_record_id))
    .sort((a, b) => Number(a.result === "passed") - Number(b.result === "passed")) : []
  const unresolvedCount = checks.filter(check => check.result !== "passed").length
  const firstBreak = record && reconciliationCase?.first_break_record?.id === record.id

  return (
    <Sheet open={Boolean(record)} onOpenChange={open => { if (!open) onClose() }}>
      <SheetContent className="evidence-sheet">
        <SheetHeader>
          <SheetTitle>Why this record matters</SheetTitle>
          <SheetDescription>{record ? `${readableLabel(record.record_type)} · ${record.external_record_id}` : "Record evidence"}</SheetDescription>
        </SheetHeader>
        {record ? <div className="evidence-sheet__body" key={record.id}>
          <section className="record-impact" aria-label="Role in this case">
            <span className="record-impact__label">{firstBreak ? "Review starts here" : "Role in this case"}</span>
            <h3>{ambiguousCitation ? "Reference needs disambiguation" : checks.length ? `${unresolvedCount} unresolved · ${checks.length - unresolvedCount} passed` : "No checks cite this record"}</h3>
            <p>{ambiguousCitation
              ? "Several records share this reference. The checks below cite that reference; they cannot be attributed to this record alone."
              : checks.length
                ? "The checks below show where this record was used and what still needs attention."
                : "A source record alone does not establish a match. Review its links and the full case."}</p>
            {reconciliationCase && !reconciliationCase.amounts_known ? <p className="record-impact__note">Case conclusion pending: the available evidence does not establish an overall monetary difference. Recorded checks below do not override that status.</p> : null}
            {firstBreak && reconciliationCase?.amounts_known ? <p className="record-impact__note">Case finding: {readableLabel(reconciliationCase.exception_type)}. Expected {formatMoney(reconciliationCase.expected_amount_minor, reconciliationCase.currency)}, actual {formatMoney(reconciliationCase.actual_amount_minor, reconciliationCase.currency)}. Recorded difference: {formatMoney(reconciliationCase.difference_minor, reconciliationCase.currency)}.</p> : null}
          </section>

          <section className="record-section" aria-label="Checks using this record">
            <h3>Checks using this record <span>{checks.length}</span></h3>
            {checks.length ? <ul className="record-checks">{checks.map(check => <li key={check.check_name}>
              <div className="record-checks__heading"><strong>{check.check_name}</strong><span className={`check check--${check.result}`}>{check.result === "passed" ? <Check aria-hidden="true" /> : null}{readableLabel(check.result)}</span></div>
              <p>{displayCheckDetails(check.details, record.currency)}</p>
              <details><summary>Supporting references and check time</summary><div className="record-checks__references">{check.evidence.map(reference => <code key={reference}>{reference}</code>)}</div><small>Checked {displayTime(check.ran_at)}</small></details>
            </li>)}</ul> : <p className="record-empty">No check result in this case names this reference yet.</p>}
          </section>

          <section className="record-section" aria-label="Linked records">
            <h3>Linked records <span>{relatedLinks.length}</span></h3>
            <p className="record-section__intro">A confirmed link establishes a relationship. The amount checks above determine whether the money agrees.</p>
            {relatedLinks.length ? <ul className="record-links">{relatedLinks.map(link => {
              const incoming = link.destination.id === record.id
              const other = incoming ? link.source : link.destination
              const ambiguous = link.rationale.state === "ambiguous"
              const explanation = ambiguous ? "Several records fit this link; it requires review."
                : link.match_method === "exact_reference" ? "The destination cites the preceding record's identifier."
                  : link.match_method === "amount_and_time" ? "Amount and time suggest a possible relationship."
                    : `Recorded matching method: ${readableLabel(link.match_method)}.`
              return <li key={link.sequence_number}>
                <button onClick={() => onSelectRecord(other)} aria-label={`Inspect ${other.external_record_id}`}><Link2 aria-hidden="true" /><span><small>{incoming ? "Links from" : "Links to"} · {readableLabel(other.record_type)}</small><strong>{other.external_record_id}</strong></span><ArrowRight aria-hidden="true" /></button>
                <p><b>{link.is_verified ? "Confirmed link" : ambiguous ? "Ambiguous link" : "Candidate link"}</b> · {explanation}</p>
              </li>
            })}</ul> : <p className="record-empty">No relationship to another record is recorded in this case.</p>}
          </section>

          <details className="record-disclosure">
            <summary>Source and import details</summary>
            <dl>
              <div><dt>Source</dt><dd>{record.source_name}</dd></div>
              <div><dt>Imported</dt><dd>{displayTime(record.ingested_at)}</dd></div>
              <div><dt>Import batch</dt><dd>{record.batch_id || "Not recorded"}</dd></div>
              <div><dt>Source status</dt><dd>{record.status || "Not recorded"}</dd></div>
              <div><dt>Source amount</dt><dd>{formatMoney(record.amount_minor, record.currency)}</dd></div>
              <div><dt>Occurred</dt><dd>{displayTime(record.occurred_at)}</dd></div>
              <div><dt>Scope</dt><dd>{record.entity_id}</dd></div>
              <div><dt>Source reference</dt><dd>{record.reference || "Not recorded"}</dd></div>
              <div><dt>Mapping version</dt><dd>{record.normalization_version || "Not recorded"}</dd></div>
            </dl>
            <details className="record-hashes"><summary>Integrity hashes</summary><p>These identify the stored contents. They do not verify the source system's authenticity.</p><dl><div><dt>Source payload</dt><dd>{record.content_hash || "Not recorded"}</dd></div><div><dt>Normalized record</dt><dd>{record.normalized_hash || "Not recorded"}</dd></div></dl></details>
          </details>
          <details className="record-disclosure">
            <summary>Original imported data · JSON</summary>
            <p>The payload retained at import, available for source comparison.</p>
            <pre>{JSON.stringify(record.raw_payload, null, 2)}</pre>
          </details>
          {onOpenCase ? <button className="evidence-sheet__case-link" onClick={onOpenCase}>Open full case <ArrowRight aria-hidden="true" /></button> : null}
        </div> : null}
      </SheetContent>
    </Sheet>
  )
}
