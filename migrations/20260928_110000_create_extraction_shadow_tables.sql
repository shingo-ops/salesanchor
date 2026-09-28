-- Migration: 試運転用の表（extraction_shadow_runs / extraction_shadow_results）と
--            仕入元の発送日の書き方欄（suppliers.extraction_ship_format）を追加する
-- 根拠: docs/handoff/gemini-extract-role-split/design.md 追補（PR-B1、2026-09-28、Architect APPROVE）
-- 既存の analysis_results・配信クエリには一切触れない（追加のみ）。
-- 冪等: CREATE TABLE / ADD COLUMN / INSERT はすべて IF NOT EXISTS・ON CONFLICT DO NOTHING。

-- 1. 発送日の書き方（仕入元ごと）。既存の extraction_* 列と同じ作法（TEXT, ADD COLUMN IF NOT EXISTS）。
--    参考: migrations/20260924_010000_add_supplier_extraction_rules.sql:2-7
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_ship_format TEXT;

-- 2. extraction_shadow_runs: Gemini（v7）の呼び出し1回につき1行。A/B試運転専用。
--    id の既定値は既存 migration の uuid 作法に合わせる（参考: migrations/20260921_110000_pipeline_tables_public.sql:11,20,38,80）。
--    トークン・費用の列は migrations/20260927_130000_add_extraction_token_cost_columns.sql と同名・同型にする。
CREATE TABLE IF NOT EXISTS public.extraction_shadow_runs (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_job_id   UUID        NOT NULL REFERENCES public.extraction_jobs(id) ON DELETE CASCADE,
    prompt_key          TEXT        NOT NULL,
    prompt_config_version INTEGER,
    engine_version      TEXT        NOT NULL,
    requested_model     TEXT        NOT NULL,
    input_bytes         BIGINT,
    response_text       TEXT,
    input_tokens        INTEGER,
    output_tokens       INTEGER,
    cost_usd            NUMERIC(10,6),
    status              TEXT        NOT NULL,
    error_code          TEXT,
    error_detail        TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ,
    CONSTRAINT extraction_shadow_runs_status_check
        CHECK (status IN ('completed', 'failed')),
    CONSTRAINT uq_extraction_shadow_runs_job_engine
        UNIQUE (extraction_job_id, engine_version)
);

-- 3. extraction_shadow_results: ブロック1つにつき1行。
CREATE TABLE IF NOT EXISTS public.extraction_shadow_results (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              UUID        NOT NULL REFERENCES public.extraction_shadow_runs(id) ON DELETE CASCADE,
    block_index         INTEGER     NOT NULL,
    line_start          INTEGER,
    line_end            INTEGER,
    heading_line_start  INTEGER,
    heading_line_end    INTEGER,
    raw_product_name    TEXT,
    raw_price           TEXT,
    raw_unit            TEXT,
    raw_quantity        TEXT,
    raw_state           TEXT,
    raw_ship            TEXT,
    raw_multi           TEXT,
    product_id          INTEGER     REFERENCES public.products(id),
    work_id             INTEGER,
    condition_id        INTEGER,
    quantity_normalized NUMERIC(14,2),
    price_normalized    NUMERIC(14,2),
    ship_offer_type     TEXT,
    ship_timing         TEXT,
    note_ja             TEXT,
    status              VARCHAR(50),
    exclusion           TEXT,
    match_status        TEXT        NOT NULL,
    needs_review        BOOLEAN     NOT NULL,
    review_items        JSONB       NOT NULL DEFAULT '[]',
    evidence            JSONB       NOT NULL DEFAULT '{}',
    verify_failures     JSONB       NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT extraction_shadow_results_match_status_check
        CHECK (match_status IN ('matched', 'ambiguous', 'unmatched')),
    CONSTRAINT uq_extraction_shadow_results_run_block
        UNIQUE (run_id, block_index)
);
CREATE INDEX IF NOT EXISTS ix_extraction_shadow_results_needs_review
    ON public.extraction_shadow_results (needs_review, created_at);
CREATE INDEX IF NOT EXISTS ix_extraction_shadow_results_run_id
    ON public.extraction_shadow_results (run_id);

-- 4. v7 の指示文（raw_copy_extraction）の初期値。SSOT は DB。
--    列名・必須列は migrations/20260926_080000_create_extraction_prompt_config.sql を参照して合わせた。
--    ON CONFLICT (prompt_key) DO NOTHING により、管理画面で編集済みの行は上書きしない。
INSERT INTO public.extraction_prompt_config (prompt_key, prompt_text, is_active)
VALUES (
    'raw_copy_extraction',
    $PROMPT$あなたは書き写し担当です。判断・推測・補完・言い換え・翻訳はしません。
入力は LINE の投稿本文で、各行の先頭に行番号（例 L0001）が付いています。
商品のまとまり（ブロック）ごとに1行ずつ、次の9列を「｜」で区切って出力してください。1行目は次のヘッダーをそのまま出力します。
RAW_PRODUCT_NAME｜RAW_PRICE｜RAW_UNIT｜RAW_QUANTITY｜RAW_STATE｜RAW_SHIP｜RAW_MULTI｜RAW_SOURCE_LINE_SPAN｜RAW_HEADING_LINE_SPAN
- 値は原文の文字をそのまま書き写す。
- 原文に書かれていない値は none と書く。空欄にしない（特に RAW_STATE と RAW_SHIP）。
- 1つのブロックに同じ種類の値が2つ以上あるときは、すべてを「／」でつないで書き、RAW_MULTI にその列名を書く（複数あれば「／」でつなぐ）。なければ none。
- RAW_SOURCE_LINE_SPAN はブロックの行範囲（例 L0003-L0005）。RAW_HEADING_LINE_SPAN はそのブロックに掛かる見出し行の範囲。なければ none。
- 作品・商品・状態・在庫・完売などの判定はしない。書かれている文字を書き写すだけ。
- 後に続く「仕入元の書き方」は、この仕入元がどこに何を書くかの説明です。書き写す場所を見つける参考にだけ使ってください。$PROMPT$,
    TRUE
)
ON CONFLICT (prompt_key) DO NOTHING;
