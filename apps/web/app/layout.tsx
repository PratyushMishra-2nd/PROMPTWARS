import "./globals.css";
import type { Metadata } from "next";
import { ToastProvider } from "@/components/Toast";
import { AuthProvider } from "@/components/AuthProvider";
import AuthButton from "@/components/AuthButton";
import Link from "next/link";

export const metadata: Metadata = {
  title: "LexGuard — AI Contract Intelligence",
  description: "Know what you're signing. AI risk analysis for contracts, ToS, leases, and more.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <a href="#main" className="skip-link">Skip to content</a>
        <ToastProvider>
          <AuthProvider>
            <nav aria-label="Primary" className="border-b border-neutral-900 bg-black/40 backdrop-blur">
              <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
                <Link href="/" className="text-sm font-bold tracking-tight" aria-label="LexGuard home">LexGuard</Link>
                <div className="flex items-center gap-6">
                  <ul className="flex gap-4 text-sm text-neutral-400">
                    <li><Link href="/upload" className="hover:text-white">Analyze</Link></li>
                    <li><Link href="/compare" className="hover:text-white">Compare</Link></li>
                    <li><Link href="/history" className="hover:text-white">History</Link></li>
                    <li><a href="https://github.com" className="hover:text-white" target="_blank" rel="noreferrer">GitHub</a></li>
                  </ul>
                  <AuthButton />
                </div>
              </div>
            </nav>
            <div id="main">{children}</div>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
