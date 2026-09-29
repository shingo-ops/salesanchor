# recon — 台帳DONE化の自動化（main）

> この文書は何か（専門用語なしの1行）:
> マージが終わったあとの作業記録の更新を機械にやらせる前に、
> いまの仕組みがどうなっているかを実際に見て記録したもの。

対象ADR: ADR-114
親テーマ: docs/specs/ledger-guard/README.md

## 実測（2026-09-02）

### 既存ワークフローが main では発火しない

.github/workflows/active-work-auto-done.yml:9 のトリガーが develop 限定である。
main へのマージでは発火しない。

同ファイル:42 の更新先が本体の台帳ファイル固定であり、
1ブランチ1ファイルの単票は対象外である。

checkout の ref も push 先も develop になっている。
ADR-114 の時代に作られたまま、ledger-guard 第2弾の書き先分割に追随していない。

### 別経路の自動化は commit しない

scripts/cleanup-worktree.sh:52 がマージ後に台帳を DONE 化する。
ただし commit も push もしないため、本店に残るだけである。
その結果、未追跡の台帳が 222 件溜まっていた（2026-09-02 実測）。

### 窓口スクリプトは Actions からも使える

scripts/ledger-update.sh:12 と scripts/ledger-update.sh:13 で、
環境変数により対象の場所を差し替えられる。

scripts/ledger-update.sh:18 で単票を優先し、
無ければ本体を見る仕組みになっている。

### 関所は台帳のみの変更を素通しする

scripts/check-process-artifacts.js:43 の分類定義に、
拡張子が md のファイルを書類とみなすパターンがある。
台帳ファイルは拡張子が md のため書類に分類される。

scripts/check-process-artifacts.js:683 で、書類のみの変更かつ正本を含まない場合に
「書類のみの変更 — 自動スキップ（pass）」を出力して終了する。

つまり台帳のみのPRは GO記録の検証に到達しない。

### main は直接 push できない

ruleset 15777895（main branch protection）の実測値:

- You can bypass: never
- bypass_actors は空
- rules に pull_request が含まれる
- required_status_checks は12件
- strict_required_status_checks_policy は true

したがって GitHub Actions も PR を経由する必要がある。

### PR自動作成の前例がある

.github/workflows/brand-asset-monitor.yml:220 に PR 自動作成の使用例がある。
ただしそちらは既定のトークンを使っている。

## 本便で追加する箇所

.github/workflows/ledger-auto-done-main.yml を新規作成する。
既存の .github/workflows/active-work-auto-done.yml:9 は変更しない。

---

## 追補：auto-merge の限定（2026-09-29）

> この節は何か（専門用語なしの1行）:
> 台帳の自動マージを「台帳の記録PRだけ」に限るために、着手前に現状と公式仕様を実際に見て記録したもの。

実測基準: origin/main = 36bf4dc14b7265c9f8845d37c378fa2139b4e089
対象ADR: ADR-050（追補先）、ADR-114
設計: docs/handoff/ledger-auto-done-main/design.md（追補節）

### 台帳ワークフローは既に自動マージを予約している（が、失敗を隠している）

- .github/workflows/ledger-auto-done-main.yml:137 で `gh pr merge --auto --merge "${PR_URL}"` を実行している。
- .github/workflows/ledger-auto-done-main.yml:139-141 は、予約に失敗すると `::warning::` を出して `exit 0` で終わる。ジョブは緑のままになる。
- リポジトリ設定の実測（`gh api repos/shingo-ops/salesanchor`）: `{"allow_auto_merge":false,"allow_merge_commit":true,"allow_squash_merge":true}`
- 開いたままの `release/ledger-done-*` の PR は 66 件（`gh pr list --state open --limit 500` の実測）。
- 台帳PRの作成者の実測: `gh pr view 3851 --json author,...` → author=`shingo-ops`, head=`release/ledger-done-3847`, files=`.claude-pipeline/active-work.d/release-enable-extraction-shadow.md`。

### 起動条件・除外条件（変更しない箇所）

