# design: LLM使用量台帳ダッシュボード サマリーカード統合 + チャート装飾（PR-E）

- recon: `docs/handoff/llm-usage-dashboard-polish/recon.md`
- 関連 ADR: ADR-1004, ADR-027, ADR-067, ADR-144

## 背景・動機

PO要望（2026-10-01）: (1) 4枚に分かれている主要指標を画面最上部の1枚のサマリーカードに集約し、ダッシュボードらしく見せる。(2) recharts チャートを Google AI Studio の使用状況ページを見せ方の参考にスタイリッシュ・可読に改善する（数値そのものの主張はしない。見せ方の参考のみ）。

バックエンド API（`GET /tcg/analysis-dashboard/llm-usage`）は無変更。既存レスポンスの `total` / `daily_requests` から集計する。

## 1. サマリーカード（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`）

- 挿入位置: 既存の note/mismatchNote の直後、「概要（LINE抽出）」セクションの直前（タブの最上部）。
- 金型: recon §3「金型探索」の結果、専用 KPI/summary コンポーネントは存在しないため `Card variant="container" density="compact" className="llm-usage-summary"` を使用し、新規 BEM クラス（`frontend/src/pages/super-admin/components/LlmUsageSection.css`、新設）をその内側に適用する。
- 構造:
  - `.llm-usage-summary__hero`: 費用合計（`data.total.cost_usd`、既存 `formatCurrency` 再利用）を大きく表示。
  - `.llm-usage-summary__stats`: 5項目のグリッド。
    1. 応答が返った回数（`data.total.calls`）
    2. 入力トークン（`formatNumber(data.total.prompt_tokens, t)`）
    3. 出力トークン（既存 `formatOutputTokens(candidates, thoughts, t)` 再利用）
    4. 成功率（LINE抽出） = `sum(completed) / sum(completed + failed)` over `data.daily_requests`（分母0のときは `null` → `notReported`）
    5. エラー件数（LINE抽出） = `sum(failed)` over `data.daily_requests`
- 旧4枚の `Card variant="metric"`（`analysis-dashboard-metrics` グリッド、旧 L624-658）は削除。数値の二重掲載なし。
- 新規ヘルパー関数:
  - `summarizeDailyRequests(rows)` — `{ successRate: number | null; errorCount: number }` を返す純粋関数（空配列なら `successRate: null, errorCount: 0`）。
  - `formatSuccessRateOrNotReported(value, t)` — `null` のとき `notReported`、それ以外は `(value*100).toFixed(1)}%`。

## 2. チャート装飾（全チャート共通、`LlmUsageSection.tsx` 内）

既存6チャート（概要2枚 + モデル別3枚 + 使いみち別日次/月次2枚）すべてに以下を適用:

| 要素 | Before | After |
|---|---|---|
| `CartesianGrid` | `strokeDasharray="3 3"`（縦横両方・色未指定） | `vertical={false} strokeDasharray="3 3" stroke="var(--border)"`（横線のみ） |
| 軸目盛 | `fontSize={12}`（生数値、色未指定） | `tick={{ fontSize: 12, fill: "var(--text-muted)" }}`（定数 `AXIS_TICK_FONT_SIZE` 経由） |
| Y軸（数量・トークン・コスト） | 桁短縮なし | `tickFormatter` に `formatCompactNumber(value, i18n.language)`（`Intl.NumberFormat(lang, {notation:"compact"})`、例: 29.8M）。ツールチップは既存の `toLocaleString()` / `formatCurrency` でフル桁を維持（変更なし）。成功率専用の `%` 軸（`domain=[0,100]`）は対象外（桁短縮の意味がないため）。 |
| `Bar` | 角丸なし・太め | `radius={[4,4,0,0]}`（定数 `BAR_RADIUS`）・`barSize={24}`（定数 `BAR_SIZE`） |
| `Line` | 全点にドット（デフォルト） | `dot` に最終点のみ描く関数 `renderLastPointDot(dataLength, color)` を渡す。`activeDot={{ r: 5 }}` でホバー時のみ強調。 |
| `Legend` | デフォルト配置・アイコン未指定 | `verticalAlign="bottom" iconType="circle" iconSize={8}`（定数 `LEGEND_ICON_SIZE`） |
| チャート高さ | 概要/使いみち別=240、モデル別=200（バラバラにハードコード） | 定数化（`CHART_HEIGHT=240` / `MODEL_CHART_HEIGHT=200`）。グループ内は既存グリッドクラス（`analysis-dashboard-grid`）でカード揺れを揃える既存仕様を維持。 |

