# design: LLM使用量台帳ダッシュボード「Health」チャート追加（リクエスト数・成功率・エラー種別・モデル別推移）

- 起票日: 2026-10-01
- 対象: PR-D（PO承認済み・2026-10-01）
- recon: [docs/handoff/llm-usage-health-charts/recon.md](./recon.md)
- 関連 ADR: [ADR-1004](../../adr/ADR-1004-llm-usage-ledger.md)（LLM使用量台帳・本便のSSOT）、[ADR-027](../../adr/ADR-027-ui-internationalization.md)（i18n強制）、[ADR-067](../../adr/ADR-067-design-token-enforcement.md)（デザイントークン強制）、[ADR-144](../../adr/ADR-144-ui-component-governance.md)（UI共通部品ガバナンス）

## 背景・動機

PO が Google AI Studio の使用状況ページ（スクリーンショット提示・2026-10-01）を見せ、同様の「健全性」ビューを Sales Anchor の LLM 使用量タブにも追加したいと依頼。具体的には (1) 日次リクエスト数＋成功率、(2) 日次エラー数（種類別）、(3) モデル別の入力/出力トークン・リクエスト数の日次推移、の3系統。既存タブはコスト・トークンの集計（テーブル・使いみち別グラフ）のみで、「失敗」側の可視化が無かった。

## pre-check 結果（STOP 条件の確認）

recon.md「2. 本番事実」の通り、本番相当の `extraction_attempts` 直近12時間の `phase` 内訳は `completed` 14 / `failed` 0（shadow `completed` 207）。コード上で使われている `phase` リテラルも `'completed'` / `'failed'` のみと一致した（`backend/app/routers/tcg_analysis_dashboard.py` L470, L872-875 他）。**premise 成立のため STOP せず実装を続行した。**

## 設計方針

### daily_requests（recon.md §3 バックエンド節 L451-479 のパターンを踏襲）

- 母集団: `{_TCG_SCHEMA}.extraction_attempts`（`_TCG_SCHEMA = "public"`, L365）。
- 時間窓: `started_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW()`（cost-summary の `>= NOW() - INTERVAL ...` より範囲を明示する書き方に統一。意味は同じ）。
- バケット: 既存 `daily`（llm_usage_events 側, L718-730）と同じ `DATE_TRUNC('day', started_at AT TIME ZONE 'Asia/Tokyo')` 表現に合わせた（cost-summary の `DATE()` ではなく、本タブの「トレンド」系に合わせる）。
- `success_rate = completed / NULLIF(completed+failed, 0)`: Python 側で `None`（completed+failed=0 のとき）。**in-flight フェーズ（pending/running 等）は分母から除外**する（design.md 本節で明記。Google AI Studio の「成功率」も完了したリクエストのみを母数にする考え方に合わせた、数値の主張はしない）。

### daily_errors

- 同じ母集団・時間窓・バケット、`WHERE phase = 'failed'` のみに絞り `error_code`（NULL は文字列 `'UNKNOWN'` に丸める）でグループ化。recon.md で確認した通り `error_code` カラムは既存の抽出エラー一覧エンドポイント（L825-926）が既に参照しており、NULLケースの既存フォールバック（L926 `row.error_code or row.error_message`）があることから NULL は起こりうる前提で `COALESCE(error_code, 'UNKNOWN')` を採用した。

### daily_by_model

- 母集団: `public.llm_usage_events`（ADR-1004 の SSOT）。既存 `_LLM_USAGE_WHERE`（L627）・既存 `daily`（L718-730）と同じ JST バケットを共用。
- `output_tokens = SUM(COALESCE(candidates_tokens,0) + COALESCE(thoughts_tokens,0))` だが、グループ内の全行で両方 NULL のときのみ結果も NULL（`_COMPUTED_TOTAL_TOKENS_EXPR`, L629-643 と同じ CASE 式パターンを再利用し、推測で0に丸めない）。
- `prompt_tokens` は単純な `SUM(prompt_tokens)`（NULL行はSUMが無視する既存仕様に準拠）。

## バックエンド変更点（`backend/app/routers/tcg_analysis_dashboard.py`）

- 新規 Pydantic モデル: `LlmUsageDailyRequestsItem`（date, attempts, completed, failed, success_rate: float|None）、`LlmUsageDailyErrorItem`（date, error_code, count）、`LlmUsageDailyByModelItem`（date, model, calls, prompt_tokens: int|None, output_tokens: int|None, cost_usd: float|None）。
- `LlmUsageResponse` に `daily_requests` / `daily_errors` / `daily_by_model` を追加（既存6フィールドは変更なし＝後方互換）。
- `monthly_by_purpose_rows` のクエリ直後・`return LlmUsageResponse(` の直前に3クエリを追加（計9クエリ）。

