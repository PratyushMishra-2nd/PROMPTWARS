"""WeasyPrint PDF report renderer. In-process, no external service."""
from __future__ import annotations
from . import store

_COLORS = {"Low": "#16a34a", "Medium": "#eab308", "High": "#f97316", "Critical": "#dc2626"}


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_html(a: store.Analysis) -> str:
    sorted_clauses = sorted(a.clauses, key=lambda c: c.risk_score, reverse=True)
    rows = []
    for c in sorted_clauses:
        color = _COLORS.get(c.risk_label, "#737373")
        reasons = "".join(f"<li>{_esc(r)}</li>" for r in (c.top_reasons or [])[:4])
        rows.append(f"""
        <section class="clause">
          <header>
            <span class="chip" style="background:{color}">{c.risk_score:.0f} · {c.risk_label}</span>
            <span class="ctype">{_esc(c.type)}</span>
            <span class="page">page {c.page_number}</span>
          </header>
          <blockquote>{_esc(c.text)}</blockquote>
          <p class="explain">{_esc(c.plain_explanation)}</p>
          {('<p class="scenario"><b>Scenario:</b> ' + _esc(c.real_world_scenario) + '</p>') if c.real_world_scenario else ''}
          {('<p class="redline"><b>Suggested language:</b> ' + _esc(c.suggested_redline) + '</p>') if c.suggested_redline else ''}
          {('<ul class="reasons">' + reasons + '</ul>') if reasons else ''}
        </section>""")

    overall_color = _COLORS.get(a.overall_label, "#737373")

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>LexGuard Report — {_esc(a.filename)}</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; color: #111; font-size: 11pt; line-height: 1.45; }}
  h1 {{ font-size: 22pt; margin: 0 0 4pt; }}
  .meta {{ color: #555; font-size: 10pt; margin-bottom: 16pt; }}
  .overall {{ display: inline-block; padding: 10pt 16pt; border-radius: 6pt; color: #fff; font-weight: 700; font-size: 16pt; background: {overall_color}; }}
  h2 {{ font-size: 14pt; margin: 24pt 0 8pt; border-bottom: 1pt solid #ddd; padding-bottom: 4pt; }}
  .clause {{ margin: 14pt 0; padding: 10pt 12pt; border: 1pt solid #e5e5e5; border-radius: 4pt; page-break-inside: avoid; }}
  .clause header {{ display: flex; gap: 8pt; align-items: center; margin-bottom: 6pt; }}
  .chip {{ color: #fff; padding: 2pt 8pt; border-radius: 12pt; font-size: 9pt; font-weight: 700; }}
  .ctype {{ font-size: 10pt; color: #444; text-transform: uppercase; letter-spacing: 0.4pt; }}
  .page {{ font-size: 9pt; color: #888; margin-left: auto; }}
  blockquote {{ margin: 6pt 0; padding: 6pt 10pt; background: #fafafa; border-left: 3pt solid #ccc; font-style: italic; color: #333; }}
  .explain {{ margin: 6pt 0; }}
  .scenario, .redline {{ margin: 4pt 0; font-size: 10pt; color: #333; }}
  .reasons {{ margin: 6pt 0 0 16pt; font-size: 10pt; color: #444; }}
  footer {{ margin-top: 24pt; font-size: 9pt; color: #888; }}
</style></head>
<body>
  <h1>LexGuard Risk Report</h1>
  <div class="meta">{_esc(a.filename)} · {_esc(a.contract_type)} · perspective: {_esc(a.perspective)}</div>
  <div class="overall">Overall: {a.overall_score:.0f} · {_esc(a.overall_label)}</div>

  <h2>Flagged clauses ({len(sorted_clauses)})</h2>
  {''.join(rows)}

  <footer>LexGuard — informational only. Not legal advice.</footer>
</body></html>"""


def render_pdf_bytes(a: store.Analysis) -> bytes:
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise RuntimeError(
            "WeasyPrint not installed. Install with: pip install -e .[pdf] "
            "and install GTK runtime on Windows."
        ) from e
    return HTML(string=render_html(a)).write_pdf()
