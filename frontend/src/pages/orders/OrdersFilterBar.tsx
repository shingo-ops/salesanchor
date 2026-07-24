/**
 * 受注管理 — 検索 / ソートコントロール。
 * ステータスフィルタは OrdersPage の左サブナビに移動済み。
 */

import { useTranslation } from "react-i18next";

interface Props {
  searchInput: string;
  setSearchInput: (v: string) => void;
  sortBy: string;
  setSortBy: (v: string) => void;
  sortOrder: "asc" | "desc";
  toggleSortOrder: () => void;
  STATUS_LABELS: Record<string, string>;
  SORT_OPTIONS: { value: string; label: string }[];
}

export function OrdersFilterBar({
  searchInput, setSearchInput,
  sortBy, setSortBy,
  sortOrder, toggleSortOrder,
  SORT_OPTIONS,
}: Props) {
  const { t } = useTranslation();

  return (
      <div
        style={{ display: "flex", gap: "var(--space-2)", flexWrap: "nowrap", alignItems: "center" }}
      >
      <input
        type="search"
        className="field-h-md field-w-md"
        aria-label={t("orders.title")}
        placeholder={t("common.search")}
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        data-testid="orders-search-input"
      />
      <select
        className="field-h-md field-w-sm"
        value={sortBy}
        onChange={(e) => setSortBy(e.target.value)}
        aria-label={t("common.filter")}
        data-testid="orders-sort-by"
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <button
        type="button"
        className="field-h-md"
        onClick={toggleSortOrder}
        aria-label={sortOrder === "desc" ? "↓" : "↑"}
        data-testid="orders-sort-order"
      >
        {sortOrder === "desc" ? "↓" : "↑"}
      </button>
    </div>
  );
}
