# design: 文書・説明文・テストの仕入元名を仮名に置き換える（社外秘・10社）

参照: docs/handoff/supplier-names-anonymize-docs/recon.md／ADR-099（在庫モデル。置換対象の文書の一つ）。PO 承認 2026-10-13（提供者G・migrations・履歴を除く10社分）。

## 方針

mapping.tsv（リポジトリ外）の対応どおり、Python で完全一致の文字列置換を行う。コードの挙動は変えない（コメント・docstring・テスト入力値のみ）。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| 対象10社の名前が追加行に1件も無い | `git diff origin/main...HEAD \| grep '^+' \| grep -c -F -f names10.txt` が 0 |
| 対象範囲（G・migrations・locales 以外）の全ファイルに10社の名前が残らない | `git grep -c -F -f names10.txt HEAD -- . ':!migrations' ':!frontend/src/locales'` が出力なし |
| テスト結果が変更前後で同じ | `python3 -m pytest tests/test_tcg_line_import.py -q --no-cov` が前後とも 69 passed |
| 複合名テストの意図が保たれる | 入力・マスタ名・期待値すべてが「提供者I 太郎」（スペース含む）で一致 |
| JSON が壊れていない | 置換後に json.load が通る |
| 提供者G・migrations・locales を触っていない | `git diff --name-only` にそれらが無い |

## 外部・過去事例の参照と我々への応用

該当なし（理由: リポジトリ内の文字列置換で、外部の導入事例が参考になる設計要素が無いため）。

## 維持の仕組み

守り手: backend/tests/test_tcg_line_import.py（仮名で通ること）と、上記の grep（受入条件の2行）。新しい文書に実名を書かない運用は、PO 方針（2026-10-01 仕入元データは社外秘）に従う。自動検査の新設は今回の範囲外。

## 戻し方

`git revert`（文字列置換のみ。DB・設定に影響なし）。

## 範囲外・既知の残り

過去の git 履歴には実名が残る。提供者G・migrations・locales は対象外。
