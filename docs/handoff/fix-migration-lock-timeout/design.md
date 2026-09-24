# design: fix-migration-lock-timeout

## KGI

デプロイで `20260922_050000_fix_phase2c_fk_drop_only.sql` がタイムアウトしない。
判定: 次回デプロイのGitHub Actions「Run database migrations」ステップが success。

## KPI / 検証方法

| 基準 | 検証方法 |
|---|---|
| migration ステップが10分以内に完了 | gh run view の「Run database migrations」ステップ conclusion=success |
| 制約が存在しない場合でもエラーなし | IF EXISTS のため `ALTER TABLE` は NOTICE なしで完了 |

## 変更設計

### 変更対象
`migrations/20260922_050000_fix_phase2c_fk_drop_only.sql`

### 変更内容
BEGIN の直後に追加:
```sql
SET LOCAL lock_timeout = '30s';
SET LOCAL statement_timeout = '60s';
```

### LOCAL スコープの理由
`SET LOCAL` はトランザクション終了時にリセットされる。次の migration に影響しない。
`SET` (SESSION) だとコネクションが再利用された場合に残留するリスクがある。

### 影響範囲
- 呼び出し元: `scripts/run_all_migrations.sh:527`（`run_sql` 経由）
- 他の migration には影響しない（LOCAL スコープ）

## 外部・過去事例の参照と我々への応用

- PostgreSQL 公式ドキュメント: `SET LOCAL lock_timeout` はトランザクション終了時にリセットされる。SESSION スコープと異なりコネクション再利用時に残留しない
- ゼロダウンタイム migration のベストプラクティス（Braintree, GitLab engineering blog）: `ALTER TABLE` に `lock_timeout` を設定することで、デプロイパイプラインのタイムアウト前に fail-fast させる
- 本プロジェクトへの応用: `command_timeout: 10m`（deploy.yml）より短い `30s` を設定し、ブロック時は明示的なエラーログを残す

## ADR参照

- ADR-082: run_all_migrations.sh SSoT

## 守り手

この migration はいずれ Phase 2c 完了後に不要になる。
`lock_timeout` 追加は後の migration にも展開すべきパターン。

## 維持の仕組み

この変更はデプロイのたびに自動実行される（run_all_migrations.sh）。
`IF NOT EXISTS` により、制約が存在しない場合はロック取得後に即完了する。
将来 Phase 2c が完了したら本 migration ファイルを削除対象にできる。

## 戻し方

`lock_timeout`/`statement_timeout` の行を削除するだけ。DDL変更なし。
