# ADR-1002: 商品IDをINTEGER一本化し、旧テーブル参照migrationを修復する

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 作成日 | 2026-09-15 |
| 起案 | しんごさん（PO）+ Claude Opus（設計パートナー） |
| 前提 | ADR-1001（Phase 2a〜2c 完了済み） |
| 関連 | ADR-090, ADR-1001 |

---

## ひとことで

旧テーブル削除後に壊れたデプロイを復旧し、商品を特定するIDを`id`（INTEGER）に一本化し、旧ID（`tcg_uuid`）を廃止する。`product_code`の自動採番をDB側に移す。

## 背景（2026-09-15 実測）

### デプロイ停止

- ADR-1001 Phase 2c で `tenant_NNN.tcg_products` テーブルを DROP した（Deploy #34918150510 成功、2026-09-15 01:42 UTC）
- 直後の Deploy #34918739146 が migration 204/240 番（`20260904_160000`）で停止。旧テーブルから商品IDを取得しようとして NULL で失敗
- `scripts/run_all_migrations.sh` は全242本を毎回再実行する設計。実行済み台帳によるスキップ機構はない
- 旧テーブルを参照する migration は **13ファイル**（全量 `grep -rln` で確認済み）

### 商品IDの分散

- `public.products` に識別子が3つ残存: `id`（INTEGER SERIAL PK）、`product_code`（TEXT）、`tcg_uuid`（UUID）
- テナントの4テーブル（keyword/exclude/analysis/logistics）の `product_id` は UUID 型で `tcg_uuid` を FK 参照
- 他のテーブル（inventory_movements/parse_logs/purchase_order_items/own_inventory）は既に `id`（INTEGER）を FK 参照
- `tcg_uuid` が NULL の商品 1,533件はLINE解析から見えない
- `tcg_uuid` は Pydantic schemas/API models/フロントエンドに露出していない（grep 0件）
- `product_code` の自動採番は Python アプリ層（`_next_pm_code()`）で実装。DB SEQUENCE なし。同時登録時の競合リスクあり

## 決定

### 1. 旧テーブル参照 migration の修復（フェーズA）

旧テーブル（`tcg_products`）を参照する 13 migration ファイルに、テーブル不在時のガード（`IF EXISTS` / 行数0チェック）を追加する。既存 migration ファイルを直接編集し、冪等性を維持する。

対象ファイル（runner 実行順）:

| # | runner行 | ファイル | grep件数 |
|---|---------|--------|---------|
| 1 | 524,530 | `20260831_110000_create_tcg_analysis_tables_t004.sql` | 8 |
| 2 | 542 | `20260902_110100_tcg_products_classification_ids.sql` | 16 |
| 3 | 557 | `20260903_180000_tcg_products_mark_en_t004.sql` | 5 |
| 4 | 573 | `20260904_160000_tcg_magazine_promo_products_t004.sql` | 11 |
| 5 | 574 | `20260905_010000_tcg_pokemon_master_batch1_t004.sql` | 9 |
| 6 | 575 | `20260905_020000_tcg_fix_product_names_t004.sql` | 8 |
| 7 | 588 | `20260906_120000_create_tcg_tables_t001.sql` | 12 |
| 8 | 598 | `20260907_140000_tcg_keyword_hygiene_t004.sql` | 11 |
| 9 | 613 | `20260908_170000_tcg_keyword_v4_t004.sql` | 9 |
| 10 | 619 | `20260909_000000_public_products_phase2b_columns.sql` | 3 |
| 11 | 630 | `20260910_170000_tcg_keyword_false_positive_guards.sql` | 2 |
| 12 | 642 | `20260914_080000_add_abbreviation_keywords_t004.sql` | 27 |
| 13 | 648 | `20260914_140000_unify_tcg_products_to_public.sql` | 多数 |

修復パターン: 各 migration の冒頭で `SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_004' AND c.relname='tcg_products')` を確認し、テーブルが存在しない場合は RAISE NOTICE で記録して正常終了する。

### 2. FK付替え: tcg_uuid → id（フェーズB）

4テーブルの `product_id` カラムを UUID → INTEGER に変換し、FK先を `public.products.id` に変更する。

| テーブル | 変更前 | 変更後 |
|---------|-------|--------|
| `product_search_keywords.product_id` | UUID → `tcg_uuid` | INTEGER → `id` |
| `product_exclude_keywords.product_id` | UUID → `tcg_uuid` | INTEGER → `id` |
| `products_logistics.product_id` | UUID → `tcg_uuid` | INTEGER → `id` |
| `analysis_results.product_id` | UUID → `tcg_uuid` | INTEGER → `id` |

