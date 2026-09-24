# design: fix-extraction-rules-detail

## 参照ADR

- ADR-027: i18n 強制 — 全 UI 文字列は t("key") 経由（新規キー追加なし）
- ADR-144: UIガバナンス — 金型コンポーネントのみ（新規コンポーネント追加なし）

## 外部事例

- バックエンドのフィールド名はAPIレスポンスのJSON構造に従うのが標準（Python snake_case → JSON snake_case）
- `supplier_id` はバックエンド全体を通じた公開 suppliers テーブルの主キー参照方法として統一されている

## 変更前後

### バグ1: フィールド名修正

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `SupplierExtractionRulesPage.tsx:28` | `id: number` | `supplier_id: number` |
| `SupplierExtractionRulesPage.tsx:31` | `unit_ng: number` | `unit_ng_count: number` |
| 上記の全参照箇所 | `row.id`, `.unit_ng` | `row.supplier_id`, `.unit_ng_count` |

### バグ2: MobileShell にエントリ追加

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `MobileShell.tsx:170` | `buybackPrices` の直前に欠落 | `supplierExtractionRules` を `analysisRules` の直後に追加 |

## KGI/KPI

| 基準 | 検証方法 |
|---|---|
| 詳細ページで仕入元を選択してもエラーが出ない | SupplierExtractionRulesPage で行クリック → 詳細が表示される |
| モバイルのメニューシートに「抽出ルール設定」が表示される | モバイルビューで「…」ボタン → メニューに項目が見える |

## 触らない範囲

- バックエンドのAPIエンドポイント実装（`backend/`）: 変更なし
- i18nファイル（`locales/`）: 変更なし（キーは既存）
- CSSファイル: 変更なし
