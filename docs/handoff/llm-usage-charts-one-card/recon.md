# recon: LLM 使用量台帳ダッシュボード チャートを1枚のカードに集約（PR-F）

- 起票日: 2026-10-01
- 対象ブランチ: `release/llm-usage-charts-one-card`（origin/main `166943554a7db2da86c3ce22266026f0fb06f01` 起点）
- 前便: PR-E（#3902、`release/llm-usage-dashboard-polish`、マージ済み・サマリーカード統合+チャート装飾）
- 関連 ADR: ADR-1004（LLM使用量台帳）、ADR-027（i18n強制）、ADR-067（デザイントークン強制）、ADR-144（UI共通部品ガバナンス）
- 今便はフロントエンドのみ。バックエンド（`backend/app/routers/tcg_analysis_dashboard.py` の `GET /tcg/analysis-dashboard/llm-usage`）は無変更。

## 1. 既存 ADR 検索（着手前）

`git grep -i docs/adr/` で `llm_usage` / `llm-usage` を検索した結果、`docs/adr/ADR-1004-llm-usage-ledger.md` が既存（台帳SSoT）。本便は同台帳から取得済みのレスポンスのフロント表示レイアウトのみを変更し、ADR-1004 のスキーマ・書き込み経路は変更しない。`docs/adr/FEATURE-INDEX.md` に本便固有の新規エントリなし（該当なし、確認済み）。

## 2. PO 要望

PO（2026-10-01）: PR-E でサマリーカードは1枚に集約済み。残る7枚のチャートカードが個別の `Card` に分かれているため、これも1枚のカードにまとめる（3行構成: 概要/モデル別/費用）。

## 3. 現状コード（origin/main `16694355` 時点、フルパス:行番号）

### 7枚の既存チャートカード（今回1枚のカードへ統合）

`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`

- L558-564: `{/* 概要（LINE抽出）: ... */}` セクション見出し + note（`analysis-dashboard-section-title` + `analysis-dashboard-section-note`）。
- L565-667: `<div className="analysis-dashboard-grid">` 内に `Card variant="container" density="compact" className="analysis-dashboard-chart-card"` が2枚。
  - L566-627: 「リクエスト数と成功率」`ComposedChart`（Bar + Line の2軸）。
  - L629-666: 「エラー数（種類別）」積み上げ `BarChart`。
- L670-795: 「モデル別」セクション見出し + `<div className="analysis-dashboard-grid">` 内に `Card` が3枚。
  - L677-714: 「入力トークン」`LineChart`。
  - L716-753: 「出力トークン」`LineChart`。
  - L755-793: 「リクエスト数」`LineChart`。
- L798-839: 「日次の費用（使いみち別）」積み上げ `BarChart`（単独 `Card`、グリッドなし・1列フル幅）。
- L842-883: 「月次の費用（使いみち別）」積み上げ `BarChart`（単独 `Card`、同上）。

### 現状の構造上の特徴

- 7枚とも `Card variant="container" density="compact" className="analysis-dashboard-chart-card"` を直接使用し、カード内に `analysis-dashboard-section-title` でチャート見出しを表示。
- 概要2枚・モデル別3枚は `analysis-dashboard-grid`（`grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`、`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:318-322`）でグリッド化済み。費用2枚（日次/月次）はグリッド化されておらず、縦に並んでいるだけ（各1枚がフル幅）。
- チャート本体（データ取得・pivot関数・recharts内部props・色定数）はPR-Eで整備済みで、本便では変更しない。

### サマリーカード（今回は対象外・変更なし）

`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:505-556`（`Card variant="container" density="compact" className="llm-usage-summary"`）。

### 表（段2〜4、今回は対象外・変更なし）

`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:886-926`（使いみち別 / 日別 / モデル別の3枚の `DataTable` カード、各 `Card variant="container" density="compact" className="analysis-dashboard-chart-card"`）。

### 金型探索（`frontend/src/components/`）

