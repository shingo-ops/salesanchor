# recon.md — product-master-crud

## 問題

商品マスタ画面で商品の新規追加と削除ができない。
ADR-155 で商品マスタの更新手段を CSV + アプリ画面に一本化したが、
アプリ画面での追加・削除機能が未実装だった。

## 根本原因

| 要因 | 詳細 |
|------|------|
| 作成機能なし | 既存の `POST /tcg/products` は LINE 解析連携用で `extraction_item_id` が必須。独立した作成経路がない |
| 削除機能なし | tcg_product_import.py に DELETE エンドポイントが存在しない |
| UI未対応 | TcgProductDetailDrawer は編集（PUT）のみ。作成モード・削除ボタンなし |

根拠:
- `backend/app/routers/tcg_product_import.py:150-286`（PUT のみ、DELETE なし）
- `backend/app/routers/tcg_product_master.py:90-103`（CreateProductRequest に extraction_item_id 必須）
- `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:96`（PUT 呼び出しのみ）

## 影響範囲

| ファイル | 役割 | 影響 |
|---------|------|------|
| `backend/app/routers/tcg_product_import.py` | 商品マスタ API | エンドポイント追加 |
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx` | 商品詳細ドロワー | 作成モード・削除機能追加 |
| `frontend/src/pages/super-admin/TcgProductMasterPage.tsx` | 商品マスタ一覧 | 新規追加ボタン追加 |
| `frontend/src/locales/en.json` / `frontend/src/locales/ja.json` | i18n | キー追加 |

## FK 制約（削除時）

| テーブル | ON DELETE | 対処 |
|---------|-----------|------|
| product_search_keywords | CASCADE | 自動削除（対処不要） |
| product_exclude_keywords | CASCADE | 自動削除（対処不要） |
| analysis_results | NO ACTION（nullable） | 事前に product_id を NULL に設定 |
| inventory | RESTRICT | 参照あれば 409 エラー返却（削除不可） |
| parse_logs | NO ACTION | 参照あれば 409 エラー返却 |
| own_inventory | NO ACTION | 参照あれば 409 エラー返却 |

根拠: migrations/20260915_120000 系マイグレーション（Phase B）の ON DELETE 定義

## ADR 参照

- ADR-155: 商品マスタデータの更新手段を CSV 取り込みとアプリ画面に一本化する
