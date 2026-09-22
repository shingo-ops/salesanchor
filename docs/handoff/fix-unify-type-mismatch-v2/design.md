# design — fix-unify-type-mismatch-v2

**日付**: 2026-09-22  
**対象ADR**: ADR-1001, ADR-1002  
参照: docs/handoff/fix-unify-type-mismatch-v2/recon.md

## KGI

| 基準 | 検証方法 |
|------|----------|
| `scripts/run_all_migrations.sh` が型ミスマッチなしで COMMIT まで完走する | deploy ログで COMMIT が出力される |
| Step2 の product_category_id が abort しない | NOTICE ログに "Step2 complete" または "Step2 をスキップ" が出力される |

## 変更内容

`migrations/20260914_140000_unify_tcg_products_to_public.sql` の Step2 に `_product_category_id_is_uuid` ガードを追加。

### Step2 ガードロジック（追加分）

pg_attribute で実行時に `product_category_id` 列型を確認する:

1. `public.products.product_category_id` が UUID 型で存在するか確認
   - `work_id` も `product_category_id` も UUID → 両列をそのままコピー
   - `work_id` が INTEGER だが `product_category_id` は UUID → `work_id` のみ NULL::INTEGER でコピー
   - `work_id` も `product_category_id` も INTEGER → 両列とも NULL::INTEGER でコピー

## 触るファイル

- `migrations/20260914_140000_unify_tcg_products_to_public.sql` — Step2 に product_category_id 型ガード追加
- `docs/handoff/fix-unify-type-mismatch-v2/recon.md` — 新規作成
- `docs/handoff/fix-unify-type-mismatch-v2/design.md` — 新規作成

## 削除するファイル

- `migrations/20260914_140000_unify_tcg_products_to_public.sql` — 旧 ELSE ブランチのコードを置換（行削除を伴う）

## 弊害

- `product_category_id` が INTEGER の状態でも `tcg_uuid` 列があれば Step2 は実行される（product_category_id は NULL でコピー）。INTEGER 値は 20260920_010000 の設計通り（手動コピーで補完）。問題なし。

## 戻し方

このブランチを revert → 元の migration に戻る。DB への影響はガード追加のみ（構造変更なし）。

## 外部・過去事例の参照と我々への応用

- `migrations/20260919_010000_master_ssot_work_id_recast.sql:38` — 本プロジェクト内で pg_attribute による実行時型チェックを既に採用済み。同パターンを product_category_id にも適用する。
- PR #3672（fix-unify-type-mismatch）— work_id に同じパターンを適用した先行事例。今回はそのパターンを product_category_id にも拡張する。

## 維持の仕組み

守り手: `migrations/20260919_010000_master_ssot_work_id_recast.sql`（pg_attribute ガードのリファレンス実装）

- 同様の型ミスマッチが発生した場合は pg_attribute チェックを同じパターンで追加する。
