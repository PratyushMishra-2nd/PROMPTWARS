"use client";

import { use, useEffect, useState, useRef } from "react";
import Link from "next/link";
import Chat from "@/components/Chat";
import BenchmarkDiff from "@/components/BenchmarkDiff";
import { DashboardSkeleton } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Clause = {
  id: string;
  type: string;
  text: string;
  page_number: number;
  risk_score: number;
  risk_label: "Low" | "Medium" | "High" | "Critical";
  top_reasons: string[];
  affected_interest: string;
  plain_explanation: string;
  real_world_scenario?: string;
  suggested_redline?: string;
  confidence?: number;
};

type Analysis = {
  id: string;
  filename: string;
  contract_type: string;
  perspective: string;
  stage: string;
  overall_score: number;
  overall_label: string;
  top_risk_clause_ids: string[];
  clauses: Clause[];
  contradictions: string[];
  error_message?: string | null;
};

const RISK_COLORS: Record<string, string> = {
  Low: "bg-green-700/90",
  Medium: "bg-yellow-600/90",
  High: "bg-orange-600/90",
  Critical: "bg-red-700/90",
};

const RISK_ICON: Record<string, string> = {
  Low: "●",
  Medium: "◆",
  High: "▲",
  Critical: "■",
};

const RISK_RING: Record<string, string> = {
  Low: "ring-green-700/50",
  Medium: "ring-yellow-600/50",
  High: "ring-orange-600/50",
  Critical: "ring-red-700/50",
};

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const toast = useToast();
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Clause | null>(null);
  const [tab, setTab] = useState<"detail" | "chat" | "benchmark">("detail");
  const [filter, setFilter] = useState<"all" | "Critical" | "High" | "Medium" | "Low">("all");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const clauseRefs = useRef<Record<string, HTMLLIElement | null>>({});
  const audioRef = useRef<HTMLAudioElement | null>(null);

  function stopAudio() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setPlayingId(null);
  }

  function toggleAudio(clauseId: string) {
    if (playingId === clauseId) {
      stopAudio();
      return;
    }
    stopAudio();
    const audio = new Audio(`${API}/api/v1/clauses/${id}/${clauseId}/tts.mp3`);
    audio.onended = () => setPlayingId(null);
    audio.onerror = () => {
      toast.push("error", "TTS unavailable. Enable ENABLE_TTS in backend env.");
      setPlayingId(null);
    };
    audio.play().then(() => {
      audioRef.current = audio;
      setPlayingId(clauseId);
    }).catch(() => {
      toast.push("error", "TTS unavailable. Enable ENABLE_TTS in backend env.");
      setPlayingId(null);
    });
  }

  // stop audio on unmount
  useEffect(() => stopAudio, []);

  useEffect(() => {
    fetch(`${API}/api/v1/analyses/${id}`)
      .then((r) => r.json())
      .then((j) => {
        if (j.error || !j.data) setError(j.error || "Not found");
        else setData(j.data);
      })
      .catch((e) => setError(e.message));
  }, [id]);

  function jumpToClause(clauseId: string) {
    if (!data) return;
    const c = data.clauses.find((x) => x.id === clauseId);
    if (!c) {
      toast.push("info", `Citation [${clauseId}] not found in clause list`);
      return;
    }
    setSelected(c);
    setTab("detail");
    setHighlightId(clauseId);
    setFilter("all");
    setTimeout(() => clauseRefs.current[clauseId]?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
    setTimeout(() => setHighlightId(null), 2000);
  }

  if (error) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h1 className="text-2xl font-bold text-red-400">Analysis not found</h1>
        <p className="mt-2 text-neutral-400">{error}. Backend may have restarted (analyses are in-memory).</p>
        <a href="/upload" className="mt-6 inline-block rounded-md bg-white px-5 py-2 text-sm font-medium text-black">Start over</a>
      </main>
    );
  }
  if (!data) return <DashboardSkeleton />;

  const q = search.trim().toLowerCase();
  const filtered = data.clauses.filter((c) => {
    if (filter !== "all" && c.risk_label !== filter) return false;
    if (typeFilter && c.type !== typeFilter) return false;
    if (q && !c.text.toLowerCase().includes(q) && !c.type.toLowerCase().includes(q) && !c.plain_explanation.toLowerCase().includes(q)) return false;
    return true;
  });
  const sorted = [...filtered].sort((a, b) => b.risk_score - a.risk_score);

  const clauseTypes = Array.from(new Set(data.clauses.map((c) => c.type))).sort();

  const counts = data.clauses.reduce((acc: Record<string, number>, c) => {
    acc[c.risk_label] = (acc[c.risk_label] || 0) + 1;
    return acc;
  }, {});

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 fade-in">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <span className="rounded bg-neutral-900 px-2 py-0.5">{data.contract_type}</span>
            <span>perspective: {data.perspective}</span>
          </div>
          <h1 className="mt-2 truncate text-2xl font-bold">{data.filename}</h1>
        </div>
        <div className="text-right">
          <div className="text-xs text-neutral-500">Overall risk</div>
          <div className={`mt-1 inline-block rounded-md px-4 py-2 text-2xl font-bold ring-2 ring-offset-2 ring-offset-black ${RISK_COLORS[data.overall_label] || "bg-neutral-700"} ${RISK_RING[data.overall_label] || ""}`}>
            {data.overall_score.toFixed(0)} <span className="ml-1 text-sm">{data.overall_label}</span>
          </div>
          <div className="mt-2 flex flex-wrap justify-end gap-2 text-xs">
            <a href={`${API}/api/v1/analyses/${id}/report.pdf`} className="text-neutral-400 underline hover:text-white">PDF</a>
            <a href={`${API}/api/v1/analyses/${id}/export.json`} className="text-neutral-400 underline hover:text-white">JSON</a>
            <a href={`${API}/api/v1/analyses/${id}/export.csv`} className="text-neutral-400 underline hover:text-white">CSV</a>
            <Link href={`/compare?prev=${id}`} className="text-neutral-400 underline hover:text-white">Compare vs…</Link>
          </div>
        </div>
      </header>

      {data.error_message && (
        <section className="mt-6 rounded-md border border-red-900/60 bg-red-950/30 p-4 fade-in">
          <h2 className="text-sm font-semibold text-red-300">⚠ Extraction error</h2>
          <p className="mt-2 break-words text-sm text-red-100">{data.error_message}</p>
          <p className="mt-2 text-xs text-red-300/70">Check backend terminal for full Gemini error. Common causes: invalid API key, rate limit, doc too short.</p>
        </section>
      )}

      {data.clauses.length === 0 && !data.error_message && (
        <section className="mt-6 rounded-md border border-yellow-900/60 bg-yellow-950/30 p-4 fade-in">
          <h2 className="text-sm font-semibold text-yellow-300">No clauses extracted</h2>
          <p className="mt-2 text-sm text-yellow-100">
            Gemini returned zero clauses. Pasted text may be too short or not contract-like. Try one of the samples in <code>docs/samples/</code>.
          </p>
        </section>
      )}

      {data.contradictions && data.contradictions.length > 0 && (
        <section className="mt-6 rounded-md border border-red-900/60 bg-red-950/20 p-4 fade-in">
          <h2 className="text-sm font-semibold text-red-300">⚠ Contradictions detected ({data.contradictions.length})</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-red-100">
            {data.contradictions.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </section>
      )}

      {/* risk-tier summary */}
      <section className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {(["Critical", "High", "Medium", "Low"] as const).map((tier) => (
          <button
            key={tier}
            onClick={() => setFilter(filter === tier ? "all" : tier)}
            className={`rounded-md border p-3 text-left transition-colors ${
              filter === tier ? "border-white bg-neutral-900" : "border-neutral-800 bg-neutral-950 hover:border-neutral-600"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${RISK_COLORS[tier]}`} />
              <span className="text-xs uppercase tracking-wide text-neutral-400">{tier}</span>
            </div>
            <div className="mt-1 text-2xl font-bold">{counts[tier] || 0}</div>
          </button>
        ))}
      </section>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_400px]">
        <section aria-labelledby="clause-list-heading">
          <div className="flex items-center justify-between">
            <h2 id="clause-list-heading" className="text-base font-semibold">
              Clauses <span className="text-neutral-500">({sorted.length}{(filter !== "all" || typeFilter || q) ? ` of ${data.clauses.length}` : ""})</span>
            </h2>
            {(filter !== "all" || typeFilter || q) && (
              <button onClick={() => { setFilter("all"); setTypeFilter(""); setSearch(""); }}
                className="text-xs text-neutral-400 hover:text-white">
                Clear all
              </button>
            )}
          </div>

          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <label htmlFor="clause-search" className="sr-only">Search clauses</label>
            <input
              id="clause-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search clause text…"
              className="flex-1 rounded-md border border-neutral-800 bg-neutral-950 px-3 py-1.5 text-sm focus:border-neutral-600 focus:outline-none"
            />
            <label htmlFor="type-filter" className="sr-only">Filter by clause type</label>
            <select
              id="type-filter"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-1.5 text-sm"
            >
              <option value="">All types</option>
              {clauseTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          {sorted.length === 0 ? (
            <p className="mt-4 rounded-md border border-neutral-800 bg-neutral-950 p-6 text-center text-sm text-neutral-500">
              No clauses match this filter.
            </p>
          ) : (
            <ul className="mt-4 space-y-2">
              {sorted.map((c) => (
                <li
                  key={c.id}
                  ref={(el) => { clauseRefs.current[c.id] = el; }}
                  onClick={() => { setSelected(c); setTab("detail"); }}
                  className={`group cursor-pointer rounded-md border p-4 transition-all ${
                    highlightId === c.id
                      ? "border-yellow-400 bg-yellow-950/30 ring-2 ring-yellow-400/50"
                      : selected?.id === c.id
                      ? "border-neutral-500 bg-neutral-900"
                      : "border-neutral-800 bg-neutral-950 hover:border-neutral-600"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-neutral-500">
                        <span className="rounded bg-neutral-800 px-1.5 py-0.5 font-mono text-[10px] normal-case">{c.id}</span>
                        <span>{c.type}</span>
                        {c.page_number > 0 && <span className="text-neutral-600">· p{c.page_number}</span>}
                      </div>
                      <div className="mt-1 line-clamp-2 text-sm">{c.text}</div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <span
                        className={`rounded px-2 py-1 text-xs font-semibold ${RISK_COLORS[c.risk_label] || "bg-neutral-700"}`}
                        aria-label={`Risk ${c.risk_label}, score ${c.risk_score.toFixed(0)} of 100`}
                      >
                        <span aria-hidden="true">{RISK_ICON[c.risk_label]} </span>
                        {c.risk_score.toFixed(0)} {c.risk_label}
                      </span>
                      {c.confidence !== undefined && c.confidence < 0.7 && (
                        <span
                          className="rounded bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-400"
                          aria-label={`Low extraction confidence ${Math.round(c.confidence * 100)} percent`}
                        >
                          {Math.round(c.confidence * 100)}% conf
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="flex h-[70vh] flex-col lg:sticky lg:top-6 lg:h-[calc(100vh-6rem)]">
          <div className="mb-2 flex gap-1 text-xs">
            {(["detail", "chat", "benchmark"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 rounded px-3 py-1.5 capitalize transition-colors ${
                  tab === t ? "bg-white text-black" : "bg-neutral-900 text-neutral-300 hover:text-white"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === "chat" && (
            <div className="min-h-0 flex-1">
              <Chat analysisId={id} onCite={jumpToClause} />
            </div>
          )}
          {tab === "benchmark" && (
            <div className="flex-1 overflow-auto rounded-md border border-neutral-800 bg-neutral-950 p-4">
              <BenchmarkDiff analysisId={id} />
            </div>
          )}
          {tab === "detail" && (
            <div className="flex-1 overflow-auto rounded-md border border-neutral-800 bg-neutral-950 p-5">
              {selected ? (
                <div className="fade-in">
                  <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-neutral-500">
                    <span className="rounded bg-neutral-800 px-1.5 py-0.5 font-mono text-[10px] normal-case">{selected.id}</span>
                    <span>{selected.type}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded px-2 py-1 text-xs font-semibold ${RISK_COLORS[selected.risk_label] || "bg-neutral-700"}`}
                      aria-label={`Risk ${selected.risk_label}, score ${selected.risk_score.toFixed(0)}`}
                    >
                      <span aria-hidden="true">{RISK_ICON[selected.risk_label]} </span>
                      {selected.risk_score.toFixed(0)} · {selected.risk_label}
                    </span>
                    {selected.confidence !== undefined && (
                      <span className="rounded bg-neutral-800 px-2 py-1 text-xs text-neutral-300">
                        {Math.round(selected.confidence * 100)}% confidence
                      </span>
                    )}
                    <span className="rounded bg-neutral-800 px-2 py-1 text-xs text-neutral-300">{selected.affected_interest}</span>
                    <button
                      onClick={() => toggleAudio(selected.id)}
                      className={`ml-auto rounded border px-2 py-1 text-xs transition-colors ${
                        playingId === selected.id
                          ? "border-red-700 bg-red-950 text-red-200 hover:border-red-500"
                          : "border-neutral-700 bg-neutral-900 hover:border-neutral-500"
                      }`}
                      aria-label={playingId === selected.id ? "Stop audio playback" : "Listen to plain-language explanation"}
                      aria-pressed={playingId === selected.id}
                    >
                      {playingId === selected.id ? "⏹ Stop" : "🔊 Listen"}
                    </button>
                  </div>
                  <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">Clause text</h3>
                  <p className="mt-1 max-h-48 overflow-auto rounded bg-neutral-900 p-3 text-sm text-neutral-200">{selected.text}</p>
                  <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">What it means for you</h3>
                  <p className="mt-1 text-sm leading-relaxed text-neutral-200">{selected.plain_explanation || "—"}</p>
                  {selected.real_world_scenario && (
                    <>
                      <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">Real-world scenario</h3>
                      <p className="mt-1 text-sm text-neutral-300">{selected.real_world_scenario}</p>
                    </>
                  )}
                  {selected.suggested_redline && (
                    <>
                      <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">Suggested language</h3>
                      <p className="mt-1 rounded border border-blue-900/50 bg-blue-950/20 p-2 text-sm text-blue-100">{selected.suggested_redline}</p>
                    </>
                  )}
                  {selected.top_reasons?.length > 0 && (
                    <>
                      <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">Why it&apos;s risky</h3>
                      <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-neutral-300">
                        {selected.top_reasons.map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    </>
                  )}
                </div>
              ) : (
                <div className="flex h-full flex-col items-center justify-center text-center">
                  <div className="text-4xl">📄</div>
                  <p className="mt-3 text-sm text-neutral-400">Click any clause to see plain-language analysis.</p>
                  <p className="mt-1 text-xs text-neutral-600">Chat citations like [cl3] jump here.</p>
                </div>
              )}
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}
