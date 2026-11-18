# card-R5: 請求書の作成画面を見本どおりに作り直す（invoice-create-portfolio 便 R5）

作成: Opus（Planner）2026-11-19。設計: docs/handoff/invoice-create-portfolio/design-v2.md 第8版 §3-1〜§3-3・§3-5・§3-6・§3-8・§4 R5・K1〜K5・K9〜K14・K19〜K21・K23（設計審査 5回目 APPROVE。第7版・第8版の足し分はこのカードと一緒に審査する）。
実装承認: PO は 2026-11-17 に p1〜p8 を「見本どおり」と決め、2026-11-18「1」で単価の為替の直し方と、在庫表に出ない21商品を別テーマにすることを決め、PR マージ・デプロイまでの完走を委ねた（ccopusgo の委任の範囲）。
枝: release/invoice-portfolio-r5-page（origin/main から）。移行（migrations/）なし・deploy.yml なし・scripts/ なし・backend なし。
基準: origin/main d7973da781653c3e75704f6f2268010a27267922（置き換える9ファイルの指紋は P1 で照合する）。
# rules-ack: d5738ef7
改訂: 2026-11-19 第2版。1回目の実行（K10 だけ失敗・87本中86本成功）を受け、K10 の試験が数える範囲を商品の候補一覧（role=listbox。AsyncCombobox が body へ描く1つだけの一覧）に絞った。ほかの行は第1版のまま。
改訂: 2026-11-19 第3版。2回目の実行（試験87本すべて成功）で、記録の前の自動点検（eslint --max-warnings=0）が試験2本の日本語の文字25件の警告で止めた。2-3 と 2-7 の先頭に、既存の試験と同じ形の除外の1行（理由と前例つき）を足した。手順5 の eslint を同じ条件にし、自動点検の残り1つ（check-css-var-fallbacks）も手順5 で流す。§4 の「警告なら続ける」を消した。

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-portfolio-R5 HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 画面は4枚のカード（SectionCard）を上から「発送先 → 支払いと合計 → 商品一覧 → 操作」（design-v2 §3-1・K1）。金型は便 R4 で足した SectionCard・ReadOnlyField・ThreeColumn・TotalsBox と既存の DataTable・Select・AsyncCombobox・Button・ConfirmModal・Callout・Stack だけを使う（ADR-144。生の select・input・色の直値を書かない）。
- D2 「在庫表から／見積から」の切り替えと見積を読み込む道は消す（p8）。在庫表の画面から持ってきた商品（QuoteHandoffState）は先頭の行から入る。
- D3 発送先は会社の画面で登録した住所を 12 欄で読んで見せるだけ（GET /invoices/draft-context。サーバーの DraftContextAddress は backend/app/schemas/invoice.py:115-132 で recipient_name・email・tax_id・address_line_1〜3・country_name を既に返す）。画面の型 DraftAddress にその7つを足す（§2 の invoiceDraftContext.ts の Edit）。
- D4 商品の行は初め12行・最大20行（見本どおり）。値段・在庫数・重さは GET /invoices/draft-inventory（便 R1）の値だけ。単価の初期値は floor(円÷為替×100)/100、円はそのまま、為替が無ければ 0 で作成を止める（手で直せる）。通貨を選び直したら手で直していない行（price_edited=false）だけ入れ直す（PO 2026-11-18「1」）。
- D5 送料は総重量が変わったら 800ms 待って POST /invoices/draft-shipping-quotes（便 R2）を1回呼び、便ごとに「ライブ」「静的」の印をつけて並べる。合計・税・関税はサーバーの試算（POST /invoices/preview）の答えを TotalsBox で見せ、画面で足し算しない。
- D6 操作のカードは「キャンセル」（今の画面にある。一覧へ戻る）・「クリア」（確認を出してから空に戻す・K19）・「請求書を作成」（今の文言 invoices.createBtn のまま。名前を「請求書を発行」に変えるかは便 R6 の前に PO に聞く）。作成は今の道（POST /invoices・下書きで保存）。
- D7 LineItemsTable・lineItems・useDraftInventory・useDraftShippingQuotes は frontend/src/pages/quote-create/ に置く（便 R7 で見積の画面も同じ部品を使う。§4 R7）。FedExRateModal と useInvoicePreview.ts は変えない（見積の画面が FedExRateModal を使う）。
- D8 LineItem（quoteDraft.ts）に画面だけの4項目（category_code・stock_limit・price_yen・price_edited）を任意で足す。保存に送る形（toInvoiceItem）には入れない。
- D9 文言は ja.json・en.json の invoiceForm に 30 キー、新しい節 lineItems に 29 キーを足す（両方同じキー。ADR-027）。今ある invoiceForm のキーは消さない。
- D10 画面の作りが変わるので、今の画面を前提にした試験5本（AllLegacyButtonDynamicMigration・BillToCountryGuidance・CommerceNavigationButtonMigration・CommerceSubmitButtonMigration・batch3cPages）を新しい画面に合わせて書き換える（切り替えの試験と見積の読み込みの試験は消す。キャンセル・作成を止める・空の行の欄の試験は残す）。
- D11 frontend/tsconfig.json の noUnusedLocals は false（使わなくなった import が残っても型の検査は通る）。

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。新しいファイルと丸ごと置き換えるファイルは Write ツール（置き換えは先に Read）。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順8） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-2. 実装前点検（手順2 で流す。外れたら実装せず停止して BLOCKED: で報告）

- P1 置き換える9ファイルの指紋（git hash-object）が次と同じ（この順）:
  - `fce512e81e87e52abc930a3f4d9d33e20b50609f` frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
  - `c9f2d602bb4f7f786de8c3d256aa1ce65a102b85` frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx
  - `77c07e201e91d5e304696075ed9e67c7e0ceb586` frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx
  - `1406be5290b0cdee2e25ef56ccb9a39895d15ef6` frontend/src/pages/invoice-create/InvoiceShipToSection.tsx
  - `f8c799ec1e5dda810c2fe704d6fcf05e107f8a20` frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx
  - `ca9d1757f97351c1179382df3bec470c949d4302` frontend/src/components/BillToCountryGuidance.test.tsx
  - `de411e03fd5c209e5d83a3ff3eed6ca13da7ba26` frontend/src/components/CommerceNavigationButtonMigration.test.tsx
  - `05762db4f09129af7b8371003767d374bb83f334` frontend/src/components/CommerceSubmitButtonMigration.test.tsx
  - `7ca6bdd1f23d5eb9d5454b0a06d1ee84b8648534` frontend/src/lib/query/batch3cPages.test.tsx
- P2 frontend/src/pages/quote-create/ に LineItemsTable・lineItems・useDraftInventory・useDraftShippingQuotes で始まるファイルが 0。
- P3 `  zero_stock_warning?: boolean;` が frontend/src/pages/quote-create/quoteDraft.ts に 1。
- P4 `  phone: string | null;` が frontend/src/lib/invoiceDraftContext.ts に 1。
- P5 `"lineItems"` が ja.json・en.json の一番上の節に無い（python の出力 `False False`）。
- P6 SectionCard.tsx・ReadOnlyField.tsx・ThreeColumn.tsx・TotalsBox.tsx が frontend/src/components/ にある（便 R4。4）。

## 1. 触るファイル

- frontend/src/pages/quote-create/LineItemsTable.tsx（新規）
- frontend/src/pages/quote-create/lineItems.ts（新規）
- frontend/src/pages/quote-create/lineItems.test.ts（新規）
- frontend/src/pages/quote-create/useDraftInventory.ts（新規）
- frontend/src/pages/quote-create/useDraftShippingQuotes.ts（新規）
- frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（丸ごと置き換え）
- frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx（丸ごと置き換え）
- frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx（丸ごと置き換え）
- frontend/src/pages/invoice-create/InvoiceShipToSection.tsx（丸ごと置き換え）
- frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx（丸ごと置き換え）
- frontend/src/components/BillToCountryGuidance.test.tsx（丸ごと置き換え）
- frontend/src/components/CommerceNavigationButtonMigration.test.tsx（丸ごと置き換え）
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx（丸ごと置き換え）
- frontend/src/lib/query/batch3cPages.test.tsx（丸ごと置き換え）
- frontend/src/pages/quote-create/quoteDraft.ts（Edit・1か所）
- frontend/src/lib/invoiceDraftContext.ts（Edit・1か所）
- frontend/src/locales/ja.json・frontend/src/locales/en.json（Edit・1か所ずつ）

## 2. 変更

新規ファイルは Write ツールで下の中身をそのまま書く。丸ごと置き換えるファイルは、先に Read ツールで開いてから Write ツールで下の中身をそのまま書く（字下げは囲みのとおり）。既存ファイルの一部は Edit ツール。

### 2-1. frontend/src/pages/quote-create/LineItemsTable.tsx（新規）

```tsx
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
```

### 2-2. frontend/src/pages/quote-create/lineItems.ts（新規）

```ts
/**
 * 請求書・見積の商品行の純粋な関数（invoice-create-portfolio design-v2 §3-3・§3-8）。
 *
 * - 値段・在庫数・重さはサーバーの在庫の道（useDraftInventory）の値だけを使う。ここに値を直書きしない。
 * - 単価の初期値は「在庫表の円の値段 ÷ 為替」を小数 2 けたで切り捨て（PO 2026-11-18「1」）。円の請求書は直さない。
 *   為替が無い通貨は 0 にして作成を止める（手で直せる）。通貨を選び直したら、手で直していない行だけ入れ直す。
 * - 文言は文言キーで返し、t() は部品が呼ぶ（React も i18n も読まない）。
 */
import { isCreatableItem } from "../../lib/invoiceDraftContext";
import type { LineItem, QuoteHandoffState } from "./quoteDraft";
import { blankItem } from "./quoteDraft";
import type { DraftInventoryItem } from "./useDraftInventory";

/** 初期の行数と最大の行数（見本どおり。§3-3） */
export const INIT_ROWS = 12;
export const MAX_ROWS = 20;

/** 状態の並び順（在庫表の列と同じ）。これ以外の状態は後ろに名前順 */
export const STATE_ORDER: readonly string[] = ["Case", "Sealed box", "No shrink box", "Damaged sealed box"];

/** 空の行（商品が選ばれていない行。数量 0 は「空」の印で、保存には送らない） */
export function emptyRow(): LineItem {
  return {
    ...blankItem,
    quantity: 0,
    category_code: null,
    stock_limit: null,
    price_yen: null,
    price_edited: false,
    zero_stock_warning: false,
  };
}

/** 行を INIT_ROWS まで空の行で足す（それより多ければそのまま。消さない） */
export function padRows(rows: LineItem[]): LineItem[] {
  const out = [...rows];
  while (out.length < INIT_ROWS) out.push(emptyRow());
  return out;
}

/** 在庫表の画面から持ってきた商品を先頭の行から入れる（§3-1）。カテゴリ・状態は在庫の答えから画面が引く */
export function handoffRows(handoff: QuoteHandoffState): LineItem[] {
  const picked = (handoff?.selectedProducts ?? []).map((p) => ({
    ...emptyRow(),
    product_id: p.product_id,
    product_name: p.product_name,
    inventory_id: p.inventory_id ?? null,
    quantity: 1,
  }));
  return padRows(picked);
}

/** 円 → 請求書の通貨。円はそのまま。為替が無い・0 以下は 0。ほかは小数 2 けたで切り捨て */
export function yenToCurrency(yen: number | null | undefined, currency: string, rate: number | null | undefined): number {
  if (yen === null || yen === undefined || !Number.isFinite(yen)) return 0;
  if (currency === "JPY") return yen;
  if (rate === null || rate === undefined || !(rate > 0)) return 0;
  return Math.floor((yen * 100) / rate + 1e-9) / 100;
}

/** 状態の名前 → 保存する unit（§3-3）。"Case"→case・box を含む→box・pack を含む→pack・ほかは null */
export function unitFromState(state: string): string | null {
  if (state === "Case") return "case";
  const s = state.toLowerCase();
  if (s.includes("box")) return "box";
  if (s.includes("pack")) return "pack";
  return null;
}

/** 状態に合う 1 個の重さ。"Case" はケースの重さ、ほかは BOX の重さ。無ければ null */
export function weightForState(item: DraftInventoryItem, state: string): number | null {
  const w = state === "Case" ? item.case_weight_kg : item.box_weight_kg;
  return w === null || w === undefined ? null : w;
}

/** 在庫のある状態だけ（数が 0 の状態は除く。数が分からない null は残す）を、在庫表の列の順で */
export function statesFor(item: DraftInventoryItem | undefined): string[] {
  if (!item) return [];
  const keys = Object.keys(item.cells).filter((k) => {
    const q = item.cells[k]?.quantity;
    return q === null || q === undefined || q > 0;
  });
  const known = STATE_ORDER.filter((s) => keys.includes(s));
  const others = keys.filter((k) => !STATE_ORDER.includes(k)).sort();
  return [...known, ...others];
}

/** 在庫の上限を超えたら上限に戻す */
export function clampQuantity(quantity: number, limit: number | null | undefined): number {
  return limit !== null && limit !== undefined && quantity > limit ? limit : quantity;
}

/** 行のカテゴリ。行に無ければ商品の作品の符号（在庫表から持ってきた行） */
export function categoryOf(row: LineItem, items: DraftInventoryItem[]): string {
  if (row.category_code) return row.category_code;
  if (row.product_id === null) return "";
  return items.find((i) => i.product_id === row.product_id)?.work_code ?? "";
}

/** カテゴリを選び直す。変われば、その行の商品・状態・数量を空にする（§3-3） */
export function changeCategory(row: LineItem, code: string): LineItem {
  if ((row.category_code ?? "") === code) return row;
  return { ...emptyRow(), category_code: code === "" ? null : code };
}

/** 商品を選ぶ。状態・重さ・単価・在庫上限は空に戻す（状態を選んだときに入る） */
export function applyProduct(row: LineItem, item: DraftInventoryItem): LineItem {
  return {
    ...emptyRow(),
    category_code: item.work_code ?? row.category_code ?? null,
    product_id: item.product_id,
    product_name: item.name,
    name_en: item.name_en,
    box_weight_kg: item.box_weight_kg,
    case_weight_kg: item.case_weight_kg,
    quantity: row.quantity,
  };
}

/** 状態を選ぶ。重さ・単価・在庫上限が入り、数量が空なら 1、上限を超えれば上限（§3-3・K11・K12） */
export function applyState(
  row: LineItem,
  item: DraftInventoryItem,
  state: string,
  currency: string,
  rate: number | null,
): LineItem {
  if (state === "") {
    return { ...row, condition: null, unit: null, weight: null, unit_price: 0, price_yen: null, price_edited: false, stock_limit: null };
  }
  const cell = item.cells[state];
  const priceYen = cell?.price ?? null;
  const limit = cell?.quantity ?? null;
  const quantity = row.quantity >= 1 ? row.quantity : 1;
  return {
    ...row,
    // 在庫表の画面から持ってきた行は英語名を持たないため、在庫の道の値で入れる
    name_en: item.name_en,
    condition: state,
    unit: unitFromState(state),
    weight: weightForState(item, state),
    box_weight_kg: item.box_weight_kg,
    case_weight_kg: item.case_weight_kg,
    price_yen: priceYen,
    price_edited: false,
    unit_price: yenToCurrency(priceYen, currency, rate),
    stock_limit: limit,
    quantity: clampQuantity(quantity, limit),
  };
}

/** 数量を打つ。整数でない・0 未満は 0、上限を超えたら上限 */
export function applyQuantity(row: LineItem, text: string): LineItem {
  const n = Number(text);
  const q = text.trim() === "" || !Number.isFinite(n) || n < 0 ? 0 : Math.floor(n);
  return { ...row, quantity: clampQuantity(q, row.stock_limit) };
}

/** 単価を打つ。手で直した印を付ける（通貨を選び直しても入れ直さない） */
export function applyUnitPrice(row: LineItem, text: string): LineItem {
  const n = Number(text);
  return { ...row, unit_price: text.trim() === "" || !Number.isFinite(n) ? 0 : n, price_edited: true };
}

/** 通貨を選び直したとき、手で直していない行だけ単価を入れ直す（PO 2026-11-18「1」） */
export function reconvertPrices(rows: LineItem[], currency: string, rate: number | null): LineItem[] {
  return rows.map((r) =>
    r.price_edited || r.price_yen === null || r.price_yen === undefined
      ? r
      : { ...r, unit_price: yenToCurrency(r.price_yen, currency, rate) },
  );
}

export type RowStatus = "empty" | "needsState" | "weightMissing" | "invalid" | "ready";

/** 行の状態。空の行は送らない。状態が無い・重さが無い・数や単価が正しくない行があれば作成を止める（§3-3・K20・K21） */
export function rowStatus(row: LineItem): RowStatus {
  if (row.product_id === null && row.product_name.trim() === "") return "empty";
  if (!row.condition) return "needsState";
  if (row.weight === null || row.weight === undefined) return "weightMissing";
  return isCreatableItem(row) ? "ready" : "invalid";
}

/** 商品の入った行だけ */
export function filledRows(rows: LineItem[]): LineItem[] {
  return rows.filter((r) => rowStatus(r) !== "empty");
}

/** 作れるか: 商品の入った行が 1 つ以上で、その全部が ready */
export function allRowsReady(rows: LineItem[]): boolean {
  const filled = filledRows(rows);
  return filled.length > 0 && filled.every((r) => rowStatus(r) === "ready");
}

/** 総重量（重さ×数量の和・小数 3 けた）。重さの無い行は数えない */
export function totalWeight(rows: LineItem[]): number {
  const sum = filledRows(rows).reduce((acc, r) => (r.weight === null || r.weight === undefined ? acc : acc + r.weight * r.quantity), 0);
  return Math.round(sum * 1000) / 1000;
}

/** 小計（画面の表示だけ。合計はサーバーの試算） */
export function rowSubtotal(row: LineItem): number {
  return Math.round(row.quantity * row.unit_price * 100) / 100;
}

/** 保存に送る形（今の InvoiceItemInput。画面だけの項目は送らない） */
export function toInvoiceItem(row: LineItem) {
  return {
    product_id: row.product_id,
    product_name: row.product_name,
    name_en: row.name_en ?? null,
    condition: row.condition ?? null,
    unit: row.unit ?? null,
    quantity: row.quantity,
    unit_price: row.unit_price,
    weight: row.weight,
  };
}
```

