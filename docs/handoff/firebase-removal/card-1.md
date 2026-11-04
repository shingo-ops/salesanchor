# card: 便1 画面から Firebase を外す（frontend と e2e の workflow だけ）

状態: カード発行（Opus、2026-11-04）。PO の承認は 2026-11-04「1」（design.md の状態の行）。設計: [design.md](./design.md) §5-1。根拠: [recon.md](./recon.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・サーバー・GitHub の secret と Variables には触らない。PR は作らない（Opus が作る）。
基準: origin/main `63a69bfb6`。下の行番号はすべてこの時点のもの。行がずれていたら、行番号ではなく「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。
新しい画面の部品は作らない（見た目は変えない。中身の処理だけ）。デザイントークン・金型には触らない。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルを §1 で全部挙げた。消すファイルも §1 に挙げ、`find … -delete` で消す。PR は Opus が手元で shingo-cc 名義で作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に変更後のコードを全文で書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED firebase-removal-bin1 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/firebase-removal-bin1` を origin から取り直し、`docs/handoff/firebase-removal/card-1.md` が在ること。
- P2 `git diff --quiet 63a69bfb6 HEAD -- frontend .github/workflows/e2e.yml .github/workflows/karte-gate.yml .github/workflows/frontend-check.yml` が終了 0（基準から変わっていない）。
- P3 `sed -n '3274p;3304p' frontend/src/locales/ja.json` が `  "firebaseError": {` と `    "passwordTooShort": "パスワードは8文字以上で入力してください",` の 2 行。
- P4 `sed -n '3274p;3304p' frontend/src/locales/en.json` が `  "firebaseError": {` と `    "passwordTooShort": "Password must be at least 8 characters",` の 2 行。
- P5 `frontend/src/test-utils` と `frontend/src/lib/auth/devSessionSlot.ts` と `frontend/src/lib/auth/devSession.ts` が無いこと。

## 1. 触るファイル

新しく作る（3 つ）:
1. `frontend/src/lib/auth/devSessionSlot.ts`（2-1）
2. `frontend/src/lib/auth/devSession.ts`（2-2）
3. `frontend/src/test-utils/devSession.ts`（2-3）

書き換える:
4. `frontend/src/test-setup.ts`（2-4 全文）
5. `frontend/src/contexts/AuthContext.tsx`（2-5 全文）
6. `frontend/src/lib/auth/selfAuth.ts`（2-6）
7. `frontend/src/lib/api.ts`（2-7）
8. `frontend/src/lib/auth/passkey.ts`（2-8）
9. `frontend/src/features/auth/LoginApprovalWatcher.tsx`（2-9）
10. `frontend/src/features/auth/RecoveryCodePrompt.tsx`（2-9）
11. `frontend/src/pages/account-settings/SecuritySection.tsx`（2-10）
12. `frontend/src/pages/login/LoginPage.tsx`（2-11）
13. `frontend/src/lib/auth/authErrorMessage.ts`・`frontend/src/contexts/UiPrefsContext.tsx`・`frontend/src/lib/query/QueryAuthSync.tsx`（2-12 注釈だけ）
14. `frontend/src/main.tsx`（2-13 全文）
15. `frontend/.storybook/main.ts`・`frontend/.storybook/preview.tsx`（2-14 全文）
16. `frontend/vite.config.ts`・`frontend/playwright.config.ts`（2-15）
17. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（2-16 行の削除だけ）
18. `frontend/package.json`・`frontend/package-lock.json`（手順4 の `npm uninstall firebase` だけで変える。手で書かない）
19. 試験 22 ファイル（2-17）
20. `frontend/tests-e2e/` の 5 ファイル（2-18）
21. `.github/workflows/e2e.yml`・`.github/workflows/karte-gate.yml`・`.github/workflows/frontend-check.yml`（2-19）

消す（手順5、`find … -delete`）:
- `frontend/src/lib/firebase.ts`・`frontend/src/lib/firebase-auth.ts`
- `frontend/src/lib/firebaseErrorMessage.ts`・`frontend/src/lib/firebaseErrorMessage.test.ts`
- `frontend/src/lib/__storybook-mocks__/firebase-app.ts`・`frontend/src/lib/__storybook-mocks__/firebase-auth.ts`
- `frontend/src/lib/auth/provider.ts`・`frontend/src/lib/auth/provider.test.ts`

触らない: 上に挙げた以外のすべて（`backend/`・`deploy.yml`・`frontend/Dockerfile`・`docker-compose*.yml`・`frontend/.env.example`・`frontend/api-contract/`・`nginx/`・`docs/` を含む）。上のファイルの中でも、書いていない行は 1 文字も変えない。

## 2. 変更の中身

### 2-1. 新規 `frontend/src/lib/auth/devSessionSlot.ts`

```ts
/**
 * 開発用の偽ログインの差し込み口（ADR-1013）。
 * 本番では何も登録されない（null）＝自社ログイン。開発サーバー・Storybook・単体試験だけが起動時に登録する。
 * 「偽ログインか」を決めるのはこのファイルだけ。画面と部品は isDevSession() / getDevSession() で読む。
 */

export interface DevSessionUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  emailVerified: boolean;
}

export interface DevSessionAdapter {
  getUser(): DevSessionUser | null;
  subscribe(listener: (user: DevSessionUser | null) => void): () => void;
  signIn(email: string, password: string): Promise<void>;
  signOut(): Promise<void>;
  getAccessToken(): Promise<string>;
  hasSession(): boolean;
}

let current: DevSessionAdapter | null = null;

export function registerDevSession(adapter: DevSessionAdapter | null): void {
  current = adapter;
}

export function isDevSession(): boolean {
  return current !== null;
}

export function getDevSession(): DevSessionAdapter | null {
  return current;
}
```

### 2-2. 新規 `frontend/src/lib/auth/devSession.ts`

```ts
/**
 * 開発用の偽ログイン（開発サーバーと Storybook）。本番の組み立てには入らない
 * （main.tsx が import.meta.env.DEV のときだけ読み込む。CI の「Firebase removal check」で確かめる）。
 * e2e は window.__salesanchorE2eAuthUser か、保存領域の "salesanchor:e2e-auth-user" で利用者を先に入れておける
 * （tests-e2e/utils/auth.ts）。ログイン・ログアウト・トークンでは自社 API を呼ばない（パスワード再設定の依頼は自社 API へ送る）。
 */
import type { DevSessionAdapter, DevSessionUser } from "./devSessionSlot";

const STORAGE_KEY = "salesanchor:e2e-auth-user";
const FAKE_TOKEN = "e2e-fake-id-token";

type Seed = Partial<DevSessionUser>;

function readSeed(): Seed | undefined {
  return (window as unknown as { __salesanchorE2eAuthUser?: Seed }).__salesanchorE2eAuthUser;
}

/** ログイン画面の外: 先に入れた利用者があればそれ、無ければ決まった試験用の利用者。 */
function defaultUser(): DevSessionUser {
  const seeded = readSeed();
  return {
    uid: seeded?.uid || "e2e-test-user-uid",
    email: seeded?.email || "review@salesanchor.jp",
    displayName: seeded?.displayName || "E2E Test User",
    emailVerified: seeded?.emailVerified ?? true,
  };
}

/** ログイン画面: 先に入れた利用者、無ければ保存領域の利用者、どちらも無ければ未ログイン。 */
function storedUser(): DevSessionUser | null {
  try {
    const seed = readSeed();
    if (seed && seed.uid && seed.email) {
      return {
        uid: seed.uid,
        email: seed.email,
        displayName: seed.displayName || seed.email,
        emailVerified: seed.emailVerified ?? true,
      };
    }
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Seed;
    if (!parsed.uid || !parsed.email) return null;
    return {
      uid: parsed.uid,
      email: parsed.email,
      displayName: parsed.displayName || parsed.email,
      emailVerified: parsed.emailVerified ?? true,
    };
  } catch {
    return null;
  }
}

function writeUser(user: DevSessionUser | null): void {
  try {
    (window as unknown as { __salesanchorE2eAuthUser?: unknown }).__salesanchorE2eAuthUser = user ? { ...user } : undefined;
    if (!user) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  } catch {
    // 保存領域が使えなくても続ける
  }
}

export function createDevSession(): DevSessionAdapter {
  const isLoginRoute = window.location.pathname === "/login";
  let user: DevSessionUser | null = isLoginRoute ? storedUser() : defaultUser();
  const listeners = new Set<(user: DevSessionUser | null) => void>();
  const notify = () => {
    for (const listener of listeners) listener(user);
  };

  return {
    getUser: () => user,
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    async signIn(email) {
      const localPart = email.split("@")[0] || "e2e-user";
      user = { uid: `e2e-${localPart}`, email, displayName: email, emailVerified: true };
      writeUser(user);
      notify();
    },
    async signOut() {
      user = null;
      writeUser(null);
      notify();
    },
    async getAccessToken() {
      if (user) return FAKE_TOKEN;
      // 文言の初期化（i18n）はここで初めて必要になるので、読み込みを遅らせる
      const { default: i18n } = await import("../../i18n");
      throw new Error(i18n.t("common.notAuthenticated"));
    },
    hasSession: () => user !== null,
  };
}
```

### 2-3. 新規 `frontend/src/test-utils/devSession.ts`

```ts
/**
 * 単体試験用の開発ログイン。test-setup.ts が毎回の試験の前に登録する（今までの「開発中は偽ログイン」と同じ振る舞い）。
 * 自社ログインの動きを試す試験は、beforeEach で registerDevSession(null) を呼ぶ。
 */
import { vi } from "vitest";
import { registerDevSession, type DevSessionAdapter, type DevSessionUser } from "../lib/auth/devSessionSlot";

export const TEST_DEV_USER: DevSessionUser = {
  uid: "e2e-test-user-uid",
  email: "review@salesanchor.jp",
  displayName: "E2E Test User",
  emailVerified: true,
};

export function registerTestDevSession(overrides: Partial<DevSessionAdapter> = {}): DevSessionAdapter {
  const adapter: DevSessionAdapter = {
    getUser: () => (window.location.pathname === "/login" ? null : TEST_DEV_USER),
    subscribe: () => () => {},
    signIn: vi.fn(async () => undefined),
    signOut: vi.fn(async () => undefined),
    getAccessToken: async () => {
      const { default: i18n } = await import("../i18n");
      throw new Error(i18n.t("common.notAuthenticated"));
    },
    hasSession: () => false,
    ...overrides,
  };
  registerDevSession(adapter);
  return adapter;
}
```

### 2-4. `frontend/src/test-setup.ts`（全文を置き換える）

```ts
/**
 * Vitest グローバルセットアップ（unit テスト専用）
 *
 * 毎回の試験の前に、単体試験用の開発ログインを登録する（src/test-utils/devSession.ts）。
 * 自社ログインの動きを試す試験は、自分の beforeEach で registerDevSession(null) を呼ぶ。
 */

import { beforeEach } from "vitest";
import { registerTestDevSession } from "./test-utils/devSession";

beforeEach(() => {
  registerTestDevSession();
});
```

### 2-5. `frontend/src/contexts/AuthContext.tsx`（全文を置き換える）

```tsx
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
      return { kind: "ok" };
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
      signIn: async (): Promise<SelfLoginResult> => ({ kind: "ok" }),
      signInWithPasskey: async () => {},
      signOut: async () => {},
      sendPasswordReset: async () => {},
    };
  }
  throw new Error("useAuth must be used within AuthProvider");
}
```

### 2-6. `frontend/src/lib/auth/selfAuth.ts`

(a) 変更前（`:9-10`）:

```ts
import { auth } from "../firebase";
import { isSelfAuth } from "./provider";
```

変更後:

```ts
import { getDevSession } from "./devSessionSlot";
```

(b) 変更前（`:219-237`）:

```ts
/**
 * API に付けるトークンの取得口（唯一）。
 * 自社ログインのときはメモリのトークン（切れていたら refresh を 1 回）、それ以外は今の Firebase の ID トークン。
 */
