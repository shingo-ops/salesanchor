# design: fix-extraction-rules-detail

## 参照recon

- recon: docs/handoff/fix-extraction-rules-detail/recon.md

## 参照ADR

- ADR-027: i18n 強制 — 全 UI 文字列は t("key") 経由（新規キー追加なし）
- ADR-144: UIガバナンス — 金型コンポーネントのみ（新規コンポーネント追加なし）

## 外部・過去事例の参照と我々への応用

- バックエンドのフィールド名はAPIレスポンスのJSON構造に従うのが標準（Python snake_case → JSON snake_case）
- `supplier_id` はバックエンド全体を通じた public.suppliers テーブルの主キー参照方法として統一されている（`backend/app/schemas/central_masters.py` の `SupplierAliasBase` 等で確認済み）
- `unit_ng_count` はカウント系フィールドに `_count` サフィックスを付ける慣例に合致

## 変更前後

### バグ1: フィールド名修正

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:28` | `id: number` | `supplier_id: number` |
| `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:31` | `unit_ng: number` | `unit_ng_count: number` |
| 上記の全参照箇所 | `row.id`, `.unit_ng` | `row.supplier_id`, `.unit_ng_count` |

### バグ2: MobileShell にエントリ追加

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/components/MobileShell.tsx:170` | `buybackPrices` の直前に欠落 | `supplierExtractionRules` を `analysisRules` の直後に追加 |

## KGI/KPI

| 基準 | 検証方法 |
|---|---|
| 詳細ページで仕入元を選択してもエラーが出ない | SupplierExtractionRulesPage で行クリック → 詳細が表示される |
| モバイルのメニューシートに「抽出ルール設定」が表示される | モバイルビューで「…」ボタン → メニューに項目が見える |

## 維持の仕組み

- 守り手: CI Frontend lint（i18nキー整合チェック）、ADR-144 UIガバナンスゲート（金型外コンポーネント検出）
- フィールド名の一致はバックエンドのAPIスキーマを変更した際に、フロントエンドの型定義も同時に更新することで維持する
- DesktopShell と MobileShell の項目の同期は、新規ページ追加時に両方に追加するコードレビューチェックで維持する
- 解析管理サブナビへの統合は AnalysisRulesSidebarKey 型定義で管理（型エラーで未宣言キーを検出）

## 触らない範囲

- バックエンドのAPIエンドポイント実装（`backend/`）: 変更なし
- i18nファイル（`locales/`）: `analysisRules.sidebar.extractionRules` キーを ja/en 両方に追加
- CSSファイル: 変更なし