数値 props（radius/barSize/strokeWidth/fontSize）は recon §3 で確認した前例（`AnalysisDashboardPanel.tsx` の `strokeWidth={2}` 等）に従い、`LlmUsageSection.tsx` 冒頭で `UPPER_SNAKE_CASE` 定数として定義する（`CHART_HEIGHT` / `MODEL_CHART_HEIGHT` / `AXIS_TICK_FONT_SIZE` / `BAR_RADIUS` / `BAR_SIZE` / `LINE_STROKE_WIDTH` / `LAST_POINT_DOT_RADIUS` / `ACTIVE_DOT_RADIUS` / `LEGEND_ICON_SIZE`）。numeric recharts props を flag するチェックスクリプトは存在しないため（recon §3 確認済み）、STOP 条件には該当しない。

## 3. i18n（`frontend/src/locales/ja.json` / `en.json`、同一キー構造）

`analysisRules.dashboard.usage.health` の直後に `summary` ブロックを追加:

```json
"summary": {
  "costLabel": "費用合計",
  "callsLabel": "応答が返った回数",
  "inputLabel": "入力トークン",
  "outputLabel": "出力トークン",
  "successRateLabel": "成功率（LINE抽出）",
  "errorCountLabel": "エラー件数（LINE抽出）"
}
```
(en: "Total Cost" / "Calls with response" / "Input Tokens" / "Output Tokens" / "Success Rate (LINE Extraction)" / "Error Count (LINE Extraction)")

旧4枚カード専用の `metricCost` / `metricCalls` / `metricInput` / `metricOutput` は使用箇所が無くなるため削除（recon §3 で他箇所からの参照なしを確認済み）。

## 4. フロントエンドテスト（`frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`）

- 既存15ケースは変更なし（コールテキスト「Calls with response」は `colCalls` 列ヘッダーと `summary.callsLabel` の両方で使われるため、既存アサーション `getAllByText(...).length > 0` は維持したまま成立する）。
- 追加:
  1. サマリーカードがヒーロー費用 + 5スタッツを表示する（`.llm-usage-summary` を class で特定し `textContent` を検証）。
  2. `daily_requests: []` のとき成功率が `notReported`（"Not reported"）になる。
  3. 旧4枚カードのグリッド（`.analysis-dashboard-metrics`）が存在しない。
  4. `formatCompactNumber`（export した純粋関数）の単体テスト: `29766307 → "30M"`、`388393 → "388K"`、小さい値はそのまま。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 旧4枚の個別メトリクスカードが画面上から消え、数値が重複表示されない | `container.querySelector(".analysis-dashboard-metrics")` が `null` であることをテストで確認 |
| サマリーカードが1枚で、費用合計(hero)+5スタッツを表示する | テストで `.llm-usage-summary` の `textContent` に6項目すべてを確認 |
| 成功率の分母0は「記録なし」にフォールバックする | `daily_requests: []` fixture でテスト |
| 新規UI文字列がすべて `t()` 経由・ja/en同一キー | `npm run check:i18n-missing-keys` が0件 |
| 色・サイズがすべてデザイントークン経由（新規hexなし） | `npm run check:css-colors` / `check:css-values` / `check:color-token-sync` が0件 |
| ダークモードの色トークンに欠落がない | `npm run check:dark-parity` |
| numeric recharts props が既存前例どおりで、flagされない | `npm run check:all` の全チェックが通ること（専用チェックは存在しないため lint/tsc が通れば良い） |
| 日本語ハードコードがコメント外に無い | `grep -n '[ぁ-んァ-ン一-龥]' frontend/src/pages/super-admin/components/LlmUsageSection.tsx` をコメント行除外で0件 |
| TypeScript/ESLintが通る | `npx tsc --noEmit` / `npx eslint <touched files>` |
| 既存+新規テストが通る | `npx vitest run LlmUsageSection.test.tsx` |

## 外部・過去事例の参照と我々への応用

Google AI Studio の使用状況ページ（API Usage ダッシュボード）の見せ方を参考にした（数値そのものの主張・比較は行わない。あくまで「上部に1枚の集約カード＋下に推移チャート」というレイアウトパターンの参考）。本便では既存の `--chart-series-*` / `--border` / `--text-muted` 等、既存トークンのみでこのレイアウトパターンを再現する。

## 維持の仕組み

- 守り手: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` 冒頭の定数群（`CHART_HEIGHT` 等）が全チャートの装飾値を一元管理するため、将来チャートを追加する開発者は定数を再利用するだけで同じ見た目になる（ハードコードの再発防止）。
- 守り手: `frontend/src/pages/super-admin/components/LlmUsageSection.css` の BEM クラス（`.llm-usage-summary__*`）はこのコンポーネント専用スコープのため、他ページの `analysis-dashboard-*` クラスと衝突しない。
- 守り手: `frontend/scripts/check-css-colors.js` 相当（`npm run check:css-colors` / `check:color-token-sync`）が新規hexの追加をCIで検出するため、将来の色追加もトークン経由に強制される。
