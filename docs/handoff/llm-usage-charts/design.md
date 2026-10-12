# design: LLM使用量台帳ダッシュボードの拡張（使いみち別グラフ・合計列修正・呼び出し回数ラベル修正）

- 起票日: 2026-10-01
- 対象: PR-C（PO承認済み・2026-10-01）
- recon: [docs/handoff/llm-usage-charts/recon.md](./recon.md)
- 関連 ADR: [ADR-1004](../../adr/ADR-1004-llm-usage-ledger.md)（LLM使用量台帳・本便のSSOT）、[ADR-027](../../adr/ADR-027-ui-internationalization.md)（i18n強制）、[ADR-067](../../adr/ADR-067-design-token-enforcement.md)（デザイントークン強制）、[ADR-144](../../adr/ADR-144-ui-component-governance.md)（UI共通部品ガバナンス）

## 背景・動機（recon 3節・本番事実）

recon.md「2. 本番事実」の通り、`public.llm_usage_events` は 290件のバックフィル行で `total_tokens` が NULL、3件のライブ行のみ値を持つ。既存 UI（PR-B #3892）の「合計」列は `total_tokens` の SUM を素直に表示していたため、290件を無視した 274,506 という数値になり PO に誤解を与えていた（recon.md L1〜13相当）。また「呼び出し回数」は台帳に記録された行のみを数えており、応答が返らず失敗した呼び出しは含まれないことが UI 上に明記されていなかった。本便はこの2点の誤解を解消し、併せて使いみち別の費用推移を可視化するグラフを追加する。

## 設計方針（ADR-1004 との整合）

ADR-1004 は `public.llm_usage_events` を LLM使用量の SSOT と定めている。本便は台帳のスキーマ・書き込み経路を一切変更せず、読み出し側（GET /tcg/analysis-dashboard/llm-usage）の集計ロジックのみを拡張する。「推測で0に丸めない」という既存方針（recon.md「バックエンド」L620-625 相当のコメント）を `computed_total_tokens` にも適用する: prompt/candidates/thoughts/tool_use_prompt の4項目が**全行にわたって**すべて NULL のときだけ NULL のままとし、1件でも報告があれば COALESCE(...,0) で合算する。SUM() は NULL を無視する性質を利用し、CASE式で「4項目すべて NULL の行」だけを NULL として渡すことで、この挙動を自然に実現する（SQLは `backend/app/routers/tcg_analysis_dashboard.py` の `_COMPUTED_TOTAL_TOKENS_EXPR` / `_TOTAL_MISMATCH_CALLS_EXPR` 参照）。

## チャート実装方針（pre-check 結果）

- (a) `frontend/src/components` 配下に Chart 名を含む専用金型コンポーネントは存在しない（recon.md「フロントエンド」節、`grep -rl "Chart" frontend/src/components --include="*.tsx"` が 0 件）。
- (b) そのため `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` が既に使っている recharts 直書きパターン（`ResponsiveContainer` + `CartesianGrid` + `XAxis`/`YAxis` + `Tooltip` + `Legend`、L959-983 等）を踏襲し、積み上げ棒グラフ用に `BarChart`/`Bar`（`stackId` 指定）を同じ import スタイルで追加した。recharts は `frontend/package.json:87` で `^3.8.1` として既存依存済み（新規パッケージ追加なし）。
- 色: 新規 hex は追加せず、`frontend/src/tokens.css` L396-402（ライト）/ L566-572（ダーク）に light/dark 両方定義済みの `--cal-personal`〜`--cal-holiday`（7色、カレンダーカテゴリ用の既存トークン）を使いみち別カラーとして転用した（6 purpose に対し7色で充足）。`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` の既存3チャートが使う `--color-success`/`--color-error`/`--color-warning-*` は状態色2〜3色のみで、カテゴリカルな塗り分けには不足するため対象外とした。
- 金型もトークンベースの色源も両方存在したため、「STOP して報告」の条件（金型なし かつ 色源なし）には該当しない。