export async function getAccessToken(): Promise<string> {
  if (isSelfAuth()) return ensureSelfToken();
  const user = auth.currentUser;
  if (!user) {
    // 文言の初期化（i18n）はここで初めて必要になるので、読み込みを遅らせる
    const { default: i18n } = await import("../../i18n");
    throw new Error(i18n.t("common.notAuthenticated"));
  }
  return user.getIdToken();
}

/** ログイン中か（トークンを取る前の確認用）。 */
export function hasSession(): boolean {
  return isSelfAuth() ? session !== null : auth.currentUser != null;
}
```

変更後:

```ts
/**
 * API に付けるトークンの取得口（唯一）。
 * 自社ログインのメモリのトークン（切れていたら refresh を 1 回）。開発用の偽ログインのときは、その偽のトークン。
 */
export async function getAccessToken(): Promise<string> {
  const dev = getDevSession();
  if (dev) return dev.getAccessToken();
  return ensureSelfToken();
}

/** ログイン中か（トークンを取る前の確認用）。 */
export function hasSession(): boolean {
  const dev = getDevSession();
  return dev ? dev.hasSession() : session !== null;
}
```

### 2-7. `frontend/src/lib/api.ts`

- `:3` 変更前 ` * アクセストークン（Firebase の ID トークン、または自社ログインのトークン）をAuthorizationヘッダーに自動付与する。`
  変更後 ` * アクセストークン（自社ログインのトークン）をAuthorizationヘッダーに自動付与する。`
- `:28` 変更前 `import { isSelfAuth } from "./auth/provider";`
  変更後 `import { isDevSession } from "./auth/devSessionSlot";`
- `:41` 変更前 `// getAccessToken()（Firebase の getIdToken() や自社の refresh）のタイムアウト（ミリ秒）。`
  変更後 `// getAccessToken()（自社の refresh）のタイムアウト（ミリ秒）。`
