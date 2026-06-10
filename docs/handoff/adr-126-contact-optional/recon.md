# recon — ADR-126 追補: 担当者名任意化・フォールバック

**仕事名**: adr-126-contact-optional  
**日付**: 2026-06-11  
**対象ADR**: ADR-126  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/schemas/registration_token.py:116` | `RegisterRequest` クラス定義。`contact_name: Optional[str]` フィールド確認 |
| `backend/app/schemas/registration_token.py:141` | `validate_contact_required` モデルバリデーター（担当者名必須チェック）— 削除対象 |
| `backend/app/routers/registration_tokens.py:180` | `SELECT id FROM companies WHERE lead_id` — `billing_display_name` 追加取得対象 |
| `backend/app/routers/registration_tokens.py:244` | `contact_code` 生成 + contacts INSERT — フォールバック適用箇所 |
| `backend/app/routers/registration_tokens.py:245` | `"display_name": data.contact_name or ""` — フォールバック変更前の行 |
| `frontend/src/pages/register/RegisterPage.tsx:149` | `if (!contactName.trim())` — 必須バリデーション（削除対象） |
| `frontend/src/pages/register/RegisterPage.tsx:495` | `{t("registration.contactName")} {requiredMark}` — `*` マーク除去対象 |
| `frontend/src/locales/en.json:2331` | `contactHint` キー — フォールバック説明文への変更対象 |
| `frontend/src/locales/ja.json:2331` | `contactHint` キー — フォールバック説明文への変更対象 |
| `backend/tests/test_registration_token_schema.py:140` | `TestRegisterRequestContactRequired` — 任意化テストに置き換え対象 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `billing_display_name` が NULL の場合の挙動 | `row[1] or ""` で空文字列にフォールバック。contacts.display_name NOT NULL なら空文字が入る | ✅ 解消済み |
| 2 | migration 要否 | スキーマ変更なし（バリデーション変更・ロジック変更のみ）。migration 不要 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
