# card: 目次を短い表にして会話の始めに読み込む（案 C3 をそのまま入れる。クラウドの Sonnet 向け）

## カードチェック（design-partner.md §5.5）
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 記号を `` ` `` で囲む | ○ |
| 2 | PR | ○ 担当は PR を作らない。Opus が差分を読んでから作る |
| 3 | 報告先 | ○ 生出力入りの報告ファイル（§6） |
| 4 | 目的は 1 つ | ○ AI が依頼を受けたとき正しい手順書を開く（K12 ≥ 18/20）ようにする |
| 5 | 土台のブランチ | ○ このカードがあるブランチ `release/k12-index-push`（`origin/main` から作成済み） |
| 6 | 形は例で示す | ○ 変更後の全文は `docs/handoff/doc-library-one-tree/drafts/` の3ファイル。追記は §2 に全文 |
| 7 | 合格基準に出力 | ○ §5 |
| 8 | 対象の名前 | ○ 触ってよいファイル 8 つ（§1 の 4・§2 の 2・§2b の台帳 1・§6 の報告 1） |
| 9 | 出力の上限 | ○ tail -80 |
| 10 | 受付と終わりの合図 | ○ 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` |
| 11 | 想定値は実測 | ○ §0 の想定は 2026-11-04 の実物（origin/main 7d56ab771 と同じ中身） |
| 12 | 止まる条件 2 段 | ○ §4 |
| 13 | sleep なし・Write/Edit・見張りで止まったら言い換えない | ○ |

- 設計: [k12-fix-design.md](k12-fix-design.md) §4・§12・§13。合格ライン: [kgi.md](../../specs/doc-agenda-nav/kgi.md) K9（7.5k 以下、PO 決定 2026-11-04）・K11・K12。
- PO の承認: 2026-11-04 チャット「1」（K9 の上限を 7.5k に上げ、案 C3 が 18/20 以上なら採用）。案 C3 は 19/20 で条件を満たした。完走（マージまで）は PO の先の指示。
- 作業ブランチ: `release/k12-index-push`。このブランチにコミットして push する。main には触らない。
- 公開リポジトリ。`~/.claude`・`~/kb` の決まりの本文を書き写さない。

## §0 着手前の点検（違えば NEEDS_DECISION で止まる）
結果を報告に貼る。
| 確かめること | 想定 |
|---|---|
| `wc -l CLAUDE.md AGENTS.md docs/INDEX.md` | 9・46・44 |
| `diff AGENTS.md docs/handoff/doc-library-one-tree/drafts/AGENTS-C.md` | 違いは 26・43・45 行目の3か所だけ |
| `ls docs/ai-agents/entry-rule-add.md` | 無い |
| `grep -c "AGENTS.md から移した" docs/handoff/rehearsal-env/design-b-ssh-isolation.md docs/ai-agents/executor-checklist.md` | どちらも 0 |
| `grep -n "^## §1" docs/ai-agents/executor-checklist.md` | 1 か所 |

## §1 入れ替えと追加（下書きをそのまま使う。中身を書き換えない）
(1) 26・43 行目の元の文を先に控える: `sed -n 26p AGENTS.md > /tmp/l26.txt; sed -n 43p AGENTS.md > /tmp/l43.txt`
(2) `cp docs/handoff/doc-library-one-tree/drafts/INDEX-C3.md docs/INDEX.md`
(3) `cp docs/handoff/doc-library-one-tree/drafts/entry-rule-add.md docs/ai-agents/entry-rule-add.md`
(4) `cp docs/handoff/doc-library-one-tree/drafts/AGENTS-C.md AGENTS.md`
(5) `CLAUDE.md` の末尾に `@docs/INDEX.md` の1行を足す（`printf '@docs/INDEX.md\n' >> CLAUDE.md`。10 行になる）。

## §2 外した文を移し先へ一字一句置く（K11）
(1) `docs/handoff/rehearsal-env/design-b-ssh-isolation.md` の末尾に、空行・見出し `## 無制限鍵の使い方（AGENTS.md から移した決まり、2026-11-04）`・空行・`/tmp/l26.txt` の1行をそのまま足す。
(2) `docs/ai-agents/executor-checklist.md` の `## §1` 見出しの直前（§0 の最後の箇条の後）に、`/tmp/l43.txt` の1行をそのまま足し、その行の行末に ` （AGENTS.md から移した決まり、2026-11-04）` は足さない（一字一句のため）。§0 の最後の箇条と §1 見出しの間の空行は1行に保つ。

