# design: 置き忘れの作業場所を、写しを取ってから自動で片付ける

この文書は何か：PR を作らずに終わった作業の部屋と審査の写しが溜まり、上限 100 に達する件の直し方と、その副作用を書いたもの。
親（設計仕様書）: [docs/specs/reaper-auto-cleanup/README.md](../../specs/reaper-auto-cleanup/README.md)
recon: [docs/handoff/reaper-auto-cleanup/recon-idle-reclaim.md](recon-idle-reclaim.md)
上位方針: ADR-114（本設計で R13 を足す。§7）

## 1. 目的

作業場所が上限に達して新しい作業を始められない事態を、人の手の片付けなしで起こさない。記録していない変更は 1 件も失わない。

## 2. KGI（PO 承認 2026-11-17「1」）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| K11 | 直した翌朝、作業場所が 50 件以下 | 翌朝 03:00 の自動回収のログの「作業場所の数」 | ≤50 |
| K12 | 30 日間、毎朝 50 件以下が続く | 毎朝の自動回収のログの「作業場所の数」30 日分 | 30/30 日 ≤50 |
| K13 | 記録していない変更の失いゼロ | ログの「片付け N 件」と「写し N 件」が一致。試験で写しから元に戻せる | 片付け件数＝写しの件数、戻し試験 合格 |
| K14 | 70 件を超えたらその日のうちに Discord に知らせが来る | 線を下げて 1 回試す | 知らせ 1/1 |

PR が開いている部屋（2026-11-17 時点 13 件）は今までどおり消さない。

## 3. 変える所

### 3-1. 置き忘れの部屋の片付け（`scripts/reaper-worktree.sh`）

次のすべてに当たる部屋を「置き忘れ」とし、写しを取ってから部屋を消す。ブランチは消さない。台帳は書き換えない。

| # | 条件 | 当たらないとき |
|---|---|---|
| I1 | 部屋が `$HOME/worktrees/` の下にある | 残す（`~/.salesanchor-tools`・`~/salesanchor/src`・`~/salesanchor/.claude/worktrees/*` は対象外） |
| I2 | ブランチが main・develop・`REAPER_BASE_BRANCH` でない（既存チェック 0） | 残す |
| I3 | git の繋がりが合う（既存チェック -1） | 残す |
| I4 | 使用中でない（既存チェック 1.5）。消す直前にも lsof をもう一度取って確かめる（既存は :195 の 1 回だけ） | 残す |
| I5 | 鍵がかかっていない（`git worktree list --porcelain` に `locked` 行が無い） | 残す |
| I6 | そのブランチの PR が開いていない（`gh pr list --repo <repo> --state open --head <branch>` の終了コードが 0 で、0 件）。gh が失敗したら残す。既存の :286・:337 の「失敗は 0 件扱い」の形は流用しない | 残す |
| I7 | 最後に触ってから `REAPER_IDLE_DAYS`（既定 14）日以上（3-2） | 残す |
| I8 | 入れ子のリポジトリが無い（既存 R11） | 残す |
| I9 | 写しが取れて照合が合った（3-3） | 残す |

- 台帳の状態（IN_PROGRESS 等）は I1〜I9 の判定に使わない。完了の判定ではなく「部屋だけ片付け、ブランチと台帳はそのまま」だから。ADR-114 §1 の「完了判定に経過時間を使わない」は守る。§5 の「IN_PROGRESS は絶対に消さない」は R13 で変える（§7）。
- 既存の「DONE・合流済・閉じた PR」の回収（チェック 3）は今までどおり。置き忘れの判定は、既存の回収で消えなかった部屋と detached の部屋（3-4）にだけ行う。
- 既存の分け先（`SKIP_IN_PROGRESS`・`SKIP_UNSAVED`・`SKIP_NOT_MERGED`、:322・:324・:370・:375）はブランチ名しか持たない。置き忘れの判定用に、パスとブランチ名の組を持つ別の一覧 `IDLE_CANDIDATES` を同じ場所で積む。
- fetch が失敗した回（:378-381）は、置き忘れの候補も空にして何も消さない。
- 置き忘れの処理（写し・照合・消す）は、既存の「削除対象なし」の終わり（:477-480）と dry-run の終わり（:499-503）より前に置く。dry-run のときは候補と写しの見込みの大きさを出すだけで、写しも削除もしない。
- 走らせる回: 毎日 03:00 の定期の回（`reaper-schedule.yml` 経由）と、`new-worktree.sh:66-68` が作るたびに流す回の両方で走らせる（上限に近いときほど空きが要るため）。後者は待たずに skip する既存のロックに従う。
- detached の候補は本ループ（branch 行のある部屋）の外で積むため、I3（`git_safe_link_ok`）をその部屋への最初の git 命令より前に当てる。
- 消す処理は既存の削除のループ（:535-554。ブランチ削除と台帳 DONE を含む）を使わない。置き忘れ専用の処理を作り、`git worktree remove --force` が成功した部屋だけを数える（既存 :553 は失敗しても数える）。