### テストの調整（`backend/tests/test_tcg_analysis_dashboard_llm_usage.py`）

- recon.md で確認した通り、既存の「6クエリすべてが llm_usage_events のみ参照」アサーション（旧 L142-146）は9クエリ化すると成立しなくなる。**最初の6クエリ（既存コスト系集計）にのみ**このアサーションを残し（`db._executed_sql[:6]`）、追加した7〜8番目（daily_requests/daily_errors、`extraction_attempts` 参照が設計通り）と9番目（daily_by_model、`llm_usage_events` 参照）を別途個別アサーションで検証する形に変更した。
- 新規テスト3本を追加: `test_daily_requests_success_rate_null_when_no_terminal_attempts`（completed=failed=0 のとき success_rate が None のまま＝0除算を推測しない）、`test_daily_errors_maps_null_error_code_to_unknown`、`test_daily_by_model_output_tokens_null_when_all_null_in_group`（candidates/thoughts が全行NULLのグループは output_tokens も None）。
- 既存3テスト（`test_llm_usage_reads_only_ledger_and_propagates_null` 等）は `_mock_db_with_sequenced_results` の呼び出しに3件分のモック結果を追加し、新規フィールドのアサーションを追記。

## フロントエンド変更点（`LlmUsageSection.tsx` のみ、`AnalysisDashboardPanel.tsx` は変更なし）

- recharts import に `ComposedChart` / `Line` / `LineChart` を追加。
- 型定義に `LlmUsageDailyRequestsItem` / `LlmUsageDailyErrorItem` / `LlmUsageDailyByModelItem` を追加し `LlmUsageResponse` を拡張。
- ヘルパー追加: `pivotErrorsByDate()`（date × error_code の横持ち、既存 `pivotByPurpose` と同じパターン）、`uniqueInOrder()`、`pivotByModel()`（date × model の横持ち、値が `null` の場合はキー自体を書き込まず recharts の `connectNulls={false}` でギャップとして表現）。
- JSX: タブ先頭（既存 note/mismatch note の直後、段1メトリクスカードの直前）に新ブロックを2つ追加。
  1. 「概要（LINE抽出）」タイトル＋説明ノート＋ `.analysis-dashboard-grid`（既存クラス再利用、新規pxなし）で横並びの2カード:
     - 「リクエスト数と成功率」: `ComposedChart`（`Bar dataKey="attempts"` 左軸・`var(--chart-series-1)`、`Line dataKey=(row)=>row.success_rate*100` 右軸 0–100%・`var(--color-success)`、`connectNulls={false}`）。Tooltip は成功率系列のときだけ `formatSuccessRatePercent()` で小数1桁%表示。
     - 「エラー数（種類別）」: 積み上げ `BarChart`（`error_code` ごとに `stackId="errors"`、色は既存 `PURPOSE_CHART_COLOR_VARS` を巡回。凡例は `error_code` の生値をそのまま表示 — コードであり文章ではないため t() 非対象、design.md に明記）。データ無しは既存 `noData` 文言。
  2. 「モデル別」タイトル＋ `.analysis-dashboard-grid` で3枚の `LineChart`（入力トークン／出力トークン／リクエスト数、モデルごとに1本の線、色は `PURPOSE_CHART_COLOR_VARS` をモデル順インデックスで巡回、`connectNulls={false}` でギャップ表現）。
- 新規 hex/rgb・新規インラインpx・生 select/input は追加していない（`.analysis-dashboard-grid` / `.analysis-dashboard-chart-card` / `.analysis-dashboard-chart` / `.analysis-dashboard-section-title` / `.analysis-dashboard-empty` を再利用、CSSファイルは無変更）。

### i18n（`frontend/src/locales/ja.json` / `en.json`、同一キー構造）

`analysisRules.dashboard.usage.health.*` を新設: `title`（概要（LINE抽出）/ Overview (LINE Extraction)）、`note`（成功率の定義・翻訳が含まれない理由）、`requestsChartTitle`、`errorsChartTitle`、`attemptsLabel`、`successRateLabel`、`modelTrendTitle`、`inputTokensChartTitle`、`outputTokensChartTitle`、`requestsByModelChartTitle`。既存 `byModelTitle`（モデル別テーブルの見出し）とは別キーとし、文言「モデル別」が2箇所（テーブル見出しと新チャート見出し）に出る設計はPO依頼どおり（Google AI Studio 参考画面も同様の重複見出し構成）。

