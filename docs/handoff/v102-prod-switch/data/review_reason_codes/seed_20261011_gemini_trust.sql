-- 理由コード4つの追加（便G）。quantity_unresolved の追加（qu_*）の後にだけ実行する。1回だけのデータ変更（ADR-1007）。
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('price_source_mismatch', 'system', 'analysis'),
    ('quantity_source_mismatch', 'system', 'analysis'),
    ('value_out_of_range', 'system', 'analysis'),
    ('item_mapping_mismatch', 'system', 'analysis');
