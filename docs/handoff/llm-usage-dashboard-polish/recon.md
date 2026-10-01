# recon: LLM 使用量台帳ダッシュボード サマリーカード統合 + チャート装飾（PR-E）

- 起票日: 2026-10-01
- 対象ブランチ: `release/llm-usage-dashboard-polish`（origin/main `01c275171` 起点）
- 関連 ADR: ADR-1004（LLM使用量台帳）、ADR-027（i18n強制）、ADR-067（デザイントークン強制）、ADR-144（UI共通部品ガバナンス）
- 前便: PR-B #3892 / PR-C #3895 / PR-D #3898（いずれも main マージ済み）
- 今便はフロントエンドのみ。バックエンド（`backend/app/routers/tcg_analysis_dashboard.py` の `GET /tcg/analysis-dashboard/llm-usage`）は無変更。

## 1. 既存 ADR 検索（着手前）

`git grep -i docs/adr/` で `llm_usage` / `llm-usage` を検索した結果、`docs/adr/ADR-1004-llm-usage-ledger.md` が既存（台帳SSoT）。本便は同台帳から取得済みのレスポンスをフロント側で集約表示するのみで、ADR-1004 のスキーマ・書き込み経路は変更しない。`docs/adr/FEATURE-INDEX.md` に本便固有の新規エントリなし（確認済み、該当なし）。

## 2. PO 入力（2026-10-01 時点の表示値、テスト fixture の参考値）

- 費用合計: $8.0243
- 応答が返った回数: 664
- 入力トークン: 29,766,307
- 出力トークン: 388,393

## 3. 現状コード（origin/main `01c275171` 時点、フルパス:行番号）

### 4枚の既存メトリクスカード（今回削除・サマリーカードへ統合）

`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:624-658`
- L624: `{/* 段1: 4枚のメトリクスカード */}`
- L625-658: `<div className="analysis-dashboard-metrics">` 内に `Card variant="metric"` が4枚（費用合計 L626-633 / 応答が返った回数 L634-641 / 入力トークン L642-649 / 出力トークン L650-657）。

### 既存チャート実装（装飾対象）

同ファイル:
- L452-500: 概要「リクエスト数と成功率」`ComposedChart`（Bar + Line の2軸）。
- L502-530: 概要「エラー数（種類別）」積み上げ `BarChart`。
- L541-566 / 568-593 / 595-620: モデル別「入力トークン」「出力トークン」「リクエスト数」の3枚の `LineChart`。
- L661-689: 「日次の費用（使いみち別）」積み上げ `BarChart`。
- L692-720: 「月次の費用（使いみち別）」積み上げ `BarChart`。
- 全チャート共通: `CartesianGrid strokeDasharray="3 3"`（vertical指定なし=デフォルトで縦横両方描画）、`fontSize={12}`（トークン未参照の生数値）、`<Legend />`（デフォルト配置・アイコン未指定）。Y軸に桁短縮なし（`fontSize={12}` のみ）。Line の `dot` は未指定（デフォルトで全点にドット）。

### 金型探索（`frontend/src/components/`）

`git grep -il -e stat -e kpi -e metric -e summary -- frontend/src/components` の結果、専用の KPI/stat/summary コンポーネントは存在しない。唯一の関連ヒットは `frontend/src/components/Card.tsx`（`export type CardVariant = "container" | "interactive" | "metric";`、L16）。`variant="metric"` は単一指標カード用で、複数指標を1枚に集約する金型ではない。
既存の "hero" パターン（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1488-1504`、CSS: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:157-175`）はボトルネック信号（success/warning/danger の border-left 色）が前提のクラス設計で、中立的な集約カードへの転用は意味的に不適合と判断。→ 新規 BEM クラス（`frontend/src/pages/super-admin/components/LlmUsageSection.css`、新設）を `Card variant="container"` の内側に適用する方針（design.md 参照）。

### recharts 数値 props の前例（numeric props チェックの有無）

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` に生数値リテラルの recharts props が既存:
- `strokeWidth={2}`: L971, L979, L1178, L1186, L1602, L1610, L1618
- `strokeWidth="1.5"`: L784（文字列指定の例もある）
- `fontSize={12}`: L961-963, L1168-1170, L1592-1594 ほか多数

`frontend/package.json` の `check:*` スクリプト一覧（L15-41）・`check:all`（L44）を確認した結果、numeric recharts props を flag するチェックは存在しない。→ STOP 条件（「numeric recharts props が flag される」）に該当せず、前例に従い定数化（`UPPER_SNAKE_CASE`）して使用する。

### デザイントークン確認（`frontend/src/index.css` / `frontend/src/tokens.css`）

- `--border`（グリッド線、`frontend/src/index.css:29`）
- `--text-muted`（軸目盛の色、`frontend/src/index.css:25`）
- `--text-primary` / `--text-secondary`（`frontend/src/index.css:23-24`）
- `--font-xs` / `--font-sm` / `--font-md` / `--font-display`（`frontend/src/tokens.css:14-25`）
- `--font-weight-medium` / `--font-weight-semi` / `--font-weight-bold`（`frontend/src/tokens.css:29-31`）
- `--space-1`〜`--space-12`（`frontend/src/tokens.css:68-77`）
- `--chart-series-1`〜`--chart-series-7`（`frontend/src/tokens.css:408-414`、light/dark 両方定義済み、`--cal-*` のエイリアス）
- `--color-success`（成功率ラインの色、既存利用あり）

いずれも既存トークンの再利用のみで、新規色トークンの追加は無し（ADR-067 準拠）。

### i18n 現行キー（`frontend/src/locales/ja.json` / `en.json`、両言語とも L4479-4523 付近）

`analysisRules.dashboard.usage.*` 配下に `note` / `notReported` / `metricCost` / `metricCalls` / `metricInput` / `metricOutput` / `byPurposeTitle` 等、および `health.*`（L4511-4522）が既存。`metricCost`〜`metricOutput`（4キー）は本便で削除対象の4枚カード専用キーのため、使用箇所が無くなることを `git grep -rn "usage\.metricCost\|usage\.metricCalls\|usage\.metricInput\|usage\.metricOutput" frontend/src` で確認済み（他箇所からの参照なし）。新規 `summary.*`（6キー: costLabel/callsLabel/inputLabel/outputLabel/successRateLabel/errorCountLabel）を `health` の直後に追加する設計。

### テストファイル（`frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`、origin/main 215行）

既存15ケース、fixture は `response`（L24-85、`daily_requests: [{ date: "2026-10-01", attempts: 5, completed: 3, failed: 1, success_rate: 0.75 }]` 1行のみ）。成功率（LINE抽出）・エラー件数（LINE抽出）の集計元データとして同じ fixture を再利用し、completed=3/failed=1 → 75.0% を期待値とする。
