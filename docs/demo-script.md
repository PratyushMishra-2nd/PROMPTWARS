# Demo script

3 prepared contracts. Walk judges through golden path.

## Setup
1. Backend: `cd apps/api && uvicorn app.main:app --port 8000`
2. Frontend: `cd apps/web && pnpm dev`
3. Open `http://localhost:3000`
4. Have 3 sample PDFs ready in `docs/samples/`:
   - `employment_aggressive.pdf` — 12-page offer with 18-month non-compete, broad IP assignment, at-will termination
   - `lease_landlord_friendly.pdf` — residential lease with no-notice entry, 90-day cancellation penalty
   - `saas_tos.pdf` — SaaS terms with auto-renewal, binding arbitration + class-action waiver

**Easiest demo path:** use the **Paste text** tab on `/upload` with the prepared samples in `docs/samples/`. No PDF conversion needed.

## Flow (90 seconds)
1. Open `/upload`, click **Paste text** tab.
2. Copy contents of `docs/samples/employment_aggressive.txt`, paste, perspective = Employee, type = Auto-detect.
3. SSE progress runs: extracting → scoring → explaining → done. (~30–45s)
4. **Risk dashboard** opens. Point at overall score (should be ~80+, Critical).
5. Show **Contradictions panel** at top if any surfaced by adversarial reviewer.
6. Click the **non-compete** clause → side panel shows plain explanation + scenario + suggested redline.
7. Switch tab to **chat**. Ask: *"Can they fire me without cause?"* — answer cites a clause id like `[cl3]`.
8. **Click the citation chip** — view auto-switches to detail tab, scrolls to that clause, briefly highlights it yellow. This is the wow moment.
9. Switch tab to **benchmark**. Show non-compete row labeled "more restrictive" with side-by-side diff vs standard 6-month/25-mile baseline.
10. Click **Download PDF report** — opens WeasyPrint-rendered report.

## Talking points
- Single Gemini Pro mega-call = 60% token savings vs naive multi-agent.
- Adversarial reviewer = differentiator vs summarizers (surfaces what first pass missed).
- Risk score is hybrid: LLM severity + rulebook + benchmark divergence, perspective-weighted.
- $5 GCP credit covers 60+ analyses; AI Studio free tier makes most dev runs $0.
- Zero infra: no DB, no queue, no auth — single FastAPI process.

## Resilience
- If process restarts mid-demo, all analyses lost. Re-upload.
- If chat hits rate limit, switch `GEMINI_PROVIDER` to vertex (post-MVP).
