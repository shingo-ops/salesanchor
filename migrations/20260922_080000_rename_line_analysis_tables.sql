-- ============================================================
-- LINE解析テーブルリネーム（Phase 1: RENAME + 後方互換VIEW）
-- ============================================================
-- 目的: LINE解析用テーブルを正式マスタ（quantity_units / condition_definitions）
--       と明確に区別するため、テーブル名に line_ 接頭辞を付与する。
-- 安全: 旧名で VIEW を作成するため、既存コードは変更不要。
--       FK・INDEX は RENAME に自動追従する。
-- 冪等: IF EXISTS / IF NOT EXISTS で二重実行可。
-- 値操作: なし（DDLのみ）
-- ============================================================

-- Step 1: units → line_units
-- units: LINEメッセージから抽出した販売単位を格納するマスタ。
-- 「ボックス」「パック」「カートン」等の単位名と、解析パイプラインでの
-- 正規化ルールを保持する。正式な販売単位マスタ（quantity_units）とは別物。
DO $$
BEGIN
    -- テーブルが存在し、かつまだリネームされていない場合のみ
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'units' AND table_type = 'BASE TABLE') THEN
        ALTER TABLE public.units RENAME TO line_units;
        RAISE NOTICE 'Renamed public.units → public.line_units';
    ELSE
        RAISE NOTICE 'public.units (BASE TABLE) does not exist — skipping rename';
    END IF;
END $$;

-- 後方互換 VIEW
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'units') THEN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_units') THEN
            CREATE VIEW public.units AS TABLE public.line_units;
            RAISE NOTICE 'Created backward-compat VIEW public.units → public.line_units';
        END IF;
    ELSE
        RAISE NOTICE 'VIEW public.units already exists — skipping';
    END IF;
END $$;

-- Step 2: unit_aliases → line_unit_aliases
-- unit_aliases: LINE解析用単位の別名テーブル。「BOX」「箱」→「ボックス」のように、
-- 表記揺れを正規の単位名に紐づける。units テーブルの子テーブル。
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'unit_aliases' AND table_type = 'BASE TABLE') THEN
        ALTER TABLE public.unit_aliases RENAME TO line_unit_aliases;
        RAISE NOTICE 'Renamed public.unit_aliases → public.line_unit_aliases';
    ELSE
        RAISE NOTICE 'public.unit_aliases (BASE TABLE) does not exist — skipping rename';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'unit_aliases') THEN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_unit_aliases') THEN
            CREATE VIEW public.unit_aliases AS TABLE public.line_unit_aliases;
            RAISE NOTICE 'Created backward-compat VIEW public.unit_aliases → public.line_unit_aliases';
        END IF;
    ELSE
        RAISE NOTICE 'VIEW public.unit_aliases already exists — skipping';
    END IF;
END $$;

-- Step 3: conditions → line_conditions
-- conditions: LINEメッセージから抽出した商品状態を格納するマスタ。
-- 「未開封」「美品」「傷あり」等の状態名を保持する。
-- 正式な商品状態マスタ（condition_definitions）とは別物。
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'conditions' AND table_type = 'BASE TABLE') THEN
        ALTER TABLE public.conditions RENAME TO line_conditions;
        RAISE NOTICE 'Renamed public.conditions → public.line_conditions';
    ELSE
        RAISE NOTICE 'public.conditions (BASE TABLE) does not exist — skipping rename';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'conditions') THEN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_conditions') THEN
            CREATE VIEW public.conditions AS TABLE public.line_conditions;
            RAISE NOTICE 'Created backward-compat VIEW public.conditions → public.line_conditions';
        END IF;
    ELSE
        RAISE NOTICE 'VIEW public.conditions already exists — skipping';
    END IF;
END $$;

-- Step 4: condition_aliases → line_condition_aliases
-- condition_aliases: LINE解析用状態の別名テーブル。「新品未開封」「シュリンク付き」→「未開封」のように、
-- 表記揺れを正規の状態名に紐づける。conditions テーブルの子テーブル。
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'condition_aliases' AND table_type = 'BASE TABLE') THEN
        ALTER TABLE public.condition_aliases RENAME TO line_condition_aliases;
        RAISE NOTICE 'Renamed public.condition_aliases → public.line_condition_aliases';
    ELSE
        RAISE NOTICE 'public.condition_aliases (BASE TABLE) does not exist — skipping rename';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'condition_aliases') THEN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_condition_aliases') THEN
            CREATE VIEW public.condition_aliases AS TABLE public.line_condition_aliases;
            RAISE NOTICE 'Created backward-compat VIEW public.condition_aliases → public.line_condition_aliases';
        END IF;
    ELSE
        RAISE NOTICE 'VIEW public.condition_aliases already exists — skipping';
    END IF;
END $$;

-- Step 5: テーブルコメント更新
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_units') THEN
        COMMENT ON TABLE public.line_units IS 'LINE解析パイプライン用 単位マスタ（正式な販売単位は quantity_units を使用）';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_unit_aliases') THEN
        COMMENT ON TABLE public.line_unit_aliases IS 'LINE解析パイプライン用 単位エイリアス（正式な販売単位は quantity_units を使用）';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_conditions') THEN
        COMMENT ON TABLE public.line_conditions IS 'LINE解析パイプライン用 状態マスタ（正式な商品状態は condition_definitions を使用）';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_condition_aliases') THEN
        COMMENT ON TABLE public.line_condition_aliases IS 'LINE解析パイプライン用 状態エイリアス（正式な商品状態は condition_definitions を使用）';
    END IF;
END $$;
