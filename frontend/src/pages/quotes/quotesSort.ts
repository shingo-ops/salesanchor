/**
 * 見積履歴一覧のステータスバッジ配色＆各列ソートの純関数。
 * QuotesPage から分離してユニットテスト可能にする（副作用なし）。
 */

/** ソート対象として参照する見積フィールドの最小形（QuotesPage の Quote はこの上位互換）。 */
export interface SortableQuote {
  quote_code: string | null;
  company_name: string | null;
  contact_name: string | null;
  created_by_name: string | null;
  currency: string;
  total_amount: number | null;
  status: string;
  validity_date: string | null;
  created_at: string;
}

/** テーブルのステータスバッジと同じ配色クラス名（フィルタボタンと共用）。 */
export const badgeVariant = (status: string): string =>
  status === "approved" ? "won"
    : status === "rejected" ? "lost"
      : status === "expired" ? "cancelled"
        : status === "sent" ? "negotiating"
          : "pending";

/** 各列ソート用の値抽出（クライアントサイド）。文字列 or 数値を返す。 */
export const SORT_VALUE: Record<string, (q: SortableQuote) => string | number> = {
  quote_code: (q) => q.quote_code ?? "",
  customer: (q) => `${q.company_name ?? ""}${q.contact_name ?? ""}`,
  sales_rep: (q) => q.created_by_name ?? "",
  currency: (q) => q.currency ?? "",
  total: (q) => q.total_amount ?? Number.NEGATIVE_INFINITY,
  status: (q) => q.status ?? "",
  validity_date: (q) => q.validity_date ?? "",
  created_at: (q) => q.created_at ?? "",
};

/** 一覧を field/dir で並べ替えた新配列を返す（元配列は変更しない）。 */
export function sortQuotes<T extends SortableQuote>(
  quotes: T[],
  field: string,
  dir: "asc" | "desc",
): T[] {
  const getv = SORT_VALUE[field] ?? SORT_VALUE.created_at;
  const factor = dir === "asc" ? 1 : -1;
  return [...quotes].sort((a, b) => {
    const av = getv(a);
    const bv = getv(b);
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * factor;
    return String(av).localeCompare(String(bv), "ja") * factor;
  });
}
