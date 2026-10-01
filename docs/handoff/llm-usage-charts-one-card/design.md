# design: LLM使用量台帳ダッシュボード チャートを1枚のカードに集約（PR-F）

- recon: `docs/handoff/llm-usage-charts-one-card/recon.md`
- 関連 ADR: ADR-1004, ADR-027, ADR-067, ADR-144

## 背景・動機

PO要望（2026-10-01、PR-F）: PR-E（#3902、マージ済み）でサマリーカードは1枚に集約済みだが、残る7枚のチャート（概要2枚・モデル別3枚・費用2枚）はそれぞれ個別の `Card` に分かれたまま。これを1枚の `Card` に集約し、3行（概要/モデル別/費用）構成にする。

バックエンド API（`GET /tcg/analysis-dashboard/llm-usage`）は無変更。チャート内部（データ・色・recharts props）も無変更。変更はレイアウト（カードの入れ子構造）とそれに伴う新規CSS/i18nキーのみ。

## 1. カード構造（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`）

既存7枚の `Card variant="container" density="compact" className="analysis-dashboard-chart-card"`（recon §3、L558-883）を、以下の1枚の `Card` に置き換える。

```
<Card variant="container" density="compact" className="llm-usage-charts">
  <div className="analysis-dashboard-section-title">{t("...chartsCardTitle")}</div>

  <div className="llm-usage-charts__row">          {/* 行1: 概要（LINE抽出） */}
    <div className="llm-usage-charts__row-title">{t("...health.title")}</div>
    <p className="analysis-dashboard-section-note">{t("...health.note")}</p>
    <div className="llm-usage-charts__grid">
      <div className="llm-usage-charts__item">
        <div className="llm-usage-charts__item-title">{t("...requestsChartTitle")}</div>
        {/* 既存 ComposedChart、データ/props 変更なし */}
      </div>
      <div className="llm-usage-charts__item">
        <div className="llm-usage-charts__item-title">{t("...errorsChartTitle")}</div>
        {/* 既存 BarChart、データ/props 変更なし */}
      </div>
    </div>
  </div>

  <div className="llm-usage-charts__row">          {/* 行2: モデル別 */}
    <div className="llm-usage-charts__row-title">{t("...modelTrendTitle")}</div>
    <div className="llm-usage-charts__grid">
      {/* 入力トークン / 出力トークン / リクエスト数 の3枚、既存 LineChart ×3 */}
    </div>
  </div>

  <div className="llm-usage-charts__row">          {/* 行3: 費用 */}
    <div className="llm-usage-charts__row-title">{t("...costRowTitle")}</div>
    <div className="llm-usage-charts__grid">
      {/* 日次の費用 / 月次の費用 の2枚、既存 BarChart ×2 */}
    </div>
  </div>
</Card>
```

- 各チャートはネストした `Card` を持たず、`llm-usage-charts__item` の中に小見出し（`llm-usage-charts__item-title`）＋既存の `analysis-dashboard-chart` / `llm-usage-chart` ラッパーのみを置く。
- 各行の「データなし」空状態（`dailyRequestsData.length === 0` 等）は既存のチャート単位の条件分岐をそのまま維持（recon §3 の各チャートの既存ロジックを移植するのみ）。
- サマリーカード（L505-556）と表3枚（L886-926）はこの変更の対象外。既存のまま。

## 2. CSS（`frontend/src/pages/super-admin/components/LlmUsageSection.css`、新設クラス追加）

recon §3「CSS グリッド precedent」の `minmax(<n>px, 1fr)` + `auto-fit` + `gap: var(--space-4)` パターンを踏襲。行間の区切りは `<hr>` ではなく `border-top: 1px solid var(--border)` を使う（`--border` は `frontend/src/index.css:29` で定義済み、`LlmUsageSection.tsx` の `GRID_STROKE_VAR` で既に参照されているトークンと同一）。

```css
.llm-usage-charts__row {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border);
}

.llm-usage-charts__row:first-of-type {
  padding-top: 0;
  border-top: none;
}

.llm-usage-charts__row-title {
  font-size: var(--font-md);
  font-weight: var(--font-weight-semi);
  color: var(--text-primary);
}

.llm-usage-charts__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-4);
}

.llm-usage-charts__item-title {
  font-size: var(--font-sm);
  font-weight: var(--font-weight-semi);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}
```

`minmax(280px, 1fr)` は `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:320` と同じ値をそのまま踏襲（既存7枚のチャートが元々 `analysis-dashboard-grid` でこの値を使っていたため、見た目の列幅を変えないための選択）。`auto-fit` により画面幅が狭いと自動で1列に折りたたまれる（レスポンシブ要件を満たす）。

## 3. i18n（`frontend/src/locales/ja.json` / `frontend/src/locales/en.json`、同一キー構造）