`git grep -il -e stat -e kpi -e metric -e summary -- frontend/src/components` の結果、専用の「複数チャートを1枚に集約する」金型は存在しない（PR-E recon で既に確認済みの結論を踏襲）。`frontend/src/components/Card.tsx` の `CardVariant = "container" | "interactive" | "metric"`（L16）のうち `"container"` が既存7枚すべてで使われており、本便でも同じ `variant="container"` を外側カードに使う。

### CSS グリッド precedent（minmax パターン）

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:318-322`:
  ```css
  .analysis-dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: var(--space-4);
  }
  ```
- `frontend/src/pages/super-admin/components/LlmUsageSection.css:30-34`（サマリーカード内統計グリッド、PR-Eで新設）:
  ```css
  .llm-usage-summary__stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--space-4);
  }
  ```
- いずれも `minmax(<n>px, 1fr)` + `auto-fit` + `gap: var(--space-4)` のパターン。本便もこのパターンを踏襲する（design.md 参照）。

### デザイントークン確認（`frontend/src/index.css` / `frontend/src/tokens.css`）

- `--border`（区切り線、`frontend/src/index.css:29`。`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:167` 内 `GRID_STROKE_VAR = "var(--border)"` で既に参照あり）
- `--text-primary` / `--text-secondary`（`frontend/src/index.css:23-24`）
- `--font-sm` / `--font-md`（`frontend/src/tokens.css:14-25` 付近）
- `--font-weight-semi`（`frontend/src/tokens.css:29-31` 付近）
- `--space-1`〜`--space-12`（`frontend/src/tokens.css:68-77` 付近）

いずれも既存トークンの再利用のみで、新規色トークンの追加は無し（ADR-067 準拠）。

### i18n 現行キー（`frontend/src/locales/ja.json` / `frontend/src/locales/en.json`、両言語とも L4477-4525 付近）

`analysisRules.dashboard.usage.*` 配下に `note` / `notReported` / `byPurposeTitle` / `dailyTitle` / `byModelTitle` / `dailyByPurposeChartTitle` / `monthlyByPurposeChartTitle` / `health.*`（`title` / `note` / `requestsChartTitle` / `errorsChartTitle` / `attemptsLabel` / `successRateLabel` / `modelTrendTitle` / `inputTokensChartTitle` / `outputTokensChartTitle` / `requestsByModelChartTitle`）/ `summary.*` が既存。カード・行・グラフの見出しに使う既存キーはすべて再利用可能で、削除対象キーは無い。新規に必要なのは「カード全体のタイトル」（グラフ）と「費用行の見出し」（費用）の2キーのみ（design.md 参照）。

`git grep -rn "usage\.chartsCardTitle\|usage\.costRowTitle" frontend/src` は本便の変更前には0件（新規キーであることを確認済み）。

### CSS/i18n 未使用化の有無（今回の変更で不要になるキー・クラス）

- `.analysis-dashboard-grid` は本便で概要行・モデル別行の内部グリッドとして使わなくなる（新規 `.llm-usage-charts__grid` に置き換え）が、`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1628` で引き続き使用中のため削除しない。
- `.analysis-dashboard-chart-card` は費用2枚のカード単体利用が無くなるが、段2〜4（表3枚）で引き続き使用中（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:886-926`）のため削除しない。
- i18n キーはすべて既存キーを再利用するのみで、削除対象キーなし。

### テストファイル（`frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`、origin/main 259行）

既存21ケース（PR-Eで21件まで増加済み）。チャートタイトルのテキストアサーション（`screen.findByText("Requests & Success Rate")` 等）はDOM構造に依存しないため、カード構造を1枚に統合しても既存アサーションは変更なしで成立する。新規にDOM構造（`.llm-usage-charts` コンテナ・`.llm-usage-charts__item` の個数・ネストした `.analysis-dashboard-chart-card` の不在）を検証するテストを追加する（design.md 参照）。
