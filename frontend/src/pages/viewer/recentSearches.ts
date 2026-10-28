/**
 * recentSearches — 閲覧ページ（/viewer/）の「最近使った語」の読み書き
 * （docs/handoff/viewer-search-mercari/design.md 4-4）。
 *
 * 置き場: localStorage のキー `viewer:recent-searches`。サーバーには送らない
 * （閲覧ページは誰でも見られるため。design.md 4-4）。
 * 形: 文字列の配列。新しい順・重複なし・最大10件（design.md ③ 単体テスト U1）。
 *
 * localStorage が使えない／壊れている／JSON が壊れている環境でも例外を投げない
 * （design.md ③ U2）。読みは空配列を返し、書きは黙って諦める。
 */

const STORAGE_KEY = "viewer:recent-searches";
const MAX_ITEMS = 10;

/** localStorage へのアクセス自体が例外を投げる環境（プライベートモード等）を吸収する */
function getStorage(): Storage | null {
  try {
    return window.localStorage ?? null;
  } catch {
    return null;
  }
}

/** 保存されている履歴を読む。使えない/壊れているときは空配列（design.md ③ U2） */
export function loadRecentSearches(): string[] {
  const storage = getStorage();
  if (!storage) return [];
  let raw: string | null;
  try {
    raw = storage.getItem(STORAGE_KEY);
  } catch {
    return [];
  }
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((v): v is string => typeof v === "string");
  } catch {
    return [];
  }
}

/** 黙って諦める書き込み（design.md ③ U2） */
function trySave(list: string[]): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch {
    // 書き込みに失敗しても黙って諦める
  }
}

/** 語を先頭に積む。新しい順・重複なし・最大10件に保つ（design.md ③ U1）。戻り値は保存後の一覧 */
export function addRecentSearch(term: string): string[] {
  const current = loadRecentSearches();
  if (!term) return current;
  const next = [term, ...current.filter((v) => v !== term)].slice(0, MAX_ITEMS);
  trySave(next);
  return next;
}

/** 履歴を空にする（「すべて消す」。design.md 4-4） */
export function clearRecentSearches(): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.removeItem(STORAGE_KEY);
  } catch {
    // 黙って諦める
  }
}
