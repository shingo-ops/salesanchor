-- 理由コード1つの追加（g28 便2）。gemini_gap_suspect の追加（gs_*）の後にだけ実行する。1回だけのデータ変更（ADR-1007）。
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('bulk_price_basis_unknown', 'system', 'analysis');
