"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type AnalysisListItem = {
  id: string;
  filename: string;
  contract_type: string;
  perspective: string;
  overall_score: number;
  overall_label: string;
  clause_count: number;
  created_at: number;
};

type CompareResult = {
  prev_id: string;
  new_id: string;
  prev_score: number;
  new_score: number;
  overall_delta: number;
  verdict: "better" | "worse" | "neutral";
  added: any[];
  removed: any[];
  changed: any[];
  unchanged: any[];
  summary: { added: number; removed: number; changed: number; unchanged: number };
};

const RISK_COLORS: Record<string, string> = {
  Low: "bg-green-700/90", Medium: "bg-yellow-600/90", High: "bg-orange-600/90", Critical: "bg-red-700/90",
};

function ComparePageInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [list, setList] = useState<AnalysisListItem[]>([]);
  const [prev, setPrev] = useState(params.get("prev") || "");
  const [next, setNext] = useState(params.get("new") || "");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/v1/analyses`).then((r) => r.json()).then((j) => setList(j.data?.analyses || []));
  }, []);

  useEffect(() => {
    if (!prev || !next || prev === next) {
      setResult(null);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(`${API}/api/v1/compare?prev=${prev}&new=${next}`)
      .then((r) => r.json())
      .then((j) => {
        if (j.error || !j.data) throw new Error(j.error || j.detail || "Failed");
        setResult(j.data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [prev, next]);

  const verdictColor =
    result?.verdict === "worse" ? "text-red-400" : result?.verdict === "better" ? "text-green-400" : "text-neutral-400";

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 fade-in">
      <div>
        <Link href="/" className="text-xs text-neutral-500 hover:text-white">← Home</Link>
        <h1 className="mt-2 text-2xl font-bold">Compare contract versions</h1>
        <p className="mt-1 text-sm text-neutral-400">
          Pick two prior analyses to diff clause-by-clause. Useful when negotiating: did the new draft get better or worse?
        </p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
        {[
          { label: "Previous version (v1)", value: prev, setter: setPrev },
          { label: "New version (v2)", value: next, setter: setNext },
        ].map((s) => (
          <div key={s.label}>
            <label className="block text-xs font-medium uppercase tracking-wide text-neutral-500">{s.label}</label>
            <select
              value={s.value}
              onChange={(e) => s.setter(e.target.value)}
              className="mt-1 block w-full rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
            >
              <option value="">Select…</option>
              {list.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.filename} · {a.contract_type} · {a.overall_score.toFixed(0)} {a.overall_label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {list.length < 2 && (
        <p className="mt-6 rounded-md border border-yellow-900/60 bg-yellow-950/30 p-4 text-sm text-yellow-100">
          Analyze at least 2 contracts first. <Link href="/upload" className="underline">Upload one →</Link>
        </p>
      )}

      {error && <p className="mt-6 rounded-md border border-red-900 bg-red-950/30 p-4 text-sm text-red-200">{error}</p>}

      {loading && <p className="mt-6 text-sm text-neutral-500">Comparing…</p>}

      {result && (
        <section className="mt-10 space-y-6 fade-in">
          <div className="rounded-lg border border-neutral-800 bg-neutral-950 p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-xs uppercase tracking-wide text-neutral-500">Overall verdict</div>
                <div className={`mt-1 text-2xl font-bold capitalize ${verdictColor}`}>{result.verdict}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-neutral-500">Risk score</div>
                <div className="text-2xl font-bold">
                  {result.prev_score.toFixed(0)} → {result.new_score.toFixed(0)}
                  <span className={`ml-2 text-sm ${result.overall_delta > 0 ? "text-red-400" : result.overall_delta < 0 ? "text-green-400" : "text-neutral-500"}`}>
                    {result.overall_delta > 0 ? "+" : ""}{result.overall_delta}
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-4 gap-2 text-center text-sm">
              <div className="rounded bg-green-950/40 p-2"><div className="font-bold text-green-300">{result.summary.added}</div><div className="text-xs text-neutral-400">added</div></div>
              <div className="rounded bg-red-950/40 p-2"><div className="font-bold text-red-300">{result.summary.removed}</div><div className="text-xs text-neutral-400">removed</div></div>
              <div className="rounded bg-yellow-950/40 p-2"><div className="font-bold text-yellow-300">{result.summary.changed}</div><div className="text-xs text-neutral-400">changed</div></div>
              <div className="rounded bg-neutral-900 p-2"><div className="font-bold text-neutral-300">{result.summary.unchanged}</div><div className="text-xs text-neutral-400">unchanged</div></div>
            </div>
          </div>

          {result.changed.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold">Changed clauses</h2>
              <div className="mt-3 space-y-3">
                {result.changed.map((c, i) => (
                  <div key={i} className="rounded-md border border-yellow-900/60 bg-yellow-950/10 p-4">
                    <div className="flex items-center justify-between text-xs">
                      <span className="uppercase tracking-wide text-neutral-400">{c.type}</span>
                      <span className={c.risk_score_delta > 0 ? "text-red-400" : "text-green-400"}>
                        {c.prev_risk_score.toFixed(0)} → {c.new_risk_score.toFixed(0)} ({c.risk_score_delta > 0 ? "+" : ""}{c.risk_score_delta})
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div>
                        <div className="text-xs text-neutral-500">v1 — <span className={`rounded px-1 py-0.5 text-[10px] ${RISK_COLORS[c.prev_risk_label]}`}>{c.prev_risk_label}</span></div>
                        <p className="mt-1 text-sm text-neutral-300 line-through opacity-70">{c.prev_text}</p>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-500">v2 — <span className={`rounded px-1 py-0.5 text-[10px] ${RISK_COLORS[c.new_risk_label]}`}>{c.new_risk_label}</span></div>
                        <p className="mt-1 text-sm text-neutral-100">{c.new_text}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.added.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-green-300">Added in v2</h2>
              <ul className="mt-3 space-y-2">
                {result.added.map((c, i) => (
                  <li key={i} className="rounded-md border border-green-900/60 bg-green-950/10 p-3 text-sm">
                    <div className="flex items-center justify-between text-xs">
                      <span className="uppercase tracking-wide text-neutral-400">{c.type}</span>
                      <span className={`rounded px-1.5 py-0.5 ${RISK_COLORS[c.risk_label]}`}>{c.risk_score.toFixed(0)} {c.risk_label}</span>
                    </div>
                    <p className="mt-1 text-neutral-200">{c.text}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.removed.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-red-300">Removed in v2</h2>
              <ul className="mt-3 space-y-2">
                {result.removed.map((c, i) => (
                  <li key={i} className="rounded-md border border-red-900/60 bg-red-950/10 p-3 text-sm">
                    <div className="flex items-center justify-between text-xs">
                      <span className="uppercase tracking-wide text-neutral-400">{c.type}</span>
                      <span className={`rounded px-1.5 py-0.5 ${RISK_COLORS[c.risk_label]}`}>{c.risk_score.toFixed(0)} {c.risk_label}</span>
                    </div>
                    <p className="mt-1 text-neutral-200 line-through opacity-70">{c.text}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </main>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<main className="p-8 text-neutral-400">Loading…</main>}>
      <ComparePageInner />
    </Suspense>
  );
}