- `:73` 変更前 ` * fetch の 401 を自社ログインの規則で扱う（自社ログインのときだけ。Firebase のときは素通し）。`
  変更後 ` * fetch の 401 を自社ログインの規則で扱う（開発用の偽ログインのときは素通し）。`
- `:83` 変更前 `  if (res.status !== 401 || !isSelfAuth()) return res;`
  変更後 `  if (res.status !== 401 || isDevSession()) return res;`

### 2-8. `frontend/src/lib/auth/passkey.ts`

- `:13` 変更前 `import { isSelfAuth } from "./provider";`
  変更後 `import { isDevSession } from "./devSessionSlot";`
- `:23` 変更前 `  return isSelfAuth() && browserSupportsWebAuthn();`
  変更後 `  return !isDevSession() && browserSupportsWebAuthn();`

### 2-9. `LoginApprovalWatcher.tsx` と `RecoveryCodePrompt.tsx`

`frontend/src/features/auth/LoginApprovalWatcher.tsx`:
- `:14` 変更前 `import { isSelfAuth } from "../../lib/auth/provider";`
  変更後 `import { isDevSession } from "../../lib/auth/devSessionSlot";`
- `:34` 変更前 `  const selfMode = isSelfAuth();`
  変更後 `  const selfMode = !isDevSession();`

`frontend/src/features/auth/RecoveryCodePrompt.tsx`:
- `:12` 変更前 `import { isSelfAuth } from "../../lib/auth/provider";`
  変更後 `import { isDevSession } from "../../lib/auth/devSessionSlot";`
- `:61` 変更前 `  const selfMode = isSelfAuth();`
  変更後 `  const selfMode = !isDevSession();`

### 2-10. `frontend/src/pages/account-settings/SecuritySection.tsx`

(a) 変更前（`:3-11`）:

```tsx
import {
  EmailAuthProvider,
  reauthenticateWithCredential,
  updatePassword,
} from "../../lib/firebase-auth";
import { auth } from "../../lib/firebase";
import { firebaseErrorMessage } from "../../lib/firebaseErrorMessage";
import { authErrorMessage } from "../../lib/auth/authErrorMessage";
import { isSelfAuth } from "../../lib/auth/provider";
```

変更後:

```tsx
import { authErrorMessage } from "../../lib/auth/authErrorMessage";
import { isDevSession } from "../../lib/auth/devSessionSlot";
```

(b) 変更前（`:262-305`。`:258-261` の一致の確かめと `:306` の `  };` は残す）:

```tsx
    const selfMode = isSelfAuth();
    // 自社ログインの長さ・よく使われるパスワードの決まりは backend が判定する（422 の識別子を文言にする）
    if (!selfMode && form.next.length < 8) {
      setError(t("accountSettings.passwordTooShort"));
      return;
    }

    if (selfMode) {
      setChanging(true);
      try {
        const res = await api.post<{ access_token?: string | null; expires_in?: number | null }>(
          "/auth/password/change",
          { current_password: form.current, new_password: form.next },
        );
        // 他の端末の更新用トークンは失効するので、今の端末は応答の新しいトークンに入れ替える
        if (res.access_token && res.expires_in) adoptAccessToken(res.access_token, res.expires_in);
        setSuccess(true);
        setForm({ current: "", next: "", confirm: "" });
      } catch (err) {
        setError(authErrorMessage(err, t, "passwordChange"));
      } finally {
        setChanging(false);
      }
      return;
    }

    const user = auth.currentUser;
    if (!user || !user.email) {
      setError(t("firebaseError.default"));
      return;
    }

    setChanging(true);
    try {
      const cred = EmailAuthProvider.credential(user.email, form.current);
      await reauthenticateWithCredential(user as never, cred as never);
      await updatePassword(user as never, form.next);
      setSuccess(true);
      setForm({ current: "", next: "", confirm: "" });
    } catch (err) {
      setError(firebaseErrorMessage(err, t));
    } finally {
      setChanging(false);
    }
```

変更後:

```tsx
    // 長さ・よく使われるパスワードの決まりは backend が判定する（422 の識別子を文言にする）
    setChanging(true);
    try {
      const res = await api.post<{ access_token?: string | null; expires_in?: number | null }>(
        "/auth/password/change",
        { current_password: form.current, new_password: form.next },
      );
      // 他の端末の更新用トークンは失効するので、今の端末は応答の新しいトークンに入れ替える
      if (res.access_token && res.expires_in) adoptAccessToken(res.access_token, res.expires_in);
      setSuccess(true);
      setForm({ current: "", next: "", confirm: "" });
    } catch (err) {
      setError(authErrorMessage(err, t, "passwordChange"));
    } finally {
      setChanging(false);
    }
```

(c) 変更前（`:366-369`）:

