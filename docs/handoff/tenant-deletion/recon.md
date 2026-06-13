# recon — テナント削除機能

**仕事名**: tenant-deletion  
**日付**: 2026-06-14（初版 2026-06-13、修正版）  
**担当**: shingo-cc

---

## ADR 検索結果

### 検索コマンドと結果

```
git grep -il "tenant.*delet\|DELETE.*tenant\|DROP SCHEMA\|論理削除\|物理削除" docs/adr/
→ docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md
   docs/adr/ADR-072-tenant-schema-prefix-enforcement.md
   docs/adr/ADR-090-products-central-unification.md
   docs/adr/ADR-131-tenant-context-auto-reset.md
```

`docs/adr/FEATURE-INDEX.md` キーワード照合:

| キーワード | 該当ADR |
|-----------|---------|
| テナント / RLS / schema prefix / tenant_context | ADR-072 / ADR-034 / ADR-036 |
| 権限 / role / 認証 / Firebase | ADR-023 / ADR-032 |

### 各ADRの確認結果

| ADR | タイトル | テナント削除との関係 |
|-----|---------|-------------------|
| **ADR-023** | スタッフライフサイクル3層同期 `docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md:35` | **参照必須**。スタッフ削除時に Firebase Auth + public.users + tenant_NNN.staff を3層同期する設計。テナント削除でも同パターン（Firebase 無効化 + DB削除）が必要になる。Firebase 無効化方針の判断材料。 |
| **ADR-032** | Firebase Authentication カスタムドメイン | 確認済み・今回直接影響なし。認証ドメイン切替のみ。テナント削除ロジックへの影響ゼロ。 |
| **ADR-034** | 新規テナントmigration自動化 `docs/adr/ADR-034-tenant-migration-automation.md` | 確認済み・参照推奨。テナント作成の逆順操作（DROP SCHEMA等）を設計する際に作成フロー全体像の正本として参照する。 |
| **ADR-036** | テナントスキーマ整合性 `docs/adr/ADR-036_tenant_schema_integrity.md` | 確認済み・参照推奨。Level 4 テスト（`test_tenant_schema_integrity.py`）が整合性の基準。削除後の残留確認テストを追加する際の先例。 |
| **ADR-072** | テナントスキーマプレフィックス強制 `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md` | **適用必須**。削除エンドポイントも write endpoint のため `db.commit()` 直後に `reset_tenant_context()` 必須。 |
| **ADR-131** | テナントコンテキスト自動リセット `docs/adr/ADR-131-tenant-context-auto-reset.md` | **適用必須**。ADR-072 の強化版。削除エンドポイント実装時に同様に適用。 |
| **ADR-090** | Products中央化 `docs/adr/ADR-090-products-central-unification.md:35` | 確認済み・今回直接影響なし。public.products と tenant スキーマの接点あるが、削除 CASCADE 対象外（公開テーブル側）。 |

**未起案**: テナント削除プロセス自体を定めた ADR は存在しない（本 recon が起案判断材料）。

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

**バックグラウンドタスク（`backend/app/tasks/`）の is_active フィルタ調査結果**:

| ファイル | 確認箇所 | is_active フィルタ | 判定 |
|---------|---------|-------------------|------|
| `priority_scoring_check.py:92` | `WHERE is_active = TRUE` | あり ✅ | 安全 |
| `dashboard.py:161` | `WHERE is_active = true` | あり ✅ | 安全 |
| `translation.py:58,156` | `WHERE is_active = true` | あり ✅ | 安全 |
| `verify_meta_subscriptions.py:90` | `WHERE is_active = true` | あり ✅ | 安全 |
| `avatar.py:101` | `WHERE is_active = true` | あり ✅ | 安全 |
| `refresh_meta_tokens.py:105` | `WHERE is_active = true` | あり ✅ | 安全 |
| `data_deletion.py:55` | `WHERE is_active = true` | あり ✅ | 安全 |
| `maintenance.py:114` | `WHERE is_active = true` | あり ✅ | 安全 |
| `sa02_recon_monitor.py:57` | `WHERE is_active = true` | あり ✅ | 安全 |
| **`reports.py:187`** | `export_csv(tenant_id: int, ...)` | **なし ⚠️** | 要確認 |

**⚠️ reports.py の詳細**:  
`backend/app/tasks/reports.py:187` の `export_csv(tenant_id: int, report_type: str)` は  
`tenant_id` をパラメータとして受け取る構造で、自身では `is_active` チェックをしない。  
Celery タスクとして呼び出された場合、呼び出し元が無効テナントの ID を渡すと  
論理削除後のテナントに対してもCSVエクスポートが実行される可能性がある。  
→ 呼び出し元の Celery キュー投入箇所で `is_active` を確認しているか追加調査が必要。

**結論**: 主要バックグラウンドタスク9件は `is_active = TRUE` フィルタあり。  
`reports.py` のみ呼び出しチェーン確認が残件。

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
→ ADR-023 のスタッフ3層同期パターンを参照し、テナント削除時に Firebase 側も無効化するか否かは ADR で決定が必要。

---

## C. スキーマ DROP の安全性

### C-7: バックアップ運用

`scripts/backup.sh` — 30 日保持の pg_dump  
`.github/workflows/deploy.yml:141-160` — デプロイ前自動バックアップ

DROP 前の手動バックアップ手順は未整備（スクリプト化されていない）。  
バックアップ取得後 DROP するまでの猶予ウィンドウも規定なし。

---

### C-8: クロススキーマ FK の有無（初版訂正）

**初版の「tenant_NNN から他スキーマへの FK は存在しない」は誤り。以下のとおり訂正する。**

`backend/app/services/tenant.py` の `_TENANT_TABLES_SQL` 定義:

