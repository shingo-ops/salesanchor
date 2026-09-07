# dev-continuity recon — 六本柱の現状距離測定 v1

> この文書は何か（専門用語なしの1行）:
> 「開発が止まりにくい仕組み」が今どこまでできているかを、実物の file:line だけで測った記録。

親: [docs/specs/dev-continuity/](../../specs/dev-continuity/) ／ 型: [docs/specs/agent-complete-design/README.md](../../specs/agent-complete-design/README.md) §4

## 柱ごとの距離表

| 柱 | 現状[有/一部有/無] | 実物の根拠 file:line | To-Beとの差分の事実 |
|---|---|---|---|
| 柱1 自動のホワイトボード | 一部有 | `.claude-pipeline/active-work.md:1-18`, `scripts/new-worktree.sh:121-157`, `scripts/reaper-worktree.sh:317-352`, `scripts/cleanup-worktree.sh:52-79`, `scripts/register-pr.sh:62-95` | 台帳は `active-work.md` が正本で、新規作成時の自動追記と完了時の DONE 化はある。ただし `担当機能エリア` と `PR#` は手作業または別スクリプトで埋めており、机の新設/完了/マージ/削除が 1 本の自動 writer で完結していない。 |
| 柱2 残量メーター | 一部有 | `scripts/new-worktree.sh:57-75`, `scripts/check-stale-worktrees.sh:27-31`, `scripts/check-stale-worktrees.sh:100-165`, `docs/adr/ADR-114-worktree-auto-cleanup.md:80-83` | 上限つき資源として worktree 数の上限 `WORKTREE_LIMIT=100` と、放置判定の `STALE_HOURS=24` はある。警報は通知止まりで、警報→自動起票/自動PR の経路は見つからない。stash 上限の定義も見つからない。 |
| 柱3 貸出札 | 一部有 | `.claude/settings.json:25-108`, `/Users/tanizawashingo/.claude/scripts/worktree-only-guard.sh:1-130`, `/Users/tanizawashingo/.claude/scripts/worktree-access-guard.sh:1-128`, `/Users/tanizawashingo/.claude/scripts/gh-scope-guard.sh:1-330`, `/Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh:1-105`, `/Users/tanizawashingo/.claude/agent-tokens.json:6-18`, `.claude-pipeline/active-work.md:17-18` | worktree 外の Edit/Write/Bash/Glob/Grep/Read、他PR参照、危険操作は止められる。だが危険ファイルの file-based 定義は見つからず、実体は `danger_ops` の操作列挙で代替している。台帳にも占有欄はなく、開始日時/状態/PR# での管理に留まる。 |
| 柱4 通報の自動化 | 一部有 | `.claude/settings.json:14-108`, `/Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh:46-105`, `/Users/tanizawashingo/.claude/scripts/gh-scope-guard.sh:303-327`, `/Users/tanizawashingo/.claude/scripts/worktree-only-guard.sh:75-130`, `/Users/tanizawashingo/.claude/scripts/worktree-access-guard.sh:103-125`, `/Users/tanizawashingo/.claude/logs/agent-events.jsonl:37328`, `/Users/tanizawashingo/.claude/logs/agent-events.jsonl:37561`, `/Users/tanizawashingo/.claude/logs/agent-events.jsonl:37607` | PreToolUse は Bash / Read / Edit / Write / Glob / Grep で実行され、Bash では危険操作・scope・worktree がブロックされる。`Read` matcher もあるが、2026-07-03 の `access_blocked` は 0 件だった。停止事実は JSONL に記録されるが、PO への自動起票・自動 PR 起票は見つからない。 `--no-verify` の explicit 検知も見つからない。 |
| 柱5 新陳代謝 | 一部有 | `scripts/reaper-worktree.sh:29-37`, `scripts/reaper-worktree.sh:136-253`, `scripts/reaper-worktree.sh:296-352`, `scripts/cleanup-worktree.sh:1-87`, `scripts/release-worktree.sh:1-97`, `scripts/check-stale-worktrees.sh:19-20`, `scripts/check-stale-worktrees.sh:53-165` | 自動回収の実体はある。完了机は cleanup/reaper でフォルダ削除と DONE 化され、放置机は 24h 超で通知される。ただし実行起動は cron/manual 前提で、寿命管理は「通知＋回収」に留まり、放置物を期限で自動閉鎖する一体の仕組みではない。 |
| 柱6 単一の今 | 一部有 | `.claude/settings.json:34-54`, `.claude/hooks/check-freshness.sh:1-45`, `scripts/new-worktree.sh:77-104`, `scripts/validate-worktree-start.sh:26-81`, `scripts/validate-pr-ownership.sh:21-150`, `scripts/gh-pr-create-safe.sh:51-86`, `docs/handoff/branch-operations/recon.md:27-35`, `docs/handoff/branch-operations/design.md:48-55` | セッション開始時の鮮度確認はあるが、参照先が割れている。`check-freshness` は `origin/develop` を見に行き、`validate-pr-ownership` は `develop` を既定 base にし、`gh-pr-create-safe` は `main` 既定、`new-worktree` は `origin/main` 直指定。最新を読む仕組みはあるのに、ルール正本が重複していて SSOT が揃っていない。 |
| 成長回路 | 一部有 | `docs/specs/agent-complete-design/track-record.md:1-46`, `docs/specs/agent-complete-design/kgi.md:29-34,51-52`, `docs/specs/agent-complete-design/README.md:41-45`, `docs/specs/agent-complete-design/README.md:87-93` | track-record 型は `agent-complete-design` にだけ実在し、起因ラベル `設計/実装/環境/外部` と 5W2H 記帳は定義済み。だが repo 横断の停止台帳は見つからず、同じ × が続いたときに自動で別テーマへ格上げする実装も見つからない。 |

## 検算

- 調査項目 7/7 を埋めた。
- 柱1〜柱6 と成長回路の全項目に、実物の file:line か「見つからない」を書いた。
- `--no-verify` の explicit 検知、stash 上限、警報→自動起票の経路、repo 横断の track-record は見つからなかった。
