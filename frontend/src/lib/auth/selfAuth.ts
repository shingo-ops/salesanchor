/**
 * 自社ログイン（ADR-1013）の画面側。login・refresh・パスワード再設定と、メモリのアクセストークン。
 *
 * - アクセストークンは画面のメモリだけに置く（ブラウザの保存領域には入れない）。
 * - 更新用トークンは httpOnly Cookie なので、ここからは読めない。
 * - refresh は同時に 1 本だけ。同じタブは 1 つの Promise を共有し、タブの間は navigator.locks で順番にする
 *   （2 本同時に送ると 2 本目が失効済みになり、組ごと失効してログアウトになるため）。
 */
import { auth } from "../firebase";
import { isSelfAuth } from "./provider";

const AUTH_BASE = "/api/v1/auth";
const REFRESH_LOCK_NAME = "sa-auth-refresh";
/** 期限のこれだけ前になったら使う前に更新する（ミリ秒） */
const EXPIRY_MARGIN_MS = 30_000;

/** 自社 API の誤り応答。status と、決まった識別子の detail（文章ではない）を持つ。 */
export class SelfAuthError extends Error {
  status: number;
  detail: string | null;

  constructor(status: number, detail: string | null) {
    super(detail ?? `HTTP ${status}`);
    this.name = "SelfAuthError";
    this.status = status;
    this.detail = detail;
  }
}

interface Session {
  accessToken: string;
  expiresAt: number;
}

interface TokenResponse {
  access_token: string;
  expires_in: number;
}

let session: Session | null = null;
let inFlightRefresh: Promise<string> | null = null;
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) listener();
}

/** セッションが変わったとき（ログイン・更新・失効）に呼ばれる。戻り値で購読をやめる。 */
export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** メモリのアクセストークン（無ければ null）。期限は見ない。 */
export function currentAccessToken(): string | null {
  return session?.accessToken ?? null;
}

export function adoptAccessToken(accessToken: string, expiresInSeconds: number): void {
  session = { accessToken, expiresAt: Date.now() + expiresInSeconds * 1000 };
  notify();
}

/** メモリのトークンを捨てる。画面はログインしていない状態になる。 */
export function expireSession(): void {
  const had = session !== null;
  session = null;
  if (had) notify();
}

/** アクセストークンの中身（表示用）。署名の確かめは backend が行うので、ここでは信用しない。 */
export function readClaims(token: string): { sub: string; email: string } | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
    const claims = JSON.parse(new TextDecoder().decode(bytes)) as { sub?: unknown; email?: unknown };
    if (typeof claims.sub !== "string" || typeof claims.email !== "string") return null;
    return { sub: claims.sub, email: claims.email };
  } catch {
    return null;
  }
}

async function postAuth<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${AUTH_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const parsed = (await res.json().catch(() => ({}))) as { detail?: unknown };
    // detail は決まった識別子のときだけ読む。配列（入力検査の 422）や文章は読まない
    throw new SelfAuthError(res.status, typeof parsed.detail === "string" ? parsed.detail : null);
  }
  return (await res.json().catch(() => ({}))) as T;
}

export async function selfLogin(email: string, password: string): Promise<void> {
  const res = await postAuth<TokenResponse>("/login", { email, password });
  adoptAccessToken(res.access_token, res.expires_in);
}

async function refreshOnce(): Promise<string> {
  const run = async (): Promise<string> => {
    const res = await postAuth<TokenResponse>("/refresh");
    adoptAccessToken(res.access_token, res.expires_in);
    return res.access_token;
  };
  const before = session;
  try {
    if (typeof navigator !== "undefined" && navigator.locks) {
      return await navigator.locks.request(REFRESH_LOCK_NAME, async () => {
        // 待っている間に新しいトークンが入っていたら、送らずにそれを使う
        if (session && session !== before && session.expiresAt - Date.now() > EXPIRY_MARGIN_MS) {
          return session.accessToken;
        }
        return run();
      });
    }
    // navigator.locks が無いブラウザ: 同じタブの 1 本化だけで動かす（2 タブ同時だとログアウトすることがある）
    return await run();
  } catch (err) {
    if (err instanceof SelfAuthError && err.status === 401) expireSession();
    throw err;
  }
}

/** 更新用 Cookie でアクセストークンを取り直す。同時に呼ばれても送るのは 1 本。 */
export function selfRefresh(): Promise<string> {
  if (!inFlightRefresh) {
    inFlightRefresh = refreshOnce().finally(() => {
      inFlightRefresh = null;
    });
  }
  return inFlightRefresh;
}

/** 有効なアクセストークンを返す。切れそうなら refresh を 1 回送る。 */
async function ensureSelfToken(): Promise<string> {
  if (session && session.expiresAt - Date.now() > EXPIRY_MARGIN_MS) return session.accessToken;
  return selfRefresh();
}

export async function selfRequestPasswordReset(email: string): Promise<void> {
  await postAuth("/password-reset/request", { email });
}

export async function selfConfirmPasswordReset(token: string, newPassword: string): Promise<void> {
  await postAuth("/password-reset/confirm", { token, new_password: newPassword });
}

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
