# 実装カード 原因調べ — 練習問題で目次を開かない理由を分ける

> この文書は何か：doc-agenda-nav の原因調べの作業指示書です。段3c 後の測り直し（baseline.md「変更後」）で K10 0/20・K12 1/20 と変化が無かったため、「題の出し方」と「入口の書き方」のどちらが効いているかを、条件を1つずつ変えた少ない回数の試しで分けます。

- 設計: docs/handoff/doc-agenda-nav/design.md（§14 K10・K12）、記録: docs/handoff/doc-agenda-nav/baseline.md「変更後」の「判定と次への申し送り」
- 練習問題: docs/handoff/doc-agenda-nav/k12-tasks.md・k12/prompts.tsv（変えない）
- 対象ADR: ADR-1040
- 状態: PO の「1」（2026-10-25。開かない理由を先に確かめる）。試しは製品・入口の正本を変えない（入口の書き換えは使い捨ての写しの中だけ）。
- 危険便かどうか: 触るのは docs/handoff/ の下だけ。DANGEROUS_PATTERNS（scripts/check-process-artifacts.js:115-128）に当たらない。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装・実行・数える作業: Sonnet（model "sonnet"）
  - 記録（baseline.md）・審査の手配・マージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 原因調べの実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§7） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |

## 1. 範囲

入れるもの: §3 のファイル。

入れないもの:
- k12-tasks.md・k12/prompts.tsv・k12/runall.sh・k12/result.tsv・k12/result-after.tsv の変更。
- リポジトリの AGENTS.md・CLAUDE.md の変更（書き換えは §5-3 の使い捨ての写しの中だけ。commit しない）。
- baseline.md の変更（Opus が書く）。PR の作成（Opus が作る）。

## 2. 前提の事実（Opus が 2026-10-25 に確かめた）

- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-k10-diagnose（ブランチ release/doc-agenda-nav-k10-diagnose、起点 origin/main ec1d85d32）。
- 測る版: 4bd48fa429eece2d0b2dfd454f30f20644c2ee6b（測り直しと同じ版）。k12-tasks.md の sha256 は `820449563a838968f8c0d319fbfdc38c65ac18d848bcd2d93444ec053646dd5e`。
- 4bd48fa42 の CLAUDE.md は `@AGENTS.md` を取り込む。AGENTS.md は目次を2か所で案内する: :3「手順・詳細は目次 docs/INDEX.md からたどる。」、:44「- 手順書・作業方法は目次 `docs/INDEX.md` から章→末端の順にたどって読む」。docs/INDEX.md は取り込み（@）されておらず、開くには道具の呼び出しが要る。
- 測り直しで使った題の後ろの文（runall.sh の SUF）: 「計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。」
- count.py は回を 1・2 の2回で固定している（:13 `for k in (1,2):`）。

## 3. 触るファイル（これ以外は触らない）

- 新規: docs/handoff/doc-agenda-nav/k12/diag.sh
- 新規: docs/handoff/doc-agenda-nav/k12/suffix-plan.txt（測り直しと同じ文）
- 新規: docs/handoff/doc-agenda-nav/k12/suffix-open.txt（「だけ」を外した文）
- 新規: docs/handoff/doc-agenda-nav/k12/agents-line44-strong.txt（強い書き方の1行）
- 変更: docs/handoff/doc-agenda-nav/k12/count.py（回の数を引数で受ける）
- 新規: docs/handoff/doc-agenda-nav/k12/diag-B.tsv・diag-C.tsv・diag-D.tsv（§5 の結果を写す）
- 変更: このカード（§8 の報告欄に追記するだけ）

## 4. 作り方

### 4-1. k12/diag.sh を次の全文で作る（Write）

```
#!/bin/bash
# usage: diag.sh OUT_DIR COPY_DIR SUFFIX_FILE
#   OUT_DIR: 生出力の置き場（新しい空のディレクトリ）
#   COPY_DIR: 測る版の detached な写し
#   SUFFIX_FILE: 題の後ろに付ける文（1行）
# 各題を1回ずつ解かせる。写しの git status が開始時と同じであることを各回の後に確かめる
D="$1"; W="$2"; S="$3"
[ -n "$D" ] && [ -n "$W" ] && [ -f "$S" ] || { echo "usage: diag.sh OUT_DIR COPY_DIR SUFFIX_FILE" >&2; exit 1; }
P="$(cd "$(dirname "$0")" && pwd)/prompts.tsv"
SUF="$(cat "$S")"
cd "$W" || exit 1
s0=$(git -C "$W" status --porcelain)
while IFS=$'\t' read -r t p; do
 perl -e 'alarm 600; exec @ARGV' claude -p "${p}${SUF}" --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 1 --no-session-persistence --permission-prompts none < /dev/null > "$D/$t-1.jsonl" 2>"$D/$t-1.err"
 echo "$t-1 exit=$?" >> "$D/exits.txt"
 s=$(git -C "$W" status --porcelain)
 if [ "$s" != "$s0" ]; then echo "DIRTY after $t-1: $s" >> "$D/DIRTY.txt"; exit 2; fi
done < "$P"
echo ALLDONE >> "$D/exits.txt"
```

