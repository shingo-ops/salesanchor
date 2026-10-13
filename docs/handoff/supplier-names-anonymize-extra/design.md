# design: 一覧外の仕入元名と先方担当者名を仮名に置き換える（社外秘）

参照: docs/handoff/supplier-names-anonymize-extra/recon.md／前回便 docs/handoff/supplier-names-anonymize-docs/design.md。PO 承認 2026-10-13（一覧にない仕入元名と、仕入元の担当者＝先方の人の個人名。自社の人・提供者G・migrations・locales は除く）。

## 方針

repo 外の対応表（extra-mapping.tsv）にもとづき、Python で行ごとに置換する。日本語は完全一致、英字を含む名前は英数字の隣接を許さない単語境界で照合する。長い名前から先に置換し、仕入元は「提供者X」（L〜AN）、先方担当者は「担当者N」にする。置換前後の全行は repo 外 replace-plan.tsv に実名入りで残し、置換後の行に元の名前の一部が残らないか確認する。挙動は変えない（docs のみ。backend/app・backend/tests の置換は 0 行）。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| 置換対象の名前が追加行に 1 件も無い | `git diff origin/main...HEAD \| grep '^+'` に対し、日本語は `-F`、英字は単語境界（大小無視）で照合 → 0 件（名前一覧 names-target.txt は repo 外） |
| migrations/・frontend/src/locales/・backend/ を触っていない | `git diff --name-only origin/main...HEAD` にそれらが無い |
| 一般語・地名への部分一致を置換していない | 一般語 1 行と英字地名 5 行が差分に無い（`git diff` で当該ファイル・行が変わっていない） |
| 関係するテストの結果が前後で同じ | `python3 -m pytest tests/test_tcg_supplier_quality.py -q` が前後とも 30 passed |
| 提供者G の行を触っていない | 置換スクリプトが「提供者G」を含む行を丸ごと除外（該当行 0） |
| 不明 32 件を置換していない | 差分に「不明」の仮名が出ない（今回は仮名を割り当てない） |

## 外部・過去事例の参照と我々への応用

該当なし（理由: リポジトリ内の文字列置換で、外部の導入事例が参考になる設計要素が無いため）。前回便（10社）の手順をそのまま踏襲した。

## 維持の仕組み

守り手: 上記の追加行 grep（受入条件の 1 行目）と、backend/tests/test_tcg_supplier_quality.py（仕入元名を入力に使うテスト）。新しい文書に実名を書かない運用は PO 方針（2026-10-01 仕入元データは社外秘）に従う。自動検査の新設は今回の範囲外。

## 戻し方

`git revert`（文字列置換のみ。DB・設定に影響なし）。

## 範囲外・既知の残り

- 過去の git 履歴には実名が残る。
- 不明 32 件は置換しない（PO 判断待ち）。
- 姓だけ・略称だけの別表記は、前回の「2文字以下は対象外」判断に従い置換していない（行の位置は repo 外 residual-fragments.txt）。
- migrations/ にしか無い先方担当者 3 件は対象外のまま。
