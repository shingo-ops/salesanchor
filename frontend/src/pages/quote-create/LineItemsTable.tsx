/**
 * 請求書・見積の商品行の表（invoice-create-portfolio design-v2 §3-3・§3-8）。
 *
 * 列: #・カテゴリ・商品・状態・数量・重さ・単価・小計・×。初期 12 行・最大 20 行。
 * 表は DataTable（ADR-144 の金型）。欄は Select・AsyncCombobox・TextField の金型だけを使う（生の select・input は使わない）。
 * 値段・在庫数・重さは在庫の道（useDraftInventory）の値だけ。行の計算は lineItems.ts の純粋な関数。
 */
import { useTranslation } from "react-i18next";
import { AsyncCombobox } from "../../components/AsyncCombobox";
import { Badge } from "../../components/Badge";
import type { AsyncComboboxOption } from "../../components/AsyncCombobox";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { Select } from "../../components/Select";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import { formatMoney } from "../../lib/invoiceDraftContext";
import {
  MAX_ROWS,
  applyProduct,
  applyQuantity,
  applyState,
  applyUnitPrice,
  categoryOf,
  changeCategory,
  emptyRow,
  rowStatus,
  rowSubtotal,
  statesFor,
} from "./lineItems";
import type { LineItem } from "./quoteDraft";
import type { DraftInventoryItem, DraftInventoryState } from "./useDraftInventory";
import { productMatches } from "./useDraftInventory";

/** 候補の数の上限（一覧が長くなりすぎないように） */
const PRODUCT_OPTION_LIMIT = 50;

export interface LineItemsTableProps {
  rows: LineItem[];
  onChange: (rows: LineItem[]) => void;
  inventory: DraftInventoryState;
  /** 単価の通貨（空なら小計を出さない） */
  currency: string;
  /** 円 → 通貨の為替（1 通貨あたりの円）。無ければ null */
  rate: number | null;
  /** 発行を押したあと、止めた行の欄に印を付ける */
  showErrors: boolean;
  disabled?: boolean;
}

interface RowView {
  index: number;
  row: LineItem;
}

