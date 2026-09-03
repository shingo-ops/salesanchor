-- DIST-01 C: tcg_distribution_settings テーブル作成 + 初期値（tenant_004 専用・冪等）
--
-- 配信全体設定。FLAG_SINGLE の配信可否などをコード変更なしに切り替えるためのテーブル。
-- 精度ゲート閾値（確定）: 直近50件以上・修正率5%以下・3週連続・PO承認。

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_210000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.tcg_distribution_settings (
            key        TEXT         PRIMARY KEY,
            value      TEXT         NOT NULL,
            note       TEXT,
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    -- 初期値: ON CONFLICT DO NOTHING（再実行しても上書きしない）
    EXECUTE format($sql$
        INSERT INTO %I.tcg_distribution_settings (key, value, note) VALUES
          ('include_flag_single',
           'false',
           'FLAG_SINGLE 精度ゲート通過後に PO 承認で true へ変更。コード変更不要。'),
          ('flag_gate_min_samples',
           '50',
           '精度ゲート: 最低サンプル数（直近30日間のFLAG_SINGLE行数）'),
          ('flag_gate_max_correction_rate_pct',
           '5',
           '精度ゲート: 修正率上限（%%）。item_corrections との JOIN で算出'),
          ('flag_gate_consecutive_weeks',
           '3',
           '精度ゲート: 連続達成週数。3週連続で閾値以内 → PO 承認で切り替え')
        ON CONFLICT (key) DO NOTHING
    $sql$, _schema);

    RAISE NOTICE 'migration 20260903_210000: tcg_distribution_settings created (or already existed)';
END
$body$;
