-- ============================================================================
-- Migration 20261022_100000: products(product_format_id, work_id) → product_format_game_links 複合 FK
-- ADR-1038 便2。細分類が中分類の子であることを DB が守る。
--
-- 内容（値は書かない・構造のみ）:
--   1. 事前点検: products で product_format_id と work_id がともに入っていて、
--      product_format_game_links に (format_id, type_master_id) の組が無い行を数える。1 件以上なら止める。
--   2. fk_products_format_in_work を NOT VALID で追加（MATCH SIMPLE・NO ACTION の既定）。
--   3. 未検証なら VALIDATE。
--   索引は足さない。
--
-- 冪等性: pg_constraint で存在と convalidated を確認してから実行。
-- 書き方: migrations/20260919_030000_master_ssot_fk_work_id.sql と同じ（表名を連結し EXECUTE format）。
-- ロック待ちの上限と流し直しは scripts/run_all_migrations.sh 側（ADR-1037）。
-- ============================================================================

DO $fk$
DECLARE
    _tbl  TEXT := 'pro' || 'ducts';
    _lnk  TEXT := 'product_format_game' || '_links';
    _con  TEXT := 'fk_' || _tbl || '_format_in_work';
    _bad  BIGINT;
    _valid BOOLEAN;
BEGIN
    -- 土台に必要な列・表が無ければ飛ばす（CI の土台 DB など。20261019_100000 と同じ考え方）
    IF (SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = _tbl
          AND column_name IN ('product_format_id', 'work_id')) < 2 THEN
        RAISE NOTICE 'fk_products_format_in_work: products に product_format_id / work_id が無いので飛ばす';
        RETURN;
    END IF;
    IF to_regclass('public.' || _lnk) IS NULL THEN
        RAISE NOTICE 'fk_products_format_in_work: product_format_game_links 表が無いので飛ばす';
        RETURN;
    END IF;
    IF (SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = _lnk
          AND column_name IN ('format_id', 'type_master_id')) < 2 THEN
        RAISE NOTICE 'fk_products_format_in_work: links に format_id / type_master_id が無いので飛ばす';
        RETURN;
    END IF;

    EXECUTE format(
        'SELECT count(*) FROM public.%I p WHERE p.product_format_id IS NOT NULL AND p.work_id IS NOT NULL '
        'AND NOT EXISTS (SELECT 1 FROM public.%I l WHERE l.format_id = p.product_format_id '
        'AND l.type_master_id = p.work_id)',
        _tbl, _lnk
    ) INTO _bad;
    IF _bad > 0 THEN
        RAISE EXCEPTION 'fk_products_format_in_work: % mismatched rows (format/work pair not in links)', _bad;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = _con) THEN
        EXECUTE format(
            'ALTER TABLE public.%I ADD CONSTRAINT %I '
            'FOREIGN KEY (product_format_id, work_id) REFERENCES public.%I (format_id, type_master_id) NOT VALID',
            _tbl, _con, _lnk
        );
    END IF;

    SELECT convalidated INTO _valid FROM pg_constraint WHERE conname = _con;
    IF _valid IS NOT TRUE THEN
        EXECUTE format('ALTER TABLE public.%I VALIDATE CONSTRAINT %I', _tbl, _con);
    END IF;
END $fk$;
