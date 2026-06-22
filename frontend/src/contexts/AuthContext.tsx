/**
 * Firebase認証コンテキスト。
 * ログイン状態をアプリ全体で共有する。
 */

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import type { User } from "firebase/auth";
import { auth } from "../lib/firebase";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendPasswordResetEmail,
} from "../lib/firebase-auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  sendPasswordReset: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const createDevUser = () => {
    const seeded = (window as unknown as {
      __salesanchorE2eAuthUser?: { uid?: string; email?: string; displayName?: string; emailVerified?: boolean };
    }).__salesanchorE2eAuthUser;
    const uid = seeded?.uid || "e2e-test-user-uid";
    const email = seeded?.email || "review@salesanchor.jp";
    return {
      uid,
      email,
      displayName: seeded?.displayName || "E2E Test User",
      emailVerified: seeded?.emailVerified ?? true,
      getIdToken: async () => "e2e-fake-id-token",
    } as User;
  };

  const isLoginRoute = typeof window !== "undefined" && window.location.pathname === "/login";
  const [user, setUser] = useState<User | null>(() => {
    if (import.meta.env.DEV && !isLoginRoute) {
      return createDevUser();
    }
    return null;
  });
  const [loading, setLoading] = useState(() => !(import.meta.env.DEV && !isLoginRoute));

  useEffect(() => {
    if (import.meta.env.DEV && !isLoginRoute) {
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser as User | null);
      setLoading(false);
    });
    return unsubscribe;
  }, [isLoginRoute]);

  const signIn = async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email, password);
  };

  const signOut = async () => {
    await firebaseSignOut(auth);
  };

  const sendPasswordReset = async (email: string) => {
    await sendPasswordResetEmail(auth, email);
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut, sendPasswordReset }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context) return context;
  if (import.meta.env.DEV) {
    const isLoginRoute = typeof window !== "undefined" && window.location.pathname === "/login";
    const fakeUser = isLoginRoute
      ? null
      : ({
          uid: "e2e-test-user-uid",
          email: "review@salesanchor.jp",
          displayName: "E2E Test User",
          emailVerified: true,
          getIdToken: async () => "e2e-fake-id-token",
        } as User);
    return {
      user: fakeUser,
      loading: false,
      signIn: async () => {},
      signOut: async () => {},
      sendPasswordReset: async () => {},
    };
  }
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
