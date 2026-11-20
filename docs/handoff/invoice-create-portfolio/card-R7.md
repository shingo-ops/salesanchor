# card-R7: 見積の作成画面の商品行を請求書と同じ表にする（invoice-create-portfolio 便 R7）

作成: Opus（Planner）2026-11-20。設計: docs/handoff/invoice-create-portfolio/design-v2.md 第10版 §3-8・§3-8-1・§4 R7・K16・§8（第10版の足し分はこのカードと一緒に審査する）。
実装承認: PO は 2026-11-17 に p1〜p8 を「見本どおり」と決め（p6「見積の画面も同じ行」）、PR マージ・デプロイまでの完走を委ねた（ccopusgo の委任の範囲）。R7 で新しい PO の決定は無い。
枝: release/invoice-portfolio-r7-quote（origin/main から）。移行（migrations/）なし・deploy.yml なし・scripts/ なし・backend なし。
基準: origin/main 4209886d9c472928be1543069ce645cafdfc5baa（触る4ファイルの指紋は P1 で照合する。2026-11-20 時点の origin/main 7d553268 でもこの4ファイルと quote-create/ は同じ中身）。

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-portfolio-R7 HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 見積の作成画面（frontend/src/pages/quote-create/QuoteCreatePage.tsx）の商品行を、請求書と同じ `LineItemsTable`（frontend/src/pages/quote-create/LineItemsTable.tsx。請求書は InvoiceCreatePage.tsx:249-257 で使う）に替える。行の初めは `handoffRows(handoff)`（lineItems.ts:42-51）。在庫は `useDraftInventory()`（GET /invoices/draft-inventory。権限は invoices.create か quotes.create）（design-v2 §3-8-1）。
- D2 為替は今ある GET /fx-rates/{通貨}（backend/app/routers/fx_rate_admin.py:61-95。ログインだけで読める）を `useApiQuery`（frontend/src/lib/query/apiQuery.ts:52-72）で読む。円は読まない。`rate_jpy` が 0 より大きいときだけ使い、読めない・404 は為替なし（単価 0。design-v2 §8）。通貨・為替が変わったら請求書と同じ `reconvertPrices`（lineItems.ts:166-172）で入れ直す。サーバーは変えない。
- D3 保存の前の点検は `allRowsReady(rows)`。偽なら `showErrors` を立て、今と同じ「quotes.itemsRequired」の文を出して送らない。送る `items` は `filledRows(rows).map(toInvoiceItem)`（8項目。backend/app/schemas/quote.py:27-36 QuoteItemInput と同じ形）。
- D4 消すもの: 自由記入の表・addItem・removeItem・updateItem・appendFromSearch・在庫0の注意・InventorySearchBar の読み込み・quoteDraft の blankItem・buildInitialItems・weightForUnit の読み込み。quoteDraft.ts・InventorySearchBar.tsx（部品そのもの）・使われなくなる文言キーは変えない（片付けは別の作業）。
- D5 `LineItemsTable` の「×」と「行を追加」の Button に `type="button"` を足す。見積の画面は表を `<form>`（QuoteCreatePage.tsx:145）の中に置き、Button.tsx は type を決めないため、そのままだと押すと保存が走る。請求書の画面は `<form>` を持たないので動きは変わらない。
- D6 取引先・担当者・通貨（JPY・USD・EUR、既定 USD）・メモ・送料（FedEx）・税・合計・総重量・「キャンセル」「下書き保存」は変えない。総重量は `totalWeight(rows)`、小計の和は商品の入った行の `rowSubtotal` の和。FedEx の枠に渡す重さも同じ値。
- D7 frontend/tests-e2e/quote-create-inventory-search.spec.ts（消える検索欄と自由記入の行を見る画面の試験）は R7 では触らない。CI では流れていない（.github/workflows/e2e.yml:294 `if: false`）。消すのは後の片付けの作業（指示書の検査 scripts/card-lint.sh L11 が手順の中の消す命令を止めるため、消すだけの作業として別に扱う）。
- D8 試験: CommerceSubmitButtonMigration.test.tsx の見積の4本を在庫の行の形に書き直す（K16 (a)〜(g)）。CommerceNavigationButtonMigration.test.tsx は為替の道の受け答えを足すだけ。

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。新しいファイルは無い。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順8） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-2. 実装前点検（手順2 で流す。外れたら実装せず停止して BLOCKED: で報告）

