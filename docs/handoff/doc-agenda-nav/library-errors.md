# 図書館化: 本が「無い／開かれなかった／読み違えた」の記録

根拠: [library-design.md](./library-design.md) §7。題と数え方: [library-tasks.md](./library-tasks.md)（commit c86124619 で測る前に固定）。合否には使わない。記録だけ。
このリポジトリは公開されている。決まりの本文と AI の答えの全文は書かない。

## 1回目（段3 の後の基準値・2026-11-03）

- 実行: PO が `!` で「~/CC報告ファイル-keep/doc-library-20261102/practice-run.sh」を1回流した（PO 2026-11-03「1」）。写しは origin/main b492b3f1c（detached）。8実行と `/context` の終了コードはすべて 0。写しの書き換えは無かった（DIRTY 無し）。
- 生出力: 「~/CC報告ファイル-keep/doc-library-20261102/practice/」（各実行の jsonl・result.tsv・context.txt・exits.txt）。
- 合計: 開いた 4・開かれなかった 4・拒まれた 0・読み違えた 0。費用は 1.05 ドル（8実行の total_cost_usd の合計）。

| 日付 | 題 | 分類 | 直し | PR |
|---|---|---|---|---|
| 2026-11-03 | B1-1 | 開いた（Read で本を読んだ。必ず含む語あり） | — | この PR |
| 2026-11-03 | B1-2 | 開いた（同上） | — | この PR |
| 2026-11-03 | B2-1 | 開かれなかった（リポジトリの branch-operations/README.md・INDEX.md・executor-checklist.md を読んで答えた。必ず含む語あり） | PO の判断待ち（§2） | この PR |
| 2026-11-03 | B2-2 | 開かれなかった（リポジトリの INDEX.md・branch-operations/README.md・executor-checklist.md と、自動メモリの PR の作り方を読んで答えた。必ず含む語なし） | PO の判断待ち（§2） | この PR |
| 2026-11-03 | B3-1 | 開いた（Bash の cat で本を読んだ。必ず含む語あり） | — | この PR |
| 2026-11-03 | B3-2 | 開いた（同上） | — | この PR |
| 2026-11-03 | B4-1 | 開かれなかった（リポジトリの INDEX.md・branch-operations/README.md・ADR を grep して答えた。必ず含む語あり） | PO の判断待ち（§2） | この PR |
| 2026-11-03 | B4-2 | 開かれなかった（リポジトリの INDEX.md・executor-checklist.md・branch-operations/README.md・ADR を grep して答えた。必ず含む語あり） | PO の判断待ち（§2） | この PR |

## 2. 気づいたこと（設計 §7 の「開かれなかったが 8回中4回以上」に当たる）

- 開かれなかった4回は、どれも題「PR を作る手順」「マージ前に要る審査」だった。リポジトリにはこの2つの手順書が別にある（branch-operations/README.md・executor-checklist.md・ADR）。AI はそちらを読んで答えた。~/kb/AGENTS.md の優先順位では、リポジトリの決まりが一番上である。
- 開いた4回は、題「commit の文の書き方」「最初に呼ぶ担当」だった。リポジトリに同じ趣旨の手順書が見当たらない題である（どの実行もリポジトリの文書を読まずに本を開いた）。
- 毎回読む量: `/context` の Memory files が 17.8k、そのうち MEMORY.md が 11.5k。差の K9 は 6.3k で、週次点検の値と同じ（設計 §9 受入条件 L1）。本（~/.claude/books/）は Memory files の一覧に無い（BOOKS_IN_CONTEXT=0 と同じ）。
- 設計 §7 は、この場合に「目録の行の文言を直す」か「スキル化」を PO に見せると決めている。PO の選択はこの表の「直し」に書き足す。
