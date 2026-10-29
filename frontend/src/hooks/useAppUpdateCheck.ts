import { useEffect, useState } from "react";

/**
 * 新しい版が出ているかを確かめる（docs/handoff/app-update-notice/design.md §3）。
 *
 * 今の画面が読み込んだ `/assets/main-<hash>.js` の名前と、入口 `/` を取り直して見つけた名前を比べる。
 * - 確かめる時: 裏から表に戻ったとき／表に出ている間は10分ごと。前回から60秒以内なら確かめない
 * - 裏にいる間は確かめない。新しい版を見つけたら確かめるのをやめる
 * - 通信失敗・名前が取れない（開発サーバー等）ときは何もせず次の時を待つ（画面にも console にも出さない）
 */
const CHECK_INTERVAL_MS = 10 * 60 * 1000;
const MIN_GAP_MS = 60 * 1000;
const FETCH_TIMEOUT_MS = 10 * 1000;
const ENTRY_PATTERN = /\/assets\/main-[A-Za-z0-9_-]+\.js/;

function currentEntryName(): string | null {
  const el = document.querySelector('script[type="module"][src*="/assets/main-"]');
  const src = el?.getAttribute("src") ?? "";
  return ENTRY_PATTERN.exec(src)?.[0] ?? null;
}

export function useAppUpdateCheck(): boolean {
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    if (available) return;
    let cancelled = false;
    let inflight = false;
    let abortTimer: number | undefined;
    let lastCheckedAt = Date.now();

    const check = async () => {
      if (document.hidden || inflight) return;
      const now = Date.now();
      if (now - lastCheckedAt < MIN_GAP_MS) return;
      lastCheckedAt = now;
      const current = currentEntryName();
      if (!current) return;
      inflight = true;
      const controller = new AbortController();
      abortTimer = window.setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
      try {
        const res = await fetch("/", { cache: "no-store", signal: controller.signal });
        if (!res.ok) return;
        const latest = ENTRY_PATTERN.exec(await res.text())?.[0];
        if (latest && latest !== current && !cancelled) setAvailable(true);
      } catch {
        // 黙って次の時を待つ
      } finally {
        window.clearTimeout(abortTimer);
        inflight = false;
      }
    };

    const onVisibility = () => {
      if (!document.hidden) void check();
    };
    document.addEventListener("visibilitychange", onVisibility);
    const timer = window.setInterval(() => void check(), CHECK_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(abortTimer);
      document.removeEventListener("visibilitychange", onVisibility);
      window.clearInterval(timer);
    };
  }, [available]);

  return available;
}
