# design.md — ADR-156 Phase 3A: product_kind_id rewire

## 参照

- recon.md: `docs/handoff/product-kind-id-rewire/recon.md`
- ADR-156: `docs/adr/ADR-156-product-classification-tree.md`（起案中）
- ADR-155: additive-first migration 方針

## 方針

ADR-156 Phase 3A は **additive-only**。`division_id` 列は削除せず、
新規コードパスはすべて `product_kind_id` を使う。
`division_id` の削除は Phase 3B 以降（データ移行完了後）で行う。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| マイグレーション実行後、`public.products.product_kind_id` 列が存在する | `\d public.products` で確認 |
| CSV インポート（create_product）が product_kind_id を INSERT する | バックエンドテスト `test_tcg_product_import.py` PASS |
| 商品詳細ドロワーが product_kind_id の lookup を表示する | `test_tcg_product_detail_pg.py:test_detail_contains_stored_values_words_and_revision` PASS |
| 商品作成フォームが product_kind_id を送信する | `test_tcg_product_master.py` PASS |
| i18n キー `productDetail.product_kind_id` が ja/en 両方に存在する | `frontend/src/locales/ja.json` と `en.json` に `"product_kind_id"` キー確認 |
| スキーマ修飾テスト PASS | `test_tcg_schema_qualification.py` PASS |
| `division_id` 列はまだ存在し、既存データを壊さない | migration は ADD COLUMN IF NOT EXISTS のみ |

## 外部事例

該当なし（内部 SSOT 移行）

## 守り手

- `tests/test_tcg_schema_qualification.py` — SQL スキーマ修飾・text()カウント保護
- `tests/test_tcg_product_master.py` — create_product API 契約
- `tests/test_tcg_product_detail_pg.py` — detail lookup キーセット
- `scripts/check-migration-registration-exists.sh` — migration登録確認

## 弊害・戻し方

- 弊害: `division_id` は引き続き products テーブルに存在し NULL になる（Phase 3B で削除）
- 戻し方: `ALTER TABLE public.products DROP COLUMN IF EXISTS product_kind_id;` + git revert

## 影響範囲

- 呼び出し元全走査: `grep -rn "division_id\|create_product" backend/app/` で確認済み
- フロントエンド: TcgProductDetailDrawer, ProductMasterDrawer の2ファイルのみ
- テスト: 6ファイル更新済み
