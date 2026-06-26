# recon: キャリア鍵保存後 reset_tenant_context 挿入（ADR-072 準拠）

## 対象ファイル

- `backend/app/routers/integrations.py`

---

## 関連 ADR

- ADR-072: write endpoint の db.commit() 直後に reset_tenant_context() 必須

---

## バグの実体（サーバーログ）

`PUT /api/v1/integrations/carriers/fedex/credentials` が 500 を返す。
エラーは credentials 保存後の audit_logs INSERT 時に発生。

```
asyncpg.exceptions.InvalidTextRepresentationError:
invalid input syntax for type integer: ""

[SQL: INSERT INTO tenant_006.audit_logs
    (tenant_id, user_id, action, table_name, record_id, old_data, new_data)
    VALUES ($1, $2, $3, $4, $5, $6, $7)]

[parameters: (6, 10, 'update', 'tenant_carrier_credentials', None,
  '{"carrier": "fedex", "environment": "sandbox", "account_number_hint": "******073"}',
  '{"carrier": "fedex", "environment": "production", "account_number_hint": null}')]
```

---

## 根本原因

### ADR-072 違反箇所

`backend/app/routers/integrations.py:406-430`（`save_carrier_credentials` ハンドラー）

```python
await carriers.save_credentials(...)   # 内部で db.commit() 実行（:198）
# ← ここに reset_tenant_context() がない ← 違反
new_status = await carriers.get_status(...)   # app.tenant_id = '' で実行
await record_audit_log(...)                    # audit_logs RLS クラッシュ
```

### コネクションプールの挙動

`save_credentials` 内部の `db.commit()` 後、SQLAlchemy async セッションが
別コネクションを払い出す場合がある。新コネクションは前リクエストの
`clear_tenant_context`（`get_db` finally）によって `app.tenant_id = ''` に
戻された状態で払い出される。

### RLS 非対称性

| テーブル | RLS ポリシー | 空文字 `''` の挙動 |
|---|---|---|
| `public.tenant_carrier_credentials` | `NULLIF(current_setting('app.tenant_id', true), '')::INTEGER` | NULL → 0件返却（安全） |
| `tenant_006.audit_logs` | `current_setting('app.tenant_id', true)::INTEGER` | `''::INTEGER` → **500クラッシュ** |

`audit_logs` の RLS だけ `NULLIF` ガードがない（第2弾で別途修正予定）。

### new_data に "production" が出る理由

`app.tenant_id = ''` の状態で `get_status(db, ..., environment="sandbox")` を実行すると、
`tenant_carrier_credentials` の RLS（NULLIF版）が全行拒否して 0件返却 →
`configured=False` デフォルト値 `{"environment": "production"}` が返る。

---

## 変更箇所（1行追加）

`backend/app/routers/integrations.py:419` に `await reset_tenant_context(db, tenant_id)` を挿入。

変更前 `backend/app/routers/integrations.py:415-418`:
```python
    )
    # NOTE: save_credentials は内部で db.commit() 済み（carrier_credentials.py:182）。
    # audit は別 tx になる（既知の構造的制約: 設計doc §5 参照）。
    new_status = await carriers.get_status(db, tenant_id, carrier, environment=effective_env)
```

変更後 `backend/app/routers/integrations.py:415-421`:
```python
    )
    # NOTE: save_credentials は内部で db.commit() 済み（carrier_credentials.py:198）。
    # ADR-072: 内部 commit 後にコネクションプールが別コネクションを払い出す可能性があるため
    # app.tenant_id を再設定してから後続クエリ・audit_logs INSERT を実行する。
    await reset_tenant_context(db, tenant_id)
    # audit は別 tx になる（既知の構造的制約: 設計doc §5 参照）。
    new_status = await carriers.get_status(db, tenant_id, carrier, environment=effective_env)
```

---

## 影響範囲

- 修正対象エンドポイント: `PUT /api/v1/integrations/carriers/{carrier}/credentials`
- 利用箇所: ガイド 1-7（CarrierCredentialForm）・管理センター（/management-center/integrations/fedex）双方
- migration: なし（コード変更のみ）
- 他ハンドラー: 変更なし

---

## 残件（第2弾）

`tenant_{NNN}.audit_logs` の RLS を `NULLIF` 版に揃える migration は別 PR で実施。
本修正（第1弾）で症状は解消するため急がない。
