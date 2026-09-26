# design — revert-t006-migration

**設計日**: 2026-09-06  
**担当**: Hikky-dev (QA-03a)  
**対象ADR**: ADR-154  
**recon**: docs/handoff/revert-t006-migration/recon.md

---

## 目的

失敗する migration を削除し、デプロイを再開可能にする。  
**本 PR は DB への変更を一切行わない。**

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `migrations/20260906_100000_create_tcg_tables_t006.sql` がリポジトリに存在しない | `ls migrations/20260906_100000_create_tcg_tables_t006.sql` → No such file |
| `scripts/run_all_migrations.sh` に当該 migration の呼び出し行がない | `grep 20260906_100000 scripts/run_all_migrations.sh` → 0件 |
| deploy.yml が migration ステップで失敗しない | CI `deploy.yml` 全件 pass |

---

## 変更内容

| ファイル | 変更 |
|---|---|
| `migrations/20260906_100000_create_tcg_tables_t006.sql` | 削除 |
| `scripts/run_all_migrations.sh:587` | `run_sql migrations/20260906_100000_create_tcg_tables_t006.sql` 行を削除 |

**DB への変更: なし。**  
RAISE EXCEPTION によりトランザクションはロールバック済みで、tenant_006 に TCG テーブルは存在しない。

---

## migration 検算の教訓

migration の事後検証でスキーマ内の全テーブル数を数えてはいけない。  
**自分が `CREATE TABLE` した対象のみを数える。** 例:

```sql
-- NG: スキーマ全体を数える
SELECT count(*) FROM information_schema.tables WHERE table_schema = 'tenant_006';

-- OK: 自分が作ったテーブルのみ存在確認
SELECT count(*) FROM information_schema.tables
WHERE table_schema = 'tenant_006'
  AND table_name IN ('tcg_type_master', 'tcg_series_master', ...);
```

---

## 外部・過去事例の参照と我々への応用

該当なし：本 PR は migration ファイルの削除のみ。外部事例の参照は不要と判断。  
（教訓は上記「migration 検算の教訓」セクションに記載）

---

## 維持の仕組み

守り手: 人手で守る — migration 作成時に「自分が作ったテーブルのみを検算する」ルールをレビューで確認する  
守り手: `scripts/run_all_migrations.sh` — migration 追加時に CI で migration ドライランが走り、RAISE EXCEPTION は即座に検出される
