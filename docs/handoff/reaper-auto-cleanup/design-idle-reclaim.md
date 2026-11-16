# design: 置き忘れの作業場所を、写しを取ってから自動で片付ける

この文書は何か：PR を作らずに終わった作業の部屋と審査の写しが溜まり、上限 100 に達する件の直し方と、その副作用を書いたもの。
親（設計仕様書）: [docs/specs/reaper-auto-cleanup/README.md](../../specs/reaper-auto-cleanup/README.md)
recon: [recon-idle-reclaim.md](recon-idle-reclaim.md)
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
| I4 | 使用中でない（既存チェック 1.5） | 残す |
| I5 | 鍵がかかっていない（`git worktree list --porcelain` に `locked` 行が無い） | 残す |
| I6 | そのブランチの PR が開いていない（`gh pr list --state open --head <branch>` が 0 件。gh が失敗したら残す） | 残す |
| I7 | 最後に触ってから `REAPER_IDLE_DAYS`（既定 14）日以上 | 残す |
| I8 | 入れ子のリポジトリが無い（既存 R11） | 残す |
| I9 | 写しが取れて照合が合った（3-3） | 残す |

- 台帳の状態（IN_PROGRESS 等）は I1〜I9 の判定に使わない。完了の判定ではなく「部屋だけ片付け、ブランチと台帳はそのまま」だから（ADR-114 §1 の「完了判定に経過時間を使わない」は守る）。
- 既存の「DONE・合流済・閉じた PR」の回収（チェック 3）は今までどおり。置き忘れの判定は、既存の回収で消えなかった部屋（`SKIP_IN_PROGRESS`・`SKIP_UNSAVED`・`SKIP_NOT_MERGED` に入った部屋）と detached の部屋（3-4）にだけ行う。
- fetch が失敗した回は既存どおり何も消さない（:378-381）。

### 3-2. 「最後に触った日」の数え方

次の時刻のうち一番新しいもの。どれか 1 つでも読めなければ「今」とみなす（消さない側に倒す）。

- HEAD のコミット時刻（`git log -1 --format=%ct HEAD`）
- 部屋の gitdir の `index` と `HEAD` ファイルの更新時刻
- `git status --porcelain --untracked-files=all` に出る各ファイルの更新時刻

### 3-3. 写しの取り方と照合

置き場: `<git-common-dir>/reaper-archive/<YYYYMMDD>/<部屋の名前>/`（git の管理外・push されない。R9 の `reaper-drafts` と同じ考え方）。

| ファイル | 中身 |
|---|---|
| `head.txt` | ブランチ名・HEAD の sha・部屋のパス・最後に触った日 |
| `status.txt` | `git status --porcelain --untracked-files=all --ignore-submodules=all` |
| `tracked.patch` | `git diff HEAD --binary`（記録していない変更） |
| `untracked.tar` | `git ls-files --others --exclude-standard -z` の全ファイル |
| `ignored.tar` | 無視ファイルのうち、`node_modules`・`.venv`・`dist`・`build`・`__pycache__`・`.pytest_cache`・`.mypy_cache`・`coverage` の下以外 |
| `unpushed.bundle` | origin から届かないコミットがあるときだけ（`git bundle create ... HEAD --not --remotes=origin`） |

照合（1 つでも合わなければ消さない）:
- `tracked.patch`（`git diff HEAD --binary --no-renames`）の `diff --git` の数＝status（`--no-renames`）の追跡ファイルの変更数
- `untracked.tar` の中身の数＝status の `??` の数
- `unpushed.bundle` があるとき `git bundle verify` が成功
- 写し全体が `REAPER_ARCHIVE_MAX_MB`（既定 200）以下。超えたら消さずにログに名前を出す

消した後: ログに「置き忘れを片付け: <部屋> → 写し <置き場>」を 1 行ずつ、最後に「片付け N 件 / 写し N 件」。

### 3-4. 写し（detached）の部屋も見る

本番の走査で branch 行の無い部屋を飛ばしている所（`scripts/reaper-worktree.sh:164-191`）で、detached の部屋を別の一覧に集める。3-1 の I1・I3〜I9 を当てる（I2・I6 はブランチが無いので飛ばす）。detached はブランチが残らないため、origin から届かないコミットがあれば `unpushed.bundle` を必ず作る。

### 3-5. 毎回の数の記録

自動回収の最後に 1 行出す: `作業場所の数: <N>（上限 <WORKTREE_LIMIT> ・知らせる線 70）`。N は `git worktree list --porcelain` の `worktree` 行の数から本店の 1 を引いた数。K11・K12 はこの行で数える。

### 3-6. 70 件を超えたら知らせる（`scripts/mac-jobs-watch.sh`）

空き容量の知らせ（disk-low）と同じ形で `wt-high` を足す。

- 設定: `MJW_WT_HIGH`（既定 70）・`MJW_WT_OK`（既定 60）・`MJW_MAIN_REPO`（既定 `$HOME/salesanchor`）を `mjw_config` に足す。
- 判定: 数が `MJW_WT_HIGH` を超えたら問題 `wt-high`。`MJW_WT_OK` 以下に戻ったら解消。間は前の状態のまま（行ったり来たりで何度も鳴らさない）。
- 文: 「作業場所が <N> 件あります（70 件を超えました）。夜の自動片付けで減らない部屋は、PR が開いたままか、使用中か、鍵がかかっています。」
- くり返し: 既存の `MJW_REPEAT_SECONDS`（1 日）。

### 3-7. 戻し方（片付けた部屋を元に戻す）

