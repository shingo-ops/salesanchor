# recon.md — 検証用フィーチャーデモ一式削除

## 関連 ADR

- ADR-073: `docs/adr/ADR-073-storybook-component-catalog.md`（コンポーネント管理）
- ADR-027: `docs/adr/ADR-027-ui-internationalization.md`（i18n キー管理）
- 機能スイッチ本体: PR #2631（tenant_features・require_feature・FeatureGate）

## 調査結果（R-B3）

| ファイル | 変更内容 | 触る |
|---|---|---|
| **変更対象** | `frontend/src/pages/dashboard/DashboardPage.tsx:34,461-465` FeatureGate import + 検証バナー | YES |
| **変更対象** | `backend/app/routers/feature_demo.py` 検証用エンドポイント（ファイル削除） | YES |
| **変更対象** | `backend/app/main.py:51,381-385` feature_demo import + include_router | YES |
| **変更対象** | `frontend/src/locales/ja.json:3060-3062` featureDemo.enabledLabel キー | YES |
| **変更対象** | `frontend/src/locales/en.json:3060-3062` featureDemo.enabledLabel キー | YES |
| 触らない | frontend/src/components/FeatureGate.tsx | NO |
| 触らない | frontend/src/hooks/useFeatures.ts | NO |
| 触らない | backend/app/auth/dependencies.py require_feature() | NO |
| 触らない | backend/app/routers/roles.py tenant_features CRUD | NO |
| 触らない | migrations/ | NO |