### 2-3. frontend/src/pages/quote-create/lineItems.test.ts（新規）

```ts
/* eslint-disable local/no-japanese-literal -- テスト: 試験の名前と試験の商品名を日本語で書く（ADR-027・precedent: DataTable.test.tsx） */
import { describe, expect, it } from "vitest";
import {
  INIT_ROWS,
  allRowsReady,
  applyProduct,
  applyQuantity,
  applyState,
  applyUnitPrice,
  categoryOf,
  changeCategory,
  clampQuantity,
  emptyRow,
  filledRows,
  handoffRows,
  padRows,
  reconvertPrices,
  rowStatus,
  statesFor,
  toInvoiceItem,
  totalWeight,
  unitFromState,
  yenToCurrency,
} from "./lineItems";
import type { DraftInventoryItem } from "./useDraftInventory";

const ITEM: DraftInventoryItem = {
  product_id: 7,
  name: "テスト商品",
  name_en: "Test Product",
  mark: "OP-01",
  work_code: "OP",
  box_weight_kg: 0.5,
  case_weight_kg: 6,
  cells: {
    "Sealed box": { price: 15000, quantity: 3 },
    Case: { price: 170000, quantity: 1 },
    "No shrink box": { price: 9000, quantity: 0 },
  },
};

describe("yenToCurrency", () => {
  it("円はそのまま", () => expect(yenToCurrency(15000, "JPY", null)).toBe(15000));
  it("為替で割って小数2けたで切り捨て", () => expect(yenToCurrency(1000, "USD", 151.37)).toBe(6.6));
  it("割り切れる値は誤差で下がらない", () => expect(yenToCurrency(15000, "USD", 150)).toBe(100));
  it("為替が無ければ 0", () => expect(yenToCurrency(15000, "USD", null)).toBe(0));
  it("値段が無ければ 0", () => expect(yenToCurrency(null, "USD", 150)).toBe(0));
});

describe("状態と重さ", () => {
  it("unit の決め方", () => {
    expect(unitFromState("Case")).toBe("case");
    expect(unitFromState("Sealed box")).toBe("box");
    expect(unitFromState("Booster pack")).toBe("pack");
    expect(unitFromState("Other")).toBeNull();
  });
  it("在庫 0 の状態を除き、在庫表の列の順で並べる", () => {
    expect(statesFor(ITEM)).toEqual(["Case", "Sealed box"]);
    expect(statesFor(undefined)).toEqual([]);
  });
  it("上限を超えたら上限に戻す", () => {
    expect(clampQuantity(5, 3)).toBe(3);
    expect(clampQuantity(2, 3)).toBe(2);
    expect(clampQuantity(9, null)).toBe(9);
  });
});

describe("行の操作", () => {
  it("初期は12行の空の行", () => {
    const rows = padRows([]);
    expect(rows).toHaveLength(INIT_ROWS);
    expect(rows.every((r) => rowStatus(r) === "empty")).toBe(true);
  });

  it("持ってきた商品は先頭の行から入る", () => {
    const rows = handoffRows({ selectedProducts: [{ product_id: 7, product_name: "テスト商品", unit_price: 15000 }] });
    expect(rows).toHaveLength(INIT_ROWS);
    expect(rows[0].product_id).toBe(7);
    expect(rows[0].quantity).toBe(1);
    expect(rows[0].unit_price).toBe(0);
    expect(categoryOf(rows[0], [ITEM])).toBe("OP");
    expect(rowStatus(rows[1])).toBe("empty");
  });

  it("カテゴリを選び直すと商品・状態・数量が空になる", () => {
    const row = applyState(applyProduct({ ...emptyRow(), category_code: "OP" }, ITEM), ITEM, "Sealed box", "JPY", null);
    const next = changeCategory(row, "PK");
    expect(next.product_id).toBeNull();
    expect(next.condition).toBeNull();
    expect(next.quantity).toBe(0);
    expect(next.category_code).toBe("PK");
    expect(changeCategory(row, "OP")).toBe(row);
  });

  it("状態を選ぶと重さ・単価・上限が入り、数量は1", () => {
    const row = applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "USD", 150);
    expect(row.weight).toBe(0.5);
    expect(row.unit).toBe("box");
    expect(row.unit_price).toBe(100);
    expect(row.price_yen).toBe(15000);
    expect(row.stock_limit).toBe(3);
    expect(row.quantity).toBe(1);
    expect(rowStatus(row)).toBe("ready");
  });

  it("Case はケースの重さ", () => {
    expect(applyState(applyProduct(emptyRow(), ITEM), ITEM, "Case", "JPY", null).weight).toBe(6);
  });

  it("数量は在庫数に戻る", () => {
    const row = applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "JPY", null);
    expect(applyQuantity(row, "9").quantity).toBe(3);
    expect(applyQuantity(row, "").quantity).toBe(0);
  });

  it("通貨を選び直すと、手で直していない行だけ入れ直す", () => {
    const auto = applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "USD", 150);
    const edited = applyUnitPrice(auto, "80");
    const [a, e] = reconvertPrices([auto, edited], "USD", 100);
    expect(a.unit_price).toBe(150);
    expect(e.unit_price).toBe(80);
    expect(e.price_edited).toBe(true);
  });

  it("状態が無い行・重さが無い行は作れない", () => {
    const noState = applyProduct(emptyRow(), ITEM);
    expect(rowStatus(noState)).toBe("needsState");
    const noWeight = applyState(applyProduct(emptyRow(), { ...ITEM, box_weight_kg: null }), { ...ITEM, box_weight_kg: null }, "Sealed box", "JPY", null);
    expect(rowStatus(noWeight)).toBe("weightMissing");
    expect(allRowsReady([noState, emptyRow()])).toBe(false);
  });

  it("為替が無い通貨の行は単価 0 で作れない", () => {
    const row = applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "EUR", null);
    expect(row.unit_price).toBe(0);
    expect(rowStatus(row)).toBe("invalid");
  });

  it("総重量と送る形", () => {
    const row = applyQuantity(applyState(applyProduct(emptyRow(), ITEM), ITEM, "Sealed box", "JPY", null), "2");
    const rows = [row, emptyRow()];
    expect(filledRows(rows)).toHaveLength(1);
    expect(totalWeight(rows)).toBe(1);
    expect(allRowsReady(rows)).toBe(true);
    expect(toInvoiceItem(row)).toEqual({
      product_id: 7,
      product_name: "テスト商品",
      name_en: "Test Product",
      condition: "Sealed box",
      unit: "box",
      quantity: 2,
      unit_price: 15000,
      weight: 0.5,
    });
  });
});
```

### 2-4. frontend/src/pages/quote-create/useDraftInventory.ts（新規）

```ts
/**
 * 請求書・見積の商品行で使う在庫（GET /invoices/draft-inventory）を読む（invoice-create-portfolio design-v2 §3-3・§3-4）。
 *
 * 道は 1 回だけ呼ぶ（category で絞らない）。カテゴリでの絞り込みは画面で work_code を見て行う。
 * 値段・在庫数・重さの正本はサーバーのこの道だけ。画面で値段や重さを直書きしない。
 */
import { useApiQuery } from "../../lib/query/apiQuery";

export const DRAFT_INVENTORY_PATH = "/invoices/draft-inventory";

/** 状態ごとの値段（円）と在庫数。backend/app/schemas/inventory_aggregated.py の ConditionCell */
export interface DraftInventoryCell {
  price: number | null;
  quantity: number | null;
}

export interface DraftInventoryCategory {
  code: string;
  name_ja: string | null;
}

export interface DraftInventoryItem {
  product_id: number;
  name: string;
  name_en: string | null;
  mark: string | null;
  work_code: string | null;
  box_weight_kg: number | null;
  case_weight_kg: number | null;
  /** 状態の名前 → 値段と数。在庫の無い状態はキーごと無い */
  cells: Record<string, DraftInventoryCell>;
}

export interface DraftInventory {
  categories: DraftInventoryCategory[];
  items: DraftInventoryItem[];
}

export interface DraftInventoryState {
  categories: DraftInventoryCategory[];
  items: DraftInventoryItem[];
  loading: boolean;
  /** 読めなかったときの文（api が文言にしたもの）。読めたら "" */
  error: string;
}

function asDraftInventory(data: unknown): DraftInventory | null {
  if (data === null || typeof data !== "object" || Array.isArray(data)) return null;
  const d = data as Partial<DraftInventory>;
  return Array.isArray(d.items) && Array.isArray(d.categories) ? (d as DraftInventory) : null;
}

export function useDraftInventory(): DraftInventoryState {
  const q = useApiQuery<DraftInventory>(DRAFT_INVENTORY_PATH);
  const data = asDraftInventory(q.data);
  return {
    categories: data?.categories ?? [],
    items: data?.items ?? [],
    loading: q.isPending,
    error: q.error ? (q.error instanceof Error ? q.error.message : String(q.error)) : "",
  };
}

/** 商品の候補の絞り込み。商品名・英語名・型番のどれかに、大文字小文字を区別せず含まれれば当たり。空の検索語は全部 */
export function productMatches(item: DraftInventoryItem, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (q === "") return true;
  return [item.name, item.name_en, item.mark].some((s) => s !== null && s.toLowerCase().includes(q));
}
```

### 2-5. frontend/src/pages/quote-create/useDraftShippingQuotes.ts（新規）

```ts
/**
 * 請求書の送料の一覧（POST /invoices/draft-shipping-quotes）を取る（invoice-create-portfolio design-v2 §3-5・K6・K7）。
 *
 * - 会社と総重量が変わったときだけ、最後の変更から 800 ミリ秒待って 1 回呼ぶ。
 * - 同じ会社・同じ総重量の答えは覚えておき、もう呼ばない（K7）。
 * - 総重量が 0 以下・会社が無いときは呼ばない。
 * - 答えは「どの材料に対する答えか（key）」と組で持ち、材料が変わった瞬間に古い答えは使わない。
 * 届け先・発送元の国はサーバーが決める（画面からは送らない）。
 */
import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";

export const DRAFT_SHIPPING_QUOTES_PATH = "/invoices/draft-shipping-quotes";
export const SHIPPING_QUOTE_DELAY_MS = 800;

/** backend/app/schemas/shipping.py の ShippingCalcResult（使う項目だけ）。fee は Decimal なので文字で届くことがある */
export interface DraftShippingRate {
  carrier: string;
  zone: string;
  fee: string | number;
  currency: string;
  source: "static" | "fedex_live";
  service_type: string | null;
  service_name: string | null;
  transit_days: number | null;
}

export interface DraftShippingQuotes {
  results: DraftShippingRate[];
  live_error: string | null;
}

export interface DraftShippingQuotesState {
  /** いまの材料の答え。まだ届いていない・呼ばないときは null */
  quotes: DraftShippingQuotes | null;
  /** いまの材料で答えを待っているか */
  loading: boolean;
  /** いまの材料で失敗したときの文（api が文言にしたもの） */
  error: string;
  /** いまの材料の鍵。呼ばないときは "" */
  key: string;
}

interface QuoteAnswer {
  key: string;
  data: DraftShippingQuotes | null;
  error: string;
}

/** 総重量は小数 3 けたまで（サーバーの weight_kg の決まり） */
export function roundWeight(weightKg: number): number {
  return Math.round(weightKg * 1000) / 1000;
}

export function shippingQuoteKey(companyId: number | null, weightKg: number): string {
  const w = roundWeight(weightKg);
  return companyId === null || !(w > 0) ? "" : `${companyId}:${w.toFixed(3)}`;
}

export function useDraftShippingQuotes(companyId: number | null, weightKg: number): DraftShippingQuotesState {
  const key = shippingQuoteKey(companyId, weightKg);
  const cache = useRef(new Map<string, DraftShippingQuotes>());
  const seq = useRef(0);
  const [answer, setAnswer] = useState<QuoteAnswer>({ key: "", data: null, error: "" });

  useEffect(() => {
    if (key === "") return undefined;
    const mine = ++seq.current;
    const cached = cache.current.get(key);
    if (cached !== undefined) {
      setAnswer({ key, data: cached, error: "" });
      return undefined;
    }
    const [companyPart, weightPart] = key.split(":");
    const timer = setTimeout(() => {
      api
        .post<DraftShippingQuotes>(DRAFT_SHIPPING_QUOTES_PATH, { company_id: Number(companyPart), weight_kg: Number(weightPart) })
        .then((data) => {
          const safe: DraftShippingQuotes = {
            results: Array.isArray(data?.results) ? data.results : [],
            live_error: typeof data?.live_error === "string" ? data.live_error : null,
          };
          cache.current.set(key, safe);
          if (seq.current === mine) setAnswer({ key, data: safe, error: "" });
        })
        .catch((e: unknown) => {
          if (seq.current === mine) setAnswer({ key, data: null, error: e instanceof Error ? e.message : String(e) });
        });
    }, SHIPPING_QUOTE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [key]);

  const fresh = key !== "" && answer.key === key;
  return {
    quotes: fresh ? answer.data : null,
    loading: key !== "" && !fresh,
    error: fresh ? answer.error : "",
    key,
  };
}

/** 送料の行の額（小数 2 けたに丸めた数）。数でなければ null */
export function rateFee(rate: DraftShippingRate): number | null {
  const n = typeof rate.fee === "number" ? rate.fee : Number(rate.fee);
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : null;
}
```

### 2-6. frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（丸ごと置き換え）

