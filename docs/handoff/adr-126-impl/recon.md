# recon — adr-126-impl

**仕事名**: adr-126-impl  
**日付**: 2026-06-10  
**対象ADR**: ADR-126  
**担当**: architect / Generator

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/schemas/base.py:16` | validate_phone 正規表現 — 変更対象 |
| `backend/app/schemas/registration_token.py:116` | RegisterRequest クラス — billing_display_name/payment_recipient_name 追加対象 |
| `backend/app/routers/registration_tokens.py:105` | 公開 POST /register エンドポイント — companies UPDATE 差し込み対象 |
| `backend/app/routers/order_shipping_details.py:292` | _build_csv_entry() — ZIP埋め値・Email フォールバック差し込み対象 |
| `backend/app/services/shipping_carriers/elogi.py:109` | email 出力行 |
| `backend/app/services/shipping_carriers/elogi.py:113` | zip_code 出力行 |
| `migrations/028_create_companies.sql:74` | billing_display_name カラム — 実在確認済み（マイグレーション不要） |
| `migrations/028_create_companies.sql:75` | payment_recipient_name カラム — 実在確認済み |
| `migrations/030_create_company_contact_subtables.sql:46` | company_addresses テーブル — address_line_1〜3/city/state/zip/country_code/telephone/email/tax_id 全実在確認 |
| `migrations/030_create_company_contact_subtables.sql:51` | address_line_3 カラム — 実在確認済み |
| `frontend/src/pages/register/RegisterPage.tsx:1` | 公開登録フォームページ — 全面改修対象 |
| `frontend/src/i18n.ts:36` | fallbackLng:"ja" — グローバル変更禁止（公開フォームのみ en デフォルト） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 既存 DB に +なし10桁未満の電話番号があるか | company_addresses テーブル scan で確認 → +376367830（9桁）実在確認済み | ✅ 解消済み |
| 2 | 国リスト静的ファイルの既存資産 | frontend/src/ 全 grep → 既存なし、新規作成が必要 | ✅ 解消済み |
| 3 | eLogi CSV ZIP/email の差し込み口 | order_shipping_details.py:292 _build_csv_entry() & elogi.py:109,113 で確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- ADR-097 実装済み（トークン検証・テナント決定・住所帳1:N）は本ADRで一切変更しない
- AddressSnapshot の zip 未印字（invoice_renderer.py:115-122）は Scope外（別Issue）
