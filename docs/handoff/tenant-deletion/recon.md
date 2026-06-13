# recon — テナント削除機能

**仕事名**: tenant-deletion  
**日付**: 2026-06-13  
**対象 ADR**: 未起案（本 recon が起案判断材料）  
**担当**: shingo-cc

---

## 目的

テナント削除機能（論理削除 + 物理削除）の実装に必要な現状把握を行う。  
15 項目すべてに実コード file:line 引用で回答する。推測禁止・不明は「不明」と明記。

---

## A. 現状データモデル

### A-1: 論理削除フラグの現状

`backend/app/models.py:16`

```python
is_active = Column(Boolean, default=True, index=True)
```

`deleted_at`（タイムスタンプ型論理削除）は存在しない。`is_active` の Boolean のみ。  
論理削除時刻の記録は現モデルでは**不可能**（カラム追加 migration が必要）。

---

### A-2: is_active=False の認証遮断確認

`backend/app/auth/dependencies.py:208-225`

Redisキャッシュヒット時:
```python
if not cached["is_active"]:   # 依存: get_current_tenant() line 209
    raise HTTPException(status_code=403, detail="テナントが無効です")
```

キャッシュミス時（DB参照）:
```python
if not tenant or not tenant.is_active:  # line 220
    raise HTTPException(status_code=403, detail="テナントが無効です")
```

Firebase 認証 → User.is_active チェック（`line 168`）→ Tenant.is_active チェック（`line 209/220`）の順。  
`is_active=False` にするだけで API 全域から遮断される（`get_current_tenant()` が全ルートの前提 Dependency）。

---

### A-3: テナント作成フロー全体像

`backend/app/routers/admin.py:17-91` — エンドポイント側  
`backend/app/services/tenant.py:1461-1548` — スキーマ生成

作成順序:
1. `admin.py:57-83`: `async with db.begin()` — public.tenants INSERT + flush で id 確定
2. `tenant.py:1487-1490`: `safe_id = int(tenant_id)` / `schema_name = f"tenant_{safe_id:03d}"` / regex 検証
3. `tenant.py:1493`: `CREATE SCHEMA IF NOT EXISTS {schema_name}` (DDL, admin_db)
4. `tenant.py:1504`: `_TENANT_TABLES_SQL` 実行（業務テーブル群）
5. `tenant.py:1506-1511`: RLS ENABLE（ALTER TABLE 群）
6. `tenant.py:1513-1515`: RLS POLICY（DO $$ ブロック）
7. `tenant.py:1517-1536`: GRANT to salesanchor_app
8. `tenant.py:1539`: `seed_system_roles(db, safe_id, schema_name)`

削除の逆順操作: REVOKE → DROP SCHEMA CASCADE → public.tenants DELETE に相当。

---

### A-4: id=2 欠番の存在確認

実調査（tenant_001 調査ワークフロー結果・2026-06-13）:  
`public.tenants` に id=1,3,4,5,6 が存在、id=2 は存在しない（欠番）。

採番ロジック: `backend/app/models.py:11`

```python
id = Column(Integer, primary_key=True, index=True)
```

PostgreSQL SERIAL（シーケンス自動採番）。シーケンスは DELETE しても巻き戻らない。  
id=2 の欠番原因のコード記録は**不明**（git log / 本番 audit_logs に履歴がある可能性あり）。  
新規テナント作成時、id=2 が再利用される仕組みは存在しない（シーケンス連番）。

---

## B. 論理削除の影響範囲

### B-5: is_active=False がフィルタされるクエリ一覧

`backend/app/auth/dependencies.py:168` — User.is_active チェック

```python
select(User).where(User.email == email, User.is_active == True)
```

`backend/app/auth/dependencies.py:209,220` — Tenant.is_active チェック（前掲）

バックグラウンドタスク（Celery/APScheduler 系）での Tenant.is_active フィルタ状況:  
`backend/app/tasks/` 配下は `get_current_tenant()` Dependency を経由しない。  
直接 DB クエリを行うタスク（例: `backend/app/tasks/dashboard.py`, `backend/app/tasks/translation.py`）では  
is_active フィルタが個別実装依存となる。統一強制機構は**不明（要追加調査）**。

---

### B-6: Firebase UID とテナント紐付けの認証チェーン

`backend/app/auth/dependencies.py:142` — Firebase token 検証

```python
decoded = firebase_auth.verify_id_token(token)
```

`backend/app/auth/dependencies.py:168` — User.is_active + email 照合  
`backend/app/auth/dependencies.py:204` — `get_current_tenant()` で Tenant.is_active 確認

Firebase UID は `public.users.email` で紐付け（JWT の email クレーム経由）。  
Firebase SDK 側のユーザー無効化（`firebase_admin.auth.update_user(uid, disabled=True)`）は  
本コードベースでは**実装されていない**（is_active=False はアプリ DB 側のみ）。  
→ 論理削除時に Firebase 側も無効化するか否かは ADR で決定が必要。

---

## C. スキーマ DROP の安全性

### C-7: バックアップ運用

`scripts/backup.sh` — 30 日保持の pg_dump  
`.github/workflows/deploy.yml:141-160` — デプロイ前自動バックアップ

