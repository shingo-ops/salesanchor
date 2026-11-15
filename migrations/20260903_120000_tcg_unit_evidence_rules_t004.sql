-- MIG PARITY-02 A-2: tcg_unit_evidence_rules (tenant_004)
-- 単位証拠ルールマスタ 4件を新規テーブルへ投入
-- 移植元: MasterRegistry.gs:247-265 (systemResolverV2EnsureMasterRows_ 定義値)
-- 冪等: CREATE IF NOT EXISTS + INSERT ON CONFLICT DO NOTHING

DO $body$
DECLARE
    _schema TEXT    := 'tenant_004';
BEGIN
    -- -------------------------------------------------------------------------
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    -- -------------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_120000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- -------------------------------------------------------------------------
    -- テーブル作成（additive-only / IF NOT EXISTS）
    -- -------------------------------------------------------------------------
    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.tcg_unit_evidence_rules (
            id                              TEXT        PRIMARY KEY,
            evidence_type                   TEXT        NOT NULL,
            priority                        INTEGER     NOT NULL,
            enabled                         BOOLEAN     NOT NULL DEFAULT TRUE,
            requires_unique_pid             BOOLEAN     NOT NULL DEFAULT FALSE,
            requires_unique_unit_candidate  BOOLEAN     NOT NULL DEFAULT FALSE,
            exclude_product_matched_terms   BOOLEAN     NOT NULL DEFAULT FALSE,
            structure_pattern               TEXT        NOT NULL DEFAULT '',
            note                            TEXT        NOT NULL DEFAULT '',
            created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    -- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): 4件の seed（INSERT … ON CONFLICT DO NOTHING 4つ）と、4件でなければ止める件数の確かめを外した。
    -- 毎回の本番反映で、消した行が戻り、行を足すと反映が止まっていた。表を作る文は残す。
    -- 件数の確かめも外すのは、値の文だけ外すと表が空の環境で 0件になり反映が止まるため（p11-classification.md §3）。
    -- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #17
    -- 元の内容は git history で参照可能。
    RAISE NOTICE 'ADR-1007 neutralized: tcg_unit_evidence_rules seed and count check removed (20260903_120000)';
END $body$;