- P1 触る4ファイルの指紋（git hash-object）が次と同じ（この順）:
  - `4a946983dcc36a87711ff2c92b0228ff3e5d37b4` frontend/src/pages/quote-create/QuoteCreatePage.tsx
  - `14e85fd8a09281fce3e66b4d65950ec84efa8bc4` frontend/src/pages/quote-create/LineItemsTable.tsx
  - `8b6ce444b6d84055b71ad864279ac62527ad7a82` frontend/src/components/CommerceSubmitButtonMigration.test.tsx
  - `f1ada1c3a86ba040d129f91cc3164f20ab2c6f85` frontend/src/components/CommerceNavigationButtonMigration.test.tsx
- P2 変えないファイルの指紋が次と同じ（この順）:
  - `d87b90275d22531a144d2dc369cfa1851f338cf8` frontend/src/pages/quote-create/quoteDraft.ts
  - `216a16a564504aa8575f6ae2516d6289325e08cd` frontend/src/pages/quote-create/lineItems.ts
- P3 LineItemsTable.tsx に `type="button"` が 0 件（`grep -c` の出力 `0`）。
- P4 2つの試験ファイルに `fx-rates` が 0 件（`grep -c` の出力 2 行とも `:0`）。

## 1. 触るファイル

- frontend/src/pages/quote-create/QuoteCreatePage.tsx（Edit）
- frontend/src/pages/quote-create/LineItemsTable.tsx（Edit）
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx（Edit）
- frontend/src/components/CommerceNavigationButtonMigration.test.tsx（Edit）

## 2. 変更

### 2-1. frontend/src/pages/quote-create/QuoteCreatePage.tsx（Edit 13 か所）

(a) 変更前:
```
 *     在庫表起点で開いた場合、キャンセルは在庫表へ戻る。
 */
```
変更後:
```
 *     在庫表起点で開いた場合、キャンセルは在庫表へ戻る。
 *   2026-11-20: invoice-create-portfolio 便R7 — 商品行を請求書と同じ LineItemsTable に替えた
 *     （在庫の道・為替の道 GET /fx-rates/{通貨}。自由記入の行と検索で足す欄は廃止。design-v2 §3-8-1・K16）。
 */
```

(b) 変更前:
```
import { useState, FormEvent } from "react";
```
変更後:
```
import { useEffect, useState, FormEvent } from "react";
```

(c) 変更前:
```
import { api } from "../../lib/api";
```
変更後:
```
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
```

(d) 変更前:
```
import InventorySearchBar, { InventorySearchCandidate } from "../../components/InventorySearchBar";
import { FedExRateModal } from "../../components/FedExRateModal";
```
変更後:
```
import { FedExRateModal } from "../../components/FedExRateModal";
```

(e) 変更前:
```
import {
  type LineItem,
  type QuoteHandoffState,
  blankItem,
  buildInitialItems,
  weightForUnit,
} from "./quoteDraft";
```
変更後:
```
import type { LineItem, QuoteHandoffState } from "./quoteDraft";
import { LineItemsTable } from "./LineItemsTable";
import { allRowsReady, filledRows, handoffRows, reconvertPrices, rowSubtotal, toInvoiceItem, totalWeight } from "./lineItems";
import { useDraftInventory } from "./useDraftInventory";
```

(f) 変更前:
```
  const [items, setItems] = useState<LineItem[]>(() => buildInitialItems(handoff));
```
変更後:
```
  // 商品行は請求書と同じ形（在庫表の画面から持ってきた商品が先頭の行・12行まで空の行。design-v2 §3-8-1）
  const [rows, setRows] = useState<LineItem[]>(() => handoffRows(handoff));
  const [showErrors, setShowErrors] = useState(false);
```

