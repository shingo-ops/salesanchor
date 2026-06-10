# recon — sa-foundation-recon-audit

**仕事名**: sa-foundation-recon-audit  
**日付**: 2026-06-10  
**対象ADR**: ADR-131  
**担当**: architect

詳細レポート: `docs/recon/recon-sa-foundation-full-audit-20260610.md`  
フォローアップ: `docs/recon/recon-followup-rls-inventory-suppliers-20260610.md`

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/database.py:1` | get_db — ADR-131 finally ブロック対象 |
| `backend/app/auth/dependencies.py:1` | clear_tenant_context() 追加先 |
| `backend/app/routers/webhook.py:289` | process_messenger_event — ADR-132 対象 BackgroundTask |
| `migrations/056_add_suppliers_type_and_promote_public.sql:14` | public.suppliers — PO決定（2026-06-10）両系統維持 |
| `migrations/20260604_140000_create_own_inventory.sql:27` | own_inventory テーブル作成 |
| `migrations/20260604_140000_create_own_inventory.sql:58` | ENABLE ROW LEVEL SECURITY |
| `migrations/20260607_000000_fix_rls_policy_variable_name.sql:51` | RLS変数名修正（app.tenant_id） |
| `backend/app/services/tenant.py:1070` | {schema}.suppliers RLS有効化 |
| `frontend/src/pages/inventory/OwnInventoryPage.tsx:57` | own_inventory API fetch 経路 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | public.suppliers vs {schema}.suppliers 2系統の設計意図 | PO確認 | ✅ PO決定（2026-06-10）: 両系統正式維持 |
| 2 | smoke[5] BYPASSRLS設計問題かどうか | CI run 27037723851 解析 | ✅ 解消済み（一時的DB状態の問題、追加調査不要） |
| 3 | A∪Bビューの実装予定 | PO確認 | ✅ PO決定（2026-06-10）: A在庫運用開始時まで保留 |
| 4 | get_db finally で circular import になるか | database.py local import で回避 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
