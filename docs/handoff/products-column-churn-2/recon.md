# Recon: public.products 列 churn 再発（tcg_uuid）— 第2便

**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装・recon)
**インシデント**: PR #3958（commit `26a7a88d3`、マージ済み）適用後の本番デプロイ run **37133284790** が
ステップ **223/317** `migrations/20260909_000000_public_products_phase2b_columns.sql` で
`"tables can have at most 1600 columns"` により再度失敗。

---

## 1. 事実（本番・origin/main、設計担当 Opus が確認済み）

- 第1便（PR #3958）は `condition`/`unit`/`category_classification` の churn を止めたが、
  同じ ADD→DROP パターンを持つ `tcg_uuid` 列を見落としていた。
- 直前のデプロイは ステップ87 を通過（第1便の修正が効いている証拠）し、ステップ173で
  `condition`/`unit` の最終 DROP（想定済みの一回限りの後始末）に成功した。その後ステップ223
  （`migrations/20260909_000000_public_products_phase2b_columns.sql:11` の
  `ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid UUID;`）で列数上限エラーにより失敗。
- 失敗した ALTER TABLE 文自体がロールバックされるため、**tcg_uuid は現在本番に存在しない**。
- 本番 `public.products` の現在の生存列（設計担当 Opus が read-only で確認、57列、attnum降順ではなく実測順）:
  - attnum 1-47: `mark`, `status`, `weight`, `notes`, `tcg_type`, `volume_weight`, `search_keywords`,
    `exclude_keywords`, `related_series`, `required_output_value`, `item`, `product_kind`, `set_type`,
    `display_order` 他、それ以前からの列（`migrations/082_extend_products_box_attributes.sql` 由来の
    `category`/`boxes_per_case`/`packs_per_box`/`box_weight_kg`/`case_weight_kg`/`release_date`/`moq`/
    `hs_code`/`material` 等を含む）
  - attnum 706: `division_id` uuid
  - attnum 707: `work_id_old_uuid` uuid
  - attnum 708: `manufacturer_id` uuid
  - attnum 710: `category_class` text
  - attnum 711: `is_active` boolean
  - attnum 826: `work_id` integer
  - attnum 859: `product_category_id` integer
  - attnum 916: `product_line_id` integer
  - attnum 917: `product_format_id` integer
  - attnum 969: `product_kind_id` integer
  - attnum 1005: `quantity_unit_id` integer
  - attnum 1006: `weight_class_id` integer
  - attnum 1007: `type_master_id` integer
  - **max attnum = 1600**（live 57 + dropped 1543 = 1600。1543 は第1便時点の 1541 ＋ 今回
    条件/unit の最終1回限り DROP が成功した分 +2 で整合）
- `condition`/`unit` はこの run のステップ173で DROP 済み（第1便で想定していた「次回デプロイで
  現在 live 状態の condition/unit を一度だけ最終 DROP」が成功した。再発ではない）。
- **結論**: 1600/1600 で完全に使い切っており、**public.products に対する新規列 ADD は
  （既存名との衝突で IF NOT EXISTS がスキップするケースを除き）すべて失敗する状態**。

## 2. run_all_migrations.sh 全件ウォーク（public.products に列を追加できる全ステートメント）

`scripts/run_all_migrations.sh` の `run_sql`/`run_py` 行を登録順（ファイル内の行番号）に全件走査し、
`public.products`（または動的 `EXECUTE format` でそれを指すもの）に対する
`ALTER TABLE ... ADD COLUMN` / `RENAME COLUMN` / `CREATE TABLE ... AS` を含む全ファイルを洗い出した。
`run_py` 側（scripts/migrate_ 接頭辞の Python スクリプト群）は `ALTER TABLE` 文を grep した結果、products を対象にするものは
0件だった。

