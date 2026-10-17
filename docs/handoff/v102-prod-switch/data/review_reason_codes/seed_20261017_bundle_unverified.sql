-- 理由コード1つの追加（ADR-1027 まとめ売り）。bulk_price_basis_unknown の追加（seed_20261016）の後にだけ実行する。1回だけのデータ変更（ADR-1007）。
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('bundle_unverified', 'system', 'analysis');
