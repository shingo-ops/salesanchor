# 実装カード 段5a — 手元の記録（commit）でも行数の上限超えで止める・AGENTS.md の未登録も見つける

> この文書は何か：doc-agenda-nav 段5a の作業指示書です。frontend/.husky/pre-commit が行数検査の失敗を見落としている1行を直し、check-claude-size.js の未登録探しに AGENTS.md を足します。

- 設計: docs/handoff/doc-agenda-nav/design.md
  - §26: 段5の設計判断（この便の根拠。§26-3 が作り方と受け入れ基準）
  - §24 G7 の残り（pre-commit:52 が終了コードを見ていない）
  - §8 段5の行
- 対象ADR: ADR-1040（Accepted）。関連: ADR-076
- 状態: 設計は Opus の設計判断（§26、2026-10-25）。PO の承認は 2026-10-25 の「1」（見張りを強める段へ進む：文書の行数が上限を超えたら手元で記録するときにも止まる）。
- 危険便かどうか: 触る2ファイルは scripts/check-process-artifacts.js の DANGEROUS_PATTERNS に当たらない（§26-1）。GO は ADR-1003 の委譲により Opus が書きます（担当は GO 記録を書かず、マージもしない）。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装と確かめ: Sonnet（model "sonnet"）
  - 審査: Opus（reviewer を model "opus" で新しく起こす）
  - GO とマージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段5a の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

- やること: §4 の2ファイルの書き換えと、§5 の確かめ、PR の作成。
- やらないこと:
  - pre-commit の他の行（:43 lint-staged・:48 dark-parity など）を変えない。`set -e` を足さない。
  - LIMITS の表（check-claude-size.js:24-34）の数値と行を変えない。tools/claude-channels/intake/CLAUDE.md を登録しない。
  - .github/workflows/ を触らない（5b は別の便）。
  - 未登録の警告を失敗に変えない。

## 2. 前提の事実（Opus が 2026-10-25 に確かめた。起点は origin/main 6a5047685）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | 作業場所のフックの置き場は frontend/.husky で、pre-commit は `#!/bin/sh` のまま `set -e` なしに動く | scripts/new-worktree.sh:113-115、`git config --get core.hooksPath` が frontend/.husky、frontend/.husky/pre-commit:1 |
| F2 | pre-commit:52 は `node "$REPO_ROOT/frontend/scripts/check-claude-size.js"` だけで、失敗しても次へ進む | frontend/.husky/pre-commit:52 |
| F3 | check-claude-size.js:40 の find は CLAUDE.md だけを探し、`./node_modules/*` しか除かない | frontend/scripts/check-claude-size.js:39-42 |
| F4 | 起点の AGENTS.md は根・frontend・backend の3本で、3本とも LIMITS に登録済み | `git ls-files`、check-claude-size.js:25・:28・:30 |
| F5 | backend/AGENTS.md は 70行で、上限 70 ちょうど | check-claude-size.js:30、段4の審査の参考指摘 |
| F6 | 今の実行は警告1件（tools/claude-channels/intake/CLAUDE.md）・PASSED・rc=0 | この作業場所での実行 |

一つでも実物と違えば、§6 の分岐に従う。

## 3. 触るファイル（これ以外は触らない）

| ファイル | 変えるところ |
|---|---|
| frontend/.husky/pre-commit | :52 の1行 |
| frontend/scripts/check-claude-size.js | :21-23 のコメント、:36-46 の未登録探し |

## 4. 作り方

### 4-1. frontend/.husky/pre-commit（Edit。1行だけ）

変更前:

```
node "$REPO_ROOT/frontend/scripts/check-claude-size.js"
```

変更後:

```
node "$REPO_ROOT/frontend/scripts/check-claude-size.js" || exit 1
```

### 4-2. frontend/scripts/check-claude-size.js（Edit）

変更前（:21-23）:

```
// 各 CLAUDE.md の上限行数（超過すると CI / pre-commit がブロック）
// 新規サブディレクトリ CLAUDE.md を追加した場合はここに登録すること（ADR-076）
// 例: { path: 'backend/db/CLAUDE.md', limit: 70 },
```

変更後:

```
// 各 AGENTS.md・CLAUDE.md の上限行数（超過すると CI / pre-commit がブロック）
// 新規サブディレクトリ AGENTS.md・CLAUDE.md を追加した場合はここに登録すること（ADR-076・ADR-1040）
// 例: { path: 'backend/db/CLAUDE.md', limit: 70 },
```

変更前（:36-46）:

```
// LIMITS に未登録のサブディレクトリ CLAUDE.md を自動検出して警告（ADR-076）
const registeredPaths = new Set(LIMITS.map(l => l.path));
try {
  const found = execSync(
    'find . -name "CLAUDE.md" -not -path "./node_modules/*" -not -path "./.git/*" -not -name "./CLAUDE.md"',
    { encoding: 'utf8', cwd: repoRoot }
  ).trim().split('\n').filter(Boolean).map(p => p.replace(/^\.\//, ''));
  for (const p of found) {
    if (p !== 'CLAUDE.md' && !registeredPaths.has(p)) {
      console.warn(`⚠️  ${p}: LIMITS 未登録 — check-claude-size.js の LIMITS 配列に追加してください（ADR-076）`);
    }
```

