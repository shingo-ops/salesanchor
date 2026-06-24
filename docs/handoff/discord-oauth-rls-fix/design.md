# Phase 3 設計 — discord-oauth-rls-fix

**対象ADR**: ADR-091（Discord Bot OAuth フロー）
**recon**: docs/handoff/discord-oauth-rls-fix/recon.md
**日付**: 2026-06-24
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：公開 OAuth callback エンドポイントで認証コンテキストが必要なテーブルへの書き込みは既存の `set_tenant_context` パターン（ADR-072）に従って解決できる。外部事例を参照する設計上の判断点は存在しない。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| callback で `set_tenant_context(db, tenant_id)` が upsert 前に呼ばれる | `test_discord_oauth.py::test_callback_calls_set_tenant_context_before_db_writes` PASS |
| PostgreSQL 実 DB で audit_logs RLS 有効下の INSERT が通る | `test_discord_oauth_rls.py::test_audit_logs_insert_passes_with_set_tenant_context` PASS（要 RLS_ADMIN_DATABASE_URL） |
| app.tenant_id 未設定では audit_logs INSERT が RLS に弾かれる（修正前の再現） | `test_discord_oauth_rls.py::test_audit_logs_insert_blocked_without_set_tenant_context` PASS（要 RLS_ADMIN_DATABASE_URL） |
| 既存テスト全件 PASS（リグレッションなし） | `pytest backend/tests/test_discord_oauth.py` 9/9 PASS |
| migration / deploy.yml / RLS ポリシー変更ゼロ | `git diff HEAD --name-only` に migrations/ / deploy.yml / tenant.py 含まれないこと |

---

## 技術 How・KPI

- KPI: tenant_006 で Discord Bot Invite → callback → `?discord_status=connected` リダイレクトが成功すること（PO 実機確認）
- 技術選択: `set_tenant_context(db, tenant_id)` を `discord_oauth.py:183`（tenant_id 確定直後・upsert 前）に追加。ADR-072 パターン踏襲。`get_db` finally の `clear_tenant_context` でリセット全経路保証済み（追加の try/finally 不要）

---

## 弊害・トレードオフ

- `SET search_path` / `SET app.tenant_id` が 2 クエリ追加されるが、オーバーヘッドは無視できる
- `public.tenant_discord_config` は RLS なしのため search_path 変更の副作用なし

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `discord_oauth.py:183` に `await set_tenant_context(db, tenant_id)` 追加 | Generator |
| 2 | `test_discord_oauth.py` に set_tenant_context 呼び出しアサート追加 | Generator |
| 3 | `test_discord_oauth_rls.py` 新規作成（PostgreSQL RLS 実証テスト） | Generator |

---

## 継続

- 完了後の監視: デプロイ後 tenant_006 で Discord Bot Invite → callback → `/channels?discord_status=connected` を PO 目視確認
- 次フェーズへの引き継ぎ: 同種バグなし（横展開確認済み）
