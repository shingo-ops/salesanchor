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
