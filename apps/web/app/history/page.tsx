"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth, authedFetch } from "@/components/AuthProvider";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Item = {
  id: string;
  filename: string;
  contract_type: string;
  perspective: string;
  overall_score: number;
  overall_label: string;
  clause_count: number;
  created_at: number;
};

const COLOR: Record<string, string> = {
  Low: "bg-green-700/90",
  Medium: "bg-yellow-600/90",
  High: "bg-orange-600/90",
  Critical: "bg-red-700/90",
};

export default function HistoryPage() {
  const { user, loading, enabled, getToken } = useAuth();
  const [items, setItems] = useState<Item[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    authedFetch(getToken, `${API}/api/v1/me/analyses`)
      .then((r) => r.json())
      .then((j) => {
        if (!j.data) throw new Error(j.detail || "Failed");
        setItems(j.data.analyses);
      })
      .catch((e) => setErr(e.message));
  }, [user, getToken]);

  if (!enabled)
    return (
      <main className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h1 className="text-2xl font-bold">History unavailable</h1>
        <p className="mt-2 text-neutral-400">
          Set <code>NEXT_PUBLIC_FIREBASE_*</code> env vars + <code>ENABLE_FIREBASE=1</code>,{" "}
          <code>ENABLE_FIRESTORE=1</code> on the backend.
        </p>
      </main>
    );
  if (loading) return <main className="mx-auto max-w-2xl px-6 py-24 text-center text-neutral-500">Loading…</main>;
  if (!user)
    return (
      <main className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h1 className="text-2xl font-bold">Sign in to view history</h1>
        <p className="mt-2 text-neutral-400">Your analyses get saved to Firestore when signed in.</p>
      </main>
    );

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 fade-in">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold">Your analyses</h1>
          <p className="mt-1 text-sm text-neutral-400">Signed in as {user.email}</p>
        </div>
        <Link href="/upload" className="rounded-md bg-white px-4 py-2 text-sm font-medium text-black">
          + Analyze new
        </Link>
      </header>

      {err && <p className="mt-6 rounded border border-red-900/60 bg-red-950/30 p-3 text-sm text-red-200">{err}</p>}

      {items === null ? (
        <div className="mt-8 space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded border border-neutral-800 bg-neutral-950" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="mt-12 text-center text-neutral-500">No analyses yet.</p>
      ) : (
        <ul className="mt-6 space-y-2">
          {items.map((a) => (
            <li key={a.id}>
              <Link
                href={`/analyses/${a.id}`}
                className="flex items-center gap-4 rounded-md border border-neutral-800 bg-neutral-950 p-4 hover:border-neutral-600"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{a.filename}</div>
                  <div className="text-xs text-neutral-500">
                    {a.contract_type} · {a.perspective} · {a.clause_count} clauses
                  </div>
                </div>
                <span className={`shrink-0 rounded px-2 py-1 text-xs font-semibold ${COLOR[a.overall_label] || "bg-neutral-700"}`}>
                  {a.overall_score?.toFixed(0) ?? "—"} {a.overall_label}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
