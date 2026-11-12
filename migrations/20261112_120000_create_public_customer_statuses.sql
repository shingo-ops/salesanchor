-- 会社と連絡先の状態 便1: 状態の表 public.customer_statuses を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/status-ssot-contact-company/design.md §3
-- 会社（companies）と連絡先（contacts）の status に入る4つの記号・日英の名前・並び順の正本。会社ごとの独自の状態は持たない（tenant_id 列なし）。
-- RLS: 読むのは誰でも全行（USING (true)）。便2 の外部キーの VALIDATE が FORCE の下で行を絞られないため（design.md §3）。書くのは運営だけ。
-- 行を入れる文は書かない（4行は別のデータ変更で PO が流す・ADR-1007）。この便では作るだけで、どこからも読まれない。
--
-- ロールバック: 表は残してプログラムが使わない（表を消すのは別便・PO GO）。

BEGIN;

CREATE TABLE IF NOT EXISTS public.customer_statuses (
    code                 VARCHAR(20) PRIMARY KEY,
    name_ja              VARCHAR(50) NOT NULL,
    name_en              VARCHAR(50) NOT NULL,
    sort_order           SMALLINT    NOT NULL UNIQUE,
    is_active            BOOLEAN     NOT NULL DEFAULT TRUE,
    selectable_on_create BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.customer_statuses IS '会社と連絡先の状態の正本。記号・日英の名前・並び順。運営だけが書く';
COMMENT ON COLUMN public.customer_statuses.code IS '会社・連絡先の status 列に入る記号（変えない）';
COMMENT ON COLUMN public.customer_statuses.name_ja IS '画面に出す日本語の名前';
COMMENT ON COLUMN public.customer_statuses.name_en IS '画面に出す英語の名前';
COMMENT ON COLUMN public.customer_statuses.sort_order IS '選択肢と集計の並び順（小さい順）';
COMMENT ON COLUMN public.customer_statuses.is_active IS 'FALSE＝新しく選べない（過去の行は残る）。消す代わりに使う';
COMMENT ON COLUMN public.customer_statuses.selectable_on_create IS 'FALSE＝作る画面の選択肢に出さない（直す画面には出す）';
COMMENT ON COLUMN public.customer_statuses.created_at IS '作った時刻';
COMMENT ON COLUMN public.customer_statuses.updated_at IS '直した時刻';

ALTER TABLE public.customer_statuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_statuses FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customer_statuses_select ON public.customer_statuses;
CREATE POLICY customer_statuses_select ON public.customer_statuses FOR SELECT
  USING (true);

DROP POLICY IF EXISTS customer_statuses_insert ON public.customer_statuses;
CREATE POLICY customer_statuses_insert ON public.customer_statuses FOR INSERT
  WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS customer_statuses_update ON public.customer_statuses;
CREATE POLICY customer_statuses_update ON public.customer_statuses FOR UPDATE
  USING (current_setting('app.is_operator', true) = 'true')
  WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS customer_statuses_delete ON public.customer_statuses;
CREATE POLICY customer_statuses_delete ON public.customer_statuses FOR DELETE
  USING (current_setting('app.is_operator', true) = 'true');

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT ON public.customer_statuses TO salesanchor_app;
    END IF;
END $$;

COMMIT;
