# Recon: /analytics/priority-prospects PG/RLS 実走証明

## 既存 ADR 検索

```
git grep -i "priority.prospect\|priority_prospect" docs/adr/
→ 該当なし（ADR-107 は priority_scoring サービス、別物）
```

`docs/adr/FEATURE-INDEX.md` の "analytics" セクションにも priority-prospects 専用 ADR なし。

## 対象エンドポイント

- `backend/app/routers/analytics.py:1779` — `@router.get("/analytics/priority-prospects", ...)`
- `backend/app/routers/analytics.py:1784` — `async def priority_prospects(...)`
- `backend/app/routers/analytics.py:1801-1806` — team 軸集計: `_fetch_attribute_conversion_summary(db, lead_assign="", scope_params={})`
- `backend/app/routers/analytics.py:1808-1825` — scope=mine リード取得: `WHERE l.assigned_to = :uid`
- `backend/app/routers/analytics.py:1838-1861` — 軸別 smoothed_rate 算出・欠軸除外
- `backend/app/routers/analytics.py:1863` — `ease_rate = sum(sampled_rates) / len(sampled_rates) if sampled_rates else overall_rate`
- `backend/app/routers/analytics.py:1866-1873` — null forecast → 中央値補完 + "monthly_forecast_unset" フラグ
- `backend/app/routers/analytics.py:1875` — `rank_score = round(ease_pct * monthly_forecast, 2)`
- `backend/app/routers/analytics.py:1888` — `items.sort(key=lambda item: (-item.rank_score, item.lead_id))`

## 依存する集計関数（#2452）

- `backend/app/routers/analytics.py:998` — `_fetch_attribute_conversion_axis`: `COUNT(l.converted_deal_id)` で集計（Track A 基準・Track B 不含）
- `backend/app/routers/analytics.py:976` — `_smoothed_attribute_rate`: ベイズ縮退 (k=10)
- `backend/app/routers/analytics.py:959` — `ATTRIBUTE_CONVERSION_SHRINK_K = 10`

## テストファイル

| ファイル | カバレッジ |
|---------|-----------|
| `backend/tests/test_analytics.py:712` | SQLite ユニット（空/順位/中央値） |
| `backend/tests/test_analytics_conversion_by_attribute_rls.py:189` | PostgreSQL RLS（手動スキーマ） |
| `backend/tests/test_priority_prospects_pg_rls.py:1` | PostgreSQL RLS（**本 PR**: rls_bootstrap 使用） |

## rls_bootstrap

- `backend/tests/rls_bootstrap.py:155` — `bootstrap_tenant_schema(admin_engine, tenant_id)`: 本番 migration 順でテナントスキーマ構築
- `backend/tests/rls_bootstrap.py:117` — `tenant_schema_lock(admin_engine, tenant_id)`: xdist 下での直列化

## Track B との分離

- `backend/app/routers/analytics.py:1998-1825` の leads クエリ: `FROM leads l WHERE l.assigned_to = :uid`
- `COUNT(l.converted_deal_id)` (Track A 基準) を使用
- `orders` テーブルへの JOIN なし → Track B 不含 確認済み