### レビュー指摘への対応: ドメイン跨ぎのトークン直接参照をやめる

Designer レビュー（Opus）で、上記の `--cal-*`（カレンダードメイン用トークン）を LLM 使用量
チャートから直接参照すると、将来カレンダー側の配色を変更したときにこのグラフが無言で
巻き込まれて再着色される問題を指摘された。`docs/adr/ADR-067-design-token-enforcement.md`
「新規トークン追加手順」（1. `src/tokens.css` の `:root {}` に追加 → 2. 色トークンは
`:root` と `:root.force-dark` 両方に追加 → 3. `npm run check:dark-parity` で確認 →
4. ADR のコンポーネントトークン表を更新）に従い、`frontend/src/tokens.css` に
`--chart-series-1`〜`--chart-series-7` を新設した。各トークンは既存の `--cal-*` の値を
`var(--cal-*)` でエイリアスするのみで、新規 hex/rgb は追加していない（light/dark 両方に
同じ形で追加、`npm run check:dark-parity` PASS 済み）。`frontend/src/pages/super-admin/components/LlmUsageSection.tsx` は
`var(--chart-series-N)` を参照するよう変更した。`docs/CC_UI_GOVERNANCE.md` は UI
「部品」（Select/TextField 等の金型）の新設・流用ルールであり、トークンの新設手順は
規定していない（両ドキュメントを確認済み）。PO 事前承認を必須とする記述はどちらにも
なかったため、STOP せずに実装した。

## 変更点サマリ

### バックエンド（`backend/app/routers/tcg_analysis_dashboard.py`）

- `LlmUsageTotal` / `LlmUsageByPurposeItem` に `computed_total_tokens: int | None` と `total_mismatch_calls: int` を追加。
- `LlmUsageDailyByPurposeItem`（date, purpose, cost_usd, calls）と `LlmUsageMonthlyByPurposeItem`（month, purpose, calls, cost_usd）を新設し、`LlmUsageResponse` に `daily_by_purpose` / `monthly_by_purpose` を追加（既存フィールドは変更なし＝後方互換）。
- `daily_by_purpose` は既存 `daily` と同じ JST `DATE_TRUNC('day', ...)` 表現、`monthly_by_purpose` は `TO_CHAR(DATE_TRUNC('month', occurred_at AT TIME ZONE 'Asia/Tokyo'), 'YYYY-MM')`。WHERE 条件（`days` パラメータによる期間窓）は既存 `_LLM_USAGE_WHERE` を共用。
- クエリ数が4→6に増加（total / by_purpose / by_model / daily / daily_by_purpose / monthly_by_purpose）。

### フロントエンド（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`）