```tsx
    {isSelfAuth() && <PushNotifySection />}
    {isSelfAuth() && <DevicesSection />}
    {isSelfAuth() && <RecoveryCodesSection />}
    {isSelfAuth() && <PasskeySection />}
```

変更後:

```tsx
    {!isDevSession() && <PushNotifySection />}
    {!isDevSession() && <DevicesSection />}
    {!isDevSession() && <RecoveryCodesSection />}
    {!isDevSession() && <PasskeySection />}
```

### 2-11. `frontend/src/pages/login/LoginPage.tsx`

(a) 次の 3 行を消す（`:5`・`:7`・`:8`）。`:6` の `import { authErrorMessage } from "../../lib/auth/authErrorMessage";` は残す。

```tsx
import { firebaseErrorMessage } from "../../lib/firebaseErrorMessage";
import type { AuthErrorContext } from "../../lib/auth/authErrorMessage";
import { isSelfAuth } from "../../lib/auth/provider";
```

(b) 次の 5 行を消す（`:42-46`。注釈・関数・その後ろの空行 1 つ）。

```tsx
// 自社ログインのときは自社 API の応答から、Firebase のときは Firebase のエラーコードから文言を作る
function loginErrorMessage(err: unknown, t: (key: string) => string, context: AuthErrorContext): string {
  return isSelfAuth() ? authErrorMessage(err, t, context) : firebaseErrorMessage(err, t);
}

```

(c) 変更前（`:197-198`）:

```tsx
      // KGI-4: Firebase の生エラー文字列を i18n キー経由に変換
      setError(loginErrorMessage(err, t, "login"));
```

変更後:

```tsx
      // KGI-4: 自社 API の誤りを i18n キー経由の文言に変換
      setError(authErrorMessage(err, t, "login"));
```

(d) `:237` 変更前 `      setError(loginErrorMessage(err, t, "resetRequest"));`
変更後 `      setError(authErrorMessage(err, t, "resetRequest"));`

### 2-12. 注釈だけ直す 3 ファイル

- `frontend/src/lib/auth/authErrorMessage.ts:4` の ` * Firebase 用の firebaseErrorMessage.ts は便6 まで残す。` の 1 行を消す。
- `frontend/src/contexts/UiPrefsContext.tsx:46`
  変更前 `  // staff レコードが存在しないユーザ＝Firebase Auth 経由 admin の可能性が高いので`
  変更後 `  // staff レコードが存在しないユーザ＝staff に紐づかない admin の可能性が高いので`
- `frontend/src/lib/query/QueryAuthSync.tsx:3`
  変更前 ` * user の変化は、Firebase の onAuthStateChanged・自社ログインの subscribeSession・`
  変更後 ` * user の変化は、開発用の偽ログインの subscribe・自社ログインの subscribeSession・`

### 2-13. `frontend/src/main.tsx`（全文を置き換える）

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import './i18n' // i18next を App より先に初期化する（ADR-027）
import './index.css'
import './loading-animations.css'
import App from './App.tsx'
import { registerDevSession } from './lib/auth/devSessionSlot'

async function bootstrap() {
  // 開発サーバーだけ、開発用の偽ログインを登録する（本番の組み立てでは、この枝と devSession.ts は入らない）
  if (import.meta.env.DEV) {
    const { createDevSession } = await import('./lib/auth/devSession')
    registerDevSession(createDevSession())
  }
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
}

void bootstrap()
```

### 2-14. Storybook

`frontend/.storybook/main.ts`（全文を置き換える）:

```ts
import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  "stories": [
    "../src/**/*.mdx",
    "../src/**/*.stories.@(js|jsx|mjs|ts|tsx)"
  ],
  "addons": [
    "@storybook/addon-vitest",
    "@storybook/addon-a11y",
    "@storybook/addon-docs",
    "@storybook/addon-mcp"
  ],
  "framework": "@storybook/react-vite",
};
export default config;
```

`frontend/.storybook/preview.tsx`（全文を置き換える）:

```tsx
import type { Preview } from '@storybook/react-vite'
import '../src/i18n'
import '../src/index.css'
import { createDevSession } from '../src/lib/auth/devSession'
import { registerDevSession } from '../src/lib/auth/devSessionSlot'

// Storybook は常に開発用の偽ログインで描く（自社 API を呼ばない）
registerDevSession(createDevSession())

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
       color: /(background|color)$/i,
       date: /Date$/i,
      },
    },
  },
};

export default preview;
```

### 2-15. `vite.config.ts` と `playwright.config.ts`

- `frontend/vite.config.ts:66`
  変更前 `          // Firebase 初期化バイパス（環境変数なしでも動くように）`
  変更後 `          // 毎回の試験の前に開発用の偽ログインを登録する（src/test-setup.ts）`
- `frontend/playwright.config.ts:139-140` 変更前:

```ts
  // Vite dev server を自動起動する。E2E 用の env で Firebase config を空にし、
  // tests-e2e/utils/auth.ts の addInitScript と組み合わせて認証を bypass する。
```

変更後:

```ts
  // Vite dev server を自動起動する。開発サーバーでは開発用の偽ログインが登録され、
  // tests-e2e/utils/auth.ts の addInitScript と組み合わせて認証を bypass する。
```

- `frontend/playwright.config.ts:149-152` の次の 4 行を消す（`:153` の `// ファネルダッシュボード` からは残す）:

```ts
          // Firebase 実機 IDP に飛ばないようダミー値を設定（mock により無視される）
          VITE_FIREBASE_API_KEY: "AIzaSyE2E-dummy-api-key",
          VITE_FIREBASE_AUTH_DOMAIN: "e2e-fixture.firebaseapp.com",
          VITE_GCP_PROJECT_ID: "e2e-fixture",
```

### 2-16. 辞書（行の削除だけ。JSON を読み直して書き出さない＝他の行の形が変わるため）

`ja.json`・`en.json` とも、`:3274-3285`（`"firebaseError"` の塊 12 行）と `:3304`（`accountSettings.passwordTooShort` の 1 行）を消す。
`authError.passwordTooShort`（`:728` 付近）は消さない。手順6 のコマンドで消し、手順6 の確かめで 13 行減・JSON として正しいことを見る。

### 2-17. 試験 22 ファイル

