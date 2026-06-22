# recon — fedex-etd-step1-guide

**仕事名**: fedex-etd-step1-guide  
**日付**: 2026-06-22  
**対象ADR**: ADR-137  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:235` | portal ステップの JSX（サブステップ追加対象） |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:244` | `etd-guide__substeps` リスト挿入箇所 |
| `frontend/src/locales/ja.json:329` | `fedexEtdGuideStep1_1` キー（サブステップ 1-1 日本語） |
| `frontend/src/locales/ja.json:335` | `fedexEtdGuideStep1SandboxNote` キー（テストキー注記） |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:133` | `.etd-guide__substeps` CSS クラス定義 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:161` | `.etd-guide__screenshot` CSS クラス定義 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:169` | `.etd-guide__note--info` CSS クラス定義 |
| `docs/adr/ADR-137-fedex-etd-paperless-trade.md:54` | 実装フェーズ E4（FE: J4）— 本作業の位置づけ |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | スクリーンショット ⑦ にマスクが必要か | Image #8（会話内）で確認済み — グレー矩形でマスク適用済み | ✅ 解消済み |
| 2 | 危険変更ゼロか | `git diff --name-only origin/develop...HEAD` で 11 ファイルすべて `frontend/` のみ確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
