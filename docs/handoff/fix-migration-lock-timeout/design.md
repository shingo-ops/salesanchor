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

## 外部事例

PostgreSQL 公式: `lock_timeout` は `SET LOCAL` でトランザクション内のみ有効。
ゼロダウンタイム migration のベストプラクティス: 長時間テーブルを保持する
トランザクションがある本番環境では lock_timeout を設定して fail-fast にする。

## ADR参照

- ADR-082: run_all_migrations.sh SSoT

## 守り手

この migration はいずれ Phase 2c 完了後に不要になる。
`lock_timeout` 追加は後の migration にも展開すべきパターン。

## 戻し方

`lock_timeout`/`statement_timeout` の行を削除するだけ。DDL変更なし。
