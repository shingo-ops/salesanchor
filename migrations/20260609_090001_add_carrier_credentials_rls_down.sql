-- Down Migration: tenant_carrier_credentials の RLS ポリシーを無効化する
--
-- 対応 up migration: 20260609_090000_add_carrier_credentials_rls.sql
--
-- 目的:
--   PR-A（RLS ポリシー追加）を本番適用後に問題が発覚した際のロールバック手順。
--   データは一切削除しない。RLS を無効化するだけなのでアプリ層の WHERE tenant_id 句が
--   引き続き安全弁として機能する（アプリ層フィルタは RLS とは独立して動作）。
--
-- 実行タイミング:
--   1. 本番データベースで直接 psql 実行
--   2. または scripts/run_all_migrations.sh と同等の管理者権限で実行
--
-- 冪等: IF EXISTS で安全に再実行可能
--
-- 警告:
--   このスクリプトを実行すると RLS によるテナント分離が解除される。
--   アプリ層の WHERE tenant_id 句は残るが、DB レイヤの多重防衛は失われる。
--   問題解決後は up migration を再適用すること。

-- RLS ポリシーを削除
DROP POLICY IF EXISTS tenant_isolation_carrier_credentials ON tenant_carrier_credentials;

-- RLS を無効化（FORCE も同時に解除される）
ALTER TABLE tenant_carrier_credentials DISABLE ROW LEVEL SECURITY;