`analysisRules.dashboard.usage` 直下に2キー追加（`note` の直後）:

```json
"chartsCardTitle": "グラフ",
"costRowTitle": "費用",
```
(en: "Charts" / "Cost")

他の見出し（`health.title` / `health.note` / `health.requestsChartTitle` / `health.errorsChartTitle` / `health.modelTrendTitle` / `health.inputTokensChartTitle` / `health.outputTokensChartTitle` / `health.requestsByModelChartTitle` / `dailyByPurposeChartTitle` / `monthlyByPurposeChartTitle`）はすべて既存キーをそのまま再利用（recon §3 で確認済み、削除対象キーなし）。

## 4. CSS/i18n の未使用化チェック（削除可否）

recon §3「CSS/i18n 未使用化の有無」で確認済み:
- `.analysis-dashboard-grid` は `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1628` で引き続き使用中のため削除しない。
- `.analysis-dashboard-chart-card` は表3枚（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx` 段2〜4）で引き続き使用中のため削除しない。
- 削除対象の i18n キーなし（既存キーの再利用のみ、新規2キー追加のみ）。

よって本便では既存CSS/i18nの削除は発生しない。

## 5. フロントエンドテスト（`frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`）

- 既存21ケースは変更なし（チャートタイトルのテキストアサーションはDOM構造に非依存のため、カード統合後も成立する）。
- 追加: 1枚の `.llm-usage-charts` カードが7つのチャートタイトルすべてを含み、ネストした `.analysis-dashboard-chart-card` を持たないことを検証するテスト（`llm-usage-charts__item` が7個以上存在し、`.analysis-dashboard-chart-card` の個数が表3枚分の3のみであることを確認）。サマリーカード（`.llm-usage-summary`）の存在も合わせて確認。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 7枚のチャートが1枚の `Card`（`.llm-usage-charts`）に集約されている | テストで `.llm-usage-charts` の `textContent` に7チャートタイトルすべてを確認 |
| 各チャートがネストした `Card`（`.analysis-dashboard-chart-card`）を持たない | テストで `chartsCard.querySelector(".analysis-dashboard-chart-card")` が `null` |
| サマリーカード・表3枚は変更なし | テストで `.llm-usage-summary` の存在、`.analysis-dashboard-chart-card` の個数が3（表のみ）であることを確認 |
| 行間の区切りがCSS変数（`--border`）経由 | `npm run check:css-colors` / `check:css-values` が0件（新規hex・px直書きなし） |
| グリッドがレスポンシブ（`auto-fit`）で、既存precedentと同じ値 | `frontend/src/pages/super-admin/components/LlmUsageSection.css` を目視確認（`minmax(280px, 1fr)` が `AnalysisDashboardPanel.css:320` と一致） |
| 新規UI文字列がすべて `t()` 経由・ja/en同一キー | `npm run check:i18n-missing-keys` が0件 |
| ダークモードの色トークンに欠落がない | `npm run check:dark-parity` |
| 日本語ハードコードがコメント外に無い | `grep -n '[ぁ-んァ-ン一-龥]' frontend/src/pages/super-admin/components/LlmUsageSection.tsx` をコメント行除外で0件 |
| TypeScript/ESLintが通る | `npx tsc --noEmit` / `npx eslint <touched files> --max-warnings=0` |
| CSS命名規則・stylelintが通る | `npm run check:css-class-naming` / `npx stylelint LlmUsageSection.css` |
| 既存+新規テストが通る | `npx vitest run LlmUsageSection.test.tsx` |

## 外部・過去事例

該当なし。本便はレイアウト変更（複数カードを1枚に集約）のみで、PR-E（#3902）の Google AI Studio 参考はチャート装飾（色・ドット・Legend等）の話であり、本便のカード集約そのものには外部事例を参照していない。既存の社内precedent（`AnalysisDashboardPanel.css` のグリッドパターン、`llm-usage-summary` のカード集約パターン）のみを踏襲する。

## 維持の仕組み

- 守り手: `frontend/src/pages/super-admin/components/LlmUsageSection.css` の `.llm-usage-charts__*` BEM クラスはこのコンポーネント専用スコープのため、他ページの `analysis-dashboard-*` クラスと衝突しない。
- 守り手: `frontend/scripts/check-css-hardcoded-colors.js` / `frontend/scripts/check-css-hardcoded-values.js`（`npm run check:css-colors` / `check:css-values`）が新規hex・px直書きの追加をCIで検出するため、将来の区切り線・グリッド幅の変更もトークン経由に強制される。
- 守り手: `frontend/scripts/check-i18n-missing-keys.js`（`npm run check:i18n-missing-keys`）が ja/en キー不一致をCIで検出するため、`chartsCardTitle` / `costRowTitle` の片方のみ追加といった漏れが将来も防止される。
