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
