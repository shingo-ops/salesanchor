-- 理由コード1つの追加（段2a）。unit_price_mismatch の追加（up_*）の後にだけ実行する。1回だけのデータ変更（ADR-1007）。
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('gemini_gap_suspect', 'system', 'extraction');
