# recon: LLM使用量台帳（llm_usage_events）ダッシュボードの拡張（使いみち別グラフ・合計列修正・呼び出し回数ラベル修正）

- 起票日: 2026-10-01
- 対象ブランチ: release/llm-usage-charts（origin/main 起点）
- 関連 ADR: ADR-1004（LLM使用量台帳）、ADR-027（i18n強制）、ADR-067（デザイントークン強制）、ADR-144（UI共通部品ガバナンス）
- 前便: PR-B #3892（マージ済み）が GET /tcg/analysis-dashboard/llm-usage と frontend/src/pages/super-admin/components/LlmUsageSection.tsx（タブ "usage"）を追加

## 1. 既存 ADR 検索（着手前）

`git grep -i "llm_usage\|llm-usage" docs/adr/` の結果:
- `docs/adr/ADR-1004-llm-usage-ledger.md` — public.llm_usage_events を SSOT とする台帳設計の ADR。本便は同 ADR のデータを表示するダッシュボードの改善であり、台帳スキーマ自体は変更しない。
- `docs/adr/FEATURE-INDEX.md` に llm-usage 関連の追加エントリなし（確認済み、該当なし）。

## 2. 本番事実（PO 提供・2026-10-01 時点）

- public.llm_usage_events は 290 件がバックフィル行で total_tokens が NULL、3 件がライブ行で total_tokens が設定済み。
- 現行 UI（PR-B #3892 時点）の「合計」列は total_tokens の SUM であり、NULL の 290 行を無視して 3 行だけの合計 274,506 を表示していた（バックフィル分を欠落させた誤解を招く数値）。
- 「呼び出し回数」は llm_usage_events に記録された行数のみをカウントしている。応答が返らず失敗した呼び出し（台帳に記録されない）はカウントに含まれない。

## 3. 現状コード（origin/main 時点、フルパス:行番号）

### バックエンド

`backend/app/routers/tcg_analysis_dashboard.py`:
- L562-604（変更前）: `LlmUsageTotal` / `LlmUsageByPurposeItem` / `LlmUsageByModelItem` / `LlmUsageDailyItem` / `LlmUsageResponse` の Pydantic スキーマ定義。`computed_total_tokens` 相当のフィールドは存在しなかった。
- L607: `_LLM_USAGE_WHERE = "occurred_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW()"`（JST変換なしの絶対時刻窓。既存の日別バケット表現は別途 `TO_CHAR(DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo'), 'YYYY-MM-DD')` を使用、L668-680）。
- L610-726: `get_llm_usage()` エンドポイント本体。4クエリ（total / by_purpose / by_model / daily）を `db.execute` で順に実行し `LlmUsageResponse` を構築。`purpose` 別・`model` 別・`daily`（JST日次）の集計はあるが、`使いみち別の日次・月次` のクロス集計は存在しなかった。
- L620-625 のコメント: SDK が値を返さない列は SUM() が NULL を返す仕様（COALESCE で 0 に丸めない＝推測しない）という既存方針が明記されている。今回追加する `computed_total_tokens` もこの方針を踏襲する。

`backend/tests/test_tcg_analysis_dashboard_llm_usage.py`:
- L1-11: DB を AsyncMock で模擬し `get_llm_usage()` を直接呼ぶ方式（`test_tcg_analysis_dashboard_cost_summary.py` と同じ）。
- L26-45: `_mock_db_with_sequenced_results()` ヘルパーは `db.execute()` 呼び出し順に mappings 結果を返す。クエリ数が変わると `mapping_results` の要素数・`db._executed_sql` の件数アサーションを合わせる必要がある（旧: 4クエリ固定、L105 で `assert len(db._executed_sql) == 4`）。

### フロントエンド

