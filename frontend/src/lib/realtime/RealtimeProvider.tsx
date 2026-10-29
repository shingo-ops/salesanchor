/**
 * ADR-1016: 即時反映の合図を 1 本の SSE で受け、購読者へ配る。
 * 認証と再接続は useSSE.ts のやり方（fetch + ReadableStream、指数バックオフ）をまねる。
 */
import { useEffect, useMemo, useRef, type ReactNode } from "react";

import { getAccessToken, hasSession } from "../auth/selfAuth";
import { RealtimeContext, type RealtimeEvent, type RealtimeHandler, type RealtimeApi } from "./context";
import { getClientId } from "./clientId";

const ENDPOINT = "/api/v1/events/stream";
const INIT_RETRY_MS = 2_000;
const MAX_RETRY_MS = 300_000;
const BACKOFF = 2;

interface Subscriber {
  topics: readonly string[];
  handler: RealtimeHandler;
}

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const subscribersRef = useRef<Set<Subscriber>>(new Set());

  const api = useMemo<RealtimeApi>(
    () => ({
      clientId: getClientId(),
      subscribe(topics, handler) {
        const sub: Subscriber = { topics, handler };
        subscribersRef.current.add(sub);
        return () => {
          subscribersRef.current.delete(sub);
        };
      },
    }),
    []
  );

  useEffect(() => {
    let cancelled = false;
    let retry = INIT_RETRY_MS;
    let everConnected = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    // cleanup で fetch を即座に止める（StrictMode の二重実行で 2 本つないだままにしない）
    const abort = new AbortController();

    function emit(ev: RealtimeEvent): void {
      for (const sub of Array.from(subscribersRef.current)) {
        if ("reconnected" in ev || sub.topics.includes(ev.topic)) sub.handler(ev);
      }
    }

    function scheduleReconnect(): void {
      if (cancelled) return;
      const delay = retry;
      retry = Math.min(delay * BACKOFF, MAX_RETRY_MS);
      timer = setTimeout(() => {
        if (!cancelled) void connect();
      }, delay);
    }

    async function connect(): Promise<void> {
      if (!hasSession()) {
        scheduleReconnect();
        return;
      }
      let token: string;
      try {
        token = await getAccessToken();
      } catch {
        scheduleReconnect();
        return;
      }
      if (cancelled) return;

      let response: Response;
      try {
        response = await fetch(ENDPOINT, {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "text/event-stream",
            "Cache-Control": "no-cache",
          },
          signal: abort.signal,
        });
      } catch {
        scheduleReconnect();
        return;
      }
      if (!response.ok || !response.body) {
        scheduleReconnect();
        return;
      }

      retry = INIT_RETRY_MS;
      // 2 回目以降の接続成功 = 切れている間の変更を取りこぼした可能性がある
      if (everConnected) emit({ reconnected: true });
      everConnected = true;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      try {
        while (!cancelled) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const chunks = buf.split("\n\n");
          buf = chunks.pop() ?? "";
          for (const chunk of chunks) {
            if (!chunk.includes("event: change")) continue;
            const line = chunk.split("\n").find((l) => l.startsWith("data:"));
            if (!line) continue;
            try {
              const parsed = JSON.parse(line.slice(5).trim()) as { topic?: string; origin?: string | null };
              if (typeof parsed.topic === "string") {
                emit({ topic: parsed.topic, origin: parsed.origin ?? null });
              }
            } catch {
              // 壊れた合図は無視
            }
          }
        }
      } catch {
        // 切断は下で再接続
      } finally {
        void reader.cancel().catch(() => undefined);
      }
      if (!cancelled) scheduleReconnect();
    }

    void connect();
    return () => {
      cancelled = true;
      abort.abort();
      if (timer) clearTimeout(timer);
    };
  }, []);

  return <RealtimeContext.Provider value={api}>{children}</RealtimeContext.Provider>;
}
