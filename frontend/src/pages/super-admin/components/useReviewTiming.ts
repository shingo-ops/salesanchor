/**
 * 要確認パネルの計時（便0）。
 * パネルが出てから「要確認タブの一覧の1行目が描かれるまで」を測り、mount ごとに1回だけ
 * POST /tcg/analysis-results/client-timing へ送る。失敗しても画面には何も出さない。
 */
import { useCallback, useEffect, useRef } from "react";
import { api } from "../../../lib/api";

const TIMING_PATH = "/tcg/analysis-results/client-timing";
const MAX_MS = 120000;

type TimingEntry = "first" | "return";

/** この文書の中で最初のパネル mount かどうか（2回目以降は return） */
let panelMountSeen = false;

const clampMs = (ms: number) => Math.min(MAX_MS, Math.max(0, ms));

interface UseReviewTimingArgs {
  /** 要確認タブ（production）の一覧データが入っているか */
  shown: boolean;
  rows: number;
  pageSize: number;
}

export function useReviewTiming({ shown, rows, pageSize }: UseReviewTimingArgs) {
  const mountAtRef = useRef<number | null>(null);
  const entryRef = useRef<TimingEntry>("first");
  if (mountAtRef.current === null) {
    mountAtRef.current = performance.now();
    entryRef.current = panelMountSeen ? "return" : "first";
    panelMountSeen = true;
  }
  const listMsRef = useRef(0);
  const doneRef = useRef(false);

  /** 表示に使った取得の所要時間（取り消された取得では呼ばない） */
  const recordListMs = useCallback((ms: number) => {
    listMsRef.current = ms;
  }, []);

  /** 要確認タブが表示される前に別タブへ移った場合など、この mount では送らない */
  const abandon = useCallback(() => {
    doneRef.current = true;
  }, []);

  useEffect(() => {
    if (!shown || doneRef.current) return;
    let secondFrame = 0;
    const firstFrame = requestAnimationFrame(() => {
      secondFrame = requestAnimationFrame(() => {
        if (doneRef.current) return;
        doneRef.current = true;
        const end = performance.now();
        const body = {
          panel_ms: clampMs(end - (mountAtRef.current ?? end)),
          list_ms: clampMs(listMsRef.current),
          doc_ms: clampMs(end),
          rows,
          page_size: pageSize,
          entry: entryRef.current,
        };
        Promise.resolve()
          .then(() => api.post(TIMING_PATH, body))
          .catch(() => {});
      });
    });
    return () => {
      cancelAnimationFrame(firstFrame);
      cancelAnimationFrame(secondFrame);
    };
  }, [shown, rows, pageSize]);

  return { recordListMs, abandon };
}