### 3-2. 「最後に触った日」の数え方

次の時刻のうち一番新しいもの。

- HEAD のコミット時刻（`git log -1 --format=%ct HEAD`）
- 部屋の gitdir の `index` と `HEAD` ファイルの更新時刻
- `git status --porcelain --untracked-files=all` に出る各ファイルのうち、今あるものの更新時刻（消したファイル ` D`・`D ` は時刻が無いので外す）

決まり:
- 時刻は、既存のチェック 2 の `git status`（:242・:266）より前、部屋ごとの判定の最初（:238 より前）で全部屋分を取って持っておく。あわせて台本の最初で `export GIT_OPTIONAL_LOCKS=0` とし、既存の status も含めて index を書き直さないようにする（status が index を書き直して時刻が毎晩新しくなるのを防ぐ）。
- 上の命令が失敗したら「今」とみなす（消さない側に倒す）。
- 時刻の取り方は macOS（`stat -f %m`）と Linux（`stat -c %Y`）で違うため、1 つの関数にまとめて両方に対応する。

### 3-3. 写しの取り方と照合

置き場: `<git-common-dir>/reaper-archive/<YYYYMMDD-HHMMSS>-<部屋の名前>/`（git の管理外・push されない。R9 の `reaper-drafts` と同じ考え方）。同じ名前の置き場がすでにあれば、その部屋は消さない。

作り方: 先に `du` で写しの見込みの大きさを測り、`REAPER_ARCHIVE_MAX_MB` を超えるなら写しを作らずにログに名前を出して残す。超えなければ `<置き場>.tmp/` に作り、照合が全部合ったら `<置き場>/` へ名前を変える。照合が合わなければ `.tmp/` をその場で消す（照合に失敗した部屋の写しが回るたびに溜まらないようにする）。

`git add -N`（status で 2 文字目が `A`）のファイルがある部屋は、戻したときに status が同じにならないため対象にせず残し、ログに名前を出す。

| ファイル | 中身 |
|---|---|
| `head.txt` | ブランチ名・HEAD の sha・部屋のパス・最後に触った日 |
| `status.txt` | `git status --porcelain --untracked-files=all --ignore-submodules=all --no-renames` |
| `staged.patch` | `git diff --cached --binary --no-renames`（ステージ済みの変更） |
| `unstaged.patch` | `git diff --binary --no-renames`（ステージしていない変更） |
| `untracked.tar` | `git ls-files --others --exclude-standard -z` の全ファイル |
| `ignored.tar` | 無視ファイルのうち、`node_modules`・`.venv`・`dist`・`build`・`__pycache__`・`.pytest_cache`・`.mypy_cache`・`coverage` の下以外 |
| `ignored.list` | `ignored.tar` に入れたファイルの一覧（照合用） |
| `unpushed.bundle` | ブランチのある部屋: origin から届かないコミットがあるときだけ（`git bundle create ... HEAD --not --remotes=origin`）。detached の部屋: HEAD が `origin/main` から届かなければ必ず作る（`git bundle create ... HEAD --not origin/main`）。PR のブランチが後で消されると HEAD のコミットも消えうるため。HEAD から届かない reflog は写さない（ログに件数だけ出す） |

