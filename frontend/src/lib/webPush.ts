/**
 * ブラウザの通知の仕組み（service worker・Push API）を呼ぶ薄い部品。
 * ADR-1055 段W。文字は持たない（画面側で t() を通す）。
 */

export type PushSupport = "supported" | "ios_needs_home_screen" | "unsupported";

interface NavigatorWithStandalone extends Navigator {
  standalone?: boolean;
}

/** この機械で通知を出せるかを返す */
export function pushSupport(): PushSupport {
  if (typeof window === "undefined") return "unsupported";
  if ("serviceWorker" in navigator && "PushManager" in window && "Notification" in window) {
    return "supported";
  }
  const ua = navigator.userAgent;
  const isIos = /iPhone|iPad|iPod/.test(ua);
  const isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
  if (isIos && isSafari) {
    const standaloneMedia =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(display-mode: standalone)").matches;
    const standaloneNav = (navigator as NavigatorWithStandalone).standalone === true;
    if (!standaloneMedia && !standaloneNav) return "ios_needs_home_screen";
  }
  return "unsupported";
}

/** applicationServerKey 用に base64url を Uint8Array へ直す */
export function urlBase64ToUint8Array(base64url: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64url.length % 4)) % 4);
  const base64 = (base64url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

async function registration(): Promise<ServiceWorkerRegistration> {
  // updateViaCache "none": 本体と import に HTTP キャッシュを使わない
  await navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" });
  return navigator.serviceWorker.ready;
}

/** この機械の購読を作る（userVisibleOnly: true） */
export async function subscribeThisDevice(publicKey: string): Promise<PushSubscription> {
  const reg = await registration();
  return reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
}

/** この機械の今の購読（無ければ null） */
export async function currentSubscription(): Promise<PushSubscription | null> {
  const reg = await registration();
  return reg.pushManager.getSubscription();
}

/** この機械の購読を外す */
export async function unsubscribeThisDevice(): Promise<void> {
  const sub = await currentSubscription();
  if (sub) await sub.unsubscribe();
}