- 使いみち別テーブルの「合計」列を `row.total_tokens` → `row.computed_total_tokens` に変更。
- `total.total_mismatch_calls > 0` のとき、既存の note 直下に `totalMismatchNote` を1行追加表示。
- 「呼び出し回数」系ラベル（メトリクスカード `metricCalls` ＋ 3テーブル共通の `colCalls`）を ja「応答が返った回数」/ en "Calls with response" に変更し、note 末尾に「応答が返らず失敗した呼び出しは含みません。」を追記。
- 日次・月次の使いみち別積み上げ棒グラフ（Card 2枚）をテーブル群の上に追加。データが空のときはテーブルと同じ `noData` 文言を表示。
- 積み上げ棒グラフの色は `frontend/src/tokens.css` に新設した `--chart-series-1`〜`--chart-series-7`（`--cal-*` のエイリアス）を参照（ドメイン跨ぎの直接参照を回避）。
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` は変更していない（import元の `LlmUsageSection` のシグネチャ・呼び出し方に変更がないため）。

### i18n（`frontend/src/locales/ja.json` / `frontend/src/locales/en.json`）

- `analysisRules.dashboard.usage.dailyByPurposeChartTitle` / `monthlyByPurposeChartTitle` / `totalMismatchNote` を新設。
- `note` / `metricCalls` / `colCalls` の文言を変更。ja/en 同一キー（`npm run check:i18n-missing-keys` で確認済み）。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| ①日次・月次の使いみち別積み上げ棒グラフが表示される | `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx` の `"renders the daily and monthly by-purpose charts with legend entries"` / `"shows the empty state for the by-purpose charts when there is no data"`。実機確認は本番デプロイ後にダッシュボードのスクリーンショットで目視。 |
| ②使いみち別テーブルの「合計」列が computed_total_tokens（バックフィル分込みで2667万台になる想定）を表示する | `backend/tests/test_tcg_analysis_dashboard_llm_usage.py::test_llm_usage_reads_only_ledger_and_propagates_null` の `computed_total_tokens` アサーション、および frontend の `"shows computed_total_tokens (not the raw total_tokens) in the colTotal column"`。本番実数値は次回 smoke 確認時に `合計` 列を目視して 274,506（旧誤表示）と異なる値であることを確認する。 |
| ③ total_mismatch_calls > 0 のとき不一致注記が出る（0のときは出ない） | `test_llm_usage_mismatch_calls_counted_when_total_tokens_disagrees`（backend）、`"shows a mismatch note..."` / `"does not show a mismatch note..."`（frontend）。 |
| ④「呼び出し回数」系ラベルが「応答が返った回数」/ "Calls with response" に変わっている | frontend テスト `"uses the 'Calls with response' label instead of the old 'Call Count' label"` / `"mentions that failed calls without a response are excluded"`。 |
| ⑤ ja/en で i18n キーが同一（ADR-027） | `npm run check:i18n-missing-keys` PASS（実行済み、後述の生出力参照）。 |
| ⑥ 新規 hex 直値なし・ドメイン跨ぎのトークン直接参照なし（ADR-067） | `npm run check:css-colors` / `npm run check:dark-parity` PASS（実行済み）。色は `frontend/src/tokens.css` に新設した `--chart-series-1`〜`--chart-series-7`（`--cal-*` のエイリアス、light/dark 両方）を `var(--chart-series-N)` 形式で参照。`--cal-*` を他ドメインから直接参照しない。 |

## 外部・過去事例の参照と我々への応用

該当なし。Sales Anchor 社内ダッシュボードの既存パターン（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` の recharts 直書き・DataTable 金型）の拡張であり、社外事例やOSS実装を参照する必要がある新規技術要素（新ライブラリ・新アーキテクチャパターン）を含まないため、GitHub/npm調査は実施しなかった。recharts 自体は既存依存（`^3.8.1`）であり API 仕様（`BarChart`/`Bar`/`stackId`）はプロジェクト内の既存3チャート実装から確認した。

## 維持の仕組み

- `computed_total_tokens` のロジックは SQL の CASE 式コメントで「なぜ NULL のままにするか」を明記（`_COMPUTED_TOTAL_TOKENS_EXPR` 直上）。将来 SDK が新しいトークン種別を返すようになった場合、この4項目リストの更新漏れに気づけるよう、同コメント内に4項目を明記している。
- 使いみち別カラーは `PURPOSE_CHART_COLOR_VARS`（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`）の配列1箇所に集約。新しい purpose が `KNOWN_PURPOSES` に追加されても、`purposeColor()` が `--cal-*` 7色を巡回するため個別対応は不要（8種目以降は既存6種と色が重複するが、7色中6色使用時点では重複しない）。
- i18n キー・CSS色・CSS値・クラス命名の各チェックスクリプトが CI（`npm run check:all` 相当）に組み込まれており、今後の変更でも自動検出される（`check:i18n-missing-keys` / `check:css-colors` / `check:css-values` / `check:css-class-naming`）。
- 守り手: Hikky-dev（`backend/tests/test_tcg_analysis_dashboard_llm_usage.py` / `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx` のCI通過確認）／ PO しんごさん（GO判断・本番反映確認）。
