# recon — 開発データの自動片付け（disk-janitor）

基準: origin/main（HEAD 713e9149f）。根拠の生データは /tmp/CC報告ファイル/disk-cleanup/（phase2・phase3・auto-review）。推測は書かない。

## 既存 ADR の検索結果（着手前）
- `git grep -i` と `docs/adr/FEATURE-INDEX.md` で worktree 回収・片付けを検索 → ADR-114（`/Users/tanizawashingo/worktrees/salesanchor/release-disk-janitor-tools-copy/docs/adr/ADR-114-worktree-auto-cleanup.md`）が reaper の正本。
- 危険パス・GO 手順: ADR-135・ADR-136（`CLAUDE.md` の ADR-136 項）・ADR-1003。不可逆操作: `CLAUDE.md:36`。
- npm キャッシュ・不要物の片付けを定めた ADR は無し（本件が初）。

## 事実（file:line）
1. npm キャッシュが散らばる原因: `~/.npmrc` の `cache=./.npm-cache` が実行場所の相対パス。実測 `/tmp/CC報告ファイル/disk-cleanup/phase3/npm.txt:2`（`cache=./.npm-cache`）。/tmp→/private/tmp/.npm-cache、~→~/.npm-cache、agent-console→agent-console/.npm-cache（同ファイルの実測）。D1 は `cache=/Users/tanizawashingo/.npm-shared-cache`（crm-app と同じ共有の置き場）に変更済み（旧 .npm-cache は root 所有のファイルがあり EACCES になったため。改訂 2）（現在の ~/.npmrc で確認）。
2. reaper は salesanchor 専用で PR の行き先が main 固定: 変更前 `/Users/tanizawashingo/worktrees/salesanchor/release-disk-janitor-tools-copy/scripts/reaper-worktree.sh:235`（`select(.baseRefName=="main")`）、`:282`、`:297`、リポジトリ名の既定 `:65`。MAIN_REPO_ROOT は作業場所から決まる（`:59`、`:61`）。使用中判定は cwd のみ（`:164`）。→ 本 PR で `REAPER_BASE_BRANCH` 化。
3. agent-console の旧版: `ac_install_version` は `versions/<tag>` に足すだけ（`/tmp/CC報告ファイル/disk-cleanup/phase3/ac.txt:20`）、切り戻し先は current の1つ前（semver 順・`ac.txt:440`-`ac.txt:455` の ac-rollback.sh）。実機: current -> versions/v0.9.1、versions は v0.2.0〜v0.9.1 の17版。
4. 自動で消えるので対処しない物: Claude Code の一時ファイル・会話記録は `cleanupPeriodDays` 既定30日（`/tmp/CC報告ファイル/disk-cleanup/phase3/doc-scratchpad.txt:3`）。/tmp の報告ファイルは tmp_cleaner が3日超を削除（`/tmp/CC報告ファイル/disk-cleanup/phase2/summary.md:12`）。
5. CI はシェルの試験を実行しない: `/tmp/CC報告ファイル/disk-cleanup/phase3/shell-ci.txt:1`（bash -n / shellcheck のみの workflow 一覧）。→ 試験は変更時に手で実行して evidence に残す。
6. 設計審査: `/tmp/CC報告ファイル/disk-cleanup/auto-review/architect-review-v1-rev1.yaml`（APPROVE・LOW L1/L2）。範囲の実測は `auto-review/14-lsof-Fpn.txt`、`15-sa-worktrees.tsv`、`16-r2-table.tsv`。
7. salesanchor の worktree でブランチが main/develop なのは本体のみ: `evidence/sa-main-develop-worktrees.txt`（`/Users/tanizawashingo/salesanchor [main]` 1行）。reaper は最初の項目（本体）を走査しない（`scripts/reaper-worktree.sh` の本番モードの `_IS_FIRST`）ので、保護を足しても salesanchor の動きは変わらない。

## 実機 dry-run の結果（evidence 参照）
- 生出力: `/Users/tanizawashingo/worktrees/salesanchor/release-disk-janitor-tools-copy/docs/handoff/disk-janitor/evidence/dry-run.txt`
- 規則ごとの候補: R1 55件 3.7GB、R2 4件 1.6GB、R3 15件 4.6GB、R4 9件（reaper の判定。容量は reaper が出さない）。
- 前後: `evidence/before.txt`、`evidence/after.txt`（df 変化なし）、`evidence/candidates-exist-after.txt`（候補の消失 0）。
- 保護: `evidence/protection-check.txt`。
- 試験: `evidence/test-disk-janitor.txt`、`evidence/test-reaper-safety.txt`、構文・静的解析: `evidence/syntax-shellcheck.txt`。

## 設計で未確認・実装時に判明した点
- R2 の候補 4件のうち 2件（`~/worktrees/fix-sold-out-menu-visibility`・`~/worktrees/supplier-knowledge-links`、いずれも salesanchor の作業用コピー）は、審査時の表（16-r2-table.tsv）に無い場所（`~/worktrees/<名前>/frontend`）。R2 の条件（package-lock.json あり・14日更新なし・最終コミット 2026-09-20/09-25・使用中でない）には当たる。
- R2 で「最終コミット時刻を取得できない（残す）」が 22件: gitdir の指し先（例 `/Users/tanizawashingo/crm-app-new/.git/worktrees/...`）が存在しない作業用コピー。L1 に従い残す。容量は回収されない。
