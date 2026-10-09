# 設計：マージされた worktree の即時回収（reaper の配線修正）

- 状態：設計案（草案）・自己審査済み・PO の承認待ち・実装未着手
- 置き場所（予定）：`docs/handoff/reaper-on-merge/design.md`。recon を兼ねる。
- 対象の ADR：`docs/adr/ADR-114-worktree-auto-cleanup.md`（ADR-114-worktree-auto-cleanup）
- PO の要望（2026-10-08〜09）：「main に入った時点で自動で削除される仕組みにしたい」「頻度を上げて、常に不要なものを消したい」。設計に進むことに「y」。

## 1. 現在地（事実。origin/main 0f5d7e537、2026-10-09 の調査）
- worktree は本体を除いて 100 個。上限 100 に到達している（`scripts/new-worktree.sh:73-74`）。
- 内訳
  - PR が OPEN：62
  - MERGED：6、CLOSED：1、PR 無し：31
  - 台帳以外の未保存あり：31
  - 未 push あり：16
  - 最後のコミットが 30日より古い：23
  - 合計の大きさ：約 10.4GB（手元の Mac。ディスクの空きは約170MB）
- 回収の経路は3つ。
  1. launchd `jp.salesanchor.reaper-onlogin`：ログイン時と毎日 03:00。本体 `/Users/tanizawashingo/salesanchor` で `reaper-worktree.sh --execute` を実行する。
     - **実際に削除しているのは、この経路だけ。** ログでは、ほぼ毎回「削除 1 件」。
  2. GitHub Actions の `.github/workflows/reaper-schedule.yml`：毎日 18:00 UTC、self-hosted macOS。
     - runner の checkout（`_work`）で実行し、`REAPER_WORKTREES_DIR=/Users/tanizawashingo/worktrees/salesanchor` で、走査だけを本体側に向けている（:25-37）。
     - しかし `MAIN_REPO_ROOT` は、cwd の `git rev-parse --git-common-dir` から決まる（`scripts/reaper-worktree.sh:40-45`）。そのため `_work` 側を指す。
     - 削除は `git -C "${MAIN_REPO_ROOT}" worktree remove`（:352）と `branch -D`（:357）で行うので、本体の worktree を消せない。台帳の照合も `_work` 側を見る。
     - 直近の run 37698305644 は「削除対象なし」だった。
  3. 即時の経路：`repository_dispatch: reaper-run`（`reaper-schedule.yml:13-14`）。
     - 発火元は `.github/workflows/active-work-auto-done.yml:137-145` だけで、これは **develop** への PR のマージで動く（:6-9）。
     - main へのマージでは発火しない（main 用の `.github/workflows/ledger-auto-done-main.yml` は dispatch していない）。
- 削除の条件（`scripts/reaper-worktree.sh:150-242`）
  - 台帳以外の未保存・未 push があれば保護する。
  - 台帳が DONE であるか、gh で main へのマージ済み、または CLOSED の PR があれば削除する。
  - IN_PROGRESS・REVIEW の未マージ、および PR 無しは保護する。
- 使用中（どこかのセッションの作業ディレクトリ）かどうかは、確認していない。
- GitHub Actions の仕様（Context7 `/websites/github_en_actions`、events-that-trigger-workflows の pull_request）
  - `types: [closed]` で、マージで閉じたときに動かせる。マージの場合、`GITHUB_REF` は base のブランチになる。
  - GITHUB_TOKEN で行ったマージの closed では、workflow は起動しない。

## 2. 正直な見立て
- 即時回収にしても、すぐに減るのは「マージ済みで、未保存の変更が無いもの」だけ。
- 100 個のうち大半（OPEN 62、未保存あり約40）は、自動では消せないし、消してはいけない。この分は §5 の「判断リスト」で、人が判断する。

