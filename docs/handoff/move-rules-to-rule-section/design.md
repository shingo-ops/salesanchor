# design: move-rules-to-rule-section

## 対象ADR
- ADR-027（i18n強制）

## recon参照
- docs/handoff/move-rules-to-rule-section/recon.md

## 変更内容

### AnalysisRulesSidebar.tsx
- `status-master`, `conditions-master`, `unit-master` をマスタ管理グループから削除
- ルール管理グループ（`rule-management`, `extraction-rules` の後）に追加

### ja.json / en.json
- サイドバー表示名: ステータスマスタ→ステータスルール、状態マスタ→状態ルール、単位マスタ→単位ルール
- パネルtitle: 同様に変更

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

## 外部・過去事例の参照と我々への応用
- UI上のグループ分けは機能の性質に従うべきという原則（設定値=ルール、実体データ=マスタ）
- 過去: AnalysisRulesPage でルール管理グループと マスタ管理グループを分離した設計（ADR-027）
- 応用: ステータス/状態/単位はエンジン動作制御なのでルール管理グループへ移動

## 維持の仕組み
- 新規サイドバー項目追加時はPOと性質（ルール vs マスタ）を確認してグループを決定する
- i18nキーはADR-027でja/en同一キー必須（lint-stagedで強制）

## 守り手
- ESLint（commit hookで自動実行）
- i18n整合チェック（ADR-027）
