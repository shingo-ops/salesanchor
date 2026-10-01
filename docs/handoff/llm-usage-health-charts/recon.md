# recon: LLM 使用量台帳ダッシュボード「Health」チャート追加（Google AI Studio 風の使用状況ビュー）

- 起票日: 2026-10-01
- 対象ブランチ: release/llm-usage-health-charts（origin/main 起点、PR-D・PO承認済み・2026-10-01）
- 関連 ADR: ADR-1004（LLM使用量台帳）、ADR-027（i18n強制）、ADR-067（デザイントークン強制）、ADR-144（UI共通部品ガバナンス）
- 前便: PR-B #3892（GET /tcg/analysis-dashboard/llm-usage と LlmUsageSection.tsx 新設）、PR-C #3895（使いみち別グラフ・computed_total_tokens 修正）が main にマージ済み

## 1. 既存 ADR 検索（着手前）

`git grep -i "llm_usage\|llm-usage\|extraction_attempts" docs/adr/` の結果:
- `docs/adr/ADR-1004-llm-usage-ledger.md` — `public.llm_usage_events` を LLM使用量の SSOT とする ADR。本便は同台帳の読み出し集計（daily_by_model）と、既存の `{_TCG_SCHEMA}.extraction_attempts`（cost-summary で既に参照されている表）の読み出し集計（daily_requests / daily_errors）を追加するのみで、どちらの書き込み経路・スキーマも変更しない。
- `docs/adr/FEATURE-INDEX.md` に llm-usage / extraction-attempts 関連の追加エントリなし（確認済み、該当なし）。

## 2. 本番事実（2026-10-01 00:24Z 読み取り）

PO 指示の pre-check として、本番相当の `extraction_attempts` 直近状況と、コード上の `phase` 値の一致を確認した（想定: `completed` / `failed`。差異があれば STOP の条件）。

- `extraction_attempts` 直近12時間: `completed` 14 件 / `failed` 0 件（shadow 分は別カウントで `completed` 207 件）。
- コード上で使われている `phase` 値は `'completed'` と `'failed'` のみ（下記 L470, L872-875, L889-890, L905-906 で確認）。想定どおり一致 — **premise 成立、STOP 条件に該当しない**。
- `extraction_attempts.error_code` カラムはコード上に存在が確認できた（`backend/app/routers/tcg_analysis_dashboard.py` L881, L888, L926、既存の抽出エラー一覧エンドポイントが参照）。NULL のケースがある前提（`row.error_code or row.error_message` のフォールバックが既にある、L926）。

## 3. 現状コード（origin/main 時点、フルパス:行番号）

### バックエンド

`backend/app/routers/tcg_analysis_dashboard.py`:
- L365: `_TCG_SCHEMA = "public"`（本番は public スキーマ。cost-summary 等がこの定数を使う）。
- L451-554: `get_cost_summary()` — `{_TCG_SCHEMA}.extraction_attempts` を `started_at >= NOW() - INTERVAL '1 day' * :days` で絞り込み `DATE(ea.started_at)` でバケット化するパターン（L466-479）。`daily_requests` / `daily_errors` の母集団・時間窓はこの実装を踏襲した。
- L470: `COUNT(*) FILTER (WHERE ea.phase = 'completed') AS success_calls` — `phase` の既存リテラル値 `'completed'` を確認。
- L562-625: 既存 Pydantic スキーマ（`LlmUsageTotal` 〜 `LlmUsageResponse`）。`daily_requests` / `daily_errors` / `daily_by_model` は未定義だった。
- L627: `_LLM_USAGE_WHERE = "occurred_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW()"`（`public.llm_usage_events` 用の絶対時刻窓）。`daily_by_model` はこの WHERE 句と、既存 `daily`（L718-730）と同じ JST `DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo')` バケットを共用する。
- L629-643: `_COMPUTED_TOTAL_TOKENS_EXPR` — candidates/thoughts などが全行 NULL のグループは SUM 結果も NULL のままにする既存パターン。`daily_by_model.output_tokens` のNULL伝播もこのパターンを踏襲した。
- L661-730: `get_llm_usage()` 本体。クエリは6本（total / by_purpose / by_model / daily / daily_by_purpose / monthly_by_purpose）。`daily_requests` / `daily_errors`（`extraction_attempts` 由来）/ `daily_by_model`（`llm_usage_events` 由来）を追加して9本になる。
- L744-754: `monthly_by_purpose_rows` の直後、`return LlmUsageResponse(`（L756）の直前が新規クエリの挿入位置。
- L825-926: `list_extraction_errors()` — `error_code` カラムの既存利用箇所（上記2節参照）。

