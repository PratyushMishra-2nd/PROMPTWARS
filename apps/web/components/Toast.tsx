"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

type Toast = { id: number; kind: "error" | "info" | "success"; msg: string };
type Ctx = { push: (kind: Toast["kind"], msg: string) => void };

const ToastCtx = createContext<Ctx>({ push: () => {} });

export function useToast() { return useContext(ToastCtx); }

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((kind: Toast["kind"], msg: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, msg }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000);
  }, []);

  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto min-w-[260px] max-w-[400px] rounded-md border px-4 py-3 text-sm shadow-lg ${
              t.kind === "error"
                ? "border-red-800 bg-red-950 text-red-100"
                : t.kind === "success"
                ? "border-green-800 bg-green-950 text-green-100"
                : "border-neutral-700 bg-neutral-900 text-neutral-100"
            }`}
          >
            {t.msg}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