(g) 変更前:
```
  const [showFedExModal, setShowFedExModal] = useState(false);

  // 自由記入の空行を追加（マスタに無い商品も入力できる）。
  const addItem = () => {
    setItems((prev) => [...prev, { ...blankItem }]);
  };

  const removeItem = (index: number) => {
    setItems((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)));
  };

  const updateItem = (index: number, field: keyof LineItem, value: unknown) => {
    setItems((prev) => {
      const next = [...prev];
      (next[index] as unknown as Record<string, unknown>)[field] = value;
      return next;
    });
  };

  // 「検索して追加」: InventorySearchBar の選択商品を新しい明細行として追加する（上書きではなく追加）。
  // 海外顧客向け: 英語タイトル/状態/形態を引き込み、形態(unit)に応じてマスタ重量を weight にセットする。
  const appendFromSearch = (c: InventorySearchCandidate) => {
    const isOutOfStock = c.stock_quantity !== null && c.stock_quantity <= 0;
    setItems((prev) => [
      ...prev,
      {
        product_id: c.product_id,
        product_name: c.name,
        name_en: c.name_en ?? null,
        condition: null,
        unit: null,
        quantity: isOutOfStock ? 0 : 1,
        unit_price: c.unit_price ?? 0,
        box_weight_kg: c.box_weight_kg ?? null,
        case_weight_kg: c.case_weight_kg ?? null,
        weight: null,
        inventory_id: null,
        zero_stock_warning: isOutOfStock,
      },
    ]);
  };
```
変更後:
```
  const [showFedExModal, setShowFedExModal] = useState(false);

  // 在庫は請求書と同じ道（GET /invoices/draft-inventory。K23）
  const inventory = useDraftInventory();
  // 為替は今ある道 GET /fx-rates/{通貨}（請求書の draft-context と同じ表の最新の1行）。円は読まない。読めない・404 は為替なし（単価 0。design-v2 §8）
  const fxQ = useApiQuery<{ currency: string; rate_jpy: number }>(`/fx-rates/${currency}`, { enabled: currency !== "JPY" });
  const rate = currency !== "JPY" && fxQ.data !== undefined && fxQ.data.rate_jpy > 0 ? fxQ.data.rate_jpy : null;

  // 通貨（または為替）が変わったら、単価を手で直していない行だけ入れ直す（PO 2026-11-18「1」）
  useEffect(() => {
    setRows((prev) => reconvertPrices(prev, currency, rate));
  }, [currency, rate]);
```

(h) 変更前:
```
  const subtotal = items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0);
  // 総重量 = Σ(数量 × 行重量)。重量未設定の行は 0 扱い。
  const totalWeight = items.reduce(
    (sum, item) => sum + item.quantity * (item.weight ?? 0),
    0,
  );
```
変更後:
```
  const subtotal = filledRows(rows).reduce((sum, row) => sum + rowSubtotal(row), 0);
  // 総重量 = 商品の入った行の 重さ×数量 の和（lineItems.ts totalWeight）
  const totalWeightKg = totalWeight(rows);
```

(i) 変更前:
```
    if (items.some((i) => !i.product_name || i.unit_price <= 0 || i.quantity <= 0)) {
      setError(t("quotes.itemsRequired"));
      return;
    }
```
変更後:
```
    if (!allRowsReady(rows)) {
      setShowErrors(true);
      setError(t("quotes.itemsRequired"));
      return;
    }
```

(j) 変更前:
```
        items: items.map((i) => ({
          product_id: i.product_id,
          product_name: i.product_name,
          name_en: i.name_en ?? null,
          condition: i.condition ?? null,
          unit: i.unit ?? null,
          quantity: i.quantity,
          unit_price: i.unit_price,
          weight: i.weight,
        })),
```
変更後:
```
        items: filledRows(rows).map(toInvoiceItem),
```

