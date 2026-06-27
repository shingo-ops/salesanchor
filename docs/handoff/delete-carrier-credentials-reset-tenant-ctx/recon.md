# recon: delete-carrier-credentials-reset-tenant-ctx

## 対象ADR
- ADR-072（write endpoint: db.commit() 直後に reset_tenant_context() 必須）

## サーバーログ確認
- `DELETE /integrations/carriers/fedex/credentials` → 500 + "データベースエラー"
- エラー箇所: `audit_logs` RLS `current_setting('app.tenant_id', true)::INTEGER` が空文字でクラッシュ

## 根本原因
`backend/app/routers/integrations.py:459-468`（#2621 以前の状態）:

```python
await carriers.delete_credentials(...)  # 内部 db.commit()（carrier_credentials.py:210）
                                         # ← pool が別コネクション払い出し → app.tenant_id = ''
await record_audit_log(...)              # ← app.tenant_id='' → audit_logs RLS クラッシュ
await db.commit()
await reset_tenant_context(db, tenant_id)  # ← 位置が遅い（save と全く同根）
```

## 変更箇所
`backend/app/routers/integrations.py:459-468`

`reset_tenant_context` を `delete_credentials` の直後、`record_audit_log` の前に移動。
`save_carrier_credentials` の #2621 修正と完全に同じパターン。

## データ不整合の有無
`delete_credentials` の内部 commit は成功するため、鍵レコードは削除済み。
audit_log のみ欠落。「鍵が消えたがログ失敗」の状態が残っている可能性がある（要 PO 確認）。
