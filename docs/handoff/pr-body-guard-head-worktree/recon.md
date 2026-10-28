# recon: PR 本文の見張りが作業場所を見つけられない件（pr-body-guard-head-worktree）

作成: 2026-10-27 Opus。根拠は origin/main 995973c18 と手元の実物。

## 既存 ADR の検索
- ADR-1033（会話での同意）: 手元の見張り5本の試作の正本を `docs/handoff/conversation-consent/hooks/` に置き、PO が `po-apply-consent.sh --update` で本物へ入れ替える（`docs/handoff/conversation-consent/po-apply-consent.sh:1-6`）。
- ADR-1045（社外秘の原文の見張り confidential-quote-guard）: gh の本文の操作は「決まった形だけ通す。命令文から作業場所を推し量らない」（`docs/handoff/confidential-quote-guard/design.md:57`・`:78`）。
- `docs/specs/local-hooks-ssot/README.md`: 手元の見張りは repo の正本で管理する。

## 観測事実
1. 本物 ~/.claude/scripts/pr-body-guard.sh（リポジトリの外）は正本 `docs/handoff/conversation-consent/hooks/pr-body-guard.sh` と一字一句同じ（`git show origin/main:<正本> | diff -q - ~/.claude/scripts/pr-body-guard.sh` が差なし）。
2. pr-body-guard は検証する場所を、①フックに渡る cwd（`docs/handoff/conversation-consent/hooks/pr-body-guard.sh:85-86`）②命令文の中の `cd <パス>`（同 `:88-99`、正規表現 `cd\s+(\S+)`）の順で決め、その場所で `scripts/dev/validate-pr-body.sh` を動かす（同 `:166-170`）。validate-pr-body.sh は `git rev-parse --show-toplevel` を repo の根にして recon.md・design.md の実在を見る（`scripts/dev/validate-pr-body.sh:9`・`:62-64`）。
3. confidential-quote-guard（本物 ~/.claude/scripts/confidential-quote-guard/guard.py（リポジトリの外）、2026-10-27 00:34 JST 更新）は、gh の本文の操作を「命令全体が `gh ...` だけ」の形でしか通さない（同ファイル 1093-1131 行で先頭の単位を `strict_words` → `check_gh`、`check_gh` は先頭が `gh` でなければ `GH_MSG` で止める 同ファイル 1035-1044 行）。`cd <絶対パス> && gh pr create ...` は止まる。
4. Claude Code の Bash は、作業ディレクトリが ~/worktrees 配下だと毎回本店（/Users/tanizawashingo/salesanchor）に戻す（この会話で `cd <worktree>` 単独実行のあと「Shell cwd was reset to /Users/tanizawashingo/salesanchor」）。本店の写しは origin/main より 4824 件古い（stale-main-read-warn の表示）。
5. 結果: 本店で始めた会話からは、`gh pr create` を単独で流すと pr-body-guard が本店の古い写しで検証して「recon.md が存在しません」で止め、`cd` でつなげると confidential-quote-guard が止める。記録: `~/.claude/logs/agent-events.jsonl` の 2026-10-26T16:29Z〜17:34Z の行（写し: /tmp/CC報告ファイル/loading-english-literal/guard-conflict-log.txt）。2 つの別の作業で同じ止まり方が出ている。
6. `gh pr edit <番号> --body-file` も pr-body-guard の対象（`docs/handoff/conversation-consent/hooks/pr-body-guard.sh:70-71`）。GO記録を本文へ足すときも同じく止まる。

## 未確認
- 試験 `scripts/dev/test-agent-hooks.sh` を Linux のクラウドで動かせるか（Mac の ~/.claude を前提にする箇所があるか）。実装担当が確かめて報告する。
