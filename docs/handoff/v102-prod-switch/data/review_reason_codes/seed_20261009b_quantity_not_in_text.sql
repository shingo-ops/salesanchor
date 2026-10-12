-- quantity_not_in_text の追加（PR #4077）。初期29行（seed_20261009.sql）の後にだけ実行する。1回だけのデータ変更（ADR-1007）。
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('quantity_not_in_text', 'system', 'extraction');
