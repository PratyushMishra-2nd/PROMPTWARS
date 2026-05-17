import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-20">
      <div className="text-center">
        <span className="rounded-full border border-neutral-800 bg-neutral-900 px-3 py-1 text-xs text-neutral-400">
          Powered by Gemini · No legal advice
        </span>
        <h1 className="mt-6 text-5xl font-bold tracking-tight md:text-6xl">
          Know what you&apos;re signing.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-neutral-400">
          LexGuard reads contracts the way a senior lawyer would — clause by clause, from your perspective.
          Get a risk score, plain-language explanations, and a chat that cites the document.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/upload"
            className="rounded-md bg-white px-6 py-3 text-sm font-medium text-black hover:bg-neutral-200"
          >
            Analyze a contract →
          </Link>
          <a
            href="#how"
            className="rounded-md border border-neutral-700 px-6 py-3 text-sm font-medium text-neutral-300 hover:bg-neutral-900"
          >
            How it works
          </a>
        </div>
      </div>

      <section id="how" className="mt-24 grid grid-cols-1 gap-6 md:grid-cols-3">
        {[
          { t: "Extract", d: "Gemini parses every clause, classifies it into 30 types, and pinpoints page/offset." },
          { t: "Reason", d: "Hybrid scoring: LLM severity + rulebook + benchmark divergence, weighted to your perspective." },
          { t: "Defend", d: "Adversarial reviewer plays opposing counsel to find what the first pass missed." },
        ].map((c) => (
          <div key={c.t} className="rounded-lg border border-neutral-800 bg-neutral-950 p-6">
            <div className="text-sm font-semibold text-white">{c.t}</div>
            <p className="mt-2 text-sm text-neutral-400">{c.d}</p>
          </div>
        ))}
      </section>

      <section className="mt-16 grid grid-cols-2 gap-4 text-center md:grid-cols-4">
        {[
          { v: "30+", l: "Clause types" },
          { v: "7", l: "Contract categories" },
          { v: "4", l: "Risk tiers" },
          { v: "100%", l: "Citation grounded" },
        ].map((s) => (
          <div key={s.l} className="rounded-lg border border-neutral-800 bg-neutral-950 p-4">
            <div className="text-2xl font-bold">{s.v}</div>
            <div className="text-xs text-neutral-500">{s.l}</div>
          </div>
        ))}
      </section>
    </main>
  );
}
