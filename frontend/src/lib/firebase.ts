/**
 * Firebase Authentication 設定
 *
 * Google Identity Platform（Firebase Auth互換）を使用してユーザー認証を行う。
 * 環境変数はビルド時にViteが埋め込む（VITE_ プレフィックス必須）。
 *
 * フロー:
 *   1. ユーザーがログインページでメール/パスワードを入力
 *   2. Firebase がMFA（認証アプリのコード）を要求
 *   3. 認証成功 → Firebase が IDトークン（JWT）を発行
 *   4. 全APIリクエストに IDトークンを Authorization ヘッダーで付与
 *   5. バックエンド（FastAPI）がトークンを検証し、ユーザーを特定
 */

import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_GCP_PROJECT_ID,
};

const app = initializeApp(firebaseConfig);
const useFakeFirebaseAuth = import.meta.env.DEV;

type FakeUser = {
  uid: string;
  email: string;
  displayName: string;
  emailVerified: boolean;
  getIdToken: () => Promise<string>;
};

type FakeAuth = {
  currentUser: FakeUser | null;
  __setCurrentUser: (user: FakeUser | null) => void;
};

const createFakeAuth = (): FakeAuth => {
  const isLoginRoute = typeof window !== "undefined" && window.location.pathname === "/login";
  const seeded = typeof window !== "undefined"
    ? (window as unknown as {
        __salesanchorE2eAuthUser?: { uid?: string; email?: string; displayName?: string; emailVerified?: boolean };
      }).__salesanchorE2eAuthUser
    : undefined;
  let currentUser: FakeUser | null =
    !isLoginRoute
      ? {
          uid: seeded?.uid || "e2e-test-user-uid",
          email: seeded?.email || "review@salesanchor.jp",
          displayName: seeded?.displayName || "E2E Test User",
          emailVerified: seeded?.emailVerified ?? true,
          getIdToken: async () => "e2e-fake-id-token",
        }
      : null;
  return {
    get currentUser() {
      return currentUser;
    },
    __setCurrentUser(user) {
      currentUser = user;
    },
  };
};

export const auth = useFakeFirebaseAuth ? createFakeAuth() : getAuth(app);
export default app;
