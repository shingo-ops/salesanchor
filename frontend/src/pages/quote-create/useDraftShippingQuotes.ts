/**
 * 請求書の送料の一覧（POST /invoices/draft-shipping-quotes）を取る（invoice-create-portfolio design-v2 §3-5・K6・K7）。
 *
 * - 会社と総重量が変わったときだけ、最後の変更から 800 ミリ秒待って 1 回呼ぶ。
 * - 同じ会社・同じ総重量の答えは覚えておき、もう呼ばない（K7）。
 * - 総重量が 0 以下・会社が無いときは呼ばない。
 * - 答えは「どの材料に対する答えか（key）」と組で持ち、材料が変わった瞬間に古い答えは使わない。
 * 届け先・発送元の国はサーバーが決める（画面からは送らない）。
 */
import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";

export const DRAFT_SHIPPING_QUOTES_PATH = "/invoices/draft-shipping-quotes";
export const SHIPPING_QUOTE_DELAY_MS = 800;

/** backend/app/schemas/shipping.py の ShippingCalcResult（使う項目だけ）。fee は Decimal なので文字で届くことがある */
export interface DraftShippingRate {
  carrier: string;
  zone: string;
  fee: string | number;
  currency: string;
  source: "static" | "fedex_live";
  service_type: string | null;
  service_name: string | null;
  transit_days: number | null;
}

export interface DraftShippingQuotes {
  results: DraftShippingRate[];
  live_error: string | null;
}

export interface DraftShippingQuotesState {
  /** いまの材料の答え。まだ届いていない・呼ばないときは null */
  quotes: DraftShippingQuotes | null;
  /** いまの材料で答えを待っているか */
  loading: boolean;
  /** いまの材料で失敗したときの文（api が文言にしたもの） */
  error: string;
  /** いまの材料の鍵。呼ばないときは "" */
  key: string;
}

interface QuoteAnswer {
  key: string;
  data: DraftShippingQuotes | null;
  error: string;
}

/** 総重量は小数 3 けたまで（サーバーの weight_kg の決まり） */
export function roundWeight(weightKg: number): number {
  return Math.round(weightKg * 1000) / 1000;
}

export function shippingQuoteKey(companyId: number | null, weightKg: number): string {
  const w = roundWeight(weightKg);
  return companyId === null || !(w > 0) ? "" : `${companyId}:${w.toFixed(3)}`;
}

export function useDraftShippingQuotes(companyId: number | null, weightKg: number): DraftShippingQuotesState {
  const key = shippingQuoteKey(companyId, weightKg);
  const cache = useRef(new Map<string, DraftShippingQuotes>());
  const seq = useRef(0);
  const [answer, setAnswer] = useState<QuoteAnswer>({ key: "", data: null, error: "" });

  useEffect(() => {
    if (key === "") return undefined;
    const mine = ++seq.current;
    const cached = cache.current.get(key);
    if (cached !== undefined) {
      setAnswer({ key, data: cached, error: "" });
      return undefined;
    }
    const [companyPart, weightPart] = key.split(":");
    const timer = setTimeout(() => {
      api
        .post<DraftShippingQuotes>(DRAFT_SHIPPING_QUOTES_PATH, { company_id: Number(companyPart), weight_kg: Number(weightPart) })
        .then((data) => {
          const safe: DraftShippingQuotes = {
            results: Array.isArray(data?.results) ? data.results : [],
            live_error: typeof data?.live_error === "string" ? data.live_error : null,
          };
          cache.current.set(key, safe);
          if (seq.current === mine) setAnswer({ key, data: safe, error: "" });
        })
        .catch((e: unknown) => {
          if (seq.current === mine) setAnswer({ key, data: null, error: e instanceof Error ? e.message : String(e) });
        });
    }, SHIPPING_QUOTE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [key]);

  const fresh = key !== "" && answer.key === key;
  return {
    quotes: fresh ? answer.data : null,
    loading: key !== "" && !fresh,
    error: fresh ? answer.error : "",
    key,
  };
}

/** 送料の行の額（小数 2 けたに丸めた数）。数でなければ null */
export function rateFee(rate: DraftShippingRate): number | null {
  const n = typeof rate.fee === "number" ? rate.fee : Number(rate.fee);
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : null;
}
