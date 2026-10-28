/**
 * searchSuggestions.ts — 打っている間だけ出す候補（便12b・design.md 4-1）。
 * 候補は検索が実際に見ている matchesQuery（viewerFilter.ts）で当たった行からだけ作る。
 * シリーズ名・提供者名は matchesQuery の対象外なので、候補も対象外のまま
 * （押しても0件になる候補を作らないための作り。recon §2）。
 */
import { normalizeForSearch } from "../../features/inventory/searchNormalize";
import { matchesQuery } from "./viewerFilter";
import type { ViewerRow } from "./types";

/** 表示名: japanese_title →（空なら）english_title →（空なら）mark */
function displayName(row: ViewerRow): string {
  return row.japanese_title || row.english_title || row.mark;
}

/**
 * draft（打っている途中の語）に当たる候補を最大 limit 件返す。
 * 1. draft を空白区切りの語にして正規化する（matchesQuery と同じ分け方）。空なら [] を返す。
 * 2. 各行を matchesQuery でそのまま判定する（候補を押せば必ず1件以上当たることを作りで保証）。
 * 3. 当たった行の表示名を集め、同じ表示名はまとめる（件数は数えるが画面には出さない＝PO 決定）。
 * 4. 並べ替え: 先頭一致（正規化した表示名が draft の先頭の語で始まる）を先、次に件数の多い順、
 *    同数なら表示名の昇順（localeCompare）。決定論的にする。
 */
export function buildSuggestions(rows: ViewerRow[], draft: string, limit = 10): string[] {
  const tokens = draft
    .split(/\s+/)
    .map((tk) => normalizeForSearch(tk))
    .filter((tk) => tk !== "");
  if (tokens.length === 0) return [];
  const head = tokens[0];

  const counts = new Map<string, number>();
  for (const row of rows) {
    if (!matchesQuery(row, draft)) continue;
    const name = displayName(row);
    if (name === "") continue;
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }

  return [...counts.entries()]
    .sort(([aName, aCount], [bName, bCount]) => {
      const aHead = normalizeForSearch(aName).startsWith(head) ? 0 : 1;
      const bHead = normalizeForSearch(bName).startsWith(head) ? 0 : 1;
      if (aHead !== bHead) return aHead - bHead;
      if (aCount !== bCount) return bCount - aCount;
      return aName.localeCompare(bName);
    })
    .slice(0, limit)
    .map(([name]) => name);
}
