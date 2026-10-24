# 実装カード 入口の案内を強める — 変更前と変更後を同じ条件で20回ずつ測る

> この文書は何か：doc-agenda-nav の作業指示書です。原因調べ（baseline.md「原因調べ」）で、入口の強い書き方と「だけ」を外した題の両方がそろったときだけ、目次を開く回が増えました（10回中4〜5回）。そこで入口 AGENTS.md:44 を強い書き方に正式に変えます。題の出し方と数え方も改めます。そのうえで、変更前と変更後を同じ条件で20回ずつ測ります。

- 設計: docs/handoff/doc-agenda-nav/design.md（§14 K10・K12）、記録: docs/handoff/doc-agenda-nav/baseline.md「原因調べ」
- 練習問題: docs/handoff/doc-agenda-nav/k12-tasks.md・k12/prompts.tsv（題の文は変えない）
- 対象ADR: ADR-1040
- 状態: PO の「1」（2026-10-25）。選んだ選択肢の原文: 「入口の案内文を強い書き方に正式に変え、練習問題の頼み方も実際の依頼に近い形にします。そのうえで、変える前と後を同じ条件で20回ずつ測り直します。数え方も、本当に開いたときだけ数えるように直します。」
- 危険便かどうか: 触るのは AGENTS.md と docs/handoff/ の下だけ。migrations/・deploy.yml・本番 scripts/ を含まない。DANGEROUS_PATTERNS（scripts/check-process-artifacts.js:115-128）に当たらない。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装・実行・数える作業: Sonnet（model "sonnet"）
  - 記録（baseline.md）・審査の手配・PR・マージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 入口の案内を強める の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§7） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |

## 1. 範囲

入れるもの: §3 のファイル。

入れないもの:
- k12/prompts.tsv・k12/result.tsv・k12/result-after.tsv・k12/diag-*.tsv・k12/diag.sh の変更。
- AGENTS.md の44行目以外の行。CLAUDE.md・docs/INDEX.md の変更。
- baseline.md の変更（Opus が書く）。PR の作成（Opus が作る）。

## 2. 前提の事実（Opus が 2026-10-25 に確かめた）

- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-entry-strong（ブランチ release/doc-agenda-nav-entry-strong、起点 origin/main 6ec23c2df738c6e1dd6f892a247c6ad401f780bb）。
- AGENTS.md:44 の今の文: ``- 手順書・作業方法は目次 `docs/INDEX.md` から章→末端の順にたどって読む``
- 置き換える文は k12/agents-line44-strong.txt の1行（原因調べの C・D で使ったものと同じ）: ``- 手順や作業方法を答える・計画する前に、必ず目次 `docs/INDEX.md` を開き、章→末端の順にたどって該当する手順書を読む（記憶や推測だけで答えない）``
- AGENTS.md は53行（`wc -l`。当初54と書いたのは誤り。担当の BLOCKED: で訂正 2026-10-25）。行数の上限は80（frontend/scripts/check-claude-size.js:25）。1行の置き換えなので行数は変わらない。
- k12/prompts.tsv の sha256 は `4259f55d81855d006763b35aca614277d0d27eb98e23cbeceb499d03fadf729d`、k12-tasks.md の sha256 は `820449563a838968f8c0d319fbfdc38c65ac18d848bcd2d93444ec053646dd5e`（§4-4 で k12-tasks.md を変えるので、変えた後は値が変わる）。
- 変更前の版: 8b54381427c542ff470959753a4b0eb6c3062823（baseline.md で「変更前」とした版。docs/INDEX.md は無い）。
- k12/runall.sh は題の後ろの文を :8 の `SUF="計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。"` で固定している。各題2回。
- count.py は、道具の呼び出しの種類を区別せずに数える（:25-29）。そのため、計画を書き出す Write の中身に `docs/INDEX.md` の文字があるだけでも「開いた」に入る（baseline.md「原因調べ」）。読む道具だけで数えた値（原因調べ時の /tmp/CC報告ファイル/an-diag/strict-out.txt）は次のとおり。
  - an-measure-after/run: K12 1・K10 0
  - an-diag/D: K12 3・K10 4

## 3. 触るファイル（これ以外は触らない）

- 変更: AGENTS.md（44行目の1行だけ）
- 変更: docs/handoff/doc-agenda-nav/k12/runall.sh（題の後ろの文をファイルでも受ける）
- 変更: docs/handoff/doc-agenda-nav/k12/count.py（読む道具だけで数える方式を足す）
- 変更: docs/handoff/doc-agenda-nav/k12-tasks.md（2026-10-25 の改定の節を末尾に足す）
- 新規: docs/handoff/doc-agenda-nav/k12/result-v2-before.tsv・result-v2-after.tsv（§5 の結果を写す）
- 変更: このカード（§8 の報告欄に追記するだけ）

## 4. 作り方

### 4-1. AGENTS.md の44行目を置き換える（Edit）