```tsx
/**
 * 請求書作成ページ（invoice-create-portfolio design-v2 §3-1。見本の「見た目と操作」）。
 *
 * 4 枚のカードを上から: 発送先 → 支払いと合計 → 商品一覧 → 操作（K1）。
 *   - 発送先: 顧客を選ぶと、会社の画面で登録した住所を 12 欄で読んで見せるだけ（GET /invoices/draft-context）。
 *   - 支払いと合計: 通貨・支払方法・発送メモ／総重量と便ごとの送料（POST /invoices/draft-shipping-quotes）／合計枠。
 *     合計・税・関税はサーバーの試算（POST /invoices/preview）の答えを見せる。画面で足し算しない。
 *   - 商品一覧: LineItemsTable（値段・在庫数・重さは GET /invoices/draft-inventory の値だけ）。
 *   - 操作: 「クリア」（確認してから空に戻す）と作成。作成は今の道（POST /invoices。下書きで保存）。
 * 「在庫表から／見積から」の切り替えは無い（p8）。見積から作るのは見積の詳細画面の道。
 * 在庫表の画面から選んだ商品（QuoteHandoffState）は先頭の行から入る。
 */
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import CompanyContactSelector from "../../components/CompanyContactSelector";
import ConfirmModal from "../../components/ConfirmModal";
import { PageLayout } from "../../components/PageLayout";
import { SectionCard } from "../../components/SectionCard";
import { Stack } from "../../components/Stack";
import {
  currencyChoices,
  draftContextPath,
  effectivePaymentKey,
  fxRateFor,
  paymentChoicesFor,
  paymentRefFromKey,
  resolveCurrency,
  type DraftContext,
  type InvoicePreviewRequest,
  type ShippingChoice,
} from "../../lib/invoiceDraftContext";
import { LineItemsTable } from "../quote-create/LineItemsTable";
import { allRowsReady, filledRows, handoffRows, padRows, reconvertPrices, toInvoiceItem, totalWeight } from "../quote-create/lineItems";
import type { LineItem, QuoteHandoffState } from "../quote-create/quoteDraft";
import { useDraftInventory } from "../quote-create/useDraftInventory";
import { rateFee, useDraftShippingQuotes } from "../quote-create/useDraftShippingQuotes";
import { InvoicePaymentTotalsSection, SHIPPING_NONE, shippingRateKey } from "./InvoicePaymentTotalsSection";
import { InvoiceShipToSection } from "./InvoiceShipToSection";
import { useInvoicePreview } from "./useInvoicePreview";

/** 材料の答えが請求書の材料の形（object）のときだけ使う。配列などは「まだ無い」と同じに扱う */
function asDraftContext(data: unknown): DraftContext | null {
  return data !== null && typeof data === "object" && !Array.isArray(data) ? (data as DraftContext) : null;
}

export default function InvoiceCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const handoff = location.state as QuoteHandoffState;
  const draft = handoff?.draft;

  const [companyId, setCompanyId] = useState<number | null>(draft?.companyId ?? null);
  const [contactId, setContactId] = useState<number | null>(draft?.contactId ?? null);
  const [selectorError, setSelectorError] = useState("");
  // 人が選んだ通貨。使う通貨は材料の候補にあるときだけ（resolveCurrency）。
  const [currencyChoice, setCurrencyChoice] = useState<string>(draft?.currency ?? "");
  const [paymentChoice, setPaymentChoice] = useState("");
  // 送料の選択（"" 未選択／SHIPPING_NONE／便の鍵）。便は今の送料の一覧にあるときだけ有効。
  const [shippingPick, setShippingPick] = useState("");
  const [notes, setNotes] = useState(draft?.notes ?? "");
  const [rows, setRows] = useState<LineItem[]>(() => handoffRows(handoff));
  const [showErrors, setShowErrors] = useState(false);
  const [clearOpen, setClearOpen] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const inventory = useDraftInventory();

  // --- 請求書の材料（会社を選んだときだけ取りに行く） ---
  const ctxQ = useApiQuery<DraftContext>(
    companyId !== null ? draftContextPath(companyId, contactId) : "/invoices/draft-context",
    { enabled: companyId !== null },
  );
  const ctx = companyId !== null ? asDraftContext(ctxQ.data) : null;
  const ctxError = companyId !== null && ctxQ.error ? (ctxQ.error instanceof Error ? ctxQ.error.message : t("common.fetchError")) : "";

  const currency = resolveCurrency(ctx, currencyChoice);
  const fx = currency !== "" ? fxRateFor(ctx, currency) : null;
  const rate = fx !== null && fx.rate > 0 ? fx.rate : null;

  // 通貨（または為替）が変わったら、単価を手で直していない行だけ入れ直す（PO 2026-11-18「1」）。
  useEffect(() => {
    setRows((prev) => reconvertPrices(prev, currency, rate));
  }, [currency, rate]);

  const paymentChoices = paymentChoicesFor(ctx, currency);
  const paymentValue = effectivePaymentKey(paymentChoices, paymentChoice);

  const weight = totalWeight(rows);
  const canQuote = ctx !== null && ctx.origin_country_code !== null && ctx.destination_country_code !== null;
  const shippingQuotes = useDraftShippingQuotes(canQuote ? companyId : null, weight);
  const pickedRate = (shippingQuotes.quotes?.results ?? []).find((r) => shippingRateKey(r) === shippingPick);
  const pickedFee = pickedRate ? rateFee(pickedRate) : null;
  const shipping: ShippingChoice | null =
    shippingPick === SHIPPING_NONE
      ? { mode: "none" }
      : pickedRate && pickedFee !== null
        ? { mode: "calculate", carrier: pickedRate.carrier, service_type: pickedRate.service_type, fee: pickedFee, currency: pickedRate.currency }
        : null;

  const filled = filledRows(rows);
  const rowsReady = allRowsReady(rows);
  const previewRequest: InvoicePreviewRequest | null =
    ctx !== null && companyId !== null && currency !== "" && rowsReady
      ? {
          company_id: companyId,
          currency,
          items: filled.map((r) => ({ quantity: r.quantity, unit_price: r.unit_price })),
          shipping,
        }
      : null;
  const { preview, error: previewError, fresh } = useInvoicePreview(previewRequest);

  const canCreate =
    companyId !== null &&
    contactId !== null &&
    ctx !== null &&
    ctx.issuer_region !== null &&
    currency !== "" &&
    rowsReady &&
    shipping !== null &&
    (paymentChoices.length === 0 || paymentValue !== "") &&
    fresh &&
    preview !== null &&
    preview.uncomputed.length === 0 &&
    !saving;

  // 会社・担当者が変わったら、前の会社に合わせて選んだ送料と支払方法を外す。
  const changeCompanyContact = (nextCompanyId: number | null, nextContactId: number | null) => {
    if (nextCompanyId !== companyId || nextContactId !== contactId) {
      setShippingPick("");
      setPaymentChoice("");
    }
    setCompanyId(nextCompanyId);
    setContactId(nextContactId);
  };

  // 「クリア」の確認で「はい」: 12 行・発送先・送料・メモを空に戻す（§3-6・K19）。
  const clearAll = () => {
    changeCompanyContact(null, null);
    setShippingPick("");
    setSelectorError("");
    setCurrencyChoice("");
    setNotes("");
    setRows(padRows([]));
    setShowErrors(false);
    setError("");
    setClearOpen(false);
  };

  const submitInvoice = async () => {
    setError("");
    setSelectorError("");
    setShowErrors(true);
    if (contactId === null) {
      setSelectorError(t("companyContactSelector.contactRequired"));
      return;
    }
    if (!rowsReady) {
      setError(filled.length === 0 ? t("quotes.itemsRequired") : t("invoiceForm.rowsNotReady"));
      return;
    }
    if (!canCreate || shipping === null) {
      setError(t("invoiceForm.createNotReady"));
      return;
    }
    setSaving(true);
    try {
      const inv = await api.post<{ id: number }>("/invoices", {
        company_id: companyId,
        contact_id: contactId,
        currency,
        shipping,
        payment_method_ref: paymentRefFromKey(paymentChoices, paymentValue),
        notes: notes || null,
        items: filled.map(toInvoiceItem),
      });
      navigate(`/invoices/${inv.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageLayout
      titleText={t("invoices.createTitle")}
      subtitleKey="invoices.createSubtitle"
      headerAction={
        <Button variant="secondary" size="md" onClick={() => navigate("/management-center/tenant-profile")}>
          {t("nav.tenantProfile")}
        </Button>
      }
    >
      <Stack direction="column" gap="4">
        {error !== "" && (
          <Callout variant="warning" title={t("invoiceForm.createBlocked")}>
            <span data-testid="invoice-error">{error}</span>
          </Callout>
        )}

        <SectionCard title={t("invoiceForm.sectionShipTo")}>
          <Stack direction="column" gap="3">
            <CompanyContactSelector
              value={{ companyId, contactId }}
              onChange={({ companyId: c, contactId: ct }) => changeCompanyContact(c, ct)}
              required
              error={selectorError}
            />
            {companyId !== null && (
              <InvoiceShipToSection companyId={companyId} ctx={ctx} loading={ctxQ.isPending} errorText={ctxError} />
            )}
          </Stack>
        </SectionCard>

        <SectionCard title={t("invoiceForm.sectionPaymentTotals")}>
          <InvoicePaymentTotalsSection
            ctx={ctx}
            currencyOptions={currencyChoices(ctx)}
            currency={currency}
            onCurrencyChange={(next) => { setCurrencyChoice(next); setPaymentChoice(""); }}
            paymentChoices={paymentChoices}
            paymentValue={paymentValue}
            onPaymentChange={setPaymentChoice}
            notes={notes}
            onNotesChange={setNotes}
            totalWeight={weight}
            shippingQuotes={shippingQuotes}
            shippingPick={shippingPick}
            onShippingPick={setShippingPick}
            preview={preview}
            previewError={previewError}
            disabled={saving}
          />
        </SectionCard>

        <SectionCard title={t("invoiceForm.sectionItems")}>
          <LineItemsTable
            rows={rows}
            onChange={setRows}
            inventory={inventory}
            currency={currency}
            rate={rate}
            showErrors={showErrors}
            disabled={saving}
          />
        </SectionCard>

        <SectionCard title={t("invoiceForm.sectionActions")}>
          <Stack direction="row" gap="3">
            {/* 今の画面の「キャンセル」（請求書の一覧へ戻る）はそのまま残す */}
            <Button type="button" variant="secondary" size="md" onClick={() => navigate("/invoices")} disabled={saving}>
              {t("common.cancel")}
            </Button>
            <Button type="button" variant="secondary" size="md" onClick={() => setClearOpen(true)} disabled={saving} data-testid="invoice-clear">
              {t("invoiceForm.clear")}
            </Button>
            <Button type="button" variant="primary" size="md" loading={saving} disabled={saving} onClick={submitInvoice} data-testid="invoice-create-submit">
              {t("invoices.createBtn")}
            </Button>
          </Stack>
        </SectionCard>
      </Stack>

      <ConfirmModal
        open={clearOpen}
        title={t("invoiceForm.clearConfirmTitle")}
        message={t("invoiceForm.clearConfirmMessage")}
        confirmLabel={t("invoiceForm.clearConfirmYes")}
        cancelLabel={t("common.cancel")}
        danger
        onConfirm={clearAll}
        onCancel={() => setClearOpen(false)}
      />
    </PageLayout>
  );
}
```

### 2-7. frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx（丸ごと置き換え）

```tsx
/* eslint-disable local/no-japanese-literal -- テスト: 在庫の道が返すカテゴリの日本語名を試験データに書く（ADR-027・precedent: DataTable.test.tsx） */
// invoice-create-portfolio R5: 請求書作成ページを見本の見た目と操作に作り直した（design-v2 §3-1〜§3-6・§6 K1〜K3・K5〜K14・K19〜K21）
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from './InvoiceCreatePage';
import en from '../../locales/en.json';
import { queryClient } from '../../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string, opts?: Record<string, unknown>) => String(instance.t(key, opts));
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }

const SLOW = { timeout: 4000 };
const CTX_PATH = '/invoices/draft-context?company_id=4&contact_id=5';
const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
const address = {
  company_name: 'Buyer Inc', billing_display_name: null, label: null, postal_code: '10001', address: '1 Main St', city: 'New York', state: 'NY', country: 'US', phone: '+1 555',
  recipient_name: 'Ann Lee', email: 'ann@example.com', tax_id: 'TAX-9', address_line_1: '1 Main St', address_line_2: 'Suite 2', address_line_3: 'Floor 3', country_name: 'United States',
};
let ctx: Record<string, unknown>;
function baseCtx() {
  return {
    company_id: 4, ship_to: address, bill_to: { ...address, address_line_1: '2 Bill St' }, contact_name: 'One Buyer', contact_email: 'buyer@example.com',
    issuer_region: 'JP', origin_country_code: 'JP', destination_country_code: 'US', destination_postal_code: '10001',
    currencies: ['JPY', 'USD'], fx_rates: [{ currency: 'USD', rate: 150, fetched_at: '2026-11-15' }], default_currency: 'USD', currency: null,
    payment_methods: [
      { id: 3, method_type: 'bank', display_name: 'Main bank', wise_currency: null },
      { id: 4, method_type: 'wise', display_name: 'Wise USD', wise_currency: 'USD' },
    ],
    tax_rate_percent: null, incoterms: 'DAP',
  };
}
const inventory = {
  categories: [{ code: 'OP', name_ja: 'ワンピース' }, { code: 'PK', name_ja: 'ポケモン' }],
  items: [
    { product_id: 7, name: 'Booster Box A', name_en: 'Booster Box A EN', mark: 'OP-01', work_code: 'OP', box_weight_kg: 0.5, case_weight_kg: 6,
      cells: { Case: { price: 170000, quantity: 1 }, 'Sealed box': { price: 15000, quantity: 3 } } },
    { product_id: 8, name: 'No Weight Box', name_en: null, mark: 'PK-1', work_code: 'PK', box_weight_kg: null, case_weight_kg: null,
      cells: { 'Sealed box': { price: 3000, quantity: 2 } } },
    { product_id: 9, name: 'Sold Out Box', name_en: null, mark: 'PK-2', work_code: 'PK', box_weight_kg: 0.4, case_weight_kg: null,
      cells: { 'Sealed box': { price: 3000, quantity: 0 } } },
  ],
};
const liveRate = { carrier: 'FedEx', zone: 'A', fee: 33.333, currency: 'USD', source: 'fedex_live', service_type: 'FEDEX_IP', service_name: 'International Priority', transit_days: 3 };
const staticRate = { carrier: 'DHL', zone: '3', fee: 40, currency: 'USD', source: 'static', service_type: null, service_name: null, transit_days: null };
let shippingAnswer: Record<string, unknown>;

type PreviewBody = { currency: string; items: Array<{ quantity: number; unit_price: number }>; shipping: { mode: string; fee?: number } | null };
function previewFor(body: PreviewBody) {
  const subtotal = body.items.reduce((s, i) => s + i.quantity * i.unit_price, 0);
  if (body.shipping === null) {
    return { currency: body.currency, subtotal: String(subtotal), shipping_fee: null, tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: null, uncomputed: ['shipping_required'], incoterms: 'DAP' };
  }
  const fee = body.shipping.mode === 'calculate' ? body.shipping.fee ?? 0 : 0;
  return { currency: body.currency, subtotal: String(subtotal), shipping_fee: String(fee), tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: String(subtotal + fee), uncomputed: [], incoterms: 'DAP' };
}

