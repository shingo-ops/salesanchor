# SA-02 段階2 移行ロールバック手順

> **本番実行はShingo GOが必要。このドキュメントは実行前に必ず読むこと。**

## 概要

`meta_messages` → `conversation_logs` への移行はデータ追加のみ（`meta_messages` は変更・削除しない）。
ロールバック = 追加した `conversation_logs` 行を削除するだけ。

## ロールバック判断基準

| 状況 | 対応 |
|------|------|
| 移行スクリプトがエラーで中断した | 下記ロールバックSQLを実行し、原因修正後に再実行 |
| 移行後に業務影響が判明した | Shingoに相談の上、ロールバックSQLを実行 |
| 検証スクリプトでgapが解消しない | 原因調査（ロールバック不要）→ 修正後に再実行 |

## ロールバック手順

### Step 1: 移行ID範囲を確認

```bash
# VPS上で実行
docker compose exec backend psql "${DATABASE_URL}" -c "
SELECT
    s.nspname AS schema,
    COUNT(*) AS migrated_rows,
    MIN(cl.id) AS min_id,
    MAX(cl.id) AS max_id
FROM information_schema.schemata s
CROSS JOIN LATERAL (
    SELECT id FROM \${schema}.conversation_logs
    WHERE external_message_id LIKE 'meta_legacy:%'
       OR external_message_id IN (
           SELECT message_id FROM \${schema}.meta_messages WHERE message_id IS NOT NULL
       )
) cl
WHERE s.schema_name ~ '^tenant_[0-9]+$'
GROUP BY s.nspname
ORDER BY s.nspname;
"
```

実際にはテナントごとに個別で確認する:
```bash
docker compose exec -T postgres psql -U jarvis -d jarvis_db -c "
SELECT COUNT(*), MIN(id), MAX(id)
FROM tenant_001.conversation_logs
WHERE external_message_id LIKE 'meta_legacy:%'
   OR external_message_id IN (SELECT message_id FROM tenant_001.meta_messages WHERE message_id IS NOT NULL);
"
```

### Step 2: ロールバックSQL（テナントごとに実行）

```sql
-- 確認用（先に SELECT で件数確認）
SELECT COUNT(*)
FROM tenant_001.conversation_logs
WHERE is_manual = false
  AND (
    external_message_id LIKE 'meta_legacy:%'
    OR external_message_id IN (
        SELECT message_id FROM tenant_001.meta_messages WHERE message_id IS NOT NULL
    )
  );

-- 実行（DELETE）
DELETE FROM tenant_001.conversation_logs
WHERE is_manual = false
  AND (
    external_message_id LIKE 'meta_legacy:%'
    OR external_message_id IN (
        SELECT message_id FROM tenant_001.meta_messages WHERE message_id IS NOT NULL
    )
  );
```

**注意**: `is_manual = false` 条件で手動記録（`is_manual = true`）を誤って削除しない。

### Step 3: 全テナントへの適用（スクリプト）

```bash
# VPS上のコンテナ内で実行
docker compose exec -T postgres psql -U jarvis -d jarvis_db << 'SQL'
DO $$
DECLARE
    tenant RECORD;
    deleted_count INT;
BEGIN
    FOR tenant IN
        SELECT id FROM public.tenants WHERE is_active = true ORDER BY id
    LOOP
        DECLARE schema TEXT := format('tenant_%s', lpad(tenant.id::text, 3, '0'));
        BEGIN
            EXECUTE format(
                $q$
                DELETE FROM %I.conversation_logs
                WHERE is_manual = false
                  AND (
                    external_message_id LIKE 'meta_legacy:%%'
                    OR external_message_id IN (
                        SELECT message_id FROM %I.meta_messages WHERE message_id IS NOT NULL
                    )
                  )
                $q$,
                schema, schema
            );
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RAISE NOTICE '% ロールバック: % 件削除', schema, deleted_count;
        EXCEPTION WHEN others THEN
            RAISE WARNING '% エラー: %', schema, SQLERRM;
        END;
    END LOOP;
END $$;
SQL
```

### Step 4: ロールバック確認

```bash
docker compose exec backend python /app/scripts/verify_sa02_stage2_count_check.py
```

`conv_from_meta_total = 0` になっていれば完全ロールバック完了。

## 影響範囲

| 対象 | 影響 |
|------|------|
| `meta_messages` | **変更なし**（読み取り専用で使用） |
| `conversation_logs` | 追加した行を削除（手動記録は削除しない） |
| `v_company_stats` | `conversation_logs` が空になれば `conversation_count=0` に戻る |
| `message_translations` | **変更なし** |
| UI（会話履歴タブ） | `conversation_count=0` / `last_conversation_at=NULL` に戻る（移行前と同じ） |

## 再実行

ロールバック後に原因を修正した場合、移行スクリプトはそのまま再実行できる（冪等）:

```bash
docker compose exec backend python /app/scripts/migrate_sa02_stage2_meta_to_conv_logs.py --dry-run
docker compose exec backend python /app/scripts/migrate_sa02_stage2_meta_to_conv_logs.py
```
