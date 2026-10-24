# 実装カード 測り直し — K10・K12 を段3c マージ後の版で測る

> この文書は何か：doc-agenda-nav の測り直しの作業指示書です。練習問題の実行と数える道具（k12/runall.sh・k12/count.py）の決め打ちを外し、段3c マージ後の版で練習問題20回を実行して K10（目次を開いた回数）と K12（必要な手順書まで開いた回数）を数えます。

- 設計: docs/handoff/doc-agenda-nav/design.md（§8 段0c、§14 K10・K12）、測り方の正本: docs/handoff/doc-agenda-nav/baseline.md「手順（変更後に同じ条件で測る）」の2
- 練習問題: docs/handoff/doc-agenda-nav/k12-tasks.md（変えない）
- 対象ADR: ADR-1040
- 状態: 測り方は PO 承認済み（2026-10-23 の「1」）。この測り直しは PO の「1」（2026-10-24。次は効果を測る）。
- 危険便かどうか: 触るのは docs/handoff/ の下だけ。DANGEROUS_PATTERNS（scripts/check-process-artifacts.js:115-128）に当たらない。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装・実行・数える作業: Sonnet（model "sonnet"）
  - 記録（baseline.md）・審査の手配・マージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 測り直しの実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§7） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |

## 1. 範囲

入れるもの: §3 のファイル。

入れないもの:
- k12-tasks.md・k12/prompts.tsv・k12/result.tsv（変更前の記録）の変更。
- baseline.md の変更（Opus が書く）。
- PR の作成（Opus が作る）。

## 2. 前提の事実（Opus が 2026-10-24 に確かめた）

- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-measure-after（ブランチ release/doc-agenda-nav-measure-after、起点 4bd48fa429eece2d0b2dfd454f30f20644c2ee6b＝段3c-2 PR #4710 のマージ後の origin/main）。
- k12-tasks.md の sha256 は origin/main で `820449563a838968f8c0d319fbfdc38c65ac18d848bcd2d93444ec053646dd5e`（baseline.md:110 と同じ）。
- 決め打ち（k12/runall.sh）: :3 出力先が /tmp/CC報告ファイル/an-stage1/k12/run 固定、:4・:6 写しの場所が固定、:9 T1 の1回目を飛ばす、:14 題を出力先の prompts.tsv から読む。
- 決め打ち（k12/count.py）: :2 出力先が固定、:11 T1-1 の終了コードを '0' と書き込む。
- 変更前の生出力 /tmp/CC報告ファイル/an-stage1/k12/run は在る（48ファイル）。
- この Mac の claude は 2.1.310（変更前の測定は 2.1.309）。`claude --help` に --max-budget-usd・--no-session-persistence・--permission-prompts が在る。

## 3. 触るファイル（これ以外は触らない）

- 変更: docs/handoff/doc-agenda-nav/k12/runall.sh
- 変更: docs/handoff/doc-agenda-nav/k12/count.py
- 新規: docs/handoff/doc-agenda-nav/k12/result-after.tsv（§5-4 の結果を写す）
- 変更: このカード（§8 の報告欄に追記するだけ）

## 4. 作り方

### 4-1. k12/runall.sh を次の全文に置き換える（Write）

```
#!/bin/bash
# usage: runall.sh OUT_DIR COPY_DIR
#   OUT_DIR: 生出力の置き場（新しい空のディレクトリ）
#   COPY_DIR: 測る版の detached な写し
D="$1"; W="$2"
[ -n "$D" ] && [ -n "$W" ] || { echo "usage: runall.sh OUT_DIR COPY_DIR" >&2; exit 1; }
P="$(cd "$(dirname "$0")" && pwd)/prompts.tsv"
SUF="計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。"
cd "$W" || exit 1
for k in 1 2; do
 while IFS=$'\t' read -r t p; do
  perl -e 'alarm 600; exec @ARGV' claude -p "${p}${SUF}" --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 1 --no-session-persistence --permission-prompts none < /dev/null > "$D/$t-$k.jsonl" 2>"$D/$t-$k.err"
  echo "$t-$k exit=$?" >> "$D/exits.txt"
  s=$(git -C "$W" status --porcelain)
  if [ -n "$s" ]; then echo "DIRTY after $t-$k: $s" >> "$D/DIRTY.txt"; exit 2; fi
 done < "$P"
done
echo ALLDONE >> "$D/exits.txt"
```

