# Recon: ETD ガイド Step1 「ステップ2へ進む」ボタン移動

## 変更対象

| 分類 | ファイル:行 | 内容 |
|------|------------|------|
| メインコンポーネント | `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:74` | `SubstepPane` 関数定義・props |
| 新 props 追加 | `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:79` | `onAdvance?: () => void` |
| 新 props 追加 | `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:85` | `advanceLabel?: string` |
| isLast 計算 | `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:89` | `isLast = activeIndex === substeps.length - 1` |
| advance ボタン配置 | `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:137` | substep-detail 末尾に条件付きボタン |
| props 渡し | `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:381` | portal ステップの SubstepPane に `onAdvance={advance}` |
| props 渡し | `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:382` | `advanceLabel={t("carrierIntegration.fedexEtdGuideStep1AdvanceButton")}` |
| フッター条件変更 | `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:547` | `currentStep.key !== "portal"` 条件でのみフッターを表示 |
| i18n (ja) | `frontend/src/locales/ja.json:375` | `"fedexEtdGuideStep1AdvanceButton": "ステップ2へ進む"` |
| i18n (en) | `frontend/src/locales/en.json:375` | `"fedexEtdGuideStep1AdvanceButton": "Proceed to Step 2"` |

## 既存 ADR 検索結果

- `docs/adr/ADR-027-ui-internationalization.md` — i18n 必須（全 UI 文字列を `t()` 経由）
- `docs/adr/FEATURE-INDEX.md` で "fedex" "etd" "guide" を確認 → ETD ガイド固有 ADR なし
- ETD ガイド関連の既存 handoff: `docs/handoff/etd-guide-remove-back/`（#2583 戻るボタン削除）

## 変更しない範囲

- `frontend/src/pages/integrations/FedexLabelValidationTab.css` — CSS は変更なし
- `frontend/public/images/fedex-setup/step1-07-overview.png` — 画像は変更なし（既存と同一）
- Portal ステップ以外のナビゲーション動作 — 変更なし
