-- ADR-1043 便1: 精度測定の正解表。空の表を作るだけ。値は書かない（ADR-1007）。冪等。
-- ロールバック: docs/handoff/accuracy-gold-db/design.md §7（表ごと消す文はそこに書く。不可逆のため PO 確認）

CREATE TABLE IF NOT EXISTS public.accuracy_gold_versions (
    id           SERIAL       PRIMARY KEY,
    gold_version TEXT         NOT NULL UNIQUE,
    file_sha256  TEXT         NOT NULL,
    row_count    INTEGER      NOT NULL,
    post_count   INTEGER      NOT NULL,
    note         TEXT         NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT accuracy_gold_versions_version_check CHECK (gold_version ~ '^[a-z0-9_]+$'),
    CONSTRAINT accuracy_gold_versions_sha256_check CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT accuracy_gold_versions_rows_check CHECK (row_count > 0),
    CONSTRAINT accuracy_gold_versions_posts_check CHECK (post_count > 0)
);

CREATE TABLE IF NOT EXISTS public.accuracy_gold_rows (
    id            SERIAL       PRIMARY KEY,
    gold_version  TEXT         NOT NULL REFERENCES public.accuracy_gold_versions(gold_version) ON DELETE CASCADE,
    row_no        INTEGER      NOT NULL CHECK (row_no > 0),
    post_id       UUID         NOT NULL,
    price_line    TEXT         NOT NULL DEFAULT '',
    lines         TEXT         NOT NULL DEFAULT '',
    allowed_lines TEXT         NOT NULL DEFAULT '',
    e2_price      TEXT         NOT NULL DEFAULT '',
    e3_quantity   TEXT         NOT NULL DEFAULT '',
    a1_product_id TEXT         NOT NULL DEFAULT '',
    a2_condition  TEXT         NOT NULL DEFAULT '',
    a3_unit       TEXT         NOT NULL DEFAULT '',
    a4_status     TEXT         NOT NULL DEFAULT '',
    a5_ship       TEXT         NOT NULL DEFAULT '',
    a4_basis      TEXT         NOT NULL DEFAULT '',
    hesitation    TEXT         NOT NULL DEFAULT '',
    exclusion     TEXT         NOT NULL DEFAULT '',
    ruling_basis  TEXT         NOT NULL DEFAULT '',
    po_check      TEXT         NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT accuracy_gold_rows_version_row_key UNIQUE (gold_version, row_no)
);

CREATE INDEX IF NOT EXISTS accuracy_gold_rows_version_post_idx ON public.accuracy_gold_rows (gold_version, post_id);

COMMENT ON TABLE public.accuracy_gold_versions IS
    'ADR-1043: 精度測定の正解表の版。1行=1版（ファイルの sha256・行数・投稿数）';
COMMENT ON TABLE public.accuracy_gold_rows IS
    'ADR-1043: 精度測定の正解表の中身。1行=正解表の1行（row_no=ファイルのデータ行番号）。社外秘。通常の接続からは読めない（RLS）';

ALTER TABLE public.accuracy_gold_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accuracy_gold_versions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS accuracy_gold_versions_operator ON public.accuracy_gold_versions;
CREATE POLICY accuracy_gold_versions_operator ON public.accuracy_gold_versions
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.accuracy_gold_rows ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accuracy_gold_rows FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS accuracy_gold_rows_operator ON public.accuracy_gold_rows;
CREATE POLICY accuracy_gold_rows_operator ON public.accuracy_gold_rows
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');
