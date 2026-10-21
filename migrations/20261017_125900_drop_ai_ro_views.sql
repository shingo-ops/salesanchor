-- ADR-1024 便3a: ai_ro スキーマ（AI 用の読み取り専用ビュー）を外す（冪等）。
-- 目的: run_all_migrations.sh は全 migration を毎デプロイ再実行する。ビューが残っていると、
--       後続の migration の DROP / ALTER（列削除・型変更・表の作り直し）が
--       「ビューが依存している」と言って失敗するため、一覧の先頭で外す。
--       ビューの作成（20261017_130100_create_ai_ro_views.sql）は、スクリプトが正常終了したとき
--       だけ EXIT trap で最後に流す。
DROP SCHEMA IF EXISTS ai_ro CASCADE;
