/**
 * ログインの仕組みの切り替え（ADR-1013）。ビルド変数を読むのはこのファイルだけ。
 *
 * 値がちょうど "self" のときだけ自社ログイン。それ以外（未設定・空・大文字違いを含む）は Firebase。
 * 開発サーバー（import.meta.env.DEV）では、どちらの値でも e2e 用の偽ログインを使うため自社 API を呼ばない。
 */

export type AuthProvider = "firebase" | "self";

export function resolveAuthProvider(value: unknown): AuthProvider {
  return value === "self" ? "self" : "firebase";
}

export function getAuthProvider(): AuthProvider {
  return resolveAuthProvider(import.meta.env.VITE_AUTH_PROVIDER);
}

/** 自社 API でログインするか。開発サーバーでは常に false（e2e の偽ログインを使う）。 */
export function isSelfAuth(): boolean {
  return getAuthProvider() === "self" && !import.meta.env.DEV;
}
