# 実装カード 段7（段6を含む） — 全員共通のルール集を短くする

> この文書は何か：doc-agenda-nav 段7 の作業指示書です。会話の始まりに必ず読まれる ~/.claude/CLAUDE.md から、古い決まり1つ（段6）を消し、GAS / clasp の決まりを GAS の作業のときだけ読まれる ~/.claude/rules/gas-clasp.md へ文言そのまま移します。変えるたびに K9（会話の始まりに読む量）を測ります。

- 設計: docs/handoff/doc-agenda-nav/design.md
  - §28: 段7 の設計判断（§28-3 が作り方、§28-4 が受け入れ基準）
  - §10-5: 段6 の3行を消すことの決定
- 対象ADR: ADR-1040（Accepted）
- 状態: 設計は Opus の設計判断（§28、2026-10-25）。PO の承認は 2026-10-25 の「1」（全員共通のルール集を組み替える案を作る）と、案を見せた後の「1」（この案で直す＝実装の承認）。
- 危険便かどうか: 変えるのはリポジトリの外のユーザー側の2ファイルだけ。リポジトリ・本番・CI・Ruleset・secrets・~/kb は触らない。
- 作業の最初に: リポジトリの作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage7 で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装と確かめ: Sonnet（model "sonnet"）
  - 結果の照合と記録: Opus

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを絶対パスの cd から始める・出力はファイルへ・sleep しない・報告に無い出力を成功と扱わない | ○（§4・§8） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段7 の実行結果である」と書くこと。

## 1. 範囲

- やること: §3 の2ファイルの変更と、§5 の確かめ。7a と 7b は分けて行い、それぞれの後で K9 を測る。
- やらないこと:
  - ~/.claude/CLAUDE.md の §3 に書いた行以外を変えない（報告の型・認証情報・生出力はファイルへ 等はそのまま）。
  - ~/kb・~/.claude/rules/common/・~/.claude/settings.json・フック・リポジトリのファイルを変えない。
  - 移す GAS の決まりの文言を1字も変えない（直したくなっても直さない）。
  - claude の起動は §5 に書いた回数だけ。失敗しても同じコマンドを繰り返さず BLOCKED: で報告する。

## 2. 前提の事実（Opus が 2026-10-25 に確かめた）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | ~/.claude/CLAUDE.md は 84 行の通常のファイル（symlink でも git 管理でもない） | `wc -l`・`ls -la`・/tmp/CC報告ファイル/an-gl/ |
| F2 | :12 が「## AGENTS.md 自動更新ルール」、:13 が本文、:14 が空行 | /tmp/CC報告ファイル/an-gl/claude_md_numbered.txt |
| F3 | :57 が「## GAS / clasp」、:58-73 が本文、:74 が空行、:75 が「## 生出力はファイルへ（チャットに貼らない）」 | 同上 |
| F4 | ~/.claude/rules/gas-clasp.md は無い | `ls ~/.claude/rules/` |
| F5 | GAS の4リポジトリはどれも appsscript.json を持つ。~/tcg-inventory-parser は直下にある | `find`（design §28-5） |

一つでも実物と違えば、§6 の分岐に従う。

## 3. 触るファイル（これ以外は触らない）

| ファイル | 変えるところ |
|---|---|
| ~/.claude/CLAUDE.md | 7a で :12-14 を消す。7b で（7a 後の行番号で）GAS / clasp の本文16行を案内1行に置き換える |
| ~/.claude/rules/gas-clasp.md | 7b で新しく作る |

写しの置き場: ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/（新しく作る）。生出力は /tmp/CC報告ファイル/an-s7/ に置く。

## 4. 手順

各コマンドは絶対パスで書く。Bash は毎回 cwd が元に戻るので、cd が要るときは同じコマンドの中で、cd と絶対パスと && から始める。

### 7-0 写し

1. `mkdir -p ~/CC報告ファイル-keep/agenda-nav-stage7-20261025 /tmp/CC報告ファイル/an-s7`
2. `cp -p ~/.claude/CLAUDE.md ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/CLAUDE.md.before`
3. `ls -la ~/.claude/rules/ ~/.claude/rules/common/ > ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/rules-ls.before.txt`
4. T1 を確かめる。

### 7a 段6の3行を消す

1. F2 を `sed -n 12,14p ~/.claude/CLAUDE.md` で確かめる。
2. Edit で、:12 の見出しから :14 の空行までの3行を消す。
3. T2 を確かめる。
4. §4-M のとおり K9 を測る（ラベル 7a）。

### 7b GAS / clasp を移す

1. 写しから中身を作る。`sed -n 57,73p ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/CLAUDE.md.before > /tmp/CC報告ファイル/an-s7/gas-body.txt`
2. ~/.claude/rules/gas-clasp.md を作る。中身は、次の6行の frontmatter の直後に gas-body.txt をそのまま続けたもの。`cat` でつなげて作り、手で打ち直さない。

```
---
paths:
  - "**/*.gs"
  - "**/appsscript.json"
  - "**/.clasp.json"
---
```

3. ~/.claude/CLAUDE.md で、見出し「## GAS / clasp」の下の本文16行（「- `~/.clasprc.json` はホームに1つしかない共有ファイル。」から「    新種は既存と重複しない接頭辞＋4桁連番）」まで）を、次の1行に置き換える。見出しと後ろの空行は残す。