function view(state: Record<string, unknown> | null = { draft: { companyId: 4, contactId: 5, currency: 'USD', notes: '' } }) {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={[{ pathname: '/invoices/new', state }]}>
        <InvoiceCreatePage />
        <Location />
      </MemoryRouter>
    </I18nextProvider>,
  );
}
/** 在庫表の画面から 1 商品を持ってきた形で開き、状態を選ぶ */
async function openWithProduct(productId = 7, state = 'Sealed box') {
  const product = inventory.items.find((i) => i.product_id === productId)!;
  view({ draft: { companyId: 4, contactId: 5, currency: 'USD', notes: '' }, selectedProducts: [{ product_id: productId, product_name: product.name, unit_price: null }] });
  await screen.findByTestId('invoice-ship-to-address');
  // 在庫の答えが届くと状態の選択肢が出る（どの商品も Sealed box を持つ）
  await waitFor(() => expect(optionValues('invoice-item-state-0')).toContain('Sealed box'));
  if (state !== '') fireEvent.change(screen.getByTestId('invoice-item-state-0'), { target: { value: state } });
}
const optionValues = (testId: string) => Array.from((screen.getByTestId(testId) as HTMLSelectElement).options).map((o) => o.value);
const posts = (path: string) => mock.post.mock.calls.filter(([url]) => url === path).map(([, body]) => body as Record<string, unknown>);
const previewCalls = () => posts('/invoices/preview') as unknown as PreviewBody[];
const rows = () => screen.getAllByTestId(/^invoice-item-row-\d+$/);
const submit = () => screen.getByTestId('invoice-create-submit') as HTMLButtonElement;

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  ctx = baseCtx();
  shippingAnswer = { results: [liveRate, staticRate], live_error: null };
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.create'] };
    if (url === '/companies?per_page=100') return [company];
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === CTX_PATH) return ctx;
    if (url === '/invoices/draft-inventory') return inventory;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(async (url: string, body: unknown) => {
    if (url === '/invoices/preview') return previewFor(body as PreviewBody);
    if (url === '/invoices/draft-shipping-quotes') return shippingAnswer;
    if (url === '/invoices') return { id: 11 };
    throw new Error(`Unexpected POST ${url}`);
  });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected patch'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('InvoiceCreatePage (invoice-create-portfolio R5)', () => {
  it('K1: four cards in the order ship-to, payment and totals, products, actions', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    const headings = Array.from(document.querySelectorAll('.comp-section-card__title')).map((h) => h.textContent);
    expect(headings).toEqual([tr('invoiceForm.sectionShipTo'), tr('invoiceForm.sectionPaymentTotals'), tr('invoiceForm.sectionItems'), tr('invoiceForm.sectionActions')]);
  });

  it('K2/K3: ship-to shows 12 read-only fields in two columns with the registered values', async () => {
    view();
    const box = await screen.findByTestId('invoice-ship-to-address');
    expect(box.querySelectorAll('input, textarea, select').length).toBe(0);
    const fields = within(box).getAllByTestId(/^invoice-ship-to-field-/);
    expect(fields.length).toBe(12);
    const text = (key: string) => within(box).getByTestId(`invoice-ship-to-field-${key}`).textContent;
    expect(text('customer')).toContain('Buyer Inc');
    expect(text('recipient')).toContain('Ann Lee');
    expect(text('phone')).toContain('+1 555');
    expect(text('email')).toContain('ann@example.com');
    expect(text('tax')).toContain('TAX-9');
    expect(text('country')).toContain('United States');
    expect(text('address1')).toContain('1 Main St');
    expect(text('address2')).toContain('Suite 2');
    expect(text('address3')).toContain('Floor 3');
    expect(text('city')).toContain('New York');
    expect(text('state')).toContain('NY');
    expect(text('zip')).toContain('10001');
  });

  it('K3: empty fields show "unregistered"', async () => {
    ctx = { ...baseCtx(), ship_to: { ...address, tax_id: null, address_line_3: '' } };
    view();
    const box = await screen.findByTestId('invoice-ship-to-address');
    expect(within(box).getByTestId('invoice-ship-to-field-tax').textContent).toContain(tr('common.unregistered'));
    expect(within(box).getByTestId('invoice-ship-to-field-address3').textContent).toContain(tr('common.unregistered'));
  });

  it('K5: payment and totals has three columns with the designed contents', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    const pay = screen.getByTestId('invoice-col-payment');
    await waitFor(() => expect(within(pay).getByTestId('invoice-currency-select')).toBeTruthy());
    expect(within(pay).getByTestId('invoice-payment-select')).toBeTruthy();
    expect(within(pay).getByTestId('invoice-notes')).toBeTruthy();
    const ship = screen.getByTestId('invoice-col-shipping');
    expect(within(ship).getByTestId('invoice-total-weight')).toBeTruthy();
    expect(within(ship).getByTestId('invoice-shipping-none')).toBeTruthy();
    const totals = screen.getByTestId('invoice-col-totals');
    for (const id of ['invoice-total-subtotal', 'invoice-total-shipping', 'invoice-total-tax', 'invoice-total-amount']) expect(within(totals).getByTestId(id)).toBeTruthy();
  });

  it('K2 (payment): currency and payment choices come from draft-context; JPY drops the Wise USD row', async () => {
    view();
    await waitFor(() => expect(optionValues('invoice-currency-select')).toEqual(['', 'JPY', 'USD']));
    expect((screen.getByTestId('invoice-currency-select') as HTMLSelectElement).value).toBe('USD');
    expect(optionValues('invoice-payment-select')).toEqual(['', 'bank:3', 'wise:4']);
    fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'wise:4' } });
    fireEvent.change(screen.getByTestId('invoice-currency-select'), { target: { value: 'JPY' } });
    await waitFor(() => expect(optionValues('invoice-payment-select')).toEqual(['', 'bank:3']));
    expect((screen.getByTestId('invoice-payment-select') as HTMLSelectElement).value).toBe('');
  });

  it('K6: once the weight is known, every rate is listed without any click, each with a live/static badge', async () => {
    await openWithProduct();
    const list = await screen.findByTestId('invoice-shipping-list');
    await waitFor(() => expect(within(list).getByTestId('invoice-shipping-rate-fedex_live|FedEx|FEDEX_IP')).toBeTruthy(), SLOW);
    expect(within(list).getByTestId('invoice-shipping-rate-static|DHL|')).toBeTruthy();
    expect(list.textContent).toContain(tr('invoiceForm.sourceLive'));
    expect(list.textContent).toContain(tr('invoiceForm.sourceStatic'));
    expect(posts('/invoices/draft-shipping-quotes')).toEqual([{ company_id: 4, weight_kg: 0.5 }]);
  });

  it('K6: when live FedEx fails, the reason is shown', async () => {
    shippingAnswer = { results: [staticRate], live_error: 'FedEx is not connected' };
    await openWithProduct();
    expect((await screen.findByTestId('invoice-shipping-live-error', {}, SLOW)).textContent).toContain('FedEx is not connected');
    expect(screen.queryByTestId('invoice-shipping-rate-fedex_live|FedEx|FEDEX_IP')).toBeNull();
  });

  it('K7: the same weight is not asked twice', async () => {
    await openWithProduct();
    await waitFor(() => expect(posts('/invoices/draft-shipping-quotes').length).toBe(1), SLOW);
    fireEvent.change(screen.getByTestId('invoice-item-quantity-0'), { target: { value: '2' } });
    await waitFor(() => expect(posts('/invoices/draft-shipping-quotes').length).toBe(2), SLOW);
    fireEvent.change(screen.getByTestId('invoice-item-quantity-0'), { target: { value: '1' } });
    await waitFor(() => expect(screen.getByTestId('invoice-shipping-rate-static|DHL|')).toBeTruthy(), SLOW);
    expect(posts('/invoices/draft-shipping-quotes').map((b) => b.weight_kg)).toEqual([0.5, 1]);
  });

  it('K5/K8: choosing a rate sends it to the preview and the total is shown', async () => {
    await openWithProduct();
    const pick = await screen.findByTestId('invoice-shipping-rate-fedex_live|FedEx|FEDEX_IP', {}, SLOW);
    expect(screen.getByTestId('invoice-total-amount').textContent).toBe(tr('invoiceForm.notComputed'));
    fireEvent.click(pick);
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'calculate' && b.shipping.fee === 33.33)).toBe(true), SLOW);
    await waitFor(() => expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed')), SLOW);
  });

  it('K9: 12 rows at first, up to 20, the 21st is refused with a notice; one row cannot be removed', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    expect(rows().length).toBe(12);
    for (let i = 0; i < 8; i += 1) fireEvent.click(screen.getByTestId('invoice-add-row'));
    expect(rows().length).toBe(20);
    expect((screen.getByTestId('invoice-add-row') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId('invoice-max-rows').textContent).toBe(tr('lineItems.maxRows', { count: 20 }));
    for (let i = 0; i < 19; i += 1) fireEvent.click(screen.getByTestId('invoice-item-remove-0'));
    expect(rows().length).toBe(1);
    expect((screen.getByTestId('invoice-item-remove-0') as HTMLButtonElement).disabled).toBe(true);
  });

  it('K10: after choosing a category, only in-stock products of that category are offered', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    await waitFor(() => expect(optionValues('invoice-item-category-0')).toEqual(['', 'OP', 'PK']));
    fireEvent.change(screen.getByTestId('invoice-item-category-0'), { target: { value: 'PK' } });
    const input = within(screen.getByTestId('invoice-item-product-0')).getByRole('combobox');
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: 'box' } });
    await screen.findByRole('option', { name: 'No Weight Box (PK-1)' });
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map((o) => o.textContent)).toEqual(['No Weight Box (PK-1)']);
  });

  it('K11/K13: choosing a product offers only in-stock states; the state fills weight, price and stock limit', async () => {
    await openWithProduct(7, '');
    expect(optionValues('invoice-item-state-0')).toEqual(['', 'Case', 'Sealed box']);
    fireEvent.change(screen.getByTestId('invoice-item-state-0'), { target: { value: 'Sealed box' } });
    expect(screen.getByTestId('invoice-item-weight-0').textContent).toBe(tr('lineItems.weightKg', { value: 0.5 }));
    expect(within(screen.getByTestId('invoice-item-row-0')).queryAllByRole('spinbutton').map((el) => el.getAttribute('data-testid'))).toEqual(['invoice-item-quantity-0', 'invoice-item-price-0']);
    expect((screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value).toBe('100');
  });

  it('K12: a quantity above stock goes back to the stock count with a notice', async () => {
    await openWithProduct();
    fireEvent.change(screen.getByTestId('invoice-item-quantity-0'), { target: { value: '9' } });
    expect((screen.getByTestId('invoice-item-quantity-0') as HTMLInputElement).value).toBe('3');
    expect(screen.getByTestId('invoice-item-row-0').textContent).toContain(tr('lineItems.stockLimit', { count: 3 }));
  });

  it('unit price: a currency change reconverts only rows whose price was not typed by hand', async () => {
    await openWithProduct();
    expect((screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value).toBe('100');
    fireEvent.change(screen.getByTestId('invoice-currency-select'), { target: { value: 'JPY' } });
    await waitFor(() => expect((screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value).toBe('15000'));
    fireEvent.change(screen.getByTestId('invoice-item-price-0'), { target: { value: '14000' } });
    fireEvent.change(screen.getByTestId('invoice-currency-select'), { target: { value: 'USD' } });
    await waitFor(() => expect((screen.getByTestId('invoice-currency-select') as HTMLSelectElement).value).toBe('USD'));
    expect((screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value).toBe('14000');
  });

  it('K14: there is no inventory/quote mode switch and no quote list is read', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    expect(screen.queryByTestId('invoice-mode-inventory')).toBeNull();
    expect(screen.queryByTestId('invoice-mode-quote')).toBeNull();
    expect(mock.get.mock.calls.some(([url]) => String(url).startsWith('/quotes'))).toBe(false);
  });

  it('K19: clear asks first; "no" changes nothing, "yes" empties rows, ship-to, shipping and memo', async () => {
    await openWithProduct();
    fireEvent.change(screen.getByTestId('invoice-notes'), { target: { value: 'Fragile' } });
    fireEvent.click(screen.getByTestId('invoice-clear'));
    let dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect((screen.getByTestId('invoice-notes') as HTMLInputElement).value).toBe('Fragile');
    expect((screen.getByTestId('invoice-item-state-0') as HTMLSelectElement).value).toBe('Sealed box');
    fireEvent.click(screen.getByTestId('invoice-clear'));
    dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: tr('invoiceForm.clearConfirmYes') }));
    await waitFor(() => expect(screen.queryByTestId('invoice-ship-to')).toBeNull());
    expect((screen.getByTestId('invoice-notes') as HTMLInputElement).value).toBe('');
    expect(rows().length).toBe(12);
    expect((screen.getByTestId('invoice-item-state-0') as HTMLSelectElement).value).toBe('');
    expect((screen.getByTestId('invoice-shipping-none') as HTMLInputElement).checked).toBe(false);
  });

  it('K20: a row without a state stops creation and marks the state field', async () => {
    await openWithProduct(7, '');
    fireEvent.click(submit());
    expect(await screen.findByText(tr('lineItems.stateMissing'))).toBeTruthy();
    expect(screen.getByTestId('invoice-error').textContent).toBe(tr('invoiceForm.rowsNotReady'));
    expect(posts('/invoices')).toEqual([]);
  });

  it('K21: a product without a registered weight shows "unregistered" and is not created', async () => {
    await openWithProduct(8, 'Sealed box');
    expect(within(screen.getByTestId('invoice-item-weight-0')).getByText(tr('common.unregistered'))).toBeTruthy();
    fireEvent.click(submit());
    expect(await screen.findByTestId('invoice-item-weight-missing-0')).toBeTruthy();
    expect(posts('/invoices')).toEqual([]);
  });

  it('create: "no shipping" + payment sends the exact body once and opens the detail page', async () => {
    await openWithProduct();
    await waitFor(() => expect(optionValues('invoice-payment-select')).toContain('bank:3'));
    fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'bank:3' } });
    fireEvent.click(screen.getByTestId('invoice-shipping-none'));
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'none' && b.items.length === 1)).toBe(true), SLOW);
    await waitFor(() => expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed')), SLOW);
    fireEvent.click(submit());
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/invoices/11'));
    expect(posts('/invoices')).toEqual([{
      company_id: 4, contact_id: 5, currency: 'USD', shipping: { mode: 'none' }, payment_method_ref: { method_type: 'bank', id: 3 }, notes: null,
      items: [{ product_id: 7, product_name: 'Booster Box A', name_en: 'Booster Box A EN', condition: 'Sealed box', unit: 'box', quantity: 1, unit_price: 100, weight: 0.5 }],
    }]);
  });

  it('create is refused with a reason while shipping is not chosen', async () => {
    await openWithProduct();
    fireEvent.click(submit());
    expect(screen.getByTestId('invoice-error').textContent).toBe(tr('invoiceForm.createNotReady'));
    expect(posts('/invoices')).toEqual([]);
  });

  it('no payment destinations: create is allowed without one and the profile link is offered', async () => {
    ctx = { ...baseCtx(), payment_methods: [] };
    await openWithProduct();
    expect(await screen.findByTestId('invoice-open-tenant-profile')).toBeTruthy();
    fireEvent.click(screen.getByTestId('invoice-shipping-none'));
    await waitFor(() => expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed')), SLOW);
    fireEvent.click(submit());
    await waitFor(() => expect(posts('/invoices').length).toBe(1));
    expect(posts('/invoices')[0].payment_method_ref).toBeNull();
  });

  it('issuer region missing: create is refused and the company page link is shown', async () => {
    ctx = { ...baseCtx(), issuer_region: null };
    await openWithProduct();
    expect(await screen.findByTestId('invoice-open-company-for-bill-to')).toBeTruthy();
    fireEvent.click(screen.getByTestId('invoice-shipping-none'));
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'none')).toBe(true), SLOW);
    fireEvent.click(submit());
    expect(posts('/invoices')).toEqual([]);
    fireEvent.click(screen.getByTestId('invoice-open-company-for-bill-to'));
    expect(screen.getByTestId('location').textContent).toBe('/crm/companies/4');
  });
});
```

### 2-8. frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx（丸ごと置き換え）

```tsx
/**
 * 請求書作成ページの「支払いと合計」の中身（invoice-create-portfolio design-v2 §3-1・§3-5・K5〜K8）。
 *
 * 3 列（ThreeColumn。狭い画面では縦 1 列）:
 *   左: 通貨・支払方法・発送メモ（候補はサーバーの材料 draft-context だけ。直書きしない）
 *   中: 総重量と便ごとの送料の一覧（POST /invoices/draft-shipping-quotes の答え）。1 つ選ぶか「送料を請求しない」。
 *       各行に出所の印（ライブ／静的。ADR-125 D6）。
 *   右: 合計枠（TotalsBox）。額はサーバーの試算（preview）の答えをそのまま見せる。答えが無い所は「未計算」と理由。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Radio } from "../../components/Radio";
import { Select } from "../../components/Select";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import { ThreeColumn } from "../../components/ThreeColumn";
import { TotalsBox } from "../../components/TotalsBox";
import {
  PAYMENT_METHOD_LABEL_KEYS,
  formatMoney,
  fxRateFor,
  paymentKey,
  uncomputedReasonKey,
  type DraftContext,
  type DraftContextPayment,
  type InvoicePreview,
} from "../../lib/invoiceDraftContext";
import { rateFee, type DraftShippingQuotesState, type DraftShippingRate } from "./useDraftShippingQuotes";

/** 送料の選択の値。「送料を請求しない」は SHIPPING_NONE、便は shippingRateKey */
export const SHIPPING_NONE = "none";

