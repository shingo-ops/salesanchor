# Recon: public.products tcg_uuid 未ガード参照の再発（第3便）

**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装・recon)
**インシデント**: PR #3958(`26a7a88d3`)・PR #3959(`f4df2b756`) マージ後、2026-10-04 デプロイ
run **37135632445** がステップ238 `migrations/20260913_200000_tcg_cardset_exclusion.sql` で
`ERROR: column p.tcg_uuid does not exist` により失敗。

---

## 1. 事実（設計担当 Opus が確認済み。本書では未確認のプロダクション事実を事実として書かない）

- run 37135632445 はステップ223（第2便 #3959 が修正した `tcg_uuid` ADD churn）を通過した
  （= 列数上限の再発は無かった）。
- 失敗箇所は `migrations/20260913_200000_tcg_cardset_exclusion.sql` の
  `_pid_col := 'tcg_uuid'` を選んだ分岐（:27、`tenant_004.product_search_keywords.product_id`
  が int4 でないため ELSE に入る）の後、`EXECUTE format('SELECT p.%I AS pid FROM
  public.products p WHERE p.product_code = $1', _pid_col)`（:44）で `tcg_uuid` 列に
  アクセスして失敗。
- 原因: 第1便・第2便の手動ウォークは `scripts/run_all_migrations.sh` の
  **628〜674の範囲のみ**を対象にしており、それより手前（651・652）にある同じパターンの
  未ガード参照を見落としていた。

## 2. `tcg_uuid` の全件スキャン（登録済み全 `run_sql`/`run_py`、非コメント行）

`scripts/run_all_migrations.sh` の `run_sql`/`run_py` 行を全件抽出し、各対象ファイルで
`tcg_uuid` を含む非コメント行（`--` で始まる行を除外）を機械的に再スキャンした。生出力:

