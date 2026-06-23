# Recon — Analytics RLS test session pinning

**対象ADR**: ADR-131  
**日付**: 2026-06-22  
**担当**: Codex

## file:line 参照

| file | lines | 事実 |
|---|---|---|
| `backend/app/auth/dependencies.py:192-237` | `get_current_tenant` が `SET search_path` / `SET app.tenant_id` / `SET app.is_operator` を同一 `AsyncSession` に設定する |
| `backend/app/database.py:46-61` | `get_db` の `finally` で `clear_tenant_context()` を呼び、接続返却前に文脈を消す |
| `backend/app/routers/analytics.py:2288-2331` | `/analytics/conversion-by-attribute` は `db: AsyncSession = Depends(get_db)` と `tenant_id: int = Depends(get_current_tenant)` を持ち、同一リクエスト内で集計する |
| `backend/tests/test_analytics_conversion_by_attribute_rls.py:46-101` | 失敗テストは `override_get_db` と `override_get_current_tenant` を持ち、request 側の接続に tenant 文脈を乗せる必要がある |
| `backend/tests/test_lead_country_control.py:71-155` | 同種の RLS テストでは `override_get_current_tenant` を使って request 経路を固定している |
| `backend/tests/test_channel_type_control.py:107-205` | 同種の RLS テストでは `override_get_current_tenant` を使って request 経路を固定している |

## まとめ

- 失敗機構は「tenant 文脈が乗っていない接続で RLS 集計が実行され、0 行化する」こと。
- この修正では、テストの request 経路で `get_current_tenant` を差し替え、同じセッションに `search_path` と `app.tenant_id` を設定する。
