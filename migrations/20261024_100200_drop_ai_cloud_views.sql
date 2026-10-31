-- ADR-1052 段1: ai_cloud スキーマ（相談係用の伏せたビュー）を外す（冪等）。
-- 目的: run_all_migrations.sh は全 migration を毎デプロイ再実行する。ビューが残っていると、
--       後続の migration の DROP / ALTER（列削除・型変更・表の作り直し）が
--       「ビューが依存している」と言って失敗するため、一覧の先頭で外す。
--       ビューの作成（20261024_100300_create_ai_cloud_views.sql）は EXIT trap で最後に流す。
-- ai_cloud_meta（分類表・記録）は ai_cloud の外にあるので消えない。
DROP SCHEMA IF EXISTS ai_cloud CASCADE;