- .github/workflows/ledger-auto-done-main.yml:15-18 起動は `pull_request: types [closed] / branches [main]` のみ。
- .github/workflows/ledger-auto-done-main.yml:26-29 `merged == true` かつ head が `release/ledger-done-` `release/ledger-auto-` で始まらないこと（無限ループ防止）。
- .github/workflows/ledger-auto-done-main.yml:87 台帳ブランチ名 `release/ledger-done-${PR_NUMBER}`。
- .github/workflows/ledger-auto-done-main.yml:92,130 コミット・PRタイトル `chore(ledger): PR #${PR_NUMBER} を DONE 化（自動）`。
- .github/workflows/ledger-auto-done-main.yml:79 予約・PR作成に使うトークンは `secrets.PIPELINE_PAT`。

### テストの置き場所と実行方法

- `scripts/ci/` は origin/main に存在しない（`git ls-tree -r origin/main --name-only | grep -E '(^|/)ci/'` → 0 件）。本便で新設する（設計者判断 2026-09-29）。
- 既存のシェルテストは scripts/tests/ にある: scripts/tests/test-ledger-helpers.sh, scripts/tests/test-manifest-generation.sh, scripts/tests/test-merge-safe-guard.sh, scripts/tests/test-reaper-safety.sh。
- 書き方: scripts/tests/test-merge-safe-guard.sh:1-20（素の bash、`set -u`、`mktemp -d` と `trap`、`ok`/`ng` 関数、`bash scripts/tests/<name>.sh` で実行、終了コード 0=全PASS）。
- CI での実行: `git grep -n 'scripts/tests' -- .github/workflows` の結果は node/python のテストのみ（dangling-route-gate.yml:35, guard-authoring-gate.yml:11,14,41, migration-test.yml:83, test-schema-dup-gate.yml:35, ui-governance-gate.yml:33）。`test-*.sh` を呼ぶワークフローは 0 件。CI への組み込みは本便の範囲外。

### 公式仕様の確認（Context7、2026-09-29）

- (a) `pull_request_target` の activity type: `auto_merge_enabled` / `auto_merge_disabled` を含む。出典: github/docs `data/reusables/actions/workflow-triggers-pull-request-activity-types.md`（raw を取得して一覧を確認）、同 `content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md`。同文書の記述: このイベントは base 側（デフォルトブランチ）の文脈で動き、PR の head のコードを実行しない。SHA に似たブランチ名では起動しないことがある。
- (b) `PUT /repos/{owner}/{repo}/pulls/{pull_number}/update-branch`: base の最新を PR ブランチへ merge する。body は任意の `expected_head_sha` のみ（不一致は 422）。成功は 202。出典: https://docs.github.com/en/rest/pulls/pulls（Context7 /websites/github_en）。update_method に相当する REST パラメータは確認できなかったため使わない。
- (c) `gh pr merge --disable-auto`: PR の auto-merge を無効にする。出典: https://cli.github.com/manual/gh_pr_merge（Context7 /websites/cli_github_manual）。手元の `gh pr merge --help` にも `--disable-auto  Disable auto-merge for this pull request` がある。

### 既存 ADR の検索

- `git grep -il "auto-merge\|ledger\|台帳" docs/adr` → ADR-023（別文脈：ユーザー台帳）, ADR-056（develop への auto-merge。別件）, ADR-099（古物台帳。別件）, ADR-1002（migration の実行済み台帳。別件）, README.md。
- docs/adr/FEATURE-INDEX.md に ledger / 台帳 / auto-merge の項目なし。
- 追補先は docs/adr/ADR-050-release-pr-workflow-standardization.md（変更履歴節に追補形式の前例あり）。

### 未確認（実測が要る点）

- GITHUB_TOKEN の `--disable-auto` の可否は、本便では PIPELINE_PAT を使うため論点にしない。
- 画面から予約した場合に auto-merge-guard.yml が起動するか（マージ後のテスト用 PR で確認する）。
- `pull_request_target` のワークフローは main に存在して初めて起動する。本PRのマージ前は動作確認できない。
