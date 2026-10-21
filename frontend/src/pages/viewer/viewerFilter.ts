/**
 * 閲覧ページの絞り込み・検索・並べ替え（すべて手元の行に対する純関数）。
 * 規則の正本は設計 D4（docs/handoff/gas-viewer-fresh-fast/design.md）。アプリの在庫表（サーバー側）と同じ結果にする。
 * 検索の正規化は features/inventory/searchNormalize.ts の normalizeForSearch を使う（ここに正規化は書かない）。
 */
import { normalizeForSearch } from "../../features/inventory/searchNormalize";
import type { ViewerRow, ViewerTableRow } from "./types";

export const PER_PAGE = 50;
export const TAB_ALL = "all";
/** 既定の並び（アプリの InventoryPage の release_date 降順と同じ。ADR-1014 改訂 2026-10-18） */
export const DEFAULT_SORT_KEY = "release_date";
export const DEFAULT_SORT_DIR = "desc" as const;
/** 並べ替えプルダウンの3択（既定の発売日の新しい順は見出しで表す。アプリの SORT_MENU_VALUES と同じ） */
export const SORT_MENU_VALUES = ["unit_price:asc", "quantity:desc", "offered_at:desc"] as const;

export type SortDir = "asc" | "desc";

export interface ViewerFilters {
  /** シリーズのタブ。TAB_ALL は全て */
  tab: string;
  /** 検索（空白区切りは AND） */
  query: string;
  /** 24時間以内だけ出す */
  freshOnly: boolean;
  /** 24時間の時間数（応答の fresh_window_hours） */
  freshWindowHours: number;
  /** 選んだ提供者だけ出す（空なら全員） */
  providers: string[];
  /** 選んだコンディションだけ出す（空なら全部） */
  conditions: string[];
  priceMin: string;
  priceMax: string;
  qtyMin: string;
  qtyMax: string;
}

export function withIndex(rows: ViewerRow[]): ViewerTableRow[] {
  return rows.map((r, idx) => ({ ...r, idx }));
}

/** posted_at（タイムゾーン無しの日本時間 'YYYY-MM-DD HH:MM:SS'）をミリ秒にする。読めなければ null。 */
export function parsePostedAt(s: string): number | null {
  if (!s) return null;
  const ms = Date.parse(`${s.trim().replace(" ", "T")}+09:00`);
  return Number.isNaN(ms) ? null : ms;
}

/** 空白区切りの AND。4つの対象（日本語名・英語名・型番・検索ワード）のどれかに各語が含まれる。 */
export function matchesQuery(row: ViewerRow, query: string): boolean {
  const tokens = query
    .split(/\s+/)
    .map((tk) => normalizeForSearch(tk))
    .filter((tk) => tk !== "");
  if (tokens.length === 0) return true;
  const hay = normalizeForSearch(
    [row.japanese_title, row.english_title, row.mark, row.search_keywords].join("\n"),
  );
  return tokens.every((tk) => hay.includes(tk));
}

/** 範囲の入力（'' や不正値は無視）を 0 以上の整数にする */
function toBound(s: string): number | null {
  const n = Number(s);
  return s.trim() !== "" && Number.isFinite(n) && n >= 0 ? Math.floor(n) : null;
}

function inRange(value: string, min: number | null, max: number | null): boolean {
  if (min === null && max === null) return true;
  if (value === "") return false;
  const n = Number(value);
  if (!Number.isFinite(n)) return false;
  if (min !== null && n < min) return false;
  if (max !== null && n > max) return false;
  return true;
}

export function filterRows(rows: ViewerTableRow[], f: ViewerFilters, now: number): ViewerTableRow[] {
  const pMin = toBound(f.priceMin);
  const pMax = toBound(f.priceMax);
  const qMin = toBound(f.qtyMin);
  const qMax = toBound(f.qtyMax);
  const freshFrom = now - f.freshWindowHours * 3600 * 1000;
  return rows.filter((r) => {
    if (f.tab !== TAB_ALL && r.series !== f.tab) return false;
    if (f.freshOnly) {
      const ts = parsePostedAt(r.posted_at);
      if (ts === null || ts < freshFrom) return false;
    }
    if (f.providers.length > 0 && !f.providers.includes(r.provider)) return false;
    if (f.conditions.length > 0 && !f.conditions.includes(r.condition)) return false;
    if (!inRange(r.unit_price, pMin, pMax)) return false;
    if (!inRange(r.quantity, qMin, qMax)) return false;
    return matchesQuery(r, f.query);
  });
}