§2 の今の文を、§2 の置き換える文に変える。ほかの行は変えない。

### 4-2. k12/runall.sh を2か所直す（Edit）

- :2 `# usage: runall.sh OUT_DIR COPY_DIR` を次の2行に置き換える:
  ```
  # usage: runall.sh OUT_DIR COPY_DIR [SUFFIX_FILE]
  #   SUFFIX_FILE: 題の後ろに付ける文（1行）。省くと下の SUF を使う
  ```
- :8 の SUF の行の直後に、次の1行を足す:
  ```
  [ -n "$3" ] && SUF="$(cat "$3")"
  ```

ほかの行は変えない（引数を2つだけ渡したときの動きは今と同じ）。

### 4-3. k12/count.py を2か所直す（Edit）

- :3 `R=int(sys.argv[2]) if len(sys.argv)>2 else 2` の直後に、次の1行を足す:
  ```
  M=sys.argv[3] if len(sys.argv)>3 else 'any'
  ```
- `n+=1; s=json.dumps(c.get('input'),ensure_ascii=False)` の行の直後に、同じ字下げで次の1行を足す:
  ```
  if M=='read' and c.get('name') not in ('Read','Bash','Grep','Glob'): continue
  ```

ほかの行は変えない（引数を1つか2つだけ渡したときの動きは今と同じ。`read` を渡すと、Write・Edit などの書く道具の中身は数えない。tool_use数の列はこれまでどおり全部を数える）。

### 4-4. k12-tasks.md の末尾に次の節を足す（Edit。既存の行は変えない）

```

## 2026-10-25 の改定（PO「1」2026-10-25）

この日以降の測定（k12/result-v2-*.tsv）は次の条件に変える。前の測定（result.tsv・result-after.tsv）は上の条件のまま残す。
- 共通の末尾文: 「日本語で答えてください。ファイルの変更・commit・push はしないでください。」（k12/suffix-open.txt。実際の依頼に近づけるため「計画だけ」を外した）
- 「開いた」の定義: 読む道具（Read・Bash・Grep・Glob）の tool_use の input に、正解の集合のどれかのパスが含まれていれば 1。Write・Edit などの書く道具は数えない（`count.py <dir> 2 read`）。K10 も同じ数え方。
- 実行: `runall.sh <OUT_DIR> <COPY_DIR> docs/handoff/doc-agenda-nav/k12/suffix-open.txt`。claude の引数・各題2回は上と同じ。
```

## 5. 確かめ方と実行（生出力は /tmp/CC報告ファイル/an-v2/ に保存。各コマンドの rc を残す）

判定の決まり（実行前に Opus が固定。数えるのは `count.py <dir> 2 read` の最後の行。各20回中）:
- 変更後の K10 が10以上 → K10 合格。9以下 → K10 未達。
- 変更後の K12 が10以上 → K12 合格。9以下 → K12 未達。
- 変更前と変更後の差は数字をそのまま記録する。合否は上の2つだけで決める。

- 5-1: `bash -n docs/handoff/doc-agenda-nav/k12/runall.sh` と `python3 -m py_compile docs/handoff/doc-agenda-nav/k12/count.py` が rc=0。`wc -l < AGENTS.md` が 53。`git diff -U0 origin/main -- AGENTS.md` を保存し、差が44行目の1行だけであること。`node frontend/scripts/check-claude-size.js` の rc を保存する（0 であること）。
- 5-2（数える道具の確かめ。元の生出力には書き込まない）:
  - `mkdir -p /tmp/CC報告ファイル/an-v2` → `cp -R /tmp/CC報告ファイル/an-measure-after/run /tmp/CC報告ファイル/an-v2/chk-a`
    - `python3 docs/handoff/doc-agenda-nav/k12/count.py /tmp/CC報告ファイル/an-v2/chk-a` の最後の行が `K12 1 K10 0 cost 2.8805707` であること。
    - `diff /tmp/CC報告ファイル/an-v2/chk-a/result.tsv docs/handoff/doc-agenda-nav/k12/result-after.tsv` が空であること。
    - `python3 docs/handoff/doc-agenda-nav/k12/count.py /tmp/CC報告ファイル/an-v2/chk-a 2 read` の最後の行が `K12 1 K10 0 cost 2.8805707` であること。
  - `cp -R /tmp/CC報告ファイル/an-diag/D /tmp/CC報告ファイル/an-v2/chk-d` → `python3 docs/handoff/doc-agenda-nav/k12/count.py /tmp/CC報告ファイル/an-v2/chk-d 1 read` の最後の行が `K12 3 K10 4 cost 2.1422289` であること。
