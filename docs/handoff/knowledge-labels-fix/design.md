# 設計 — knowledge-labels-fix

**対象ADR**: ADR-093
**recon**: docs/handoff/knowledge-labels-fix/recon.md
**日付**: 2026-09-27
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：i18n JSONキー追加とTSX配列更新のみ。外部事例の参照は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| block_delimiter/skip_condition/status_keyword がUIに日本語で表示される | 画面確認（KnowledgeAliasesTab の正規化ルール一覧 カテゴリ列） |
| 列名「変換前ワード」→「検索キーワード」に変わっている | 画面確認（テーブルヘッダー） |
| 列名「変換後ワード」→「変換先」に変わっている | 画面確認（テーブルヘッダー） |
| フォームのカテゴリ選択肢に block_delimiter/skip_condition/status_keyword が表示される | 画面確認（新規ルール作成ポップアップ） |
| 既存カテゴリ（normalize/split/alias_normalize等）が引き続き正常表示 | 画面確認 |

---

## 技術 How・KPI

- KPI: 上記5基準を全て満たす
- 技術選択: i18n JSON への追記 + RULE_CATEGORIES 配列への追記のみ（ロジック変更なし）

---

## 弊害・トレードオフ

- なし（既存キーを削除せず追記のみ。DB・API・ルーターに変更なし）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | ja.json categories に3キー追加、fields修正、categoryHelp修正 | Hikky-dev |
| 2 | en.json 同様修正 | Hikky-dev |
| 3 | KnowledgeAliasesTab.tsx RULE_CATEGORIES に3値追加 | Hikky-dev |
| 4 | PR作成・CI確認 | Hikky-dev |

## 維持の仕組み

- 新たなDBカテゴリ値が増えた場合は同ファイルに追記が必要（3箇所: ja.json/en.json/RULE_CATEGORIES）
- 既存の `defaultValue: r.category` フォールバックにより未対応カテゴリも内部名で表示され続ける