// ── 並べ替え ────────────────────────────────────────────────

/** 文字の比べ方は Intl.Collator('en')（numeric は付けない。数字を数として並べると PG と違うため） */
const collator = new Intl.Collator("en");

/** '' は他のどの文字より前に置く */
function compareText(a: string, b: string): number {
  if (a === b) return 0;
  if (a === "") return -1;
  if (b === "") return 1;
  return collator.compare(a, b);
}

/** 'YYYY-MM-DD…' 形式の文字は、そのまま文字の順で比べる（'' は先頭） */
function comparePlain(a: string, b: string): number {
  if (a === b) return 0;
  return a < b ? -1 : 1;
}

type Compare = (a: ViewerTableRow, b: ViewerTableRow) => number;

/** 空を末尾に置く比べ方（昇順・降順のどちらでも末尾）。cmp は空でない値どうしの比べ方。 */
function nullsLast(get: (r: ViewerTableRow) => string, cmp: (x: string, y: string) => number, dir: SortDir): Compare {
  return (a, b) => {
    const x = get(a);
    const y = get(b);
    if (x === "" && y === "") return 0;
    if (x === "") return 1;
    if (y === "") return -1;
    const c = cmp(x, y);
    return dir === "asc" ? c : -c;
  };
}

/** 空も値として比べる（昇順では先頭、降順では末尾） */
function plain(get: (r: ViewerTableRow) => string, cmp: (x: string, y: string) => number, dir: SortDir): Compare {
  return (a, b) => {
    const c = cmp(get(a), get(b));
    return dir === "asc" ? c : -c;
  };
}

const numCmp = (x: string, y: string): number => Number(x) - Number(y);

/** 列（表の見出しの key とプルダウンの offered_at）→ 比べる値。アプリの _SORT_COLUMNS に対応する。 */
function columnCompare(sortKey: string, dir: SortDir): Compare | null {
  switch (sortKey) {
    case "mark":
      return nullsLast((r) => r.mark, compareText, dir);
    case "condition":
      return plain((r) => r.condition, compareText, dir);
    case "offer_type":
      return plain((r) => r.status, compareText, dir);
    case "quantity":
      return nullsLast((r) => r.quantity, numCmp, dir);
    case "unit_price":
      return nullsLast((r) => r.unit_price, numCmp, dir);
    case "supplier":
      return plain((r) => r.provider, compareText, dir);
    case "offered_at":
      return plain((r) => r.posted_at, comparePlain, dir);
    case "release_date":
      return nullsLast((r) => r.release_date, comparePlain, dir);
    default:
      return null;
  }
}

/**
 * アプリの並びと同じ（ADR-1014 改訂 2026-10-18）。
 * まとまり（商品）の順: 発売日（空は末尾）→ english_title → japanese_title。発売日の向きは release_date を選んだときだけ sortDir。ほかの並び替えでは desc（既定と同じ、ADR-1014 改訂 2026-10-19）。
 * まとまりの中: 状態のまとまり（元の順の最小 idx の昇順＝価値順）→ 選んだ列、最後に元の順。商品名（name）の見出しだけは変更前のまま、
 * english_title と japanese_title を同じ向きで並べる。
 */
export function sortRows(rows: ViewerTableRow[], sortKey: string, sortDir: SortDir): ViewerTableRow[] {
  const keys: Compare[] = [];
  if (sortKey === "name") {
    keys.push(plain((r) => r.english_title, compareText, sortDir));
    keys.push(plain((r) => r.japanese_title, compareText, sortDir));
  } else {
    keys.push(nullsLast((r) => r.release_date, comparePlain, sortKey === "release_date" ? sortDir : "desc"));
    keys.push(plain((r) => r.english_title, compareText, "asc"));
    keys.push(plain((r) => r.japanese_title, compareText, "asc"));
    if (sortKey !== "release_date") {
      // 状態ブロック番号: 同じ商品・同じ状態の行のうち最小の idx（= サーバーの価値順）。選んだ列より先に比べる（ADR-1014 改訂 2026-10-19（5））
      const blockOf = (r: ViewerTableRow) =>
        `${r.release_date}\u0000${r.english_title}\u0000${r.japanese_title}\u0000${r.condition}`;
      const minIdx = new Map<string, number>();
      for (const r of rows) {
        const k = blockOf(r);
        const cur = minIdx.get(k);
        if (cur === undefined || r.idx < cur) minIdx.set(k, r.idx);
      }
      keys.push((a, b) => (minIdx.get(blockOf(a)) ?? 0) - (minIdx.get(blockOf(b)) ?? 0));
      const col = columnCompare(sortKey, sortDir);
      if (col) keys.push(col);
    }
  }
  return [...rows].sort((a, b) => {
    for (const k of keys) {
      const c = k(a, b);
      if (c !== 0) return c;
    }
    return a.idx - b.idx;
  });
}