(1) 次の 9 ファイルは、`vi.mock("../auth/provider", () => ({ isSelfAuth: () => false }));` の 1 行を消すだけ。
`frontend/src/lib/query/` の `apiQuery.test.tsx:19`・`batch3aPages.test.tsx:30`・`batch3bPages.test.tsx:30`・`batch3cPages.test.tsx:29`・
`batch3dPages.test.tsx:30`・`batch3ePages.test.tsx:27`・`batch3fPages.test.tsx:25`・`dashboardPage.test.tsx:26`・`stage2Pages.test.tsx:25`。

(2) `frontend/src/pages/reset-password/ResetPasswordPage.test.tsx:8` の `vi.mock("../../lib/firebase", () => ({ auth: { currentUser: null } }));` の 1 行を消す。

(3) `frontend/src/components/LeadFormButtonMigration.test.tsx`
- `:14` の `vi.mock('../lib/firebase', () => ({ auth: { currentUser: { getIdToken: async () => 'synthetic-token' } } }));` を消す。
- import の並びの最後（`:10` `import { queryClient } from '../lib/query/apiQuery';` の次）に足す:
  `import { registerTestDevSession } from '../test-utils/devSession';`
- `:66` の `beforeEach(async () => {` の次の行に足す:
  `  registerTestDevSession({ getAccessToken: async () => 'synthetic-token', hasSession: () => true });`

(4) `frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx`
- `:12` の `vi.mock('../lib/firebase', () => ({ auth: { currentUser: { getIdToken: vi.fn().mockResolvedValue('token') } } }));` を消す。
- `:8` `import { queryClient } from '../lib/query/apiQuery';` の次に足す: `import { registerTestDevSession } from '../test-utils/devSession';`
- `:19`（`  vi.resetAllMocks(); instance = createInstance(); …` の行）の次の行に足す:
  `  registerTestDevSession({ getAccessToken: async () => 'token', hasSession: () => true });`

(5) `frontend/src/components/SharedButtonMigration.test.tsx`
- `:13` の `vi.mock('../lib/firebase', () => ({ auth: { currentUser: { getIdToken: mock.token } } }));` を消す。
- `:9` `import type { CustomerScoreData } from './PriorityScoreBadge';` の次に足す: `import { registerTestDevSession } from '../test-utils/devSession';`
- `:38` の `  mock.token.mockResolvedValue('fixture-token');` の次の行に足す:
  `  registerTestDevSession({ getAccessToken: () => mock.token(), hasSession: () => true });`

(6) `frontend/src/lib/api.httpError.test.ts`
- `:1` 変更前 `import { afterEach, describe, expect, it, vi } from "vitest";`
  変更後 `import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";`
- `:3` `import { api, ApiError } from "./api";` の次に足す: `import { registerTestDevSession } from "../test-utils/devSession";`
- `:5` の `vi.mock("./firebase", () => ({ auth: { currentUser: { getIdToken: async () => "t" } } }));` を、次の 3 行に置き換える:

```ts
beforeEach(() => {
  registerTestDevSession({ getAccessToken: async () => "t", hasSession: () => true });
});
```

(7) `frontend/src/lib/realtime/RealtimeProvider.test.tsx`
- `:5-7`（`vi.mock("../firebase", () => ({` から `}));` までの 3 行）を消す。
- `:9` `import { RealtimeProvider } from "./RealtimeProvider";` の次に足す: `import { registerTestDevSession } from "../../test-utils/devSession";`
- `:13` の `  beforeEach(() => {` の次の行に足す:
  `    registerTestDevSession({ getAccessToken: async () => "tok", hasSession: () => true });`

(8) 自社ログインの試験 3 つ（偽ログインを外して自社ログインで試す）
- `frontend/src/features/auth/RecoveryCodePrompt.test.tsx`: `:9-10`（provider と firebase の vi.mock の 2 行）を消す。
  `:13` の次に `import { registerDevSession } from "../../lib/auth/devSessionSlot";` を足す。`:32` の `  localStorage.clear();` の次に `  registerDevSession(null);` を足す。
- `frontend/src/lib/auth/apiReauth.test.ts`: `:9-10`（firebase と provider の vi.mock の 2 行）を消す。
  `:13` の次に `import { registerDevSession } from "./devSessionSlot";` を足す。`:23` の `beforeEach(() => {` の次に `  registerDevSession(null);` を足す。
- `frontend/src/lib/auth/selfAuth.test.ts`: `:3-4`（firebase と provider の vi.mock の 2 行）を消す。
  `:17` の `} from "./selfAuth";` の次に `import { registerDevSession } from "./devSessionSlot";` を足す。`:29` の `beforeEach(() => {` の次に `  registerDevSession(null);` を足す。

(9) `frontend/src/features/auth/LoginApprovalWatcher.test.tsx`
- `:9` `const provider = vi.hoisted(() => ({ self: true }));` と `:11` `vi.mock("../../lib/auth/provider", () => ({ isSelfAuth: () => provider.self }));` を消す。
- `:13` `import LoginApprovalWatcher from "./LoginApprovalWatcher";` の前に 2 行足す:

```tsx
import { registerDevSession } from "../../lib/auth/devSessionSlot";
import { registerTestDevSession } from "../../test-utils/devSession";
```

- `:38` 変更前 `  provider.self = true;` 変更後 `  registerDevSession(null);`
- `:54-58` 変更前:

```tsx
  it("does nothing outside self login", () => {
    provider.self = false;
    renderWatcher();
    expect(api.get).not.toHaveBeenCalled();
  });
```

変更後:

```tsx
  it("does nothing in dev session", () => {
    registerTestDevSession();
    renderWatcher();
    expect(api.get).not.toHaveBeenCalled();
  });
```

(10) `frontend/src/lib/auth/passkey.test.ts`
- `:4` の `  self: true,` を消す。
- `:12-13`（`vi.mock("../firebase", …` と `vi.mock("./provider", …` の 2 行）を消す。
- `:29` `import { currentAccessToken, expireSession } from "./selfAuth";` の次に 2 行足す:

```ts
import { registerDevSession } from "./devSessionSlot";
import { registerTestDevSession } from "../../test-utils/devSession";
```

- `:35` 変更前 `  mock.self = true;` 変更後 `  registerDevSession(null);`
- `:56` 変更前 `    mock.self = false;` 変更後 `    registerTestDevSession();`

