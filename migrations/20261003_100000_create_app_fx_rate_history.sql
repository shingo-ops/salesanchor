-- Migration 20261003_100000: public.app_fx_rate_history テーブル新設
-- 目的: ADR-148 の為替レート SSOT (app_fx_rates) は UPSERT により上書きされるため、
--       過去の実際のレートが失われる。LLM 使用量ダッシュボードで「その時点のレート」で
--       USD→JPY 換算するために、追記専用（append-only）の履歴テーブルを新設する。
--       本 PR（PR-A）はテーブル作成のみ。書き込み/読み取りの切替は別PR（PR-B）で行う。
--       詳細: docs/adr/ADR-148-fx-rate-ssot.md の 2026-10-03 追記セクション。
--
-- 設計:
--   - 全テナント共通の公開情報（public に配置、app_fx_rates と同じ方針）
--   - PRIMARY KEY (currency, fetched_at) — 取得時刻ごとに1行を追記（上書きしない）
--   - rate_jpy は 0 より大きい値のみ許可（CHECK 制約）
--   - RLS は app_fx_rates と同じ方針: 読み取りは全ロール許可・書き込みは operator のみ
--
-- ロールバック / DOWN:
--   手順は docs/handoff/fx-rate-history/design.md のロールバック節を参照。
--   本テーブルを削除する操作は不可逆であり、ADR-1003 の委任 GO の例外に当たる
--   ため PO 本人の GO が必要（process-artifacts ゲートの DROP 検出対象になるため
--   migration ファイル本体にも DROP 文を書かない）。
--
-- 冪等: CREATE TABLE IF NOT EXISTS / DROP POLICY IF EXISTS → CREATE POLICY /
--       INSERT ... ON CONFLICT DO NOTHING（既存 app_fx_rates からのシード取り込み）

-- === 1. テーブル作成 ===
CREATE TABLE IF NOT EXISTS public.app_fx_rate_history (
    currency   VARCHAR(3)    NOT NULL,
    rate_jpy   NUMERIC(12,4) NOT NULL CHECK (rate_jpy > 0),
    fetched_at TIMESTAMPTZ   NOT NULL,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (currency, fetched_at)
);

COMMENT ON TABLE  public.app_fx_rate_history            IS 'ADR-148 追補: 為替レート履歴（追記専用・上書きしない）。PR-B 以降 app_fx_rates に代わる SSOT。LLM使用量ダッシュボードで各使用時点のレートによるJPY換算に使う。';
COMMENT ON COLUMN public.app_fx_rate_history.currency   IS '通貨コード (ISO 4217): USD / EUR 等';
COMMENT ON COLUMN public.app_fx_rate_history.rate_jpy   IS '1外貨 = rate_jpy 円（JPY 建て）取得時点の値';
COMMENT ON COLUMN public.app_fx_rate_history.fetched_at IS '外部API (open.er-api.com) から取得した時刻（UTC）。(currency, fetched_at) で一意';
COMMENT ON COLUMN public.app_fx_rate_history.created_at IS '当行がこのテーブルに挿入された時刻（追記監査用）';

-- === 2. RLS 有効化 ===
ALTER TABLE public.app_fx_rate_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_fx_rate_history FORCE ROW LEVEL SECURITY;

-- 読み取り: 全ロール許可（為替は公開情報・テナント分離不要）
DROP POLICY IF EXISTS app_fx_rate_history_read ON public.app_fx_rate_history;
CREATE POLICY app_fx_rate_history_read
    ON public.app_fx_rate_history
    FOR SELECT
    USING (true);

-- 書き込み (INSERT / UPDATE / DELETE): operator のみ
-- app.is_operator='true' は Celery ワーカーの set_tenant_context_sync が付与する
DROP POLICY IF EXISTS app_fx_rate_history_write ON public.app_fx_rate_history;
CREATE POLICY app_fx_rate_history_write
    ON public.app_fx_rate_history
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

-- === 3. シード: 既存 app_fx_rates の現在値を履歴に取り込む（冪等） ===
-- FORCE ROW LEVEL SECURITY が有効なため、この INSERT は app_fx_rate_history_write
-- ポリシー（app.is_operator='true' 必須）の対象になる。本番でマイグレーション実行
-- ロールが RLS を自動バイパスするか（BYPASSRLS 権限・テーブル所有者等）は未確認のため、
-- それに依存せず SELECT set_config で明示的に operator コンテキストを与える。
-- scripts/run_all_migrations.sh の run_sql() は `docker exec -i ... psql < file` で
-- ファイル単位に新規 psql 接続（セッション）を起動するため、ここで設定する
-- app.is_operator はこのファイル専用の1セッションに限定され、他マイグレーション・
-- 他セッションには影響しない（false = セッションスコープ、トランザクション終了で
-- 消えるトランザクションローカルではなく、このpsqlセッション全体で有効）。
SELECT set_config('app.is_operator', 'true', false);

INSERT INTO public.app_fx_rate_history (currency, rate_jpy, fetched_at)
SELECT currency, rate_jpy, fetched_at
FROM public.app_fx_rates
ON CONFLICT (currency, fetched_at) DO NOTHING;