```sql
-- tenant.py:493
permission_id INTEGER NOT NULL REFERENCES public.permissions(id) ON DELETE CASCADE,

-- tenant.py:580
user_id INTEGER UNIQUE REFERENCES public.users(id),

-- tenant.py:1020
user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,

-- tenant.py:1032
created_by INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
```

**存在するクロススキーマ FK（tenant_NNN → public）**:
- `tenant_NNN.role_permissions.permission_id → public.permissions(id)` (tenant.py:493)
- `tenant_NNN.{staff系テーブル}.user_id → public.users(id)` (tenant.py:580, 1020)
- `tenant_NNN.{テーブル}.created_by → public.users(id)` (tenant.py:1032)

**DROP SCHEMA CASCADE への影響評価**:  
FK は tenant_NNN 側のテーブルに定義されている（参照先が public）。  
`DROP SCHEMA tenant_NNN CASCADE` はスキーマ内テーブル（FK制約ごと）を削除するため、  
public 側の `permissions` / `users` テーブル自体には影響しない。  
ただし断定には実機確認が必要。

**実機確認用 SQL（READ ONLY トランザクション内で実行すること）**:

```sql
SELECT
  conname,
  conrelid::regclass AS from_table,
  confrelid::regclass AS to_table
FROM pg_constraint
WHERE contype = 'f'
  AND (conrelid::regclass::text LIKE 'tenant_004.%'
       OR confrelid::regclass::text LIKE 'tenant_004.%')
ORDER BY conrelid::regclass::text;
```

---

### C-9: DDL トランザクション保証（初版訂正）

`backend/app/routers/admin.py:57-83`:

```python
async with db.begin():
    # public.tenants INSERT (db セッション)
    await db.flush()
    schema_name = await create_tenant_schema(db, tenant.id, admin_db=admin_db)
```

`backend/app/database.py:88-95` — `get_admin_db()`:

```python
async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    async with AdminSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # ← 成功時の session.commit() が存在しない
```

`backend/app/database.py:84-85`:

```python
admin_engine = create_async_engine(ADMIN_DATABASE_URL, **_admin_engine_kwargs)
AdminSessionLocal = sessionmaker(admin_engine, class_=AsyncSession, expire_on_commit=False)
# isolation_level="AUTOCOMMIT" は設定されていない
```

`backend/app/services/tenant.py:1573`:

```python
# commitは呼び出し元で行う（監査ログ等と一括でcommitするため）
```

**初版の「PostgreSQL では DDL は自動コミット」という断定は誤り。以下のとおり訂正する。**

- `admin_db` セッションは `autocommit=True` 未設定、成功時の `session.commit()` も存在しない
- SQLAlchemy + asyncpg の組み合わせで DDL が暗黙コミットされるかどうかはコードから追跡できない
- 既存のテナント作成が本番で動作している事実があるが、その挙動の根拠はコードのみでは確定できない
- **既存作成フローの DDL 永続化挙動は実機またはテストで要確認**

**削除設計の必須論点**:  
削除エンドポイント実装では `DROP SCHEMA CASCADE` の永続化を確実にするため、  
以下のいずれかを明示的に選択すること（ADR で決定）:
- `await admin_db.commit()` を DROP 後に明示実行
- `isolation_level="AUTOCOMMIT"` 接続を DROP 専用に使用
- 補償トランザクション（DROP 失敗時のリカバリ手順）を設計

---

### C-10: 既存の DELETE エンドポイント

`backend/app/routers/admin.py` を全確認:  
テナント DELETE エンドポイントは**存在しない**（POST /tenants のみ）。  
super_admin ルーターにも削除エンドポイントなし（別途確認済み）。

---

## D. 権限・監査

### D-11: super_admin UI の現状と今回スコープ

**今回の実装対象: backend API のみ。UI（削除ボタン等）は今回スコープ外。**

現状:
- テナント管理 UI（フロントエンド）にテナント一覧・削除機能は**存在しない**（未実装）
- `backend/app/routers/admin.py` は POST のみ
- フロントエンド側でテナント削除ページ・ルートは存在しない  
  （`git grep -r "tenant.*delet\|deleteTenant" frontend/` 結果: 0件）

Phase 3 設計では backend エンドポイント（API）のみを対象とし、  
UI（管理画面の削除ボタン）は別フェーズとして明示的にスコープ外とする。

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
テナント削除の監査記録をどこに残すかは ADR で決定が必要（例: public.tenant_deletion_audit 新設）。

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
C-9 の DDL 永続化挙動確認もこの PostgreSQL 実機テストで実施すること。

---

## 総括

| 項目 | 状態 |
|------|------|
| 論理削除フラグ | is_active のみ・deleted_at なし |
| 認証遮断 | is_active=False で API 全域遮断済み |
| バックグラウンドタスクの is_active フィルタ | 9件すべて ✅・reports.py のみ呼び出し元確認残件 |
| クロススキーマFK | **存在する**（tenant_NNN→public.permissions/users）・DROP CASCADE は安全だが実機確認必須 |
| DDL トランザクション | admin_db に commit() なし・DDL 永続化挙動は実機確認必要 |
| 削除エンドポイント | 未実装 |
| 監査ログ保全 | スキーマ内のみ・DROP で消える・中央保全先の ADR 決定が必要 |
| super_admin ガード | require_super_admin 実装済み |
| Firebase 無効化 | 未実装（ADR-023 参照・ADR 決定が必要） |
| UI スコープ | 今回対象外（backend API のみ） |
| テスト（CI） | SQLite 限界・PostgreSQL 実機テスト必要 |
| ADR 対象 | テナント削除 ADR 未起案・本 recon が起案材料 |
