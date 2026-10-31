/**
 * ADR-1054: 画面が取ったデータの写しの置き場（この 1 か所だけ）。
 * - QueryClient はここで 1 個だけ作る。ほかの場所で作らない。
 * - 取り方は useApiQuery だけ。中で今の api.get を呼ぶ（通信・送り直し・401 の扱いは api.ts のまま）。
 * - 写しは出すだけ。staleTime は既定の 0 のままにし、開くたび・タブに戻るたびに取り直す。
 * - 写しはメモリだけに持つ（ブラウザの保存に書かない）。
 */
import { QueryClient, useQuery, type UseQueryResult } from "@tanstack/react-query";

import { useAuth } from "../../contexts/AuthContext";
import { api } from "../api";

/** 使われない写しを捨てるまでの時間（30 分・ADR-1054。既定の 5 分だと 5 分を過ぎて戻った画面が初回と同じになる） */
const GC_TIME_MS = 30 * 60 * 1000;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // api.ts が GET を 3 回まで送り直す（api.ts の MAX_RETRIES）。ここでも送り直すと最大 16 回になる
      retry: 0,
      gcTime: GC_TIME_MS,
    },
  },
});

/** path を最初の「?」で分け、前を「/」で区切った言葉（空は捨てる）と後ろ（無ければ空文字）にする。 */
export function splitApiPath(path: string): { words: string[]; query: string } {
  const at = path.indexOf("?");
  const head = at === -1 ? path : path.slice(0, at);
  const query = at === -1 ? "" : path.slice(at + 1);
  return { words: head.split("/").filter((word) => word !== ""), query };
}

/** 写しの名前。例: /companies?status=a → ["api", uid, "companies", { query: "status=a" }] */
export function apiQueryKey(uid: string, path: string): readonly unknown[] {
  const { words, query } = splitApiPath(path);
  return ["api", uid, ...words, { query }];
}

/** 写しを出してから裏で取り直す取り方。ログインしていない間は取りに行かない。 */
export function useApiQuery<T>(path: string, options?: { enabled?: boolean }): UseQueryResult<T> {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  return useQuery({
    queryKey: apiQueryKey(uid ?? "", path),
    queryFn: () => api.get<T>(path),
    enabled: uid !== null && (options?.enabled ?? true),
  });
}

/**
 * 頭の言葉が同じ写しを全部取り直す（条件や id が違う写しも含む）。
 * 例: invalidateApi(uid, ["companies"]) は /companies?… も /companies/5 も取り直す。
 */
export function invalidateApi(uid: string, head: readonly string[]): Promise<void> {
  const { words } = splitApiPath(head.join("/"));
  return queryClient.invalidateQueries({ queryKey: ["api", uid, ...words] });
}
