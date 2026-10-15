/**
 * 在庫検索の正規化。GAS 在庫一覧の normalizeForSearch と、backend の normalize_search_text と同じ結果にする。
 * NFKC → 小文字 → ひらがな(U+3041〜U+3096)をカタカナ(+0x60)へ。
 * 共通テストベクタ: searchNormalize.vectors.json（変えるときは backend の test_inventory_distribution_rows_pg.py も触る）。
 */
export function normalizeForSearch(s: string): string {
  return s
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[ぁ-ゖ]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) + 0x60));
}
