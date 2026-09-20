# Design: product-categories-csv

## recon 参照

`docs/handoff/product-categories-csv/recon.md`

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| スーパー管理者が `/super-admin/product-categories/export` を叩くと CSV が返る | curl でステータス 200・Content-Type: text/csv を確認 |
| スーパー管理者が `/super-admin/product-categories/import/preview` に CSV を送ると行数が返る | curl で digest・total・inserts・updates フィールドを確認 |
| スーパー管理者が `/super-admin/product-categories/import/commit` で digest 一致時に DB が更新される | DB で行数増減を確認 |
| テナントが `/product-categories/export` を叩くと自テナントの CSV が返る | テナント認証付き curl で確認 |
| テナントが `/product-categories/import/commit` で commit 後に reset_tenant_context が呼ばれる | ADR-072 準拠コードレビューで確認 |
| フロントに「更新用CSVを出力」「CSV取り込み」ボタンが表示される | 画面確認 |

## How（実装方針）

### バックエンド

参照パターン: `backend/app/routers/super_admin_units.py:44-420`

1. `_compute_digest(raw: bytes) -> str` — SHA-256 先頭 16 文字
2. `_read_pc_upload(file)` — 拡張子・空ファイル・サイズ・UTF-8 チェック
3. `_parse_product_categories(raw)` — DictReader でバリデーション、`_line` キー付きで返す
4. `GET /super-admin/product-categories/export` — WHERE tenant_id IS NULL ORDER BY id
5. `POST /super-admin/product-categories/import/preview` — digest + inserts/updates カウント
6. `POST /super-admin/product-categories/import/commit` — digest 照合 → upsert → commit
7. テナント側: 同じ構造で tenant_id スコープ、commit 後に `reset_tenant_context()` (ADR-072)

**FastAPI ルート順序**: export/import/preview/commit を `/{category_id}` パスパラメータルートより前に配置（"export" が ID として解釈されるのを防ぐ）。

### フロントエンド

- `ProductCategoriesMasterPanel.tsx` — ContentToolbar に export・import ボタン追加
- `ProductCategoriesPage.tsx` — headerAction に export・import ボタン追加
- `ProductCategoriesImportPage.tsx`（super-admin）— UnitImportPage.tsx 踏襲、API パスのみ変更
- `ProductCategoriesImportPage.tsx`（tenant）— UnitImportTenantPage.tsx 踏襲
- App.tsx — `/super-admin/masters/product-categories/import` と `/management-center/product-categories/import` を追加
- i18n — `productCategoriesCsv` キーセットを ja.json・en.json に追加

## 弊害と対策

| リスク | 対策 |
|-------|------|
| "export" が `/{category_id}` にマッチする | export/import を先に定義（FastAPI の先着優先） |
| digest 不一致による上書き破壊 | 409 エラーで早期 return、フロントで再プレビュー促す |
| テナント間データ漏洩 | WHERE tenant_id = :tenant_id で必ずスコープ |
| commit 後テナントコンテキスト残留 | reset_tenant_context() を commit 直後に呼ぶ（ADR-072） |

## 守り手

`.github/workflows/test.yml` — ruff・TypeScript type check が CI で自動実行される。

## 計画フェーズ

1. バックエンド実装（super_admin + tenant）
2. フロントエンド実装（Panel + Page 両方にボタン、import ページ新規作成）
3. App.tsx ルート追加
4. i18n 追加
5. pre-commit チェック（ruff + tsc）
6. commit・push・Draft PR 作成

## 継続観察

本番適用後、スーパー管理者・テナント双方で export → import ラウンドトリップを 1 件確認すること。
