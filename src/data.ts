export type PathEvent = {
  label: string
  reference: string
  amount: string
  detail?: string
  state: "verified" | "fee" | "mismatch"
}

export const pathEvents: PathEvent[] = [
  { label: "Order amount", reference: "ORD-88451234", amount: "₹10,000.00", state: "verified" },
  { label: "Captured", reference: "PAY-33117890", amount: "₹10,000.00", detail: "May 14, 10:12 AM", state: "verified" },
  { label: "Processing fee", reference: "FEE-771233 · 1.20%", amount: "−₹120.00", state: "fee" },
  { label: "Tax on fee", reference: "TAX-991122 · 18%", amount: "−₹21.60", state: "fee" },
  { label: "Settlement expected", reference: "SET-55667788", amount: "₹9,858.40", state: "verified" },
  { label: "Bank credit actual", reference: "TXN-11223344", amount: "₹9,855.00", detail: "May 15, 9:42 AM", state: "mismatch" },
]

export const checks = [
  { check: "Order amount matches capture", result: "Passed", evidence: "ORD-88451234 · PAY-33117890" },
  { check: "Processing fee calculation", result: "Passed", evidence: "FEE-771233 · FEE-RULE-001" },
  { check: "Tax on fee calculation", result: "Passed", evidence: "TAX-991122 · TAX-RULE-018" },
  { check: "Settlement amount calculation", result: "Passed", evidence: "SET-55667788 · SET-RULE-010" },
  { check: "Settlement acknowledged by bank", result: "Passed", evidence: "ACK-77889900" },
  { check: "Bank credit equals settlement", result: "Failed", evidence: "TXN-11223344 · short by ₹3.40" },
  { check: "Reconciliation note present", result: "Waiting", evidence: "No source record" },
] as const

export const exceptionRows = [
  { id: "EXC-2025-05-000145", type: "Settlement short", entity: "Stellar Electronics", captured: "₹10,000.00", variance: "−₹3.40", status: "Needs review", owner: "Unassigned" },
  { id: "EXC-2025-05-000142", type: "Fee mismatch", entity: "Bright Retail", captured: "₹25,000.00", variance: "₹0.00", status: "Needs review", owner: "Arjun Mehta" },
  { id: "EXC-2025-05-000138", type: "Bank credit delay", entity: "Zenith Supplies", captured: "₹8,500.00", variance: "Pending", status: "Investigating", owner: "Kavya Iyer" },
  { id: "EXC-2025-05-000137", type: "Refund mismatch", entity: "Vertex Solutions", captured: "₹15,000.00", variance: "₹0.00", status: "Closed", owner: "Rohit Verma" },
] as const