```
scripts/run_all_migrations.sh:524 [run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql] -> migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:24:        SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
scripts/run_all_migrations.sh:524 [run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql] -> migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:26:        RAISE NOTICE 'public.products.tcg_uuid column does not exist — skipping UNIQUE constraint';
scripts/run_all_migrations.sh:524 [run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql] -> migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:30:        SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'products' AND constraint_name = 'uq_products_tcg_uuid'
scripts/run_all_migrations.sh:524 [run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql] -> migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:33:            ALTER TABLE public.products ADD CONSTRAINT uq_products_tcg_uuid UNIQUE (tcg_uuid);
scripts/run_all_migrations.sh:524 [run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql] -> migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:34:            RAISE NOTICE 'Created UNIQUE constraint uq_products_tcg_uuid on public.products';
scripts/run_all_migrations.sh:524 [run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql] -> migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:36:            RAISE NOTICE 'Cannot create uq_products_tcg_uuid (duplicate values): %', SQLERRM;
scripts/run_all_migrations.sh:524 [run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql] -> migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:39:        RAISE NOTICE 'uq_products_tcg_uuid already exists — skipping';
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:33:DO $guard_tcg_uuid$
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:37:        WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:43:        ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid UUID;
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:46:        CREATE UNIQUE INDEX IF NOT EXISTS idx_products_tcg_uuid
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:47:            ON public.products (tcg_uuid) WHERE tcg_uuid IS NOT NULL;
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:49:        RAISE NOTICE 'tcg_uuid: work_id が INTEGER に再キャスト済み（Phase 3 完了）— tcg_uuid 再 ADD をスキップ';
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:51:END $guard_tcg_uuid$;
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:106:                tcg_uuid, division_id, work_id, manufacturer_id, product_category_id,
scripts/run_all_migrations.sh:628 [run_sql migrations/20260909_000000_public_products_phase2b_columns.sql] -> migrations/20260909_000000_public_products_phase2b_columns.sql:128:                tcg_uuid             = EXCLUDED.tcg_uuid,
scripts/run_all_migrations.sh:651 [run_sql migrations/20260913_200000_tcg_cardset_exclusion.sql] -> migrations/20260913_200000_tcg_cardset_exclusion.sql:27:        _pid_col := 'tcg_uuid';
scripts/run_all_migrations.sh:652 [run_sql migrations/20260913_210000_tcg_cardset_bundle_registration.sql] -> migrations/20260913_210000_tcg_cardset_bundle_registration.sql:29:        _pid_col := 'tcg_uuid';
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:48:DO $guard_tcg_uuid$
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:52:        WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:58:        ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid UUID;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:61:        CREATE UNIQUE INDEX IF NOT EXISTS idx_products_tcg_uuid
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:62:            ON public.products (tcg_uuid) WHERE tcg_uuid IS NOT NULL;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:68:              AND conname = 'uq_products_tcg_uuid'
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:71:            ALTER TABLE public.products ADD CONSTRAINT uq_products_tcg_uuid UNIQUE (tcg_uuid);
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:74:        RAISE NOTICE 'tcg_uuid: work_id が INTEGER に再キャスト済み（Phase 3 完了）— tcg_uuid 再 ADD をスキップ';
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:76:END $guard_tcg_uuid$;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:94:    _tcg_uuid_is_uuid            BOOLEAN;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:114:          AND a.attname = 'tcg_uuid'
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:118:    ) INTO _tcg_uuid_is_uuid;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:120:    IF NOT _tcg_uuid_is_uuid THEN
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:121:        RAISE NOTICE 'Step2: public.products.tcg_uuid が UUID 型で存在しません（Phase 2c 適用済み or DROP 済み）。Step2 をスキップします。';
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:182:                    tcg_uuid, division_id, work_id, manufacturer_id, product_category_id,
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:204:                    tcg_uuid             = EXCLUDED.tcg_uuid,
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:218:                    tcg_uuid, division_id, work_id, manufacturer_id, product_category_id,
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:240:                    tcg_uuid             = EXCLUDED.tcg_uuid,
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:253:                    tcg_uuid, division_id, work_id, manufacturer_id, product_category_id,
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:275:                    tcg_uuid             = EXCLUDED.tcg_uuid,
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:301:    _tcg_uuid_is_uuid BOOLEAN;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:313:          AND a.attname = 'tcg_uuid'
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:317:    ) INTO _tcg_uuid_is_uuid;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:319:    IF NOT _tcg_uuid_is_uuid THEN
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:320:        RAISE NOTICE 'Step3: public.products.tcg_uuid が UUID 型で存在しません。FK 張替えをスキップします。';
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:384:                    REFERENCES public.products (tcg_uuid)
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:441:                    REFERENCES public.products (tcg_uuid)
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:498:                    REFERENCES public.products (tcg_uuid)
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:555:                    REFERENCES public.products (tcg_uuid)
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:579:    _tcg_uuid_is_uuid BOOLEAN;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:602:          AND a.attname = 'tcg_uuid'
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:606:    ) INTO _tcg_uuid_is_uuid;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:608:    IF NOT _tcg_uuid_is_uuid THEN
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:609:        RAISE NOTICE 'Step4: public.products.tcg_uuid が UUID 型で存在しません（Phase 2c 適用済み）— 件数照合をスキップ';
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:630:    WHERE tcg_uuid IS NOT NULL;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:633:    RAISE NOTICE 'Step4: public.products WHERE tcg_uuid IS NOT NULL = %', public_count;
scripts/run_all_migrations.sh:661 [run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql] -> migrations/20260914_140000_unify_tcg_products_to_public.sql:637:            'Step4 FAILED: 件数不一致。tcg合計=% vs public.products(tcg_uuid IS NOT NULL)=%. 移行に問題があります。',
scripts/run_all_migrations.sh:665 [run_sql migrations/20260922_040000_fix_phase2c_fk_blocker.sql] -> migrations/20260922_040000_fix_phase2c_fk_blocker.sql:53:      REFERENCES public.products(tcg_uuid);
scripts/run_all_migrations.sh:671 [run_sql migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql] -> migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:52:                WHERE p.tcg_uuid = sk.product_id
scripts/run_all_migrations.sh:671 [run_sql migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql] -> migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:127:                WHERE p.tcg_uuid = ek.product_id
scripts/run_all_migrations.sh:671 [run_sql migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql] -> migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:197:                    WHERE p.tcg_uuid = pl.product_id
scripts/run_all_migrations.sh:671 [run_sql migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql] -> migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:282:                    WHERE p.tcg_uuid = ar.product_id
scripts/run_all_migrations.sh:671 [run_sql migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql] -> migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:348:            EXECUTE format('UPDATE %I.analysis_run_snapshots ars SET product_int_id = p.id FROM public.products p WHERE p.tcg_uuid = ars.product_id', _schema);
scripts/run_all_migrations.sh:674 [run_sql migrations/20260916_120000_phase_c_drop_tcg_uuid.sql] -> migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:5:ALTER TABLE public.products DROP CONSTRAINT IF EXISTS uq_products_tcg_uuid;
scripts/run_all_migrations.sh:674 [run_sql migrations/20260916_120000_phase_c_drop_tcg_uuid.sql] -> migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:6:DROP INDEX IF EXISTS idx_products_tcg_uuid;
scripts/run_all_migrations.sh:674 [run_sql migrations/20260916_120000_phase_c_drop_tcg_uuid.sql] -> migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:7:ALTER TABLE public.products DROP COLUMN IF EXISTS tcg_uuid;
```

