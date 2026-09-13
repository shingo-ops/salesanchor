-- DIST-01 A': tcg_normalization_rules に NR0136（全角＠ U+FF20 除去）を追加（冪等）
--
-- 背景（設計書 ~/Documents/dist01_backup/DISTRIBUTION_DESIGN.md §2）:
--   price_normalized = NULL の91件のうち51件が全角＠（U+FF20）+ 数値 + 円 形式。
--   既存 NR0001 は半角@（U+0040）のみ対応。NR0136 で全角＠を除去することで
--   新エンジン再解析後に51件が数値化され、NULL が 91 → 3件 になる見込み。
--   ※「時」（80,000時 の3件）は除去しない（意味確定不可・誤適用リスク）
--   ※ NR0008 は QUANTITY フィールドに既存（3桁区切り）のため NR0136 を使用

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_190000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format($sql$
        INSERT INTO %I.tcg_normalization_rules
            (normalization_rule_id, field, rule_type, from_val, to_val, enabled, priority, note)
        VALUES
            ('NR0136', 'PRICE', 'REMOVE', '＠', '', true, 35,
             '全角アットマーク（U+FF20）除去。半角@と同義の表記ゆれ。配信時 price_normalized NULL 51件を解消')
        ON CONFLICT (normalization_rule_id) DO NOTHING
    $sql$, _schema);

    RAISE NOTICE 'migration 20260903_190000: NR0136 inserted (or already existed)';
END
$body$;
