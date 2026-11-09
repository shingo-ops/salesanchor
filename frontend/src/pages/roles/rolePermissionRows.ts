/**
 * 役割の画面の「行」を作る純粋関数（React を import しない）。
 *
 * - 行 = 同じ許可で一緒に出るメニューのまとまり（正本は constants/menuPermissions.ts の ROLE_ROWS）。
 * - 3択の状態（非表示 / 表示のみ / 編集可 / 個別）は、行の許可のうち持っている数で決める。
 * 設計: docs/handoff/role-menu-permissions/design.md §5〜§6
 */

import type { RoleRowDef, RoleRowSection, RowMenuId } from "../../constants/menuPermissions";

export type RowState = "off" | "view" | "edit" | "mixed";

export interface PermLike {
  key: string;
  category: string;
}

export interface PermRow {
  id: string;
  section: RoleRowSection | "other";
  /** 一緒に出るメニュー。許可だけの行は null */
  menus: RowMenuId[] | null;
  /** 実在する許可の鍵だけ */
  keys: string[];
  fixed?: "always" | "ownerOnly" | "roleEditors";
  noteKey?: string;
  /** 「メニュー以外の許可」の行だけ: DB の区分名 */
  category?: string;
}

/** 「見る」許可か: 最後の部分が view・view_ で始まる・_view で終わる */
export function isViewKey(key: string): boolean {
  const last = key.slice(key.lastIndexOf(".") + 1);
  return last === "view" || last.startsWith("view_") || last.endsWith("_view");
}

/** メニュー用の許可（画面に出さず、保存のときもそのまま残す） */
export function isMenuKey(key: string): boolean {
  return key.startsWith("menu.");
}

/** ／（表示のみ）を押せる行か: 見る許可がある */
export function canSetView(rowKeys: readonly string[]): boolean {
  return rowKeys.some(isViewKey);
}

/** ✓（編集可）を押せる行か: 見る許可以外がある */
export function canSetEdit(rowKeys: readonly string[]): boolean {
  return rowKeys.some((k) => !isViewKey(k));
}

/** 行を作る。categoryOrder は「メニュー以外の許可」の区分の並び（小さい順・無い区分は後ろ） */
export function buildRows(
  allPerms: readonly PermLike[],
  roleRows: readonly RoleRowDef[],
  categoryOrder: Readonly<Record<string, number>> = {},
): PermRow[] {
  const existing = new Set(allPerms.map((p) => p.key));
  const used = new Set<string>();
  const rows: PermRow[] = [];

  for (const def of roleRows) {
    const keys = def.keys.filter((k) => existing.has(k));
    // 許可が1つも実在しない行は出さない（固定の行は許可を持たないので残す）
    if (!def.fixed && keys.length === 0) continue;
    for (const k of keys) used.add(k);
    rows.push({
      id: def.id,
      section: def.section,
      menus: def.menus ? [...def.menus] : null,
      keys,
      fixed: def.fixed,
      noteKey: def.noteKey,
    });
  }

  const byCategory = new Map<string, string[]>();
  for (const p of allPerms) {
    if (used.has(p.key) || isMenuKey(p.key)) continue;
    const list = byCategory.get(p.category);
    if (list) list.push(p.key);
    else byCategory.set(p.category, [p.key]);
  }
  const others = Array.from(byCategory.entries())
    .sort(([a], [b]) => (categoryOrder[a] ?? 100) - (categoryOrder[b] ?? 100))
    .map(([category, keys]): PermRow => ({
      id: `other:${category}`,
      section: "other",
      menus: null,
      keys,
      category,
    }));

  return [...rows, ...others];
}

/** 行の状態。held は持っている許可の鍵 */
export function rowState(rowKeys: readonly string[], held: ReadonlySet<string>): RowState {
  if (rowKeys.length === 0) return "off";
  const heldKeys = rowKeys.filter((k) => held.has(k));
  if (heldKeys.length === 0) return "off";
  if (heldKeys.length === rowKeys.length) return canSetEdit(rowKeys) ? "edit" : "view";
  // 一部だけ: 見る許可だけを全部持っていれば「表示のみ」
  const viewKeys = rowKeys.filter(isViewKey);
  if (viewKeys.length > 0 && canSetEdit(rowKeys)
      && heldKeys.length === viewKeys.length && heldKeys.every(isViewKey)) {
    return "view";
  }
  return "mixed";
}

/** 押したあとの許可の一覧。新しい Set を返し、行の外の鍵（menu.* を含む）は1つも変えない */
export function applyState(
  held: ReadonlySet<string>,
  rowKeys: readonly string[],
  state: RowState,
): Set<string> {
  const next = new Set(held);
  if (state === "mixed") return next;
  if (state === "off") {
    for (const k of rowKeys) next.delete(k);
  } else if (state === "view") {
    if (!canSetView(rowKeys)) return next;
    for (const k of rowKeys) {
      if (isViewKey(k)) next.add(k);
      else next.delete(k);
    }
  } else {
    if (!canSetEdit(rowKeys) && !canSetView(rowKeys)) return next;
    for (const k of rowKeys) next.add(k);
  }
  return next;
}
