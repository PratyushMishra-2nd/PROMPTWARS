# LexGuard

AI contract intelligence platform. Upload contract → extract clauses → score risk → explain in plain English → chat with citations → compare vs benchmark.

Hackathon MVP. Stack: Next.js + FastAPI + Gemini.

## Quickstart

### Prerequisites
- Python 3.11+
- Node 20+, pnpm
- Gemini API key from https://aistudio.google.com/apikey (free tier OK)

### Backend
```powershell
cd apps\api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
copy ..\..\.env.example ..\..\.env
# edit .env → set GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend (new terminal)
```powershell
cd apps\web
pnpm install
pnpm dev
# open http://localhost:3000
```

### Try it
1. `/upload` → drop a PDF/DOCX, pick perspective.
2. Watch SSE stream stages: extracting → scoring → explaining → done.
3. Dashboard: clauses sorted by risk. Click for plain-language explanation + redline.
4. Tabs: detail / chat (RAG with citations) / benchmark (vs standard template).
5. Download PDF report.

## Architecture
- **Backend:** FastAPI sync, in-memory `ANALYSES: dict`, numpy cosine RAG, WeasyPrint PDF, pdfplumber/docx parsing
- **LLM:** Gemini 2.5 Pro (1 mega-call: classify + extract + score), Flash (explainer, adversarial, chat)
- **Frontend:** Next.js 15 App Router, Tailwind
- **Cost:** ~$0.05–0.08 per 20-page analysis; AI Studio free tier covers most dev

See `docs/demo-script.md` and the PRD at `~/.claude/plans/problem-statement-01-lexguard-wobbly-lobster.md`.

## Docker / deploy

Local everything:
```bash
cp .env.example .env  # set GEMINI_API_KEY
docker compose up --build
# api → http://localhost:8000   web → http://localhost:3000
```

Cloud Run (backend):
```bash
gcloud builds submit --tag gcr.io/PROJECT/lexguard-api --file Dockerfile.api .
gcloud run deploy lexguard-api --image gcr.io/PROJECT/lexguard-api \
  --region asia-south1 --allow-unauthenticated \
  --set-env-vars CORS_ORIGIN=https://your-frontend.vercel.app \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

Frontend → Vercel: connect repo, set root to `apps/web`, env `NEXT_PUBLIC_API_URL=<cloud-run-url>`.

## Limits (hackathon-by-design)
- No auth (single demo session)
- No DB — process restart wipes analyses
- Scanned/image PDFs not yet supported (need Document AI fallback)
- English / Hindi only (lang-detect rejects others)