### フロントエンドテスト（`LlmUsageSection.test.tsx`）

- モックレスポンスに `daily_requests` / `daily_errors` / `daily_by_model` を追加。
- 新規4テスト: 概要セクションの2チャートタイトル表示、エラー0件時の空状態表示、モデル別3チャートのタイトル・モデル名表示、成功率ノート文言の表示。
- 既存テストと同じ制約（recon.md「フロントエンド」節）で、recharts の `ResponsiveContainer` は jsdom でサイズ0のため Legend の実レンダリング内容までは検証せず、チャート見出し・空状態・データ連動テキスト（モデル名等）で確認する方針を踏襲。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| ①リクエスト数＋成功率チャートが表示され、success_rate は completed/(completed+failed) で in-flight を含まない | `backend/tests/test_tcg_analysis_dashboard_llm_usage.py::test_llm_usage_reads_only_ledger_and_propagates_null`（数値アサーション）、`test_daily_requests_success_rate_null_when_no_terminal_attempts`（0除算せずNone）。frontend `"renders the requests & success rate chart and the errors-by-type chart"`。 |
| ②エラー種類別の日次スタック棒グラフが表示され、error_code の NULL は UNKNOWN に丸まる | `test_daily_errors_maps_null_error_code_to_unknown`、frontend `"shows the empty state for the errors chart when there are no errors"`。 |
| ③モデル別の入力/出力トークン・リクエスト数の日次推移が表示され、両方NULLのグループはoutput_tokensもNULLのまま | `test_daily_by_model_output_tokens_null_when_all_null_in_group`、frontend `"renders the per-model trend charts..."`。 |
| ④既存6フィールド・既存3チャート・既存3テーブルは無変更（後方互換） | 既存バックエンドテスト3本（`test_llm_usage_reads_only_ledger_and_propagates_null` 等）が新規フィールド追加後も通過。`AnalysisDashboardPanel.tsx` は diff なし（`git diff --stat` で確認）。 |
| ⑤新規 hex/rgb・新規インラインpx・生select/input なし（ADR-067/ADR-144） | `npm run check:css-colors` / `check:css-values` / `check:dark-parity` PASS（CSSファイル自体は無変更のため既存チェックと同じ結果）。 |
| ⑥ja/enでi18nキー同一（ADR-027）、UI文字列はすべてt()経由 | `npm run check:i18n-missing-keys` PASS、`grep -n '[ぁ-んァ-ン一-龥]' frontend/src/pages/super-admin/components/LlmUsageSection.tsx` がコメント行以外で0件。 |

## 外部・過去事例の参照と我々への応用

Google AI Studio の使用状況ページ（PO 提示のスクリーンショット、2026-10-01）を見せ方の参考にした — リクエスト数と成功率を重ねたチャート、エラー種類別のスタック棒、モデル別の日次推移という3系統の構成を踏襲。**数値の主張はしない**（Google AI Studio 側の実数値・ベンチマークとの比較は行っていない。あくまで「どう見せるか」の構成のみ参考）。recharts（`^3.8.1`、既存依存）の `ComposedChart`（Bar+Line混在）は本プロジェクトで初採用だが、新規パッケージ追加は無い。

## 維持の仕組み

- 守り手: バックエンドの `daily_requests` / `daily_errors` / `daily_by_model` クエリは既存の `_COMPUTED_TOTAL_TOKENS_EXPR` と同じ「全行NULLのときだけNULLを伝播」パターンをコメント付きで再利用しているため、将来 SDK やフェーズ種別が増えても同じ規約で拡張できる。
- `success_rate` の定義（in-flight除外）は Pydantic モデルのフィールドコメントと本 design.md に明記。将来 `phase` に新しい終端値が追加された場合、`completed`/`failed` のリテラル2値決め打ちが古くなる可能性があるため、`backend/app/services/tcg_extraction_record_svc.py` の phase 定義が変わった際はこのクエリも合わせて見直す必要がある（recon.md §2 のpre-check手順を再実行すること）。
- エラー種類別チャートの凡例は `error_code` の生値（コード）をそのまま表示する設計とした。将来 error_code の命名体系が変わった場合、UI側の変更は不要（t()を介さないため）。
