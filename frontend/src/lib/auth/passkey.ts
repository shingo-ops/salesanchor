/**
 * パスキー（顔・指紋）でのログインと登録（ADR-1013 便5）。
 * 顔や指紋のデータは端末から出ない。ここで扱うのは、端末が返す署名つきの応答だけ。
 */
import {
  WebAuthnAbortService,
  base64URLStringToBuffer,
  browserSupportsWebAuthn,
  browserSupportsWebAuthnAutofill,
  bufferToBase64URLString,
  startAuthentication,
  startRegistration,
  type AuthenticationResponseJSON,
  type PublicKeyCredentialCreationOptionsJSON,
  type PublicKeyCredentialRequestOptionsJSON,
} from "@simplewebauthn/browser";
import { api } from "../api";
import { isDevSession } from "./devSessionSlot";
import { adoptAccessToken, postAuth, type TokenResponse } from "./selfAuth";

interface Challenge<O> {
  challenge_id: string;
  options: O;
}

/** ログイン画面のボタンを出してよいか（自社ログインかつ端末が対応しているとき）。 */
export function passkeySupported(): boolean {
  return !isDevSession() && browserSupportsWebAuthn();
}

/** ログインの後半（verify → トークンをメモリに入れる）。3つのログインの道で共通。 */
async function finishPasskeyLogin(challengeId: string, credential: AuthenticationResponseJSON): Promise<void> {
  const token = await postAuth<TokenResponse>("/passkey/login/verify", {
    challenge_id: challengeId,
    credential,
  });
  adoptAccessToken(token.access_token, token.expires_in);
}

/** パスキーでログインする。成功するとメモリにアクセストークンが入る。 */
export async function selfPasskeyLogin(): Promise<void> {
  const res = await postAuth<Challenge<PublicKeyCredentialRequestOptionsJSON>>("/passkey/login/options");
  const credential = await startAuthentication({ optionsJSON: res.options });
  await finishPasskeyLogin(res.challenge_id, credential);
}

function abortError(): Error {
  return Object.assign(new Error("stale"), { name: "AbortError" });
}

/** メール欄の候補にパスキーを出してよいか（端末が自動の候補に対応しているとき）。 */
export async function passkeyAutofillSupported(): Promise<boolean> {
  try {
    return passkeySupported() && (await browserSupportsWebAuthnAutofill());
  } catch {
    return false;
  }
}

/**
 * メール欄の候補からのログインを待ち受ける。候補が選ばれて顔・指紋が通ると verify まで進む。
 * isStale() が true になった呼び出しは verify もトークンの保存もせず、AbortError で終わる。
 */
export async function startPasskeyAutofill(isStale: () => boolean): Promise<void> {
  if (isStale()) throw abortError();
  let res: Challenge<PublicKeyCredentialRequestOptionsJSON>;
  // options の失敗（回数止めの 429・止まりの 503 など）は待ち受けを黙って始めない（design.md §6）
  try {
    res = await postAuth<Challenge<PublicKeyCredentialRequestOptionsJSON>>("/passkey/login/options");
  } catch {
    throw abortError();
  }
  if (isStale()) throw abortError();
  const credential = await startAuthentication({ optionsJSON: res.options, useBrowserAutofill: true });
  if (isStale()) throw abortError();
  await finishPasskeyLogin(res.challenge_id, credential);
}

/** 待ち受け中の顔・指紋の確認を取り消す。 */
export function cancelPasskeyCeremony(): void {
  WebAuthnAbortService.cancelCeremony();
}

/** ブラウザが「選ぶ画面を挟まず確認を出す」（immediate）に対応しているか（Chrome 149 以降）。 */
export async function immediateGetSupported(): Promise<boolean> {
  try {
    const getCaps = (PublicKeyCredential as unknown as {
      getClientCapabilities?: () => Promise<Record<string, boolean>>;
    }).getClientCapabilities;
    if (typeof getCaps !== "function") return false;
    const caps = await getCaps.call(PublicKeyCredential);
    return caps.immediateGet === true;
  } catch {
    return false;
  }
}

// DOM の型にまだ無い uiMode をここだけで足す
type ImmediateCredentialRequestOptions = CredentialRequestOptions & { uiMode?: "immediate" };

/** 選ぶ画面を挟まずに顔・指紋の確認を出してログインする。ブラウザの誤りはそのまま投げる。 */
export async function immediatePasskeyLogin(): Promise<void> {
  const res = await postAuth<Challenge<PublicKeyCredentialRequestOptionsJSON>>("/passkey/login/options");
  const o = res.options;
  const request: ImmediateCredentialRequestOptions = {
    publicKey: {
      challenge: base64URLStringToBuffer(o.challenge),
      rpId: o.rpId,
      timeout: o.timeout,
      userVerification: o.userVerification,
      ...(o.extensions ? { extensions: o.extensions as AuthenticationExtensionsClientInputs } : {}),
    },
    uiMode: "immediate",
  };
  const cred = (await navigator.credentials.get(request)) as PublicKeyCredential | null;
  if (!cred) throw new Error("Authentication was not completed");
  const r = cred.response as AuthenticatorAssertionResponse;
  await finishPasskeyLogin(res.challenge_id, {
    id: cred.id,
    rawId: bufferToBase64URLString(cred.rawId),
    type: "public-key",
    response: {
      authenticatorData: bufferToBase64URLString(r.authenticatorData),
      clientDataJSON: bufferToBase64URLString(r.clientDataJSON),
      signature: bufferToBase64URLString(r.signature),
      userHandle: r.userHandle ? bufferToBase64URLString(r.userHandle) : undefined,
    },
    clientExtensionResults: cred.getClientExtensionResults(),
    authenticatorAttachment:
      cred.authenticatorAttachment === "platform" || cred.authenticatorAttachment === "cross-platform"
        ? cred.authenticatorAttachment
        : undefined,
  });
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
