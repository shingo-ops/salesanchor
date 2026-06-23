# 設計 — gate-diff-3dot（関所の差分を2点→3点に変更）

**対象ADR**: ADR-121
**recon**: docs/handoff/gate-diff-3dot/recon.md

## 問題の構造

ブランチが古い土台（develop の旧コミット）から作られると、その後 develop に入った変更が
`BASE_SHA`（develop 先端）と `HEAD_SHA`（feature 先端）の単純差分に混入し、
PR が実際には加えていないファイル（例: `scripts/reaper-worktree.sh`）が `hasDangerous=true` を引き起こして GO を誤要求する。

根本原因: `scripts/check-process-artifacts.js:529` の `git diff --name-only "${base}" "${head}"` は
**2点形式**（= 2つのコミット間の単純差分）であり、「このブランチが実際に加えた変更」ではなく
「develop 先端とfeature 先端の差」を返す。

## 解決策

2点形式 → 3点形式（`A...B`）に変更する。

`git diff --name-only "${base}...${head}"` は `merge-base(base, head)` から `head` までの差分を返す。
これはそのブランチが枝分かれ後に実際に加えた変更だけになる。

- fetch-depth はすでに `0`（全履歴）なので追加設定不要（`.github/workflows/process-artifacts-gate.yml:24`）。
- `changedFiles` は1回だけ生成され全分類の共通入力（`scripts/check-process-artifacts.js:538`）なので、この1行の変更で全判定が同時に正しくなる。

## 変更箇所（1行のみ）

| ファイル | 行 | 変更前 | 変更後 |
|---|---|---|---|
| `scripts/check-process-artifacts.js` | 529 | `git diff --name-only "${base}" "${head}"` | `git diff --name-only "${base}...${head}"` |

## 外部・過去事例の参照と我々への応用

GitHub 公式ドキュメント（[About comparing branches in pull requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-comparing-branches-in-pull-requests)）では、PR の "Files changed" タブが **3点形式**（`merge-base` からの差分）を標準として採用していることが明記されている。`gh pr diff` も同様に 3点形式を使う。

→ 我々の関所が「PR が実際に加えた変更」を判定するためには、同じく 3点形式が正解。2点形式は「2ブランチの現在の状態の差」であり、PR の意図した変更セットと一致しない。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| ブランチが古い土台でも、PR が加えた変更のみ差分に出る | §実機検証ケースA（古い develop 地点からブランチ、その後 develop に別変更が入った状態で docs のみ PR → GO 要求なし） |
| PR が本当に `scripts/` を変更した場合は引き続き GO を要求する | §実機検証ケースB（ブランチで `scripts/` を実際に変更した PR → GO を要求される） |
| 既存テストがすべて PASS する | `node scripts/tests/test-process-artifacts.js` |
| 新規テスト（3点形式のユニット検証）が PASS する | 同上テストスイートに追加したケースが ✅ 表示 |
