/**
 * 認証コンテキスト。
 * ログイン状態をアプリ全体で共有する。
 * ログインの仕組みは lib/auth/provider.ts が決める（既定は Firebase。自社ログインは "self" のときだけ）。
 */

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { auth } from "../lib/firebase";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendPasswordResetEmail,
} from "../lib/firebase-auth";
import { api } from "../lib/api";
import { isSelfAuth } from "../lib/auth/provider";
import { selfPasskeyLogin } from "../lib/auth/passkey";
import {
  currentAccessToken,
  expireSession,
  readClaims,
  selfLogin,
  selfRefresh,
  selfRequestPasswordReset,
  subscribeSession,
} from "../lib/auth/selfAuth";

/** 画面が読むログイン中の利用者の項目（Firebase の User と同じ名前）。 */
export interface AuthUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  emailVerified: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithPasskey: () => Promise<void>;
  signOut: () => Promise<void>;
  sendPasswordReset: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

/** メモリのアクセストークンの中身から利用者を作る。表示に使うだけで、署名の確かめは backend が行う。 */
function userFromAccessToken(token: string | null, previous: AuthUser | null): AuthUser | null {
  if (!token) return null;
  const claims = readClaims(token);
  if (!claims) return null;
  // sub と email が変わらない限り同じ物を返す（使う所の useEffect が refresh のたびに走り直さないように）
  if (previous && previous.uid === claims.sub && previous.email === claims.email) return previous;
  return { uid: claims.sub, email: claims.email, displayName: null, emailVerified: true };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const selfMode = isSelfAuth();

  const createDevUser = (): AuthUser => {
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
    };
  };

  const isLoginRoute = typeof window !== "undefined" && window.location.pathname === "/login";
  const [user, setUser] = useState<AuthUser | null>(() => {
    if (import.meta.env.DEV && !isLoginRoute) {
      return createDevUser();
    }
    return null;
  });
  const [loading, setLoading] = useState(() => !(import.meta.env.DEV && !isLoginRoute));

  // Firebase（開発サーバーでは e2e の偽ログイン）
  useEffect(() => {
    if (selfMode) return;
    if (import.meta.env.DEV && !isLoginRoute) {
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser as AuthUser | null);
      setLoading(false);
    });
    return unsubscribe;
  }, [isLoginRoute, selfMode]);

  // 自社ログイン: 起動時にメモリにトークンが無ければ refresh を 1 回。401 なら「ログインしていない」状態にする。
  // ログイン画面へ移すのは ProtectedRoute の中のページだけ（/login・/reset-password を開いた人はそのページに留まる）
  useEffect(() => {
    if (!selfMode) return;
    let cancelled = false;
    const sync = () => {
      setUser((previous) => userFromAccessToken(currentAccessToken(), previous));
    };
    const unsubscribe = subscribeSession(sync);
    if (currentAccessToken()) {
      sync();
      setLoading(false);
    } else {
      selfRefresh()
        .catch(() => {
          // 401・ネットワーク不通のどちらでも、ログインしていない状態にする
        })
        .finally(() => {
          if (cancelled) return;
          sync();
          setLoading(false);
        });
    }
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [selfMode]);

  const signIn = async (email: string, password: string) => {
    if (selfMode) {
      await selfLogin(email, password);
      return;
    }
    await signInWithEmailAndPassword(auth, email, password);
  };

  const signInWithPasskey = async () => {
    if (!selfMode) return;
    await selfPasskeyLogin();
  };

  const signOut = async () => {
    if (selfMode) {
      try {
        await api.post("/auth/logout", {});
      } catch {
        // 通信できなくても、この端末のセッションは捨てる
      }
      expireSession();
      return;
    }
    await firebaseSignOut(auth);
  };

  const sendPasswordReset = async (email: string) => {
    if (selfMode) {
      await selfRequestPasswordReset(email);
      return;
    }
    await sendPasswordResetEmail(auth, email);
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signInWithPasskey, signOut, sendPasswordReset }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context) return context;
  if (import.meta.env.DEV) {
    const isLoginRoute = typeof window !== "undefined" && window.location.pathname === "/login";
    const fakeUser: AuthUser | null = isLoginRoute
      ? null
      : {
          uid: "e2e-test-user-uid",
          email: "review@salesanchor.jp",
          displayName: "E2E Test User",
          emailVerified: true,
        };
    return {
      user: fakeUser,
      loading: false,
      signIn: async () => {},
      signInWithPasskey: async () => {},
      signOut: async () => {},
      sendPasswordReset: async () => {},
    };
  }
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