## §2b 決まり台帳に移した2行を登録する（2026-11-04 追記）
1 回目の実行（クラウド 2026-11-04 20:10）で、提出前の検査 `check_rule_registry` が次の2行を「未仕分け」として止めた。`docs/ai-agents/entry-rule-add.md:14`（7問目）と `docs/ai-agents/executor-checklist.md:20`（§2(2) で移した行）。どちらも決まりの台帳 `docs/specs/rule-enforcement/rules.yml`（ADR-1047）に項目が無いため。台帳の変更は GO 記録の要る対象なので、GO は Opus が PR で出す（担当は気にしなくてよい）。
(1) `rules.yml` 5 行目のコメントの行末 `OI=ops-incident-agent` の後ろに ` ER=entry-rule-add` を足す（5 行目はこの1か所だけ変える）。
(2) `rules.yml` の `  - id: XP336` の行の直前に、次の 10 行をそのまま入れる（字下げは空白。既存の項目と同じ形）。
```
  - id: X412
    source: docs/ai-agents/executor-checklist.md
    anchor: "- push・PR/issue の本文・コメントに仕入元の投稿の原文を"
    kind: review
    reason: "gate候補（R6）: 仕入元の投稿の原文を書き写さない決まりと、止められたときの直し方・push と本文の渡し方。confidential-quote-guard（ADR-1045）が push・PR 本文の送信前に原文と照らして止める。ただし PO 端末に登録する見張りで、必須チェックではない（AGENTS.md の A015 から移した本文）"
  - id: ER413
    source: docs/ai-agents/entry-rule-add.md
    anchor: "7. 全セッションで Claude が知る必要があるか"
    kind: review
    reason: "入口に決まりを足す前の判定の7問目（全セッションで要らない決まりは入口に書かない）。入口を変える PR で人が見る"
```
(3) 確かめ: `python3 -I scripts/ci/check_rule_registry.py --root . > /tmp/t7.txt 2>&1; echo "rc=$?" >> /tmp/t7.txt; tail -40 /tmp/t7.txt` が `rc=0`・未仕分け 0。
(4) commit は §1・§2 の 6 ファイルと同じ commit に `docs/specs/rule-enforcement/rules.yml` を含める（7 ファイル）。

## §3 触らないもの
§1・§2 の 6 ファイル、§2b の `rules.yml`、§6 の報告以外。`docs/handoff/doc-library-one-tree/drafts/` も変えない。

## §4 止まる条件
- 1 段目（NEEDS_DECISION）: §0 の想定と違う。§5 の検査が、下書きを変えないと通らない。
- 2 段目（BLOCKED）: 見張り（hook）に止められた（言い換えない）。push が断られた。§5 が 2 回直しても通らない（生出力を報告に貼る）。

## §5 確かめ（出力はファイルへ。tail -80 で読む）
```
python3 -I scripts/ci/check_doc_index.py --root . --strict > /tmp/t1.txt 2>&1; echo "rc=$?" >> /tmp/t1.txt; tail -80 /tmp/t1.txt
node frontend/scripts/check-claude-size.js > /tmp/t2.txt 2>&1; echo "rc=$?" >> /tmp/t2.txt; tail -80 /tmp/t2.txt
grep -cxFf /tmp/l26.txt docs/handoff/rehearsal-env/design-b-ssh-isolation.md > /tmp/t3.txt; grep -cxFf /tmp/l43.txt docs/ai-agents/executor-checklist.md >> /tmp/t3.txt; cat /tmp/t3.txt
diff docs/INDEX.md docs/handoff/doc-library-one-tree/drafts/INDEX-C3.md && diff AGENTS.md docs/handoff/doc-library-one-tree/drafts/AGENTS-C.md && diff docs/ai-agents/entry-rule-add.md docs/handoff/doc-library-one-tree/drafts/entry-rule-add.md && echo SAME
for f in docs/runbooks/*.md; do grep -q "runbooks/$(basename $f)" docs/INDEX.md || echo "MISSING $f"; done
bash scripts/dev/check-before-submit.sh > /tmp/t6.txt 2>&1; echo "rc=$?" >> /tmp/t6.txt; tail -80 /tmp/t6.txt
```
- 合格: t1 が `rc=0`・警告 0。t2 が `rc=0`。t3 が `1` と `1`。`SAME` が出る。`MISSING` が 0 行。t6 が `rc=0`。§2b(3) の t7 が `rc=0`。
- 上の合格がそろうまで push しない。t6 が通らないときは §4 の止まる条件に従う（`--no-verify` は使わない）。
- K9・K12 は担当は測らない（マージ後に PO の手元で測る）。

## §6 報告
- `docs/handoff/doc-library-one-tree/impl-report-k12.md` を作り、同じブランチにコミットして push する（push は `git -C <作業場所の絶対パス> push -u origin release/k12-index-push` を単独で）。
- 中身: §0 の生出力、`git diff --stat origin/main`、§5 の生出力、最後の HEAD の sha、最後の行に `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>`。
