"use client";

import { GoogleAuthProvider, signInWithPopup, signOut } from "firebase/auth";
import { getFirebaseAuth } from "@/lib/firebase";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/Toast";

export default function AuthButton() {
  const { user, loading, enabled } = useAuth();
  const toast = useToast();

  if (!enabled) {
    return (
      <span
        className="rounded border border-neutral-800 px-2 py-1 text-[10px] text-neutral-600"
        title="Set NEXT_PUBLIC_FIREBASE_* env vars to enable sign-in"
      >
        auth: off
      </span>
    );
  }
  if (loading) return <span className="text-xs text-neutral-500">…</span>;

  async function signIn() {
    const auth = getFirebaseAuth();
    if (!auth) return;
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
    } catch (e: any) {
      toast.push("error", e?.message || "Sign-in failed");
    }
  }

  async function out() {
    const auth = getFirebaseAuth();
    if (!auth) return;
    await signOut(auth);
  }

  if (user) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="hidden text-neutral-400 sm:inline">{user.email || user.displayName}</span>
        <button
          onClick={out}
          className="rounded border border-neutral-700 px-2 py-1 hover:border-neutral-500"
          aria-label="Sign out"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={signIn}
      className="rounded bg-white px-3 py-1 text-xs font-medium text-black hover:bg-neutral-200"
      aria-label="Sign in with Google"
    >
      Sign in
    </button>
  );
}
