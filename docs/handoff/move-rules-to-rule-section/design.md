# design: move-rules-to-rule-section

## 対象ADR
- ADR-027（i18n強制）

## recon参照
- docs/handoff/move-rules-to-rule-section/recon.md

## 変更内容

### AnalysisRulesSidebar.tsx
- `status-master`, `conditions-master`, `unit-master` をマスタ管理グループから削除
- ルール管理グループ（`rule-management`, `extraction-rules` の後）に追加

### ja.json
- `analysisRules.sidebar.statusMaster`: "ステータスマスタ" → "ステータスルール"
- `analysisRules.sidebar.conditionsMaster`: "状態マスタ" → "状態ルール"
- `analysisRules.sidebar.unitMaster`: "単位マスタ" → "単位ルール"
- `unitMaster.title`: "単位マスタ" → "単位ルール"
- `statusMaster.title`: "ステータスマスタ" → "ステータスルール"
- `conditionsMaster.title`: "状態マスタ" → "状態ルール"

### en.json
- 同上（Status Rules, Condition Rules, Unit Rules）

## 影響範囲
- サイドバー表示・パネルtitleのみ変更
- DB・API・解析ロジック変更なし
- パネルコンポーネント自体（StatusMasterPanel等）は変更なし
- activeSection→パネルのマッピング（AnalysisRulesPage.tsx）は変更なし

## 基準と検証方法

| 基準 | 検証方法 |
|------|----------|
| ルール管理セクションにステータスルール・状態ルール・単位ルールが表示される | サイドバーを目視確認 |
| マスタ管理セクションに商品マスタ等が残る | サイドバーを目視確認 |
| 各パネルが正常に開く | クリックして動作確認 |
| ja/en i18nキー一致 | ja.json / en.json の同一キーを確認 |

## 外部事例
特になし（単純なUIグループ移動）

## 守り手
- ESLint（commit hookで自動実行）
- i18n整合チェック（ADR-027）