変更後:

```
// LIMITS に未登録のサブディレクトリ AGENTS.md・CLAUDE.md を自動検出して警告（ADR-076・ADR-1040）
// node_modules の中（例: パッケージ同梱の AGENTS.md）は数えない
const registeredPaths = new Set(LIMITS.map(l => l.path));
try {
  const found = execSync(
    'find . \\( -name "CLAUDE.md" -o -name "AGENTS.md" \\) -not -path "*/node_modules/*" -not -path "./.git/*"',
    { encoding: 'utf8', cwd: repoRoot }
  ).trim().split('\n').filter(Boolean).map(p => p.replace(/^\.\//, ''));
  for (const p of found) {
    if (p !== 'CLAUDE.md' && p !== 'AGENTS.md' && !registeredPaths.has(p)) {
      console.warn(`⚠️  ${p}: LIMITS 未登録 — check-claude-size.js の LIMITS 配列に追加してください（ADR-076・ADR-1040）`);
    }
```

- JavaScript の文字列の中なので、find の括弧は `\\(`・`\\)` と書く（シェルに渡るときは `\(`・`\)` になる）。
- :47-77 は変えない。

## 5. 確かめ方

生出力はすべて `/tmp/CC報告ファイル/an-s5/impl/` に保存する（無ければ作る）。各コマンドは作業場所への cd から始める。

### 5-0. 変更前の値（§4 より先に実行する）

1. `cp backend/AGENTS.md /tmp/CC報告ファイル/an-s5/impl/backend-AGENTS.bak`
2. `printf 'x\n' >> backend/AGENTS.md` の後に `sh frontend/.husky/pre-commit > /tmp/CC報告ファイル/an-s5/impl/t1-before.txt 2>&1; echo rc=$? >> /tmp/CC報告ファイル/an-s5/impl/t1-before.txt`
3. `cp /tmp/CC報告ファイル/an-s5/impl/backend-AGENTS.bak backend/AGENTS.md` の後に `git diff --exit-code backend/AGENTS.md`（rc=0）
4. `mkdir -p tools/s5probe` と Write で tools/s5probe/AGENTS.md（中身は `probe` の1行）を作り、`node frontend/scripts/check-claude-size.js > /tmp/CC報告ファイル/an-s5/impl/t3-before.txt 2>&1; echo rc=$? >> /tmp/CC報告ファイル/an-s5/impl/t3-before.txt`。その後 tools/s5probe/AGENTS.md と tools/s5probe を消す（`rm tools/s5probe/AGENTS.md` と `rmdir tools/s5probe`）。

期待: t1-before は rc=0（止まらない＝直す前の穴）で「❌ backend/AGENTS.md: 71行（上限70行）」が出る。t3-before に tools/s5probe/AGENTS.md は出ない。

### 5-1. 変更後の T1（上限超えで止まる）

5-0 の 1〜3 と同じ手順で、出力先を t1-after.txt にする。期待: rc=1 と「❌ backend/AGENTS.md: 71行（上限70行）」。戻した後の `git diff --exit-code backend/AGENTS.md` が rc=0。

### 5-2. T2（上限内なら止まらない）

何も足さずに `sh frontend/.husky/pre-commit > /tmp/CC報告ファイル/an-s5/impl/t2.txt 2>&1; echo rc=$? >> /tmp/CC報告ファイル/an-s5/impl/t2.txt`。期待: rc=0、「✅ CLAUDE.md サイズチェック PASSED」。

### 5-3. T3（AGENTS.md の未登録を見つける）

5-0 の 4 と同じ手順で、出力先を t3-after.txt にする。期待: 「⚠️  tools/s5probe/AGENTS.md: LIMITS 未登録」が出て rc=0。消した後に `node frontend/scripts/check-claude-size.js > /tmp/CC報告ファイル/an-s5/impl/t3-clean.txt 2>&1` で、警告は tools/claude-channels/intake/CLAUDE.md の1件だけ。

### 5-4. T4（node_modules の中は数えない）

`mkdir -p frontend/node_modules/s5probe` と Write で frontend/node_modules/s5probe/AGENTS.md（`probe` の1行）を作り、`node frontend/scripts/check-claude-size.js > /tmp/CC報告ファイル/an-s5/impl/t4.txt 2>&1`。期待: s5probe は警告に出ない。その後 `rm frontend/node_modules/s5probe/AGENTS.md` と `rmdir frontend/node_modules/s5probe`。frontend/node_modules が空になったら `rmdir frontend/node_modules`（作業前から在った場合は残す。作業前の有無を 5-0 の前に `ls -d frontend/node_modules` で記録する）。

### 5-5. T5（文法）

`sh -n frontend/.husky/pre-commit; echo rc=$?` と `node --check frontend/scripts/check-claude-size.js; echo rc=$?` を t5.txt に保存。期待: どちらも rc=0。

### 5-6. 差分

