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

## ロールバック判定条件の設計

移行スクリプトは挿入する全行に `analysis = '{"_source": "sa02_stage2_migration"}'` を付与する。
これにより **移行スクリプトが入れた行だけ** を正確に特定でき、以下の巻き添えを防ぐ:

| ケース | 旧条件（`external_message_id IN ...`） | 新条件（`analysis._source`）|
|--------|---------------------------------------|-----------------------------|
| 段階2移行行 | ✅ 削除対象 | ✅ 削除対象 |
| 段階1 webhook 新規受信（Meta） | ⚠️ 同一 message_id で巻き添え削除 | ✅ 削除しない |
| 段階1 Discord 新規受信 | ✅ 削除しない | ✅ 削除しない |
| 手動記録（is_manual=true） | ✅ 削除しない | ✅ 削除しない |

## ロールバック手順

### Step 1: 移行件数を確認

```bash
docker compose exec -T postgres psql -U jarvis -d jarvis_db -c "
SELECT COUNT(*), MIN(id), MAX(id)
FROM tenant_001.conversation_logs
WHERE analysis->>'_source' = 'sa02_stage2_migration';
"
```

### Step 2: ロールバックSQL（テナントごとに実行）

```sql
-- 確認用（先に SELECT で件数確認）
SELECT COUNT(*)
FROM tenant_001.conversation_logs
WHERE analysis->>'_source' = 'sa02_stage2_migration';

-- 実行（DELETE）
DELETE FROM tenant_001.conversation_logs
WHERE analysis->>'_source' = 'sa02_stage2_migration';
```

### Step 3: 全テナントへの適用（スクリプト）

```bash
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
                WHERE analysis->>'_source' = 'sa02_stage2_migration'
                $q$,
                schema
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
