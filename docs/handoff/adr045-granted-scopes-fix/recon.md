# recon: ADR-045 granted_scopes NULL — deploy Verify 失敗

調査日時: 2026-06-17
目的: deploy #2284 merge 後の "Verify deployment" ステップで ADR-045 が失敗した原因特定と修正設計

---

## 1. エラー概要

```
WARNING:  NULL granted_scopes rows: schema=tenant_006 tenant_code=tenant-review count=2
ERROR:    ADR-045 verification failed: missing_col=0 null_rows=2
```

発生ジョブ: deploy run `27653046274` / ステップ `Verify deployment`
発生時刻: 2026-06-16T22:48:56 JST

---

## 2. 対象テーブルと行数

| 項目 | 値 |
|---|---|
| DB スキーマ | `tenant_006` |
| テーブル | `tenant_006.tenant_meta_config` |
| 対象行数 | **2行**（`granted_scopes IS NULL`） |
| テナント | `tenant-review`（撮影・QAテナント） |

---

## 3. ADR-045 Verify check の仕組み

`.github/workflows/deploy.yml:649-709`

deploy 完了後の "Verify deployment" SSH ステップで以下の PL/pgSQL を実行:

```sql
-- 全 active テナントで granted_scopes 列の存在確認 + NULL 行数チェック
-- NULL が 1行でもあれば RAISE EXCEPTION → ステップ失敗
SELECT COUNT(*) FROM %I.tenant_meta_config WHERE granted_scopes IS NULL
```

`missing_col=0` → 列は存在する（migration 055 の ADD COLUMN は適用済み）  
`null_rows=2` → backfill UPDATE が未適用の行が 2行残存

---

## 4. migration 055 の設計

`migrations/055_add_granted_scopes.sql:27-33`

```sql
ALTER TABLE {schema}.tenant_meta_config
    ADD COLUMN IF NOT EXISTS granted_scopes JSONB;

UPDATE {schema}.tenant_meta_config
    SET granted_scopes = '["pages_show_list","pages_manage_metadata","pages_messaging",
                           "pages_read_engagement","instagram_basic","instagram_manage_messages"]'::jsonb
    WHERE granted_scopes IS NULL;
```

冪等設計: `ADD COLUMN IF NOT EXISTS` + `UPDATE WHERE granted_scopes IS NULL` → 再実行安全

---

## 5. なぜ NULL が残ったか（根本原因）

### deploy run 27653046274 のステップ状態

```
Run database migrations:  SKIPPED  ← ここが問題
Verify deployment:        FAILURE
```

### "Run database migrations" がスキップされた理由

`.github/workflows/deploy.yml:409-428`:
```yaml
- name: Run database migrations
  if: ${{ success() && steps.changes.outputs.migrations == 'true' }}
```

`steps.changes.outputs.migrations` が `'false'` だったためスキップ。

### パスフィルタの設定

`.github/workflows/deploy.yml:33-43`:
```yaml
- name: Detect backend / migration changes
  uses: dorny/paths-filter@v4
  id: changes
  with:
    filters: |
      migrations:
        - 'migrations/**'
        - 'scripts/**'
        - 'backend/**'
        - 'docker-compose.yml'
        - '.github/workflows/deploy.yml'
```

PR #2284 の変更ファイル:
- `frontend/Dockerfile` ← `migrations` フィルタ対象外
- `docker-compose.yml` ← `migrations` フィルタ対象
- `.github/workflows/deploy.yml` ← `migrations` フィルタ対象

`docker-compose.yml` と `deploy.yml` はフィルタ対象であるにもかかわらず SKIPPED になった理由:
**hotfix branch の cherry-pick では dorny/paths-filter が push event の `before..after` 差分ではなく、main ブランチへの merge commit の変更ファイルで判定する。**
直前の main コミット群（`81de0f04`, `5fcdbdd2` QA Firebase）がすでに `deploy.yml` 等を変更しており、連続 push の際に paths-filter の比較基点がずれた可能性がある。

### 実際の NULL 残存理由（DB 側）

migration 055 の backfill は適用時点で NULL だった行のみ対象。  
**移行後に新規 OAuth 接続された行**（INSERT by 旧コード、または granted_scopes 未設定のまま）が
その後 NULL のまま残った可能性が高い（`connect_callback` が新スコープ記録前の旧フローで動いた場合）。

---

## 6. `migrate_adr041_granted_scopes.py` の動作

`scripts/migrate_adr041_granted_scopes.py:96-135`

```python
tmpl = (MIGRATIONS_DIR / "055_add_granted_scopes.sql").read_text("utf-8")
for tid, tc in tenants:
    schema = f"tenant_{tid:03d}"
    async with engine.begin() as conn:
        await _exec(conn, tmpl.format(schema=schema))
```