（claude の引数は runall.sh と同じ。違いは、題の後ろの文をファイルで受けること・各題1回・汚れの判定を開始時の状態との比較にしたこと）

### 4-2. 文のファイル3本を作る（Write。各1行、末尾に改行1つ）

- k12/suffix-plan.txt: `計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。`
- k12/suffix-open.txt: `日本語で答えてください。ファイルの変更・commit・push はしないでください。`
- k12/agents-line44-strong.txt: ``- 手順や作業方法を答える・計画する前に、必ず目次 `docs/INDEX.md` を開き、章→末端の順にたどって該当する手順書を読む（記憶や推測だけで答えない）``

### 4-3. k12/count.py を2か所直す（Edit）

- :2 `D=sys.argv[1]` を次の2行に置き換える:
  ```
  D=sys.argv[1]
  R=int(sys.argv[2]) if len(sys.argv)>2 else 2
  ```
- :13 `  for k in (1,2):` を `  for k in range(1,R+1):` に置き換える。

ほかの行は変えない（引数を1つだけ渡したときの動きは今と同じ）。

## 5. 確かめ方と実行（生出力は /tmp/CC報告ファイル/an-diag/ に保存。各コマンドの rc を残す）

条件（題は10題とも同じ・各1回）:

| 条件 | 題の後ろの文 | 入口（写しの AGENTS.md:44） |
|---|---|---|
| A（測り直し済み。今回は実行しない） | suffix-plan.txt | そのまま |
| B | suffix-open.txt | そのまま |
| C | suffix-plan.txt | agents-line44-strong.txt に置き換え |
| D | suffix-open.txt | agents-line44-strong.txt に置き換え |

判定の決まり（実行前に Opus が固定。数えるのは K10＝INDEX 列の合計、各条件10回中）:
- B が5回以上 → 題の出し方（「計画だけ」）が主な原因。
- C が5回以上 → 入口の書き方を強めれば動く。
- B・C とも4回以下で D が5回以上 → 両方そろって初めて動く。
- B・C・D とも2回以下 → どちらも主な原因ではない。別の要因を次に調べる。
- 上のどれにも当たらない（3〜4回が混じる）→ 決めずに結果を PO に示す。

- 5-1: `bash -n docs/handoff/doc-agenda-nav/k12/diag.sh` と `python3 -m py_compile docs/handoff/doc-agenda-nav/k12/count.py` が rc=0。
- 5-2（数える道具が変わっていないことの確かめ）: `cp -R /tmp/CC報告ファイル/an-measure-after/run /tmp/CC報告ファイル/an-diag/re-run` の後、`python3 docs/handoff/doc-agenda-nav/k12/count.py /tmp/CC報告ファイル/an-diag/re-run` の最後の行が `K12 1 K10 0 cost 2.8805707`、`diff /tmp/CC報告ファイル/an-diag/re-run/result.tsv docs/handoff/doc-agenda-nav/k12/result-after.tsv` が空。元の run には書き込まない。
- 5-3（写しの用意）: 2つ作る。
  - `git worktree add --detach /Users/tanizawashingo/worktrees/salesanchor/k10-diag-plain 4bd48fa429eece2d0b2dfd454f30f20644c2ee6b`
  - `git worktree add --detach /Users/tanizawashingo/worktrees/salesanchor/k10-diag-strong 4bd48fa429eece2d0b2dfd454f30f20644c2ee6b`
  - 両方で `shasum -a 256 docs/handoff/doc-agenda-nav/k12-tasks.md` が §2 の値、`test -e docs/INDEX.md` が rc=0、`git status --porcelain` が空。
  - k10-diag-strong だけ、AGENTS.md の44行目を置き換える。先に `sed -n 44p AGENTS.md` が §2 の :44 の文と完全に同じことを確かめ、次を実行する（作業場所のファイルを読む）:
    `python3 -c "import sys;p='/Users/tanizawashingo/worktrees/salesanchor/k10-diag-strong/AGENTS.md';L=open(p).read().split('\n');L[43]=open(sys.argv[1]).read().rstrip('\n');open(p,'w').write('\n'.join(L))" /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-k10-diagnose/docs/handoff/doc-agenda-nav/k12/agents-line44-strong.txt`
    その後 `git -C /Users/tanizawashingo/worktrees/salesanchor/k10-diag-strong diff` を保存し、差が44行目の1行だけであること。
  - `claude --version` を保存。