- 5-3: 4-1〜4-4 のファイルを commit（末尾に空行＋`Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ 通常の `git push -u origin release/doc-agenda-nav-entry-strong`。この commit の sha40 を「変更後の版」とし、報告に書く。
- 5-4（写しの用意）: 2つ作る。
  - `git worktree add --detach /Users/tanizawashingo/worktrees/salesanchor/k12v2-before 8b54381427c542ff470959753a4b0eb6c3062823`
  - `git worktree add --detach /Users/tanizawashingo/worktrees/salesanchor/k12v2-after` に続けて 5-3 の sha40 を渡す
  - k12v2-before: `test -e docs/INDEX.md` の rc が 0 以外、`git status --porcelain` が空。
  - k12v2-after: `sed -n 44p AGENTS.md` が §2 の置き換える文と完全に同じ、`test -e docs/INDEX.md` が rc=0、`git status --porcelain` が空。
  - `claude --version` を保存。
- 5-5（実行。変更前→変更後の順に1つずつ。どれも作業場所の cd から始め、Bash の run_in_background で実行し、sleep で待たず終了の知らせを待つ。1つ20回で1時間ほどの見込み）:
  - 変更前: `mkdir -p /tmp/CC報告ファイル/an-v2/before` → `bash docs/handoff/doc-agenda-nav/k12/runall.sh /tmp/CC報告ファイル/an-v2/before /Users/tanizawashingo/worktrees/salesanchor/k12v2-before docs/handoff/doc-agenda-nav/k12/suffix-open.txt`
  - 変更後: `mkdir -p /tmp/CC報告ファイル/an-v2/after` → `bash docs/handoff/doc-agenda-nav/k12/runall.sh /tmp/CC報告ファイル/an-v2/after /Users/tanizawashingo/worktrees/salesanchor/k12v2-after docs/handoff/doc-agenda-nav/k12/suffix-open.txt`
  - 各実行の開始時刻と終了時刻（`date '+%Y-%m-%d %H:%M:%S %Z'`）を保存する。各実行の後に exits.txt の最後が ALLDONE、DIRTY.txt が無いこと。
- 5-6（数える）: before・after それぞれについて（例は before）、次を実行して出力を保存する。
  - `python3 docs/handoff/doc-agenda-nav/k12/count.py /tmp/CC報告ファイル/an-v2/before 2 read` → `cp /tmp/CC報告ファイル/an-v2/before/result.tsv docs/handoff/doc-agenda-nav/k12/result-v2-before.tsv`
  - 参考として `count.py ... 2`（any）も実行し、出力だけを /tmp/CC報告ファイル/an-v2/count-any-before.txt に保存する（result.tsv は上書きされるので、read の後に cp を済ませてから実行する）。
- 5-7（片付け）: `git worktree remove /Users/tanizawashingo/worktrees/salesanchor/k12v2-before` と `git worktree remove /Users/tanizawashingo/worktrees/salesanchor/k12v2-after`。--force は付けない。失敗したら BLOCKED:。
- 5-8: result-v2-before.tsv・result-v2-after.tsv と、このカードの §8 を commit（署名は 5-3 と同じ）→ 通常の push。

## 6. 分岐ごとの対処

- 5-1・5-2 のどれかが期待と違う → 出力を貼って BLOCKED:（commit・実行に進まない）。
- 5-4 の確かめが1つでも違う → BLOCKED:。
- claude が引数の誤りで止まる（exit が 0 以外で .err に usage やエラー文）→ 最初の1回で止め、.err の全文を貼って BLOCKED:。引数を自分で変えない。
- DIRTY.txt が出来た → 止まった版・題と中身を貼って BLOCKED:。写しを直さない。
- check-claude-size.js が引数を要求して rc≠0 で止まる → 出力を貼って報告に書き、続ける（CI で同じ検査が走る）。それ以外の理由の rc≠0 は BLOCKED:。
- 見張り（hook）に止められた → 言い換えず、作業を停止し、止まった手順と理由の原文を報告する。
- どの分岐でも、停止したら §7 の形で BLOCKED: を Opus に報告する（停止時の報告経路）。

## 7. 報告

最後の報告は DONE / BLOCKED: / NEEDS_DECISION: のいずれかで始め、次を書く: 5-3 の sha40、新しい HEAD の sha40、5-1〜5-8 の rc と結果、before・after それぞれの count.py の最後の行（read と any の両方）、result-v2-before.tsv・result-v2-after.tsv の全文、claude の版、各実行の開始・終了時刻、保存したファイルのパス一覧。解釈・推測は書かない。

## 8. 報告欄（担当が追記）

- 実行結果（Sonnet、2026-10-25）: 変更後の版 06fb277192cdc471c84b230a12e5627cea979d7d。変更前 02:43:29〜03:02:14 JST、変更後 03:02:36〜03:21:09 JST。claude 2.1.310。
- count.py の最後の行（read）: 変更前 K12 4 K10 0 / 変更後 K12 13 K10 7。any も同じ値。
- 生出力: /tmp/CC報告ファイル/an-v2/（before・after・count-*.txt）。結果表: k12/result-v2-before.tsv・result-v2-after.tsv。

END OF CARD
