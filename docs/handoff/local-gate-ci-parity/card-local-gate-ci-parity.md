# 実装カード: PR 作成時の関所で CI と同じ process-artifacts 検査を呼ぶ

- 設計: `docs/handoff/local-gate-ci-parity/design.md`、調査: 同 `recon.md`（scratchpad `local-gate/` から コピー）
- PO: 2026-09-30「確立したならy」。範囲は本カードのみ
- 基準: origin/main（調査時 6144412fdcbdab602ba2c4bd6c3937116ddeb6ee）。行番号は着手時に実物で再確認、ロジックが違えば停止

## 0. 事前
1. `./scripts/dev/executor-preflight.sh || exit 1`
2. 作業フォルダの空き: `git worktree list | wc -l`。上限なら、`/Users/tanizawashingo/worktrees/salesanchor/release-line-parser-unify`（PR #3861 マージ済み）について `git -C <パス> status --porcelain` が空、かつ `gh pr view 3861 --json state` が MERGED を確認してから `git -C /Users/tanizawashingo/salesanchor worktree remove <パス>`（--force 禁止）。拒否・ブロックなら全停止
3. `bash scripts/new-worktree.sh release/local-gate-ci-parity --claude`
4. scratchpad `local-gate/` の `recon.md`・`design.md`・本カードを `docs/handoff/local-gate-ci-parity/` にコピー

## 1. 実装前に読んで確かめること（食い違えば停止して報告）
- `scripts/check-process-artifacts.js` の main の流れ: GO 記録検査（validateGORecord :340-406）の呼び出し箇所、PR 番号の猶予判定2か所（:84 MAINTENANCE_GRACE_PR、:821 GRACE_THRESHOLD_PR）、PR 本文・作成者の取得（MOCK_PR_BODY があれば GitHub API を呼ばないこと）
- 環境変数 CHANGED_FILES・MOCK_ADDED_FILES・MOCK_ORIGIN_MAIN_FILES・MOCK_HEAD_REF・MOCK_BASE_REF の書式（区切り文字）と、CI 実行時にそれぞれ何から作られるか。手元で CI と同じ値を git から作る方法を決める（例: 追加ファイル＝`git diff --name-only --diff-filter=A origin/main...HEAD`）。決められないものがあれば停止
- `scripts/dev/validate-pr-body.sh` の PR_BODY_VALIDATE_SKIP 等の既存の切り替えの意味（壊さない）

## 2. 変更（これ以外は触らない）
### 2-1 `scripts/check-process-artifacts.js`
- `const LOCAL_PRECHECK = process.env.LOCAL_PRECHECK === '1';`
- 開始直後: `LOCAL_PRECHECK && process.env.GITHUB_ACTIONS === 'true'` なら「LOCAL_PRECHECK は CI では使えません」を出して exit 1
- GO 記録検査: LOCAL_PRECHECK なら呼ばずに「⏭ GO記録は PR 番号確定後に CI で検査します（PR 作成前の事前検査では省略）」を出す
- PR 番号の猶予判定2か所: LOCAL_PRECHECK なら「猶予なし（検査する）」として扱う
- ファイル冒頭の環境変数コメントに LOCAL_PRECHECK を追記
- LOCAL_PRECHECK でないときの挙動は1行も変えない
### 2-2 `scripts/dev/validate-pr-body.sh`
- 既存の検査はそのまま。既存の検査がすべて通ったあと（exit 0 の直前）に、§1 で決めた入力を付けて `LOCAL_PRECHECK=1 node scripts/check-process-artifacts.js` を実行し、exit≠0 なら exit 1
- `node` が無い、`gh api user --jq .login` が失敗する場合は、理由を出して exit 1（黙って通さない）
- 外から注入された GITHUB_ACTIONS に左右されない（gh-pr-create-safe.sh:138 と同じ理由）。CI の gate は本スクリプトを通らず JS を直接呼ぶため、CI での LOCAL_PRECHECK 拒否は有効なまま（`env -u GITHUB_ACTIONS` を付けて呼ぶ）
### 2-3 `scripts/tests/test-process-artifacts.js`
- 既存の書き方に合わせて3件: (a) LOCAL_PRECHECK=1 で危険変更＋GO 記録なしでも GO 記録で落ちず先の検査に進む (b) LOCAL_PRECHECK=1 と GITHUB_ACTIONS=true で exit 1 (c) LOCAL_PRECHECK=1 で PR_NUMBER なしでも触る／削除するファイルの宣言照合が行われる

## 3. 検証（生出力を報告）
- 変更前（origin/main）と変更後で `node scripts/tests/test-process-artifacts.js` と `python3 scripts/tests/test-pr-lifecycle.py` を実行し、結果を並べる（変更前に通っていたものが全部通る。変更前から落ちているものはそのまま記録）
- recon §2 の再現（scratchpad `local-gate/` の実験用リポジトリと材料を使ってよい）:
  - CI 相当（LOCAL_PRECHECK なし）で4通りの結果が変更前と同じ
  - `validate-pr-body.sh` 経由で: 修正前の設計書＋GO 記録なしの本文 → exit 1、エラーに「ADR 参照」／修正後の設計書＋GO 記録なし → exit 0
- 本 PR 自身の本文を `validate-pr-body.sh` に通して exit 0（GO 記録なしの状態で）

## 4. 仕上げ
- 台帳 `.claude-pipeline/active-work.d/release-local-gate-ci-parity.md`
- design.md の「対象ADR」: `git grep -il "process-artifacts" origin/main -- docs/adr/` の結果（ファイル名と該当行）を報告し、**PR は作らずに停止**（設計担当が対象ADRを確定してから PR 作成を指示する）。commit・push までは行ってよい

## 5. 停止条件
- 行番号・ロジックの食い違い、入力の作り方が決められない、既存テストが変更後に新たに落ちる、フック・分類器・権限に止められた → 全停止し、生出力で報告