照合（1 つでも合わなければ消さない）:
- 写しを作る命令すべての終了コードが 0。
- 写しを作る前に、置き場のある場所の空き容量が `REAPER_ARCHIVE_MAX_MB` の 2 倍以上ある。
- `staged.patch`・`unstaged.patch` の `diff --git` の数が、status の 1 文字目・2 文字目の変更の数と一致する。
- 一時の index（`GIT_INDEX_FILE=<一時ファイル>`）で次の順に通る。部屋の index と作業ファイルは触らない: `git read-tree HEAD` → `git apply --cached --binary staged.patch` → `git apply --cached --check --binary unstaged.patch`。
- `untracked.tar` の `tar -tf` の件数が status の `??` の数と一致する。`ignored.tar` の `tar -tf` の件数が `ignored.list` の行数と一致する。
- `unpushed.bundle` があるとき `git bundle verify` が成功する。
- 写し全体が `REAPER_ARCHIVE_MAX_MB`（既定 200）以下。超えたら消さずにログに名前を出す。

stash について: stash は本店の共有の refs にあるため、部屋を消しても消えない（写さない）。

消した後: 部屋を消すのに成功したときだけ、ログに「置き忘れを片付け: <部屋> → 写し <置き場>」を 1 行出す。最後に「片付け N 件 / 写し N 件」。
- 片付け N: 上の行の数。写し N: 上の行のうち、置き場（`.tmp` でない）が実在する数。K13 はこの 2 つの一致で測る。
- `worktree remove` が失敗した部屋は「片付けに失敗: <部屋>（写しは <置き場> に残した）」と別の行に出し、どちらの数にも入れない。

### 3-4. 写し（detached）の部屋も見る

本番の走査で branch 行の無い部屋を飛ばしている所（`scripts/reaper-worktree.sh:164-191`）で、detached の部屋を `IDLE_CANDIDATES` に積む。3-1 の I1・I3〜I5・I7〜I9 を当てる（I2・I6 はブランチが無いので飛ばす）。detached はブランチが残らないため、origin から届かないコミットがあれば `unpushed.bundle` を必ず作る。

### 3-5. 毎回の数の記録

自動回収の最後に 1 行出す: `作業場所の数: <N>（上限 <WORKTREE_LIMIT> ・知らせる線 70）`。

- N の数え方は、上限の判定（`scripts/new-worktree.sh:74`）と同じにする: `git worktree list` の本店以外の行のうち、`/cbs-copy.` を含まない行の数。
- この行は台本の終わりの処理（`trap ... EXIT`）で出す。早めに終わる道（:477-480・:499-503）を含め、どの道で終わっても、片付けた後の数が必ず 1 行出る。
- K11・K12 は、毎日 03:00 の定期の回（GitHub Actions の `reaper-schedule.yml` の実行記録）のこの行で数える。`new-worktree.sh` が作るたびに流す回（:66-68）は出力を捨てているため数えない。

### 3-6. 70 件を超えたら知らせる（`scripts/mac-jobs-watch.sh`）

空き容量の知らせ（disk-low）と同じ形で `wt-high` を足す。

- 設定: `MJW_WT_HIGH`（既定 70）・`MJW_WT_OK`（既定 60）・`MJW_MAIN_REPO`（既定 `$HOME/salesanchor`）を `mjw_config` に足す。
- 数え方: 3-5 と同じ。
- 判定: 数が `MJW_WT_HIGH` を超えたら問題 `wt-high`。`MJW_WT_OK` 以下に戻ったら解消。間は前の状態のまま（行ったり来たりで何度も鳴らさない）。
- 文: 「作業場所が <N> 件あります（70 件を超えました）。夜の自動片付けで減らない部屋は、PR が開いたままか、使用中か、鍵がかかっています。」
- くり返し: 既存の `MJW_REPEAT_SECONDS`（1 日）。

### 3-7. 戻し方（片付けた部屋を元に戻す）

1. `git worktree add --detach <元のパス> <head.txt の sha>`（`unpushed.bundle` があるときは先に `git fetch <bundle> HEAD` でコミットを本店に入れてから）
2. ブランチがあった部屋は、部屋の中で `git switch <ブランチ>`（ブランチの指す先が head.txt の sha と違えば止めて人に回す）
3. `git apply --binary --index staged.patch`、続けて `git apply --binary unstaged.patch`
4. `tar -xf untracked.tar`・`tar -xf ignored.tar`（部屋の中で）

`reset --hard` は使わない。この手順を scripts/reaper-restore.sh（新設） <写しの置き場> 1 本にまとめる（読むのは写しだけ・元のパスに何かあれば止まる）。

## 4. 触らない範囲