export function shippingRateKey(rate: DraftShippingRate): string {
  return `${rate.source}|${rate.carrier}|${rate.service_type ?? ""}`;
}

export interface InvoicePaymentTotalsSectionProps {
  ctx: DraftContext | null;
  currencyOptions: string[];
  currency: string;
  onCurrencyChange: (next: string) => void;
  paymentChoices: DraftContextPayment[];
  paymentValue: string;
  onPaymentChange: (next: string) => void;
  notes: string;
  onNotesChange: (next: string) => void;
  totalWeight: number;
  shippingQuotes: DraftShippingQuotesState;
  /** 選んだ送料の値（"" は未選択） */
  shippingPick: string;
  onShippingPick: (next: string) => void;
  preview: InvoicePreview | null;
  previewError: string;
  disabled?: boolean;
}

export function InvoicePaymentTotalsSection(props: InvoicePaymentTotalsSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    ctx, currencyOptions, currency, onCurrencyChange, paymentChoices, paymentValue, onPaymentChange,
    notes, onNotesChange, totalWeight, shippingQuotes, shippingPick, onShippingPick, preview, previewError,
    disabled = false,
  } = props;

  const fx = currency !== "" ? fxRateFor(ctx, currency) : null;
  const paymentLabel = (p: DraftContextPayment) =>
    p.display_name !== null && p.display_name !== "" ? p.display_name : t(PAYMENT_METHOD_LABEL_KEYS[p.method_type]);
  const money = (v: string | null | undefined) => formatMoney(v, currency) ?? t("invoiceForm.notComputed");
  const rates = shippingQuotes.quotes?.results ?? [];
  const liveError = shippingQuotes.quotes?.live_error ?? null;
  const canQuote = ctx !== null && ctx.origin_country_code !== null && ctx.destination_country_code !== null;

  const left = (
    <Stack direction="column" gap="3">
      <div data-testid="invoice-currency">
        <Select
          label={t("invoiceForm.currency")}
          required
          fullWidth
          value={currency}
          disabled={disabled}
          onChange={(e) => onCurrencyChange(e.target.value)}
          placeholder={t("invoiceForm.currencyPlaceholder")}
          options={currencyOptions.map((c) => ({ value: c, label: c }))}
          helperText={
            fx !== null
              ? t("invoiceForm.fxRateLine", { currency: fx.currency, rate: fx.rate, at: fx.fetched_at ?? "-" })
              : currencyOptions.length === 0 && ctx !== null
                ? t("invoiceForm.noCurrency")
                : undefined
          }
          data-testid="invoice-currency-select"
        />
      </div>
      {paymentChoices.length > 0 ? (
        <Select
          label={t("invoiceForm.payment")}
          required
          fullWidth
          value={paymentValue}
          disabled={disabled}
          onChange={(e) => onPaymentChange(e.target.value)}
          placeholder={t("invoiceForm.paymentPlaceholder")}
          options={paymentChoices.map((p) => ({ value: paymentKey(p), label: paymentLabel(p) }))}
          data-testid="invoice-payment-select"
        />
      ) : ctx !== null && ctx.issuer_region !== null ? (
        <Callout variant="info" title={t("invoiceForm.noPaymentMethods")}>
          <Button type="button" variant="secondary" size="sm" onClick={() => navigate("/management-center/tenant-profile")} data-testid="invoice-open-tenant-profile">
            {t("invoiceForm.openTenantProfile")}
          </Button>
        </Callout>
      ) : null}
      <TextField
        label={t("invoiceForm.shippingMemo")}
        fullWidth
        value={notes}
        disabled={disabled}
        onChange={(e) => onNotesChange(e.target.value)}
        data-testid="invoice-notes"
      />
    </Stack>
  );

  const middle = (
    <Stack direction="column" gap="2">
      <p data-testid="invoice-total-weight">{t("invoiceForm.totalWeightLine", { value: totalWeight })}</p>
      <div role="radiogroup" aria-label={t("invoiceForm.shipping")} data-testid="invoice-shipping-list">
        <Stack direction="column" gap="2">
          <Radio
            name="invoice-shipping"
            value={SHIPPING_NONE}
            label={t("invoiceForm.shippingNone")}
            checked={shippingPick === SHIPPING_NONE}
            disabled={disabled}
            onChange={() => onShippingPick(SHIPPING_NONE)}
            data-testid="invoice-shipping-none"
          />
          {rates.map((r) => {
            const key = shippingRateKey(r);
            const fee = rateFee(r);
            return (
              <Stack key={key} direction="row" gap="2">
                <Radio
                  name="invoice-shipping"
                  value={key}
                  label={t("invoiceForm.shippingRateLine", {
                    carrier: r.carrier,
                    service: r.service_name ?? r.service_type ?? "-",
                    fee: fee === null ? "-" : formatMoney(fee, r.currency) ?? String(fee),
                  })}
                  description={r.transit_days !== null ? t("invoiceForm.transitDays", { count: r.transit_days }) : undefined}
                  checked={shippingPick === key}
                  disabled={disabled || fee === null}
                  onChange={() => onShippingPick(key)}
                  data-testid={`invoice-shipping-rate-${key}`}
                />
                <Badge variant={r.source === "fedex_live" ? "success" : "neutral"} size="sm">
                  {t(r.source === "fedex_live" ? "invoiceForm.sourceLive" : "invoiceForm.sourceStatic")}
                </Badge>
              </Stack>
            );
          })}
        </Stack>
      </div>
      {!canQuote && ctx !== null && (
        <p data-testid="invoice-shipping-needs-countries">{t("invoiceForm.shippingNeedsCountries")}</p>
      )}
      {canQuote && shippingQuotes.key === "" && (
        <p data-testid="invoice-shipping-needs-weight">{t("invoiceForm.shippingNeedsWeight")}</p>
      )}
      {shippingQuotes.loading && <p role="status" data-testid="invoice-shipping-loading">{t("invoiceForm.shippingLoading")}</p>}
      {shippingQuotes.error !== "" && (
        <Callout variant="warning" title={t("invoiceForm.shippingQuoteError")}>
          <span data-testid="invoice-shipping-error">{shippingQuotes.error}</span>
        </Callout>
      )}
      {liveError !== null && (
        <Callout variant="info" title={t("invoiceForm.fedexLiveUnavailable")}>
          <span data-testid="invoice-shipping-live-error">{liveError}</span>
        </Callout>
      )}
    </Stack>
  );

  const taxLabel = preview?.duty_label ?? t("invoiceForm.tax", { rate: preview?.tax_rate_percent ?? "-" });
  const taxValue = preview === null ? t("invoiceForm.notComputed") : preview.duty_label !== null ? money(preview.duty_amount) : money(preview.tax_amount);
  const right = (
    <Stack direction="column" gap="2">
      <div data-testid="invoice-totals">
        <TotalsBox
          rows={[
            { key: "subtotal", label: t("invoiceForm.subtotal"), value: <span data-testid="invoice-total-subtotal">{preview ? money(preview.subtotal) : t("invoiceForm.notComputed")}</span> },
            { key: "shipping", label: t("invoiceForm.shippingFee"), value: <span data-testid="invoice-total-shipping">{preview ? money(preview.shipping_fee) : t("invoiceForm.notComputed")}</span> },
            { key: "tax", label: taxLabel, value: <span data-testid="invoice-total-tax">{taxValue}</span> },
          ]}
          total={{ label: t("invoiceForm.total"), value: <span data-testid="invoice-total-amount">{preview ? money(preview.total_amount) : t("invoiceForm.notComputed")}</span> }}
        />
      </div>
      {preview && preview.uncomputed.length > 0 && (
        <Callout variant="warning" title={t("invoiceForm.uncomputedTitle")}>
          <ul data-testid="invoice-uncomputed">
            {preview.uncomputed.map((r) => (
              <li key={r} data-testid={`invoice-uncomputed-${r}`}>{t(uncomputedReasonKey(r))}</li>
            ))}
          </ul>
        </Callout>
      )}
      {previewError !== "" && (
        <Callout variant="warning" title={t("invoiceForm.previewErrorTitle")}>
          <span data-testid="invoice-preview-error">{previewError}</span>
        </Callout>
      )}
    </Stack>
  );

  return (
    <div data-testid="invoice-payment-totals">
      <ThreeColumn gap="4">
        <div data-testid="invoice-col-payment">{left}</div>
        <div data-testid="invoice-col-shipping">{middle}</div>
        <div data-testid="invoice-col-totals">{right}</div>
      </ThreeColumn>
    </div>
  );
}
```

### 2-9. frontend/src/pages/invoice-create/InvoiceShipToSection.tsx（丸ごと置き換え）

```tsx
/**
 * 請求書作成ページの「発送先」の中身（invoice-create-portfolio design-v2 §3-2・K2・K3）。
 *
 * 会社の画面で登録した住所を 12 欄・2 列で読んで見せるだけ（この画面では打たない）。空の欄は「未登録」。
 * 届け先の既定の住所を使い、無ければ請求先の既定（サーバーの選び方と同じ）。
 * 直したいときは会社の画面へ移るボタンを出す。
 * 請求書を出す側の地域（issuer_region）が決まらないときは、作成できない理由と会社の画面への道を出す。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { LoadingBlock } from "../../components/loading";
import { ReadOnlyField } from "../../components/ReadOnlyField";
import { Stack } from "../../components/Stack";
import { TwoColumn } from "../../components/TwoColumn";
import type { DraftAddress, DraftContext } from "../../lib/invoiceDraftContext";

export interface InvoiceShipToSectionProps {
  companyId: number | null;
  ctx: DraftContext | null;
  loading: boolean;
  errorText: string;
}

interface ShipToField {
  key: string;
  labelKey: string;
  value: string | null | undefined;
}

function firstFilled(...values: Array<string | null | undefined>): string | null {
  return values.find((v) => v !== null && v !== undefined && v.trim() !== "") ?? null;
}

/** 12 欄の中身（左 6・右 6）。出どころは design-v2 §3-2 の表 */
export function shipToFields(ctx: DraftContext): { left: ShipToField[]; right: ShipToField[] } {
  const a: DraftAddress | null = ctx.ship_to ?? ctx.bill_to;
  return {
    left: [
      { key: "customer", labelKey: "invoiceForm.fieldCustomer", value: firstFilled(a?.billing_display_name, a?.company_name) },
      { key: "recipient", labelKey: "invoiceForm.fieldRecipient", value: firstFilled(a?.recipient_name, ctx.contact_name) },
      { key: "phone", labelKey: "invoiceForm.fieldPhone", value: a?.phone },
      { key: "email", labelKey: "invoiceForm.fieldEmail", value: firstFilled(a?.email, ctx.contact_email) },
      { key: "tax", labelKey: "invoiceForm.fieldTaxId", value: a?.tax_id },
      { key: "country", labelKey: "invoiceForm.fieldCountry", value: firstFilled(a?.country_name, a?.country) },
    ],
    right: [
      { key: "address1", labelKey: "invoiceForm.fieldAddress1", value: a?.address_line_1 },
      { key: "address2", labelKey: "invoiceForm.fieldAddress2", value: a?.address_line_2 },
      { key: "address3", labelKey: "invoiceForm.fieldAddress3", value: a?.address_line_3 },
      { key: "city", labelKey: "invoiceForm.fieldCity", value: a?.city },
      { key: "state", labelKey: "invoiceForm.fieldState", value: a?.state },
      { key: "zip", labelKey: "invoiceForm.fieldZip", value: a?.postal_code },
    ],
  };
}

export function InvoiceShipToSection({ companyId, ctx, loading, errorText }: InvoiceShipToSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const openCompany = () => {
    if (companyId !== null) navigate(`/crm/companies/${companyId}`);
  };

  if (errorText !== "") {
    return (
      <div data-testid="invoice-ship-to">
        <Callout variant="warning" title={t("invoiceForm.contextError")}>
          <p data-testid="invoice-context-error">{errorText}</p>
        </Callout>
      </div>
    );
  }
  if (ctx === null) {
    return (
      <div data-testid="invoice-ship-to">
        {loading ? <LoadingBlock /> : <p>{t("invoiceForm.chooseCompany")}</p>}
      </div>
    );
  }

  const { left, right } = shipToFields(ctx);
  const column = (fields: ShipToField[]) => (
    <Stack direction="column" gap="2">
      {fields.map((f) => (
        <div key={f.key} data-testid={`invoice-ship-to-field-${f.key}`}>
          <ReadOnlyField label={t(f.labelKey)} value={f.value ?? null} />
        </div>
      ))}
    </Stack>
  );

  return (
    <div data-testid="invoice-ship-to">
      <Stack direction="column" gap="3">
        {ctx.issuer_region === null && (
          <Callout variant="warning" title={t("apiError.billToCountry")}>
            <Button type="button" variant="secondary" size="sm" onClick={openCompany} data-testid="invoice-open-company-for-bill-to">
              {t("invoices.openCompanyForBillTo")}
            </Button>
          </Callout>
        )}
        <div data-testid="invoice-ship-to-address">
          <TwoColumn ratio="1:1" gap="4">
            {column(left)}
            {column(right)}
          </TwoColumn>
        </div>
        <Stack direction="row" gap="2">
          <Button type="button" variant="secondary" size="sm" onClick={openCompany} data-testid="invoice-open-company">
            {t("invoiceForm.openCompany")}
          </Button>
        </Stack>
      </Stack>
    </div>
  );
}
```

### 2-10. frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx（丸ごと置き換え）

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InventoryPage from '../pages/inventory/InventoryPage';
import ProductsPage from '../pages/products/ProductsPage';
import QuotesPage from '../pages/quotes/QuotesPage';
import en from '../locales/en.json';
import { queryClient } from '../lib/query/apiQuery';

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api }));
let instance = createInstance();
const permissions = ['products.update', 'products.create'];
const filters = (enabled: boolean) => ({ enabled, hidden_supplier_ids: [], hidden_categories: [], hidden_columns: [], show_conditions: [], show_units: [], show_offer_types: [], qty_min: null, qty_max: null, price_min: null, price_max: null });
function wrap(node: React.ReactNode) { return <I18nextProvider i18n={instance}><MemoryRouter>{node}</MemoryRouter></I18nextProvider>; }
function expectVariant(node: HTMLElement, variant: 'primary' | 'secondary') { expect(node.classList.contains(`comp-btn--${variant}`)).toBe(true); expect(node.classList.contains('comp-btn--tab')).toBe(false); }

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('five real-page dynamic Button migrations', () => {
  it.each([false, true])('Inventory uses enabled=%s independently from expanded state', async (enabled) => {
    api.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions };
      if (url === '/products/tcg-types') return [];
      if (url === '/me/inventory-filters') return filters(enabled);
      if (url.startsWith('/inventory?')) return { items: [], total: 0, page: 1, per_page: 50 };
      throw new Error(`Unexpected GET ${url}`);
    });
    render(wrap(<InventoryPage />)); const toggle = await screen.findByTestId('inventory-filter-toggle');
    expectVariant(toggle, enabled ? 'primary' : 'secondary'); expect(toggle.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(toggle); expect(toggle.getAttribute('aria-expanded')).toBe('true'); expectVariant(toggle, enabled ? 'primary' : 'secondary');
  });

  it('Products reorder condition changes real-page state and variant', async () => {
    api.get.mockImplementation(async (url: string) => { if (url === '/me/permissions') return { permissions }; if (url === '/products/tcg-types') return []; if (url === '/products/attribute-options') return {}; if (url.startsWith('/products?')) return []; throw new Error(`Unexpected GET ${url}`); });
    render(wrap(<ProductsPage />)); const toggle = await screen.findByTestId('products-reorder-toggle'); expectVariant(toggle, 'secondary'); expect(toggle.getAttribute('aria-pressed')).toBe('false'); fireEvent.click(toggle); expectVariant(toggle, 'primary'); expect(toggle.getAttribute('aria-pressed')).toBe('true'); expect(screen.getByTestId('products-reorder-hint')).toBeTruthy();
  });

  it('Quotes all-status condition changes on the real filter', async () => {
    api.get.mockImplementation(async (url: string) => { if (url === '/quotes') return []; throw new Error(`Unexpected GET ${url}`); });
    render(wrap(<QuotesPage />)); const all = await screen.findByTestId('quotes-filter-all'); expectVariant(all, 'primary'); fireEvent.click(screen.getByTestId('quotes-filter-draft')); expectVariant(all, 'secondary'); expect(screen.getByTestId('quotes-filter-draft').getAttribute('aria-pressed')).toBe('true');
  });
});
```

