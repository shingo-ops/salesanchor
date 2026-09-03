-- PARITY-03 Phase 3 Stage 3: 修正履歴テーブル（tenant_004 専用・冪等）
--
-- 設計方針:
--   1修正 = 1行（field_name 単位で append-only）。GAS は上書き方式だが踏襲しない。
--   system_value: Gemini 抽出値（修正時点）、human_value: 人間の修正値
--   extraction_item_id / source_message_id は FK 制約なし（参照先が別スキーマのため）

CREATE TABLE IF NOT EXISTS tenant_004.item_corrections (
    id                 BIGSERIAL    PRIMARY KEY,
    extraction_item_id UUID         NOT NULL,
    source_message_id  UUID         NOT NULL,
    field_name         TEXT         NOT NULL,
    system_value       TEXT         NOT NULL DEFAULT '',
    human_value        TEXT         NOT NULL,
    corrected_by       TEXT         NOT NULL,
    corrected_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_item_corrections_extraction_item_id
    ON tenant_004.item_corrections (extraction_item_id);

CREATE INDEX IF NOT EXISTS idx_item_corrections_corrected_at
    ON tenant_004.item_corrections (corrected_at DESC);
