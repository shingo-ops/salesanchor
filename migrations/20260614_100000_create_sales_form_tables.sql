-- ADR-108 Phase B-1: sales_form 複数選択対応
--
-- 目的:
--   カルテ company tab の販売形態フィールドを複数選択 + その他自由記述 +
--   テナント別カスタム選択肢に対応するため、2テーブルを新設する。
--
-- 設計方針:
--   - D案（tenant_sales_form_options + lead_sales_form_selections）
--   - 旧 leads.sales_form カラムは残す（additive-only, ADR-045）
--   - option 削除は is_active=false 運用（CASCADE DELETE はリード削除時のみ）
--   - 全テナントスキーマに適用 (DO $$ pg_namespace ループ)
--   - スキーマプレースホルダ形式禁止 → EXECUTE format() で動的SQL (ADR チェック3)
--   - REFERENCES public.X 禁止 → テナント内FK使用 (ADR チェック4)
--   - 初期データは tenant_004 のみ投入（existing テナント）
--
-- 冪等性: CREATE TABLE IF NOT EXISTS / INSERT ... ON CONFLICT DO NOTHING

DO $$
DECLARE
  schema_record RECORD;
BEGIN
  FOR schema_record IN
    SELECT nspname AS schema_name
    FROM pg_namespace
    WHERE nspname LIKE 'tenant_%'
    ORDER BY nspname
  LOOP

    -- ----------------------------------------------------------------
    -- 1. tenant_sales_form_options
    --    テナントごとに管理できる販売形態マスタ
    --    将来のテナント管理画面CRUD用途に is_active / sort_order を持つ
    -- ----------------------------------------------------------------
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I.tenant_sales_form_options (
         id         SERIAL PRIMARY KEY,
         tenant_id  INTEGER      NOT NULL,
         label      VARCHAR(100) NOT NULL,
         value      VARCHAR(100) NOT NULL,
         sort_order INTEGER      NOT NULL DEFAULT 0,
         is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
         created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
         UNIQUE (tenant_id, value)
       )',
      schema_record.schema_name
    );

    -- ----------------------------------------------------------------
    -- 2. lead_sales_form_selections
    --    リードごとの選択状態（多対多）
    --    option 側は is_active=false 運用のため CASCADE DELETE しない
    --    lead 削除時は selections も CASCADE DELETE する
    -- ----------------------------------------------------------------
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I.lead_sales_form_selections (
         id          SERIAL PRIMARY KEY,
         lead_id     INTEGER NOT NULL
                       REFERENCES %I.leads(id) ON DELETE CASCADE,
         option_id   INTEGER NOT NULL
                       REFERENCES %I.tenant_sales_form_options(id) ON DELETE RESTRICT,
         other_text  TEXT,
         created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
         UNIQUE (lead_id, option_id)
       )',
      schema_record.schema_name,
      schema_record.schema_name,
      schema_record.schema_name
    );

    -- ----------------------------------------------------------------
    -- 3. インデックス（検索効率化）
    -- ----------------------------------------------------------------
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_lead_sales_form_selections_lead_id
       ON %I.lead_sales_form_selections (lead_id)',
      schema_record.schema_name
    );

    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_tenant_sales_form_options_tenant_active
       ON %I.tenant_sales_form_options (tenant_id, is_active)',
      schema_record.schema_name
    );

    -- ----------------------------------------------------------------
    -- 4. 初期データ投入（tenant_004 のみ）
    --    新規テナント作成時はテナント管理画面 or 別スクリプトで投入する
    -- ----------------------------------------------------------------
    IF schema_record.schema_name = 'tenant_004' THEN
      INSERT INTO tenant_004.tenant_sales_form_options
        (tenant_id, label, value, sort_order)
      VALUES
        (4, '実店舗',   'physical_store',  1),
        (4, 'ECサイト', 'ec_site',          2),
        (4, 'ライブ配信', 'live_streaming', 3),
        (4, '卸・代理店', 'wholesale',      4),
        (4, 'その他',   'other',            5)
      ON CONFLICT (tenant_id, value) DO NOTHING;
    END IF;

  END LOOP;
END $$;