### 2-11. frontend/src/components/BillToCountryGuidance.test.tsx（丸ごと置き換え）

```tsx
// ADR-1061 便2-2c2a: 請求先の国が無くて請求書を作れなかったとき、取引先の画面へ移るボタンを出す
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import QuoteDetailPage from '../pages/quote-detail/QuoteDetailPage';
import en from '../locales/en.json';
import { ApiError } from '../lib/api';
import { queryClient } from '../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }

const approvedQuote = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', subtotal: 10, shipping_fee: null, tax_amount: null, total_amount: 10, status: 'approved', validity_date: null, notes: null, created_at: '', items: [] };
const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
// invoice-create-portfolio 便D: 作成画面は請求書の材料の issuer_region が無いときに案内を出す（作る前に分かる）
const draftCtx = (issuerRegion: string | null) => ({
  company_id: 4, ship_to: null, bill_to: null, contact_name: null, contact_email: null,
  issuer_region: issuerRegion, origin_country_code: issuerRegion, destination_country_code: null, destination_postal_code: null,
  currencies: ['USD'], fx_rates: [], default_currency: 'USD', currency: null, payment_methods: [], tax_rate_percent: null, incoterms: 'DAP',
});
let issuer: string | null = null;

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.create'] };
    if (url === '/companies?per_page=100') return [company];
    if (url === '/invoices/draft-inventory') return { categories: [], items: [] };
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === '/invoices/draft-context?company_id=4&contact_id=5') return draftCtx(issuer);
    throw new Error(`Unexpected GET ${url}`);
  });
  issuer = null;
  mock.post.mockImplementation(async (url: string) => {
    if (url === '/invoices/preview') return { currency: 'USD', subtotal: '10', shipping_fee: null, tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: null, uncomputed: ['shipping_required'], incoterms: 'DAP' };
    throw new Error(`Unexpected post ${url}`);
  });
  mock.patch.mockResolvedValue({});
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

// invoice-create-portfolio 便R5: 見積から読み込む切り替えは無くなった（p8）。会社と担当者を持って作成画面を開く
async function openCreatePageForCompany() {
  const state = { draft: { companyId: 4, contactId: 5, currency: 'USD' } };
  render(<I18nextProvider i18n={instance}><MemoryRouter initialEntries={[{ pathname: '/invoices/new', state }]}><InvoiceCreatePage /><Location /></MemoryRouter></I18nextProvider>);
  expect(await screen.findByRole('option', { name: /Buyer/ })).toBeTruthy();
}

describe('bill-to country guidance (ADR-1061 bin2-2c2a)', () => {
  it('create page: without a bill-to country it shows the reason and a button that opens the customer page', async () => {
    issuer = null;
    await openCreatePageForCompany();
    expect(await screen.findByText(tr('apiError.billToCountry'))).toBeTruthy();
    // 作成を押しても請求書は作られない
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.createBtn') }));
    expect(mock.post).not.toHaveBeenCalledWith('/invoices', expect.anything());
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.openCompanyForBillTo') }));
    expect(screen.getByTestId('location').textContent).toBe('/crm/companies/4');
  });

  it('create page: with a bill-to country the button is not shown', async () => {
    issuer = 'JP';
    await openCreatePageForCompany();
    expect(await screen.findByTestId('invoice-ship-to-address')).toBeTruthy();
    expect(screen.queryByRole('button', { name: tr('invoices.openCompanyForBillTo') })).toBeNull();
    expect(mock.post).not.toHaveBeenCalledWith('/invoices', expect.anything());
  });

  it('quote detail: converting shows the reason and a button that opens the customer page', async () => {
    mock.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions: ['invoices.create'] };
      if (url === '/quotes/7') return approvedQuote;
      throw new Error(`Unexpected GET ${url}`);
    });
    mock.post.mockRejectedValue(new ApiError(tr('apiError.billToCountry'), 422, 'bill_to_country'));
    render(routed(<QuoteDetailPage />, '/quotes/:id', ['/quotes/7']));
    fireEvent.click(await screen.findByRole('button', { name: tr('quotes.convertToInvoice') }));
    expect(await screen.findByText(tr('apiError.billToCountry'))).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.openCompanyForBillTo') }));
    expect((await screen.findByTestId('location')).textContent).toBe('/crm/companies/4');
  });
});
```

### 2-12. frontend/src/components/CommerceNavigationButtonMigration.test.tsx（丸ごと置き換え）

```tsx
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InventoryPage from '../pages/inventory/InventoryPage';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import InvoiceDetailPage from '../pages/invoice-detail/InvoiceDetailPage';
import ProductEditPage from '../pages/products/ProductEditPage';
import ProductsPage from '../pages/products/ProductsPage';
import QuoteCreatePage from '../pages/quote-create/QuoteCreatePage';
import QuotesPage from '../pages/quotes/QuotesPage';
import en from '../locales/en.json';
import { queryClient } from '../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
let permissions: string[] = [];
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }
function wrap(node: React.ReactNode, entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}<Location /></MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }
function deferred() { let resolve!: (v: unknown) => void; let reject!: (e: Error) => void; const promise = new Promise((r, j) => { resolve = r; reject = j; }); return { promise, resolve, reject }; }

beforeEach(async () => {
  vi.resetAllMocks(); permissions = ['products.create', 'quotes.create', 'invoices.void']; instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions };
    if (url === '/products/tcg-types') return [];
    if (url === '/products/attribute-options') return {};
    if (url.startsWith('/products?')) return [];
    if (url === '/quotes') return [];
    if (url === '/companies?per_page=100') return [];
    // invoice-create-portfolio 便R5: 請求書の作成画面は在庫の道を 1 回読む
    if (url === '/invoices/draft-inventory') return { categories: [], items: [] };
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected post'); });
  mock.patch.mockResolvedValue({});
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('commerce navigation Button migration contracts', () => {
  it('paginates inventory with exact GETs and disabled pending boundaries', async () => {
    const row = { id: '1', product_id: 2, product_name: 'Card', name_en: null, category: null, mark: null, condition: 'new', unit: null, offer_type: 'in_stock', status: 'in_stock', note_ja: null, ship_ja: null, merged_count: 1, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: 'Supplier', unit_price: 10, quantity: 1, work_code: 'pokemon_booster_box', offered_at: '', release_date: null };
    const page1Url = '/inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=false&fresh_only=true&work_code=pokemon_booster_box';
    const page2Url = '/inventory?page=2&per_page=50&sort=release_date&order=desc&merge_same_post=false&fresh_only=true&work_code=pokemon_booster_box';
    const page2 = deferred();
    mock.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions };
      if (url === '/products/tcg-types') return [];
      if (url === page1Url) return { items: [row], total: 51, page: 1, per_page: 50 };
      if (url === page2Url) return page2.promise;
      throw new Error(`Unexpected GET ${url}`);
    });
    render(wrap(<InventoryPage />));
    const next = await screen.findByTestId('inventory-next') as HTMLButtonElement;
    const prev = screen.getByTestId('inventory-prev') as HTMLButtonElement;
    expect(prev.disabled).toBe(true); await waitFor(() => expect(next.disabled).toBe(false));
    fireEvent.click(next);
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/inventory?page=2&per_page=50&sort=release_date&order=desc&merge_same_post=false&fresh_only=true&work_code=pokemon_booster_box'));
    expect(next.disabled).toBe(true); expect(prev.disabled).toBe(true);
    await act(async () => page2.resolve({ items: [row], total: 51, page: 2, per_page: 50 }));
    await waitFor(() => expect((screen.getByTestId('inventory-prev') as HTMLButtonElement).disabled).toBe(false));
    expect((screen.getByTestId('inventory-next') as HTMLButtonElement).disabled).toBe(true);
    const page2Reads = mock.get.mock.calls.filter(c => c[0] === page2Url).length;
    fireEvent.click(screen.getByTestId('inventory-next'));
    expect(mock.get.mock.calls.filter(c => c[0] === page2Url)).toHaveLength(page2Reads);
    const page1Reads = mock.get.mock.calls.filter(c => c[0] === page1Url).length;
    fireEvent.click(screen.getByTestId('inventory-prev'));
    await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === page1Url)).toHaveLength(page1Reads + 1));
  });

  it('closes invoice void UI with zero writes', async () => {
    const invoice = { id: 3, invoice_number: 'INV-3', quote_id: null, company_id: 1, currency: 'USD', subtotal: 1, shipping_fee: 0, tax_amount: 0, total_amount: 1, exchange_rate_jpy: null, exchange_rate_usd: null, amount_jpy: null, amount_usd: null, payment_method: null, status: 'draft', branch_number: null, erp_key: null, issued_at: null, due_date: null, paid_at: null, voided_at: null, void_reason: null, notes: null, created_at: '', items: [], ship_to_snapshot: null, bill_to_snapshot: null, duty_amount: null, fx_rate_snapshot: null, paypal_order_id: null, paypal_approval_url: null, payment_fee: null, paypal_invoicer_view_url: null, paypal_copy_pdf_at: null };
    mock.get.mockImplementation(async (url: string) => { if (url === '/me/permissions') return { permissions }; if (url === '/invoices/3') return invoice; if (url === '/invoices/3/paypal-disputes') return []; throw new Error(`Unexpected GET ${url}`); });
    render(routed(<InvoiceDetailPage />, '/invoices/:id', ['/invoices/3']));
    fireEvent.click(await screen.findByRole('button', { name: tr('invoices.voidAction') }));
    expect(screen.getByPlaceholderText(tr('invoices.voidReasonPlaceholder'))).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: tr('common.cancel') }));
    expect(screen.queryByPlaceholderText(tr('invoices.voidReasonPlaceholder'))).toBeNull(); expect(mock.post).not.toHaveBeenCalled();
  });

  it.each([
    ['invoice profile', <InvoiceCreatePage />, '/invoices/new', ['/invoices/new'], 'nav.tenantProfile', '/management-center/tenant-profile'],
    ['product back', <ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new'], 'common.cancel', '/before'],
    ['new product', <ProductsPage />, '/admin/products', ['/admin/products'], 'products.newProduct', '/admin/products/new'],
    ['quote cancel', <QuoteCreatePage />, '/quotes/new', ['/quotes/new'], 'common.cancel', '/quotes'],
    ['new quote', <QuotesPage />, '/quotes', ['/quotes'], 'quotes.newQuote', '/quotes/new'],
  ] as const)('%s preserves exact navigation', async (_name, Page, path, entries, label, destination) => {
    render(routed(Page, path, [...entries]));
    fireEvent.click(await screen.findByRole('button', { name: tr(label) }));
    expect((await screen.findByTestId('location')).textContent).toBe(destination);
  });

  it('cancels invoice creation to the exact invoices route', async () => {
    // invoice-create-portfolio 便R5: 「在庫表から／見積から」の切り替えは無くなった（p8）。キャンセルは最初から出ている
    render(routed(<InvoiceCreatePage />, '/invoices/new', ['/invoices/new']));
    fireEvent.click(await screen.findByRole('button', { name: tr('common.cancel') }));
    expect((await screen.findByTestId('location')).textContent).toBe('/invoices');
  });

  it('blocks ProductEdit cancel navigation while a save is pending', async () => {
    const pending = deferred(); mock.post.mockReturnValue(pending.promise);
    render(routed(<ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new']));
    await screen.findByTestId('product-edit-save'); fireEvent.change(document.querySelector('input[required]')!, { target: { value: 'Product' } });
    fireEvent.click(screen.getByTestId('product-edit-save'));
    const cancel = screen.getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement;
    await waitFor(() => expect(cancel.disabled).toBe(true)); fireEvent.click(cancel);
    expect(screen.queryByTestId('location')).toBeNull(); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => pending.reject(new Error('Save failed'))); expect(await screen.findByText('Save failed')).toBeTruthy();
  });

  it('opens and cancels the FedEx dialog without quote or rate writes', async () => {
    render(wrap(<QuoteCreatePage />));
    fireEvent.click(screen.getByTestId('fedex-estimate-btn'));
    const dialog = screen.getByRole('dialog'); expect(within(dialog).getByText(tr('fedexRateModal.title'))).toBeTruthy();
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') }));
    expect(screen.queryByRole('dialog')).toBeNull(); expect(mock.post).not.toHaveBeenCalled();
  });
});
```

### 2-13. frontend/src/components/CommerceSubmitButtonMigration.test.tsx（丸ごと置き換え）

