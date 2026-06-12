# recon — fedex-label-validation-wizard

**仕事名**: fedex-label-validation-wizard  
**日付**: 2026-06-12  
**対象ADR**: ADR-129  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/20260612_200000_fedex_creds_unique_env.sql:1` | UNIQUE 制約変更マイグレーション（冪等・DO$$ ガード済み） |
| `scripts/run_all_migrations.sh:1` | fedex_creds_unique_env.sql を登録済み |
| `backend/app/services/carrier_credentials.py:67` | `get_status` に `environment` パラメータ追加（default="production"）|
| `backend/app/services/carrier_credentials.py:114` | `get_credentials` に `environment` パラメータ追加（default="production"）|
| `backend/app/services/carrier_credentials.py:158` | `save_credentials` に `environment` パラメータ追加 |
| `backend/app/services/label_validation.py:1` | FedEx 公式フォーム pypdf オーバーレイ + メール文面生成 |
| `backend/app/assets/Label-Cover-Sheet-form.pdf:1` | FedEx 公式カバーシート v7.0 同梱 |
| `backend/app/routers/integrations.py:346` | carrier_status に `environment` クエリパラメータ追加 |
| `backend/app/routers/integrations.py:371` | save_carrier_credentials で FedEx 以外 production 強制 |
| `backend/app/routers/shipping.py:1` | POST /samples / GET /cover-sheet / GET /email-template 追加 |
| `backend/requirements.txt:31` | `pypdf>=4.0.0,<6.0.0` 追加 |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:64` | pageTab / env state 追加・FedEx 環境タブ + LV タブ |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:49` | 9 ステップウィザード UI |
| `frontend/src/locales/ja.json:1` | `lv*` / `tabCredentials` / `tabLabelValidation` 等 40 キー追加 |
| `frontend/src/locales/en.json:1` | ja.json と同一キー（ADR-027 準拠） |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md:1` | ADR-129 新規（J1〜J5 決定事項） |
| `backend/tests/test_carrier_integrations.py:104` | テストモックに `environment` kwarg 追加、FedEx sandbox テスト追加 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | FedEx 公式カバーシートに AcroForm フィールドがあるか | pypdf で検査 → フィールドなし。reportlab overlay 方式に決定 | ✅ 解消済み |
| 2 | ON CONFLICT 句が environment 込みで動作するか | migration + integration で確認済み | ✅ 解消済み |
| 3 | 既存 Ship/Pickup エンドポイントへの後方互換 | `environment="production"` デフォルト引数で維持 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- FedEx 公式フォーム PDF（v7.0, 178KB）は AcroForm フィールドなし（Word → PDF 変換品）。
  pdfminer で座標を実測し、reportlab テキストオーバーレイ + pypdf merge で入力欄を埋める。
- UNIQUE 制約変更は既存行すべてが `environment='production'` のため、データ損失ゼロ。
