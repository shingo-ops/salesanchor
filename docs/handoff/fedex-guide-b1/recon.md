# recon — FedEx 連携ガイド骨格 B-1

**仕事名**: fedex-guide-b1  
**日付**: 2026-06-13  
**対象ADR**: ADR-129  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 | 確認内容 |
|--------|---------|
| `docs/STANDARD-WORKFLOW.md:20` | Phase 2 現在地把握（recon）の定義。file:line 引用・推測禁止ルール |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md:1` | ADR-129 冒頭: Label Validation 申請支援ウィザードの目的・スコープ |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:31` | `type PageTab = "credentials" \| "integrationGuide"` — タブ定義 |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:200` | `pageTabs` 定義: FedEx のみ 2 タブ（tabCredentials / tabIntegrationGuide）|
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:420` | `{pageTab === "integrationGuide" && isFedex && <FedexLabelValidationTab />}` — 連携ガイドタブからの呼び出し箇所 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:39` | `function StepHeader(...)` — ステップヘッダー共通コンポーネント |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:50` | `export function FedexLabelValidationTab()` — タブ本体エクスポート |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:153` | `<div className="lv-wizard">` — 現行ルート要素 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:154` | `<h3>{t("carrierIntegration.lvTitle")}</h3>` — 現行タイトル（置き換え対象）|
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:8` | `.lv-wizard` — ウィザード全体コンテナ |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:35` | `.lv-step-num` — ステップ番号バッジ |
| `frontend/src/locales/ja.json:226` | `"tabIntegrationGuide": "連携ガイド"` — タブ名 |
| `frontend/src/locales/ja.json:249` | `"lvTitle": "FedEx Label Validation 申請支援"` — 現行タイトル（置き換え対象）|
| `frontend/src/locales/en.json:226` | `"tabIntegrationGuide": "Integration guide"` — タブ名（英語）|
| `frontend/src/locales/en.json:249` | `"lvTitle": "FedEx Label Validation Wizard"` — 現行タイトル（英語）|

---

## 既存ADR検索結果

- `docs/adr/FEATURE-INDEX.md` 行 17: FedEx / shipping → ADR-103 / ADR-123 / ADR-128 / ADR-125 / ADR-129
- ADR-129（fedex-label-validation-wizard）: J4 で「Label Validation 申請支援タブ」として実装済み。B-1 ではこのタブを「連携ガイド」全体として2部構成に拡張する
- ADR-067（design-tokens）: PR-A3 で FedEx ページの全カラーをトークン化済み。lv-* CSS はトークン参照済み
- ADR-027（i18n）: 全文字列は t("key") 経由。新規キーは carrierIntegration.fedexGuide* で追加

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | CarrierIntegrationPage に props を追加するか | 対象外ファイルのため変更なし。Step 6 はテキスト案内のみで対応 | ✅ 解消済み |
| 2 | 既存 9 ステップの番号を Part 2 内で継続するか | 既存 lv-key を壊さないため Step 1〜9 のまま維持（Part 2 内で独立）| ✅ 解消済み |
| 3 | backend / migration 変更が必要か | 不要。frontend only で完結（既存 API はそのまま使用）| ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- CarrierIntegrationPage.tsx:420 が `FedexLabelValidationTab` を呼び出す唯一の箇所
- lv-* CSS は PR-A3 で ADR-067 トークン準拠済み。追加クラスも同じ方針で実装
- B-1 は骨格（skeleton）。プレースホルダは data-screenshot 属性で後工程の差し替えに対応