migration 手順:
1. 新カラム `product_int_id` (INTEGER) を追加
2. `tcg_uuid` → `id` の対応表で全行のデータを変換
3. 旧 FK（`tcg_uuid` 向き）を削除
4. 新 FK（`id` 向き）を作成
5. 旧カラム `product_id` (UUID) を削除
6. `product_int_id` を `product_id` にリネーム

### 3. バックエンドコード書換え（フェーズB、FK付替えと同時）

tcg_uuid を参照する SQL JOIN を `id` 参照に書き換える。

本番コード: 13ファイル・42箇所
テストコード: 10ファイル・69箇所
テスト基盤: conftest.py:768（テーブル定義の tcg_uuid カラム）

### 4. product_code 自動採番の DB 移行（フェーズB）

現在の Python 層の `_next_pm_code()` を PostgreSQL SEQUENCE に置き換える。

```sql
-- 現在の最大値から SEQUENCE を開始
CREATE SEQUENCE IF NOT EXISTS public.product_code_seq
    START WITH <現在の最大PM番号+1>;

-- DEFAULT 句で自動採番
ALTER TABLE public.products
    ALTER COLUMN product_code
    SET DEFAULT 'PM' || lpad(nextval('public.product_code_seq')::text, 4, '0');
```

利点: 同時登録時の競合なし（SEQUENCE は原子的）、Python 側のロジック削除で単純化。

### 5. tcg_uuid カラム DROP（フェーズC）

フェーズB 完了後、tcg_uuid カラム参照 migration（6ファイル、うち3つはフェーズAと重複）にもガードを追加したうえで `ALTER TABLE public.products DROP COLUMN tcg_uuid` を実行。

### 6. 残存参照クリーンアップ（フェーズD）

| 対象 | ファイル数 | 箇所数 |
|------|----------|-------|
| backend/scripts/ | 1 | 1 |
| backend/tcg_migration/ | 4 | 9 |
| テスト（tcg_products 文字列） | 5 | 18 |

## 理由

- デプロイが停止しているため、フェーズA は緊急。全変更のリリースが塞がれている
- 商品IDが3種類あると「どのIDで引けばよいか」が不明確になり、新機能開発のたびに間違いが起きる。INTEGER に統一すれば既存の inventory_movements 等と同じパターンになる
- `tcg_uuid` が NULL の 1,533 商品がLINE解析対象外であることは、商品マスタの価値を損ねている
- product_code の自動採番を DB 側に移すことで、同時登録時の番号衝突を構造的に防ぐ

## 弊害・トレードオフ

| リスク | 対処 |
|-------|------|
| 13 migration ファイルの修正漏れ | 全量 `grep -rln` で確認済み。修正後に全 migration ドライランで検証 |
| UUID → INTEGER 変換のデータ不整合 | tcg_uuid → id の対応は public.products 内で 1:1。変換前後の件数検証を migration に組み込む |
| SEQUENCE の開始値ずれ | 現在の最大 PM 番号を SELECT MAX で取得してから SEQUENCE 作成 |
| 既存 API レスポンスへの影響 | tcg_uuid は API/フロントに露出していない（grep 0件で確認済み）。影響なし |
| フェーズA で既存 migration を編集する副作用 | 追加するのは先頭のテーブル存在チェックのみ。テーブルが存在する場合の動作は一切変更しない |

## 実施順序

```
フェーズA: migration修復 → デプロイ復旧（最優先）
    ↓
フェーズB: FK付替え + コード書換え + product_code自動採番
    ↓
フェーズC: tcg_uuidカラムDROP
    ↓
フェーズD: 残存参照クリーンアップ
```

各フェーズは独立した PR で実施し、PO GO を受けてからマージする。

## 受入条件

### フェーズA
- [ ] 全 242 migration がエラー 0 で通過する（ドライラン）
- [ ] デプロイワークフローが success になる
- [ ] smoke test 全項目 PASS

### フェーズB
- [ ] 4テーブルの `product_id` が INTEGER 型で `public.products.id` を FK 参照している
- [ ] 全 1,830+ 商品（tcg_uuid の有無によらず）がLINE解析の対象になる
- [ ] `product_code` が DB SEQUENCE で自動採番される
- [ ] pytest 全 PASS
- [ ] デプロイ成功 + smoke test PASS

### フェーズC
- [ ] `public.products` に `tcg_uuid` カラムが存在しない
- [ ] 全 migration ドライラン成功
- [ ] pytest 全 PASS

### フェーズD
- [ ] `grep -rn 'tcg_products' backend/` が 0 件（テスト・スクリプト含む）
- [ ] `grep -rn 'tcg_uuid' backend/` が 0 件
