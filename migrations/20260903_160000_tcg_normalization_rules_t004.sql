-- MIG PARITY-02 A-1: tcg_normalization_rules (tenant_004)
-- 正規化ルール 135件を新規テーブルへ投入
-- 移植元: GAS スプレッドシート「正規化ルール」タブ（全135行）
--         spreadsheetId: 1or39_glwYtF9OfOxXizN8ZjcUKL0hNIeW3qP3nCx3AI
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
        RAISE NOTICE 'migration 20260903_160000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- -------------------------------------------------------------------------
    -- テーブル作成（additive-only / IF NOT EXISTS）
    -- -------------------------------------------------------------------------
    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.tcg_normalization_rules (
            normalization_rule_id  TEXT        PRIMARY KEY,
            field                  TEXT        NOT NULL,
            rule_type              TEXT        NOT NULL,
            from_val               TEXT        NOT NULL DEFAULT '',
            to_val                 TEXT        NOT NULL DEFAULT '',
            enabled                BOOLEAN     NOT NULL DEFAULT TRUE,
            priority               INTEGER     NOT NULL,
            note                   TEXT        NOT NULL DEFAULT '',
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    -- -------------------------------------------------------------------------
    -- 135件 seed（スプレッドシート「正規化ルール」タブ確定値）
    -- from_val / to_val はシート原文をそのまま投入（正規表現・リテラル・Unicode含む）
    -- ON CONFLICT DO NOTHING で冪等
    -- -------------------------------------------------------------------------

    EXECUTE format($ins$
        INSERT INTO %I.tcg_normalization_rules
            (normalization_rule_id, field, rule_type, from_val, to_val, enabled, priority, note)
        VALUES
            ('NR0001', 'PRICE', 'REMOVE', '@', '', TRUE, 10, 'AI価格接頭辞'),
            ('NR0002', 'PRICE', 'REMOVE', '円', '', TRUE, 20, '価格通貨'),
            ('NR0003', 'PRICE', 'REMOVE', '¥', '', TRUE, 30, '価格通貨'),
            ('NR0004', 'PRICE', 'REMOVE', '￥', '', TRUE, 40, '価格通貨'),
            ('NR0005', 'PRICE', 'REMOVE', ',', '', TRUE, 50, '3桁区切り'),
            ('NR0006', 'PRICE', 'REMOVE', ' ', '', TRUE, 60, '半角空白'),
            ('NR0007', 'PRICE', 'REMOVE', '　', '', TRUE, 70, '全角空白'),
            ('NR0008', 'QUANTITY', 'REMOVE', ',', '', TRUE, 10, '3桁区切り'),
            ('NR0009', 'QUANTITY', 'REMOVE', ' ', '', TRUE, 20, '半角空白'),
            ('NR0010', 'QUANTITY', 'REMOVE', '　', '', TRUE, 30, '全角空白'),
            ('NR0011', 'PRODUCT_NAME', 'REMOVE', '⭐️', '', TRUE, 10, '先頭装飾'),
            ('NR0012', 'CONDITION', 'REMOVE', '⭐️', '', TRUE, 10, '先頭装飾'),
            ('NR0013', 'NOTE', 'REMOVE', '⭐️', '', TRUE, 10, '先頭装飾'),
            ('NR0014', 'UNIT', 'REMOVE', '⭐️', '', TRUE, 10, '先頭装飾'),
            ('NR0015', 'STATUS', 'REMOVE', '⭐️', '', TRUE, 10, '先頭装飾'),
            ('NR0016', 'PRODUCT_NAME', 'REPLACE', '－', 'ー', TRUE, 20, '全角ハイフン'),
            ('NR0017', 'CONDITION', 'REPLACE', '－', 'ー', TRUE, 20, '全角ハイフン'),
            ('NR0018', 'NOTE', 'REPLACE', '－', 'ー', TRUE, 20, '全角ハイフン'),
            ('NR0019', 'UNIT', 'REPLACE', '－', 'ー', TRUE, 20, '全角ハイフン'),
            ('NR0020', 'STATUS', 'REPLACE', '－', 'ー', TRUE, 20, '全角ハイフン'),
            ('NR0021', 'PRODUCT_NAME', 'REMOVE', '●', '', TRUE, 30, '既存装飾除去'),
            ('NR0022', 'PRODUCT_NAME', 'REMOVE', '◆', '', TRUE, 40, '既存装飾除去'),
            ('NR0023', 'PRODUCT_NAME', 'REMOVE', '◎', '', TRUE, 50, '既存装飾除去'),
            ('NR0024', 'PRODUCT_NAME', 'REMOVE', '▪', '', TRUE, 60, '既存装飾除去'),
            ('NR0025', 'PRODUCT_NAME', 'REMOVE', '▫', '', TRUE, 70, '既存装飾除去'),
            ('NR0026', 'PRODUCT_NAME', 'REMOVE', '■', '', TRUE, 80, '既存装飾除去'),
            ('NR0027', 'PRODUCT_NAME', 'REMOVE', '□', '', TRUE, 90, '既存装飾除去'),
            ('NR0028', 'PRODUCT_NAME', 'REMOVE', '★', '', TRUE, 100, '既存装飾除去'),
            ('NR0029', 'PRODUCT_NAME', 'REMOVE', '☆', '', TRUE, 110, '既存装飾除去'),
            ('NR0030', 'PRODUCT_NAME', 'REMOVE', '・', '', TRUE, 120, '既存装飾除去'),
            ('NR0031', 'PRODUCT_NAME', 'REMOVE', '※', '', TRUE, 130, '既存装飾除去'),
            ('NR0032', 'PRODUCT_NAME', 'REMOVE', '▶', '', TRUE, 140, '既存装飾除去'),
            ('NR0033', 'PRODUCT_NAME', 'REMOVE', '▷', '', TRUE, 150, '既存装飾除去'),
            ('NR0034', 'PRODUCT_NAME', 'REMOVE', '▼', '', TRUE, 160, '既存装飾除去'),
            ('NR0035', 'PRODUCT_NAME', 'REMOVE', '▽', '', TRUE, 170, '既存装飾除去'),
            ('NR0036', 'PRODUCT_NAME', 'REMOVE', '◉', '', TRUE, 180, '既存装飾除去'),
            ('NR0037', 'PRODUCT_NAME', 'REMOVE', '⚫', '', TRUE, 190, '既存装飾除去'),
            ('NR0038', 'PRODUCT_NAME', 'REMOVE', '⭐', '', TRUE, 200, '既存装飾除去'),
            ('NR0039', 'PRODUCT_NAME', 'REMOVE', '️', '', TRUE, 210, '既存装飾除去'),
            ('NR0040', 'PRODUCT_NAME', 'REMOVE', '‍', '', TRUE, 220, '既存装飾除去'),
            ('NR0041', 'CONDITION', 'REMOVE', '●', '', TRUE, 30, '既存装飾除去'),
            ('NR0042', 'CONDITION', 'REMOVE', '◆', '', TRUE, 40, '既存装飾除去'),
            ('NR0043', 'CONDITION', 'REMOVE', '◎', '', TRUE, 50, '既存装飾除去'),
            ('NR0044', 'CONDITION', 'REMOVE', '▪', '', TRUE, 60, '既存装飾除去'),
            ('NR0045', 'CONDITION', 'REMOVE', '▫', '', TRUE, 70, '既存装飾除去'),
            ('NR0046', 'CONDITION', 'REMOVE', '■', '', TRUE, 80, '既存装飾除去'),
            ('NR0047', 'CONDITION', 'REMOVE', '□', '', TRUE, 90, '既存装飾除去'),
            ('NR0048', 'CONDITION', 'REMOVE', '★', '', TRUE, 100, '既存装飾除去'),
            ('NR0049', 'CONDITION', 'REMOVE', '☆', '', TRUE, 110, '既存装飾除去'),
            ('NR0050', 'CONDITION', 'REMOVE', '・', '', TRUE, 120, '既存装飾除去'),
            ('NR0051', 'CONDITION', 'REMOVE', '※', '', TRUE, 130, '既存装飾除去'),
            ('NR0052', 'CONDITION', 'REMOVE', '▶', '', TRUE, 140, '既存装飾除去'),
            ('NR0053', 'CONDITION', 'REMOVE', '▷', '', TRUE, 150, '既存装飾除去'),
            ('NR0054', 'CONDITION', 'REMOVE', '▼', '', TRUE, 160, '既存装飾除去'),
            ('NR0055', 'CONDITION', 'REMOVE', '▽', '', TRUE, 170, '既存装飾除去'),
            ('NR0056', 'CONDITION', 'REMOVE', '◉', '', TRUE, 180, '既存装飾除去'),
            ('NR0057', 'CONDITION', 'REMOVE', '⚫', '', TRUE, 190, '既存装飾除去'),
            ('NR0058', 'CONDITION', 'REMOVE', '⭐', '', TRUE, 200, '既存装飾除去'),
            ('NR0059', 'CONDITION', 'REMOVE', '️', '', TRUE, 210, '既存装飾除去'),
            ('NR0060', 'CONDITION', 'REMOVE', '‍', '', TRUE, 220, '既存装飾除去'),
            ('NR0061', 'NOTE', 'REMOVE', '●', '', TRUE, 30, '既存装飾除去'),
            ('NR0062', 'NOTE', 'REMOVE', '◆', '', TRUE, 40, '既存装飾除去'),
            ('NR0063', 'NOTE', 'REMOVE', '◎', '', TRUE, 50, '既存装飾除去'),
            ('NR0064', 'NOTE', 'REMOVE', '▪', '', TRUE, 60, '既存装飾除去'),
            ('NR0065', 'NOTE', 'REMOVE', '▫', '', TRUE, 70, '既存装飾除去'),
            ('NR0066', 'NOTE', 'REMOVE', '■', '', TRUE, 80, '既存装飾除去'),
            ('NR0067', 'NOTE', 'REMOVE', '□', '', TRUE, 90, '既存装飾除去'),
            ('NR0068', 'NOTE', 'REMOVE', '★', '', TRUE, 100, '既存装飾除去'),
            ('NR0069', 'NOTE', 'REMOVE', '☆', '', TRUE, 110, '既存装飾除去'),
            ('NR0070', 'NOTE', 'REMOVE', '・', '', TRUE, 120, '既存装飾除去'),
            ('NR0071', 'NOTE', 'REMOVE', '※', '', TRUE, 130, '既存装飾除去'),
            ('NR0072', 'NOTE', 'REMOVE', '▶', '', TRUE, 140, '既存装飾除去'),
            ('NR0073', 'NOTE', 'REMOVE', '▷', '', TRUE, 150, '既存装飾除去'),
            ('NR0074', 'NOTE', 'REMOVE', '▼', '', TRUE, 160, '既存装飾除去'),
            ('NR0075', 'NOTE', 'REMOVE', '▽', '', TRUE, 170, '既存装飾除去'),
            ('NR0076', 'NOTE', 'REMOVE', '◉', '', TRUE, 180, '既存装飾除去'),
            ('NR0077', 'NOTE', 'REMOVE', '⚫', '', TRUE, 190, '既存装飾除去'),
            ('NR0078', 'NOTE', 'REMOVE', '⭐', '', TRUE, 200, '既存装飾除去'),
            ('NR0079', 'NOTE', 'REMOVE', '️', '', TRUE, 210, '既存装飾除去'),
            ('NR0080', 'NOTE', 'REMOVE', '‍', '', TRUE, 220, '既存装飾除去'),
            ('NR0081', 'UNIT', 'REMOVE', '●', '', TRUE, 30, '既存装飾除去'),
            ('NR0082', 'UNIT', 'REMOVE', '◆', '', TRUE, 40, '既存装飾除去'),
            ('NR0083', 'UNIT', 'REMOVE', '◎', '', TRUE, 50, '既存装飾除去'),
            ('NR0084', 'UNIT', 'REMOVE', '▪', '', TRUE, 60, '既存装飾除去'),
            ('NR0085', 'UNIT', 'REMOVE', '▫', '', TRUE, 70, '既存装飾除去'),
            ('NR0086', 'UNIT', 'REMOVE', '■', '', TRUE, 80, '既存装飾除去'),
            ('NR0087', 'UNIT', 'REMOVE', '□', '', TRUE, 90, '既存装飾除去'),
            ('NR0088', 'UNIT', 'REMOVE', '★', '', TRUE, 100, '既存装飾除去'),
            ('NR0089', 'UNIT', 'REMOVE', '☆', '', TRUE, 110, '既存装飾除去'),
            ('NR0090', 'UNIT', 'REMOVE', '・', '', TRUE, 120, '既存装飾除去'),
            ('NR0091', 'UNIT', 'REMOVE', '※', '', TRUE, 130, '既存装飾除去'),
            ('NR0092', 'UNIT', 'REMOVE', '▶', '', TRUE, 140, '既存装飾除去'),
            ('NR0093', 'UNIT', 'REMOVE', '▷', '', TRUE, 150, '既存装飾除去'),
            ('NR0094', 'UNIT', 'REMOVE', '▼', '', TRUE, 160, '既存装飾除去'),
            ('NR0095', 'UNIT', 'REMOVE', '▽', '', TRUE, 170, '既存装飾除去'),
            ('NR0096', 'UNIT', 'REMOVE', '◉', '', TRUE, 180, '既存装飾除去'),
            ('NR0097', 'UNIT', 'REMOVE', '⚫', '', TRUE, 190, '既存装飾除去'),
            ('NR0098', 'UNIT', 'REMOVE', '⭐', '', TRUE, 200, '既存装飾除去'),
            ('NR0099', 'UNIT', 'REMOVE', '️', '', TRUE, 210, '既存装飾除去'),
            ('NR0100', 'UNIT', 'REMOVE', '‍', '', TRUE, 220, '既存装飾除去'),
            ('NR0101', 'STATUS', 'REMOVE', '●', '', TRUE, 30, '既存装飾除去'),
            ('NR0102', 'STATUS', 'REMOVE', '◆', '', TRUE, 40, '既存装飾除去'),
            ('NR0103', 'STATUS', 'REMOVE', '◎', '', TRUE, 50, '既存装飾除去'),
            ('NR0104', 'STATUS', 'REMOVE', '▪', '', TRUE, 60, '既存装飾除去'),
            ('NR0105', 'STATUS', 'REMOVE', '▫', '', TRUE, 70, '既存装飾除去'),
            ('NR0106', 'STATUS', 'REMOVE', '■', '', TRUE, 80, '既存装飾除去'),
            ('NR0107', 'STATUS', 'REMOVE', '□', '', TRUE, 90, '既存装飾除去'),
            ('NR0108', 'STATUS', 'REMOVE', '★', '', TRUE, 100, '既存装飾除去'),
            ('NR0109', 'STATUS', 'REMOVE', '☆', '', TRUE, 110, '既存装飾除去'),
            ('NR0110', 'STATUS', 'REMOVE', '・', '', TRUE, 120, '既存装飾除去'),
            ('NR0111', 'STATUS', 'REMOVE', '※', '', TRUE, 130, '既存装飾除去'),
            ('NR0112', 'STATUS', 'REMOVE', '▶', '', TRUE, 140, '既存装飾除去'),
            ('NR0113', 'STATUS', 'REMOVE', '▷', '', TRUE, 150, '既存装飾除去'),
            ('NR0114', 'STATUS', 'REMOVE', '▼', '', TRUE, 160, '既存装飾除去'),
            ('NR0115', 'STATUS', 'REMOVE', '▽', '', TRUE, 170, '既存装飾除去'),
            ('NR0116', 'STATUS', 'REMOVE', '◉', '', TRUE, 180, '既存装飾除去'),
            ('NR0117', 'STATUS', 'REMOVE', '⚫', '', TRUE, 190, '既存装飾除去'),
            ('NR0118', 'STATUS', 'REMOVE', '⭐', '', TRUE, 200, '既存装飾除去'),
            ('NR0119', 'STATUS', 'REMOVE', '️', '', TRUE, 210, '既存装飾除去'),
            ('NR0120', 'STATUS', 'REMOVE', '‍', '', TRUE, 220, '既存装飾除去'),
            ('NR0121', 'NOTE', 'REGEX_REPLACE', '^\((\d{1,2}\/\d{1,2})発\)$', '$1発送', TRUE, 1000, 'existing shipping normalization'),
            ('NR0122', 'NOTE', 'REGEX_REPLACE', '^\((\d{1,2}日)\)$', '$1発送', TRUE, 1010, 'existing shipping normalization'),
            ('NR0123', 'NOTE', 'REGEX_REPLACE', '^\((\d{1,2}\/\d{1,2}発送)\)$', '$1', TRUE, 1020, 'existing shipping normalization'),
            ('NR0124', 'NOTE', 'REGEX_REPLACE', '^(\d{1,2}\/\d{1,2})発$', '$1発送', TRUE, 1030, 'existing shipping normalization'),
            ('NR0125', 'NOTE', 'REGEX_REPLACE', '^(\d{1,2}日)$', '$1発送', TRUE, 1040, 'existing shipping normalization'),
            ('NR0126', 'NOTE', 'REGEX_REPLACE', '(\d{1,2}\/\d{1,2})[^\d\/]*発送', '$1発送', TRUE, 1050, 'existing shipping normalization'),
            ('NR0127', 'NOTE', 'REGEX_REPLACE', '(\d{1,2}\/\d{1,2})[^\d\/]*発$', '$1発送', TRUE, 1060, 'existing shipping normalization'),
            ('NR0128', 'PRODUCT_NAME_MATCH', 'REGEX_REPLACE', '^[■●▲・\s\d.]+', '', TRUE, 10, 'existing partial-match normalization'),
            ('NR0129', 'PRODUCT_NAME_MATCH', 'REGEX_REPLACE', '\s+', ' ', TRUE, 20, 'existing partial-match normalization'),
            ('NR0130', 'SCORING_COMPARE', 'REPLACE', '　', ' ', TRUE, 10, 'existing scoring comparison normalization'),
            ('NR0131', 'SCORING_COMPARE', 'REGEX_REPLACE', '[\n\r]', ' ', TRUE, 20, 'existing scoring comparison normalization'),
            ('NR0132', 'SCORING_COMPARE', 'REGEX_REPLACE', '[ \t]+', ' ', TRUE, 30, 'existing scoring comparison normalization'),
            ('NR0133', 'CONDITION', 'REGEX_REPLACE', '[　]+', ' ', TRUE, 1000, 'existing condition whitespace normalization'),
            ('NR0134', 'CONDITION', 'REGEX_REPLACE', '\s+', ' ', TRUE, 1010, 'existing condition whitespace normalization'),
            ('NR0135', 'STATUS', 'REGEX_REPLACE', '[\s　  ]+', '', TRUE, 1000, 'existing status matching normalization')
        ON CONFLICT (normalization_rule_id) DO NOTHING
    $ins$, _schema);

    -- -------------------------------------------------------------------------
    -- COUNT 検証（このmigrationが挿入した NR0001〜NR0135 の135件を確認）
    -- BETWEEN で担当範囲を限定することで、後から追加された行に影響されない
    -- -------------------------------------------------------------------------
    EXECUTE format(
        'SELECT count(*) FROM %I.tcg_normalization_rules WHERE normalization_rule_id BETWEEN $1 AND $2',
        _schema
    ) INTO _count USING 'NR0001', 'NR0135';

    IF _count <> 135 THEN
        RAISE EXCEPTION 'migration 20260903_160000: tcg_normalization_rules count mismatch (expected 135, got %)', _count;
    END IF;

    RAISE NOTICE 'migration 20260903_160000: tcg_normalization_rules: 135 rows OK (NR0001-NR0135)';
END $body$;