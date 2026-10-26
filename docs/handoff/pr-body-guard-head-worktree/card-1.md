# card-1: pr-body-guard が --head／PR 番号から worktree を見つける

状態: Opus 作成・自己審査済み（2026-10-27）。PO 承認 2026-10-27「1」。設計: [design.md](design.md)。

## 1. 触るファイル（これ以外は触らない）
1. `docs/handoff/conversation-consent/hooks/pr-body-guard.sh`
2. `scripts/dev/test-agent-hooks.sh`

## 2. 変更
### 2-1. pr-body-guard.sh
- `CMD_CD` で CWD を補正するブロック（いまの `:88-99`、`if [[ -n "$CMD_CD" ]] && [[ -d "$CMD_CD" ]]; then CWD="$CMD_CD"; fi`）の**直後**に、次のブロックを足す。既存の行は変えない。
- 条件: `CMD_CD` が空のときだけ動く。
- ブランチ名: `python3 -c` で COMMAND を `shlex.split` し（失敗したら空）、`gh` `pr` `create` の並びのあとの `--head <b>`／`--head=<b>`／`-H <b>` を取る。`gh` `pr` `edit` の並びなら、`edit` の次の `-` で始まらない語を PR の指定とし、`gh pr view <指定> --json headRefName -q .headRefName`（命令文に `-R`/`--repo` の値があれば `-R <値>` を足す）を python の `subprocess.run(..., timeout=10)` で引く。失敗・時間切れ・空は「ブランチなし」。`gh` と `pr` のあいだの `-R <値>`／`--repo <値>` は飛ばして並びを見る。
- worktree: ブランチがあれば `git -C "$CWD" worktree list --porcelain` を読み、`worktree <パス>` の組のうち `branch refs/heads/<b>` と完全一致する組を集める。ちょうど 1 つでディレクトリが在るときだけ `CWD="<パス>"` にし、標準エラーへ `pr-body-guard: 作業場所を <b> の worktree <パス> にしました` を出す。それ以外は何もしない。
- `set -euo pipefail` の下で、このブロックの失敗がフック全体を落とさないこと（`|| true` 等）。落ちたときは何もしない側。

### 2-2. test-agent-hooks.sh
- 既存の試験の作法（`t` 行・`run_hook_err` など）に合わせて、K1〜K3 の 3 件を足す（design.md §6）。
  - 一時ディレクトリに git repo を作り、ブランチ `release/t-headwt` の worktree を足し、その worktree に `docs/handoff/t/recon.md` と `design.md` を置く。
  - K1: cwd を本体側にして `gh pr create --head release/t-headwt --title t --body-file <一時の本文>` を pr-body-guard に渡すと、標準エラーに「作業場所を release/t-headwt の worktree」が含まれる。
  - K2: `--head no-such-branch` では含まれない。
  - K3: `cd <本体の絶対パス> && gh pr create --head release/t-headwt ...` では含まれない。
  - 判定は標準エラーの行だけで行い、終了コードは問わない（本文の検証の合否は今回の対象外）。
  - `gh pr edit` の経路はネットワークが要るので試験にしない（本物の K5 で確かめる）。

## 3. 確かめること（報告に生の結果を書く）
1. `bash -n docs/handoff/conversation-consent/hooks/pr-body-guard.sh` が exit 0
2. `bash scripts/dev/test-agent-hooks.sh` の最後の集計（PASS/FAIL 数）。Mac の ~/.claude を前提にして動かない試験があれば、どれがなぜかを書く（直さない）
3. `git diff origin/main...HEAD --name-only` が §1 の 2 ファイルと、この便の文書（docs/handoff/pr-body-guard-head-worktree/ の 3 つ）と台帳だけ

## 4. 想定される分岐
- 試験の作法上、cwd を本体にして渡す手段が無い → 止めて NEEDS_DECISION で報告する
- 既存の試験が直す前から FAIL している → 直さずに、直す前の数を書いて報告する
- shlex で読めない命令（引用符が閉じない等）→ ブランチなし（何もしない）
