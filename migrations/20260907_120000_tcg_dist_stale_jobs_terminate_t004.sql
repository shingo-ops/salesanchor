-- MIG DIST-STALE-A: 滞留 extraction_jobs 12件を終端化 (tenant_004)
-- 目的: 安全装置 #8b が3日前の滞留ジョブで配信を恒久的に止める状態を解消する
-- 設計: docs/handoff/tcg-product-master-growth/design.md
-- 対象ADR: ADR-154
-- 冪等: 再実行時は既に error のため WHERE の status 条件に合致せず、更新は起きない
-- 件数確認は本ファイルが対象とする12件の範囲のみを数える（テーブル全体は数えない）

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
    _ids    UUID[] := ARRAY[
        'eb4d23a8-06a6-4bdf-b0c3-d12273a156a7',
        '3a6c52f8-d60d-47ad-ae25-6b3ff24e54b3',
        'c6e0ffe7-ece3-4ef0-8e2e-ac4e2d597c9b',
        '2f65c8a2-4c5b-4232-b22e-30433a658d1e',
        '4e2002bd-3018-46ab-bf55-2b2ecc4953dd',
        'c86876dd-10c7-4b0e-bddb-927c561d7c6d',
        '8dbcd939-d355-4073-8d40-bd93902d478b',
        'c1518343-a7eb-4429-86a5-8a7d9b710230',
        'cbe093ef-a78d-4c7c-b538-09ea21a272d8',
        '81a3f452-9c07-4208-90a9-6b7d49691896',
        '802211ed-3789-4c39-8137-bd0a23100dd0',
        '0713391d-d0d6-4163-b726-61741b3b1a51'
    ]::UUID[];
    _count INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE 'migration DIST-STALE-A: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format($q$
        UPDATE %I.extraction_jobs
        SET status = 'error',
            error_message = 'DIST-STALE-A: 滞留ジョブを終端化 (2026-09-07)'
        WHERE id = ANY($1)
          AND status = ANY(ARRAY['pending','running','extracted'])
    $q$, _schema) USING _ids;

    EXECUTE format(
        'SELECT count(*) FROM %I.extraction_jobs WHERE id = ANY($1) AND status = ''error''',
        _schema
    ) INTO _count USING _ids;

    IF _count != 12 THEN
        RAISE EXCEPTION 'DIST-STALE-A: 期待12件、実際%件', _count;
    END IF;

    RAISE NOTICE 'DIST-STALE-A: % 件終端化 OK', _count;
END $body$;
