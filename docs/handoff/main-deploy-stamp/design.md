# Design: main デプロイ成功スタンプ（ADR-116）

## 参照

- ADR: `docs/adr/ADR-116-main-deploy-stamp.md`
- Recon: `docs/handoff/main-deploy-stamp/recon.md`

## How（実装方針）

1. `active-work.md` に `main` 列（7列目）を追加し、本番デプロイ日を記録する
2. `deploy.yml` の Verify deployment ステップ通過後に stamp ステップを挿入
3. GitHub Actions bot が develop ブランチに直接コミットするため `PIPELINE_PAT` を使用
4. `check-active-work-format.sh` の `EXPECTED_COLS` を 6→7 に変更し CI でスキーマ整合性を担保
5. `new-worktree.sh` の新規行テンプレートを 7列形式に更新

## KPI / 検証基準

| 基準 | 検証方法 |
|------|---------|
| deploy.yml に stamp ステップが存在する | `grep -c "Stamp main deploy date" .github/workflows/deploy.yml` が 1 以上 |
| active-work.md が 7列形式 | `bash scripts/check-active-work-format.sh` が exit 0 |
| new-worktree.sh が 7列新規行を生成する | スクリプト内 `new_row` の `\|` 数が 8（区切り7列） |
| スタンプが DONE 行の main 列のみ更新する | Python スクリプトのロジックで `DONE` かつ `cols[5].strip() == ""` の条件確認 |
| stamp 失敗でデプロイがブロックされない | `continue-on-error: true` の設定確認 |

## 外部・過去事例の参照と我々への応用

- **GitHub Actions / auto-commit pattern**: `stefanzweifel/git-auto-commit-action` — CI 実行後に自動コミットするパターンの標準実装。`GITHUB_TOKEN` ではなく PAT を使う理由は branch protection bypass のため（本実装と同じアプローチ）
- **Heroku release tracking**: デプロイ成功後にメタデータ（リビジョン番号・日時）を専用ファイルに記録し、ロールバック判断に活用するパターン。本実装の `main` 列はこれに相当

## 弊害・トレードオフ

| 弊害 | 対策 |
|------|------|
| `PIPELINE_PAT` 期限切れでスタンプ失敗 | `continue-on-error: true`、監視ログで検知 |
| develop への直接コミットが Branch Protection に抵触する可能性 | PAT は admin 権限付与済み（`docs/BRANCH_PROTECTION_SETUP.md` 参照） |
| 同一デプロイで複数行スタンプされる | 意図した動作（全 DONE 行を一括スタンプ） |
| active-work.md の 6列→7列マイグレーションが全ワークツリーに必要 | `new-worktree.sh` のテンプレート更新で新規は自動対応、既存は手動マイグレーション済み |