`backend/tests/test_tcg_analysis_dashboard_llm_usage.py`:
- L26-45: `_mock_db_with_sequenced_results()` — `db.execute()` 呼び出し順に mappings 結果を返すヘルパー。クエリ数が変わると `mapping_results` の要素数・`db._executed_sql` の件数アサーションを合わせる必要がある（旧: 6クエリ固定、L142 で `assert len(db._executed_sql) == 6` かつ全クエリが `extraction_attempts` を含まないことを検証）。本便で9クエリに増え、うち2本（daily_requests/daily_errors）は意図的に `extraction_attempts` を参照するため、既存の「全クエリで extraction_attempts 不在」アサーションをそのまま流用できない（後述 design.md で対応）。

### フロントエンド

`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（origin/main、500行）:
- L10-20: recharts import（`ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend`）。`ComposedChart` / `Line` / `LineChart` は未import。
- L87-94: `LlmUsageResponse` 型定義。`daily_requests` / `daily_errors` / `daily_by_model` は未定義。
- L109-128: `PURPOSE_CHART_COLOR_VARS`（`--chart-series-1`〜`7`）と `purposeColor()`。新規チャートの色もこの配列を再利用する方針（新規 hex 追加なし）。
- L130-146: `pivotByPurpose()` — purpose列を横持ちに変換する既存ヘルパー。error_code 別・model別の横持ち変換にも同じパターンを適用する。
- L196-215: データ取得（`useEffect` + `api.get`）。
- L348-358: `return` 直下、既存の note / mismatch note の直後が「概要（LINE抽出）」ブロックの挿入位置（タブの先頭）。
- L359-393: 段1（4枚のメトリクスカード）。
- L395-455: 日次・月次の使いみち別積み上げ棒グラフ（`BarChart` + `stackId` パターン。新規2チャートの実装モデル）。
- L457-497: 段2〜4（使いみち別テーブル・日別テーブル・モデル別テーブル）。変更しない。

`frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`（origin/main、168行）: 既存14ケース。recharts の `ResponsiveContainer` は jsdom でサイズ0のため、既存テストも実際には凡例（Legend）のレンダリング内容を厳密に検証しておらず、チャートタイトル文字列や DataTable 側のテキストで代替確認している（L71-168）。新規チャートのテストも同じ制約に従う。

`frontend/src/tokens.css`:
- L408-414（light）/ L587-593（dark）: `--chart-series-1`〜`7`（`--cal-*` のエイリアス）。
- L557-559（light）/ L602-604（dark）: `--color-success`。成功率ラインの色として利用可能（新規 hex 追加不要）。

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css`:
- L295-301: `.analysis-dashboard-chart-card` / `.analysis-dashboard-chart`。
- L318-322: `.analysis-dashboard-grid`（`grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`）— 「横並び（広い画面）」のレイアウトに新規CSSを足さず、このグリッドクラスを再利用する。

`frontend/src/locales/ja.json` / `frontend/src/locales/en.json`: `analysisRules.dashboard.usage.*` 配下に `health.*` の新規キーは未定義。

## 4. 影響範囲

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` は `LlmUsageSection` の props（`days`, `t`）をそのまま渡しているのみで、本便ではシグネチャを変更しないため触らない。
- バックエンドの既存6クエリ・既存フィールドは変更なし（後方互換）。