```tsx
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import ProductEditPage from '../pages/products/ProductEditPage';
import QuoteCreatePage from '../pages/quote-create/QuoteCreatePage';
import en from '../locales/en.json';
import { queryClient } from '../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../lib/api')>()), api: mock }));
let instance = createInstance();
function Location() { const location = useLocation(); return <output data-testid="location">{location.pathname}</output>; }
function wrap(node: React.ReactNode, entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}</MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }
function deferred() { let resolve!: (value: unknown) => void; let reject!: (error: Error) => void; const promise = new Promise((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }

const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
const productPayload = {
  name_ja: 'Product', name_en: null, product_kind: 'TCG', set_type: null,
  category: null, mark: null, status: 'active', unit_price: null, quantity: 0, weight: null,
  notes: null, release_date: null, jan_code: null, card_number: null, expansion_code: null,
  rarity: null, language: null, unit_price_usd: null, unit_price_eur: null, image_url: null,
  boxes_per_case: null, packs_per_box: null, box_weight_kg: null, case_weight_kg: null,
  volume_weight: null, moq: null, hs_code: '9504400000', material: 'Paper', item: 'Playing card',
  required_output_value: null, search_keywords: null, exclude_keywords: null, related_series: null,
};
const productOptions = {
  product_kind: [{ code: 'kind', label_ja: 'Kind', label_en: null }],
  set_type: [{ code: 'set', label_ja: 'Set', label_en: null }],
  rarity: [{ code: 'rare', label_ja: 'Rare', label_en: null }],
  language: [{ code: 'en', label_ja: 'English', label_en: null }],
  hs_code: [{ code: 'hs', label_ja: 'HS', label_en: null }],
  item: [{ code: 'item', label_ja: 'Item', label_en: null }],
  material: [{ code: 'material', label_ja: 'Material', label_en: null }],
};
const nonDefaultProductPayload = { ...productPayload, name_ja: 'Product', name_en: 'Product EN', product_kind: 'Kind', set_type: 'Set', category: 'Category', mark: 'M', status: 'discontinued', unit_price: 12.5, quantity: 7, weight: 0.75, notes: 'memo', release_date: '2026-09-28', jan_code: 'JAN-1', card_number: 'CARD-1', expansion_code: 'EXP-1', rarity: 'Rare', language: 'en', unit_price_usd: 11.5, unit_price_eur: 10.5, image_url: 'https://example.com/p.png', boxes_per_case: 24, packs_per_box: 12, box_weight_kg: 1.5, case_weight_kg: 3.5, volume_weight: 4.5, moq: 6, hs_code: 'HS', material: 'Material', item: 'Item', required_output_value: 'Required', search_keywords: 'search', exclude_keywords: 'exclude', related_series: 'Series' };
const visibleProductValues = ['Product', 'Product EN', 'Kind', 'M', 'Set', '2026-09-28', 'CARD-1', 'EXP-1', 'Rare', 'en', '12.5', 'https://example.com/p.png', 'discontinued', 'memo', '24', '12', '3.5', '1.5', '4.5', '6', 'HS', 'Item', 'Material'];
function fillVisibleProductForm() {
  const form = screen.getByTestId('product-edit-form');
  const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea'));
  expect(controls).toHaveLength(23); controls.forEach((control, index) => fireEvent.change(control, { target: { value: visibleProductValues[index] } }));
}

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/companies?per_page=100') return [company];
    // invoice-create-portfolio 便R5: 請求書の作成画面は在庫の道を 1 回読む
    if (url === '/invoices/draft-inventory') return { categories: [], items: [] };
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === '/products/tcg-types') return [{ code: 'pokemon', name_ja: 'Pokemon' }];
    if (url === '/products/attribute-options') return productOptions;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('commerce submit Button migration contracts', () => {
  it.each([
    // invoice-create-portfolio 便R5: 請求書の行は選ぶ欄（カテゴリ・商品・状態）と数の欄 2 つ（数量・単価）。空の行は数の欄も空
    ['invoice', <InvoiceCreatePage />, 'invoice-add-row', 'invoice-item-row-', [], ['', '']],
    ['quote', <QuoteCreatePage />, 'quote-add-blank', 'quote-item-row-', ['', '', '', ''], ['1', '0', '']],
  ] as const)('%s addItem appends one blank row per click with zero writes', async (_name, page, buttonId, rowPrefix, textValues, numberValues) => {
    render(wrap(page));
    const button = await screen.findByTestId(buttonId) as HTMLButtonElement;
    const count = () => document.querySelectorAll(`tr[data-testid^="${rowPrefix}"]`).length;
    const before = count();
    fireEvent.click(button); expect(count()).toBe(before + 1);
    const row = screen.getByTestId(`${rowPrefix}${before}`); const inputs = within(row).queryAllByRole('textbox'); const numbers = within(row).getAllByRole('spinbutton');
    expect(inputs.map(input => (input as HTMLInputElement).value)).toEqual([...textValues]); expect(numbers.map(input => (input as HTMLInputElement).value)).toEqual([...numberValues]);
    fireEvent.click(button); expect(count()).toBe(before + 2);
    expect(button.disabled).toBe(false); expect(button.getAttribute('aria-busy')).toBeNull();
    expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled();
  });

  it('Quote submit enforces contact and item guards without writing', async () => {
    render(wrap(<QuoteCreatePage />));
    const submit = await screen.findByRole('button', { name: String(instance.t('quotes.saveDraft')) });
    fireEvent.submit(submit.closest('form')!);
    expect(await screen.findByText(String(instance.t('companyContactSelector.contactRequired')))).toBeTruthy();
    expect(mock.post).not.toHaveBeenCalled();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: '4' } });
    await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } });
    fireEvent.submit(submit.closest('form')!);
    expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy();
    expect(mock.post).not.toHaveBeenCalled();
  });

  it.each([
    ['empty name', 'name', ''], ['zero price', 'price', '0'], ['zero quantity', 'quantity', '0'],
  ] as const)('Quote item handler rejects %s with zero POST', async (_label, field, value) => {
    render(wrap(<QuoteCreatePage />)); const selects = await screen.findAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } }); await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } });
    const row = screen.getByTestId('quote-item-row-0'); const name = within(row).getByTestId('quote-item-row-0-name'); const numbers = within(row).getAllByRole('spinbutton'); fireEvent.change(name, { target: { value: field === 'name' ? value : 'Card' } }); fireEvent.change(numbers[0], { target: { value: field === 'quantity' ? value : '1' } }); fireEvent.change(numbers[1], { target: { value: field === 'price' ? value : '10' } });
    if (field === 'quantity') { fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) })); expect(mock.post).not.toHaveBeenCalled(); }
    fireEvent.submit(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }).closest('form')!); expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy(); expect(mock.post).not.toHaveBeenCalled();
  });

  it('Quote submit preserves the exact payload, pending lock, failure state, retry, and success route', async () => {
    const first = deferred(); mock.post.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    render(routed(<QuoteCreatePage />, '/quotes/new', ['/quotes/new']));
    const selects = await screen.findAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } });
    await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } }); fireEvent.change(selects[2], { target: { value: 'EUR' } });
    const row = screen.getByTestId('quote-item-row-0'); fireEvent.change(within(row).getByTestId('quote-item-row-0-name'), { target: { value: 'Card' } });
    const numbers = within(row).getAllByRole('spinbutton'); fireEvent.change(numbers[1], { target: { value: '12.5' } }); fireEvent.change(numbers[2], { target: { value: '0.25' } });
    fireEvent.change(screen.getByTestId('shipping-fee-input'), { target: { value: '3' } });
    fireEvent.change(screen.getByText(String(instance.t('quotes.tax'))).parentElement!.querySelector('input')!, { target: { value: '7' } }); fireEvent.change(screen.getByText(String(instance.t('common.notes'))).parentElement!.querySelector('input')!, { target: { value: 'memo' } });
    const submit = screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }) as HTMLButtonElement;
    fireEvent.click(submit);
    const expected = { company_id: 4, contact_id: 5, currency: 'EUR', shipping_fee: 3, tax_amount: 7, notes: 'memo', items: [{ product_id: null, product_name: 'Card', name_en: null, condition: null, unit: null, quantity: 1, unit_price: 12.5, weight: 0.25 }] };
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/quotes', expected); expect(submit.disabled).toBe(true); fireEvent.click(submit); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Quote save failed'))); expect(await screen.findByText('Quote save failed')).toBeTruthy();
    expect((screen.getByTestId('quote-item-row-0-name') as HTMLInputElement).value).toBe('Card'); expect(submit.disabled).toBe(false);
    fireEvent.click(submit); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2)); expect(mock.post.mock.calls[1]).toEqual(['/quotes', expected]);
    expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });

  it('Quote submit maps empty fee, tax, and notes to null', async () => {
    mock.post.mockResolvedValue({}); render(routed(<QuoteCreatePage />, '/quotes/new', ['/quotes/new'])); const selects = await screen.findAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } }); await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } }); const row = screen.getByTestId('quote-item-row-0'); fireEvent.change(within(row).getByTestId('quote-item-row-0-name'), { target: { value: 'Card' } }); fireEvent.change(within(row).getAllByRole('spinbutton')[1], { target: { value: '10' } }); fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) })); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1)); expect(mock.post).toHaveBeenCalledExactlyOnceWith('/quotes', { company_id: 4, contact_id: 5, currency: 'USD', shipping_fee: null, tax_amount: null, notes: null, items: [{ product_id: null, product_name: 'Card', name_en: null, condition: null, unit: null, quantity: 1, unit_price: 10, weight: null }] }); expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });

  it('Product create sends all 33 payload keys, blocks duplicate pending writes, preserves failure state, and retries', async () => {
    expect(Object.keys(productPayload)).toHaveLength(33); const first = deferred(); mock.post.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    render(routed(<ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new']));
    const save = await screen.findByTestId('product-edit-save') as HTMLButtonElement; fillVisibleProductForm(); const expected = { ...nonDefaultProductPayload, category: null, quantity: 0, weight: null, jan_code: null, unit_price_usd: null, unit_price_eur: null, required_output_value: null, search_keywords: null, exclude_keywords: null, related_series: null }; expect(Object.keys(expected)).toHaveLength(33); fireEvent.click(save);
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/products', expected); await waitFor(() => expect(save.disabled).toBe(true)); const cancel = screen.getByRole('button', { name: String(instance.t('common.cancel')) }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(save); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Product save failed'))); expect(await screen.findByText('Product save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Product'); expect(save.disabled).toBe(false);
    expect(cancel.disabled).toBe(false); fireEvent.click(save); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2)); expect(mock.post.mock.calls[1]).toEqual(['/products', expected]); expect((await screen.findByTestId('location')).textContent).toBe('/before');
  });

  it('Product required and edit-loading guards write zero', async () => {
    render(routed(<ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new'])); const save = await screen.findByTestId('product-edit-save'); fireEvent.click(save); expect(mock.post).not.toHaveBeenCalled(); cleanup();
    const load = deferred(); mock.get.mockImplementation(async (url: string) => { if (url === '/products/tcg-types') return []; if (url === '/products/attribute-options') return {}; if (url === '/products/9') return load.promise; throw new Error(`Unexpected GET ${url}`); });
    render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); const editSave = await screen.findByTestId('product-edit-save') as HTMLButtonElement; expect(editSave.disabled).toBe(true); fireEvent.click(editSave); expect(mock.patch).not.toHaveBeenCalled(); await act(async () => load.reject(new Error('load failed'))); expect(await screen.findByText('load failed')).toBeTruthy();
  });

  it('Product edit PATCHes the exact 33-key payload, locks pending, preserves failure state, and retries', async () => {
    const fixture = { id: 9, product_code: null, ...nonDefaultProductPayload, name_ja: 'Existing', created_at: '', updated_at: '', is_archived: false, archived_at: null, supplier_default_id: null, display_order: null };
    const first = deferred(); mock.get.mockImplementation(async (url: string) => { if (url === '/products/tcg-types') return []; if (url === '/products/attribute-options') return {}; if (url === '/products/9') return fixture; throw new Error(`Unexpected GET ${url}`); }); mock.patch.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); await waitFor(() => expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Existing'));
    const form = screen.getByTestId('product-edit-form'); const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea')); fireEvent.change(controls[0], { target: { value: 'Edited' } }); fireEvent.change(controls[10], { target: { value: '99.25' } });
    const save = screen.getByTestId('product-edit-save') as HTMLButtonElement; fireEvent.click(save); const expected = { ...nonDefaultProductPayload, name_ja: 'Edited', unit_price: 99.25 }; expect(Object.keys(expected)).toHaveLength(33); await waitFor(() => expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/products/9', expected)); expect(save.disabled).toBe(true); const cancel = screen.getByRole('button', { name: String(instance.t('common.cancel')) }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(save); expect(mock.patch).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Edit save failed'))); expect(await screen.findByText('Edit save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Edited'); expect(save.disabled).toBe(false); expect(cancel.disabled).toBe(false);
    fireEvent.click(save); await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(2)); expect(mock.patch.mock.calls[1]).toEqual(['/products/9', expected]); expect((await screen.findByTestId('location')).textContent).toBe('/before');
  });
});
```

### 2-14. frontend/src/lib/query/batch3cPages.test.tsx（丸ごと置き換え）

```tsx
/**
 * ADR-1054 段 3 の 3 回目: 本物の画面の試験（Q1）。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧と詳しい画面は見出しの横に回る印・裏で取り直す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import FollowUpsPage from "../../pages/dashboard/FollowUpsPage";
import FunnelReasonsPage from "../../pages/dashboard/FunnelReasonsPage";
import FunnelRevenuePage from "../../pages/dashboard/FunnelRevenuePage";
import OwnInventoryPage from "../../pages/inventory/OwnInventoryPage";
import InvoiceCreatePage from "../../pages/invoice-create/InvoiceCreatePage";
import InvoicesPage from "../../pages/invoices/InvoicesPage";
import SupplierEditPage from "../../pages/suppliers/SupplierEditPage";
import TeamEditPage from "../../pages/teams/TeamEditPage";
import { api } from "../api";
import { QueryAuthSync } from "./QueryAuthSync";
import { queryClient } from "./apiQuery";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: auth.user, loading: false }),
}));
vi.mock("../auth/selfAuth", () => ({
  getAccessToken: async () => "test-token",
  expireSession: vi.fn(),
  selfRefresh: vi.fn(),
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true, loading: false }) }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3bPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（TeamEditPage・SupplierEditPage の型・backend/app/schemas/own_inventory.py:42-56・
// InvoicesPage.tsx:21-34・InvoiceCreatePage.tsx:30-38・api/funnel.ts:42-93）の欄
const team = { id: 7, name: "Fixture Team", leader_id: null, description: null };
const supplier = { id: 63, name: "Fixture supplier", contact_name: null, email: null, phone: null, address: null, notes: null };
const ownRow = { id: 1, tenant_id: 1, product_id: 77, physical_qty: 2, reserved_qty: 0, available_qty: 2, unit_price: null, condition: "Fixture Cond", status: "in_stock", note_ja: null, note_en: null, antique_ledger_id: null, created_at: "", updated_at: "" };
const invoice = { id: 7, invoice_number: "INV-7", company_id: 4, currency: "USD", total_amount: 10, amount_jpy: null, status: "draft", issued_at: null, due_date: null, paid_at: null, created_at: "" };
// invoice-create-portfolio 便R5: 請求書の作成画面は在庫の道を読み、カテゴリの名前を選ぶ欄に出す（useDraftInventory.ts の型）
const draftInventory = { categories: [{ code: "FX", name_ja: "Fixture Category" }], items: [] };
const followUps = { items: [{ customer_id: 5, name: "Fixture Customer", segment: "order_stopped", days: 3, last_order_at: null, last_contact_at: null, assignee: "Fixture Assignee" }] };
const revenue = { revenue: { target: 2000000, actual: 1234567, pace: "on_track" }, split: { new: 1, repeat: 1 }, new_customers: { target: 1, actual: 1 }, active_existing_customers: 1, gross_margin: { amount: 1, uncosted_orders: 0 } };
const reasons = { reasons: [{ label: "Fixture Reason", primary_count: 1, secondary_count: 0 }], memos: [] };

const fixtures: Record<string, unknown> = {
  "/teams/7": team,
  "/suppliers/63": supplier,
  "/own-inventory?page=1&per_page=20": [ownRow],
  "/invoices": [invoice],
  "/invoices/draft-inventory": draftInventory,
  "/analytics/follow-ups?": followUps,
};
// 売上と理由は月で path が変わるので頭で見分ける。画面の中の部品が別に取る物（会社の選び欄など）は空の一覧で返す
const answer = (path: string) =>
  (path in fixtures
    ? fixtures[path]
    : path.startsWith("/analytics/revenue-summary?")
      ? revenue
      : path.startsWith("/analytics/reasons?")
        ? reasons
        : []) as never;

type Case = {
  name: string; Page: ComponentType; route: string; at: string;
  path: string | RegExp; text: string; value: boolean; spinner: boolean;
};
const cases: Case[] = [
  { name: "supplier edit", Page: SupplierEditPage, route: "/suppliers/:id/edit", at: "/suppliers/63/edit", path: "/suppliers/63", text: "Fixture supplier", value: true, spinner: false },
  { name: "own inventory", Page: OwnInventoryPage, route: "/own-inventory", at: "/own-inventory", path: "/own-inventory?page=1&per_page=20", text: "Fixture Cond", value: false, spinner: true },
  { name: "follow ups", Page: FollowUpsPage, route: "/dashboard/follow-ups", at: "/dashboard/follow-ups", path: "/analytics/follow-ups?", text: "Fixture Customer", value: false, spinner: true },
  { name: "invoice create", Page: InvoiceCreatePage, route: "/invoices/new", at: "/invoices/new", path: "/invoices/draft-inventory", text: "Fixture Category", value: false, spinner: false },
  { name: "invoices", Page: InvoicesPage, route: "/invoices", at: "/invoices", path: "/invoices", text: "INV-7", value: false, spinner: true },
  { name: "team edit", Page: TeamEditPage, route: "/teams/:id/edit", at: "/teams/7/edit", path: "/teams/7", text: "Fixture Team", value: true, spinner: false },
  { name: "revenue", Page: FunnelRevenuePage, route: "/dashboard/revenue", at: "/dashboard/revenue", path: /^\/analytics\/revenue-summary\?month=\d{4}-\d{2}$/, text: "¥1,234,567", value: false, spinner: true },
  { name: "reasons", Page: FunnelReasonsPage, route: "/dashboard/reasons", at: "/dashboard/reasons", path: /^\/analytics\/reasons\?type=won&month=\d{4}-\d{2}$/, text: "Fixture Reason", value: false, spinner: true },
];

function Tree({ c }: { c: Pick<Case, "Page" | "route" | "at"> }) {
  const Page = c.Page;
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      <MemoryRouter initialEntries={[c.at]}>
        <Routes><Route path={c.route} element={<Page />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// 編集の画面は欄の中の値で、ほかは文字で見分ける
const shown = (c: Case) => (c.value ? screen.queryAllByDisplayValue(c.text) : screen.queryAllByText(c.text));
const found = (c: Case) => (c.value ? screen.findAllByDisplayValue(c.text) : screen.findAllByText(c.text));
const calledPath = (c: Case) => (typeof c.path === "string" ? c.path : expect.stringMatching(c.path));

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => { throw new Error("Unexpected real network request"); }));
});

afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  auth.user = { uid: "uid-A" };
});

describe("revisit shows the copy first (Q1)", () => {
  it.each(cases)("$name shows the previous content at once on revisit", async (c) => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    const first = render(<Tree c={c} />);
    await found(c);
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree c={c} />);
    expect(shown(c).length).toBeGreaterThan(0);
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    if (c.spinner) {
      await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());
    }
    await waitFor(() => expect(spy).toHaveBeenCalledWith(calledPath(c)));
  });
});
```

