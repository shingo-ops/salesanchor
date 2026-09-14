-- ============================================================================
-- Migration 20260914_080000: tenant_004 略語キーワード追加（検索語・除外語）
--
-- 目的:
--   TCG解析エンジンが読む tenant_004.product_search_keywords /
--   product_exclude_keywords に略語キーワードを追加する。
--
-- 根拠:
--   PR #3495 の背景調査により、解析エンジンは public.products.search_keywords
--   ではなく tenant_004 スキーマのテーブルを参照することが確認された。
--   略語（「頂上」「決戦」等）がないとメッセージ内の短縮表記にマッチしない。
--
-- 対象テーブル:
--   tenant_004.product_search_keywords  — 検索語（網）
--   tenant_004.product_exclude_keywords — 除外語（壁）
--
-- UNIQUE制約: (product_id, keyword) → ON CONFLICT DO NOTHING で冪等
-- position: 既存最大値が 13〜14 程度のため、20 から開始（衝突なし）
--
-- 承認: PR #3495
-- ============================================================================

DO $mig$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- 前提テーブルが存在しない場合はスキップ（CI 空DB テスト対応）
    IF to_regclass(_schema || '.tcg_products') IS NULL
       OR to_regclass(_schema || '.product_search_keywords') IS NULL
       OR to_regclass(_schema || '.product_exclude_keywords') IS NULL THEN
        RAISE NOTICE '20260914_080000: 前提テーブルが無いためスキップしました（schema=%）', _schema;
        RETURN;
    END IF;

    -- =========================================================================
    -- 1) 検索語（網）の追加 — ONE PIECE
    -- =========================================================================

    -- PM0085: 頂上決戦 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('頂上', 20),
        ('決戦', 21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0085'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0094: 強大な敵 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('強大', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0094'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0103: 謀略の王国 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('謀略', 20),
        ('王国', 21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0103'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0118: 新時代の主役 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('新時代', 20),
        ('主役',   21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0118'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0127: 双璧の覇者 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('双璧', 20),
        ('覇者', 21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0127'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0134: 500年後の未来 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('500年', 20),
        ('未来',  21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0134'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0143: 二つの伝説 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('伝説', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0143'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0141: 新たなる皇帝 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('皇帝', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0141'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0157: 神速の拳 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('神速', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0157'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0160: 王族の血統 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('王族', 20),
        ('血統', 21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0160'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0180: 師弟の絆 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('師弟', 20),
        ('絆',   21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0180'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0181: 受け継がれる意志 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('意志',  20),
        ('受け継', 21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0181'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0196: 蒼海の七傑 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('蒼海', 20),
        ('七傑', 21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0196'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0222: 決戦の刻 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('決戦', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0222'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- =========================================================================
    -- 2) 検索語（網）の追加 — Dragon Ball
    -- =========================================================================

    -- PM0124 (FB01): 覚醒の鼓動 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('覚醒', 20),
        ('鼓動', 21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0124'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0130 (FB02): 烈火の闘気 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('烈火', 20),
        ('闘気', 21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0130'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0138 (FB03): 怒りの咆哮 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('咆哮', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0138'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0154 (FB05): 未知なる冒険 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('冒険', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0154'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0164 (FB06): 迫り来る脅威 — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('脅威', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0164'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0187 (FB07): 神龍への願い — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('神龍', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0187'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0226 (FB09): DUAL EVOLUTION — 略語追加
    INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('DUAL EVOLUTION', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0226'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- =========================================================================
    -- 3) 除外語（壁）の追加 — ONE PIECE
    -- =========================================================================

    -- PM0085 (頂上決戦): 「決戦の刻」(OP-16) との誤マッチ防止
    INSERT INTO tenant_004.product_exclude_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('決戦の刻', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0085'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0222 (決戦の刻): 「頂上決戦」(OP-02) との誤マッチ防止
    INSERT INTO tenant_004.product_exclude_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('頂上決戦', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0222'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- PM0180 (師弟の絆): 「3兄弟の絆」(ST-13) との誤マッチ防止
    INSERT INTO tenant_004.product_exclude_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('3兄弟の絆', 20),
        ('兄弟',     21)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0180'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    -- =========================================================================
    -- 4) 除外語（壁）の追加 — Pokemon
    -- =========================================================================

    -- PM0059 (双璧のファイター): ONE PIECE OP-06「双璧の覇者」との誤マッチ防止
    INSERT INTO tenant_004.product_exclude_keywords (product_id, keyword, position)
    SELECT p.id, v.keyword, v.position
    FROM tenant_004.tcg_products p
    CROSS JOIN (VALUES
        ('双璧の覇者', 20)
    ) AS v(keyword, position)
    WHERE p.code = 'PM0059'
    ON CONFLICT (product_id, keyword) DO NOTHING;

    RAISE NOTICE '20260914_080000: 完了 — tenant_004 略語キーワード追加';
END
$mig$;
