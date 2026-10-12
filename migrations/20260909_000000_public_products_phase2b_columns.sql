-- Phase 2b prerequisites: ensure public.products has the columns AND data
-- that Phase 2b-modified migrations (20260910_*, 20260913_*) reference.
-- Columns and data are also added by 20260914_140000 (Phase 2a unification),
-- but that migration runs later in sort order. Using IF NOT EXISTS and
-- ON CONFLICT ensures no conflict when 20260914 runs again.

-- ============================================================
-- Step 1: カラム追加
-- ============================================================

-- incident 2026-10-04 (deploy run 37133284790): tcg_uuid は 20260916_120000 で永久 DROP
-- される列。Phase 2c（tcg_products テーブル DROP、migrations/20260915_010000）が完了した後は
-- tcg_uuid は二度と必要にならないため、その状態を過ぎたら再 ADD しない（毎デプロイ ADD→DROP
-- を繰り返すと attribute number を消費し続け、public.products が 1600 列上限に達する）。
--
-- マーカー訂正（2026-10-04、設計担当 Opus の指摘）: 当初は「tenant_*.tcg_products が
-- どこにも残っていない」をマーカーにしていたが、これは誤り。設計担当 Opus が本番を
-- read-only で確認した事実（未確認ではなく確認済み）として、tenant_004.tcg_products は
-- 現在も存在する（Phase 2c の DROP が、tcg_uuid 側の churn バグにより毎回それより手前の
-- ステップで失敗し続けていたため、一度も実行完了に到達していない。作成元:
-- migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:91-92、
-- scripts/run_all_migrations.sh の line 530 と 536 に重複登録されている。この生成元
-- migration はこの PR では変更しない）。この状態で旧マーカーを使うと本番で再び
-- tcg_uuid を ADD しようとして同じ 1600 列上限エラーで失敗する。
--
-- 正しいマーカー: public.products.work_id は migrations/20260919_010000_master_ssot_work_id_recast.sql
-- （scripts/run_all_migrations.sh の tcg_uuid DROP より後、work_id を UUID→INTEGER に
-- 永久変換する）が成功した後は INTEGER のまま変わらない（他のどの migration も
-- public.products.work_id を再び UUID にはしない）。よって
-- 「tcg_uuid が既に存在する」または「work_id が INTEGER でない（未存在 or UUID）」場合のみ
-- ADD + index を実行し、「tcg_uuid が無い かつ work_id が INTEGER」なら恒久的にスキップする。
-- 詳細: docs/handoff/products-column-churn-2/design.md
DO $guard_tcg_uuid$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products'
          AND column_name = 'work_id' AND data_type = 'integer'
    ) THEN
        ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid UUID;

        -- tcg_uuid に部分ユニークインデックス（ON CONFLICT で必要）
        CREATE UNIQUE INDEX IF NOT EXISTS idx_products_tcg_uuid
            ON public.products (tcg_uuid) WHERE tcg_uuid IS NOT NULL;
    ELSE
        RAISE NOTICE 'tcg_uuid: work_id が INTEGER に再キャスト済み（Phase 3 完了）— tcg_uuid 再 ADD をスキップ';
    END IF;
END $guard_tcg_uuid$;

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS division_id       UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS work_id           UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS manufacturer_id   UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS product_category_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS category_class    TEXT;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS is_active         BOOLEAN DEFAULT true;

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-09):
-- tcg_products から public.products への UPSERT（旧 Step2）を外した。
-- 同じ内容は 20260914_140000 の Step2 にあり、本ファイルでは行わない。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: Phase2b tcg_products copy removed'; END $$;