- 上限 `WORKTREE_LIMIT` の値（100 のまま）。
- ブランチの削除・台帳の書き換え（置き忘れの片付けでは行わない）。
- 既存の回収（DONE・合流済・閉じた PR）の条件と、R8〜R12 の安全条件。
- `.github/workflows/`（変えない）。

## 5. 代わりの案と選んだ理由

| 案 | 中身 | 見込み（2026-11-17 の 65 件に当てる） | 採否 |
|---|---|---|---|
| A | 上限を上げる | 0 件減る | 不採用（ADR-114 §6 で禁止） |
| B | 合流済・閉じた PR だけ消す（今のまま） | 0 件減る（残る部屋は PR なし・PR 開だけ） | 不採用 |
| C | 作業の終わりに台帳を DONE にするよう担当へ徹底する | 人と AI の注意しだい。今回たまったのはこれが守られなかったため | 不採用 |
| D | 14 日触っていない・PR が開いていない部屋を、写しを取って片付ける | 約 20 件減り 45 件（概算。下の注） | **採用** |
| D' | D を 30 日にする | 約 6 件減り 59 件（K11 を満たさない） | 不採用 |
| D'' | D を 7 日にする | もっと減るが、PO の答え待ちの作業を巻き込みやすい | 不採用 |
| E | 部屋と一緒にブランチも消す | 戻せなくなる | 不採用 |

注: 45 件は index の時刻からの概算で、200MB 超・入れ子・鍵付き・PR 開の部屋と、その後に作られた部屋を差し引いていない（未確認）。便1 の実装の最初に `--dry-run` で「置き忘れの候補 N 件」を出して数え直し、65−N が 50 を超えるなら合流前に止めて PO に返す。

## 6. 弊害とリスク

| リスク | 対処 |
|---|---|
| PO の答え待ちで 14 日止まった作業の部屋が消える | ブランチと写しが残り、3-7 で戻せる。長く置きたい部屋は `git worktree lock --reason "<理由>"` で外せる（I5） |
| 写しが Mac の容量を食う | 1 部屋 200MB の上限・node_modules 等は写さない。`reaper-archive` を 90 日で消すかは 30 日の観測後に決める（今回は消さない） |
| 無視ファイルの中の手書きの記録が写しから漏れる | `ignored.tar` で無視ファイルも写す（作り直せる大きな置き場だけ除く） |
| 無視ファイルに `.env` 等の鍵が入っていると写しにも入る | 置き場は同じ Mac の `.git` の中（push されない・元の部屋と同じ場所に同じ物があっただけ）。写しの置き場のファイル名と件数だけをログに出し、中身は出さない |
| 使用中の判定（cwd）は、部屋に cd せず絶対パスで書き込む作業を見落とす | そうした作業もファイルの更新時刻が変わるため、I7（14 日）で守られる |
| detached の部屋の reflog だけにあるコミット（HEAD から届かない）は写さないので消える | ログに件数を出す。HEAD から届くコミットは bundle で残る |
| 消している途中で失敗する | 写しを先に作り照合が合ってから消す。`worktree remove` が失敗した部屋は数えず、写しは残す |
| 走査の時間が延びる（部屋ごとに gh を 1 回） | 対象は既存の回収で残った部屋だけ。延びた秒数を実装の結果に書く |
| 安全条件「未保存は絶対に消さない」を変える | 写しの照合が合ったときだけ消す。ADR-114 R13 に書き、PO 承認の KGI K13 で守る |

## 7. ADR-114 R13（実装の PR で ADR に足す文案）

§5 安全条件の「IN_PROGRESS の部屋は絶対に消さない」（ADR-114:78）と「未保存の作業がある部屋は絶対に消さない」（:79）の後ろに「（R13 の置き忘れの部屋を除く）」を足す。同じ趣旨の :118（人を残す 1 点目）・:143（IN_PROGRESS かつ未マージ）・:144（未コミット・未push）にも同じ但し書きを足す（行番号は 2026-11-17 の origin/main 基準。実装の PR で読み直す）。そのうえで §5 に足す:
「置き忘れの部屋（2026-11-17 R13）：`$HOME/worktrees/` の下にあり、PR が開いておらず、使用中でも鍵付きでもなく、最後に触ってから `REAPER_IDLE_DAYS`（既定 14）日以上の部屋は、記録していない変更・新しいファイル・無視ファイル（作り直せる置き場を除く）・origin から届かないコミットを `<git-common-dir>/reaper-archive/` に写し、照合が合ったときだけ部屋を消す。ブランチと台帳は変えない。detached の部屋も同じ。戻しは scripts/reaper-restore.sh（新設）。」

