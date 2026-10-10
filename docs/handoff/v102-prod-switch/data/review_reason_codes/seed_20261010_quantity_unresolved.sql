-- quantity_unresolved の追加（便PQ）。qty_*（quantity_not_in_text）の後にだけ実行する。1回だけのデータ変更（ADR-1007）。
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('quantity_unresolved', 'system', 'analysis');