(k) 変更前:
```
        <h3 style={{ marginBottom: "var(--space-3)" }}>{t("quotes.items")}</h3>
        {/* 明細表示ゾーン: 行内検索/AND-OR は廃止。商品名は自由記入可（マスタに無い商品も入力できる）。 */}
        <div style={{ overflowX: "auto", marginBottom: "var(--space-4)" }}>
          <table className="data-table" style={{ minWidth: 'var(--table-min-width-base)' }}>
            <thead>
              <tr>
                <th>{t("quotes.titleColumn")}</th>
                <th>{t("quotes.condition")}</th>
                <th>{t("quotes.unit")}</th>
                <th>{t("quotes.quantity")}</th>
                <th>{t("quotes.unitPrice")}</th>
                <th>{t("quotes.weight")}</th>
                <th>{t("quotes.subtotal")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} data-testid={`quote-item-row-${i}`}>
                  <td style={{ minWidth: 'var(--table-col-product-name-min-w)' }}>
                    {/* 英語タイトル(name_en)をメイン(太字)、日本語(product_name)を参考表示。
                        いずれも自由記入可（マスタに無い商品も入力できる）。 */}
                    <TextFieldControl size="sm"
                      value={item.name_en ?? ""}
                      onChange={(e) => updateItem(i, "name_en", e.target.value || null)}
                      placeholder={t("quotes.titleColumn")}
                      style={{ width: "100%", minWidth: 'var(--input-width-product-name)', fontWeight: "var(--font-weight-semi)" }}
                      data-testid={`quote-item-row-${i}-name-en`}
                    />
                    <TextFieldControl size="sm"
                      value={item.product_name}
                      onChange={(e) => updateItem(i, "product_name", e.target.value)}
                      placeholder={t("quotes.productNamePlaceholder")}
                      style={{ width: "100%", minWidth: 'var(--input-width-product-name)', marginTop: "var(--space-1)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}
                      data-testid={`quote-item-row-${i}-name`}
                    />
                    {item.zero_stock_warning && (
                      <div
                        data-testid={`quote-item-row-${i}-zero-stock-warning`}
                        className="warning-message"
                        style={{ marginTop: "var(--space-1)", color: "var(--color-warning)", fontSize: "var(--font-sm)" }}
                      >
                        {t("inventory.search.zeroStockWarning", { name: item.product_name })}
                      </div>
                    )}
                  </td>
                  <td>
                    <TextFieldControl size="sm" value={item.condition ?? ""} onChange={(e) => updateItem(i, "condition", e.target.value || null)} placeholder={t("quotes.condition")} style={{ width: 'var(--input-width-weight)' }} data-testid={`quote-item-row-${i}-condition`} />
                  </td>
                  <td>
                    {/* 形態(unit)変更時はマスタ重量を引き込み直す。 */}
                    <TextFieldControl size="sm"
                      value={item.unit ?? ""}
                      onChange={(e) => {
                        const nextUnit = e.target.value || null;
                        updateItem(i, "unit", nextUnit);
                        updateItem(i, "weight", weightForUnit(nextUnit, item.box_weight_kg, item.case_weight_kg, item.weight));
                      }}
                      placeholder={t("quotes.unit")}
                      style={{ width: 'var(--input-width-weight)' }}
                      data-testid={`quote-item-row-${i}-unit`}
                    />
                  </td>
                  <td>
                    <TextFieldControl size="sm" type="number" min="1" value={item.quantity} onChange={(e) => updateItem(i, "quantity", Number(e.target.value))} style={{ width: 'var(--input-width-qty)' }} data-testid={`quote-item-row-${i}-qty`} />
                  </td>
                  <td>
                    <TextFieldControl size="sm" type="number" min="0" step="0.01" value={item.unit_price} onChange={(e) => updateItem(i, "unit_price", Number(e.target.value))} style={{ width: 'var(--input-width-price)' }} />
                  </td>
                  <td>
                    <TextFieldControl size="sm" type="number" min="0" step="0.001" value={item.weight || ""} onChange={(e) => updateItem(i, "weight", e.target.value ? Number(e.target.value) : null)} style={{ width: 'var(--input-width-weight)' }} data-testid={`quote-item-row-${i}-weight`} />
                  </td>
                  <td style={{ fontWeight: "var(--font-weight-semi)", whiteSpace: "nowrap" }}>{(item.quantity * item.unit_price).toLocaleString()}</td>
                  <td>
                    {items.length > 1 && (
                      <Button variant="danger" size="sm" type="button" onClick={() => removeItem(i)}>{t("quotes.removeItem")}</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ marginBottom: "var(--space-3)" }}>
          <Button type="button" variant="secondary" size="md" onClick={addItem} data-testid="quote-add-blank">{t("quotes.addItem")}</Button>
        </div>

        <div style={{ width: "min(100%, 40rem)", marginBottom: "var(--space-6)" }}>
          <InventorySearchBar
            onSelect={appendFromSearch}
            testIdPrefix="quote-add-search"
            placeholder={t("inventory.view.searchPlaceholder")}
          />
        </div>
```
変更後:
```
        <h3 style={{ marginBottom: "var(--space-3)" }}>{t("quotes.items")}</h3>
        {/* 商品行は請求書と同じ表（#・カテゴリ・商品・状態・数量・重さ・単価・小計・×。design-v2 §3-8-1・K16）。値段・在庫・重さは在庫の道の値だけ。 */}
        <div style={{ marginBottom: "var(--space-6)" }}>
          <LineItemsTable
            rows={rows}
            onChange={setRows}
            inventory={inventory}
            currency={currency}
            rate={rate}
            showErrors={showErrors}
            disabled={saving}
          />
        </div>
```

(l) 変更前:
```
            <div style={{ padding: "var(--space-2) var(--space-3)", fontWeight: "var(--font-weight-semi)" }} data-testid="quote-total-weight">{totalWeight.toLocaleString()} kg</div>
```
変更後:
```
            <div style={{ padding: "var(--space-2) var(--space-3)", fontWeight: "var(--font-weight-semi)" }} data-testid="quote-total-weight">{totalWeightKg.toLocaleString()} kg</div>
```