## 3. 変更（1便に1つずつ）
| 便 | 箇所 | 変更前 | 変更後 | 目的 |
|---|---|---|---|---|
| R1 | `.github/workflows/reaper-schedule.yml:25-37` | `REAPER_WORKTREES_DIR` を注入し、`_work` を cwd にして `bash scripts/reaper-worktree.sh --execute` | `REAPER_WORKTREES_DIR` を外し、`working-directory: /Users/tanizawashingo/salesanchor` で `bash "$GITHUB_WORKSPACE/scripts/reaper-worktree.sh" --execute` を実行する（スクリプトは最新の checkout のもの、git の基点は本体） | GitHub Actions 経路が、本体の worktree を実際に回収できるようにする。台帳の照合も本体を見る |
| R2 | 同 `:9-14` の `on:` | schedule / workflow_dispatch / repository_dispatch | `pull_request: types: [closed], branches: [main]` を追加する。job に `if: github.event_name != 'pull_request' \|\| github.event.pull_request.merged == true` と `concurrency: { group: reaper, cancel-in-progress: false }` を付ける | main へのマージの直後に回収する |
| R3 | `scripts/reaper-worktree.sh` のチェック2の直前 | 使用中かどうかを見ない | `lsof -a -d cwd -Fn 2>/dev/null` の結果に、その worktree のパス（またはその配下）があれば、新しい区分 `SKIP_IN_USE` に入れて保護する。サマリに件数を出す | マージ直後に、まだそのフォルダで作業しているセッションを壊さない |
| R4 | `scripts/new-worktree.sh:77` | `grep -c "未保存あり" \|\| echo "0"`（一致が0件のとき "0\n0" になり、:83 の比較が壊れる。一致してもヘッダ行の数しか数えない） | `grep -oE '未保存あり（削除しない）: [0-9]+' \| grep -oE '[0-9]+$' \|\| true` とし、空なら 0 | 上限に到達したときの案内を正しく出す |
| R5 | `docs/adr/ADR-114-worktree-auto-cleanup.md` | develop 前提、即時経路は develop のみ | main のマージで即時回収すること、本体を基点に実行すること、使用中を保護することを、改訂の節として追記する（PO の承認が必要） | 決まりを実物に合わせる |

- 変えないこと：削除の安全条件（未保存・未 push の保護）、CLOSED の扱い、上限の値（100）、launchd の経路。
- self-hosted runner の上で `pull_request` を動かすことについて：このリポジトリはフォークからの PR を前提にしていない。それでも、`if` で merged かつ base が main の場合に限る。フォークの扱いのリポジトリ設定は未確認なので、実装の前に確かめる。

## 4. テスト・受入条件
| 基準 | 検証方法 |
|---|---|
| R1：GitHub Actions 経路が、本体の worktree を走査・削除できる | `workflow_dispatch` で手動実行し、ログの「対象 worktree 数」が本体の `git worktree list` の数と一致し、GHOST の誤検出が無いこと |
| R2：main へのマージの直後に起動する | 次のマージで、reaper-schedule の run が `pull_request` のイベントで起動し、そのブランチの worktree（未保存が無い場合）が消えること |
| R3：使用中は消さない | 使い捨ての worktree を作り、その中で `sleep` するプロセスを置いた状態で dry-run を実行し、`SKIP_IN_USE` に入ること。プロセスが無ければ、通常どおり判定されること |
| R4：上限の案内が正しい | 未保存ありが0件の状態と、N件の状態で、`UNSAVED_COUNT` が 0 と N になること（bash の単体の確認） |
| 既存の動作を壊さない | launchd の 03:00 の実行ログで、削除の件数・保護の件数が、前日と同じ傾向であること |

## 5. 判断リスト（今回の実装の外。PO に提示するだけ）
- 30日以上更新の無い OPEN の PR（23件）と、未保存ありの worktree（約40件）の一覧は、`/tmp/CC報告ファイル/ops-memory/20261008-worktrees/inventory.tsv` に保存済み。続けるか閉じるかは、PO と作業の持ち主が決める。

## 外部・過去事例の参照と我々への応用
- 社内の過去事例：`reaper-schedule.yml:26-29` のコメント（2026-07-20 の実測「対象0件」）と、それへの対処のコミット d2498937a。走査先だけを本体に向けたが、git の基点（MAIN_REPO_ROOT）は `_work` のまま残った。R1 は、その残りを直す。
- 公式の仕様：GitHub Actions の pull_request の closed イベント（上記 §1）。
- 外部の一般事例は使わない。

## 維持の仕組み
- 守り手：ADR-114（R5 の改訂）、reaper-schedule の run のログ、launchd のログ（`~/Library/Logs/reaper-onlogin.log`）。

## 戻し方
- 各便の PR を revert する。R1 と R2 は workflow のみ。R3 と R4 はスクリプトのみ。データ（worktree）の削除は、安全条件を変えていないので、増えるのは「マージ済みで、未保存が無いもの」の回収だけ。

## 審査（自己審査）
- 判定：APPROVE（設計の範囲）。
- 当初案の「main の祖先なら削除」は取り下げた。作ったばかりで変更が無い worktree も祖先になるため、作業の開始直後に消してしまう危険がある（2026-10-08 の実測で、祖先 21 件のうち 19 件に、コミットされていない作業が残っていた）。
- 未確認：
  - runner のラベルと online の状態（`gh api .../actions/runners` が 403）。runner のサービス `actions.runner.shingo-ops-salesanchor.Shingo-Mac-Temp` は launchd で稼働中。
  - フォークの PR の扱いのリポジトリ設定。

worktree 作成：上限100到達のため、PO 決定（2026-10-09）で WORKTREE_LIMIT=101 を1回限り使用（ADR-114 §6 の例外。本 PR が回収の仕組みの修正のため）