改訂履歴に 1 行足す。

## 8. 受け入れ条件

| 基準 | 検証方法 |
|---|---|
| 置き忘れの部屋（14 日・PR なし）が写しを取って消え、ブランチは残る | `scripts/tests/test-reaper-safety.sh` に試験を足す: 一時リポジトリで 15 日前の時刻にした部屋を作り、`--execute` 後に部屋なし・ブランチあり・写し 6 種の照合 |
| PR が開いている・使用中・鍵付き・13 日の部屋は消えない | 同じ試験で 4 件が残る |
| 写しから元に戻せる | 試験: reaper-restore.sh（新設）後の `git status --porcelain` と各ファイルの sha256 が消す前と同じ |
| 照合が合わないと消さない | 試験: patch の書き出しを失敗させて部屋が残る |
| 失う道・誤って消す道を止める | 試験で各 1 件、部屋が残る（または写しが合う）: gh が失敗する／写しが 200MB を超える／fetch が失敗する／入れ子のリポジトリがある／置き場が既にある／空き容量が足りない |
| 消えたファイル・ステージ済み・未ステージが戻る | 試験: 3 種を混ぜた部屋を消して戻し、`git status --porcelain` と sha256 が同じ |
| 写しの確かめが、ステージ済みと未ステージが同じファイルに重なる部屋でも通る | 試験: 同じファイルに両方の変更がある部屋を消して戻し、status と sha256 が同じ |
| 照合に失敗した写しが溜まらない | 試験: 照合を失敗させて 2 回流し、`reaper-archive` に `.tmp` も写しも増えない |
| 部屋が 0 件で終わる回・dry-run の回でも数の行が出る | 試験で行を grep |
| 時刻の数え方が status で動かない | 試験: 15 日前の部屋に回収を 2 回流し、index の時刻が変わらない。消えたファイルがある部屋も対象になる |
| detached・鍵付きは本番の走査で扱う | 試験は `REAPER_WORKTREES_DIR` の形ではなく、本番の走査（既存の試験の detached の形）で流す |
| detached の部屋も同じに扱われ、`~/.salesanchor-tools` は残る | 試験: detached・届かないコミット 1 件の部屋が bundle 付きで消える／`$HOME/worktrees` の外の部屋は残る |
| ログに「作業場所の数」と「片付け N 件 / 写し N 件」が出る | 試験で行を grep |
| 70 件超で知らせが出る | `scripts/tests/test-mac-jobs-watch.sh` に試験を足す。本番では `MJW_WT_HIGH=1 bash scripts/mac-jobs-watch.sh` を 1 回流し Discord に 1 通（K14） |
| K11 の見込み | 便1 の最初に `--dry-run` の候補数で 65−N ≤50 を確かめる |
| K11 | 合流の翌朝のログで ≤50 |
| K12 | 30 日後にログを数える |

## 9. 実施の順（便）

- 便1: 3-1〜3-5・3-7（自動回収と戻しの台本・試験）。合流後の最初の 03:00 で K11 を測る。
- 便2: 3-6（知らせ）。K14 を測る。
- 30 日後: K12 を数える。

本店で動く台本（`scripts/`）を変えるため、合流前に PO の実装承認と GO（ADR-136）を取る。

## 10. 外部・過去事例の参照と我々への応用

なし。理由: 調べる対象は自分の Mac の作業場所の片付け方で、外の事例の数字が判断を変えない。使う git の決まり（`locked` 行・`git worktree lock`・`git bundle`）は Context7 `/git/htmldocs` の git-worktree の説明で確かめた（recon §5）。

## 維持の仕組み

- 守り手: `scripts/tests/test-reaper-safety.sh`（置き忘れの片付け・写しの照合・戻し）と `scripts/tests/test-mac-jobs-watch.sh`（70 件の知らせ）。
- 見張り: 毎朝の自動回収のログの「作業場所の数」と、mac-jobs-watch の 70 件の知らせ。
- 決まりの正本: ADR-114 R13。