(m) 変更前:
```
        weightKg={totalWeight}
```
変更後:
```
        weightKg={totalWeightKg}
```

### 2-2. frontend/src/pages/quote-create/LineItemsTable.tsx（Edit 2 か所）

(a) 変更前:
```
        <Button
          variant="ghost"
          size="sm"
```
変更後:
```
        <Button
          type="button"
          variant="ghost"
          size="sm"
```

(b) 変更前:
```
        <Button
          variant="secondary"
          size="sm"
          data-testid="invoice-add-row"
```
変更後:
```
        <Button
          type="button"
          variant="secondary"
          size="sm"
          data-testid="invoice-add-row"
```

### 2-3. frontend/src/components/CommerceSubmitButtonMigration.test.tsx（Edit 7 か所）

(a) 変更前:
```
function wrap(node: React.ReactNode, entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}</MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }
```
変更後:
```
type Entries = React.ComponentProps<typeof MemoryRouter>['initialEntries'];
function wrap(node: React.ReactNode, entries: Entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}</MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: Entries) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }
```

(b) 変更前:
```
  expect(controls).toHaveLength(23); controls.forEach((control, index) => fireEvent.change(control, { target: { value: visibleProductValues[index] } }));
}
```
変更後:
```
  expect(controls).toHaveLength(23); controls.forEach((control, index) => fireEvent.change(control, { target: { value: visibleProductValues[index] } }));
}
// invoice-create-portfolio 便R7: 見積の作成画面は請求書と同じ商品行（在庫の道・為替の道を読む。design-v2 §3-8-1・K16）
const inventory = {
  categories: [{ code: 'OP', name_ja: 'One Piece' }],
  items: [
    { product_id: 7, name: 'Booster Box A', name_en: 'Booster Box A EN', mark: 'OP-01', work_code: 'OP', box_weight_kg: 0.5, case_weight_kg: 6,
      cells: { Case: { price: 170000, quantity: 1 }, 'Sealed box': { price: 15000, quantity: 3 } } },
  ],
};
const fxUsd = { currency: 'USD', rate_jpy: 150, fetched_at: '2026-11-19T21:00:00+00:00', updated_at: '2026-11-19T21:00:00+00:00' };
const quoteHandoff = { selectedProducts: [{ product_id: 7, product_name: 'Booster Box A', unit_price: null }] };
const stockRow = { product_id: 7, product_name: 'Booster Box A', name_en: 'Booster Box A EN', condition: 'Sealed box', unit: 'box', quantity: 1, unit_price: 100, weight: 0.5 };
const optionValues = (testId: string) => Array.from((screen.getByTestId(testId) as HTMLSelectElement).options).map((o) => o.value);
const priceValue = () => (screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value;
/** 在庫表の画面から商品 7 を持ってきた形で見積の画面を開き、取引先と担当者を選ぶ。state が空でなければ状態も選ぶ */
async function openQuoteWithProduct(state: string) {
  render(routed(<QuoteCreatePage />, '/quotes/new', [{ pathname: '/quotes/new', state: quoteHandoff }]));
  await waitFor(() => expect(optionValues('invoice-item-state-0')).toContain('Sealed box'), { timeout: 4000 });
  const selects = screen.getAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } });
  await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } });
  if (state !== '') fireEvent.change(screen.getByTestId('invoice-item-state-0'), { target: { value: state } });
}
```

(c) 変更前:
```
    // invoice-create-portfolio 便R5: 請求書の作成画面は在庫の道を 1 回読む
    if (url === '/invoices/draft-inventory') return { categories: [], items: [] };
```
変更後:
```
    // invoice-create-portfolio 便R5・R7: 請求書と見積の作成画面は在庫の道を 1 回読む。見積は為替の道も読む（USD）
    if (url === '/invoices/draft-inventory') return inventory;
    if (url === '/fx-rates/USD') return fxUsd;
```

(d) 変更前:
```
    ['quote', <QuoteCreatePage />, 'quote-add-blank', 'quote-item-row-', ['', '', '', ''], ['1', '0', '']],
  ] as const)('%s addItem appends one blank row per click with zero writes', async (_name, page, buttonId, rowPrefix, textValues, numberValues) => {
    render(wrap(page));
    const button = await screen.findByTestId(buttonId) as HTMLButtonElement;
```
変更後:
```
    // invoice-create-portfolio 便R7: 見積も同じ商品行の表（K16 (a)）
    ['quote', <QuoteCreatePage />, 'invoice-add-row', 'invoice-item-row-', [], ['', '']],
  ] as const)('%s addItem appends one blank row per click with zero writes', async (_name, page, buttonId, rowPrefix, textValues, numberValues) => {
    render(wrap(page));
    const button = await screen.findByTestId(buttonId) as HTMLButtonElement;
    // 見積の画面は表を form の中に置くので、押しても保存が走らない種類のボタン（design-v2 §3-8-1）
    expect(button.getAttribute('type')).toBe('button');
```

