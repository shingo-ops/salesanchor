# recon（現在地・file:line 実物・推測禁止）

親: ./README.md

> この文書は何か（専門用語なしの1行）:
> 掃除機の今の状態を、実際に動かして確かめた事実だけで記録したもの。

実測日: 2026-07-20 〜 2026-07-22
実測時 origin/main SHA: f1429829f56e858d5e706fd736605a99c1ba67d0

## 観点1: 対象（worktree 母集団）

本店 /Users/tanizawashingo/worktrees/salesanchor 直下フォルダ実数 91件。内訳は完全に閉じた。
- reaper 解決 86件
- git worktree でない異物 3件: feature / feature-morimoto-fedex-page-redesign-pr-a / release-doc-heading-duplicates-20260702
- worktree だがブランチ名が読めず数から漏れる 1件: main-rls-bootstrap-ordering（is worktree=true・branch --show-current が空）
- .worktree-id により解決される 1件: feature-morimoto-discord-b-method-impl

## 観点2: なぜ今の姿か（配線ズレの根本原因）

定期 reaper は self-hosted runner 上で actions/checkout@v5（.github/workflows/reaper-schedule.yml:21）により _work 配下に別チェックアウトを作って動く。
そのため reaper の git-common-dir が _work 側を指し、本店の worktree 登録を共有しない。
物証: 定期実行ログ Working directory is '/Users/tanizawashingo/actions-runner-shingo/_work/salesanchor/salesanchor' ／ 対象 worktree 数: 0 件（2026-07-20 実測）
本店 .git/worktrees 登録 93件 に対し Actions 側 worktree 登録 1件。

## 観点3: 保護判定の動作

scripts/reaper-worktree.sh は --execute 指定時のみ実削除に進む（同 25行目）。削除前に以下の順で保護を通す。
- チェック1: active-work.md のステータス（136行目）
- チェック2: 未保存の作業がないか・最優先保護（144行目・154行目）
- チェック3: DONE またはマージ済み（193行目）
出力分類は SKIP_IN_PROGRESS / SKIP_UNSAVED / SKIP_NOT_MERGED の3種（52-54行目）。

REAPER_WORKTREES_DIR を指定した本店走査の dry-run実測（2026-07-22）: 対象87件、IN_PROGRESS/REVIEW 29件・未保存あり 46件・未マージ 12件、削除対象 0件。develop/main の混入なし。

## 観点4: 即時掃除の配線

.github/workflows/active-work-auto-done.yml:137-143 が repository_dispatch で event_type=reaper-run を発火する配線を持つ。
.github/workflows/reaper-schedule.yml:13-14 が repository_dispatch types: [reaper-run] を受け口として持つ。
ただし直近5runはすべて event=schedule。reaper-run による即時起動の実動作履歴は未確認。

## 観点5: 監視（ghost-count）の現状

scripts/ghost-count.sh は実在。閾値は既定20・GHOST_THRESHOLD で注入可。見張りのみで exit 値を変えない設計（同 13-17行目）。
.github/workflows/ 配下から ghost-count を呼ぶ記述は 0件。定期jobに接続されていない。

## 観点6: 異物・ラベル欠けの扱い

REAPER_WORKTREES_DIR モードでは、ブランチ名が取れない場合に無言で continue する（scripts/reaper-worktree.sh:90）。
異物専用の出力欄は存在しない（観点3の3分類のみ）。

## 観点7: 接触面（逆参照・拡張子無制限）

scripts/reaper-worktree.sh を参照する文書・スクリプト 17件:
ops/launchd/jp.salesanchor.reaper-onlogin.plist / .github/workflows/reaper-schedule.yml / docs/PARALLEL_TERMINAL_GUIDE.md / docs/ops/runner-commands.md / scripts/reaper-worktree.sh / scripts/new-worktree.sh / scripts/tests/test-reaper-safety.sh / docs/ai-agents/evidence-registry.md / docs/adr/ADR-029-self-hosted-runner-fleet.md / docs/handoff/gate-diff-3dot/design.md / docs/handoff/ledger-guard/recon.md / docs/handoff/dev-continuity/recon.md / docs/handoff/branch-operations/recon.md / docs/handoff/branch-operations/design.md / docs/specs/ledger-guard/design-phase2.md / docs/specs/ledger-guard/recon.md / docs/handoff/agent-complete-design/recon.md
.github/workflows/reaper-schedule.yml を参照するのは同ファイルのみ。
