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

export type AutoRegisterResult = "created" | "exists" | "not_allowed" | "failed";
const AUTO_REGISTER_TIMEOUT_MS = 10_000;

/** ブラウザが「裏での自動作成」に対応しているか（ADR-1013 便6）。 */
export async function conditionalCreateSupported(): Promise<boolean> {
  try {
    const getCaps = (PublicKeyCredential as unknown as {
      getClientCapabilities?: () => Promise<Record<string, boolean>>;
    }).getClientCapabilities;
    if (typeof getCaps !== "function") return false;
    const caps = await getCaps.call(PublicKeyCredential);
    return caps.conditionalCreate === true;
  } catch {
    return false;
  }
}

/** パスワードでログインした直後に、自動作成と案内を出してよいか。 */
export async function getPasskeyPrompt(): Promise<{ can_auto: boolean; show_prompt: boolean }> {
  return api.get<{ can_auto: boolean; show_prompt: boolean }>("/auth/passkey/prompt");
}

async function autoRegisterOnce(): Promise<AutoRegisterResult> {
  try {
    const res = await api.post<Challenge<PublicKeyCredentialCreationOptionsJSON>>(
      "/auth/passkey/register/options",
      { auto: true },
    );
    const credential = await startRegistration({ optionsJSON: res.options, useAutoRegister: true });
    await api.post("/auth/passkey/register/verify", {
      challenge_id: res.challenge_id,
      credential,
      label: "",
    });
    return "created";
  } catch (err) {
    if (err instanceof Error && err.name === "InvalidStateError") return "exists";
    if (err instanceof Error && err.name === "NotAllowedError") return "not_allowed";
    return "failed";
  }
}

/** ログイン直後にパスキーを裏で作る。10 秒で打ち切る。 */
export async function autoRegisterPasskey(): Promise<AutoRegisterResult> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<AutoRegisterResult>((resolve) => {
    timer = setTimeout(() => resolve("failed"), AUTO_REGISTER_TIMEOUT_MS);
  });
  try {
    return await Promise.race([autoRegisterOnce(), timeout]);
  } finally {
    clearTimeout(timer);
  }
}

/** 「今はスキップ」を記録する。 */
export async function skipPasskeyPrompt(): Promise<void> {
  await api.post("/auth/passkey/prompt/skip", {});
}
