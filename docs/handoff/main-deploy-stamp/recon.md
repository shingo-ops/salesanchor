# Recon: main デプロイ成功スタンプ（ADR-116）

## 対象ファイル

| ファイル | 参照箇所 | 内容 |
|---------|---------|------|
| `.github/workflows/deploy.yml:638` | Verify deployment ステップ末尾 | ADR-116 スタンプステップの挿入位置 |
| `.claude-pipeline/active-work.md:1` | ヘッダー行 | 7列目 `main` 列（デプロイ日付）の定義 |
| `scripts/check-active-work-format.sh:1` | EXPECTED_COLS 変数 | 6→7 列チェック変更 |
| `scripts/new-worktree.sh:1` | new_row テンプレート | 7列形式の新規行テンプレート |

## 現状把握

### active-work.md の列構成（変更前 6列 → 変更後 7列）

変更前:
```
| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | 備考 |
```

変更後:
```
| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
```

- `main` 列: 本番デプロイ成功日（`YYYY-MM-DD`）。未デプロイは空欄。

### deploy.yml の構成（変更箇所）

- `.github/workflows/deploy.yml:638` の `VERIFY_EOF` 直後に stamp ステップを追加
- `if: success()` 条件により、前段の smoke/health/verify が全通過した場合のみ実行
- `continue-on-error: true` によりスタンプ失敗でもデプロイ全体はブロックしない
- `PIPELINE_PAT` シークレットで develop ブランチへプッシュバック

### スタンプロジック

- `active-work.md` の全行を走査
- 7列かつ `DONE` かつ `cols[5]`（main列）が空の行にデプロイ日付を書き込む
- 変更があれば develop ブランチへ自動コミット＆プッシュ

## 不明点・リスク

- `PIPELINE_PAT` シークレットが設定されていない場合はプッシュ失敗（`continue-on-error: true` でデプロイ本体には影響なし）
- 複数 PR が同一デプロイで DONE になる場合、全件まとめてスタンプされる（意図した動作）