(e) 変更前:
```
    fireEvent.submit(submit.closest('form')!);
    expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy();
```
変更後:
```
    fireEvent.submit(submit.closest('form')!);
    expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy();
    // K16 (g): 自由記入の欄と検索で足す欄は画面に無い
    expect(document.querySelectorAll('[data-testid^="quote-add-search"], [data-testid^="quote-item-row-"]').length).toBe(0);
```

(f) 変更前:
```
  it.each([
    ['empty name', 'name', ''], ['zero price', 'price', '0'], ['zero quantity', 'quantity', '0'],
  ] as const)('Quote item handler rejects %s with zero POST', async (_label, field, value) => {
    render(wrap(<QuoteCreatePage />)); const selects = await screen.findAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } }); await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } });
    const row = screen.getByTestId('quote-item-row-0'); const name = within(row).getByTestId('quote-item-row-0-name'); const numbers = within(row).getAllByRole('spinbutton'); fireEvent.change(name, { target: { value: field === 'name' ? value : 'Card' } }); fireEvent.change(numbers[0], { target: { value: field === 'quantity' ? value : '1' } }); fireEvent.change(numbers[1], { target: { value: field === 'price' ? value : '10' } });
    if (field === 'quantity') { fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) })); expect(mock.post).not.toHaveBeenCalled(); }
    fireEvent.submit(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }).closest('form')!); expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy(); expect(mock.post).not.toHaveBeenCalled();
  });
```
変更後:
```
  it.each([
    ['no state', 'state'], ['zero price', 'price'], ['zero quantity', 'quantity'],
  ] as const)('Quote item guard rejects a stock row with %s with zero POST (K16 (c))', async (_label, field) => {
    await openQuoteWithProduct(field === 'state' ? '' : 'Sealed box');
    if (field !== 'state') await waitFor(() => expect(priceValue()).toBe('100'));
    if (field === 'price') fireEvent.change(screen.getByTestId('invoice-item-price-0'), { target: { value: '0' } });
    if (field === 'quantity') fireEvent.change(screen.getByTestId('invoice-item-quantity-0'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }));
    expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy(); expect(mock.post).not.toHaveBeenCalled();
  });
```

(g) 変更前:
```
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
```
変更後:
```
  it('Quote submit sends the stock row in the same 8-field shape, locks pending, keeps the row on failure, retries, and routes (K16 (b)(d)(e))', async () => {
    const first = deferred(); mock.post.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    await openQuoteWithProduct('Sealed box');
    // USD: 在庫表の円の値段 15000 ÷ 為替 150 = 100。Sealed box の重さは箱の重さ 0.5
    await waitFor(() => expect(priceValue()).toBe('100'));
    expect(screen.getByTestId('invoice-item-weight-0').textContent).toBe(String(instance.t('lineItems.weightKg', { value: 0.5 })));
    fireEvent.change(screen.getByTestId('shipping-fee-input'), { target: { value: '3' } });
    fireEvent.change(screen.getByText(String(instance.t('quotes.tax'))).parentElement!.querySelector('input')!, { target: { value: '7' } }); fireEvent.change(screen.getByText(String(instance.t('common.notes'))).parentElement!.querySelector('input')!, { target: { value: 'memo' } });
    const submit = screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }) as HTMLButtonElement;
    fireEvent.click(submit);
    // 空の行（11行）は送らない（K16 (d)）
    const expected = { company_id: 4, contact_id: 5, currency: 'USD', shipping_fee: 3, tax_amount: 7, notes: 'memo', items: [stockRow] };
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/quotes', expected); expect(submit.disabled).toBe(true); fireEvent.click(submit); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Quote save failed'))); expect(await screen.findByText('Quote save failed')).toBeTruthy();
    expect((screen.getByTestId('invoice-item-state-0') as HTMLSelectElement).value).toBe('Sealed box'); expect(submit.disabled).toBe(false);
    fireEvent.click(submit); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2)); expect(mock.post.mock.calls[1]).toEqual(['/quotes', expected]);
    expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });

  it('Quote submit maps empty fee, tax, and notes to null (K16 (f))', async () => {
    mock.post.mockResolvedValue({}); await openQuoteWithProduct('Sealed box'); await waitFor(() => expect(priceValue()).toBe('100'));
    fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) })); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/quotes', { company_id: 4, contact_id: 5, currency: 'USD', shipping_fee: null, tax_amount: null, notes: null, items: [stockRow] }); expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });
```

