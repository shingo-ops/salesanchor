-- channel-master-shared PR-C（design §6 の4）: 古い会社ごとの名簿 tenant_NNN.channel_masters を消す。
-- 名簿は public.channel_masters（全社1つ）に移った（PR-A/PR-B）。会社ごとの表は 2026-11-07 時点で全社 public と同じ6行だけ。
-- 何度流しても安全（IF EXISTS）。CASCADE は付けない（ビューは run_all_migrations.sh の先頭で外れている。
-- 想定外の依存があれば止まって反映が失敗する側に倒す）。連番 channel_masters_id_seq は表と一緒に消える（OWNED BY）。
-- 戻し方: この PR を revert して反映すると 20260611 が流れ空の表ができる。中身は反映前の控え（reader の道で取った6行×5社）から戻す。ADR-1069。
DO $$
DECLARE
  r record;
BEGIN
  FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' ORDER BY nspname LOOP
    EXECUTE format('DROP TABLE IF EXISTS %I.channel_masters', r.nspname);
  END LOOP;
END $$;
