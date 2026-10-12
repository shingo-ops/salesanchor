-- 理由コード1つの追加（便UP）。gemini_trust（gt_*）の追加の後にだけ実行する。1回だけのデータ変更（ADR-1007）。
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('unit_price_mismatch', 'system', 'analysis');
