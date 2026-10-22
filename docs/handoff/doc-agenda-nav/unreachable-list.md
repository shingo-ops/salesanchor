# 目次から届かない文書の一覧と扱い（design §10-4）

status: 決定済み（PO 原文「fableにまかせてくれ」2026-10-22 → Fable の判断で全件確定。design §20）。作成 2026-10-22。

## 1. 数え方（基準値の訂正）

- 基準: origin/main 5e1193a39（2026-10-22 fetch）。入口6ファイル（CLAUDE.md・AGENTS.md と frontend・backend の各 CLAUDE.md・AGENTS.md）から、本文中の「.md で終わるパス文字列」をすべて辺として幅優先で辿る（recon §2-5 の記述どおり）。
- 結果: docs/specs 308本中 届かない 17本、docs/ai-agents 34本中 届かない 19本、最深 15段。
- 【事実】kgi.md K4 の基準値「specs 35・ai-agents 19・最深14段」は、元のスクリプトが保存されておらず（§11）、辺の取り方を7通り試しても specs 35 と ai-agents 19 が同時に出る定義は無かった。よって本一覧と段2の CI は上の定義を正とし、K4 の基準値は specs 17・ai-agents 19 に読み替える（合格ライン「0」は不変）。
- 参考: リンク記法（角かっこと丸かっこ）だけを辺にすると、入口6ファイルにリンク記法が1本も無いため docs/specs 308本すべてが届かない扱いになる。フォルダ名の言及から直下の全文書へ辺を張ると、届かないのは specs 8・ai-agents 0 になる（言及だけで中身の文書名は分からないため、K4 の定義には採らない）。
- 生出力（リポジトリ外）: ~/CC報告ファイル-keep/agenda-nav-20261022/unreach/（reach.py・reach-out.txt・facts.md・round2/specs17.md・round2/lessons.md）。

## 2. 推奨の決め方

- 「目次に登録」: 消さずに辿れるようにするだけで、あとで戻せる。迷うものはこちらに倒す。
- 「記録扱いへ移動」: 1回限りの作業記録で、同じ作業の記録置き場（docs/handoff/<作業名>/）が既にあるものだけ。
- 登録先は、そのテーマの表紙（README.md）に1行足す。表紙が無いものは親の表紙に足す。

## 3. 一覧（docs/specs 17本）

