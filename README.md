# LedgerLens

LedgerLens is a frontend prototype for financial reconciliation and investigation. It connects an order, payment, fee, tax, settlement, bank credit, and ledger entry into one evidence trail, then highlights the first point where the records stop matching.

## Run locally

Frontend:

```bash
npm install
npm run dev
```

Backend:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

Open the local URL printed by Vite. The Django health endpoint is available at `http://127.0.0.1:8000/api/health/`. Use `npm run check` for TypeScript and ESLint validation, `npm run build` for a production bundle, and run `python manage.py test` from `backend/` for backend tests.

## Prototype flow

- Landing page with the interactive CRTWarp background
- Reconciliation overview with financial-health metrics and money movement
- Filterable exceptions table
- Case investigation with deterministic checks, cited evidence, and an AI explanation
- Responsive desktop and mobile layouts

The UI still uses mock data from `src/data.ts`. The Django backend now contains the first canonical evidence models, but the frontend is not connected to them yet. No external accounts, payment APIs, or AI keys are required for this prototype.

## Product boundary

The reconciliation engine—not an LLM—must calculate amounts, apply tolerances, and decide whether records match. AI receives that verified result to explain the likely cause, cite the supporting records, group similar exceptions, and recommend a safe next action; it never moves money or rewrites source records.

## Stack

React 19, TypeScript, Vite, Tailwind CSS v4, shadcn-compatible UI components, Lucide icons, Three.js, the React Bits CRTWarp effect, Django 5.2 LTS, and the Django ORM. SQLite is used locally; PostgreSQL is the production database target.
