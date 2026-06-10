# Phase 3 設計 — ProductEditPage（商品編集専用ページ）

**対象ADR**: ADR-122  
**recon**: docs/handoff/products-price-deprecation/recon.md  
**日付**: 2026-06-09  
**担当**: Generator

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回はモーダル→専用ページへの機械的な移植（フィールドゼロロス・API変更なし）のため、外部事例の参照は不要と判断。パターンは既存 `QuoteCreatePage`・`InvoiceCreatePage` と同一の `PageLayout` + フォームグリッド構成を踏襲。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `/admin/products/new` で新規登録フォームが開く | Playwright: navigate + snapshot |
| `/admin/products/:id/edit` で既存データがフォームに入る | Playwright: navigate + field value check |
| 保存後に一覧ページへ戻る | Playwright: submit + URL assertion |
| キャンセルで一覧ページへ戻る | Playwright: cancel + URL assertion |
| `products.unit_price` 参照が CI ゲートをパスする（Path B 免除） | `check_deprecated_columns.sh` PASS |
| TypeScript ビルドエラーなし | `tsc --noEmit` |

---

## 技術 How・KPI

- KPI: 30+ フィールドすべてが専用ページに表示される（フィールドゼロロス）
- 技術選択: `PageLayout` + `product-edit-form` CSS グリッド（既存 ADR-122 標準コンポーネント）
- `products.unit_price` は暫定免除（Path B）。廃止は Issue #1850 で追跡

---

## 弊害・トレードオフ

- `products.unit_price` 参照は DEPRECATED C-4 だが、代替入力UIが未整備のため暫定継続（recon: `docs/handoff/products-price-deprecation/recon.md` §5 参照）
- 免除スコープは `check_deprecated_columns.sh` の `products.unit_price` チェックのみ（`trust_level`・`transaction_count` は対象外）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `ProductEditPage.tsx` 新規作成（モーダルから移植） | Generator |
| 2 | `ProductsPage.tsx` モーダル削除・行クリック→navigate | Generator |
| 3 | `App.tsx` に 2 ルート追加 | Generator |
| 4 | `check_deprecated_columns.sh` に理由付き免除登録（Path B） | Generator |

---

## 継続

- `products.unit_price` 廃止完了: Issue #1850 で追跡（`own_inventory.unit_price` 編集UI整備後）
- 免除行撤去: Issue #1850 クローズ時に `check_deprecated_columns.sh` の exempt 引数を削除すること
