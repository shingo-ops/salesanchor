# design.md — deal-removal 便C

> **素人向け1行説明**: 社内で使わなくなった「案件管理」APIとその画面を削除し、関連する権限設定を「リード管理」権限に引き継いだ。

親仕様書: [../../specs/db-ssot/deal-removal/design.md](../../specs/db-ssot/deal-removal/design.md)  
recon参照: [./recon.md](./recon.md)  
対象ADR: ADR-121

---

## 外部・過去事例の参照と我々への応用

本便は便A（deals 新規作成廃止）・便B（deal_id FK 撤去）の延長線上にある第3フェーズ。
- **便A**: POST /deals を 405 で封鎖（API形だけ残す）
- **便B**: orders/leads/quotes の deal_id FK を削除
- **便C（本便）**: deals router/schema/テスト を物理削除、フロント導線を除去
- **便D（次便）**: deals テーブル本体 DROP、conftest DDL 除去、権限データ改名

REST API 廃止のベストプラクティス（Stripe/GitHub等）では「段階的廃止→405返却→物理削除」の順序を推奨。本便はその「物理削除」フェーズに相当。

---

## 変更サマリ

### バックエンド

| 変更 | 詳細 |
|------|------|
| `routers/deals.py` 削除 | GET/PATCH/DELETE /deals エンドポイント群（305行） |
| `schemas/deal.py` 削除 | DealCreate/DealUpdate/DealResponse 等（126行） |
| `main.py` 修正 | deals import + include_router 除去 |
| `archives.py` 修正 | ARCHIVABLE_TABLES から "deals" を除去（ローンチ前・データなし） |
| `close_reasons.py` 修正 | deals.view/update → leads.view/update に付け替え |

### フロント

| 変更 | 詳細 |
|------|------|
| `DesktopShell.tsx` | showManagementCenter の `hasAny()` から "deals.view" を除去 |
| `RolesPage.tsx` | MENU_VIEW_KEY から "案件": ["deals.view"] エントリを除去 |

### テスト

| 変更 | 詳細 |
|------|------|
| `test_deals.py` 削除 | deals API テスト全件（341行） |
| `conftest.py` 修正 | `_audit_targets` から "app.routers.deals" 除去（モジュール削除による） |
| `test_security.py` 修正 | /api/v1/deals テストパラメータと test_negative_amount_rejected を除去 |

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| GET /api/v1/deals が 404 を返す | curl or pytest でレスポンスコード確認 |
| POST /api/v1/deals が 404 を返す | curl or pytest でレスポンスコード確認 |
| GET /api/v1/close-reasons が 200 を返す（leads.view 権限保持時） | test_close_reasons.py 12 passed |
| backend tests: 既存不安定事象以外に赤なし | 2 failed（test_meta_graph/test_analytics）のみ、deals起因ゼロ |
| frontend tsc build が成功する | `npm run build` → ✓ built in 806ms |
| DesktopShell: deals.view 権限なしでも管理センター表示不変 | 他の権限（orders.view等）でカバー済み |
| RolesPage: 「案件」カテゴリ行が非表示 | deals.view エントリ除去 |

---

## 便Dへの引き継ぎ（権限データ本体は別テーマ予約）

本便では触らない範囲:

- **`conftest.py` deals DDL / DELETE FROM deals** → 便D/段階③で除去
- **`ALL_TEST_PERMISSIONS` の deals.* エントリ** → 便D/段階③で除去
- **本番DB deals テーブル DROP** → 便D/段階③で実施（PO GO 必須）
- **権限データ本体（deals.* 70行 → leads.* 改名）** → reservation: deals-perms-rename（別テーマ・別便）

archives.py: deals 除去はローンチ前確認不要（deals テーブル行はゼロ）。

---

## 維持の仕組み

**守り手**: process-artifacts gate（`.github/workflows/process-artifacts.yml`）  
**対象**: deals API の再追加を防ぐ  
**具体策**: `routers/deals.py` および `schemas/deal.py` が復活した場合、CI が failing し merge できない体制。また main.py に include_router(deals) を再追加すると ImportError が発生するため物理的に防止される。