run_py 側（`scripts/migrate_*` Python スクリプト群、登録済み全件）を同様に走査した結果、
`tcg_uuid` を含む行は **0件**。

### 判定（designer 提示の8箇所 + 今回の再確認）

| line | file | 判定 | 根拠 |
|---|---|---|---|
| 524 | `migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:20-28` | **GUARDED** | `IF NOT EXISTS (tcg_uuid列) THEN RAISE NOTICE; RETURN; END IF;` が制約追加の前に存在（再確認済み） |
| 628 | `migrations/20260909_000000_public_products_phase2b_columns.sql:18-37` | **GUARDED**（第2便で修正） | `work_id` INTEGER マーカーで ADD/索引をガード |
| **651** | `migrations/20260913_200000_tcg_cardset_exclusion.sql:27` | **UNGUARDED → 本PRで修正** | `_pid_col := 'tcg_uuid'` の直後に tcg_uuid 列存在チェックが無かった |
| **652** | `migrations/20260913_210000_tcg_cardset_bundle_registration.sql:29` | **UNGUARDED → 本PRで修正** | 同上パターン |
| 661 | `migrations/20260914_140000_unify_tcg_products_to_public.sql:48-76, 94-122, 301-321, 579-611` | **GUARDED**（第2便で修正・既存自己ガード） | Step1は`work_id`マーカー、Step2/3/4は`tcg_uuid`型チェックで`RETURN` |
| 665 | `migrations/20260922_040000_fix_phase2c_fk_blocker.sql:53` | **GUARDED** | 後述§3で型チェックを確認 |
| 671 | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:52,127,197,282,348` | **GUARDED** | 各テーブルの `product_id` が既に INTEGER なら該当ブロックに入らない（`IF _atttypid=_int_oid THEN skip`） |
| 674 | `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:5-7` | **GUARDED** | `IF EXISTS`/`DROP ... IF EXISTS` |

## 3. 665（`migrations/20260922_040000_fix_phase2c_fk_blocker.sql`）のガード再確認

```
cat -n migrations/20260922_040000_fix_phase2c_fk_blocker.sql (抜粋)
```
この行（:53、`REFERENCES public.products(tcg_uuid)`）はFK再作成文の中にあり、ファイル冒頭で
対象テナントの `product_id` が UUID型かどうかを型チェックしてから実行する分岐の内側にある
（他の671ファイルと同じ「product_idが既にINTEGERなら実行しない」パターン）。本 PR では
このファイルを変更しない。

## 4. `products.condition`/`products.unit`/`products.category_classification` の全件スキャン

同じ方法で `scripts/run_all_migrations.sh` 登録済み全ファイルを再スキャンした（非コメント行、
`\bcondition\b`・`\bunit\b`・`category_classification` を含む行）。生出力:

```
scripts/run_all_migrations.sh:178 migrations/081_create_inventory.sql:33:    condition       VARCHAR(50) NOT NULL,
scripts/run_all_migrations.sh:178 migrations/081_create_inventory.sql:44:    UNIQUE (supplier_id, product_id, condition)
scripts/run_all_migrations.sh:181 migrations/084_add_unit_to_inventory.sql:26:        ALTER TABLE public.inventory ADD COLUMN IF NOT EXISTS unit VARCHAR(20);
scripts/run_all_migrations.sh:181 migrations/084_add_unit_to_inventory.sql:27:        COMMENT ON COLUMN public.inventory.unit IS
scripts/run_all_migrations.sh:181 migrations/084_add_unit_to_inventory.sql:30:        RAISE NOTICE 'public.inventory not present; skipping unit column add';
scripts/run_all_migrations.sh:182 migrations/20260620_010000_create_inventory_aggregation_rules.sql:17:    condition TEXT NOT NULL,
scripts/run_all_migrations.sh:182 migrations/20260620_010000_create_inventory_aggregation_rules.sql:22:    CONSTRAINT inventory_aggregation_rules_condition_key UNIQUE (condition)
scripts/run_all_migrations.sh:182 migrations/20260620_010000_create_inventory_aggregation_rules.sql:26:    (condition, price_tolerance, stock_tolerance)
scripts/run_all_migrations.sh:182 migrations/20260620_010000_create_inventory_aggregation_rules.sql:32:ON CONFLICT (condition) DO UPDATE SET
scripts/run_all_migrations.sh:185 migrations/20260623_040000_make_inventory_condition_nullable.sql:12:          AND column_name = 'condition'
scripts/run_all_migrations.sh:185 migrations/20260623_040000_make_inventory_condition_nullable.sql:15:            ALTER COLUMN condition DROP NOT NULL;
scripts/run_all_migrations.sh:186 migrations/20260623_020000_create_inventory_offer_v2_unique_key.sql:29:        COALESCE(unit, ''),
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:9:CREATE TABLE IF NOT EXISTS public.products_category_classification_backup (
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:14:    category_classification VARCHAR(100) NOT NULL,
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:28:          AND column_name = 'category_classification'
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:33:            INSERT INTO public.products_category_classification_backup (
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:38:                category_classification,
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:46:                category_classification,
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:49:            WHERE category_classification IS NOT NULL
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:54:                category_classification = EXCLUDED.category_classification,
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:58:        RAISE NOTICE 'migration 20260623_020000: backed up % products.category_classification rows', backed_up_rows;
scripts/run_all_migrations.sh:191 migrations/20260623_020000_drop_products_category_classification.sql:60:        EXECUTE 'ALTER TABLE public.products DROP COLUMN IF EXISTS category_classification';
scripts/run_all_migrations.sh:233 migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql:47:          AND column_name = 'condition'
scripts/run_all_migrations.sh:233 migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql:51:        RAISE NOTICE 'public.inventory has no condition column; skipping ADR-093 Phase 3a changes';
scripts/run_all_migrations.sh:233 migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql:59:    ALTER TABLE public.inventory ADD COLUMN IF NOT EXISTS unit VARCHAR(20);
scripts/run_all_migrations.sh:233 migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql:78:            supplier_id, product_id, condition,
scripts/run_all_migrations.sh:233 migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql:79:            COALESCE(unit, ''), offer_type, COALESCE(ship_timing, '')
scripts/run_all_migrations.sh:270 migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql:47:            EXECUTE format('ALTER TABLE %I.quote_items ADD COLUMN IF NOT EXISTS condition VARCHAR(50)', schema_rec.nspname);
scripts/run_all_migrations.sh:270 migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql:48:            EXECUTE format('ALTER TABLE %I.quote_items ADD COLUMN IF NOT EXISTS unit VARCHAR(20)', schema_rec.nspname);
scripts/run_all_migrations.sh:270 migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql:50:            RAISE NOTICE 'migration 20260604_030000: %.quote_items に name_en/condition/unit を追加', schema_rec.nspname;
scripts/run_all_migrations.sh:270 migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql:61:            EXECUTE format('ALTER TABLE %I.invoice_items ADD COLUMN IF NOT EXISTS condition VARCHAR(50)', schema_rec.nspname);
scripts/run_all_migrations.sh:270 migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql:62:            EXECUTE format('ALTER TABLE %I.invoice_items ADD COLUMN IF NOT EXISTS unit VARCHAR(20)', schema_rec.nspname);
scripts/run_all_migrations.sh:270 migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql:64:            RAISE NOTICE 'migration 20260604_030000: %.invoice_items に name_en/condition/unit を追加', schema_rec.nspname;
scripts/run_all_migrations.sh:285 migrations/20260604_140000_create_own_inventory.sql:36:                condition      VARCHAR(50),
scripts/run_all_migrations.sh:309 migrations/20260604_170000_create_product_attribute_masters.sql:23:    attribute   VARCHAR(40)  NOT NULL,   -- product_kind / set_type / rarity / language / unit / hs_code / item / material
scripts/run_all_migrations.sh:309 migrations/20260604_170000_create_product_attribute_masters.sql:94:    ('unit', 'piece', 'piece', 'piece', 10),
scripts/run_all_migrations.sh:309 migrations/20260604_170000_create_product_attribute_masters.sql:95:    ('unit', 'pack',  'pack',  'pack',  20),
scripts/run_all_migrations.sh:309 migrations/20260604_170000_create_product_attribute_masters.sql:96:    ('unit', 'box',   'box',   'box',   30),
scripts/run_all_migrations.sh:309 migrations/20260604_170000_create_product_attribute_masters.sql:97:    ('unit', 'case',  'case',  'case',  40),
scripts/run_all_migrations.sh:309 migrations/20260604_170000_create_product_attribute_masters.sql:98:    ('unit', 'set',   'set',   'set',   50),
scripts/run_all_migrations.sh:467 migrations/20260624_140000_converge_inventory_v2.sql:14:ALTER TABLE public.inventory DROP COLUMN IF EXISTS condition;
scripts/run_all_migrations.sh:482 migrations/20260629_010000_backfill_inventory_unit_from_products.sql:11:     WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'unit'
scripts/run_all_migrations.sh:482 migrations/20260629_010000_backfill_inventory_unit_from_products.sql:14:     WHERE table_schema = 'public' AND table_name = 'inventory' AND column_name = 'unit'
scripts/run_all_migrations.sh:482 migrations/20260629_010000_backfill_inventory_unit_from_products.sql:17:       SET unit = p.unit
scripts/run_all_migrations.sh:482 migrations/20260629_010000_backfill_inventory_unit_from_products.sql:20:       AND (i.unit IS NULL OR i.unit = '')
scripts/run_all_migrations.sh:482 migrations/20260629_010000_backfill_inventory_unit_from_products.sql:21:       AND p.unit IS NOT NULL;
scripts/run_all_migrations.sh:491 migrations/20260629_020000_drop_products_condition_unit.sql:5:ALTER TABLE public.products DROP COLUMN IF EXISTS condition;
scripts/run_all_migrations.sh:491 migrations/20260629_020000_drop_products_condition_unit.sql:6:ALTER TABLE public.products DROP COLUMN IF EXISTS unit;
scripts/run_all_migrations.sh:506 migrations/20260703_030000_order_items_ben2.sql:23:        condition VARCHAR(50),
scripts/run_all_migrations.sh:506 migrations/20260703_030000_order_items_ben2.sql:24:        unit VARCHAR(20),
scripts/run_all_migrations.sh:560 migrations/20260903_160000_tcg_normalization_rules_t004.sql:181:            ('NR0133', 'CONDITION', 'REGEX_REPLACE', '[　]+', ' ', TRUE, 1000, 'existing condition whitespace normalization'),
scripts/run_all_migrations.sh:560 migrations/20260903_160000_tcg_normalization_rules_t004.sql:182:            ('NR0134', 'CONDITION', 'REGEX_REPLACE', '\s+', ' ', TRUE, 1010, 'existing condition whitespace normalization'),
scripts/run_all_migrations.sh:600 migrations/20260907_100000_tcg_note_master_expand_t004.sql:51:        ('NJ049','美品','Mint condition',TRUE,'美品','','外装系',3),
scripts/run_all_migrations.sh:641 migrations/20260910_200000_tcg_condition_note_delivery_t004.sql:17:        RAISE NOTICE 'condition note: partial structure (% of 2 tables), skipping (SSOT migration moved to public)', table_count;
scripts/run_all_migrations.sh:641 migrations/20260910_200000_tcg_condition_note_delivery_t004.sql:33:        RAISE EXCEPTION 'condition note: NJ079 identity collision';
scripts/run_all_migrations.sh:650 migrations/20260913_150000_tcg_empty_box_condition.sql:31:        RAISE EXCEPTION 'empty box: conflicting condition identities';
scripts/run_all_migrations.sh:707 migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:20:    _tbl_u   TEXT := 'unit' || 's';
scripts/run_all_migrations.sh:707 migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:21:    _tbl_c   TEXT := 'condition' || 's';
scripts/run_all_migrations.sh:740 migrations/20260921_090000_create_condition_definitions.sql:56:COMMENT ON TABLE public.condition_definitions IS 'コンディション定義マスタ（ADR-156）。product_lines（小分類）ごとのコンディション定義。解析マスタ（condition 解析テーブル）の正規化参照元。';
```

run_py 側は同条件で 0件。

### 判定（全57ヒット、public.products への未ガード参照は0件）

| ヒット群（ファイル名） | 対象 | 判定 |
|---|---|---|
| 081_create_inventory.sql・084_add_unit_to_inventory.sql・20260620_010000_create_inventory_aggregation_rules.sql・20260623_040000_make_inventory_condition_nullable.sql・20260623_020000_create_inventory_offer_v2_unique_key.sql・20260602_180000_add_inventory_offer_type_ship_timing.sql・20260624_140000_converge_inventory_v2.sql | `public.inventory` / `inventory_aggregation_rules` / `inventory_offer_v2` 自身の `condition`/`unit` 列 | **無関係**（別テーブル） |
| 20260623_020000_drop_products_category_classification.sql | `category_classification` の DROP 本体（既存ガード済み） | **無関係**（既にガード済み・PR #3958対応済み・無変更） |
| 20260604_030000_add_quote_invoice_item_overseas_columns.sql | `tenant_NNN.quote_items`/`invoice_items` の `condition`/`unit` | **無関係**（別テーブル） |
| 20260604_140000_create_own_inventory.sql | own-inventory テーブル自身の `condition` | **無関係**（別テーブル） |
| 20260604_170000_create_product_attribute_masters.sql | マスタテーブルへの `'unit'` という**文字列値**の INSERT（属性名としてのデータ値） | **無関係**（列参照ではない） |
| 20260629_010000_backfill_inventory_unit_from_products.sql | `p.unit`（`public.products.unit`）読み取り | **GUARDED**（:9-15 で `products.unit`/`inventory.unit` 両方の列存在を確認してから実行。PR #3958 以降無変更・再確認済み） |
| 20260629_020000_drop_products_condition_unit.sql | `condition`/`unit` の DROP 本体 | **無関係**（既にガード済み・PR #3958対応済み・無変更） |
| 20260703_030000_order_items_ben2.sql | `tenant_NNN.order_items` 自身の `condition`/`unit` | **無関係**（別テーブル） |
| 20260903_160000_tcg_normalization_rules_t004.sql・20260907_100000_tcg_note_master_expand_t004.sql・20260910_200000_tcg_condition_note_delivery_t004.sql・20260913_150000_tcg_empty_box_condition.sql・20260921_090000_create_condition_definitions.sql | 文字列リテラル・エラーメッセージ・コメント中の "condition" | **無関係**（列参照ではない） |
| 20260920_010000_phase3_fk_rewire_unit_condition.sql | `'unit'||'s'`・`'condition'||'s'` でテーブル名 `units`/`conditions`（別マスタテーブル）を組み立てる変数 | **無関係**（`public.products.unit`/`.condition` ではない） |

**結論**: `products.condition`/`products.unit`/`products.category_classification` への
未ガード参照は無し（PR #3958 で対応済みの箇所以外に新規発見は無し）。

## 5. 既存 ADR 検索

ADR-1001（tcg_products → public.products 統合）・ADR-1002（マスタ SSOT 型統一）・ADR-155 が関連。
本件はこれらの ADR で導入された一時列・一時ロジックの後始末（第3便）であり、新規 ADR は起票しない。
