import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useApiQuery } from "../lib/query/apiQuery";
import type { CustomerStatusRow } from "../lib/customerStatuses";

export interface CustomerStatusOption { value: string; label: string }

/**
 * 会社・連絡先の状態の表（API GET /customer-statuses）を読み、選択肢と名前を出す（ADR-1076）。
 * 選ぶ・出すかは表の列 selectable_on_create・is_active だけで決める。記号で行を選び分けない。
 */
export function useCustomerStatuses() {
  const { i18n } = useTranslation();
  const query = useApiQuery<CustomerStatusRow[]>("/customer-statuses");
  const isJa = (i18n?.language ?? "ja").startsWith("ja");
  const rows = query.data;

  const sorted = useMemo(
    () => (rows ? [...rows].sort((a, b) => a.sort_order - b.sort_order) : []),
    [rows],
  );
  const labelOf = useCallback(
    (row: CustomerStatusRow) => (isJa ? row.name_ja : row.name_en),
    [isJa],
  );

  const options = useCallback(
    (mode: "create" | "edit", currentValue?: string): CustomerStatusOption[] => {
      if (!rows) return [];
      const picked = sorted.filter((r) =>
        mode === "create" ? r.is_active && r.selectable_on_create : r.is_active,
      );
      const list = picked.map((r) => ({ value: r.code, label: labelOf(r) }));
      if (mode === "edit" && currentValue !== undefined && !picked.some((r) => r.code === currentValue)) {
        const current = sorted.find((r) => r.code === currentValue);
        if (current) {
          // 今の値の1行だけ、並び順の位置に加える
          return sorted
            .filter((r) => r === current || picked.includes(r))
            .map((r) => ({ value: r.code, label: labelOf(r) }));
        }
      }
      return list;
    },
    [rows, sorted, labelOf],
  );

  const nameOf = useCallback(
    (code: string): string => {
      const row = sorted.find((r) => r.code === code);
      return row ? labelOf(row) : code;
    },
    [sorted, labelOf],
  );

  return { isLoading: query.isLoading, isError: query.isError, options, nameOf };
}
