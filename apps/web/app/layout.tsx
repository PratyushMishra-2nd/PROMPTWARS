import "./globals.css";
import type { Metadata } from "next";
import { ToastProvider } from "@/components/Toast";
import Link from "next/link";

export const metadata: Metadata = {
  title: "LexGuard — AI Contract Intelligence",
  description: "Know what you're signing. AI risk analysis for contracts, ToS, leases, and more.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <ToastProvider>
          <nav className="border-b border-neutral-900 bg-black/40 backdrop-blur">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
              <Link href="/" className="text-sm font-bold tracking-tight">LexGuard</Link>
              <div className="flex gap-4 text-sm text-neutral-400">
                <Link href="/upload" className="hover:text-white">Analyze</Link>
                <a href="https://github.com" className="hover:text-white" target="_blank" rel="noreferrer">GitHub</a>
              </div>
            </div>
          </nav>
          {children}
        </ToastProvider>
      </body>
    </html>
  );
}