| # | 文書 | 最終更新 | ほかからの参照 | 事実 | 推奨 |
|---|---|---|---|---|---|
| 1 | docs/specs/attachment-storage/to-be.md | 2026-09-01 | 3ファイル（handoff） | 表紙 README に名前なし。テーマは docs/specs/README.md:86 | 登録 |
| 2 | docs/specs/dashboard/to-be.md | 2026-07-07 | 0 | 表紙に名前なし。テーマは docs/specs/README.md:57 | 登録 |
| 3 | docs/specs/dashboard/track-record.md | 2026-07-07 | 0 | 同上（実績台帳） | 登録 |
| 4 | docs/specs/schedule/to-be.md | 2026-07-07 | 0 | 表紙に名前なし。テーマは docs/specs/README.md:56 | 登録 |
| 5 | docs/specs/schedule/track-record.md | 2026-07-07 | 0 | 同上（実績台帳） | 登録 |
| 6 | docs/specs/inbox/track-record.md | 2026-07-05 | 0 | 表紙 docs/specs/inbox/README.md:21-23 は ideal-state・kgi・design のみ | 登録 |
| 7 | docs/specs/inventory-management/spec-v1.0.md | 2026-05-25 | 0 | 509行。表紙に名前なし。後継は同フォルダの spec.md（1行目の題名が同一。spec.md §Version に v1.0 初版起案〜v1.3 の履歴。spec.md:3 は「.claude-pipeline/spec-v1.0.md に保管」と書くが、そのパスは origin/main に無い） | 登録（docs/specs/inventory-management/README.md:24「既存資料との関係」節に「spec.md の v1.0 起案版（spec.md §Version で v1.1〜v1.3 に置き換え済み）」と1行。spec.md:3 の保管先の記載を同じ PR で直すのは任意） |
| 8 | docs/specs/ledger-guard/design-g2.md | 2026-07-20 | scripts/dev/executor-preflight.sh:79 が設計の場所として指す | 表紙に名前なし | 登録（移すと scripts の注記が切れる） |
| 9 | docs/specs/process-hardening/design-pillar1.md | 2026-07-24 | 0 | 表紙に名前なし。同フォルダに pillar2・pillar3 あり | 登録 |
| 10 | docs/specs/product-master/product-classification-decisions.md | 2026-06-30 | 0 | 表紙に名前なし。決定記録 | 登録 |
| 11 | docs/specs/product-master/dev-plans/2026-09-tcg-product-master-fill-title-date.md | 2026-09-06 | 0 | dev-plans に表紙なし | 登録（product-master の表紙へ） |
| 12 | docs/specs/local-hooks-ssot/guard-disabled-record.md | 2026-08-31 | 0 | 見張りを止めた記録。:48 に「操作できる状態が続いている」と今の状態を書く | 登録 |
| 13 | docs/specs/process-hardening/proof-of-behavior/README.md | 2026-07-21 | handoff 1 | 子テーマの表紙。親 process-hardening の表紙から案内が無い | 登録（親の表紙に1行。14・15 もこれで届く） |
| 14 | docs/specs/process-hardening/proof-of-behavior/ideal-state.md | 2026-07-21 | 0 | 13 の表紙に名前あり | 登録（13 で解決） |
| 15 | docs/specs/process-hardening/proof-of-behavior/kgi.md | 2026-07-21 | 0 | 13 の表紙に名前あり | 登録（13 で解決） |
| 16 | docs/specs/master-ssot-migration/design-fix-unify-type-mismatch.md | 2026-09-22 | docs/handoff/fix-unify-type-mismatch/design.md:43 | フォルダに表紙なし・docs/specs/README.md に行なし。1回の不具合修正の設計メモ。同じ修正の記録置き場が docs/handoff/fix-unify-type-mismatch/ にある | 移動（docs/handoff/fix-unify-type-mismatch/ へ。参照元 :43 はパスを書き換えず、行末に「（2026-10 に同フォルダへ移動）」を添える＝記録の原本は書き換えない） |
| 17 | docs/specs/master-ssot-migration/recon-fix-unify-type-mismatch.md | 2026-09-22 | docs/handoff/fix-unify-type-mismatch/design.md:42 | 同上（調査メモ） | 移動（同上。:42 にも同じ添え書き。2本を一緒に移すので design 側 :4 の相対参照は切れない） |

## 4. docs/ai-agents 19本（教訓のメモ）

- 19本すべて docs/ai-agents/lessons.d/ の教訓メモ。決まり: docs/ai-agents/design-partner.md:202「教訓は lessons.d/ に1便1ファイル。本文への移植は清書便のみ」、読む道具 scripts/lessons-view.sh:9（フォルダごと表示）、守り .github/workflows/lessons-guard.yml:29。
- 19本とも design-partner.md §6 本文へまだ清書されていない（要点行の固定文字列 grep で 19件すべて一致0。round2/seisho-check.txt）。
- 推奨: 1本ずつではなく、目次（段2で作る docs/INDEX.md）に lessons.d のフォルダを「読み方: scripts/lessons-view.sh」と1行で登録する。CI では「目次にフォルダとして登録された場所の直下の文書は届く」とみなす。中身の整理（清書）は既存の lessons-guard の決まりのまま、本テーマでは触らない。

## 5. PO の判断

- 2026-10-22 PO 原文「fableにまかせてくれ」→ Fable の判断（全文 ~/CC報告ファイル-keep/agenda-nav-20261022/fable/decisions.md）: §3 と §4 の推奨どおりに確定（#7 と #16・#17 は上の書き方に確定）。段2の PR に含める。
- 参考（判断は不要）: lessons.d の直下は 22枚で scripts/lessons-view.sh:37 の警告の目安 20 を超える（清書は本テーマの範囲外）。docs/specs/master-ssot-migration/ に表紙が無い（K4 には影響しない。段2で docs/specs/README.md に1行足すのは任意）。
