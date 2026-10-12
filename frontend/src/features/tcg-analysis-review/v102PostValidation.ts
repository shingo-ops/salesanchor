/**
 * v102 の書き写しを直す画面の入力検査と送信形（設計 §13-5。サーバー側の検査と同じ規則を保存前に画面でも見る）。
 * 行番号は整数・1〜行数・件の中で重複なし・1つ以上。価格・数量は200字以内。件は1件以上。
 */
export const TEXT_MAX_LENGTH = 200;

export interface EditRow {
  /** 画面内の識別子（新しい行にも付く） */
  key: string;
  /** 既存の件の id。新しい件は null */
  id: string | null;
  linesText: string;
  price: string;
  quantity: string;
  /** 件の理由（表示用の訳済みの文字。編集しない） */
  reasonsText: string;
}

export type LinesErrorCode = "empty" | "notInteger" | "outOfRange" | "duplicate";

export interface RowErrors {
  lines: LinesErrorCode | null;
  price: boolean;
  quantity: boolean;
}

export interface ValidationResult {
  rowErrors: Record<string, RowErrors>;
  hasNoRows: boolean;
  isValid: boolean;
}

export interface ParsedLines {
  lines: number[];
  error: LinesErrorCode | null;
}

/** 「3,5,7」の形を読む。空白は無視、半角の整数だけ受ける。 */
export function parseLines(text: string, lineCount: number): ParsedLines {
  const parts = text.split(",").map((part) => part.trim());
  if (parts.length === 1 && parts[0] === "") return { lines: [], error: "empty" };
  if (parts.some((part) => !/^[0-9]+$/.test(part))) return { lines: [], error: "notInteger" };
  const lines = parts.map(Number);
  if (lines.some((n) => n < 1 || n > lineCount)) return { lines, error: "outOfRange" };
  if (new Set(lines).size !== lines.length) return { lines, error: "duplicate" };
  return { lines, error: null };
}

export function validateRows(rows: EditRow[], lineCount: number): ValidationResult {
  const rowErrors: Record<string, RowErrors> = {};
  for (const row of rows) {
    rowErrors[row.key] = {
      lines: parseLines(row.linesText, lineCount).error,
      price: row.price.length > TEXT_MAX_LENGTH,
      quantity: row.quantity.length > TEXT_MAX_LENGTH,
    };
  }
  const hasNoRows = rows.length === 0;
  const hasRowError = Object.values(rowErrors).some((e) => e.lines !== null || e.price || e.quantity);
  return { rowErrors, hasNoRows, isValid: !hasNoRows && !hasRowError };
}

/** 空欄（空白だけを含む）は null で送る。 */
function blankToNull(value: string): string | null {
  return value.trim() === "" ? null : value;
}

export interface SaveItemBody {
  id?: string;
  source_lines: number[];
  raw_price: string | null;
  raw_quantity: string | null;
}

/** 検査を通った行から PUT の件を作る。新しい件は id を付けない。 */
export function toSaveItems(rows: EditRow[], lineCount: number): SaveItemBody[] {
  return rows.map((row) => {
    const sorted = [...parseLines(row.linesText, lineCount).lines].sort((a, b) => a - b);
    const base = { source_lines: sorted, raw_price: blankToNull(row.price), raw_quantity: blankToNull(row.quantity) };
    return row.id === null ? base : { id: row.id, ...base };
  });
}

/** 選んだ行の原文の色付け範囲。行番号が読めないときは null。 */
export function blockRangeOf(row: EditRow | undefined, lineCount: number): { start: number; end: number } | null {
  if (!row) return null;
  const parsed = parseLines(row.linesText, lineCount);
  if (parsed.error !== null && parsed.error !== "duplicate") return null;
  if (parsed.lines.length === 0) return null;
  return { start: Math.min(...parsed.lines), end: Math.max(...parsed.lines) };
}
