# recon: LLM使用量チャートカードのヘッダー文言変更

## 対象
PR #3906（`e07fa5972`, PR-F）で新設されたチャート集約カード（class `llm-usage-charts`）。
origin/main (`a0c3ae38872ba1e308ff758009f6b1c2bd550c34`) 時点のコード。

## PO指示（2026-10-01、スクリーンショット添付・原文）
「カードのヘッダーにグラフと記載されているが不要なので削除。概要（LINE抽出）をヘッダーにする」

## 現状（origin/main）の該当箇所

### 1. カードタイトル「グラフ」
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:558` コメント `{/* グラフ: 概要（LINE抽出）/ モデル別 / 費用 を1枚のカードに集約 */}`
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:559` `<Card variant="container" density="compact" className="llm-usage-charts">`
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:560-562`
  ```tsx
  <div className="analysis-dashboard-section-title">
    {t("analysisRules.dashboard.usage.chartsCardTitle")}
  </div>
  ```

### 2. 行1（概要）のサブ見出し「概要（LINE抽出）」
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:564` コメント `{/* 行1: 概要（LINE抽出）: Google AI Studio の使用状況ページを参考にした見せ方 */}`
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:565-571`
  ```tsx
  <div className="llm-usage-charts__row">
    <div className="llm-usage-charts__row-title">
      {t("analysisRules.dashboard.usage.health.title")}
    </div>
    <p className="analysis-dashboard-section-note">
      {t("analysisRules.dashboard.usage.health.note")}
    </p>
  ```
- 行2（モデル別見出し `.llm-usage-charts__row-title` を使用）: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:678-680`
- 行3（費用見出し `.llm-usage-charts__row-title` を使用）: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:808-810`

### 3. i18nキー
- `chartsCardTitle`
  - `frontend/src/locales/ja.json:4480` `"chartsCardTitle": "グラフ",`
  - `frontend/src/locales/en.json:4480` `"chartsCardTitle": "Charts",`
- `health.title`（流用先。変更しない・削除しない）
  - `frontend/src/locales/ja.json:4508` `"title": "概要（LINE抽出）",`
  - `frontend/src/locales/en.json:4507` `"title": "Overview (LINE Extraction)",`
- `chartsCardTitle` の参照箇所は上記 `LlmUsageSection.tsx:561` の1箇所のみ（`git grep -n "chartsCardTitle" -- frontend/src` で確認、origin/main時点でヒットは locales 2ファイル + tsx 1箇所の計3件）。

### 4. CSS
- 共通クラス `.analysis-dashboard-section-title`（カードタイトルに使用、他の分析ダッシュボードカードと共用）
  - 定義: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:307-312`
  - `LlmUsageSection.tsx` 内の他3箇所（段2〜4の表カード見出し、`LlmUsageSection.tsx:904`, `918`, `932`）でも同一クラスを使用しており、PO指示の「同じ要素・スタイルでヘッダーにする」の基準を満たす既存クラス。
- 行見出しクラス `.llm-usage-charts__row-title`
  - 定義: `frontend/src/pages/super-admin/components/LlmUsageSection.css:72-76`
  - 行2・行3（モデル別・費用）で使用継続のため削除しない。
- 行の区切り線（border-top）
  - 定義: `frontend/src/pages/super-admin/components/LlmUsageSection.css:59-70`
  - `.llm-usage-charts__row:first-of-type { padding-top: 0; border-top: none; }`（`:72` 前の `:67-70`）により、行1はもともと区切り線なし。カードタイトルと行1の間に別途の区切り線要素は存在しない（`.analysis-dashboard-section-title` に `border` 指定なし、`margin-bottom` のみ）。

### 5. テスト
- `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx:250-274`（`"consolidates all 7 charts into a single charts card"`）が `text.toContain("Charts")`（chartsCardTitle の英訳）をアサートしており、変更後は失格するため要修正。
- `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx:186-191`（`"renders the requests & success rate chart..."`）は既に `health.title` の英訳 `"Overview (LINE Extraction)"` を `findByText` しており、カード見出しに昇格しても文言自体は変わらないため影響なし。

## ADR確認（着手前検索）
`git grep -i -l "llm.usage\|chartsCardTitle\|analysis-dashboard-section-title" docs/adr/` でカード見出し文言そのものを規定するADRはヒットなし。関連する横断ルールは以下:
- `docs/adr/ADR-027-ui-internationalization.md`（全UI文字列 t() 経由 → 本変更も `health.title` キーを再利用、新規ハードコードなし）
- `docs/adr/ADR-067-design-token-enforcement.md`（色・サイズはトークンのみ → 本変更はCSS新規追加なし）
- `docs/adr/ADR-144-ui-component-governance.md`（Card/DataTable 金型のみ使用 → 既存 `Card` コンポーネント・既存クラスを流用、新規UI部品なし）
- `docs/adr/ADR-1004-llm-usage-ledger.md`（このセクション自体の由来・PR-F=#3906 の集約方針）
`docs/adr/FEATURE-INDEX.md` にも「チャートカードヘッダー」固有のエントリなし（機能キーワード `llm-usage` / `chart` で検索、該当ADRなし）。
