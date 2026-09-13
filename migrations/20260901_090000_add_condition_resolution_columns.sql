-- Migration: add_condition_resolution_columns
--
-- 背景:
--   TCG 状態解決エンジンを GAS の R1〜R4 ロジックに合わせるため、
--   tenant_004.conditions に不足していた 3 列を追加し、
--   GAS 状態マスタの実データで seed する。
--
-- 設計判断:
--   - additive-only: 列追加のみ。既存列・行を削除/変更しない
--   - 冪等性: ADD COLUMN IF NOT EXISTS + UPDATE (WHERE code IN ...)
--   - tenant_004 のみ対象（他テナントループなし）
--   - app_kubun 列は既存（空欄）。priority / search_kw / exclude_kw は今回追加
--   - units.kubun は既存・値投入済み → 今回変更なし
--
-- 出典: GAS backupConditionMaster07() 実測値 2026-09-01
--   CN0001 Case        / 優先度4 / 適用区分:箱系大
--   CN0002 Damaged case/ 優先度2 / 適用区分:箱系大
--   CN0003 Sealed box  / 優先度4 / 適用区分:箱系
--   CN0004 Damaged sealed box / 優先度2 / 適用区分:箱系
--   CN0005 No shrink box / 優先度3 / 適用区分:(空=全)
--   CN0006 Opened box  / 優先度3 / 適用区分:(空=全)
--   CN0007 Unsearched pack / 優先度3 / 適用区分:(空=全)
--   CN0008 FLAG_SINGLE / 優先度1 / 適用区分:枚系,単位不明
--   CN0009 Opened case / 優先度2 / 適用区分:箱系大
--   CN0010 Searched pack / 優先度2 / 適用区分:パック系
--
-- 作成日: 2026-09-01

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ----------------------------------------------------------------
    -- ガード: tenant_004 が存在しない場合はスキップ
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260901_090000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- ----------------------------------------------------------------
    -- Step 1: conditions テーブルに列追加 (additive-only)
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'conditions' AND column_name = 'priority'
    ) THEN
        EXECUTE format('ALTER TABLE %I.conditions ADD COLUMN priority INTEGER', _schema);
        RAISE NOTICE 'migration 20260901_090000: added conditions.priority';
    ELSE
        RAISE NOTICE 'migration 20260901_090000: conditions.priority already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'conditions' AND column_name = 'search_kw'
    ) THEN
        EXECUTE format($q$ALTER TABLE %I.conditions ADD COLUMN search_kw TEXT NOT NULL DEFAULT ''$q$, _schema);
        RAISE NOTICE 'migration 20260901_090000: added conditions.search_kw';
    ELSE
        RAISE NOTICE 'migration 20260901_090000: conditions.search_kw already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'conditions' AND column_name = 'exclude_kw'
    ) THEN
        EXECUTE format($q$ALTER TABLE %I.conditions ADD COLUMN exclude_kw TEXT NOT NULL DEFAULT ''$q$, _schema);
        RAISE NOTICE 'migration 20260901_090000: added conditions.exclude_kw';
    ELSE
        RAISE NOTICE 'migration 20260901_090000: conditions.exclude_kw already exists, skipping';
    END IF;

    -- ----------------------------------------------------------------
    -- Step 2: 優先度インデックス
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = _schema AND tablename = 'conditions'
          AND indexname = 'idx_conditions_priority'
    ) THEN
        EXECUTE format(
            'CREATE INDEX idx_conditions_priority ON %I.conditions (priority ASC NULLS LAST)',
            _schema
        );
        RAISE NOTICE 'migration 20260901_090000: created idx_conditions_priority';
    END IF;

    -- ----------------------------------------------------------------
    -- Step 3: 既存列 app_kubun + 新列 priority / search_kw / exclude_kw を seed
    --
    -- 冪等: WHERE code IN (...) で対象を限定。
    --        既存値を上書きする（priority/search_kw/exclude_kw は新規追加列なので NULL or ''）。
    --        app_kubun は既存列だが全行空欄のため上書き安全（バックアップ確認済み）。
    -- ----------------------------------------------------------------
    EXECUTE format($seed$
        UPDATE %I.conditions
        SET
            app_kubun  = CASE code
                WHEN 'CN0001' THEN '箱系大'
                WHEN 'CN0002' THEN '箱系大'
                WHEN 'CN0003' THEN '箱系'
                WHEN 'CN0004' THEN '箱系'
                WHEN 'CN0005' THEN ''
                WHEN 'CN0006' THEN ''
                WHEN 'CN0007' THEN ''
                WHEN 'CN0008' THEN '枚系,単位不明'
                WHEN 'CN0009' THEN '箱系大'
                WHEN 'CN0010' THEN 'パック系'
                ELSE app_kubun
            END,
            priority   = CASE code
                WHEN 'CN0001' THEN 4
                WHEN 'CN0002' THEN 2
                WHEN 'CN0003' THEN 4
                WHEN 'CN0004' THEN 2
                WHEN 'CN0005' THEN 3
                WHEN 'CN0006' THEN 3
                WHEN 'CN0007' THEN 3
                WHEN 'CN0008' THEN 1
                WHEN 'CN0009' THEN 2
                WHEN 'CN0010' THEN 2
                ELSE priority
            END,
            search_kw  = CASE code
                WHEN 'CN0001' THEN '通常品,[通常品]'
                WHEN 'CN0002' THEN '傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B'
                WHEN 'CN0003' THEN '通常品,[通常品],未開封,新品未開封,新品,シュリンク付き,シュリ付,シュリ付き,シュリンクあり,シュリ有り,シュリ有'
                WHEN 'CN0004' THEN '傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B'
                WHEN 'CN0005' THEN 'シュリなし,シュリ無し,シュリ無,シュリンクなし,シュリンク無し,シュリンク無,no shrink'
                WHEN 'CN0006' THEN 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み'
                WHEN 'CN0007' THEN '未サーチ,サーチなし,サーチ痕なし,サーチ痕無し,サーチ無し'
                WHEN 'CN0008' THEN 'PSA,BGS,CGC,ARS,鑑定,SAR,SR,UR,CHR,プロモ,連番,単品,枚'
                WHEN 'CN0009' THEN 'カートンテープカット,テープカット済,テープカット,テープ切'
                WHEN 'CN0010' THEN 'サーチ済,サーチ済み'
                ELSE search_kw
            END,
            exclude_kw = CASE code
                WHEN 'CN0001' THEN '傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B'
                WHEN 'CN0002' THEN ''
                WHEN 'CN0003' THEN '傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B'
                WHEN 'CN0004' THEN ''
                WHEN 'CN0005' THEN ''
                WHEN 'CN0006' THEN ''
                WHEN 'CN0007' THEN '[サーチ済み]'
                WHEN 'CN0008' THEN ''
                WHEN 'CN0009' THEN ''
                WHEN 'CN0010' THEN '未サーチ,サーチ痕なし'
                ELSE exclude_kw
            END
        WHERE code IN (
            'CN0001','CN0002','CN0003','CN0004','CN0005',
            'CN0006','CN0007','CN0008','CN0009','CN0010'
        )
    $seed$, _schema);

    RAISE NOTICE 'migration 20260901_090000: seeded conditions R1-R4 columns (10 rows)';

END;
$$;
