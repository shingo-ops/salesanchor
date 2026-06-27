# recon.md — テナント作成 RLS/トランザクションバグ調査

- **日付**: 2026-06-24
- **対象KGI**: POST /api/v1/tenants で新テナント作成が 42501 エラーなく成功する
- **参照**: [design.md](./design.md)

---

## R-1: 既存 ADR 確認

- `docs/adr/FEATURE-INDEX.md` + `git grep -i tenant docs/adr/` 実施
- ADR-034: 新規テナント作成時の不変条件チェック（backend/CLAUDE.md §2）
- ADR-045: Migration additive-only 原則（downgrade未整備）
- ADR-072: write endpoint で `db.commit()` 直後に `reset_tenant_context()` 必須
- ADR-089: `companies` テーブルが取引先 SSOT（`customers` 廃止済み）

---

## R-2: RLS 号室漏れ横断 recon

### 号室設定なしで RLS テーブルを触る疑惑箇所

| # | ファイル:行 | テーブル | 状態 |
|---|---|---|---|
| 1 | `backend/app/services/tenant.py:1474` | `{schema}.roles` | 号室なし → seed失敗候補 |
| 2 | `backend/app/services/tenant.py:1094` | `{schema}.role_permissions` | 号室なし → seed失敗候補 |
| 3 | `backend/app/services/tenant.py:1127` | `{schema}.channel_masters` | 号室なし → seed失敗候補 |

### CI gate の穴（ADR-072）

- `.github/workflows/lint-tenant-schema.yml` のカバー対象: backend/app/routers/ のみ
- `backend/app/services/tenant.py` は**対象外**（gate 未検知）

---

## R-3: Layer 特定

### Layer 1 — トランザクション二重開始（即時 500 ブロッカー）

```
backend/app/routers/admin.py:57
    async with db.begin():   ← ❌ autobegin済みセッションに二重begin
```

autobegin の発火源:
```
backend/app/auth/dependencies.py:126  # cache HIT → db.execute() → autobegin
backend/app/auth/dependencies.py:167  # cache MISS → db.execute() → autobegin
```

SQLAlchemy 2.x 動作: `AsyncSession` は `autobegin=True`（デフォルト）。
`async with session.begin():` を autobegun 済みセッションに呼ぶと
`InvalidRequestError: "A transaction is already begun on this Session."` → HTTP 500。

### Layer 2 — 号室漏れ（Layer 1 解消後に露出する 42501）

`create_tenant_schema`（`backend/app/services/tenant.py`）内の seed 関数群が
`app.tenant_id` を SET せずに RLS 有効テーブルへ INSERT。
→ `SQLSTATE 42501: permission denied for table roles` 等。

---

## R-4: 実機実証（Firebase ID トークン → POST /api/v1/admin/tenants）

**実施日**: 2026-06-24  
**環境**: 本番 API `https://api.salesanchor.jp/`  
**手順**: Firebase Admin SDK でカスタムトークン生成 → ID トークン取得 → POST

**結果（Layer 1 修正前）**:
```
HTTP 500
{"detail": "A transaction is already begun on this Session."}
```

Layer 1（`backend/app/routers/admin.py:57` の `async with db.begin():`）が発火していることを実機で確認。
DB ロールバック確認済み（`verify-rls-42501` テナントは DB に残存なし）。

---

## R-5: 安全な修正パターン確認

### 動いている手本

| ファイル:行 | パターン |
|---|---|
| `backend/app/routers/auth.py:131` | `await db.commit()`（begin なし・autobegun 直接使用） |
| `backend/app/routers/auth.py:125` | `except Exception: await db.rollback()` |
| `backend/app/routers/companies.py:465` | `await db.commit()` → `reset_tenant_context()` |

### super_admin_tenants.py の注意点

`backend/app/routers/super_admin_tenants.py:43` の `async with db.begin():` も
同じ double-begin リスクあり（`require_super_admin → get_current_user → get_db` 経由で
同一 db が autobegun 済み）。フォロー項目として記録。
