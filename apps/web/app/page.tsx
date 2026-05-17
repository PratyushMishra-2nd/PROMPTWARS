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

      <section id="how" className="mt-32">
        <div className="text-center">
          <div className="text-xs uppercase tracking-widest text-neutral-500">How it works</div>
          <h2 className="mt-2 text-3xl font-bold">Four agents. One verdict.</h2>
          <p className="mx-auto mt-3 max-w-2xl text-neutral-400">
            LexGuard runs a multi-agent Gemini pipeline that extracts, scores, explains, and stress-tests every clause from your perspective.
          </p>
        </div>

        <ol className="mt-12 space-y-4">
          {[
            { n: "01", t: "Extract", d: "Gemini 2.5 Pro reads the full document in one pass. Classifies the contract type and pulls every clause into a 30-type taxonomy with exact page + character offsets back to the source." },
            { n: "02", t: "Score", d: "Hybrid risk formula: 55% LLM severity + 25% benchmark divergence vs standard template + 20% rulebook (e.g., non-compete >12 months auto-bumps +20). Weighted by your perspective — IP-assignment hits freelancers 1.6×." },
            { n: "03", t: "Explain", d: "Flash explainer rewrites each flagged clause in plain second-person English. Includes a real-world scenario where it bites you and suggested redline language to push back with." },
            { n: "04", t: "Stress-test", d: "Adversarial reviewer agent role-plays opposing counsel — re-reads the analysis to surface what the first pass missed, and flags any internal contradictions in the contract." },
          ].map((s) => (
            <li key={s.n} className="flex gap-5 rounded-lg border border-neutral-800 bg-neutral-950 p-6">
              <div className="text-3xl font-bold text-neutral-700">{s.n}</div>
              <div>
                <h3 className="text-lg font-semibold">{s.t}</h3>
                <p className="mt-1 text-sm text-neutral-400">{s.d}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section id="stats" className="mt-24 grid grid-cols-2 gap-4 text-center md:grid-cols-4">
        {[
          { v: "30+", l: "Clause types" },
          { v: "7", l: "Contract categories" },
          { v: "4", l: "Risk tiers" },
          { v: "100%", l: "Citation grounded" },
        ].map((s) => (
          <div key={s.l} className="rounded-lg border border-neutral-800 bg-neutral-950 p-6">
            <div className="text-3xl font-bold">{s.v}</div>
            <div className="mt-1 text-xs text-neutral-500">{s.l}</div>
          </div>
        ))}
      </section>

      <section id="grounding" className="mt-24 rounded-lg border border-neutral-800 bg-neutral-950 p-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          <div>
            <div className="text-xs uppercase tracking-widest text-neutral-500">Grounded chat</div>
            <h3 className="mt-2 text-2xl font-bold">Every answer cites the contract.</h3>
            <p className="mt-3 text-sm text-neutral-400">
              Ask &ldquo;Can they fire me without cause?&rdquo; — the answer points at the exact clause. Click the citation chip and the UI jumps to that clause and highlights it. If the contract doesn&apos;t address it, the model says so instead of guessing.
            </p>
          </div>
          <div className="rounded-md border border-neutral-800 bg-black/40 p-4 font-mono text-xs">
            <div className="text-neutral-500">user</div>
            <div className="mt-1 text-neutral-200">Can they fire me without cause?</div>
            <div className="mt-3 text-neutral-500">assistant</div>
            <div className="mt-1 text-neutral-200">
              Yes. The contract is at-will <span className="rounded bg-neutral-800 px-1 py-0.5 text-blue-300">[cl3]</span>, meaning the company can terminate you at any time, with or without cause, with no notice. You also forfeit unpaid bonuses if you resign without 60 days notice.
            </div>
          </div>
        </div>
      </section>

      <section className="mt-24 mb-8 rounded-lg border border-neutral-800 bg-gradient-to-br from-neutral-950 to-neutral-900 p-10 text-center">
        <h3 className="text-2xl font-bold">Try it now.</h3>
        <p className="mt-2 text-neutral-400">Paste a contract or upload a PDF. No account, nothing stored.</p>
        <Link href="/upload" className="mt-6 inline-block rounded-md bg-white px-6 py-3 text-sm font-semibold text-black hover:bg-neutral-200">
          Analyze a contract →
        </Link>
      </section>
    </main>
  );
}
