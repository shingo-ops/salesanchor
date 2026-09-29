# handoff — 台帳DONE化の auto-merge 限定

> この文書は何か（専門用語なしの1行）:
> 台帳の自動マージを「台帳の記録PRだけ」に限る仕組みを、次の担当者が引き継ぐための手順書。

対象ADR: ADR-050（追補）、ADR-114
recon: docs/handoff/ledger-auto-done-main/recon.md
design: docs/handoff/ledger-auto-done-main/design.md

## 入れたもの

| ファイル | 役割 |
|---|---|
| scripts/ci/is-ledger-done-pr.sh | 台帳 DONE化 PR かどうかの判定（唯一の置き場所） |
| scripts/tests/test-is-ledger-done-pr.sh | 上の判定テスト（gh をスタブ化） |
| .github/workflows/ledger-auto-done-main.yml | 予約前に判定・予約失敗を赤に・mode=backlog を追加 |
| .github/workflows/ledger-done-update-branch.yml | 予約済みで BEHIND の台帳PRを main に追従 |
| .github/workflows/auto-merge-guard.yml | 台帳以外に予約された auto-merge を取り消す |
| docs/adr/ADR-050-release-pr-workflow-standardization.md | 追補：auto-merge の限定 |

## このPRのマージ後に行うこと（順番を守る）

1. テスト用PRで実測する（未確認2点）。
   - 台帳DONE化PR ではないPRに `gh pr merge --auto --merge` を付けると、auto-merge-guard.yml が取り消してコメントを残すこと。
   - 画面から予約した場合にも auto-merge-guard.yml が起動すること。
2. PO が Allow auto-merge を ON にする（**auto-merge-guard.yml が main に入った後に**行う。先に ON にすると見張りのいない時間ができる）。
3. `ledger-auto-done-main` を workflow_dispatch（mode=backlog）で1回実行し、溜まった台帳PRを1本に集約する。実行前後の open 件数（`gh pr list --state open --limit 500 --json headRefName` の `release/ledger-done-` 件数）を記録する。
4. 今後、GITHUB_TOKEN で `gh pr merge --auto` を使うワークフローを追加しない。

## 戻し方

- PO が Allow auto-merge を OFF にする（すぐ効く）。
- 上の6ファイルの変更を戻す PR を出す。

## 注意

- 作成者の定数 `LEDGER_PR_AUTHOR`（`shingo-ops`）は scripts/ci/is-ledger-done-pr.sh の1か所だけ。PIPELINE_PAT の持ち主を変えるときは、ここを同時に直す。
- scripts/tests/test-is-ledger-done-pr.sh は CI から実行されない。判定を変える便で `bash scripts/tests/test-is-ledger-done-pr.sh` を手で実行する。
