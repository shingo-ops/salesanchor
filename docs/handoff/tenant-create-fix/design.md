# design.md — 壁1: テナント作成時のトランザクション二重開始 修正

- **日付**: 2026-06-24
- **対象**: `backend/app/routers/admin.py` の `register_tenant`
- **スコープ**: 2層バグのうち Layer 1（壁1）のみ。壁2（号室漏れ）は別途。
- **参照**: [recon.md](./recon.md)

---

## 何の問題か

新テナント作成処理で、ログイン確認（`get_current_user`）の時点で
SQLAlchemy `AsyncSession` が自動でトランザクションを開始（autobegin）済み。
なのに `admin.py:57` が `async with db.begin():` でもう一度開始を宣言
→ `InvalidRequestError: A transaction is already begun` → HTTP 500。

実機 R-4 で確認済み（2026-06-24、本番 API）。

---

## KGI（壁1の成功条件）

```
壁1修正後、テナント作成 API を叩くと、
500「A transaction is already begun」が出なくなる。
（その先で壁2の 42501 が出るところまで進めば、壁1突破の証拠）
```

---

## 変更対象

**ファイル**: `backend/app/routers/admin.py`  
**関数**: `register_tenant`（`admin.py:55〜83`）

### 変更前

```python
    # テナント作成（ロールバック保証: db.begin() で明示的なトランザクション開始）
    # create_tenant_schema が途中で失敗した場合も tenant レコードが残らないよう保証する。
    async with db.begin():
        tenant = Tenant(
            tenant_name=data.tenant_name,
            tenant_code=data.tenant_code,
            is_active=True,
        )
        db.add(tenant)
        await db.flush()  # IDを確定させる（commit前にIDが必要）

        # 専用スキーマを自動生成（テーブル + RLSポリシー込み）
        schema_name = await create_tenant_schema(db, tenant.id, admin_db=admin_db)

        # 監査ログ記録
        await record_audit_log(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="create",
            table_name="tenants",
            record_id=tenant.id,
            new_data={
                "tenant_name": tenant.tenant_name,
                "tenant_code": tenant.tenant_code,
                "schema_name": schema_name,
            },
        )
    # async with db.begin() がコミットを行う（例外時は自動ロールバック）
```

### 変更後

```python
    # テナント作成（autobegun トランザクションを継続使用。auth.py/companies.py と同パターン）
    # create_tenant_schema が途中で失敗した場合は except で明示ロールバックし、
    # tenant レコードが残らないよう保証する。
    try:
        tenant = Tenant(
            tenant_name=data.tenant_name,
            tenant_code=data.tenant_code,
            is_active=True,
        )
        db.add(tenant)
        await db.flush()  # IDを確定させる（commit前にIDが必要）

        # 専用スキーマを自動生成（テーブル + RLSポリシー込み）
        schema_name = await create_tenant_schema(db, tenant.id, admin_db=admin_db)

        # 監査ログ記録
        await record_audit_log(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="create",
            table_name="tenants",
            record_id=tenant.id,
            new_data={
                "tenant_name": tenant.tenant_name,
                "tenant_code": tenant.tenant_code,
                "schema_name": schema_name,
            },
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
```

### 変更点まとめ

1. `async with db.begin():` を削除（インデント1段解除）
2. 全体を `try:` で囲む
3. `record_audit_log` の後に `await db.commit()` を追加
4. `except Exception: await db.rollback(); raise` を追加
5. コメントを実態に合わせて書き換え

---

## 触らない範囲

- **壁2（号室漏れ）は今回触らない**（`set_tenant_context` 追加は壁2の設計で）
- `tenant.py` の `create_tenant_schema` 内部は触らない
- テナント作成のロジック順序・内容は変えない（tx の宣言方法のみ修正）
- 他 router・他エンドポイントは触らない

---

## 弊害対策

元の `async with db.begin():` が持っていた「例外時自動ロールバック」保証を、
`except Exception: await db.rollback(); raise` で明示的に再現（`auth.py:125` と同パターン）。

---

## KPI（成功判定）

| 基準 | 検証方法 |
|---|---|
| `async with db.begin()` 削除・明示 commit/rollback 追加 | `git diff` |
| テナント作成 API で「transaction already begun」が出ない | R-4 再実行 |
| その先で 42501 が出る（壁2露出） | R-4 ログ |
| 既存データ影響なし（新規作成パスのみ） | 既存テナント確認 |
| CI 緑 | CI |

---

## 継続・フォロー

- 壁1突破確認後 → 壁2（号室漏れ）設計・実装へ
- `super_admin_tenants.py:43` の `async with db.begin():` も同リスクあり（フォロー項目）
- `lint-tenant-schema.yml` の対象に `services/tenant.py` を追加（ADR 起案候補）
