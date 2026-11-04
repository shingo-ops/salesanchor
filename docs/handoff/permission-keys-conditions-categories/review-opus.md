# 設計審査の記録: 状態マスタ・商品カテゴリの権限キー

設計: [design.md](design.md)。審査はクラウドの Opus（書いた本人と別の会話）が、ファイルを変えずに読んで行った。同じ AI の系統による審査で、独立した第三者の審査ではない。

| 回 | 日時（UTC） | 先頭 | 判定 | 主な指摘 | 直し |
|---|---|---|---|---|---|
| 1 | 2026-11-04 00:25 | a348ec1f1 | REVISE | 行番号のずれ、Depends を 2 つ並べると両方必要（合っていた）、取り込みが is_active を書くので削除の権限なしで消せる、戻しの SQL が無い、見張りの作りたての値、名前だけの試験 | design.md §10-1 |
| 2 | 2026-11-04 00:35 | f3b89a8c7 | REVISE | T7 が SQLite の試験では書けない（表が無く 500 になる）、delete_condition の行番号、§10-1 の番号 | design.md §10-2 |
| 3 | 2026-11-04 00:41 | e9318f7d8 | APPROVE | 軽い注記 2 点（T4 の依存の扱い、確認元の版の書き方） | design.md §10-3 |

- 3 回目の照合範囲: conditions.py :43・:50-63・:66-75・:324-361・:412-470、conftest.py の client と bypass_permissions、dependencies.py の require_permission、main.py の router の組み込み、cache.py:19。
- 設計審査の合格は、PO の承認・実装の開始・マージ・本番反映の承認を兼ねない。

## 便1-コードの差分の確認（Opus・手元）

- 対象: ブランチ `release/permission-keys-conditions-code` の実装 commit 3e1fa12d8（クラウドの Sonnet が [card-impl-1.md](card-impl-1.md) に沿って作成）。報告は [impl-report-1.md](impl-report-1.md)（最後の行 DONE）。
- 照合: `git diff origin/main...3e1fa12d8` の 7 ファイルを、design.md §4-1・§6 と card-impl-1.md §1・§2 に 1 行ずつ当てた。
  - dependencies.py は `return checker` の直前に 1 行足しただけで、判定の中身は変わっていない。
  - conditions.py は catalog の鍵の付け替えと、import の preview・commit への 3 つの Depends だけ。ほかの経路は変わっていない。
  - 画面 2 ファイルは表示条件だけを変え、部品・文言・`data-testid`・`onClick` は変わっていない。画面の試験が使う `conditionCsv.selectFile` の文言キーは部品に実在する。
  - 試験 T1〜T7 は数をちょうどの値で確かめている（403・200 と total 0・409）。
- 担当の確かめ（報告の生出力）: pytest 9 passed（全体カバレッジ 60% 未満の表示は 2 ファイルだけ流したため）・vitest 2 passed・tsc 0・eslint 0・check-before-submit 落ち 0。最後の判定は CI。
- 判定: 設計どおり。マージ前の審査役（Opus）の審査は PR で別に受ける。
