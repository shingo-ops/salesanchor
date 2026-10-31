/**
 * パスキー（顔・指紋）でのログインと登録（ADR-1013 便5）。
 * 顔や指紋のデータは端末から出ない。ここで扱うのは、端末が返す署名つきの応答だけ。
 */
import {
  browserSupportsWebAuthn,
  startAuthentication,
  startRegistration,
  type PublicKeyCredentialCreationOptionsJSON,
  type PublicKeyCredentialRequestOptionsJSON,
} from "@simplewebauthn/browser";
import { api } from "../api";
import { isSelfAuth } from "./provider";
import { adoptAccessToken, postAuth, type TokenResponse } from "./selfAuth";

interface Challenge<O> {
  challenge_id: string;
  options: O;
}

/** ログイン画面のボタンを出してよいか（自社ログインかつ端末が対応しているとき）。 */
export function passkeySupported(): boolean {
  return isSelfAuth() && browserSupportsWebAuthn();
}

/** パスキーでログインする。成功するとメモリにアクセストークンが入る。 */
export async function selfPasskeyLogin(): Promise<void> {
  const res = await postAuth<Challenge<PublicKeyCredentialRequestOptionsJSON>>("/passkey/login/options");
  const credential = await startAuthentication({ optionsJSON: res.options });
  const token = await postAuth<TokenResponse>("/passkey/login/verify", {
    challenge_id: res.challenge_id,
    credential,
  });
  adoptAccessToken(token.access_token, token.expires_in);
}

/** この端末をパスキーとして登録する（ログイン中）。 */
export async function registerPasskey(label: string): Promise<void> {
  const res = await api.post<Challenge<PublicKeyCredentialCreationOptionsJSON>>(
    "/auth/passkey/register/options",
    {},
  );
  const credential = await startRegistration({ optionsJSON: res.options });
  await api.post("/auth/passkey/register/verify", {
    challenge_id: res.challenge_id,
    credential,
    label,
  });
}

/** ブラウザ側の誤り（取り消し・登録済みの端末）を見分ける。それ以外は null。 */
export function passkeyBrowserError(err: unknown): "cancelled" | "exists" | null {
  if (!(err instanceof Error)) return null;
  if (err.name === "NotAllowedError") return "cancelled";
  if (err.name === "InvalidStateError") return "exists";
  return null;
}
