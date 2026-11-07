/**
 * 認証コンテキスト。
 * ログイン状態をアプリ全体で共有する。
 * ログインは自社ログイン（ADR-1013）だけ。開発サーバー・Storybook・単体試験では、起動時に登録された
 * 開発用の偽ログイン（lib/auth/devSessionSlot.ts）を使い、ログインでは自社 API を呼ばない（パスワード再設定の依頼だけは自社 API へ送る）。
 */

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "../lib/api";
import { getDevSession } from "../lib/auth/devSessionSlot";
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
import { clearRecoveryPromptMarksForCurrentUser } from "../features/auth/RecoveryCodePrompt";
import type { SelfLoginResult } from "../lib/auth/selfAuth";

/** 画面が読むログイン中の利用者の項目。 */
export interface AuthUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  emailVerified: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<SelfLoginResult>;
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
  // 開発用の偽ログイン（登録が無ければ null＝自社ログイン）
  const dev = getDevSession();

  const [user, setUser] = useState<AuthUser | null>(() => (dev ? dev.getUser() : null));
  const [loading, setLoading] = useState(() => !dev);

  // 開発用の偽ログイン: 利用者の変化を受け取る
  useEffect(() => {
    if (!dev) return;
    return dev.subscribe(setUser);
  }, [dev]);

  // 自社ログイン: 起動時にメモリにトークンが無ければ refresh を 1 回。401 なら「ログインしていない」状態にする。
  // ログイン画面へ移すのは ProtectedRoute の中のページだけ（/login・/reset-password を開いた人はそのページに留まる）
  useEffect(() => {
    if (dev) return;
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
  }, [dev]);

  const signIn = async (email: string, password: string): Promise<SelfLoginResult> => {
    if (dev) {
      await dev.signIn(email, password);
      return { kind: "ok", mustChangePassword: false };
    }
    const result = await selfLogin(email, password);
    // 新しいログインでは案内を出し直せるように、前のログインの印を消す
    if (result.kind === "ok") clearRecoveryPromptMarksForCurrentUser();
    return result;
  };

  const signInWithPasskey = async () => {
    if (dev) return;
    await selfPasskeyLogin();
  };

  const signOut = async () => {
    if (dev) {
      await dev.signOut();
      return;
    }
    try {
      await api.post("/auth/logout", {});
    } catch {
      // 通信できなくても、この端末のセッションは捨てる
    }
    clearRecoveryPromptMarksForCurrentUser();
    expireSession();
  };

  const sendPasswordReset = async (email: string) => {
    await selfRequestPasswordReset(email);
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
  // AuthProvider の外（Storybook・単体試験の部品だけの描画）は、開発用の偽ログインの利用者を返す
  const dev = getDevSession();
  if (dev) {
    return {
      user: dev.getUser(),
      loading: false,
      signIn: async (): Promise<SelfLoginResult> => ({ kind: "ok", mustChangePassword: false }),
      signInWithPasskey: async () => {},
      signOut: async () => {},
      sendPasswordReset: async () => {},
    };
  }
  throw new Error("useAuth must be used within AuthProvider");
}