DROP 前の手動バックアップ手順は未整備（スクリプト化されていない）。  
バックアップ取得後 DROP するまでの猶予ウィンドウも規定なし。

---

### C-8: クロススキーマ FK の有無

`backend/app/models.py:26`:

```python
tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
```

public.users → public.tenants の CASCADE FK のみ。  
`tenant_NNN` スキーマ内テーブルから他スキーマへの FK は**存在しない**（調査済み）。  
`DROP SCHEMA tenant_NNN CASCADE` で当該スキーマのテーブルは完全消去可能。  
public.users は CASCADE DELETE により連鎖削除される（公開スキーマ側）。

---

### C-9: DDL トランザクション保証

`backend/app/routers/admin.py:57`:

```python
async with db.begin():
    # public.tenants INSERT
    await db.flush()
    schema_name = await create_tenant_schema(db, tenant.id, admin_db=admin_db)
```

`backend/app/services/tenant.py:1493`:

```python
await ddl_db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
```

`db.begin()` は public.tenants の DML トランザクションを保護する。  
ただし DDL（CREATE SCHEMA / ALTER TABLE / CREATE POLICY）は `admin_db` セッションで実行される別接続。  
PostgreSQL では DDL は自動コミットのため、`db.begin()` ロールバック時でも  
DDL（スキーマ・テーブル・RLS）は巻き戻らない（create_tenant_schema に独立トランザクションがない）。  
→ 削除時の DDL（DROP SCHEMA CASCADE）も同様に自動コミット。  
ロールバック設計が必要な場合は明示的トランザクションか補償トランザクションを検討。

---

### C-10: 既存の DELETE エンドポイント

`backend/app/routers/admin.py` を全確認:  
テナント DELETE エンドポイントは**存在しない**（POST /tenants のみ）。  
super_admin ルーターにも削除エンドポイントなし（別途確認済み）。

---

## D. 権限・監査

### D-11: super_admin UI の現状

テナント管理 UI（フロントエンド）にテナント一覧・削除機能は**存在しない**（未実装）。  
`backend/app/routers/admin.py` は POST のみ。フロント側の管理画面も未確認。

---

### D-12: 監査ログの記録先

`backend/app/services/audit.py:303,313`:

```python
schema_name = f"tenant_{tenant_id:03d}"
# ...
INSERT INTO {schema_name}.audit_logs ...
```

監査ログはテナント自身のスキーマ内 `audit_logs` テーブルに書き込む。  
`public.system_audit_logs`（中央監査テーブル）は**存在しない**。  
→ テナントスキーマを DROP すると、そのテナントの操作履歴も全消去される。  
テナント削除の監査記録をどこに残すかは ADR で決定が必要。

---

### D-13: 削除実行権限のガード

`backend/app/auth/dependencies.py:453-481`:

```python
async def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not getattr(current_user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="この操作にはJarvis運用admin（中央admin）権限が必要です")
    return current_user
```

`is_super_admin = True` のユーザーのみ通過。  
削除エンドポイントを実装する場合は `Depends(require_super_admin)` を付与すること。  
現在 `is_super_admin=True` のユーザーが本番に何名いるかは**不明（要確認）**。

---

## E. テスト

### E-14: テナント関連テストカバレッジ

`backend/tests/test_tenant_schema_integrity.py:1-50` — ADR-036 Level 4  
`backend/tests/test_rls_tenant_meta_config.py:156-157` — DROP SCHEMA (tenant_998/999)  
`backend/tests/test_products_cross_tenant_fk.py:67,103` — DROP SCHEMA cascade  
`backend/tests/test_meta_channels.py:704` — DROP SCHEMA (tenant_997)

削除機能のテストは**ゼロ**（エンドポイント未実装のため当然）。  
スキーマ DROP の後処理テストとして teardown に実績あり（上記4ファイル）。

---

### E-15: SQLite テスト環境でのカバレッジ限界

`backend/tests/conftest.py:47-48`:

```python
engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
```

CI は SQLite インメモリ。`DROP SCHEMA ... CASCADE` は PostgreSQL 構文であり  
SQLite では実行不可。削除機能の統合テストは PostgreSQL 実機（`RLS_TEST_DATABASE_URL`）が必要。  
`test_tenant_schema_integrity.py` がその先例（`RLS_TEST_DATABASE_URL` 指定時のみ実行）。

---

## 総括

| 項目 | 状態 |
|------|------|
| 論理削除フラグ | is_active のみ・deleted_at なし |
| 認証遮断 | is_active=False で API 全域遮断済み |
| 物理削除 (DROP) | クロススキーマ FK なし・CASCADE 安全 |
| DDL トランザクション | 作成時も非ラップ（削除も同様） |
| 削除エンドポイント | 未実装 |
| 監査ログ保全 | スキーマ内のみ・DROP で消える |
| super_admin ガード | require_super_admin 実装済み |
| Firebase 無効化 | 未実装（ADR 決定が必要） |
| バックグラウンドタスクの is_active フィルタ | 要追加調査 |
| テスト（CI） | SQLite 限界・PostgreSQL 実機テスト必要 |