### 2-4. frontend/src/components/CommerceNavigationButtonMigration.test.tsx（Edit 1 か所）

変更前:
```
    // invoice-create-portfolio 便R5: 請求書の作成画面は在庫の道を 1 回読む
    if (url === '/invoices/draft-inventory') return { categories: [], items: [] };
```
変更後:
```
    // invoice-create-portfolio 便R5: 請求書の作成画面は在庫の道を 1 回読む
    if (url === '/invoices/draft-inventory') return { categories: [], items: [] };
    // invoice-create-portfolio 便R7: 見積の作成画面は為替の道を読む（既定の通貨 USD）
    if (url === '/fx-rates/USD') return { currency: 'USD', rate_jpy: 150, fetched_at: '2026-11-19T21:00:00+00:00', updated_at: '2026-11-19T21:00:00+00:00' };
```

## 3. 手順（1つずつ流し、出力を報告に書く）

手順1 作業場所
    cd /home/user/salesanchor && git fetch origin main
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-r7-quote
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-r7-quote
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git merge-base --is-ancestor origin/main HEAD; echo "main exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git rev-parse HEAD
  期待: 2行目の出力が空（空でなければ `BLOCKED: 手順1 枝が既にある`）。4行目に `worktrees/salesanchor/release-invoice-portfolio-r7-quote` が出る。5行目 `main exit=0`。

手順2 実装前点検 P1〜P4
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git hash-object frontend/src/pages/quote-create/QuoteCreatePage.tsx frontend/src/pages/quote-create/LineItemsTable.tsx frontend/src/components/CommerceSubmitButtonMigration.test.tsx frontend/src/components/CommerceNavigationButtonMigration.test.tsx
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git hash-object frontend/src/pages/quote-create/quoteDraft.ts frontend/src/pages/quote-create/lineItems.ts
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && grep -c 'type="button"' frontend/src/pages/quote-create/LineItemsTable.tsx
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && grep -c "fx-rates" frontend/src/components/CommerceSubmitButtonMigration.test.tsx frontend/src/components/CommerceNavigationButtonMigration.test.tsx
  期待（命令の順）: P1 の4つの指紋がその順に出る。P2 の2つの指紋がその順に出る。`0`。2行とも末尾が `:0`。