`git diff $(git merge-base origin/main HEAD) --stat > /tmp/CC報告ファイル/an-s5/impl/diff-stat.txt` と同じ起点の `git diff` 全文を diff.txt に保存。期待: 製品側の変更は §3 の2ファイルだけ（docs/handoff/doc-agenda-nav/ の design.md・card-stage5a.md は Opus のコミット）。`git status --short` で tools/s5probe・frontend/node_modules/s5probe が残っていないこと。

## 6. 分岐ごとの対処

| 起きたこと | 対処 |
|---|---|
| §2 の F1〜F6 のどれかが実物と違う | 書き換えずに NEEDS_DECISION: 違った事実と実物の出力 |
| §4 の変更前の文が見つからない・2か所ある | 書き換えずに BLOCKED: 見つかった行番号 |
| 5-0 の t1-before が rc=1（もう止まっている） | 書き換えずに NEEDS_DECISION: t1-before の全文のパス |
| 5-1 が rc=0 のまま | §4-1 の1行を見直す。直らなければ BLOCKED: |
| `npx lint-staged` が網の取得で長く止まる・対話を求める | 待たずに止め、BLOCKED: 出力の全文のパス |
| commit がフックで止まる | 言い換えて再試行しない。止めた文の原文で BLOCKED: |
| backend/AGENTS.md が写しに戻らない | 以降を止めて BLOCKED:（勝手に git checkout しない） |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 上限超えで手元が止まる | t1-before rc=0・t1-after rc=1、どちらも「71行（上限70行）」が出る |
| 上限内なら止まらない | t2 rc=0。この便の commit が成功する |
| AGENTS.md の未登録を見つける | t3-before に出ない・t3-after に出る。t3-clean は警告1件 |
| node_modules の中は数えない | t4 に s5probe が出ない |
| 文法 | t5 の2つが rc=0 |
| 触ったのは2ファイルだけ | diff-stat.txt |
| 試しの書き足しが残っていない | `git status --short` と `git diff --exit-code backend/AGENTS.md` |

## 8. 戻し方

PR を revert する（2ファイル）。

## 9. PR

- 作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage5。Opus が作成済み（origin/main 6a5047685 が起点）で、このカードと design.md §26 のコミットも入っている。担当は作り直さない。
- commit は1つ（2ファイル）。メッセージは `fix: 手元の記録でも行数の上限超えで止める・AGENTS.md の未登録も見つける（doc-agenda-nav 段5a）`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- push は `git push -u origin release/doc-agenda-nav-stage5`。
  - commit の後に `git log -1 --oneline` で確かめる。
  - push の後に `git log origin/release/doc-agenda-nav-stage5 -1 --oneline` で確かめる。
- PR の作り方:
  - `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-s5/pr-body.md` を作り、別のコマンドで `--body-file` に渡す（同じコマンドで作ると pr-body-guard に止められる）。
  - 作る前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
  - ready で作る。base は main。タイトルは `fix: doc-agenda-nav 段5a 手元の記録でも行数の上限超えで止める`。担当はマージせず、GO 記録も書かない。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` には次を書く。
  - `recon: docs/handoff/doc-agenda-nav/recon.md`
  - `設計: docs/handoff/doc-agenda-nav/design.md`
  - `対象ADR: ADR-1040（関連: ADR-076）`
  - `設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`
  - `触るファイル: frontend/.husky/pre-commit, frontend/scripts/check-claude-size.js, docs/handoff/doc-agenda-nav/design.md, docs/handoff/doc-agenda-nav/card-stage5a.md`
  - `削除するファイル: frontend/.husky/pre-commit, frontend/scripts/check-claude-size.js, docs/handoff/doc-agenda-nav/design.md`
  - `区分: A（ADR-1015。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`
  - `PO承認: 「1」（2026-10-25）`
  - `Opus 審査記録: コード審査はこれから`
- 本文には §7 の各基準の結果（t1-before・t1-after の rc と ❌ の行、t3-before・t3-after の警告の行）を貼る。
- 作る前に、`scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了の報告に書くこと:
  - 冒頭の受領文
  - §5-0〜5-6 の結果（rc と該当行。全文はファイルのパス）
  - PR の URL
  - 新しい HEAD の sha
  - 判断が必要だった点（事実のみ）
- 停止したときに書くこと:
  - 止まった手順の番号
  - 最後に実行したコマンド
  - 止まった理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれかにする。
- 委任のときの決まり:
  - sleep しない。
  - ファイルの作成と編集は Write/Edit ツールで行う（§5 の cp・printf の一時的な書き足しと戻し、試しのファイルの rm・rmdir を除く）。
  - PR を作る前に validate-pr-body.sh で exit 0 を確かめる。
  - フックや自動判定に止められたら、言い換えて再試行しない。

## 11. 報告欄（担当が追記）

- 2026-10-25 Sonnet: §5-0〜5-6 全て期待どおり（t1-before rc=0・t1-after rc=1、どちらも「71行（上限70行）」／t2 rc=0／t3-after に tools/s5probe/AGENTS.md の警告・t3-clean は警告1件／t4 s5probe 0件／t5 両方 rc=0）。生出力は /tmp/CC報告ファイル/an-s5/impl/。試し書き足しは残っていない。

END OF CARD