export function LineItemsTable({ rows, onChange, inventory, currency, rate, showErrors, disabled = false }: LineItemsTableProps) {
  const { t } = useTranslation();
  const { items, categories } = inventory;
  const byId = new Map<number, DraftInventoryItem>(items.map((i) => [i.product_id, i]));

  const setRow = (index: number, next: LineItem) => onChange(rows.map((r, i) => (i === index ? next : r)));
  const removeRow = (index: number) => onChange(rows.filter((_, i) => i !== index));
  const addRow = () => {
    if (rows.length < MAX_ROWS) onChange([...rows, emptyRow()]);
  };

  const categoryOptions = categories.map((c) => ({ value: c.code, label: c.name_ja ?? c.code }));

  const productOptions = (category: string, query: string): Promise<AsyncComboboxOption[]> =>
    Promise.resolve(
      items
        .filter((i) => (category === "" || i.work_code === category) && statesFor(i).length > 0 && productMatches(i, query))
        .slice(0, PRODUCT_OPTION_LIMIT)
        .map((i) => ({ value: String(i.product_id), label: i.mark ? `${i.name} (${i.mark})` : i.name })),
    );

  const columns: DataTableColumn<RowView>[] = [
    { key: "no", header: t("lineItems.colNo"), width: "40px", align: "right", renderCell: (v) => v.index + 1 },
    {
      key: "category",
      header: t("lineItems.colCategory"),
      renderCell: (v) => (
        <Select
          size="sm"
          options={categoryOptions}
          placeholder={t("lineItems.categoryPlaceholder")}
          value={categoryOf(v.row, items)}
          disabled={disabled}
          aria-label={t("lineItems.categoryAria", { n: v.index + 1 })}
          data-testid={`invoice-item-category-${v.index}`}
          onChange={(e) => setRow(v.index, changeCategory(v.row, e.target.value))}
        />
      ),
    },
    {
      key: "product",
      header: t("lineItems.colProduct"),
      renderCell: (v) => (
        <div data-testid={`invoice-item-product-${v.index}`}>
          <AsyncCombobox
            id={`invoice-item-product-input-${v.index}`}
            ariaLabel={t("lineItems.productAria", { n: v.index + 1 })}
            value={v.row.product_name}
            placeholder={t("lineItems.productPlaceholder")}
            disabled={disabled || inventory.loading}
            minChars={0}
            loadOptions={(q) => productOptions(categoryOf(v.row, items), q)}
            onSelect={(opt) => {
              const item = byId.get(Number(opt.value));
              if (item) setRow(v.index, applyProduct(v.row, item));
            }}
            noResultsText={t("lineItems.productNoResults")}
            loadingText={t("lineItems.productLoading")}
          />
        </div>
      ),
    },
    {
      key: "state",
      header: t("lineItems.colState"),
      renderCell: (v) => {
        const item = v.row.product_id === null ? undefined : byId.get(v.row.product_id);
        const status = rowStatus(v.row);
        return (
          <Select
            size="sm"
            options={statesFor(item).map((s) => ({ value: s, label: s }))}
            placeholder={t("lineItems.statePlaceholder")}
            value={v.row.condition ?? ""}
            disabled={disabled || item === undefined}
            error={showErrors && status === "needsState" ? t("lineItems.stateMissing") : undefined}
            aria-label={t("lineItems.stateAria", { n: v.index + 1 })}
            data-testid={`invoice-item-state-${v.index}`}
            onChange={(e) => {
              if (item) setRow(v.index, applyState(v.row, item, e.target.value, currency, rate));
            }}
          />
        );
      },
    },
    {
      key: "quantity",
      header: t("lineItems.colQuantity"),
      width: "96px",
      renderCell: (v) => {
        const atLimit = v.row.stock_limit !== null && v.row.stock_limit !== undefined && v.row.quantity >= v.row.stock_limit;
        return (
          <TextField
            size="sm"
            type="number"
            min={0}
            step={1}
            value={rowStatus(v.row) === "empty" && v.row.quantity === 0 ? "" : v.row.quantity}
            disabled={disabled || v.row.product_id === null}
            helperText={atLimit ? t("lineItems.stockLimit", { count: v.row.stock_limit ?? 0 }) : undefined}
            aria-label={t("lineItems.quantityAria", { n: v.index + 1 })}
            data-testid={`invoice-item-quantity-${v.index}`}
            onChange={(e) => setRow(v.index, applyQuantity(v.row, e.target.value))}
          />
        );
      },
    },
    {
      key: "weight",
      header: t("lineItems.colWeight"),
      width: "96px",
      align: "right",
      renderCell: (v) => {
        const status = rowStatus(v.row);
        if (status === "weightMissing") {
          return (
            <Stack direction="column" gap="1">
              <span data-testid={`invoice-item-weight-${v.index}`}>
                <Badge variant="warning" appearance="soft" size="sm">
                  {t("common.unregistered")}
                </Badge>
              </span>
              {showErrors && (
                <span role="alert" data-testid={`invoice-item-weight-missing-${v.index}`}>
                  {t("lineItems.weightMissing")}
                </span>
              )}
            </Stack>
          );
        }
        return (
          <span data-testid={`invoice-item-weight-${v.index}`}>
            {v.row.weight === null || v.row.weight === undefined ? "" : t("lineItems.weightKg", { value: v.row.weight })}
          </span>
        );
      },
    },
    {
      key: "unitPrice",
      header: t("lineItems.colUnitPrice"),
      width: "128px",
      renderCell: (v) => {
        const status = rowStatus(v.row);
        return (
          <TextField
            size="sm"
            type="number"
            min={0}
            step={0.01}
            value={status === "empty" ? "" : v.row.unit_price}
            disabled={disabled || v.row.product_id === null}
            error={showErrors && status === "invalid" && !(v.row.unit_price > 0) ? t("lineItems.priceMissing") : undefined}
            aria-label={t("lineItems.priceAria", { n: v.index + 1 })}
            data-testid={`invoice-item-price-${v.index}`}
            onChange={(e) => setRow(v.index, applyUnitPrice(v.row, e.target.value))}
          />
        );
      },
    },
    {
      key: "subtotal",
      header: t("lineItems.colSubtotal"),
      width: "120px",
      align: "right",
      renderCell: (v) => (
        <span data-testid={`invoice-item-subtotal-${v.index}`}>
          {rowStatus(v.row) === "empty" || currency === "" ? "" : formatMoney(rowSubtotal(v.row), currency) ?? ""}
        </span>
      ),
    },
    {
      key: "remove",
      header: t("lineItems.colRemove"),
      width: "48px",
      align: "center",
      renderCell: (v) => (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-label={t("lineItems.removeRow", { n: v.index + 1 })}
          data-testid={`invoice-item-remove-${v.index}`}
          disabled={disabled || rows.length <= 1}
          onClick={() => removeRow(v.index)}
        >
          {t("lineItems.removeRowMark")}
        </Button>
      ),
    },
  ];

  return (
    <Stack direction="column" gap="3">
      {inventory.error !== "" && (
        <Callout variant="warning" title={t("lineItems.inventoryError")}>
          <span data-testid="invoice-inventory-error">{inventory.error}</span>
        </Callout>
      )}
      <DataTable<RowView>
        columns={columns}
        data={rows.map((row, index) => ({ index, row }))}
        rowKey={(v) => String(v.index)}
        rowTestId={(v) => `invoice-item-row-${v.index}`}
        density="compact"
      />
      <Stack direction="row" gap="3">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          data-testid="invoice-add-row"
          disabled={disabled || rows.length >= MAX_ROWS}
          onClick={addRow}
        >
          {t("lineItems.addRow")}
        </Button>
        {rows.length >= MAX_ROWS && (
          <span role="status" data-testid="invoice-max-rows">
            {t("lineItems.maxRows", { count: MAX_ROWS })}
          </span>
        )}
      </Stack>
    </Stack>
  );
}
