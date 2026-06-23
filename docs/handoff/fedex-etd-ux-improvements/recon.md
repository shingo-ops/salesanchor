# recon — fedex-etd-ux-improvements

**仕事名**: FedEx ETD ガイド UX 改善 3点  
**日付**: 2026-06-23  
**対象ADR**: ADR-027, ADR-067, ADR-129  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:1-9` | コンポーネントの import 構造・依存確認 |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:19-23` | `StepDefinition` interface に `heading` フィールドあり |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:148-156` | `stepDefinitions` 配列が `ETD_ENABLED` フラグで step4 を動的に追加 |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:213-224` | 旧プログレスバー実装（`.etd-guide__progress`）→ 置き換え対象 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:44-73` | `.etd-guide__progress*` CSS（置き換え対象） |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:161-170` | `.etd-guide__screenshot` — サムネイル制限 CSS（復元対象） |
| `frontend/src/tokens.css:160-164` | `--size-screenshot-thumb-h: 180px` — 削除対象トークン |
| `frontend/src/locales/ja.json:1` | `fedexEtdGuideStep1Desc` キー — Trans プレースホルダ更新対象 |
| `frontend/src/constants/icons.tsx:196` | `Check` icon export — ステッパー完了ドットで使用 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `ETD_ENABLED=false` 時にステッパーが破綻しないか | `stepDefinitions` 配列を直接参照するため自動で step 数が変わる | ✅ 解消済み |
| 2 | `z-index` ハードコード禁止（ADR-067）に引っかからないか | `--z-base: 10` トークンを使用 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
