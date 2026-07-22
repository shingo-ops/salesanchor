# recon: reaper 自動掃除（worktree の自動回収）

> この文書は何か（専門用語なしの1行）:
> 掃除機（reaper）の今の状態を、実際に動かして確かめた事実だけで記録したもの。

親（あるべき姿）: ../../specs/reaper-auto-cleanup/README.md

実測日: 2026-07-20 〜 2026-07-22
実測時 origin/main SHA: 5165d73a3a2d2483bb16ce6b0fac3a462d9519be

## 観点1: 対象（worktree 母集団）

本店 /Users/tanizawashingo/worktrees/salesanchor 直下フォルダ実数 91件。内訳は完全に閉じた。

- reaper 解決 86件
- git worktree でない異物 3件: feature / feature-morimoto-fedex-page-redesign-pr-a / release-doc-heading-duplicates-20260702
- worktree だがブランチ名が読めず数から漏れる 1件: main-rls-bootstrap-ordering
- .worktree-id により解決される 1件: feature-morimoto-discord-b-method-impl

## 観点2: なぜ今の姿か（配線ズレの根本原因）

定期 reaper は self-hosted runner 上で `.github/workflows/reaper-schedule.yml:21` の actions/checkout により _work 配下に別チェックアウトを作って動く。
そのため reaper の git-common-dir が _work 側を指し、本店の worktree 登録を共有しない。

物証: 定期実行ログ Working directory is '/Users/tanizawashingo/actions-runner-shingo/_work/salesanchor/salesanchor' ／ 対象 worktree 数: 0 件（2026-07-20 実測）
本店 .git/worktrees 登録 93件 に対し Actions 側 worktree 登録 1件。

## 観点3: 保護判定の動作

`scripts/reaper-worktree.sh:25` で --execute 指定時のみ実削除に進む。削除前に以下の順で保護を通す。

- `scripts/reaper-worktree.sh:136` チェック1: active-work.md のステータス
- `scripts/reaper-worktree.sh:154` チェック2: 未保存の作業がないか（最優先保護）
- `scripts/reaper-worktree.sh:193` チェック3: DONE またはマージ済み

出力分類は `scripts/reaper-worktree.sh:52` からの SKIP_IN_PROGRESS / SKIP_UNSAVED / SKIP_NOT_MERGED の3種。

REAPER_WORKTREES_DIR を指定した本店走査の dry-run 実測（2026-07-22）: 対象87件、IN_PROGRESS/REVIEW 29件・未保存あり 46件・未マージ 12件、削除対象 0件。develop/main の混入なし。

## 観点4: 即時掃除の配線

`.github/workflows/active-work-auto-done.yml:137` が repository_dispatch で event_type=reaper-run を発火する配線を持つ。
`.github/workflows/reaper-schedule.yml:13` が repository_dispatch types: [reaper-run] を受け口として持つ。
ただし直近5runはすべて event=schedule。reaper-run による即時起動の実動作履歴は未確認。

## 観点5: 監視（ghost-count）の現状

`scripts/ghost-count.sh:15` に閾値の既定20（GHOST_THRESHOLD で注入可）。見張りのみで exit 値を変えない設計。
.github/workflows/ 配下から ghost-count を呼ぶ記述は 0件。定期jobに接続されていない。

## 観点6: 異物・ラベル欠けの扱い

REAPER_WORKTREES_DIR モードでは、ブランチ名が取れない場合に `scripts/reaper-worktree.sh:90` で無言で continue する。
異物専用の出力欄は存在しない（観点3の3分類のみ）。

## 観点7: 接触面（逆参照・拡張子無制限）

`scripts/reaper-worktree.sh` を参照する文書・スクリプト 17件。主なもの:
`ops/launchd/jp.salesanchor.reaper-onlogin.plist` / `.github/workflows/reaper-schedule.yml` / `docs/PARALLEL_TERMINAL_GUIDE.md` / `docs/ops/runner-commands.md` / `scripts/new-worktree.sh` / `scripts/tests/test-reaper-safety.sh` / `docs/adr/ADR-114-worktree-auto-cleanup.md`

`.github/workflows/reaper-schedule.yml` を参照するのは同ファイルのみ。

## 既存ADR検索の結果

`git grep -i "reaper" docs/adr/` 実施済み。該当: ADR-114（worktree ライフサイクルの完全自動化）、ADR-029（self-hosted runner fleet）。
