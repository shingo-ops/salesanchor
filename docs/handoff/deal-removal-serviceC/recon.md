# recon.md — deal-removal 便C

対象ADR: ADR-121（deals テーブル段階的廃止）

## 削除対象ファイル（実測）

| ファイル | 種別 | 内容 |
|---------|------|------|
| `backend/app/routers/deals.py:1-311` | 削除 | GET/PATCH/DELETE /deals + POST(405封鎖) |
| `backend/app/schemas/deal.py:1-127` | 削除 | DealCreate/DealUpdate/DealResponse/DealStatus/DealStage/Currency Enum |
| `backend/tests/test_deals.py:1-341` | 削除 | deals API の全テストケース |

## 変更ファイル（実測）

| ファイル:行 | 変更前 | 変更後 |
|-----------|-------|-------|
| `backend/app/main.py:40` | `deals,` import | 削除 |
| `backend/app/main.py:278-281` | `app.include_router(deals.router, ...)` | 削除 |
| `backend/app/routers/archives.py:31` | `{"deals", "orders", "leads", "quotes", "invoices"}` | `{"orders", "leads", "quotes", "invoices"}` |
| `backend/app/routers/close_reasons.py:33` | `require_permission("deals.view")` | `require_permission("leads.view")` |
| `backend/app/routers/close_reasons.py:73` | `require_permission("deals.update")` | `require_permission("leads.update")` |
| `backend/app/routers/close_reasons.py:100` | `require_permission("deals.update")` | `require_permission("leads.update")` |
| `backend/tests/conftest.py:1545` | `"app.routers.deals"` in `_audit_targets` | 削除 |
| `backend/tests/test_security.py:33-34` | `/api/v1/deals` GET/POST テストパラメータ | 削除 |
| `backend/tests/test_security.py:151-158` | `test_negative_amount_rejected` | 削除 |
| `frontend/src/components/DesktopShell.tsx:185` | `"deals.view"` in `showManagementCenter hasAny(...)` | 削除 |
| `frontend/src/pages/roles/RolesPage.tsx:64` | `"案件": ["deals.view"]` in `MENU_VIEW_KEY` | 削除 |

## 既存ADR調査結果

- `git grep -i deals docs/adr/` → ADR-121 にて deals 段階的廃止を確認
- `docs/adr/FEATURE-INDEX.md` → deal-removal の各便は ADR-121 傘下

## 範囲外（便D/段階③ 対応）

- `backend/tests/conftest.py:413` — deals テーブル DDL（SQLite）
- `backend/tests/conftest.py:1365` — `DELETE FROM deals` cleanup
- `backend/tests/conftest.py:1457` — `ALL_TEST_PERMISSIONS` の deals.* エントリ
- `v_company_stats` ビューの deals JOIN
- 本番DB deals テーブル DROP
- 権限データ本体（deals.* 70行 → leads.* 改名）

## deals 参照の残存確認

```
rg -n "from app.routers import.*deals|import deals|from app.schemas.deal" backend/app/
→ 0件（クリーン）
```

フロント `src/api/` に deals 専用 API クライアントは存在しなかった（既に前段便で除去済み）。
`src/pages/` に deals ページは存在しなかった（同上）。
