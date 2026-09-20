# Design: remaining-master-crud

## KGI
- `tcg_product_categories` に管理 UI（super-admin パネル＋テナント管理ページ）が揃い、POが画面から CRUD できる
- `condition_aliases` に alias 管理 UI が揃い、POが conditions 編集モーダルから別名を追加・削除できる

| 基準 | 検証方法 |
|---|---|
| /super-admin/analysis-rules で商品カテゴリパネルが表示される | ブラウザで確認 |
| /management-center/product-categories でページが表示される | ブラウザで確認 |
| conditions 編集モーダルに「別名」ボタンが表示される（super-admin・テナント両方） | ブラウザで確認 |
| 別名を追加・削除できる | ブラウザで確認 |

## 変更ファイル一覧

### 新規作成
- `migrations/20260920_070000_product_categories_tenant_id.sql`
- `backend/app/schemas/product_category.py`
- `backend/app/routers/super_admin_product_categories.py`
- `backend/app/routers/product_categories.py`
- `frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx`
- `frontend/src/pages/product-categories/ProductCategoriesPage.tsx`

### 変更
- `backend/app/schemas/condition.py` — ConditionAliasCreate/Response 追加
- `backend/app/routers/super_admin_conditions.py` — alias sub-routes 追加
- `backend/app/routers/conditions.py` — alias sub-routes 追加
- `backend/app/main.py` — product_categories・super_admin_product_categories router 登録
- `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx` — alias UI 追加
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` — product-categories-master 追加
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — ProductCategoriesMasterPanel 追加
- `frontend/src/pages/conditions/ConditionsPage.tsx` — alias UI 追加
- `frontend/src/App.tsx` — product-categories route 追加
- `frontend/src/pages/management-center/ManagementCenterPage.tsx` — nav item 追加
- `frontend/src/config/routeTitles.ts` — route title 追加
- `frontend/src/locales/ja.json` — i18n keys 追加
- `frontend/src/locales/en.json` — i18n keys 追加

## 技術制約
- ADR-027: 全 UI 文字列は t("key") 経由
- ADR-072: write endpoint の db.commit() 直後に reset_tenant_context() 必須
- ADR-144: 金型クラスのみ使用
- HeaderButton type="submit" 不可 → useRef + requestSubmit() パターン使用

## 外部・過去事例の参照と我々への応用
- unit_aliases（`public.unit_aliases`）と同一構造。alias_text/lang カラム名・FK パターンをそのまま踏襲
- StatusMasterPage → ProductCategoriesPage のページ構造（PageLayout + DataTable + Modal パターン）を参照
- UnitMasterPanel → ConditionsMasterPanel・ProductCategoriesMasterPanel のパネル構造を参照

## 維持の仕組み
- i18n: CI の `ja.json`/`en.json` キー整合チェックが差異を検出する
- ADR-072: backend/app/routers/ 変更時のチェックリスト（PR テンプレート）が抜け漏れを防ぐ
- migration-guard: ADD COLUMN IF NOT EXISTS のみ → 冪等・本番 apply 安全

## 守り手
- CI: TypeScript tsc、ESLint、i18n key check が通ること
- migration-guard: ADD COLUMN IF NOT EXISTS のみ → 冪等・安全
