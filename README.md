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
  --set-env-vars CORS_ORIGIN=https://your-frontend.vercel.app,ENABLE_FIREBASE=1,TRUST_PROXY=1 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

Frontend → Vercel: connect repo, set root to `apps/web`, env `NEXT_PUBLIC_API_URL=<cloud-run-url>`.

## Security

Project hardened in May 2026 (see commit history). Key model:

- **Auth**: Firebase ID token via `Authorization: Bearer <token>`. Set `ENABLE_FIREBASE=1` in prod — bad/expired tokens then return **401** (fail-closed). When unset, runs in legacy demo mode (anonymous allowed).
- **Ownership**: every analysis carries `owner_uid`. All `/api/v1/analyses/{id}/*` routes (get, export.json/csv, report.pdf, chat, chat/stream, benchmark, delete, clause TTS, compare) 404 on cross-user access. List endpoint scopes to caller. Dedupe cache is per-user.
- **Rate limit**: per-uid bucket when signed in, per-IP otherwise. Set `TRUST_PROXY=1` on Cloud Run / behind a known LB so `X-Forwarded-For` is read from the rightmost (trusted) hop; otherwise XFF is ignored to block spoofing.
- **Prompt injection**: contract text is wrapped in `<contract_text>` / `<clauses>` delimiters and tag-stripped before insertion. System prompts mark those blocks untrusted and refuse to follow instructions inside them.
- **Firestore rules**: see `firestore.rules`. Reads/deletes gated on `request.auth.uid == uid`; writes are admin-SDK only; default-deny everything else. Deploy with `firebase deploy --only firestore:rules`.
- **Container**: `apps/api/Dockerfile` runs as non-root (`USER app`, UID 1001).
- **CI**: least-privilege `permissions:`, `persist-credentials: false`, `pnpm install --frozen-lockfile --ignore-scripts` so an untrusted PR cannot pull arbitrary deps with install scripts.
- **Errors**: pipeline/chat exceptions are logged server-side; clients see a generic message (no internal paths or key prefixes leaked).

Env flags relevant to security:
| Var | Default | Notes |
|-----|---------|-------|
| `ENABLE_FIREBASE` | `0` | `1` in prod. Required to enforce auth. |
| `TRUST_PROXY` | `0` | `1` only when behind a trusted LB (Cloud Run, GCLB). |
| `CORS_ORIGIN` | `http://localhost:3000` | Comma-separated. Never set to `*` with auth. |

## Limits (hackathon-by-design)
- In-memory store: process restart wipes the analysis cache (Firestore persists per-user history when `ENABLE_FIREBASE=1`).
- Scanned/image PDFs handled via Document AI fallback when `GCP_PROJECT_ID` + `DOCAI_PROCESSOR_ID` are set.
- English / Hindi only (lang-detect rejects others).
