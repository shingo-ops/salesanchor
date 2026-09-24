-- Migration: Seed knowledge extraction vocab (block_delimiter / skip_condition / status_keyword)
-- 冪等: WHERE NOT EXISTS で既存レコードと衝突しない

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

-- スキップ条件（このキーワードを含むブロックは抽出対象外）
INSERT INTO public.knowledge_rules (category, pattern_type, pattern, normalized_to, priority, language, is_active, description)
SELECT 'skip_condition', v.pattern_type, v.pattern, 'skip', 100, 'ja', TRUE, v.description
FROM (VALUES
    ('exact', '[サーチ済み]', '出力抑止: サーチ痕あり'),
    ('exact', '[サーチ済]', '出力抑止: サーチ痕あり(短縮)'),
    ('substring', 'サーチ済', '出力抑止: サーチ済(部分一致)'),
    ('substring', '完売しました', '出力抑止: 完売'),
    ('substring', '売り切れ', '出力抑止: 売り切れ'),
    ('substring', '売切', '出力抑止: 売切(短縮)'),
    ('exact', '〆', '出力抑止: 締め切り'),
    ('substring', 'ペリ無', '出力抑止: ペリ無(付属品なし)'),
    ('substring', 'ペリ無し', '出力抑止: ペリ無し'),
    ('substring', 'セット', '出力抑止: セット商品'),
    ('substring', 'バラパック', '出力抑止: バラパック'),
    ('substring', '適格請求事業者', '出力抑止: 事業者情報'),
    ('substring', '発送元', '出力抑止: 発送元情報')
) AS v(pattern_type, pattern, description)
WHERE NOT EXISTS (
    SELECT 1 FROM public.knowledge_rules kr
    WHERE kr.category = 'skip_condition' AND kr.pattern = v.pattern
);

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
