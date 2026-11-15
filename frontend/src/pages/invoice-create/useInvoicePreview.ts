/**
 * 請求書の試算（POST /invoices/preview）を、入力が止まって 300 ミリ秒後に 1 回だけ取りに行く
 * （invoice-create-portfolio 便D・design.md §3-2）。
 *
 * 合計・税・関税の計算はサーバーだけが行う（画面で足し算しない）。
 * 答えは「どの入力に対する答えか（key）」と組で持ち、入力が変わった瞬間に古い答えは使わない（fresh=false）。
 * request が null のとき（会社・通貨・明細がそろわないとき）は取りに行かない。
 */
import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import type { InvoicePreview, InvoicePreviewRequest } from "../../lib/invoiceDraftContext";

const PREVIEW_DELAY_MS = 300;

interface PreviewAnswer {
  key: string;
  data: InvoicePreview | null;
  error: string;
}

export interface InvoicePreviewState {
  /** いまの入力に対する答え。まだ届いていない・入力が変わった直後は null */
  preview: InvoicePreview | null;
  /** いまの入力に対する失敗の文（api が文言にしたもの） */
  error: string;
  /** いまの入力に対する答えが届いているか */
  fresh: boolean;
}

export function useInvoicePreview(request: InvoicePreviewRequest | null): InvoicePreviewState {
  const key = request === null ? "" : JSON.stringify(request);
  const [answer, setAnswer] = useState<PreviewAnswer>({ key: "", data: null, error: "" });
  const seq = useRef(0);

  useEffect(() => {
    if (key === "") return undefined;
    const mine = ++seq.current;
    const timer = setTimeout(() => {
      api
        .post<InvoicePreview>("/invoices/preview", JSON.parse(key) as InvoicePreviewRequest)
        .then((data) => {
          if (seq.current === mine) setAnswer({ key, data, error: "" });
        })
        .catch((e: unknown) => {
          if (seq.current === mine) {
            setAnswer({ key, data: null, error: e instanceof Error ? e.message : String(e) });
          }
        });
    }, PREVIEW_DELAY_MS);
    return () => clearTimeout(timer);
  }, [key]);

  const fresh = key !== "" && answer.key === key;
  return {
    preview: fresh ? answer.data : null,
    error: fresh ? answer.error : "",
    fresh,
  };
}
