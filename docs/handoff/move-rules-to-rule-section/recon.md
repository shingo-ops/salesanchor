# recon: move-rules-to-rule-section

## 対象ADR
- ADR-027（i18n強制）: 全UI文字列はt("key")経由。ja.jsonとen.jsonで同一キー必須

## 現状確認

### AnalysisRulesSidebar.tsx
- ファイル: `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:84-112`
- `status-master`, `conditions-master`, `unit-master` は「マスタ管理グループ」（`hub-subnav-section`）内に配置
- ルール管理グループには `rule-management`, `extraction-rules` の2項目のみ

### ja.json（analysisRules.sidebar）
- ファイル: `frontend/src/locales/ja.json:3973-3977`
- `statusMaster: "ステータスマスタ"`, `conditionsMaster: "状態マスタ"`, `unitMaster: "単位マスタ"`

### en.json（analysisRules.sidebar）
- ファイル: `frontend/src/locales/en.json:3973-3977`
- `statusMaster: "Status Master"`, `conditionsMaster: "Condition Master"`, `unitMaster: "Unit Master"`

### パネルtitle（ja/en）
- `ja.json:1825` `unitMaster.title: "単位マスタ"`
- `ja.json:1844` `statusMaster.title: "ステータスマスタ"`
- `ja.json:4288` `conditionsMaster.title: "状態マスタ"`
- `en.json:1825` `unitMaster.title: "Unit Master"`
- `en.json:1844` `statusMaster.title: "Status Master"`
- `en.json:4288` `conditionsMaster.title: "Condition Master"`

## PO判断
ステータス・状態・単位はTCG解析エンジンの挙動を制御するルール定義であり、実体マスタ（商品・カテゴリ等）とは性質が異なる。ルール管理グループで管理するのが適切（2026-09-24 PO判断）。
