-- Migration: Seed knowledge extraction vocab (block_delimiter / status_keyword)
-- 冪等: WHERE NOT EXISTS で既存レコードと衝突しない
-- 注: skip_condition の INSERT は PR #3823（2026-09-28 PO決定）で削除済み。詳細は本ファイル下部のコメント参照。

-- ブロック区切り記号（仕入元メッセージで商品ブロックの開始を示す記号）
INSERT INTO public.knowledge_rules (category, pattern_type, pattern, normalized_to, priority, language, is_active, description)
SELECT 'block_delimiter', 'exact', v.pattern, v.normalized_to, 100, 'ja', TRUE, v.description
FROM (VALUES
    ('■', 'product_block_start', 'ブロック区切り: 黒四角'),
    ('◆', 'product_block_start', 'ブロック区切り: 黒ひし形'),
    ('□', 'product_block_start', 'ブロック区切り: 白四角'),
    ('●', 'product_block_start', 'ブロック区切り: 黒丸'),
    ('⭐️', 'product_block_start', 'ブロック区切り: 星'),
    ('◎', 'product_block_start', 'ブロック区切り: 二重丸'),
    ('◉', 'product_block_start', 'ブロック区切り: 中黒丸'),
    ('▪️', 'product_block_start', 'ブロック区切り: 小黒四角'),
    ('⚫', 'product_block_start', 'ブロック区切り: 大黒丸'),
    ('🔥', 'product_block_start', 'ブロック区切り: 炎'),
    ('▫️', 'product_block_start', 'ブロック区切り: 小白四角'),
    ('▶', 'product_block_start', 'ブロック区切り: 右三角'),
    ('◼', 'product_block_start', 'ブロック区切り: 中黒四角'),
    ('『', 'product_block_start', 'ブロック区切り: 二重鉤括弧'),
    ('🔸', 'product_block_start', 'ブロック区切り: 小オレンジひし形'),
    ('・', 'product_block_start', 'ブロック区切り: 中点'),
    ('▢', 'product_block_start', 'ブロック区切り: 白四角(丸角)')
) AS v(pattern, normalized_to, description)
WHERE NOT EXISTS (
    SELECT 1 FROM public.knowledge_rules kr
    WHERE kr.category = 'block_delimiter' AND kr.pattern = v.pattern
);

-- スキップ条件（skip_condition）の INSERT は削除済み。
-- 理由: Gemini が抽出時点で完売・サーチ済み等を既に判断するため重複ルールとなり、
-- PO決定（2026-09-28 チャット）により skip_condition カテゴリ全体を廃止。
-- 削除は migrations/20260928_100000_delete_skip_condition_rules.sql（PR #3823）で実施。
-- この INSERT ブロックを残したままだと、run_all_migrations.sh の全件再実行のたびに
-- WHERE NOT EXISTS で再挿入 → 上記 delete migration が再度削除、を繰り返すため、
-- 再挿入源を止める目的でここを削除した（block_delimiter / status_keyword は変更なし）。

-- ステータス判定キーワード
INSERT INTO public.knowledge_rules (category, pattern_type, pattern, normalized_to, priority, language, is_active, description)
SELECT 'status_keyword', 'substring', v.pattern, v.normalized_to, 100, 'ja', TRUE, v.description
FROM (VALUES
    ('【予約商品】', 'Pre-order', 'ステータス: 予約商品'),
    ('【在庫商品】', 'In Stock', 'ステータス: 在庫商品'),
    ('予約', 'Pre-order', 'ステータス: 予約(短縮)'),
    ('在庫', 'In Stock', 'ステータス: 在庫(短縮)')
) AS v(pattern, normalized_to, description)
WHERE NOT EXISTS (
    SELECT 1 FROM public.knowledge_rules kr
    WHERE kr.category = 'status_keyword' AND kr.pattern = v.pattern
);
