-- ============================================================================
-- Migration 20260925_120000: 商品除外キーワード追加（ADR-158 精度改善）
--
-- 目的:
--   GEMINI バイパス修正（ADR-158）で exclude_keywords チェックが有効になったため、
--   88件の誤解決を防ぐ除外キーワードを public.product_exclude_keywords に追加する。
--
-- 対象:
--   - ONE PIECE BOX 商品（24件）: パラレル/SEC/SAR/SR/PSA/プロモ/一番くじ 等
--   - ポケモン BOX 商品（箱系カテゴリ全体）: SAR/SR/AR/PSA/パラレル/マスターボールミラー
--   - 個別商品除外（PM0184, PM0196, PM0225, PM0177, PM0209, PM0203, PM0200）
--   - 検索キーワード修正（PM0264 誤キーワード削除・PM0181 補完）
--
-- NEUTRALIZED (ADR-155, 2026-09-18):
-- 商品マスタデータはアプリ画面/CSVで管理する。migrationは構造変更のみ。
-- 以下の SQL は PO が直接 DB で実行するか、アプリ管理画面から登録すること。
-- 元コメントに意図した SQL を残してある。
--
-- 承認待ち: PR #xxxx (ADR-158)
-- ============================================================================

DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: exclude keyword inserts removed — manage via app/CSV. See comment block in this file for intended SQL.'; END $$;

/*
==============================================================================
  以下は実行 SQL（ADR-155 により migration では禁止。PO が直接実行すること）
  実行先: 本番 DB（public スキーマ）
  冪等: WHERE NOT EXISTS ガード付き
  注意: position 列は NOT NULL のため、既存最大値+1 を使う計算式を含む
==============================================================================

-- ============================================================
-- [1] ONE PIECE BOX 商品（24件）への除外キーワード追加
-- パラレル/SEC/SAR/SR/PSA等 を除外して単品カードの誤解決を防ぐ
-- ============================================================
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT
    p.id,
    kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES
    ('パラレル'),
    ('SEC'),
    ('リーダーパラレル'),
    ('コミパラ'),
    ('コミックパラレル'),
    ('PSA'),
    ('PSA10'),
    ('PSA9'),
    ('SAR'),
    ('SR'),
    ('プロモ'),
    ('一番くじ')
) AS kw(keyword)
WHERE p.product_code IN (
    'PM0082','PM0085','PM0094','PM0103','PM0118','PM0123','PM0127','PM0134',
    'PM0137','PM0141','PM0143','PM0153','PM0157','PM0160','PM0172','PM0180',
    'PM0181','PM0193','PM0196','PM0206','PM0207','PM0222','PM0227','PM0266'
)
AND NOT EXISTS (
    SELECT 1 FROM public.product_exclude_keywords ex
    WHERE ex.product_id = p.id AND ex.keyword = kw.keyword
);

-- ============================================================
-- [2] ポケモン BOX 商品（箱系カテゴリ全体）への除外キーワード追加
-- ============================================================
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT
    p.id,
    kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES
    ('SAR'),
    ('SR'),
    ('AR'),
    ('PSA'),
    ('PSA10'),
    ('PSA9'),
    ('パラレル'),
    ('マスターボールミラー')
) AS kw(keyword)
WHERE p.category = '箱系'
AND p.work_id = (SELECT id FROM public.works WHERE code = 'IP001' LIMIT 1)
AND NOT EXISTS (
    SELECT 1 FROM public.product_exclude_keywords ex
    WHERE ex.product_id = p.id AND ex.keyword = kw.keyword
);

-- ============================================================
-- [3] 個別商品除外キーワード
-- ============================================================

-- PM0184 メガゲンガーex: スペシャルデッキセットとの誤解決を防ぐ
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT p.id, kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES ('スペシャルデッキセット')) AS kw(keyword)
WHERE p.product_code = 'PM0184'
AND NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = p.id AND keyword = kw.keyword);

-- PM0196 蒼海の七傑 (OP-14): OP-13 表記との混同を防ぐ
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT p.id, kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES ('OP-13'), ('OP13'), ('受け継がれる意志')) AS kw(keyword)
WHERE p.product_code = 'PM0196'
AND NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = p.id AND keyword = kw.keyword);

-- PM0225 UA NIKKE: ヴァイスシュヴァルツとの混同を防ぐ
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT p.id, kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES ('ヴァイスシュヴァルツ'), ('ヴァイス'), ('WS')) AS kw(keyword)
WHERE p.product_code = 'PM0225'
AND NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = p.id AND keyword = kw.keyword);

-- PM0177 メガブレイブPC: メガシンフォニアとの混同を防ぐ
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT p.id, kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES ('メガシンフォニア'), ('シンフォニア')) AS kw(keyword)
WHERE p.product_code = 'PM0177'
AND NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = p.id AND keyword = kw.keyword);

-- PM0209 ニンジャスピナー: 個別/@表記の誤解決を防ぐ
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT p.id, kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES ('個別'), ('@')) AS kw(keyword)
WHERE p.product_code = 'PM0209'
AND NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = p.id AND keyword = kw.keyword);

-- PM0203 メガエルレイドex: パルワールド/Masters League との混同を防ぐ
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT p.id, kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES ('パルワールド'), ('Masters League'), ('MA')) AS kw(keyword)
WHERE p.product_code = 'PM0203'
AND NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = p.id AND keyword = kw.keyword);

-- PM0200 バトルコレクション: コロチャオとの混同を防ぐ
INSERT INTO public.product_exclude_keywords (product_id, keyword, position, updated_at)
SELECT p.id, kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_exclude_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES ('コロチャオ')) AS kw(keyword)
WHERE p.product_code = 'PM0200'
AND NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = p.id AND keyword = kw.keyword);

-- ============================================================
-- [4] 検索キーワード修正
-- ============================================================

-- PM0264 30th CELEBRATION FUTURISTIC BOX: 誤キーワード削除
DELETE FROM public.product_search_keywords
WHERE product_id = (SELECT id FROM public.products WHERE product_code = 'PM0264')
AND keyword = '30th CELEBRATION FUTURISTIC';

-- PM0181 受け継がれる意志 OP-13: 検索キーワード補完
INSERT INTO public.product_search_keywords (product_id, keyword, position, updated_at)
SELECT p.id, kw.keyword,
    COALESCE((SELECT MAX(position) FROM public.product_search_keywords WHERE product_id = p.id), 0) + ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY kw.keyword),
    now()
FROM public.products p
CROSS JOIN (VALUES ('受け継がれる意志'), ('受け継がれる意志 OP-13')) AS kw(keyword)
WHERE p.product_code = 'PM0181'
AND NOT EXISTS (SELECT 1 FROM public.product_search_keywords WHERE product_id = p.id AND keyword = kw.keyword);

==============================================================================
*/
