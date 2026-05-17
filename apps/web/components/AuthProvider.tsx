"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { getFirebaseAuth, FIREBASE_ENABLED } from "@/lib/firebase";

type Ctx = {
  user: User | null;
  loading: boolean;
  enabled: boolean;
  getToken: () => Promise<string | null>;
};

const AuthCtx = createContext<Ctx>({
  user: null,
  loading: false,
  enabled: false,
  getToken: async () => null,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(FIREBASE_ENABLED);

  useEffect(() => {
    const auth = getFirebaseAuth();
    if (!auth) {
      setLoading(false);
      return;
    }
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
    });
    return () => unsub();
  }, []);

  const getToken = async (): Promise<string | null> => {
    const auth = getFirebaseAuth();
    if (!auth?.currentUser) return null;
    try {
      return await auth.currentUser.getIdToken();
    } catch {
      return null;
    }
  };

  return (
    <AuthCtx.Provider value={{ user, loading, enabled: FIREBASE_ENABLED, getToken }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);

/** Wrap fetch — auto-injects Authorization header when signed in. */
export async function authedFetch(
  getToken: () => Promise<string | null>,
  url: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await getToken();
  const headers = new Headers(init.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...init, headers });
}
