# 設計 — adr-126-impl

**対象ADR**: ADR-126  
**recon**: docs/handoff/adr-126-impl/recon.md  
**日付**: 2026-06-10  
**担当**: Generator

---

## 外部・過去事例の参照と我々への応用

- **E.164（ITU-T国際電話番号規格）**: 国番号込み最大15桁。validate_phone の緩和上限 15桁の根拠。我々への応用: +\d{6,15} パターンで E.164 範囲を受容
- **ISO 3166-1 alpha-2**: 国コード標準。country_code カラムの型（CHAR(2)）と整合。我々への応用: 国リスト SSOT から alpha-2 のみ保存
- **郵便番号制度のない国（UAE・香港等）**: ZIP必須化を採らない根拠。我々への応用: ZIP 任意 + 出口補完（`0000000`）

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| +つき9桁の国際番号（+376367830）がバリデーションを通過する | `pytest tests/test_validate_phone.py::test_e164_short` |
| +なし10〜15桁の既存形式（15551234567）がバリデーションを通過する | `pytest tests/test_validate_phone.py::test_legacy_plus_less` |
| RegisterRequest に billing_display_name / payment_recipient_name が存在する | `pytest tests/test_register_request.py` |
| 公開フォームが英語デフォルトで表示され言語切替できる | Evaluator（Playwright: RegisterPage 表示確認） |
| Section 1 に Payment Account Name が任意項目として表示される | Evaluator（Playwright: RegisterPage Section 1） |
| 「Ship to the same address.」選択時 Section 2 が非表示になる | Evaluator（Playwright: RegisterPage 分岐制御） |
| Country コンボボックスで文字入力→候補絞り込み→ISO alpha-2 保存 | Evaluator（Playwright: RegisterPage Country） |
| ZIP 空欄登録の eLogi CSV に 0000000 が出力される | `pytest tests/test_elogi_csv.py::test_zip_fallback` |
| 配送先Email空欄の eLogi CSV に請求先メールが出力される | `pytest tests/test_elogi_csv.py::test_email_fallback` |
| 全文言が en.json / ja.json のキーで管理され ESLint を通過する | `cd frontend && npm run lint` |

---

## 技術 How・KPI

- **validate_phone**: 正規表現を `^(\+\d{6,15}|\d{10,15}|0\d{9,10})$` に変更。既存 cleaned 処理（スペース・ハイフン・括弧除去）は維持
- **RegisterRequest**: Pydantic スキーマに `billing_display_name: str | None` / `payment_recipient_name: str | None` を追加。registrations_tokens.py で companies UPDATE
- **国リスト SSOT**: `frontend/src/constants/countries.ts`（186か国・name/code/dialCode）。Country と TelephoneDialCode 両コンボボックスが参照
- **英語デフォルト**: RegisterPage の useEffect で i18n.changeLanguage('en')（fallbackLng グローバル変更なし）
- **出口補完**: `_build_csv_entry()` で `zip_code or "0000000"` / `email or billing_email`

---

## 弊害・トレードオフ

- validate_phone 緩和により 6桁+記号の誤入力（+123456）が通過する → 国番号コンボボックス側の UI 制約で補完（コンボ選択後は+dial code が固定）
- 英語デフォルト useEffect は初回マウント時のみ動作 — スタッフUIに影響なし

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | backend/app/schemas/base.py — validate_phone 正規表現変更 | Generator |
| 2 | backend/app/schemas/registration_token.py — RegisterRequest 拡張 | Generator |
| 3 | backend/app/routers/registration_tokens.py — companies UPDATE 追加 | Generator |
| 4 | backend/app/routers/order_shipping_details.py — ZIP/email 出口補完 | Generator |
| 5 | frontend/src/constants/countries.ts — 国リスト新設 | Generator |
| 6 | frontend/src/pages/register/RegisterPage.tsx — 全面改修 | Generator |
| 7 | frontend/src/locales/en.json / ja.json — キー追加 | Generator |
| 8 | backend/tests/test_validate_phone.py — 24テスト | Generator |

---

## 継続

- 完了後: eLogi CSV 出力を本番確認（ZIP埋め値・Email フォールバック）
- 別Issue: 請求書PDFの ZIP 未印字（invoice_renderer.py:115-122 の AddressSnapshot）
