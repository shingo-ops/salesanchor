-- MIG PARITY-02 A-2: tcg_unit_evidence_rules (tenant_004)
-- 単位証拠ルールマスタ 4件を新規テーブルへ投入
-- 移植元: MasterRegistry.gs:247-265 (systemResolverV2EnsureMasterRows_ 定義値)
-- 冪等: CREATE IF NOT EXISTS + INSERT ON CONFLICT DO NOTHING

DO $body$
DECLARE
    _schema TEXT    := 'tenant_004';
    _count  INTEGER;
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

    -- -------------------------------------------------------------------------
    -- 4件 seed（GAS: MasterRegistry.gs:251-265 の確定値）
    -- structure_pattern は JavaScript string escape を展開した実値を格納
    -- ON CONFLICT DO NOTHING で冪等
    -- -------------------------------------------------------------------------

    -- UER_E2_PRICE_X_QTY_UNIT: Enabled=false（審査前ルール）
    EXECUTE format($q$
        INSERT INTO %I.tcg_unit_evidence_rules
            (id, evidence_type, priority, enabled,
             requires_unique_pid, requires_unique_unit_candidate,
             exclude_product_matched_terms, structure_pattern, note)
        VALUES (
            'UER_E2_PRICE_X_QTY_UNIT',
            'E2_PRICE_X_QTY_UNIT',
            1,
            FALSE,
            FALSE,
            TRUE,
            FALSE,
            $p$(?:[@＠¥￥]\s*)?\d[\d,]*(?:\s*(?:円|¥|￥))?\s*(?:×|x|X)\s*\d[\d,]*\s*{{UNIT}}$p$,
            $n$価格→乗算→数量+Unitのみ。Unit語・乗算記号・構造patternは各Masterを正本とする。$n$
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- UER_E2_AT_PRICE_X_QTY_UNIT: Enabled=true（@付き価格パターン）
    EXECUTE format($q$
        INSERT INTO %I.tcg_unit_evidence_rules
            (id, evidence_type, priority, enabled,
             requires_unique_pid, requires_unique_unit_candidate,
             exclude_product_matched_terms, structure_pattern, note)
        VALUES (
            'UER_E2_AT_PRICE_X_QTY_UNIT',
            'AT_PRICE_X_QTY_UNIT',
            1,
            TRUE,
            TRUE,
            FALSE,
            TRUE,
            $p$[@＠]\s*\d[\d,]*(?:\s*(?:円|¥|￥))?\s*(?:×|x|X)\s*\d[\d,]*\s*{{UNIT}}$p$,
            $n$監査済み: @付き価格→乗算→数量+Unit。$n$
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- UER_E2_CURRENCY_PRICE_X_QTY_UNIT: Enabled=true（通貨表記パターン）
    EXECUTE format($q$
        INSERT INTO %I.tcg_unit_evidence_rules
            (id, evidence_type, priority, enabled,
             requires_unique_pid, requires_unique_unit_candidate,
             exclude_product_matched_terms, structure_pattern, note)
        VALUES (
            'UER_E2_CURRENCY_PRICE_X_QTY_UNIT',
            'CURRENCY_PRICE_X_QTY_UNIT',
            2,
            TRUE,
            TRUE,
            FALSE,
            TRUE,
            $p$\d[\d,]*\s*(?:円|¥|￥)\s*(?:×|x|X)\s*\d[\d,]*\s*{{UNIT}}$p$,
            $n$監査済み: 通貨表記付き価格→乗算→数量+Unit。$n$
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- UER_E3: Enabled=true（商品照合残余ルール）
    EXECUTE format($q$
        INSERT INTO %I.tcg_unit_evidence_rules
            (id, evidence_type, priority, enabled,
             requires_unique_pid, requires_unique_unit_candidate,
             exclude_product_matched_terms, structure_pattern, note)
        VALUES (
            'UER_E3',
            'E3_PRODUCT_RESIDUAL',
            3,
            TRUE,
            TRUE,
            TRUE,
            TRUE,
            '',
            $n$PID一意・商品照合残余のみ。Unit語は単位マスタを正本とする。$n$
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- -------------------------------------------------------------------------
    -- 件数確認（このmigrationが挿入した4件を確認）
    -- id = ANY($1) で担当IDを明示することで、後から追加された行に影響されない
    -- -------------------------------------------------------------------------
    EXECUTE format(
        'SELECT count(*) FROM %I.tcg_unit_evidence_rules WHERE id = ANY($1)',
        _schema
    ) INTO _count USING ARRAY[
        'UER_E2_PRICE_X_QTY_UNIT',
        'UER_E2_AT_PRICE_X_QTY_UNIT',
        'UER_E2_CURRENCY_PRICE_X_QTY_UNIT',
        'UER_E3'
    ];
    IF _count != 4 THEN
        RAISE EXCEPTION 'tcg_unit_evidence_rules: 期待4件、実際%件', _count;
    END IF;

    RAISE NOTICE 'tcg_unit_evidence_rules: 4 件確認 OK (UER_E2_*, UER_E3)';
END $body$;