| 登録順(行) | file:line | 列 | 次回デプロイ時に live か | 次回デプロイで新 attnum を消費するか（**修正前**） | 後で DROP する file:line |
|---|---|---|---|---|---|
| 108 | `migrations/038_add_products_phase1c_columns.sql` | （tenant_NNN.products 向け、public.products 対象外） | N/A | N/A | N/A |
| 179 | `migrations/082_extend_products_box_attributes.sql:32-41` | category, boxes_per_case, packs_per_box, box_weight_kg, case_weight_kg, release_date, moq, hs_code, material | YES（全列 live） | NO | なし |
| 191 | `migrations/20260623_020000_drop_products_category_classification.sql:60` | category_classification（DROP） | NO（既に無い） | N/A（DROPのみ、ガード済み） | — |
| 216 | `migrations/20260602_000000_add_products_central_columns.sql:17-20` | mark, status, weight, notes（condition は第1便で削除済み） | YES | NO | なし |
| 218 | `migrations/20260602_020000_add_products_tcg_type.sql:7` | tcg_type | YES | NO | なし |
| 219 | `migrations/20260602_030000_add_products_unit.sql` | （第1便で no-op 化済み） | N/A | N/A | — |
| 220 | `migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql` | （第1便で no-op 化済み） | N/A | N/A | — |
| 230 | `migrations/20260602_170000_add_products_master_label_columns.sql:28-33` | volume_weight, search_keywords, exclude_keywords, related_series, required_output_value, item（category_classification は第1便で削除済み） | YES | NO | なし |
| 249 | `migrations/20260603_000000_add_products_product_kind.sql:16-18` | product_kind | YES | NO | なし |
| 261 | `migrations/20260603_040000_add_products_set_type.sql:16-18` | set_type | YES | NO | なし |
| 318 | `migrations/20260605_000000_add_products_display_order.sql:17-19` | display_order | YES | NO | なし |
| 458 | `migrations/20260623_060000_add_products_tcg_type_fk.sql:69-72` | （ADD CONSTRAINT のみ、列追加なし） | N/A | N/A | — |
| 476 | `migrations/20260626_130000_force_rls_public_products.sql:5-6` | （RLS のみ、列追加なし） | N/A | N/A | — |
| 491 | `migrations/20260629_020000_drop_products_condition_unit.sql:5-6` | condition, unit（DROP） | NO（既に無い） | N/A（DROPのみ、ガード済み） | — |
| 524 | `migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:20-37` | （tcg_uuid への ADD CONSTRAINT のみ。列存在ガードあり: `information_schema.columns` チェックで RETURN） | tcg_uuid は NO | N/A（列追加なし、ガードで制約追加もスキップ） | — |
| **628** | **`migrations/20260909_000000_public_products_phase2b_columns.sql:11`** | **tcg_uuid** | **NO** | **YES（バグ本体）** | **`migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:7`** |
| 628 | 同ファイル:12-17 | division_id, work_id(UUID名で ADD), manufacturer_id, product_category_id(UUID名で ADD), category_class, is_active | division_id/manufacturer_id/category_class/is_active は YES。work_id は「work_id」という名前が既に INTEGER で live のため IF NOT EXISTS が名前一致でスキップ。product_category_id も同様（既に INTEGER で live） | NO（全て） | なし（work_id/product_category_id は名前衝突で安全にスキップされるだけで DROP されない） |
| 631,634,637,642 | tcg_note_b2_t004 / tcg_import_message_links / tcg_work_evidence / tcg_resolved_work_id | （tenant_004 スキーマ対象、public.products 対象外） | N/A | N/A | N/A |
| **661** | **`migrations/20260914_140000_unify_tcg_products_to_public.sql:35`** | **tcg_uuid（Step1、20260909 と同一内容の再掲）** | **NO**（628 が本来の意図ではガードされ skip した後の状態を想定すると、628 だけ直してもここが無ガードだと ここで新 attnum を消費してしまう） | **YES（628 を直しても、661 を直さない限りバグが残る）** | `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:7` |
| 661 | 同ファイル:36-41 | division_id, work_id, manufacturer_id, product_category_id, category_class, is_active | 628 と同じ理由で全て live or 名前衝突スキップ | NO | なし |
| 671 | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql` | （public.products への列追加なし。`p.tcg_uuid` を JOIN キーとして読むが、各テーブルごとに `product_id` が既に INTEGER なら丸ごとスキップするガード済み分岐の中でのみ tcg_uuid を参照する） | — | N/A（列追加なし） | — |
| 674 | `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:5-7` | uq_products_tcg_uuid（制約DROP）, idx_products_tcg_uuid（索引DROP）, tcg_uuid（列DROP） | tcg_uuid は YES（628/661 が再 ADD した直後） | N/A（DROPのみ、ガード済み） | — |
| 677 | `migrations/20260916_130000_work_id_not_null.sql` | （列追加なし。`information_schema.columns` でガード済み） | — | N/A | — |
| 692 | `migrations/20260919_010000_master_ssot_work_id_recast.sql:74,107` | work_id（RENAME→work_id_old_uuid、ADD work_id INTEGER） | 両方 `pg_attribute` で既存チェック済み（work_id_old_uuid 存在／work_id が INTEGER で存在）→ 共にスキップ | NO | — |
| 707 | `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:264,302` | product_category_id（ADD tmp INTEGER列→RENAME） | `_atttypid = _int_oid` チェックで既に INTEGER ならスキップ | NO | — |
| 731 | `migrations/20260920_130000_create_product_classification.sql:93-99` | product_line_id, product_format_id | YES | NO | なし（DROP はコメントアウトのみ、未実行） |
| 750 | `migrations/20260921_120000_add_products_product_kind_id.sql:5-6` | product_kind_id | YES | NO | なし |
| 762 | `migrations/20260921_140000_product_classification_masters.sql:76-79` | quantity_unit_id, weight_class_id | YES | NO | なし |
| 768 | `migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql:21` | type_master_id | YES | NO | なし |
| 807 | `migrations/20260924_100000_buyback_product_matching.sql` | （`public.buyback_shop_products`、別テーブル。public.products 対象外） | N/A | N/A | N/A |

**結論**: 修正前の状態で次回デプロイ時に新規 attnum を消費する（かつ 1600 上限のため確実に失敗する）
のは `tcg_uuid` のみ。2ファイル（628・661）の両方に同一の無ガード ADD が存在するため、
片方だけ直すと残った方で同じ問題が再発する。

## 3. 他テーブルの churn 有無の確認

全 migrations の `DROP COLUMN` を対象テーブル別に集計したところ、`public.products` 以外の
テーブルで同名列を複数ファイルにわたって ADD→DROP している例は見つからなかった
（`public.discord_inbound_messages.version` のみ2回 DROP 文があるが、片方は別日程の重複登録
チェック用でどちらも「ADD されたことがない列への DROP IF EXISTS」であり、churn ではない）。
設計担当 Opus が確認した「他テーブルの dropped attribute 数の最大は3件」という事実と整合する。
よって本件は `public.products` に限定される。

## 4. 既存 ADR 検索

ADR-1001（tcg_products → public.products 統合）・ADR-1002（マスタ SSOT 型統一）が関連。
本件はこれらの ADR で導入された一時列（tcg_uuid）の後始末であり、新規 ADR は起票しない
（第1便の recon.md と同じ方針）。
