# recon: 作業場所が上限 100 に達した件（置き忘れの部屋が溜まる）

この文書は何か：作業場所（worktree）が上限 100 に達して新しい作業を始められなくなった件の、今の仕組みの事実の一覧。
親（設計仕様書）: [docs/specs/reaper-auto-cleanup/README.md](../../specs/reaper-auto-cleanup/README.md)（子: [design-idle-reclaim.md](design-idle-reclaim.md)）

- 行番号の基準: origin/main `2adefae2e`（2026-11-17 fetch）。`git show origin/main:<path>` で読んだ。
- 区分（STANDARD-WORKFLOW §1.8）: 既存の延長（reaper-auto-cleanup テーマ・ADR-114）。
- KGI の PO 承認: 2026-11-17 チャット「1」。承認した目標は design-idle-reclaim.md §2。

## 1. 起きたこと

- 2026-11-17 早朝、`bash scripts/new-worktree.sh release/v102-heading-product-match --claude` が「⚠️ worktree が上限（100個）に達しています（現在 100 個）」で止まった。上限は `scripts/new-worktree.sh:73-81`（`WORKTREE_LIMIT` 既定 100）。直前の自動回収は「✅ 削除対象なし」。
- 自動回収（`scripts/reaper-worktree.sh`）はログイン時と毎日 03:00 に動く（`~/Library/LaunchAgents/jp.salesanchor.reaper-onlogin.plist`）。ログ `~/Library/Logs/reaper-onlogin.log` の最後の削除は「削除 1 件」で、その後の約 37 回は続けて「削除対象なし」。
- 作業場所を作った月（gitdir の作成日）: 2026-06 4 件・09 16 件・10 36 件・11 39 件。作る数が増え、消える数がほぼ 0。

## 2. その朝の 100 件の内訳（自動回収の分類・87 件走査）

| 分類 | 件数 | 自動回収で消えない理由（コード） |
|---|---|---|
| 台帳 IN_PROGRESS・未マージ | 37（PR なし 22・PR 開 14・合流済 1） | IN_PROGRESS は保護（`scripts/reaper-worktree.sh:369-372`）。PR なしは閉じ判定にも当たらない（:347-360） |
| 記録していない変更あり | 46 | 未保存は保護（:235-327、`SKIP_UNSAVED` :322・:324） |
| 未マージ（台帳に行なし等） | 4 | :374-375 |
| ブランチの無い写し（detached） | 13 | 本番の走査は branch 行の無い部屋を数えない（:164-191、:170 の条件） |

- 消えない部屋の多くは「PR を作らずに終わった作業（調べ・設計の下書き・結果の記録）」と「審査のための写し」。どちらも作業の終わりに部屋を消す手順が無い。
- 台帳 DONE の自動化は「main へのマージ」が合図（ADR-114 §2・§3）。PR を作らない作業は合図が来ないため、IN_PROGRESS のまま永久に保護される。

## 3. 同じ朝、別の作業が手で片付けた（2026-11-17 05:18〜05:24）

- 記録: `~/CC報告ファイル-keep/worktree-cleanup-20261117/`（candidates.md・archive-result.txt・remove-result.txt・archive/ 80 ファイル）。
- 33 件の作業場所を消した（ブランチは 33 件とも残した: remove-result.txt の `branch_kept`）。うち 22 件は記録していない変更があり、消す前に `.head`・`.patch`・`.status` を保存、新しいファイルがある 11 件は `.untracked.tar` も保存（Opus が archive/ を数えて照合: `.status` の `??` がある 11 件すべてに `.untracked.tar` あり）。
- 片付け後の数: `git worktree list` 66 行（本店を除き 65 件・2026-11-17 05:31）。手での一度きりの片付けで、溜まる仕組みは変わっていない。

## 4. 残る 65 件の内訳（2026-11-17 05:31・Opus が `git worktree list --porcelain` と `gh pr list --state all --limit 4000` を突き合わせ）

- PR なし 52 件（うち detached 13 件）、PR 開 13 件。
- 最後に触ってから 14 日以上（index ファイルの更新日で概算）: PR なし 22 件・PR 開 7 件。
- PR なし 14 日以上のうち `~/worktrees/` の下にあるもの: 20 件。外にあるもの: `~/salesanchor/src`（detached・37 日）、`~/salesanchor/.claude/worktrees/design-inbox-brushup`（20 日）。
- 道具の写し `~/.salesanchor-tools` は detached（ADR-114 R12・`docs/handoff/disk-janitor/design.md:151`）。消してはいけない。
- 生の一覧: `/private/tmp/claude-501/-Users-tanizawashingo-salesanchor/b257ea2d-0ae6-47a4-bff2-130803656178/scratchpad/wt/list2.txt`・`prs2.json`（セッション終了で消える。数は本節に転記済み）。

## 5. 使える既存の部品

- 未保存の判定: `scripts/reaper-worktree.sh:235-327`（`git-safe.sh` の上書き付き status・入れ子リポジトリ保護・origin から届かないコミットの数 :275）。
- 使用中の保護: `lsof` の cwd 一覧（:194-195・:227-233）。
- 消す前に控える仕組み: R9 の PR 本文の下書きを `<git-common-dir>/reaper-drafts/` へ控え、失敗したら消さない（:516-533）。
- 数の見張りと Discord への知らせ: `scripts/mac-jobs-watch.sh`（30 分ごと・設定は `mjw_config` :21-57 に 1 か所）。空き容量が少ないときの知らせ（`MJW_DISK_LOW_GIB`・`MJW_DISK_OK_GIB` :45-46、判定 :428）と同じ形で足せる。送り先は ADR-1009 の番人と同じファイル（:29）。
- 試験: `scripts/tests/test-reaper-safety.sh`・`scripts/tests/test-mac-jobs-watch.sh`。
- git の決まり（Context7 `/git/htmldocs` git-worktree で確認）: `git worktree list --porcelain` は鍵をかけた部屋に `locked` 行を出す。`git worktree lock --reason` で鍵をかけられる。`remove` は鍵付きの部屋を `--force` 2 回でしか消さない。

## 6. 既存 ADR の検索

- `git grep -i -E "worktree|作業場所" docs/adr/` で関係するもの: ADR-114（worktree ライフサイクル・R1〜R12）、ADR-1039（作業場所に向けた git の守り）、ADR-111（マシン分離）。
- ADR-114 §1「スクリプト類は完了判定にリモート有無や経過時間を使わない」、§5「未保存の作業がある部屋は絶対に消さない・通知して人の判断に回す」。今回の KGI 3（消す前に写しを取る）はこの §5 を変える。→ design-idle-reclaim.md §7 で ADR-114 R13 として扱う。

## 7. 未確認

- PR なしの部屋の「最後に触った日」の正確な値（本 recon の 14 日は index の更新日での概算）。実装の最初の段で、design §3-2 の数え方で数え直す。
- 30 日で何件作られ、14 日の決まりで何件消えるかの釣り合い（K12 の 30 日の観測で確かめる）。