手順3 §2 の変更を Edit ツールでする（§2 のコードの囲み（```）の中身だけを書く）。終わったら次を流す
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git status --short | tail -15

手順4 道具を入れる
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm ci --no-audit --no-fund 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && set -o pipefail && npm run generate:api-types 2>&1 | tail -3; echo "gen exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && ls src/api/generated/schema.d.ts
  期待: 2行目 `gen exit=0`。3行目に `src/api/generated/schema.d.ts` が出る（生成物は .gitignore で記録の対象外）。外れたら `BLOCKED: 手順4 型の生成`。

手順5 形と試験（どれも作業場所の frontend で流す）
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/components/CommerceSubmitButtonMigration.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx src/pages/invoice-create/InvoiceCreatePage.test.tsx src/pages/quote-create/quoteDraft.test.ts src/pages/quote-create/lineItems.test.ts src/components/AllLegacyButtonDynamicMigration.test.tsx src/lib/query/batch3cPages.test.tsx 2>&1 | tail -15
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && set -o pipefail && npx tsc -p tsconfig.json 2>&1 | tail -15; echo "tsc exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && set -o pipefail && npx eslint --max-warnings=0 src/pages/quote-create/QuoteCreatePage.tsx src/pages/quote-create/LineItemsTable.tsx src/components/CommerceSubmitButtonMigration.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx 2>&1 | tail -15; echo "eslint exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm run check:i18n-missing-keys 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm run check:error-text-next-action 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm run check:page-size 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm run check:page-layout 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm run check:page-folder 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm run check:loading-clear 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm run check:status-direct-writes 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && npm run check:jsx-emoji 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote/frontend && set -o pipefail && node scripts/check-css-var-fallbacks.js 2>&1 | tail -5; echo "css-var exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git grep -c "components/InventorySearchBar\|appendFromSearch\|buildInitialItems\|quote-add-blank\|quote-item-row" -- frontend/src/pages/quote-create/QuoteCreatePage.tsx; echo "left exit=$?"
  期待: 1行目は failed 0（7ファイルの試験がすべて passed。本数はそのまま書く）。2行目 `tsc exit=0`。3行目 `eslint exit=0` で、誤りも警告も 0。css-var の行は `css-var exit=0`。最後の行は出力なしで `left exit=1`（消すものが 0 件）。4行目以降の検査はどれも誤りなしで終わる（✅ や 0 件の表示。❌・終了の失敗が出ない）。

手順6 変えたファイル
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git status --short | tail -15
  期待: §1 の 4 ファイルだけ（4 行とも ` M`）。.claude-pipeline/active-work.d/ の未追跡は除く。ほかが出たら `BLOCKED: 範囲外のファイル`。

手順7 記録
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git add frontend/src/pages/quote-create/QuoteCreatePage.tsx frontend/src/pages/quote-create/LineItemsTable.tsx frontend/src/components/CommerceSubmitButtonMigration.test.tsx frontend/src/components/CommerceNavigationButtonMigration.test.tsx && git status --short | tail -15
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(quote): use the shared stock line items table on the quote create page (invoice-portfolio R7)" && git log --oneline -1 | tail -1

手順8 UI の決まりの検査（commit の後。origin/main と比べる）と送り出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && set -o pipefail && BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js 2>&1 | tail -15; echo "ui-gov exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git push -u origin release/invoice-portfolio-r7-quote 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r7-quote && git rev-parse HEAD
  期待: 1行目 `ui-gov exit=0`（新規 ui-allow 0件）。外れたら push せず `BLOCKED: UI の決まりの検査`。push は --no-verify・force を付けない。push が止められたら言い換えず `BLOCKED: push`。

## 4. 想定される分かれ道

- 停止する（その場で停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P4 のどれかが外れた → `BLOCKED: P番号`（P1・P2 は違った指紋のファイル名を書く）。
  - §2 の Edit の変更前の文が見つからない・2 か所以上当たる → `BLOCKED: ファイル名 変更前の文`。
  - 手順4 の npm ci・型の生成が失敗した → 最後の 3 行を貼って `BLOCKED: 手順4`。
  - 手順5 で試験・型・eslint・検査のどれかが落ちた → 試験や検査やコードを直さず、落ちた試験の名前と最後の出力（30 行まで）を貼って `BLOCKED: 手順5 何行目`。カードからの書き写し間違い（字・字下げ）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。
    - 見積の試験で単価が `100` にならずに時間切れになった（為替の道が試験の中で読まれない）ときも、直さずに止める（Opus が設計を見直す）。
  - 手順8 の UI の決まりの検査が 0 以外 → `BLOCKED: UI の決まりの検査`。
  - 手順7 の commit が記録の前の自動点検に止められた → 止めた理由の原文を貼って `BLOCKED: 手順7`（--no-verify を付けない・試験を書き換えない）。
- 警告も止める理由になる: eslint の警告（warning）が 1 件でも出たら手順5 の失敗として扱う。

## 5. 報告の形

- 宛先: クラウドの実行の最後の返事。ファイルに書かない。
- 1 行目: 受領確認の行。2 行目: 「本報告はカード 便R7 見積の作成画面の商品行を請求書と同じ表にする の実行結果である」。
- 手順1・2・5・6・7・8 の出力をそのまま貼る（要約しない）。全体で 2000 字を超えるときは、手順5・手順8 を優先して貼り、ほかは期待と合ったかを ○× で書く。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。CI の結果は Opus が見る。PR は作らない（Opus が作る）。
- ファイルの編集は Edit ツール。ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 触らない範囲

§1 以外のファイル。frontend/src/pages/quote-create/quoteDraft.ts・quoteDraft.test.ts・lineItems.ts・lineItems.test.ts・useDraftInventory.ts・useDraftShippingQuotes.ts、frontend/src/components/InventorySearchBar.tsx とその Storybook、frontend/src/components/ の金型の中身（Button.tsx を含む）、ja.json・en.json（使われなくなる文言キー4つも消さない）、frontend/tests-e2e/quote-create-inventory-search.spec.ts（止まっている画面の試験。消すのは後の片付け）、docs/audit/ の点検表（消す画面の試験の名前が残るが、記録なので変えない）、frontend/src/pages/invoice-create/、backend/、migrations/・deploy.yml・scripts/。

END OF CARD