// ── タブ・提供者・コンディションの候補 ──────────────────────

export interface TabCount {
  key: string;
  count: number;
}

/** シリーズのタブ：件数の多い順（同数は名前順）。series が空の行は「全て」にだけ入る。 */
export function seriesTabs(rows: ViewerRow[]): TabCount[] {
  const counts = new Map<string, number>();
  for (const r of rows) {
    if (r.series === "") continue;
    counts.set(r.series, (counts.get(r.series) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count || compareText(a.key, b.key));
}

/* eslint-disable local/no-japanese-literal -- DB の type_master.name_ja と照合する値（画面文言ではない）。アプリ在庫表の MAIN_TCG_CODES の name_ja */
/** タブに常時出す主な3つ。閲覧ページの行には code が無いので名前で合わせる（docs/handoff/inventory-tabs-attach-table/recon.md 参照）。
 *  type_master の名前を変えたらここと GAS index.html の MAIN_SERIES も直す */
export const MAIN_SERIES: readonly string[] = ["ポケモン", "ワンピース", "ドラゴンボール"];
/* eslint-enable local/no-japanese-literal */

/** 「その他」に入るシリーズ：空でなく MAIN_SERIES に無いものを重複なしで名前の順に並べる */
export function otherSeries(rows: ViewerRow[]): string[] {
  return distinctValues(rows, (r) => r.series).filter((s) => !MAIN_SERIES.includes(s));
}

/** 重複を除いた値を文字の順で並べる（'' は除く） */
export function distinctValues(rows: ViewerRow[], pick: (r: ViewerRow) => string): string[] {
  return [...new Set(rows.map(pick).filter((v) => v !== ""))].sort(compareText);
}

// ── 同じ商品のまとまりの「最安」「在庫最多」バッジ（ADR-1014 改訂 2026-10-19（2）） ──────────────

export type BlockFlags = { badge_cheapest: boolean; badge_most_stock: boolean };

/** 値が数なら整数に丸めて返す（画面に出る値と同じ）。空・数でない値は null（比べる対象から外す）。 */
function roundedOrNull(s: string): number | null {
  if (s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? Math.round(n) : null;
}

/**
 * 絞り込み後・ページ前の行に、まとまりごとの最安・在庫最多の印を付ける。
 * まとまり = 発売日・英語名・日本語名・ステータス・状態が全て同じ行（ADR-1014 改訂 2026-10-19（3））。最小（最大）と等しい行は全部に付け、
 * 値のある行が1行以下、または全部同じ値のときは付けない。T の項目（idx など）は落とさない。
 */
export function markBlockBadges<T extends ViewerRow>(rows: T[]): (T & BlockFlags)[] {
  const groups = new Map<string, { prices: (number | null)[]; qtys: (number | null)[] }>();
  const keyOf = (r: T) => `${r.release_date}\u0000${r.english_title}\u0000${r.japanese_title}\u0000${r.status}\u0000${r.condition}`;
  const parsed = rows.map((r) => ({ price: roundedOrNull(r.unit_price), qty: roundedOrNull(r.quantity) }));
  rows.forEach((r, i) => {
    const key = keyOf(r);
    const g = groups.get(key) ?? { prices: [], qtys: [] };
    g.prices.push(parsed[i].price);
    g.qtys.push(parsed[i].qty);
    groups.set(key, g);
  });
  // 値が2つ以上あり、最小と最大が違うときだけ、その極値を返す（それ以外は null）
  const extremes = (vals: (number | null)[]) => {
    const nums = vals.filter((v): v is number => v !== null);
    if (nums.length < 2) return null;
    const lo = Math.min(...nums);
    const hi = Math.max(...nums);
    return lo < hi ? { lo, hi } : null;
  };
  const stats = new Map<string, { price: ReturnType<typeof extremes>; qty: ReturnType<typeof extremes> }>();
  for (const [key, g] of groups) stats.set(key, { price: extremes(g.prices), qty: extremes(g.qtys) });
  return rows.map((r, i) => {
    const s = stats.get(keyOf(r))!;
    return {
      ...r,
      badge_cheapest: s.price !== null && parsed[i].price === s.price.lo,
      badge_most_stock: s.qty !== null && parsed[i].qty === s.qty.hi,
    };
  });
}
