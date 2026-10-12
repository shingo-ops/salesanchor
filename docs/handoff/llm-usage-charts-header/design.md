# design: LLM使用量チャートカードのヘッダー文言変更

## PO指示（原文・2026-10-01、スクリーンショット添付）
「カードのヘッダーにグラフと記載されているが不要なので削除。概要（LINE抽出）をヘッダーにする」

## recon参照
`docs/handoff/llm-usage-charts-header/recon.md`（本設計の事実根拠。origin/main `a0c3ae38872ba1e308ff758009f6b1c2bd550c34` 時点）

## 対象ADR
ADR-027, ADR-067, ADR-144, ADR-1004（このセクション自体の由来・`frontend/src/pages/super-admin/components/LlmUsageSection.tsx` はADR-1004: public.llm_usage_events のダッシュボード表示。本変更はADR-1004の対象コンポーネントの見出し文言のみを変更し、データ・スキーマ・API契約には触れない）

## Before / After

### Before（origin/main）
```tsx
// frontend/src/pages/super-admin/components/LlmUsageSection.tsx:559-571
<Card variant="container" density="compact" className="llm-usage-charts">
  <div className="analysis-dashboard-section-title">
    {t("analysisRules.dashboard.usage.chartsCardTitle")}   {/* 「グラフ」 */}
  </div>

  <div className="llm-usage-charts__row">
    <div className="llm-usage-charts__row-title">
      {t("analysisRules.dashboard.usage.health.title")}     {/* 「概要（LINE抽出）」 */}
    </div>
    <p className="analysis-dashboard-section-note">
      {t("analysisRules.dashboard.usage.health.note")}
    </p>
    ...
```
表示: カード見出し「グラフ」→ 行1小見出し「概要（LINE抽出）」→ 注記、の二段表示。

### After（本PR）
```tsx
// frontend/src/pages/super-admin/components/LlmUsageSection.tsx:558-566
<Card variant="container" density="compact" className="llm-usage-charts">
  <div className="analysis-dashboard-section-title">
    {t("analysisRules.dashboard.usage.health.title")}       {/* 「概要（LINE抽出）」をカード見出しに昇格 */}
  </div>

  <div className="llm-usage-charts__row">
    <p className="analysis-dashboard-section-note">
      {t("analysisRules.dashboard.usage.health.note")}
    </p>
    ...
```
表示: カード見出し「概要（LINE抽出）」→ 注記、の一段表示。行2（モデル別）・行3（費用）の小見出しと上の区切り線（`.llm-usage-charts__row-title` / `border-top`）は変更なし。

## 変更ファイル
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（カード見出しの参照キーを `chartsCardTitle` → `health.title` に差し替え、行1の `__row-title` div を削除）
- `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`（「Charts」非表示の確認、「Overview (LINE Extraction)」が1回だけ出る確認に更新）
- `frontend/src/locales/ja.json`（`chartsCardTitle` キー削除、`:4480`）
- `frontend/src/locales/en.json`（`chartsCardTitle` キー削除、`:4480`）

CSS（`frontend/src/pages/super-admin/components/LlmUsageSection.css`）は無変更。`.analysis-dashboard-section-title`（カード見出し、共用クラス）・`.llm-usage-charts__row-title`（行2/3見出し、使用継続）とも削除・追加なし。

## 基準・検証方法

| 基準 | 検証方法 |
|---|---|
| カード見出しに「グラフ」が表示されない | `check:i18n-missing-keys` で `chartsCardTitle` キー未参照を確認 ＋ `vitest` で `screen.queryByText("Charts")` が null |
| カード見出しが「概要（LINE抽出）」（`health.title`）になる | `vitest`: `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx:186-191`（既存）が `findByText("Overview (LINE Extraction)")` で通過 |
| 「概要（LINE抽出）」が二重表示されない（行1小見出しと重複しない） | `vitest`（新規）: `screen.getAllByText("Overview (LINE Extraction)").length === 1` |
| 行2（モデル別）・行3（費用）の小見出しと上の区切り線は維持 | `vitest`: `modelTrendTitle` / `costRowTitle` の英訳文言が引き続き検出されること（既存アサーション `"Input Tokens"`, `"Output Tokens"` 等 継続通過で確認） |
| i18n: ja/en キー対称性維持、未使用キー残存なし | `npm run check:i18n-missing-keys` PASS ＋ `git grep -n "chartsCardTitle" -- frontend/src` がヒットなし |
| ADR-027（t()経由） | 新規ハードコード文字列なし。`health.title` を再利用するのみ。`grep` で `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` 内の日本語リテラルがコメント以外に存在しないことを確認 |
| ADR-067（トークンのみ） | CSS無変更。新規色・サイズ値の追加なし |
| ADR-144（金型のみ） | `Card` コンポーネント・既存クラス `.analysis-dashboard-section-title` を流用、新規UI部品・生要素の追加なし |
| TypeScript型エラーなし | `npx tsc --noEmit` exit 0 |
| Lint違反なし | `npx eslint --max-warnings=0` 対象ファイルで 0件 |
| CSSガード系（トークン・命名・ダークパリティ） | `check:css-colors` / `check:css-values` / `check:css-class-naming` / `check:dark-parity` 全てPASS（CSS無変更のため影響なしの確認目的） |

## 外部・過去事例
該当なし。本変更は社内ダッシュボードの見出し文言整理であり、同種のUIパターン選定（公開事例の参照）を要する新規デザイン判断ではない（PO指示に基づく文言差し替えのみ、デザイン上の新規判断なし）。

## 影響範囲
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` を import/使用する箇所は `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` のみ（`git grep -n "LlmUsageSection" -- frontend/src` で確認、呼び出し元は1箇所・props (`days`, `t`) 変更なし）。
- `chartsCardTitle` キーは `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` 以外から参照されていない（recon.md 確認済み）ため、キー削除による他画面への影響なし。
- `.llm-usage-charts__row-title` クラスは行2・行3で使用継続のためCSS側の影響なし。

## 戻し方
本コミットを `git revert` すれば、`chartsCardTitle` キー・行1小見出しdiv・カード見出しの参照キーがすべて復元される（ファイル変更4件のみ、マイグレーション等の不可逆操作なし）。

## 維持の仕組み
- i18nキーの対称性は `npm run check:i18n-missing-keys`（CI必須チェック）が継続的に保証する。未使用キーの残存はこのチェック対象外のため、将来また「使われていないキー」が残るリスクはあるが、本PRでは `git grep` で削除前に確認済み。
- カード見出しクラス `.analysis-dashboard-section-title` は `AnalysisDashboardPanel.css:307-312` で一元定義された共用クラスであり、個別カードごとにスタイルが分岐しない設計のため、今後も見出しの見た目が他カードと乖離しにくい。

守り手: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`, `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`, `frontend/scripts/check-i18n-missing-keys.js`