- 全 active テナントに対して `055_add_granted_scopes.sql` を展開
- `ADD COLUMN IF NOT EXISTS` → 列があれば no-op
- `UPDATE WHERE granted_scopes IS NULL` → NULL 行のみ更新

`scripts/run_all_migrations.sh:128`:
```bash
run_py  scripts/migrate_adr041_granted_scopes.py
```

→ `run_all_migrations.sh` に含まれているが、今回の deploy では呼ばれなかった。

---

## 7. 修正候補

### 案A（推奨・最小リスク）: one-shot SQL で直接 UPDATE

```sql
UPDATE tenant_006.tenant_meta_config
SET granted_scopes = '["pages_show_list","pages_manage_metadata","pages_messaging",
                       "pages_read_engagement","instagram_basic","instagram_manage_messages"]'::jsonb
WHERE granted_scopes IS NULL;
```

- 対象: tenant_006.tenant_meta_config の NULL 2行のみ
- リスク: 低（同じ backfill 値。再 OAuth 時に上書きされる設計）
- 実施者: Shingo（本番 DB 変更 → GO 必須）

```bash
# 実行コマンド（VPS 上）
docker exec -i astro-webapp-postgres-1 \
  psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 <<'SQL'
UPDATE tenant_006.tenant_meta_config
SET granted_scopes = '["pages_show_list","pages_manage_metadata","pages_messaging","pages_read_engagement","instagram_basic","instagram_manage_messages"]'::jsonb
WHERE granted_scopes IS NULL;
SELECT COUNT(*) AS remaining_nulls FROM tenant_006.tenant_meta_config WHERE granted_scopes IS NULL;
SQL
```

期待結果: `remaining_nulls = 0`、UPDATE 2行

### 案B: migration スクリプトを再実行（deploy.yml 経由）

`run_all_migrations.sh` を強制起動させるダミー変更を含む PR を作成し、  
merge → deploy 自動発火 → `migrate_adr041_granted_scopes.py` が実行される。

- リスク: deploy 全体が走る（downtime リスクあり。小）
- 確実性: `run_all_migrations.sh` が全テナントに再適用 → tenant_006 も補完

### 案C（再発防止）: Verify 前に migration を無条件実行

deploy.yml の "Verify deployment" ステップの直前に、条件なし（`if: success()`）で
`migrate_adr041_granted_scopes.py` を実行するステップを追加。

```yaml
- name: Ensure granted_scopes backfill (ADR-045 guard)
  if: success()
  uses: appleboy/ssh-action@v1
  with:
    script: |
      cd /home/ubuntu/salesanchor
      docker compose exec -T backend python scripts/migrate_adr041_granted_scopes.py
```

- deploy.yml 変更 → Shingo GO 必須
- 今後の同種問題を根本解消

---

## 8. ロールバック方法

現在の状態:
- アプリは正常稼働中（Health check passed）
- ロールバック不要

案A 実施後にロールバックが必要になった場合:
```sql
-- granted_scopes を NULL に戻す（再 OAuth 前の状態に戻る）
UPDATE tenant_006.tenant_meta_config SET granted_scopes = NULL;
```
ただし実用上の影響は小（再 OAuth 時に上書きされるため）。

---

## 9. Shingo GO が必要な次アクション

| アクション | 必要性 | 理由 |
|---|---|---|
| **案A: VPS 上で UPDATE SQL 実行** | **GO 必須** | 本番 DB 変更（CLAUDE.md 不可逆操作リスト） |
| 案B: ダミー PR → deploy → migration 再実行 | GO 必須 | deploy.yml 発火 → 本番 deploy |
| 案C: deploy.yml に migration guard ステップ追加 | GO 必須 | deploy.yml 変更 |

**推奨順序**:
1. 即時対応 → **案A**（SQL 1行）を Shingo が VPS で実行（CC は実施不可）
2. 再発防止 → **案C** を別 PR で設計・実装（deploy.yml 変更 → Shingo GO）

---

## 10. 調査ベース

| ファイル:行 | 内容 |
|---|---|
| `.github/workflows/deploy.yml:409-428` | "Run database migrations" 条件 `migrations == 'true'` |
| `.github/workflows/deploy.yml:33-43` | paths-filter 設定（対象パス一覧） |
| `.github/workflows/deploy.yml:649-709` | ADR-045 Verify check の PL/pgSQL |
| `migrations/055_add_granted_scopes.sql:27-33` | backfill UPDATE（冪等） |
| `scripts/migrate_adr041_granted_scopes.py:96-135` | 全テナント展開ロジック |
| `scripts/run_all_migrations.sh:128` | `migrate_adr041_granted_scopes.py` 呼び出し箇所 |
| `docs/adr/ADR-045-migration-055-deploy-automation.md` | ADR 設計仕様 |
| deploy run `27653046274` / step "Run database migrations" | SKIPPED 確認 |
