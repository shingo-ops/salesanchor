# Recon: public.products 列 churn による 1600 列上限インシデント

**日付**: 2026-10-03〜2026-10-04
**担当**: Opus(設計) / Sonnet(実装・recon)
**インシデント**: 2026-10-03 本番デプロイ失敗（deploy run 37130920016）

---

## 1. 事実（本番・origin/main、Opus/しんごさん確認済み）

- `scripts/run_all_migrations.sh` は毎デプロイで登録済み migration を**全件再実行**する（冪等前提の `ADD COLUMN IF NOT EXISTS` / `DROP COLUMN IF EXISTS` パターン）。
- 本件に関係する実行順（`scripts/run_all_migrations.sh` 内の行番号）:
  - `scripts/run_all_migrations.sh:191` → `migrations/20260623_020000_drop_products_category_classification.sql`（`:60` で `public.products.category_classification` を DROP）
  - `scripts/run_all_migrations.sh:216` → `migrations/20260602_000000_add_products_central_columns.sql`（`:19` で `condition` を ADD）
  - `scripts/run_all_migrations.sh:217` → `migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql`（`:83`,`:89` で `condition` 列を INSERT/SELECT 対象に含む）
  - `scripts/run_all_migrations.sh:219` → `migrations/20260602_030000_add_products_unit.sql`（`:6` で `unit` を ADD）
  - `scripts/run_all_migrations.sh:220` → `migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql`（`:31-37` で `unit`/`condition` を UPDATE、列存在ガード無し）
  - `scripts/run_all_migrations.sh:230` → `migrations/20260602_170000_add_products_master_label_columns.sql`（`:32` で `category_classification` を ADD）
  - `scripts/run_all_migrations.sh:482` → `migrations/20260629_010000_backfill_inventory_unit_from_products.sql`（`:9-21` で `information_schema.columns` による列存在ガード付きで `public.products.unit` → `public.inventory.unit` へコピー）
  - `scripts/run_all_migrations.sh:491` → `migrations/20260629_020000_drop_products_condition_unit.sql`（`:5-6` で `condition`/`unit` を永久 DROP）
- 本番 `public.products`: **1541** dropped attributes、live 列 **59**、max attnum **1600**（デプロイ失敗時点で live `condition`=1599、`unit`=1600 — 失敗した run が再 ADD した分）。
- デプロイ run **37130920016** は `scripts/run_all_migrations.sh:230`（`migrations/20260602_170000_add_products_master_label_columns.sql`、`category_classification` の再 ADD）で `"tables can have at most 1600 columns"` エラーにより失敗。
- 他テーブルでこの現象は無い（dropped attribute 数の次点は 3 件のみ）。
- **しんごさん確認（2026-10-03、本番 read-only）**: `public.products` は **1347 行**。失敗した run は `scripts/run_all_migrations.sh:220`（`migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql`）まで通過して実行済みだが、その後も `count(unit)=0`、`count(condition)=0`。つまり condition/unit の ADD→backfill→（inventory へコピー）→DROP の一連は、現時点の本番データに対しては**何も書き込んでいない**（書き込むべき対象データが無い）。この backfill の本来の一時目的（在庫表「-」表示の解消）は `migrations/20260629_010000_backfill_inventory_unit_from_products.sql`（本番 **UPDATE 62件** 確認済み、見出しコメント記載）で既に 2026-06-29 に達成済み。

## 2. PostgreSQL の仕様根拠

- DROP COLUMN は物理的に即時削除せず、カタログ上の attribute（`pg_attribute`）をマークするだけで、残った attnum は再利用されない（カラムスロットは消費済みのまま）という挙動は PostgreSQL の一般的な実装として広く知られているが、本調査では該当する公式ドキュメントの該当ページ（`ALTER TABLE ... DROP COLUMN` の Notes、および `limits.html` の 1600 列上限）を実際に fetch してワーディングを確認するには至っていない。**未確認**（設計側で fetch 済みであれば design.md 側に反映）。

## 3. 本 PR のスコープ