1. `git worktree add <元のパス> <ブランチ>`（detached のときは `head.txt` の sha）
2. `unpushed.bundle` があれば `git fetch <bundle> HEAD` してから `git reset --hard FETCH_HEAD`
3. `git apply --binary tracked.patch`
4. `tar -xf untracked.tar`・`tar -xf ignored.tar`（部屋の中で）

この手順を `scripts/reaper-restore.sh <写しの置き場>` 1 本にまとめる（読むのは写しだけ・本店以外は触らない）。

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
| D | 14 日触っていない・PR が開いていない部屋を、写しを取って片付ける | 約 20 件減り 45 件 | **採用** |
| D' | D を 30 日にする | 約 6 件減り 59 件（K11 を満たさない） | 不採用 |
| D'' | D を 7 日にする | もっと減るが、PO の答え待ちの作業を巻き込みやすい | 不採用 |
| E | 部屋と一緒にブランチも消す | 戻せなくなる | 不採用 |

## 6. 弊害とリスク

| リスク | 対処 |
|---|---|
| PO の答え待ちで 14 日止まった作業の部屋が消える | ブランチと写しが残り、3-7 で戻せる。長く置きたい部屋は `git worktree lock --reason "<理由>"` で外せる（I5） |
| 写しが Mac の容量を食う | 1 部屋 200MB の上限・node_modules 等は写さない。`reaper-archive` を 90 日で消すかは 30 日の観測後に決める（今回は消さない） |
| 無視ファイルの中の手書きの記録が写しから漏れる | `ignored.tar` で無視ファイルも写す（作り直せる大きな置き場だけ除く） |
| 無視ファイルに `.env` 等の鍵が入っていると写しにも入る | 置き場は同じ Mac の `.git` の中（push されない・元の部屋と同じ場所に同じ物があっただけ）。写しの置き場のファイル名と件数だけをログに出し、中身は出さない |
| 使用中の判定（cwd）は、部屋に cd せず絶対パスで書き込む作業を見落とす | そうした作業もファイルの更新時刻が変わるため、I7（14 日）で守られる |
| 走査の時間が延びる（部屋ごとに gh を 1 回） | 対象は既存の回収で残った部屋だけ。延びた秒数を実装の結果に書く |
| 安全条件「未保存は絶対に消さない」を変える | 写しの照合が合ったときだけ消す。ADR-114 R13 に書き、PO 承認の KGI K13 で守る |

## 7. ADR-114 R13（実装の PR で ADR に足す文案）

§5 安全条件に足す:
「置き忘れの部屋（2026-11-17 R13）：`$HOME/worktrees/` の下にあり、PR が開いておらず、使用中でも鍵付きでもなく、最後に触ってから `REAPER_IDLE_DAYS`（既定 14）日以上の部屋は、記録していない変更・新しいファイル・無視ファイル（作り直せる置き場を除く）・origin から届かないコミットを `<git-common-dir>/reaper-archive/` に写し、照合が合ったときだけ部屋を消す。ブランチと台帳は変えない。detached の部屋も同じ。戻しは `scripts/reaper-restore.sh`。」

改訂履歴に 1 行足す。

## 8. 受け入れ条件

| 基準 | 検証方法 |
|---|---|
| 置き忘れの部屋（14 日・PR なし）が写しを取って消え、ブランチは残る | `scripts/tests/test-reaper-safety.sh` に試験を足す: 一時リポジトリで 15 日前の時刻にした部屋を作り、`--execute` 後に部屋なし・ブランチあり・写し 6 種の照合 |
| PR が開いている・使用中・鍵付き・13 日の部屋は消えない | 同じ試験で 4 件が残る |
| 写しから元に戻せる | 試験: `reaper-restore.sh` 後の `git status --porcelain` と各ファイルの sha256 が消す前と同じ |
| 照合が合わないと消さない | 試験: patch の書き出しを失敗させて部屋が残る |
| detached の部屋も同じに扱われ、`~/.salesanchor-tools` は残る | 試験: detached・届かないコミット 1 件の部屋が bundle 付きで消える／`$HOME/worktrees` の外の部屋は残る |
| ログに「作業場所の数」と「片付け N 件 / 写し N 件」が出る | 試験で行を grep |
| 70 件超で知らせが出る | `scripts/tests/test-mac-jobs-watch.sh` に試験を足す。本番では `MJW_WT_HIGH=1 bash scripts/mac-jobs-watch.sh` を 1 回流し Discord に 1 通（K14） |
| K11 | 合流の翌朝のログで ≤50 |
| K12 | 30 日後にログを数える |

## 9. 実施の順（便）

- 便1: 3-1〜3-5・3-7（自動回収と戻しの台本・試験）。合流後の最初の 03:00 で K11 を測る。
- 便2: 3-6（知らせ）。K14 を測る。
- 30 日後: K12 を数える。

本店で動く台本（`scripts/`）を変えるため、合流前に PO の実装承認と GO（ADR-136）を取る。

## 10. 外部事例

なし。理由: 調べる対象は自分の Mac の作業場所の片付け方で、外の事例の数字が判断を変えない。使う git の決まり（`locked` 行・`git worktree lock`・`git bundle`）は Context7 `/git/htmldocs` の git-worktree の説明で確かめた（recon §5）。

## 維持の仕組み

- 守り手: `scripts/tests/test-reaper-safety.sh`（置き忘れの片付け・写しの照合・戻し）と `scripts/tests/test-mac-jobs-watch.sh`（70 件の知らせ）。
- 見張り: 毎朝の自動回収のログの「作業場所の数」と、mac-jobs-watch の 70 件の知らせ。
- 決まりの正本: ADR-114 R13。