(11) `frontend/src/pages/account-settings/SecuritySection.test.tsx`（全文を置き換える）

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const mock = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: mock.get, post: mock.post, delete: mock.delete } };
});

import { ApiError } from "../../lib/api";
import { registerDevSession } from "../../lib/auth/devSessionSlot";
import { currentAccessToken, expireSession } from "../../lib/auth/selfAuth";
import { registerTestDevSession } from "../../test-utils/devSession";
import SecuritySection from "./SecuritySection";

let instance = createInstance();
let view: ReturnType<typeof render>;
const tr =(key: string) => String(instance.t(key));

function submit(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText(tr("accountSettings.currentPassword")), { target: { value: current } });
  fireEvent.change(screen.getByLabelText(tr("accountSettings.newPassword")), { target: { value: next } });
  fireEvent.change(screen.getByLabelText(tr("accountSettings.confirmPassword")), { target: { value: confirm } });
  fireEvent.click(screen.getByRole("button", { name: tr("accountSettings.changePassword") }));
}

beforeEach(async () => {
  mock.post.mockReset();
  mock.get.mockReset().mockResolvedValue({ items: [] });
  mock.delete.mockReset();
  expireSession();
  registerDevSession(null);
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  view = render(<I18nextProvider i18n={instance}><SecuritySection /></I18nextProvider>);
});
afterEach(() => {
  cleanup();
  expireSession();
});

describe("SecuritySection (self login)", () => {
  it("calls password/change and adopts the new token from the response", async () => {
    mock.post.mockResolvedValue({ status: "password_updated", access_token: "new.token.value", expires_in: 900 });

    submit("old-password", "a-long-enough-password-1", "a-long-enough-password-1");

    await waitFor(() => expect(screen.getByText(tr("accountSettings.passwordChanged"))).toBeTruthy());
    expect(mock.post).toHaveBeenCalledWith("/auth/password/change", {
      current_password: "old-password",
      new_password: "a-long-enough-password-1",
    });
    expect(currentAccessToken()).toBe("new.token.value");
  });

  it("400 is the wrong-current-password message; 422 identifiers map to rule messages", async () => {
    mock.post.mockRejectedValueOnce(new ApiError("invalid_credentials", 400, "invalid_credentials"));
    submit("wrong", "a-long-enough-password-1", "a-long-enough-password-1");
    expect(await screen.findByText(tr("authError.currentPasswordWrong"))).toBeTruthy();

    mock.post.mockRejectedValueOnce(new ApiError("password_too_short", 422, "password_too_short"));
    submit("old-password", "short", "short");
    expect(await screen.findByText(tr("authError.passwordTooShort"))).toBeTruthy();
  });

  it("does not submit when the confirmation differs", () => {
    submit("old-password", "a-long-enough-password-1", "different-password-xx");

    expect(screen.getByText(tr("accountSettings.passwordMismatch"))).toBeTruthy();
    expect(mock.post).not.toHaveBeenCalled();
  });
});

describe("SecuritySection passkey section", () => {
  it("is a sibling frame after the security section, not nested, for self login", async () => {
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith("/auth/passkeys"));
    const sections = view.container.querySelectorAll(".account-settings-section");
    expect(sections).toHaveLength(4);
    expect(sections[0].contains(sections[3])).toBe(false);
    expect(sections[3].textContent).toContain(tr("accountSettings.passkeyTitle"));
  });

  it("is not shown in dev session", () => {
    cleanup();
    registerTestDevSession();
    const rendered = render(<I18nextProvider i18n={instance}><SecuritySection /></I18nextProvider>);

    expect(rendered.container.querySelectorAll(".account-settings-section")).toHaveLength(1);
  });
});
```

(12) `frontend/src/pages/login/LoginPage.test.tsx`
- `:9` の `  self: false,` を消す。`:17-18` の `  signInWithEmailAndPassword: vi.fn(),` と `  sendPasswordResetEmail: vi.fn(),` を消す。
- `:21-31`（`vi.mock("../../lib/firebase", …` から `vi.mock("../../lib/auth/provider", …` までの 11 行）を消す。`:32` の `vi.mock("../../lib/auth/passkey", …` からは残す。
- `:44` `import { SelfAuthError, expireSession } from "../../lib/auth/selfAuth";` の次に 2 行足す:

```tsx
import { registerDevSession } from "../../lib/auth/devSessionSlot";
import { registerTestDevSession } from "../../test-utils/devSession";
```

- `:89` の `  mock.self = false;` を消す。`:97-98`（`mock.signInWithEmailAndPassword…` と `mock.sendPasswordResetEmail…` の 2 行）を消す。
- `:111-142`（`describe("LoginPage (Firebase default)", () => {` から、その塊の `});` まで）を次に置き換える:

```tsx
describe("LoginPage (dev session)", () => {
  it("sign-in goes to the dev session and not /api/v1/auth/login", async () => {
    const dev = registerTestDevSession();
    renderLogin();

    await fillAndSubmit();

    await waitFor(() => expect(dev.signIn).toHaveBeenCalledWith("a@example.com", "secret-password-1"));
    expect(fetchMock.mock.calls.some(([u]) => u === "/api/v1/auth/login")).toBe(false);
  });

  it("forgot-password and back-to-login are TextLink components", () => {
    renderLogin();

    const forgot = screen.getByRole("button", { name: tr("login.forgotPassword") });
    expect(forgot.className).toContain("comp-text-link");

    fireEvent.click(forgot);
    const back = screen.getByRole("button", { name: tr("login.backToLogin") });
    expect(back.className).toContain("comp-text-link");
  });

  it("reset email goes to the self reset request endpoint", async () => {
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/password-reset/request"
          ? new Response(JSON.stringify({ status: "accepted" }), { status: 200 })
          : new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 }),
      ),
    );
    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: tr("login.forgotPassword") }));
    fireEvent.change(screen.getByLabelText(tr("login.email")), { target: { value: "a@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: tr("login.sendResetEmail") }));

    expect(await screen.findByText(tr("login.resetEmailSent"))).toBeTruthy();
    expect(fetchMock.mock.calls.some(([u]) => u === "/api/v1/auth/password-reset/request")).toBe(true);
  });
});
```

- `:146`・`:223`・`:280` の `    mock.self = true;`（3 か所）を、それぞれ `    registerDevSession(null);` に変える。
- `:175` 変更前 `  it("sign-in calls /api/v1/auth/login and not the Firebase function", async () => {`
  変更後 `  it("sign-in calls /api/v1/auth/login", async () => {`
- `:189` の `    expect(mock.signInWithEmailAndPassword).not.toHaveBeenCalled();` を消す。
- `:217` の `    expect(mock.sendPasswordResetEmail).not.toHaveBeenCalled();` を消す。

### 2-18. `frontend/tests-e2e/` の 5 ファイル

(1) `frontend/tests-e2e/utils/auth.ts`
- `:1-7` 変更前:

```ts
/**
 * Firebase Auth bypass helper for Playwright E2E.
 *
 * Playwright では dev server 側で `firebase/auth` を E2E mock に差し替える。
 * その mock は localStorage の永続化キーを読み込むため、ページ読み込み前に
 * dummy user を埋めておけば LoginPage を経由せずに保護ページを描画できる。
 */
```

変更後:

```ts
/**
 * 開発用の偽ログインに利用者を先に入れる Playwright E2E の補助。
 *
 * 開発サーバーでは main.tsx が開発用の偽ログイン（src/lib/auth/devSession.ts）を登録する。
 * その偽ログインは window.__salesanchorE2eAuthUser と localStorage のキーを読むため、ページ読み込み前に
 * dummy user を埋めておけば LoginPage を経由せずに保護ページを描画できる。
 */
```

- `:18`（` に Firebase Auth bypass を注入する。` で終わる行。page の前後に記号が付いている）を、次の 1 行に置き換える:
  ` * Playwright の page に、開発用の偽ログインの利用者を注入する。`
- `:31` 変更前 `          "salesanchor:e2e-firebase-auth-user",`
  変更後 `          "salesanchor:e2e-auth-user",`

(2) `frontend/tests-e2e/login.spec.ts:50-57` 変更前:

```ts
    // Firebase sendOobCode エンドポイントをモック
    await page.route("**/identitytoolkit.googleapis.com/**sendOobCode**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ email: "test@example.com" }),
      });
    });
```

変更後:

```ts
    // 自社ログインのパスワード再設定の受付をモック
    await page.route("**/api/v1/auth/password-reset/request", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "accepted" }),
      });
    });
