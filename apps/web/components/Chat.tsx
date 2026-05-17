"use client";

import { useState, useRef, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Msg = { role: "user" | "assistant"; content: string; citations?: string[]; streaming?: boolean };

export default function Chat({ analysisId, onCite }: { analysisId: string; onCite?: (id: string) => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || busy) return;
    const userMsg: Msg = { role: "user", content: input };
    const next = [...msgs, userMsg];
    setMsgs([...next, { role: "assistant", content: "", streaming: true }]);
    setInput("");
    setBusy(true);

    try {
      const res = await fetch(`${API}/api/v1/analyses/${analysisId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content, history: next.slice(0, -1) }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(j.detail || `HTTP ${res.status}`);
      const content = j.data?.content || "(empty response)";
      const citations = j.data?.citations || [];
      setMsgs([...next, { role: "assistant", content, citations }]);
    } catch (err: any) {
      setMsgs([...next, { role: "assistant", content: "Error: " + (err.message || "unknown") }]);
    } finally {
      setBusy(false);
    }
  }

  function renderContent(text: string) {
    // make [clXX] / [cYY] tokens clickable mid-stream
    const parts = text.split(/(\[[a-zA-Z0-9]+\])/g);
    return parts.map((p, i) => {
      const m = p.match(/^\[([a-zA-Z0-9]+)\]$/);
      if (m) {
        return (
          <button
            key={i}
            onClick={() => onCite?.(m[1])}
            className="mx-0.5 rounded bg-neutral-800 px-1 py-0.5 font-mono text-[11px] text-blue-300 hover:bg-neutral-700"
          >
            [{m[1]}]
          </button>
        );
      }
      return <span key={i}>{p}</span>;
    });
  }

  return (
    <div className="flex h-full flex-col rounded-md border border-neutral-800 bg-neutral-950">
      <div className="border-b border-neutral-800 px-4 py-2 text-sm font-semibold">Ask the contract</div>
      <div className="flex-1 space-y-3 overflow-auto p-4 text-sm">
        {msgs.length === 0 && (
          <div className="space-y-2 text-neutral-500">
            <p>Try one of these:</p>
            <div className="space-y-1">
              {["Can they fire me without cause?", "What happens if I cancel early?", "Can I work for a competitor after?", "Who owns what I build?"].map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="block w-full rounded border border-neutral-800 px-3 py-1.5 text-left text-xs hover:border-neutral-600 hover:text-neutral-300"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-neutral-200" : "text-neutral-300"}>
            <div className="text-xs uppercase text-neutral-500">{m.role}</div>
            <div className="whitespace-pre-wrap">
              {renderContent(m.content)}
              {m.streaming && <span className="ml-1 inline-block h-3 w-1.5 animate-pulse bg-neutral-400 align-middle" />}
            </div>
            {m.citations && m.citations.length > 0 && (
              <div className="mt-1 text-xs text-neutral-500">
                Sources:{" "}
                {m.citations.map((c) => (
                  <button
                    key={c}
                    onClick={() => onCite?.(c)}
                    className="mr-1 rounded bg-neutral-800 px-1.5 py-0.5 font-mono text-[10px] hover:bg-neutral-700"
                  >
                    [{c}]
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={send} className="flex gap-2 border-t border-neutral-800 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this contract…"
          className="flex-1 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-md bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