（claude の引数は変更前と同じ。`< /dev/null` は題の一覧を claude が読み込まないための追加で、渡す題は変わらない）

### 4-2. k12/count.py を2か所直す（Edit）

- :1 `import json,os` を `import json,os,sys` に置き換える。
- :2 `D='/tmp/CC報告ファイル/an-stage1/k12/run'` を `D=sys.argv[1]` に置き換える。
- :11 `exits['T1-1']='0'` の行を消す。

ほかの行は変えない。

## 5. 確かめ方と実行（生出力は /tmp/CC報告ファイル/an-measure-after/ に保存。各コマンドの rc を残す）

- 5-1: `bash -n docs/handoff/doc-agenda-nav/k12/runall.sh` と `python3 -m py_compile docs/handoff/doc-agenda-nav/k12/count.py` が rc=0。
- 5-2（数える道具が変わっていないことの確かめ）: `cp -R /tmp/CC報告ファイル/an-stage1/k12/run /tmp/CC報告ファイル/an-measure-after/old-run` の後、`python3 docs/handoff/doc-agenda-nav/k12/count.py /tmp/CC報告ファイル/an-measure-after/old-run` を実行。最後の行が `K12 1 K10 0 cost 2.8363...` で始まり、`diff /tmp/CC報告ファイル/an-measure-after/old-run/result.tsv docs/handoff/doc-agenda-nav/k12/result.tsv` の差が T1-1 の行の終了コードの列（`?` と `0`）だけであること。元の /tmp/CC報告ファイル/an-stage1/k12/run には書き込まない。
- 5-3（写しの用意）: `git worktree add --detach /Users/tanizawashingo/worktrees/salesanchor/k12-measure-after 4bd48fa429eece2d0b2dfd454f30f20644c2ee6b`。写しで `test -e docs/INDEX.md` が rc=0、`shasum -a 256 docs/handoff/doc-agenda-nav/k12-tasks.md` が §2 の値と同じ、`git status --porcelain` が空。`claude --version` を保存。
- 5-4（実行）: `mkdir -p /tmp/CC報告ファイル/an-measure-after/run` の後、`bash docs/handoff/doc-agenda-nav/k12/runall.sh /tmp/CC報告ファイル/an-measure-after/run /Users/tanizawashingo/worktrees/salesanchor/k12-measure-after` を Bash の run_in_background で実行（20回で1時間ほどかかる見込み。sleep で待たず、終了の知らせを待つ）。終わったら exits.txt の最後が ALLDONE、DIRTY.txt が無いこと。
- 5-5（数える）: `python3 docs/handoff/doc-agenda-nav/k12/count.py /tmp/CC報告ファイル/an-measure-after/run` を実行し、出力を保存。`cp /tmp/CC報告ファイル/an-measure-after/run/result.tsv docs/handoff/doc-agenda-nav/k12/result-after.tsv`。
- 5-6（片付け）: `git worktree remove /Users/tanizawashingo/worktrees/salesanchor/k12-measure-after`（--force は付けない。写しが汚れていて失敗したら BLOCKED:）。
- 5-7: §3 のファイルを commit（末尾に空行＋`Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ 通常の `git push -u origin release/doc-agenda-nav-measure-after`。

## 6. 分岐ごとの対処

- 5-2 の差が T1-1 の終了コードの列以外にも出た → 出力を貼って BLOCKED:（実行に進まない）。
- 5-3 の sha256 が違う・INDEX が無い → BLOCKED:。
- claude が引数の誤りで止まる（exit が 0 以外で .err に usage やエラー文）→ 最初の1回で止め、.err の全文を貼って BLOCKED:。引数を自分で変えない。
- DIRTY.txt が出来た → 止まった題と中身を貼って BLOCKED:。写しを直さない。
- 見張り（hook）に止められた → 言い換えず、作業を停止し、止まった手順と理由の原文を報告する。
- どの分岐でも、停止したら §7 の形で BLOCKED: を Opus に報告する（停止時の報告経路）。

## 7. 報告

最後の報告は DONE / BLOCKED: / NEEDS_DECISION: のいずれかで始め、次を書く: 新しい HEAD の sha40、5-1〜5-7 の rc と結果、count.py の最後の行（K12・K10・cost）、result-after.tsv の全文、claude の版、保存したファイルのパス一覧。解釈・推測は書かない。

## 8. 報告欄（担当が追記）

END OF CARD