```

(3) `frontend/tests-e2e/scene1-dashboard.spec.ts:370`
変更前 `    // 0:02–0:10 のフレーム: 認証前のログイン画面（Firebase auth bypass 不要）`
変更後 `    // 0:02–0:10 のフレーム: 認証前のログイン画面（偽ログインの利用者の注入は不要）`

(4) `frontend/tests-e2e/visual-language/viewer-focus-trap.spec.ts:83`
変更前 `  // viewer はアプリ本体の Firebase Auth を使わず localStorage のトークンだけで判定する。`
変更後 `  // viewer はアプリ本体のログインを使わず localStorage のトークンだけで判定する。`

(5) `frontend/tests-e2e/visual-language/viewer-helpers.ts:8`
変更前 ` * 認証: 閲覧ページはアプリ本体の Firebase Auth（installAuthBypass）を使わない`
変更後 ` * 認証: 閲覧ページはアプリ本体のログイン（installAuthBypass）を使わない`

### 2-19. workflow 3 つ

(1) `.github/workflows/e2e.yml`
- `:202-204` の次の 3 行を消す（`:201` の `          CI: 'true'` と `:205` の `run:` は残す）:

```yaml
          VITE_FIREBASE_API_KEY: AIzaSyE2E-dummy-api-key
          VITE_FIREBASE_AUTH_DOMAIN: e2e-fixture.firebaseapp.com
          VITE_GCP_PROJECT_ID: e2e-fixture
```

- `:308-311` の次の 4 行を消す（`:307` の `          CI: 'true'` と `:312` の `run: npm run test:e2e` は残す）:

```yaml
          # Vite dev server に渡す Firebase 用ダミー値（mock 経由で bypass）
          VITE_FIREBASE_API_KEY: AIzaSyE2E-dummy-api-key
          VITE_FIREBASE_AUTH_DOMAIN: e2e-fixture.firebaseapp.com
          VITE_GCP_PROJECT_ID: e2e-fixture
```

(2) `.github/workflows/karte-gate.yml`: `:73-75`・`:83-85`・`:108-110` の 3 か所で、上と同じ 3 行（`VITE_FIREBASE_API_KEY`・`VITE_FIREBASE_AUTH_DOMAIN`・`VITE_GCP_PROJECT_ID`）を消す。各 `env:` の `CI: 'true'` は残す。

(3) `.github/workflows/frontend-check.yml`: `:37`（段「Viewer bundle check」の `        working-directory: frontend`）の次、`:38` の空行の後、`:39` の段「Verify check:all uses concurrently」の前に、次の段と空行 1 つを足す:

