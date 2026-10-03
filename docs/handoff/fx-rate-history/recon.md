# 為替レート履歴（app_fx_rate_history）新設 — Recon

**日付**: 2026-10-03
**ブランチ**: release/fx-rate-history-table（PR-A）
**担当**: Hikky-dev（実装）／設計: Opus

---

## 1. 現状の為替レート SSOT（ADR-148）

- テーブル定義: `migrations/20260628_170000_add_app_fx_rates.sql:18-23`
  ```
  CREATE TABLE IF NOT EXISTS public.app_fx_rates (
      currency   VARCHAR(3)    PRIMARY KEY,
      rate_jpy   NUMERIC(12,4) NOT NULL,
      fetched_at TIMESTAMPTZ   NOT NULL,
      updated_at TIMESTAMPTZ   NOT NULL DEFAULT NOW()
  );
  ```
  `currency` が PRIMARY KEY のため、同一通貨の新しい取得値は UPDATE（UPSERT）で既存行を上書きする。過去値は残らない。
- 書き込み元1: `backend/app/tasks/fx_rate_updater.py:39-76`（Celery beat）。JST 6:00/18:00 に発火（`backend/app/celery_app.py:141-148`）。
- 書き込み元2: `POST /api/v1/super-admin/fx-rate/refresh`（`backend/app/routers/fx_rate_admin.py:84-131`）。手動即時更新、`require_super_admin`。
- 読み取り: `GET /api/v1/fx-rates/{currency}`（`backend/app/routers/fx_rate_admin.py:44-72`）。`public.app_fx_rates` から `currency` 一致行を1件返す。404 if not found。
- ADR: `docs/adr/ADR-148-fx-rate-ssot.md`（2026-06-28 制定、2026-10-01 追記あり: 読み取りパスの衝突修正）。

## 2. 本番の現在値

- 本番 `public.app_fx_rates` には USD の1行のみ存在: `rate_jpy = 157.8034`、`fetched_at = 2026-10-03 09:00Z`（設計担当が本番調査で確認済み・本カードの Facts セクションに記載）。
- これが「取得可能な最古のレート」である（UPSERT により過去値は消えているため）。

## 3. LLM 使用量台帳（ADR-1004）との関係

- テーブル定義: `migrations/20260930_150000_create_llm_usage_events.sql:27-50`（`public.llm_usage_events`）。
  - `occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()`（`migrations/20260930_150000_create_llm_usage_events.sql:28`）
  - `cost_usd NUMERIC(12, 6)`（`migrations/20260930_150000_create_llm_usage_events.sql:39`）
- データ量: 本番 1547 行、最古 `occurred_at = 2026-09-27 14:12Z`（カードの Facts セクションに記載、設計担当の本番調査済み）。
- 読み取り API: `GET /api/v1/tcg/analysis-dashboard/llm-usage`（`backend/app/routers/tcg_analysis_dashboard.py:680-691`）。`days` クエリで期間指定、`public.llm_usage_events` を `COUNT`/`SUM` で集計し `LlmUsageResponse` を返す（`cost_usd` は USD のまま、JPY 換算は未実装）。

## 4. フロントエンドの現状の USD→JPY 換算

- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:394`: `api.get<FxRate>("/fx-rates/USD")` を呼び、失敗・未取得時は `null`（USD 表示へフォールバック）。
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:311`: `toJpy(usd, rateJpy)` — 変換ロジックを1箇所に集約（コメントに明記）。
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:423,427,433`: `costRate`（`fxRate.rate_jpy`、単一の「現在値」）を全コスト表示箇所（テーブル・チャート両方）に適用している。過去の呼び出しも「現在のレート」で換算される設計になっており、レートが変動した場合に過去分の表示が不正確になる（本カードの課題）。

## 5. migrations 登録・CI 検証の仕組み

- 新規マイグレーションは `scripts/run_all_migrations.sh` 末尾に `run_sql migrations/<file>.sql` を追記して登録する（SSoT、ファイル先頭コメント `scripts/run_all_migrations.sh:14`）。
- CI: `.github/workflows/migration-test.yml` が `migrations/**` 変更時に PostgreSQL サービスコンテナ（`postgres:16`、ユーザー `jarvis`/DB `jarvis_db`）を起動し、`scripts/run_all_migrations.sh` 相当の実行で全マイグレーションを適用 → 同じ内容をもう一度実行して冪等性を検証する（`.github/workflows/migration-test.yml` 冒頭コメント・`migration-test-run` job）。
- 静的なスキーマベースラインファイル（`app_fx_rates` を列挙するような固定リスト）は見つからなかった。`grep -rl "app_fx_rates"` の一致先は `migrations/20260628_170000_add_app_fx_rates.sql`、`backend/app/celery_app.py`、`backend/app/routers/fx_rate_admin.py`、`backend/app/tasks/fx_rate_updater.py`、`backend/tests/test_fx_rate_admin_router.py` のみで、CI 側に別途テーブル名を列挙する箇所はない。→ 本PRでは CI 側の追加登録は不要（新テーブルは `migrations/**` 経由で自動的に検証対象になる）。

## 6. ローカル検証の制約（事実）

- ローカル Docker に `salesanchor-postgres-1`（postgres:16、DB `salesanchor`、ユーザー `myapp_user`）が稼働中だが、`migrations/**` は未適用（`public` スキーマのテーブル数 0）。
- `docker exec -i salesanchor-postgres-1 psql ... < <file>` でマイグレーションを投入しようとしたところ、ローカルの PreToolUse フック（リポジトリ外 ~/.claude/scripts/agent-danger-hook.sh の `psql-write-guard`）が `docker+psql < file` パターンを検知し **BLOCKED**（本番/ローカル問わず docker 経由の psql 書き込みを一律で止める設計）。詳細は design.md §4 参照。
- 本PRのSQL構文・冪等性の正式な検証は `.github/workflows/migration-test.yml`（PR作成後にCIで自動実行）に委ねる。

## 7. PR-B 実装時の追加確認事実

- `backend/app/routers/fx_rate_admin.py` `refresh_fx_rate`（旧行 83-131）は、require_super_admin dependency 以外に operator コンテキスト（`SET app.is_operator = 'true'`）を設定するコードを含んでいなかった（grep `is_operator` で `backend/app/routers/fx_rate_admin.py` に一致なし）。一方 `backend/app/tasks/fx_rate_updater.py:66` は Celery タスク内で明示的に `session.execute(text("SET app.is_operator = 'true'"))` を実行している。**修正済み（2026-10-03 設計判断）**: `app_fx_rate_history` は FORCE RLS で書き込みポリシーが `app.is_operator='true'` を要求するため、`refresh_fx_rate` に `backend/app/auth/dependencies.py:420-451` の `set_operator_context`/`reset_operator_context` を追加した（INSERT の前に set、`finally` で reset。既存の呼び出し元パターン `docs/handoff/products-rls-stage1/design.md:41` と同形）。この2関数の現存する実際の呼び出し元は本PR時点で `backend/tests/test_rls_translation_glossary.py` のコメントのみで、過去に呼んでいた super_admin_inbound.py・parse_review.py（いずれも現存しない）はコミット d010d6700（ダミー機能削除）で消滅済み（git grep で確認）。**未確認**: 本番ログ（保持期間内）に手動更新エンドポイント呼び出しの実績が見当たらず、修正前の状態で実際に RLS 拒否が起きていたか（あるいは接続ロールが BYPASSRLS 等で素通りしていたか）は確認できていない。
- `backend/tests/test_fx_rate_admin_router.py` は実DB不要（`AsyncMock`／`MagicMock` でモック）。`backend/tests/test_tcg_analysis_dashboard_llm_usage.py` も同様（`_mock_db_with_sequenced_results` で `db.execute()` の呼び出し順に対応する結果を返す）。CI の `.github/workflows/migration-test.yml` が定義する固定スキーマ（`public.llm_usage_events` 等、行847-871）に `app_fx_rates` / `app_fx_rate_history` は含まれていない。既存の `app_fx_rates` 用テストも実DB不要のため、本PRでは CI 側の固定スキーマ追加は不要と判断した（既存の `app_fx_rates` 用テストと同じ扱い）。
- `.github/workflows/migration-guard.yml:224` の `PUBLIC_TABLES` 許可リスト（FK `REFERENCES public.X` 検証用）には `app_fx_rates` も `app_fx_rate_history` も含まれていない。本PR・PR-A いずれも `REFERENCES public.app_fx_rate_history` を書いていないため、このチェックへの抵触はない（本PRでは当該リストを変更しない）。
