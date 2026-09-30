# recon: LLM 使用量ダッシュボードUI（PR-B）

作成日: 2026-10-01
対象ブランチ: `release/llm-usage-ui`（`origin/main` 89c69193c 起点）

## 1. 既存 ADR / 関連仕様

- `docs/adr/ADR-1004-llm-usage-ledger.md` — `public.llm_usage_events` 台帳の新設・書き込み経路・費用式・受入条件の正本。
- `docs/handoff/llm-usage-ledger/design.md`, `docs/handoff/llm-usage-ledger/recon.md` — 台帳PR（#3884）の設計・根拠。
- `docs/adr/ADR-027-ui-internationalization.md` — 全 UI 文字列 `t()` 必須。
- `docs/adr/ADR-067-...`（デザイントークン強制）、`docs/adr/ADR-144-...`（UIガバナンス／金型使用）。
- ADR-INDEX で `llm-usage`/`llm_usage_events` を検索し、上記以外に本タブ表示に関する既存 ADR は無し。

## 2. テーブル定義（migrations/20260930_150000_create_llm_usage_events.sql）

`public.llm_usage_events`:
- `id UUID PK`
- `occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `purpose TEXT NOT NULL` — CHECK IN ('line_extraction','line_extraction_shadow','inventory_parse_fallback','translation_inbound','translation_inbound_escalation','translation_outbound')
- `tenant_id INTEGER`
- `model TEXT NOT NULL`
- `sdk TEXT NOT NULL`
- `prompt_tokens/cached_content_tokens/candidates_tokens/thoughts_tokens/tool_use_prompt_tokens/total_tokens INTEGER`（すべて NULL 許容、推測で埋めない）
- `cost_usd NUMERIC(12,6)`
- `extraction_attempt_id UUID REFERENCES extraction_attempts(id) ON DELETE SET NULL`
- `extraction_shadow_run_id UUID`（FK なし・理由は migration コメント参照）
- `discord_inbound_message_id INTEGER`, `source_ref TEXT`, `backfilled BOOLEAN`

## 3. 既存 router: backend/app/routers/tcg_analysis_dashboard.py（変更前 674 行）

- `GET /tcg/analysis-dashboard/cost-summary`（`backend/app/routers/tcg_analysis_dashboard.py:450-554`）: `require_super_admin` 認可・`llm_usage_events` を `extraction_attempts` に LEFT JOIN して読む唯一の既存エンドポイント。`daily` の日付バケットは `DATE(ea.started_at)`（`backend/app/routers/tcg_analysis_dashboard.py:467`）— タイムゾーン変換なし（セッションTZ依存）。
- 「トレンド」系エンドポイント本体（`get_import_trend`, `get_pipeline_trend`）は `backend/app/services/tcg_analysis_dashboard_svc.py` にあり、日付バケットは `TO_CHAR(DATE_TRUNC('day', created_at AT TIME ZONE 'Asia/Tokyo'), 'MM-DD')`（`backend/app/services/tcg_analysis_dashboard_svc.py:417-425`）— JST 固定。
- **本PRの `daily` バケットは trend 系（JST DATE_TRUNC）に合わせた**（cost-summary の daily ではなく）。理由: cost-summary の `daily` は「コスト集計」の一部であり、`import-trend`/`trend` エンドポイントの方が本タブの「日別トレンド」という性格に近いため。cost-summary の `DATE()` はセッションTZ依存で挙動が不透明という懸念もある。
- `days: int = Query(default=30, ge=1, le=360)` の形は `extraction-product-ranking`（`backend/app/routers/tcg_analysis_dashboard.py:353`）・`import-trend`（`backend/app/routers/tcg_analysis_dashboard.py:221`）と同一パターン。本PRの `llm-usage` エンドポイントも同じ形を踏襲。
- 認可は全エンドポイント共通で `_admin=Depends(require_super_admin)`（例: `backend/app/routers/tcg_analysis_dashboard.py:325`, `:355`, `:458`）。

## 4. 本番データ形状（2026-10-01 時点、PO 提供の事実）

- `public.llm_usage_events` は現在 291 行、すべて `purpose='line_extraction'`・`model='gemini-3.1-flash-lite'`。
- `thoughts_tokens`・`cached_content_tokens`・`tool_use_prompt_tokens`・`tenant_id` は全行 NULL（旧 SDK `google-generativeai` は返さないため。ADR-1004 Consequences 参照）。
- → UI の NULL 表示（「記録なし」）は現時点でほぼ全ての行・列で実際に発生する主要パスであり、null 安全な実装が必須。

## 5. フロントエンド既存構造

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`（変更前 1904 行）
  - `DashboardTab` 型定義: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:52`
  - `tabItems` 配列: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:467-472`
  - `trendDays` state: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:314`。`SelectControl` による期間セレクタは `activeTab` の条件分岐の**外側**（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:497-513`）にあり、全タブ共通で常に表示される。→ 新規セレクタ追加不要、既存 `trendDays` を `LlmUsageSection` に prop で渡すだけで良い。
  - タブごとのレンダリング分岐は `{activeTab === "xxx" && (...)}` パターン（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:516-583`）。
  - `api` クライアント: `frontend/src/lib/api.ts`（`api.get<T>(path)` 形。Firebase ID トークン自動付与・502/503/504 リトライあり）。
  - `Card`（`frontend/src/components/Card.tsx`）: `variant: "container" | "interactive" | "metric"`, `density: "default" | "compact"`。
  - `DataTable`（`frontend/src/components/DataTable.tsx`）: `columns`（`key`/`header`/`width`/`renderCell`）+ `data` + `rowKey` + `density` + `emptyState`。
  - loading/error/empty パターンはタブ関数ごとに `if (loading) return <p className="analysis-dashboard-empty">...`／`if (error || !data) return <p className="analysis-dashboard-error">...` を踏襲（例: `ImportTabContent`, `DistributionTabContent`）。専用 `EmptyState` コンポーネント（`frontend/src/components/EmptyState.tsx`）は本パネル内では未使用のため、既存パターンを踏襲した（EmptyState コンポーネントは使わない）。

## 6. テスト規約

- Backend: `backend/tests/test_tcg_analysis_dashboard_cost_summary.py` — router の関数を直接 `await` 呼び出しし、`db.execute` を `AsyncMock(side_effect=...)` で順序どおりの `mappings()` 結果を返すモックに差し替えるパターン。SQL 文字列に対象テーブル名が含まれるかを `db._executed_sql` で検証。
- Backend: `backend/tests/test_tcg_extraction_record_api.py` — `Query(..., ge=..., le=...)` の範囲外バリデーション（422）は実際に `FastAPI()` + `app.include_router(routes.router)` + `app.dependency_overrides` + `httpx.AsyncClient` で叩く必要がある（関数直接呼び出しでは Pydantic/FastAPI の Query バリデーションを経由しないため 422 を再現できない）。
- Frontend: `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.test.tsx` — `vi.mock("../../../lib/api", ...)` で `api.get`/`api.post` をモックし、`i18n.changeLanguage("en")` を `beforeEach` で呼んで英語キーで assert するパターン。

## 7. 変更ファイル一覧（本PR、`git diff origin/main...HEAD --numstat`）

- 変更: `backend/app/routers/tcg_analysis_dashboard.py`（+172, 追記のみ）
- 変更: `frontend/src/locales/en.json`（+31）
- 変更: `frontend/src/locales/ja.json`（+31）
- 変更: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css`（+6）
- 変更: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`（+6, -1）
- 新規: `backend/tests/test_tcg_analysis_dashboard_llm_usage.py`
- 新規: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`
- 新規: `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`
- 削除ファイル: なし
