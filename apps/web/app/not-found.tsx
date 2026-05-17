import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-24 text-center">
      <h1 className="text-3xl font-bold">404 — Not found</h1>
      <p className="mt-2 text-neutral-400">This page doesn&apos;t exist.</p>
      <Link href="/" className="mt-6 inline-block rounded-md bg-white px-5 py-2 text-sm font-medium text-black">
        Go home
      </Link>
    </main>
  );
}
