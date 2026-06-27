# recon.md — 検証用フィーチャーデモ一式削除

## 関連 ADR

- ADR-027: `docs/adr/ADR-027-ui-internationalization.md`（i18n キー管理）

## 調査結果（R-B3）

| ファイル | 変更内容 | 触る |
|---|---|---|
| **変更対象** | `backend/app/main.py:51` feature_demo import 削除 | YES |
| **変更対象** | `backend/app/main.py:381` include_router ブロック削除 | YES |
| **変更対象** | `frontend/src/pages/dashboard/DashboardPage.tsx:34` FeatureGate import 削除 | YES |
| **変更対象** | `frontend/src/pages/dashboard/DashboardPage.tsx:461` 検証バナーブロック削除 | YES |
| **変更対象** | `frontend/src/locales/ja.json:3060` featureDemo キー削除 | YES |
| **変更対象** | `frontend/src/locales/en.json:3060` featureDemo キー削除 | YES |
| 削除 | backend/app/routers/feature_demo.py（ファイルごと削除） | YES |
| 触らない | frontend/src/components/FeatureGate.tsx | NO |
| 触らない | frontend/src/hooks/useFeatures.ts | NO |
| 触らない | backend/app/auth/dependencies.py require_feature() | NO |
| 触らない | backend/app/routers/roles.py tenant_features CRUD | NO |
| 触らない | migrations/ | NO |