- 5-4（実行。B→C→D の順に1つずつ。どれも Bash の run_in_background で実行し、sleep で待たず終了の知らせを待つ。1条件10回で30分ほどの見込み）:
  - B: `mkdir -p /tmp/CC報告ファイル/an-diag/B` → `bash docs/handoff/doc-agenda-nav/k12/diag.sh /tmp/CC報告ファイル/an-diag/B /Users/tanizawashingo/worktrees/salesanchor/k10-diag-plain docs/handoff/doc-agenda-nav/k12/suffix-open.txt`
  - C: `mkdir -p /tmp/CC報告ファイル/an-diag/C` → `bash docs/handoff/doc-agenda-nav/k12/diag.sh /tmp/CC報告ファイル/an-diag/C /Users/tanizawashingo/worktrees/salesanchor/k10-diag-strong docs/handoff/doc-agenda-nav/k12/suffix-plan.txt`
  - D: `mkdir -p /tmp/CC報告ファイル/an-diag/D` → `bash docs/handoff/doc-agenda-nav/k12/diag.sh /tmp/CC報告ファイル/an-diag/D /Users/tanizawashingo/worktrees/salesanchor/k10-diag-strong docs/handoff/doc-agenda-nav/k12/suffix-open.txt`
  - SUFFIX_FILE は作業場所からの相対パスで渡すので、各実行は作業場所の cd から始める。各条件の後に exits.txt の最後が ALLDONE、DIRTY.txt が無いこと。
- 5-5（数える）: B・C・D それぞれについて（例は B。C・D は B の文字を置き換える） `python3 docs/handoff/doc-agenda-nav/k12/count.py /tmp/CC報告ファイル/an-diag/B 1` を実行して出力を保存し、`cp /tmp/CC報告ファイル/an-diag/B/result.tsv docs/handoff/doc-agenda-nav/k12/diag-B.tsv`。
- 5-6（片付け）: k10-diag-strong は `git -C /Users/tanizawashingo/worktrees/salesanchor/k10-diag-strong checkout -- AGENTS.md` で戻し、`git status --porcelain` が空になってから、`git worktree remove /Users/tanizawashingo/worktrees/salesanchor/k10-diag-plain` と `git worktree remove /Users/tanizawashingo/worktrees/salesanchor/k10-diag-strong`（--force は付けない。失敗したら BLOCKED:）。
- 5-7: §3 のファイルを commit（末尾に空行＋`Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ 通常の `git push -u origin release/doc-agenda-nav-k10-diagnose`。

## 6. 分岐ごとの対処

- 5-2 の最後の行が違う・diff が空でない → 出力を貼って BLOCKED:（実行に進まない）。
- 5-3 の sha256 が違う・INDEX が無い・44行目が §2 と違う・置き換え後の差が1行でない → BLOCKED:。
- claude が引数の誤りで止まる（exit が 0 以外で .err に usage やエラー文）→ 最初の1回で止め、.err の全文を貼って BLOCKED:。引数を自分で変えない。
- DIRTY.txt が出来た → 止まった条件・題と中身を貼って BLOCKED:。写しを直さない。
- 見張り（hook）に止められた → 言い換えず、作業を停止し、止まった手順と理由の原文を報告する。
- どの分岐でも、停止したら §7 の形で BLOCKED: を Opus に報告する（停止時の報告経路）。

## 7. 報告

最後の報告は DONE / BLOCKED: / NEEDS_DECISION: のいずれかで始め、次を書く: 新しい HEAD の sha40、5-1〜5-7 の rc と結果、条件ごとの count.py の最後の行（K12・K10・cost）、diag-B/C/D.tsv の全文、claude の版、保存したファイルのパス一覧。解釈・推測は書かない。

## 8. 報告欄（担当が追記）

本報告はカード doc-agenda-nav 原因調べの実行結果である。
- 5-1 rc=0/0、5-2 最後の行 `K12 1 K10 0 cost 2.8805707`・diff 空、5-3 sha256 一致・INDEX あり・差は44行目1行のみ、claude 2.1.310
- B: K12 1 K10 1 cost 1.8352219 / C: K12 0 K10 1 cost 1.7058189 / D: K12 3 K10 5 cost 2.1422289（全条件 ALLDONE・DIRTY なし）
- 結果は k12/diag-B.tsv・diag-C.tsv・diag-D.tsv、生出力は /tmp/CC報告ファイル/an-diag/

END OF CARD