- 触るのは以下 5 ファイルのみ（migrations のうち ADD 側 3 ファイル + INSERT 列リストを持つ 1 ファイル + ADD 側の残り1ファイル、計5）。
  1. `migrations/20260602_000000_add_products_central_columns.sql` — `condition` を ADD リストから削除
  2. `migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql` — `condition` を INSERT/SELECT 列リストから削除
  3. `migrations/20260602_030000_add_products_unit.sql` — 無効化（no-op化）
  4. `migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql` — 無効化（no-op化）
  5. `migrations/20260602_170000_add_products_master_label_columns.sql` — `category_classification` を ADD リストから削除
- **触らない**: `migrations/20260623_020000_drop_products_category_classification.sql`、`migrations/20260629_010000_backfill_inventory_unit_from_products.sql`（列存在ガード済みのため安全、無変更）、`migrations/20260629_020000_drop_products_condition_unit.sql`。いずれも DROP 側・ガード済み側であり、これらを変更すると「永久に DROP され続けている」という既に確定した本番状態と矛盾する。

## 4. 未ガード参照の調査結果（file:line、全件確認済み）

### ブロッキング（今回の変更で対処）

| file:line | 内容 | 判定 |
|---|---|---|
| `migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql:31-37` | `UPDATE public.products p SET unit = ..., condition = ...` | **UNGUARDED** — `information_schema.columns` 等の列存在チェックが無い。今回 no-op 化で対処済み |
| `migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql:82-96` | `INSERT INTO public.products (..., condition, ...) SELECT ..., tp.condition, ... FROM tenant_006.products` | **UNGUARDED**（`work_id NOT NULL` ガードと `tenant_006` 存在ガードはあるが、`condition` 列自体の存在はガードしていない）。今回列リストから `condition` を除去して対処済み |

### 無関係（別テーブル・別列、file:line で確認済み・変更不要）

| file:line | 内容 |
|---|---|
| `migrations/005_add_phase2_tenant_tables.sql:31` | `tenant_NNN.products`（テナントスキーマ）の `condition` 列定義。public.products ではない |
| `migrations/081_create_inventory.sql:16,18,33,44` | `public.inventory` 自身の `condition` 列（別テーブル） |
| `migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql:11-12,47-48,61-62,84-90` | `tenant_NNN.quote_items` / `invoice_items` への `condition`/`unit` 追加（別テーブル） |
| `migrations/20260604_140000_create_own_inventory.sql:36` | 新設テーブル自身の `condition` 列 |
| `migrations/20260703_030000_order_items_ben2.sql:23-24` | `tenant_NNN.order_items`（新設テーブル）自身の `condition`/`unit` 列 |
| `migrations/20260913_150000_tcg_empty_box_condition.sql:31` | `RAISE EXCEPTION` のエラー文字列（列参照ではない） |
| `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql`（全体） | ファイル名に unit/condition を含むが、実際に触るのは `tenant_*.analysis_results.unit_id`/`condition_id`（UUID→INTEGER の別列）と `public.products.product_category_id`。`products.condition`/`products.unit`/`products.category_classification` への参照は無い |
| `migrations/20260623_020000_drop_products_category_classification.sql` | `category_classification` の DROP migration 自身。`information_schema.columns` で列存在ガード済み（`:23-29`） |

### backend / frontend コード

- `backend/`: `products.condition` / `products.unit` / `products.category_classification` への参照は **0件**（grep確認）。
- `frontend/src/pages/quote-create/quoteDraft.ts:14,16`: コメントのみ（`/** 状態（マスタ products.condition）。 */` / `/** 形態（マスタ products.unit。...）。 */`）。実行コードでの列アクセスではない。

## 5. 既存 ADR 検索

- `git grep -i "products.*column\|column.*products"  docs/adr/` および `docs/adr/FEATURE-INDEX.md` を確認。ADR-090（在庫表/商品マスタ public 中央化）・ADR-093（商品マスタ再設計 Phase 1）が関連 ADR として既存（上記 migration のコメント内で参照されている）。本 PR は新しい ADR を起票するものではなく、既存 ADR-090/093 で導入された一時的な列の後始末（インシデント対応）であるため、設計判断としては ADR 本体の変更ではなく docs/handoff 配下のインシデント記録として扱う。