### 2-15. frontend/src/pages/quote-create/quoteDraft.ts（Edit・ちょうど1か所）

変更前:
```ts
  zero_stock_warning?: boolean;
```
変更後:
```ts
  zero_stock_warning?: boolean;
  /** 画面だけの項目（invoice-create-portfolio design-v2 §3-8）。保存には送らない */
  category_code?: string | null;
  stock_limit?: number | null;
  price_yen?: number | null;
  price_edited?: boolean;
```

### 2-16. frontend/src/lib/invoiceDraftContext.ts（Edit・ちょうど1か所）

変更前:
```ts
  phone: string | null;
```
変更後:
```ts
  phone: string | null;
  // サーバーの DraftContextAddress（backend/app/schemas/invoice.py）が返す発送先の残りの欄
  recipient_name?: string | null;
  email?: string | null;
  tax_id?: string | null;
  address_line_1?: string | null;
  address_line_2?: string | null;
  address_line_3?: string | null;
  country_name?: string | null;
```

### 2-17. frontend/src/locales/ja.json（Edit・ちょうど1か所）

変更前:
```json
    "clear": "入力を全部消す"
  },
  "invoices": {
```
変更後:
```json
    "clear": "入力を全部消す",
    "clearConfirmTitle": "入力を全部消しますか",
    "clearConfirmMessage": "商品の行・届け先・送料・メモを空に戻します。消した入力は元に戻せません。",
    "clearConfirmYes": "はい、消す",
    "createBlocked": "請求書をまだ作れません",
    "createNotReady": "送料・支払方法・合計がそろうまで作れません。上の欄を確かめてください",
    "fedexLiveUnavailable": "FedEx の今の値段を取れなかったため、登録済みの表の値段を出しています",
    "previewErrorTitle": "合計の計算に失敗しました。少し待ってもう一度お試しください",
    "rowsNotReady": "印の付いた行を直してください（状態・重さ・単価）",
    "sectionItems": "商品一覧",
    "shippingLoading": "送料を調べています",
    "shippingMemo": "発送メモ",
    "shippingNeedsWeight": "商品と状態を選ぶと、重さから送料の候補が出ます",
    "shippingQuoteError": "送料を調べられませんでした。少し待ってもう一度お試しください",
    "shippingRateLine": "{{carrier}} {{service}}：{{fee}}",
    "sourceLive": "ライブ",
    "sourceStatic": "静的",
    "totalWeightLine": "総重量 {{value}} kg",
    "transitDays": "目安 {{count}} 日",
    "fieldCustomer": "顧客名",
    "fieldRecipient": "受取人",
    "fieldPhone": "電話番号",
    "fieldEmail": "メール",
    "fieldTaxId": "税番号",
    "fieldCountry": "国",
    "fieldAddress1": "住所1",
    "fieldAddress2": "住所2",
    "fieldAddress3": "住所3",
    "fieldCity": "市区町村",
    "fieldState": "州・都道府県",
    "fieldZip": "郵便番号"
  },
  "lineItems": {
    "colNo": "#",
    "colCategory": "カテゴリ",
    "colProduct": "商品",
    "colState": "状態",
    "colQuantity": "数量",
    "colWeight": "重さ",
    "colUnitPrice": "単価",
    "colSubtotal": "小計",
    "colRemove": "削除",
    "categoryPlaceholder": "カテゴリ",
    "categoryAria": "{{n}}行目のカテゴリ",
    "productAria": "{{n}}行目の商品",
    "productPlaceholder": "商品を探す",
    "productNoResults": "在庫のある商品が見つかりません",
    "productLoading": "読み込み中",
    "statePlaceholder": "状態を選ぶ",
    "stateMissing": "状態を選んでください",
    "stateAria": "{{n}}行目の状態",
    "stockLimit": "在庫は {{count}} まで",
    "quantityAria": "{{n}}行目の数量",
    "weightMissing": "重さが未登録です。商品の画面で重さを入れてください",
    "weightKg": "{{value}} kg",
    "priceMissing": "単価を入れてください",
    "priceAria": "{{n}}行目の単価",
    "removeRow": "{{n}}行目を消す",
    "removeRowMark": "×",
    "inventoryError": "在庫を読めませんでした。画面を読み込み直してください",
    "addRow": "行を追加",
    "maxRows": "行は {{count}} 行までです"
  },
  "invoices": {
```

### 2-18. frontend/src/locales/en.json（Edit・ちょうど1か所）

変更前:
```json
    "clear": "Clear all input"
  },
  "invoices": {
```
変更後:
```json
    "clear": "Clear all input",
    "clearConfirmTitle": "Clear all inputs?",
    "clearConfirmMessage": "Product rows, ship-to, shipping and memo will be emptied. This cannot be undone.",
    "clearConfirmYes": "Yes, clear",
    "createBlocked": "The invoice cannot be created yet",
    "createNotReady": "The invoice cannot be created until shipping, payment and totals are ready. Please check the fields above",
    "fedexLiveUnavailable": "Live FedEx rates are unavailable, so registered table rates are shown",
    "previewErrorTitle": "Failed to calculate totals. Please wait a moment and try again",
    "rowsNotReady": "Please fix the marked rows (state, weight, unit price)",
    "sectionItems": "Products",
    "shippingLoading": "Checking shipping rates",
    "shippingMemo": "Shipping memo",
    "shippingNeedsWeight": "Choose products and states to see shipping options by weight",
    "shippingQuoteError": "Could not get shipping rates. Please wait a moment and try again",
    "shippingRateLine": "{{carrier}} {{service}}: {{fee}}",
    "sourceLive": "Live",
    "sourceStatic": "Static",
    "totalWeightLine": "Total weight {{value}} kg",
    "transitDays": "About {{count}} days",
    "fieldCustomer": "Customer",
    "fieldRecipient": "Recipient",
    "fieldPhone": "Phone",
    "fieldEmail": "Email",
    "fieldTaxId": "Tax ID",
    "fieldCountry": "Country",
    "fieldAddress1": "Address line 1",
    "fieldAddress2": "Address line 2",
    "fieldAddress3": "Address line 3",
    "fieldCity": "City",
    "fieldState": "State / Province",
    "fieldZip": "ZIP / Postal code"
  },
  "lineItems": {
    "colNo": "#",
    "colCategory": "Category",
    "colProduct": "Product",
    "colState": "State",
    "colQuantity": "Qty",
    "colWeight": "Weight",
    "colUnitPrice": "Unit price",
    "colSubtotal": "Subtotal",
    "colRemove": "Remove",
    "categoryPlaceholder": "Category",
    "categoryAria": "Category of row {{n}}",
    "productAria": "Product of row {{n}}",
    "productPlaceholder": "Search products",
    "productNoResults": "No products in stock found",
    "productLoading": "Loading",
    "statePlaceholder": "Choose state",
    "stateMissing": "Please choose a state",
    "stateAria": "State of row {{n}}",
    "stockLimit": "Up to {{count}} in stock",
    "quantityAria": "Quantity of row {{n}}",
    "weightMissing": "Weight is not registered. Please add it on the product screen",
    "weightKg": "{{value}} kg",
    "priceMissing": "Please enter a unit price",
    "priceAria": "Unit price of row {{n}}",
    "removeRow": "Remove row {{n}}",
    "removeRowMark": "×",
    "inventoryError": "Could not load inventory. Please reload the page",
    "addRow": "Add row",
    "maxRows": "Up to {{count}} rows"
  },
  "invoices": {
```

## 3. 手順（1つずつ流し、出力を報告に書く）

手順1 作業場所
    cd /home/user/salesanchor && git fetch origin main
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-r5-page
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-r5-page
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && git merge-base --is-ancestor origin/main HEAD; echo "main exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && git rev-parse HEAD
  期待: 2行目の出力が空（空でなければ `BLOCKED: 手順1 枝が既にある`）。4行目に `worktrees/salesanchor/release-invoice-portfolio-r5-page` が出る。5行目 `main exit=0`。

手順2 実装前点検 P1〜P6
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && git hash-object frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx frontend/src/pages/invoice-create/InvoiceShipToSection.tsx frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx frontend/src/components/BillToCountryGuidance.test.tsx frontend/src/components/CommerceNavigationButtonMigration.test.tsx frontend/src/components/CommerceSubmitButtonMigration.test.tsx frontend/src/lib/query/batch3cPages.test.tsx
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && ls frontend/src/pages/quote-create | grep -c -E "^(LineItemsTable|lineItems|useDraftInventory|useDraftShippingQuotes)"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && grep -c '^  zero_stock_warning?: boolean;$' frontend/src/pages/quote-create/quoteDraft.ts
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && grep -c '^  phone: string | null;$' frontend/src/lib/invoiceDraftContext.ts
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && python3 -c "import json; print('lineItems' in json.load(open('frontend/src/locales/ja.json')), 'lineItems' in json.load(open('frontend/src/locales/en.json')))"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && ls frontend/src/components/SectionCard.tsx frontend/src/components/ReadOnlyField.tsx frontend/src/components/ThreeColumn.tsx frontend/src/components/TotalsBox.tsx | grep -c tsx
  期待（命令の順）: 1行目は P1 の9つの指紋がその順に出る。続いて 0、1、1、`False False`、4。

手順3 §2 の変更をする（2-1〜2-14 は Write ツール（2-6〜2-14 は先に Read）、2-15〜2-18 は Edit ツール。§2 のコードの囲み（```）の中身だけを書く）

手順4 道具を入れる
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm ci --no-audit --no-fund 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && set -o pipefail && npm run generate:api-types 2>&1 | tail -3; echo "gen exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && ls src/api/generated/schema.d.ts
  期待: 2行目 `gen exit=0`。3行目に `src/api/generated/schema.d.ts` が出る（生成物は .gitignore で記録の対象外）。外れたら `BLOCKED: 手順4 型の生成`。

手順5 形と試験（どれも作業場所の frontend で流す）
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/quote-create/lineItems.test.ts src/pages/invoice-create/InvoiceCreatePage.test.tsx src/components/AllLegacyButtonDynamicMigration.test.tsx src/components/BillToCountryGuidance.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx src/components/CommerceSubmitButtonMigration.test.tsx src/lib/query/batch3cPages.test.tsx src/pages/quote-create/quoteDraft.test.ts 2>&1 | tail -15
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && set -o pipefail && npx tsc -p tsconfig.json 2>&1 | tail -15; echo "tsc exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && set -o pipefail && npx eslint --max-warnings=0 src/pages/quote-create/LineItemsTable.tsx src/pages/quote-create/lineItems.ts src/pages/quote-create/lineItems.test.ts src/pages/quote-create/useDraftInventory.ts src/pages/quote-create/useDraftShippingQuotes.ts src/pages/invoice-create/InvoiceCreatePage.tsx src/pages/invoice-create/InvoiceCreatePage.test.tsx src/pages/invoice-create/InvoicePaymentTotalsSection.tsx src/pages/invoice-create/InvoiceShipToSection.tsx src/components/AllLegacyButtonDynamicMigration.test.tsx src/components/BillToCountryGuidance.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx src/components/CommerceSubmitButtonMigration.test.tsx src/lib/query/batch3cPages.test.tsx src/pages/quote-create/quoteDraft.ts src/lib/invoiceDraftContext.ts 2>&1 | tail -15; echo "eslint exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm run check:i18n-missing-keys 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm run check:error-text-next-action 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm run check:page-size 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm run check:page-layout 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm run check:page-folder 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm run check:loading-clear 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm run check:status-direct-writes 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && npm run check:jsx-emoji 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page/frontend && node scripts/check-css-var-fallbacks.js 2>&1 | tail -5; echo "css-var exit=$?"
  期待: 1行目は failed 0（8ファイルの試験がすべて passed。本数はそのまま書く）。2行目 `tsc exit=0`（型の誤り 0）。3行目 `eslint exit=0` で、誤りも警告も 0（記録の前の自動点検が `eslint --max-warnings=0` で警告 1 件でも止めるため、ここで同じ条件で確かめる）。最後の行は `css-var exit=0`。4行目以降はどれも誤りなしで終わる（✅ や 0 件の表示。❌・終了の失敗が出ない）。

手順6 変えたファイル
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && git status --short | tail -25
  期待: §1 の 18 ファイルだけ（` M` が置き換えの 9 と Edit の 4、`??` が新規の 5）。.claude-pipeline/active-work.d/ の未追跡は除く。ほかが出たら `BLOCKED: 範囲外のファイル`。

手順7 記録
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && git add frontend/src/pages/quote-create/LineItemsTable.tsx frontend/src/pages/quote-create/lineItems.ts frontend/src/pages/quote-create/lineItems.test.ts frontend/src/pages/quote-create/useDraftInventory.ts frontend/src/pages/quote-create/useDraftShippingQuotes.ts frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx frontend/src/pages/invoice-create/InvoiceShipToSection.tsx frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx frontend/src/components/BillToCountryGuidance.test.tsx frontend/src/components/CommerceNavigationButtonMigration.test.tsx frontend/src/components/CommerceSubmitButtonMigration.test.tsx frontend/src/lib/query/batch3cPages.test.tsx frontend/src/pages/quote-create/quoteDraft.ts frontend/src/lib/invoiceDraftContext.ts frontend/src/locales/ja.json frontend/src/locales/en.json && git status --short | tail -25
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(invoice): rebuild the invoice create page to match the sample layout (invoice-portfolio R5)" && git log --oneline -1 | tail -1

手順8 UI の決まりの検査（commit の後。origin/main と比べる）と送り出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && set -o pipefail && BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js 2>&1 | tail -15; echo "ui-gov exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && git push -u origin release/invoice-portfolio-r5-page 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r5-page && git rev-parse HEAD
  期待: 1行目 `ui-gov exit=0`（新規 ui-allow 0件）。外れたら push せず `BLOCKED: UI の決まりの検査`。push は --no-verify・force を付けない。push が止められたら言い換えず `BLOCKED: push`。

## 4. 想定される分かれ道

- 停止する（その場で停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P6 のどれかが外れた → `BLOCKED: P番号`（P1 は違った指紋のファイル名を書く）。
  - §2 の Edit の変更前の文が見つからない・2 か所以上当たる → `BLOCKED: ファイル名 変更前の文`。
  - 手順4 の npm ci・型の生成が失敗した → 最後の 3 行を貼って `BLOCKED: 手順4`。
  - 手順5 で試験・型・eslint・検査のどれかが落ちた → 試験や検査やコードを直さず、落ちた試験の名前と最後の出力（30 行まで）を貼って `BLOCKED: 手順5 何行目`。カードからの書き写し間違い（字・字下げ）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。
  - 手順8 の UI の決まりの検査が 0 以外 → `BLOCKED: UI の決まりの検査`。
  - 手順7 の commit が記録の前の自動点検に止められた → 止めた理由の原文を貼って `BLOCKED: 手順7`（--no-verify を付けない・試験を書き換えない）。
- 警告も止める理由になる: eslint の警告（warning）が 1 件でも出たら手順5 の失敗として扱う（記録の前の自動点検が警告 0 を求めるため）。

## 5. 報告の形

- 宛先: クラウドの実行の最後の返事。ファイルに書かない。
- 1 行目: 受領確認の行。2 行目: 「本報告はカード 便R5 請求書の作成画面を見本どおりに作り直す の実行結果である」。
- 手順1・2・5・6・7・8 の出力をそのまま貼る（要約しない）。全体で 2000 字を超えるときは、手順5・手順8 を優先して貼り、ほかは期待と合ったかを ○× で書く。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。CI の結果は Opus が見る。PR は作らない（Opus が作る）。
- ファイルの編集は Edit ツール、新しいファイルは Write ツール。ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 触らない範囲

§1 以外のファイル。frontend/src/pages/invoice-create/useInvoicePreview.ts・FedExRateModal（見積の画面が使う）・QuoteCreatePage.tsx（便 R7）、frontend/src/components/ の金型の中身、tokens.css・index.css、backend/、migrations/・deploy.yml・scripts/。PDF を重ねて出す枠（便 R6）は作らない。

END OF CARD
