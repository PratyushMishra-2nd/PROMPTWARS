"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Status = {
  gemini: boolean;
  cloud_logging: boolean;
  tts: boolean;
  translation: boolean;
  document_ai: boolean;
  firebase_auth: boolean;
  firestore: boolean;
};

const LABELS: Record<keyof Status, string> = {
  gemini: "Gemini",
  cloud_logging: "Cloud Logging",
  tts: "Text-to-Speech",
  translation: "Translation",
  document_ai: "Document AI",
  firebase_auth: "Firebase Auth",
  firestore: "Firestore",
};

export default function ServiceBadges() {
  const [s, setS] = useState<Status | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/services/status`).then((r) => r.json()).then((j) => setS(j.data)).catch(() => {});
  }, []);

  if (!s) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs" aria-label="Active Google Cloud services">
      <span className="text-neutral-500">Powered by:</span>
      {(Object.keys(LABELS) as (keyof Status)[]).map((k) => (
        <span
          key={k}
          className={`rounded-full border px-2.5 py-0.5 ${
            s[k]
              ? "border-blue-700 bg-blue-950/40 text-blue-200"
              : "border-neutral-800 bg-neutral-900 text-neutral-600"
          }`}
          title={s[k] ? "Active" : "Disabled — set env var to enable"}
        >
          <span aria-hidden="true">{s[k] ? "●" : "○"}</span> {LABELS[k]}
        </span>
      ))}
    </div>
  );
}