```yaml
      - name: Firebase removal check (本体の JS に Firebase と開発用の偽ログインが入らない)
        run: |
          files=$(find dist -name '*.js')
          fb=$( (grep -ohiE 'firebase|identitytoolkit|securetoken|googleapis|gstatic' $files || true) | wc -l | tr -d ' ')
          dev=$( (grep -ohE '__salesanchorE2eAuthUser|e2e-auth-user|e2e-firebase-auth-user|e2e-fake' $files || true) | wc -l | tr -d ' ')
          echo "K1 firebase=$fb K6 dev=$dev"
          test "$fb" -eq 0
          test "$dev" -eq 0
        working-directory: frontend
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/firebase-removal-bin1

手順2 0. の点検 P1〜P5 を行い、結果をそのまま報告に書く
    cd ~/sa && git diff --quiet 63a69bfb6 HEAD -- frontend .github/workflows/e2e.yml .github/workflows/karte-gate.yml .github/workflows/frontend-check.yml; echo "P2 exit=$?"
    cd ~/sa/frontend && sed -n '3274p;3304p' src/locales/ja.json && sed -n '3274p;3304p' src/locales/en.json
    cd ~/sa/frontend && ls src/test-utils src/lib/auth/devSessionSlot.ts src/lib/auth/devSession.ts 2>&1 | tail -5

手順3 依存を入れる
    cd ~/sa/frontend && npm ci 2>&1 | tail -5

手順4 firebase の部品を外す（package.json と package-lock.json はこれだけで変える）
    cd ~/sa/frontend && npm uninstall firebase 2>&1 | tail -5

手順5 8 つのファイルを消す
    cd ~/sa/frontend && find src/lib/firebase.ts src/lib/firebase-auth.ts src/lib/firebaseErrorMessage.ts src/lib/firebaseErrorMessage.test.ts -type f -delete
    cd ~/sa/frontend && find src/lib/__storybook-mocks__ src/lib/auth/provider.ts src/lib/auth/provider.test.ts -type f -delete
    cd ~/sa/frontend && find src/lib/__storybook-mocks__ -type d -empty -delete

手順6 辞書の 13 行を消し、13 行減ったこと・JSON として正しいことを確かめる
    cd ~/sa/frontend && sed -i '3274,3285d;3304d' src/locales/ja.json
    cd ~/sa/frontend && sed -i '3274,3285d;3304d' src/locales/en.json
    cd ~/sa && git diff --numstat -- frontend/src/locales
    cd ~/sa/frontend && node -e 'for (const f of process.argv.slice(1)) JSON.parse(require("fs").readFileSync(f, "utf8")); console.log("json ok")' src/locales/ja.json src/locales/en.json

手順6 の注意: 1 ファイルずつ 1 回だけ実行する（同じファイルに 2 回かけると 13 行より多く消える）。`git diff --numstat` が 2 ファイルとも `0	13` であることを確かめる。

手順7 2. の変更を入れる（2-1〜2-19）。

手順8 型の元を作り、型検査と組み立てをする（`npm run build` は tsc の後に vite build）
    cd ~/sa/frontend && npm run generate:api-types 2>&1 | tail -5
    cd ~/sa/frontend && npm run build 2>&1 | tail -30

手順9 K1・K6 を数える（frontend-check.yml に足した段と同じ数え方。両方 0 が合格）
    cd ~/sa/frontend && files=$(find dist -name '*.js'); (grep -ohiE 'firebase|identitytoolkit|securetoken|googleapis|gstatic' $files || true) | sort | uniq -c
    cd ~/sa/frontend && files=$(find dist -name '*.js'); (grep -ohE '__salesanchorE2eAuthUser|e2e-auth-user|e2e-firebase-auth-user|e2e-fake' $files || true) | sort | uniq -c

手順10 単体試験
    cd ~/sa/frontend && npm run test:unit 2>&1 | tail -40

手順11 残りの Firebase の語を数える（2 つとも 0 が合格）
    cd ~/sa && git grep -n -i firebase -- frontend ':!frontend/package-lock.json' ':!frontend/src/locales' ':!frontend/.env.example' ':!frontend/api-contract' ':!frontend/Dockerfile' | wc -l
    cd ~/sa/frontend && grep -c -i firebase src/locales/ja.json src/locales/en.json

手順12 lint と決まりの確かめ
    cd ~/sa/frontend && npm run check:all 2>&1 | tail -30

手順13 差分のファイルを確かめる（§1 に無いファイルが出たら BLOCKED:）
    cd ~/sa && git status --short | tail -80
    cd ~/sa && git diff --stat | tail -60

手順14 commit する（message は 1 行目 `refactor(auth): remove Firebase from the frontend (firebase-removal bin1)`）
    cd ~/sa && git add -A frontend .github/workflows/e2e.yml .github/workflows/karte-gate.yml .github/workflows/frontend-check.yml && git commit -m "refactor(auth): remove Firebase from the frontend (firebase-removal bin1)"

手順15 commit が在ることを確かめる
    cd ~/sa && git log --oneline -2

手順16 push する
    cd ~/sa && git push origin release/firebase-removal-bin1

## 4. 想定される分かれ道

- 手順3・手順4 で npm が通信できない: 出力をそのまま書いて BLOCKED: で止まる（package-lock.json を手で書かない）。
- 手順6 で numstat が `0	13` でない、または JSON が壊れた: `git checkout -- frontend/src/locales` で戻し、出力を書いて BLOCKED: で止まる。
- 手順8 で `npm run generate:api-types` が失敗: 出力を書いて BLOCKED: で止まる（生成物を手で書かない）。
- 手順8 で型の誤り: §2 の書き写し違いなら直してよい（§2 のとおりに合わせる）。§2 のとおりなのに誤りなら、誤り全文を書いて BLOCKED: で止まる。
- 手順9 で K1 が 0 でない: どの語がどのファイルに出たか（`grep -oliE` でファイル名）を書いて BLOCKED: で止まる。直さない（Opus が決める）。
- 手順9 で K6 が 0 でない（開発用の偽ログインが本番の組み立てに残った）: 出たファイル名を書いて BLOCKED: で止まる。直さない（Opus が決める）。
- 手順10 で、今回書き換えた試験（§2-17 の 22 ファイル）が赤: §2 の書き写し違いでなければ直さず、試験名と出力全文を書いて BLOCKED: で止まる（push しない）。
- 手順10 で、今回書き換えていない試験が赤: `git stash` で変更を外して同じ試験を走らせ、外しても赤なら「元から赤」と書いて進む。外すと緑なら BLOCKED: で止まる。
- 手順11 で 0 でない: 出た行をそのまま書いて BLOCKED: で止まる。
- 手順12 で赤: 今回の変更が原因なら §2 との書き写し違いだけ直してよい。それ以外は出力を書いて BLOCKED: で止まる。
- push が拒まれた: 出力をそのまま書いて BLOCKED: で止まる。force は使わない。

## 5. 報告の形

1 行目に受領確認。続けて P1〜P5 の結果、手順6 の numstat と json ok、手順8 の出力の最後の 30 行、手順9 の 2 つの出力（空なら「0 件」）、
手順10 の最後の 40 行、手順11 の 2 つの数、手順12 の最後の 30 行、手順13 と手順15 の出力、push 後の `git rev-parse HEAD`。
最後の行は `DONE` か `BLOCKED: 理由`。秘密の値は書かない。

停止するとき（BLOCKED:）も、ここまでの出力を同じ形で報告に書いてから止まる。報告はこの実行の最後の返事に書く（別の場所には書かない）。

END OF CARD