`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（origin/main 時点）:
- L21-64: 型定義（`LlmUsageTotal` 等）。`computed_total_tokens` / `total_mismatch_calls` / `daily_by_purpose` / `monthly_by_purpose` は未定義。
- L70-77: `KNOWN_PURPOSES` 定数（6種: line_extraction, line_extraction_shadow, inventory_parse_fallback, translation_inbound, translation_inbound_escalation, translation_outbound）。
- L161-215: `byPurposeColumns` の `colTotal`（旧 L204-208）は `row.total_tokens` をそのまま `formatNumber()` で表示 — バックフィル行が NULL のため合計が過小表示される根本原因。
- L274-358: レンダリング本体。段1（4枚のメトリクスカード：費用合計・呼び出し回数・入力トークン・出力トークン）→ 段2（使いみち別テーブル）→ 段3（日別テーブル）→ 段4（モデル別テーブル）の順で、グラフは一切なかった（テーブルのみ）。
- インポートは `recharts` を一切使っていなかった（Card / DataTable のみ）。

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`（origin/main 時点、チャートの金型確認用）:
- L20-46: `recharts` から `ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend` を import。`../../../components/` 配下に Chart 名を含む専用コンポーネント（金型）は存在しない（`grep -rl "Chart" frontend/src/components --include="*.tsx"` は 0 件）。
- L959-983 / L1166-1190 / L1590-1622: 3箇所で `<ResponsiveContainer><LineChart>...` パターンを直書きしている。色は `stroke="var(--color-success)"` 等、CSS変数を直接指定（新規 hex なし）。
- 結論: 「チャート専用の金型コンポーネント」は存在せず、AnalysisDashboardPanel.tsx が recharts を直接使う既存パターンのみが「金型」に相当する。本便は同じ import パターン・`ResponsiveContainer` の使い方を踏襲し、`BarChart` / `Bar`（stackId 指定で積み上げ）を追加で import する（recharts 自体には最初から Bar/BarChart が含まれる。`frontend/package.json:87` に `"recharts": "^3.8.1"`）。

### カラートークン（積み上げ棒グラフの使いみち別色の出どころ）

`frontend/src/tokens.css`:
- L396-402（ライトモード）/ L566-572（`:root.force-dark`）: `--cal-personal` `--cal-meeting` `--cal-purchase` `--cal-shipping` `--cal-billing` `--cal-release` `--cal-holiday` の7色がカレンダーカテゴリ用に light/dark 両方定義済み。
- `--color-success` / `--color-error` / `--color-warning-*` は L542-548（ライト）/ L578-584（ダーク）に定義されているが、状態色（成功/失敗/警告）用の2〜3色のみで、6種の使いみちを塗り分けるカテゴリカルパレットとしては不足（AnalysisDashboardPanel.tsx の既存 LineChart 3本は success/error/warning の3色のみを使用）。
- 結論: 新規 hex を追加せず、`--cal-*` 7色（既存トークン値）を使いみち別カラーとして転用する（6種の purpose に対して7色で足りる）。

## 4. i18n 既存キー（origin/main 時点）

`frontend/src/locales/ja.json` L4479-4508 / `en.json` L4479-4508:
- `analysisRules.dashboard.usage.*` に note / notReported / metricCost / metricCalls / metricInput / metricOutput / byPurposeTitle / dailyTitle / byModelTitle / colPurpose / colCalls / colInput / colCached / colOutput / colThoughts / colTool / colTotal / colCost / colDate / colModel / purpose.* が定義済み。ja/en でキー完全一致（`npm run check:i18n-missing-keys` は既存時点で PASS）。
- `metricCalls`（ja: "呼び出し回数" / en: "Call Count"）と `colCalls`（ja: "回数" / en: "Calls"）が「応答が返った回数」であることを明示していなかった。

## 5. 本便で変更した箇所（フルパス:行番号は origin/main 基準の追加位置）

- `backend/app/routers/tcg_analysis_dashboard.py`: `LlmUsageTotal`/`LlmUsageByPurposeItem` に `computed_total_tokens`/`total_mismatch_calls` を追加、`LlmUsageDailyByPurposeItem`/`LlmUsageMonthlyByPurposeItem` を新設、`LlmUsageResponse` に `daily_by_purpose`/`monthly_by_purpose` を追加。`get_llm_usage()` に2クエリ追加（計6クエリ）。
- `backend/tests/test_tcg_analysis_dashboard_llm_usage.py`: 新フィールド・新クエリ数（6）・mismatch カウント・全NULL時のcomputed_total_tokens=NULLを検証するテストを追加。
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`: recharts BarChart による日次・月次（使いみち別）積み上げ棒グラフを追加、「合計」列を computed_total_tokens に変更、mismatch 件数の注記、呼び出し回数ラベルの変更。
- `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`: 上記の振る舞いを検証するテストを追加。
- `frontend/src/locales/ja.json` / `en.json`: `analysisRules.dashboard.usage.*` に `dailyByPurposeChartTitle` / `monthlyByPurposeChartTitle` / `totalMismatchNote` を追加、`note` / `metricCalls` / `colCalls` の文言を変更。ja/en 同一キー（`npm run check:i18n-missing-keys` で確認）。
