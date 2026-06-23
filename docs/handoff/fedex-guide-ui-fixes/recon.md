# recon — fedex-guide-ui-fixes

**仕事名**: fedex-guide-ui-fixes  
**日付**: 2026-06-23  
**対象ADR**: ADR-087  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/integrations/CarrierSetupGuidePage.tsx:37` | `PageLayout` でラップしていることを確認 |
| `frontend/src/components/PageLayout.tsx:36` | `.page-layout-content` が `overflow-y: auto` を持つことを確認 |
| `frontend/src/pages-layout.css:94` | `.page-layout-content { overflow-y: auto }` — フルスクリーンで高さ制約なし = sticky 無効の原因 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:46` | `.etd-stepper { position: sticky; top: 0 }` — sticky 設定済みだが機能していない状態 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:97` | `.etd-stepper__dot { width: var(--icon-lg); font-size: var(--font-xs) }` — サイズ拡大対象 |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:282` | `<p className="form-hint">` — サブステップ説明文のクラス確認 |
| `frontend/src/components.css:611` | `.form-hint { color: var(--text-muted) }` — 薄いグレーの原因 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | sticky が効かない根本原因 | pages-layout.css で overflow-y: auto + 高さ制約なしを確認 | ✅ 解消済み |
| 2 | ESLint raw `<h2>` ルール | CarrierSetupGuidePage を PageLayout wrapper で実装 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