```
- GAS・clasp の作業の決まりは ~/.claude/rules/gas-clasp.md にある（.gs・appsscript.json・.clasp.json を開くと自動で読まれる）。clasp を実行する前に必ず読む
```

4. T3・T4 を確かめる。
5. §4-M のとおり K9 を測る（ラベル 7b）。
6. T6 を確かめる。

### 4-M K9 の測り方（7a・7b で1回ずつ）

1. `git -C /Users/tanizawashingo/salesanchor worktree add --detach /Users/tanizawashingo/worktrees/salesanchor/k9-s7-LABEL origin/main`（LABEL は 7a か 7b。origin/main の sha を記録する）
2. `cd /Users/tanizawashingo/worktrees/salesanchor/k9-s7-LABEL && claude -p "/context" --no-session-persistence > /tmp/CC報告ファイル/an-s7/context-LABEL.txt 2>&1; echo rc=$?`（開始と終了の時刻も記録する）
3. 「Memory files」の合計と、MEMORY.md の行の値を書き出す。K9 は合計から MEMORY.md を引いた値。Memory files の一覧（ファイルごとの行）もそのまま報告に写す。
4. `git -C /Users/tanizawashingo/salesanchor worktree remove /Users/tanizawashingo/worktrees/salesanchor/k9-s7-LABEL` で消し、`git -C /Users/tanizawashingo/salesanchor worktree list` に残っていないことを確かめる。

## 5. 受け入れ基準と確かめ方

| 基準 | 確かめ方 | 合格 |
|---|---|---|
| T1 写しがある | `cmp ~/.claude/CLAUDE.md ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/CLAUDE.md.before; echo rc=$?`（7a の前） | rc=0 |
| T2 7a は3行だけ消えた | `diff ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/CLAUDE.md.before ~/.claude/CLAUDE.md > /tmp/CC報告ファイル/an-s7/diff-7a.txt`、`grep -c "AGENTS.md 自動更新ルール" ~/.claude/CLAUDE.md` | 差は 12-14 行の削除だけ。grep は 0 |
| T3 GAS の決まりが1字も欠けていない | `tail -n +7 ~/.claude/rules/gas-clasp.md \| diff /tmp/CC報告ファイル/an-s7/gas-body.txt - ; echo rc=$?` | rc=0 |
| T4 ほかの節は変わっていない | `diff ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/CLAUDE.md.before ~/.claude/CLAUDE.md > /tmp/CC報告ファイル/an-s7/diff-7b.txt` | 差は 12-14 行の削除と、GAS の本文16行→案内1行だけ |
| T5 K9 | 4-M の 7a・7b の値 | 7b の値を記録する（合否は Opus が判定する）。7b の Memory files の一覧に gas-clasp.md が無い |
| T6 GAS の作業では読まれる | 下の2回 | 1回目の答えに「ホームに1つしかない共有ファイル」がある。2回目には無い |

T6 のコマンド（それぞれ1回だけ）:

- 1回目: `cd /Users/tanizawashingo/tcg-inventory-parser && claude -p "appsscript.json を Read ツールで開いてください。そのあと、あなたに与えられている指示の中に clasprc についての決まりがあれば、その原文を1行そのまま引用してください。無ければ「無い」とだけ答えてください。" --allowedTools Read --no-session-persistence > /tmp/CC報告ファイル/an-s7/t6-open.txt 2>&1; echo rc=$?`
- 2回目: `cd /Users/tanizawashingo/tcg-inventory-parser && claude -p "ファイルは開かずに答えてください。あなたに与えられている指示の中に clasprc についての決まりがあれば、その原文を1行そのまま引用してください。無ければ「無い」とだけ答えてください。" --allowedTools Read --no-session-persistence > /tmp/CC報告ファイル/an-s7/t6-noopen.txt 2>&1; echo rc=$?`

~/tcg-inventory-parser の中のファイルは変えない。claude が書き込みを求めても許可しない（--allowedTools Read だけ）。

## 6. 想定の分岐

| 場面 | すること |
|---|---|
| F1〜F5 のどれかが実物と違う | 何も変えずに BLOCKED: で報告（違いの生出力を添える） |
| T2・T3・T4 のどれかが合格しない | 写しから ~/.claude/CLAUDE.md を戻し（`cp -p ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/CLAUDE.md.before ~/.claude/CLAUDE.md`）、gas-clasp.md を作っていれば消して、BLOCKED: で報告 |
| claude -p が rc≠0・出力が空 | 繰り返さず BLOCKED:。変更は戻さない（Opus が決める） |
| T6 の1回目に決まりが出ない | 変更は戻さずに NEEDS_DECISION: で報告（paths の当たり方を Opus が判断する） |
| worktree remove が失敗 | 消せなかったパスを書いて報告。`rm -rf` は使わない |

## 7. 戻し方

`cp -p ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/CLAUDE.md.before ~/.claude/CLAUDE.md` と `rm ~/.claude/rules/gas-clasp.md`（この便で作った1ファイルだけ）。

## 8. 報告

- 冒頭に受領確認の1文。
- T1〜T6 のそれぞれに、実行したコマンドと出力の要点と生出力のパスを書く。
- K9 は 7a・7b の Memory files の一覧をそのまま写す。
- 停止したときに書くこと: 止まった手順の番号・そのときの生出力のパス・変更を戻したかどうか。
- 最後の行は DONE / BLOCKED: / NEEDS_DECISION: のどれかにする。


END OF CARD
