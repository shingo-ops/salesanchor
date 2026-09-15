# silent failure guard recon

親参照: [docs/specs/branch-operations/README.md](/Users/tanizawashingo/worktrees/salesanchor/release-branch-guardrail-close-main/docs/specs/branch-operations/README.md) §3-3

この文書は何か（専門用語なしの1行）:
古い土台で正本を二重に作る事故を、ローカル抜け道ではなく関所側で止めるための実物確認メモ。

## 結論

- `strict_required_status_checks_policy` は main 側で off のまま維持する: **YES**
- generic な「新規作成ファイルが最新 main に既にある」検査は既存になし: **YES**
- merge queue は採用しない: **YES**
- 今回は strict を on にせず、process-artifacts gate に二重定義検出を足す: **YES**

## 実物確認

- main の legacy branch protection は strict=true になっていたが、後に `strict=false` へ是正済み。`docs/BRANCH_PROTECTION_SETUP.md:272-277`
- `process-artifacts gate` は main / develop の required check として登録されている。`docs/BRANCH_PROTECTION_SETUP.md:298-314`
- `ADR-135` は merge queue / リリースブランチ運用を「今回は採らない・コスト過大」と明記している。`docs/adr/ADR-135-release-stowaway-prevention.md:64-66`
- 既存の generic 重複検査は migrations の timestamp だけで、ファイルパス一般には広がっていない。`.github/workflows/migration-guard.yml:279-330`
- `process-artifacts gate` の workflow は `fetch-depth: 0` で PR ごとに実行されるため、latest main 参照の前提を置ける。`.github/workflows/process-artifacts-gate.yml:22-39`

## ADR 検索結果

- `docs/adr/ADR-121-sop-process-artifacts-gate.md`
- `docs/adr/ADR-135-release-stowaway-prevention.md`

## 参照点

- 既存の `scripts/check-process-artifacts.js` は touch/delete/GO 記録の検査を持つが、added file と latest main の突合はまだない。`scripts/check-process-artifacts.js:621-629`
- 追加した二重定義検出は `scripts/check-process-artifacts.js:134-177` で added file と latest origin/main を突合し、`scripts/check-process-artifacts.js:621-629` で fail する。

## 使い方の前提

- `--no-verify` / `--force` を封じるのではなく、サーバ側 gate で捕まえる。
- docs-only 自動スキップは維持する。
