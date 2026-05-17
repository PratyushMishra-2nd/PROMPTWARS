"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/Toast";
import { useAuth, authedFetch } from "@/components/AuthProvider";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PERSPECTIVES = [
  { value: "employee", label: "Employee" },
  { value: "freelancer", label: "Freelancer" },
  { value: "tenant", label: "Tenant" },
  { value: "customer", label: "Customer / Subscriber" },
  { value: "buyer", label: "Buyer / Counterparty" },
];

const TYPE_FALLBACK = [
  { value: "", label: "Auto-detect" },
  { value: "employment", label: "Employment" },
  { value: "freelance", label: "Freelance" },
  { value: "rental", label: "Rental / Lease" },
  { value: "saas", label: "SaaS" },
  { value: "tos", label: "Terms of Service" },
  { value: "privacy_policy", label: "Privacy Policy" },
  { value: "vendor_nda", label: "Vendor / NDA" },
];

const STAGE_ORDER = ["extracting", "scoring", "explaining", "done"] as const;

export default function UploadPage() {
  const router = useRouter();
  const toast = useToast();
  const { getToken } = useAuth();
  const [mode, setMode] = useState<"file" | "paste">("file");
  const [file, setFile] = useState<File | null>(null);
  const [pasted, setPasted] = useState("");
  const [perspective, setPerspective] = useState("employee");
  const [contractType, setContractType] = useState("");
  const [types, setTypes] = useState(TYPE_FALLBACK);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/v1/contract-types`)
      .then((r) => r.json())
      .then((j) => {
        if (j?.data?.types) {
          const labels: Record<string, string> = {
            employment: "Employment", freelance: "Freelance", rental: "Rental / Lease",
            saas: "SaaS", tos: "Terms of Service", privacy_policy: "Privacy Policy", vendor_nda: "Vendor / NDA",
          };
          setTypes([{ value: "", label: "Auto-detect" }, ...j.data.types.map((v: string) => ({ value: v, label: labels[v] || v }))]);
        }
      })
      .catch(() => {});
  }, []);

  async function submitFile() {
    if (!file) throw new Error("No file selected");
    setStage("uploading");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("perspective", perspective);
    if (contractType) fd.append("contractType", contractType);

    const res = await authedFetch(getToken, `${API}/api/v1/analyze/stream`, { method: "POST", body: fd });
    if (!res.ok || !res.body) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.detail || `HTTP ${res.status}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let analysisId: string | null = null;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const events = buf.split("\n\n");
      buf = events.pop() || "";
      for (const ev of events) {
        let evName = "message";
        let evData = "";
        for (const ln of ev.split("\n")) {
          if (ln.startsWith("event:")) evName = ln.slice(6).trim();
          else if (ln.startsWith("data:")) evData += ln.slice(5).trim();
        }
        if (evName === "error") throw new Error(JSON.parse(evData).message || evData);
        if (evName === "result") {
          try { analysisId = JSON.parse(evData).analysisId; } catch {}
        } else if (STAGE_ORDER.includes(evName as any)) {
          setStage(evName);
        }
      }
    }
    if (!analysisId) throw new Error("No result received");
    return analysisId;
  }

  async function submitText() {
    setStage("scoring");
    const res = await fetch(`${API}/api/v1/analyze/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: pasted, perspective, contractType: contractType || null, filename: "pasted-contract.txt" }),
    });
    const j = await res.json();
    if (!res.ok) throw new Error(j.detail || `HTTP ${res.status}`);
    if (j.data?.deduped) toast.push("info", "Already analyzed — showing cached result.");
    return j.data.analysisId as string;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const aid = mode === "file" ? await submitFile() : await submitText();
      router.push(`/analyses/${aid}`);
    } catch (err: any) {
      toast.push("error", err.message || "Analysis failed");
      setLoading(false);
    }
  }

  const canSubmit = mode === "file" ? !!file : pasted.trim().length >= 100;
  const stageIdx = STAGE_ORDER.indexOf(stage as any);
  const progressPct = stageIdx >= 0 ? ((stageIdx + 1) / STAGE_ORDER.length) * 100 : 5;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12 fade-in">
      <h1 className="text-3xl font-bold">Analyze a contract</h1>
      <p className="mt-2 text-neutral-400">Upload PDF/DOCX or paste raw text. Nothing is stored after this session.</p>

      <div className="mt-6 inline-flex rounded-md border border-neutral-800 p-1 text-sm">
        {(["file", "paste"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded px-4 py-1.5 transition-colors ${mode === m ? "bg-white text-black" : "text-neutral-300 hover:text-white"}`}
          >
            {m === "file" ? "Upload file" : "Paste text"}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="mt-6 space-y-6">
        {mode === "file" ? (
          <label
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) setFile(f);
            }}
            className={`block cursor-pointer rounded-md border-2 border-dashed p-8 text-center transition-colors ${
              dragOver ? "border-white bg-neutral-900" : "border-neutral-700 hover:border-neutral-500"
            }`}
          >
            <input type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files?.[0] || null)} className="hidden" />
            {file ? (
              <div>
                <div className="font-medium">{file.name}</div>
                <div className="text-xs text-neutral-500">{(file.size / 1024).toFixed(0)} KB · click or drop to replace</div>
              </div>
            ) : (
              <div>
                <div className="text-sm text-neutral-300">Drag a file here, or click to browse</div>
                <div className="mt-1 text-xs text-neutral-500">PDF or DOCX · up to 25 MB</div>
              </div>
            )}
          </label>
        ) : (
          <div>
            <textarea
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              rows={12}
              placeholder="Paste contract, ToS, or privacy policy text here…"
              className="block w-full rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 font-mono text-xs focus:border-neutral-500 focus:outline-none"
            />
            <div className="mt-1 flex justify-between text-xs text-neutral-500">
              <span>{pasted.length.toLocaleString()} chars</span>
              <span>{pasted.length < 100 ? `${100 - pasted.length} more to start` : "ready"}</span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-neutral-400">Your perspective</label>
            <select value={perspective} onChange={(e) => setPerspective(e.target.value)}
              className="mt-1 block w-full rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
              {PERSPECTIVES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-400">Contract type</label>
            <select value={contractType} onChange={(e) => setContractType(e.target.value)}
              className="mt-1 block w-full rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
              {types.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
        </div>

        {loading && (
          <div className="space-y-2 rounded-md border border-neutral-800 bg-neutral-950 p-4">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-800">
              <div className="h-full rounded-full bg-white transition-all duration-500" style={{ width: `${progressPct}%` }} />
            </div>
            <div className="flex justify-between text-xs">
              {STAGE_ORDER.map((s, i) => (
                <span key={s} className={i <= stageIdx ? "text-white" : "text-neutral-600"}>
                  {i < stageIdx ? "✓ " : i === stageIdx ? "● " : "○ "}{s}
                </span>
              ))}
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit || loading}
          className="w-full rounded-md bg-white px-5 py-3 text-sm font-semibold text-black transition-colors hover:bg-neutral-200 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </form>
    </main>
  );
}
