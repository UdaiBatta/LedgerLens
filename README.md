# LedgerLens

LedgerLens is a frontend prototype for financial reconciliation and investigation. It connects an order, payment, fee, tax, settlement, bank credit, and ledger entry into one evidence trail, then highlights the first point where the records stop matching.

## Run locally

```bash
npm install
npm run dev
```

Open the local URL printed by Vite. Use `npm run check` for TypeScript and ESLint validation, and `npm run build` for a production bundle.

## Prototype flow

- Landing page with the interactive CRTWarp background
- Reconciliation overview with financial-health metrics and money movement
- Filterable exceptions table
- Case investigation with deterministic checks, cited evidence, and an AI explanation
- Responsive desktop and mobile layouts

The UI uses mock data from `src/data.ts`. No external accounts, payment APIs, or AI keys are required for this prototype.

## Product boundary

The reconciliation engine—not an LLM—must calculate amounts, apply tolerances, and decide whether records match. AI receives that verified result to explain the likely cause, cite the supporting records, group similar exceptions, and recommend a safe next action; it never moves money or rewrites source records.

## Stack

React 19, TypeScript, Vite, Tailwind CSS v4, shadcn-compatible UI components, Lucide icons, Three.js, and the React Bits CRTWarp effect.
