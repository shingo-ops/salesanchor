<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。このPRに含まれない新しいファイルにはバッククォートを付けない。 -->
# 実装カード 便1 — 置き忘れの作業場所を、写しを取ってから自動で片付ける

**設計の正本**: `docs/handoff/reaper-auto-cleanup/design-idle-reclaim.md` §3-1〜§3-5・§3-7・§7・§8。このカードは手順と点検だけを足す。設計と食い違ったら設計が正。  
**設計審査**: 2026-11-17 5 回目 APPROVE（`docs/handoff/reaper-auto-cleanup/review-opus-idle-reclaim.md`）。  
**PO 承認**: 2026-11-17「1」（この決まりで実装に進む）。合流前に PO の GO を別に取る（設計 §9・ADR-136）。  
**基準の main**: 337ebbd1b（設計が頼る 8 ファイルは分岐点 2adefae2e から変わっていないことを `git diff --stat` で確かめ済み。差分 0 行）。  
**実装担当**: クラウドの Sonnet。**ブランチ**: release/worktree-idle-reclaim-design（このカードと同じブランチに積む。PR #5559）。

## 1. 触るファイル（これ以外は触らない）

- `scripts/reaper-worktree.sh` — 設計 §3-1〜§3-5
- `scripts/new-worktree.sh` — :66-68 の回収の呼び出しに `REAPER_IDLE_MAX_PER_RUN=10` を付ける 1 か所だけ（設計 §3-3）
- scripts/reaper-restore.sh（新規）— 設計 §3-7
- `scripts/tests/test-reaper-safety.sh` — 設計 §8 の試験（便2 の知らせの行と K11・K12 の行を除く全部）
- `docs/adr/ADR-114-worktree-auto-cleanup.md` — 設計 §7 の文案。その後 `node scripts/generate-adr-index.js` を流し `docs/adr/README.md` も一緒に commit
- `docs/handoff/reaper-auto-cleanup/design-idle-reclaim.md` — 先頭近くの状態だけ（「便1 実装済み・未合流」）

触らない: `.github/`（`.github/workflows/reaper-schedule.yml` を含む）、`scripts/mac-jobs-watch.sh`（便2）、`scripts/git-safe.sh`、`WORKTREE_LIMIT` の値、既存の回収（DONE・合流済・閉じた PR）の条件と R8〜R12、`backend/`・`frontend/`・`migrations/`。

## 2. 手順

1. 配られた写しの最上位で `git fetch origin main release/worktree-idle-reclaim-design` → `bash scripts/new-worktree.sh release/worktree-idle-reclaim-design`（origin/main から作られる）→ 出力に出た場所へ cd し、以後すべてその中で作業する → その中で `git merge --no-edit origin/release/worktree-idle-reclaim-design`（ぶつかったら BLOCKED:）。clone のままの commit は見張り（worktree 外での作業の禁止）に止められる（2026-11-17 1 回目で実測）。`./scripts/dev/executor-preflight.sh` を流し、結果を生で残す（クラウドで通らない項目があれば、その行を生で出して続ける）。
2. 変更前に `bash scripts/tests/test-reaper-safety.sh` を流し、今の合否を生で残す（基準）。
3. 設計 §3-5 の trap と `_LINK_OK` から書く（`trap _reaper_on_exit EXIT; trap 'exit 130' INT; trap 'exit 143' TERM`。`_LINK_OK` は判定を別の変数で行い、合ったときだけ最後に 1 を置く）。台本の最初に `export GIT_OPTIONAL_LOCKS=0`。
4. 設計 §3-2 の時刻の関数（`stat -f %m` と `stat -c %Y` の両方）→ §3-1 の候補の積み方（`IDLE_CANDIDATES`。detached は §3-4）→ §3-3 の写しと照合（作りかけは `.inprogress-` で始まる名前）→ 消す処理（既存の削除のループ :535-554 は使わない）→ §3-5 の数の行と reclaim.log の順に書く。
5. scripts/reaper-restore.sh（新規）を書く（§3-7。`reset --hard` は使わない。元のパスに何かあれば止まる）。
6. 設計 §8 の試験を `scripts/tests/test-reaper-safety.sh` に足す。時刻は `touch -t` などで 15 日前・13 日前を作る。gh は既存の試験と同じ差し替えの形で偽物にする（本物の GitHub に問い合わせない）。
7. `bash scripts/tests/test-reaper-safety.sh` を流し、全部の合否を生で残す。`bash -n` を 3 つの台本に流す。
8. ADR-114 に §7 の文を足す → `node scripts/generate-adr-index.js` → 一緒に commit。行番号は今の origin/main で読み直してから足す。
9. commit の最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。`git push origin release/worktree-idle-reclaim-design` で push して止まる。PR は作らない・本文を変えない・合流しない。

## 3. 想定される分岐（迷ったらここを見る。ここに無い分岐は止まって報告）

| 起きたこと | すること |
|---|---|
| 設計の行番号が実物とずれる | 中身で同じ場所を探す。中身も違えば止まる |
| 既存の試験が変更前から赤 | 赤の名前を生で出して続ける。自分の変更で増えた赤だけを直す |
| 既存の試験の作りでは detached・鍵付きを本番の走査で作れない | 止まる（`REAPER_WORKTREES_DIR` の形で代わりに試さない） |
| 試験を通すために既存の回収の条件や R8〜R12 を変えたくなる | 止まる |
| `.github/` や `scripts/mac-jobs-watch.sh` を変えたくなる | 止まる |
| `git worktree list --porcelain` に `locked` 行が出ない版の git | git の版を生で出して止まる |
| 本物の gh・本物の GitHub に問い合わせないと試せない | 止まる |
| 写しの照合を 1 つでも省きたくなる | 止まる |
| push が見張りに止められる | 言い換えず、止めた文を生で出して BLOCKED で終える |

## 4. 報告の形

生出力をそのまま。①preflight の結果 ②変更前の試験の合否 ③`git diff --stat origin/main...HEAD` ④変更後の試験の全出力 ⑤`bash -n` の結果 ⑥`git status --short` ⑦HEAD の sha と push の結果。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <問い> のどれか。

## 5. 受け入れ（Opus が確かめる）

| 基準 | 検証方法 |
|---|---|
| §1 のファイルだけが変わる | `git diff --name-only origin/main...HEAD` |
| 設計 §8 の試験（便1 分）が全部緑 | 報告④の生出力と CI |
| trap・`_LINK_OK`・`.inprogress-`・上限 30/10・古い順・成功だけ数える | diff を Opus が読む |
| K11 の見込み（65−N ≦50 かつ N ≦60） | 合流前に Opus が Mac で `bash scripts/reaper-worktree.sh --dry-run` を流し候補数を数える（クラウドでは測れない） |
| ADR index が最新 | CI「ADR index is up to date」 |
