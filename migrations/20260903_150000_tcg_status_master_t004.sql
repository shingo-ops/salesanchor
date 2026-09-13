-- MIG PARITY-02 A-4: tcg_status_master (tenant_004)
-- ステータスマスタ 9件を新規テーブルへ投入
-- 移植元: GAS スプレッドシート「ステータスマスタ」タブ（全9行）
--         spreadsheetId: 1or39_glwYtF9OfOxXizN8ZjcUKL0hNIeW3qP3nCx3AI
-- 冪等: CREATE IF NOT EXISTS + INSERT ON CONFLICT DO NOTHING

DO $body$
DECLARE
    _schema TEXT    := 'tenant_004';
    _count  INTEGER;
BEGIN
    -- -------------------------------------------------------------------------
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    -- -------------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_150000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- -------------------------------------------------------------------------
    -- テーブル作成（additive-only / IF NOT EXISTS）
    -- -------------------------------------------------------------------------
    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.tcg_status_master (
            status_id       TEXT        PRIMARY KEY,
            canonical       TEXT        NOT NULL,
            search_pattern  TEXT        NOT NULL DEFAULT '',
            exclude_pattern TEXT        NOT NULL DEFAULT '',
            priority        INTEGER     NOT NULL,
            enabled         BOOLEAN     NOT NULL DEFAULT TRUE,
            note            TEXT        NOT NULL DEFAULT '',
            match_type      TEXT        NOT NULL,
            effect          TEXT        NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    -- -------------------------------------------------------------------------
    -- 9件 seed（スプレッドシート「ステータスマスタ」タブ確定値）
    -- search_pattern は正規表現または検索リテラル文字列
    -- ON CONFLICT DO NOTHING で冪等
    -- -------------------------------------------------------------------------

    -- ST0001: Pre-order / 発売日付パターン (M/D発)
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0001', 'Pre-order', '\(\d{1,2}\/\d{1,2}発\)', '', 10, TRUE, '', 'REGEX', 'OUTPUT'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- ST0002: Pre-order / 発売日付パターン (M/D発送)
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0002', 'Pre-order', '\d{1,2}\/\d{1,2}.{0,8}発送', '', 20, TRUE, '', 'REGEX', 'OUTPUT'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- ST0003: Pre-order / 発売日付パターン (N日BOX/発送/入荷)
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0003', 'Pre-order', '(?:^|[^0-9\/])(\d{1,2}日)(?=BOX|発送|入荷|$)', '', 30, TRUE, '', 'REGEX', 'OUTPUT'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- ST0004: In Stock / デフォルト（他パターン非該当時）
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0004', 'In Stock', '', '', 999, TRUE, '', 'DEFAULT', 'OUTPUT'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- ST0010: Sold out / soldout（英語リテラル）
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0010', 'Sold out', 'soldout', '', 10, TRUE, '', 'LITERAL', 'EXCLUDE'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- ST0011: Sold out / 在庫なし
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0011', 'Sold out', '在庫なし', '', 20, TRUE, '', 'LITERAL', 'EXCLUDE'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- ST0012: Sold out / 売り切れ
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0012', 'Sold out', '売り切れ', '', 30, TRUE, '', 'LITERAL', 'EXCLUDE'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- ST0013: Sold out / 完売
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0013', 'Sold out', '完売', '', 40, TRUE, '', 'LITERAL', 'EXCLUDE'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- ST0014: Sold out / 欠品
    EXECUTE format($q$
        INSERT INTO %I.tcg_status_master
            (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect)
        VALUES (
            'ST0014', 'Sold out', '欠品', '', 50, TRUE, '', 'LITERAL', 'EXCLUDE'
        )
        ON CONFLICT (status_id) DO NOTHING
    $q$, _schema);

    -- -------------------------------------------------------------------------
    -- COUNT 検証（9件でなければ RAISE EXCEPTION）
    -- -------------------------------------------------------------------------
    EXECUTE format(
        'SELECT count(*) FROM %I.tcg_status_master WHERE status_id LIKE $1',
        _schema
    ) INTO _count USING 'ST%';

    IF _count <> 9 THEN
        RAISE EXCEPTION 'migration 20260903_150000: tcg_status_master count mismatch (expected 9, got %)', _count;
    END IF;

    RAISE NOTICE 'migration 20260903_150000: tcg_status_master: 9 rows OK';
END $body$;
