"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Diff = {
  clause_id: string;
  clause_type: string;
  user_text: string;
  standard_text: string;
  divergence_score: number;
  label: "similar" | "diverges" | "more_restrictive";
  risk_label: string;
  risk_score: number;
};

const LABEL_COLOR: Record<string, string> = {
  similar: "text-green-400",
  diverges: "text-yellow-400",
  more_restrictive: "text-red-400",
};

export default function BenchmarkDiff({ analysisId }: { analysisId: string }) {
  const [diffs, setDiffs] = useState<Diff[] | null>(null);
  const [contractType, setContractType] = useState<string>("");

  useEffect(() => {
    fetch(`${API}/api/v1/analyses/${analysisId}/benchmark`)
      .then((r) => r.json())
      .then((j) => {
        setDiffs(j.data?.diffs || []);
        setContractType(j.data?.contract_type || "");
      });
  }, [analysisId]);

  if (diffs === null) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => <div key={i} className="h-24 animate-pulse rounded bg-neutral-800/60" />)}
      </div>
    );
  }
  if (diffs.length === 0)
    return (
      <div className="flex h-full flex-col items-center justify-center py-12 text-center">
        <div className="text-3xl">📊</div>
        <p className="mt-3 text-sm text-neutral-400">No benchmark available for {contractType || "this contract type"}.</p>
        <p className="mt-1 text-xs text-neutral-600">Benchmark seeded for: employment, freelance, rental, saas, tos, privacy_policy, vendor_nda.</p>
      </div>
    );

  return (
    <div className="space-y-4">
      <p className="text-sm text-neutral-400">
        Comparing your contract against standard {contractType} clauses.
      </p>
      {diffs.map((d) => (
        <div key={d.clause_id} className="rounded-md border border-neutral-800 bg-neutral-950 p-4">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-wide text-neutral-500">{d.clause_type}</div>
            <div className={`text-xs font-semibold ${LABEL_COLOR[d.label]}`}>
              {d.label.replace("_", " ")} · divergence {(d.divergence_score * 100).toFixed(0)}%
            </div>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <div className="text-xs text-neutral-500">Your contract</div>
              <p className="mt-1 text-sm text-neutral-200">{d.user_text}</p>
            </div>
            <div>
              <div className="text-xs text-neutral-500">Standard</div>
              <p className="mt-1 text-sm text-neutral-400">{d.standard_text}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
