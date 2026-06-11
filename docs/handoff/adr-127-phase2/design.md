# design — ADR-127 Phase 2: 第1層ゲート（新規登録の二重発行防止）

**仕事名**: adr127-phase2-dual-gate
**日付**: 2026-06-11
**対象ADR**: ADR-127
**担当**: generator

参照: `docs/handoff/adr-127-phase2/recon.md`

## 設計方針

ADR-127 §4 に基づき、フロント無効化＋バックエンド拒否の二段ゲートを実装。
`change_billing` / `add_address` は対象外（登録後の操作なので登録済みでも発行可）。

## 変更箇所と設計根拠

| 変更箇所 | 変更内容 | 根拠 |
|---------|---------|------|
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:90-93` | `isAlreadyRegistered = billingAddresses.some(a => a.is_default)` を追加 | ADR-127 §4「billing is_default=true の存在で登録済み判定」 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:112-120` | `disabled={regLinkLoading \|\| isAlreadyRegistered}` + `title` ツールチップ追加 | 誤操作防止（第1層）。将来 change_billing/add_address ボタンを増やす際にこのゲートは register 専用 |
| `frontend/src/locales/en.json:2323` | `registration.alreadyRegisteredGate` キー追加 | i18n 強制（ADR-027）|
| `frontend/src/locales/ja.json:2323` | 同上（ja） | 同上 |
| `backend/app/routers/registration_tokens.py:76-96` | `type=register` かつ billing is_default=true 存在 → 409 + `"already_registered"` | ADR-127 §4「最後の砦」。`change_billing`/`add_address` は通す |

## 受け入れ条件と検証方法

| 基準 | 検証方法 |
|------|---------|
| 登録済み会社では「登録リンクを発行」ボタンが disabled になる | ブラウザ確認（billing is_default=true の会社） |
| 未登録会社ではボタンが有効 | ブラウザ確認（billing なし / is_default=false） |
| API 直叩き（type=register、登録済み）→ 409 + "already_registered" | curl / dev tools 確認 |
| type=add_address / change_billing は登録済みでも通る | API 確認 |
| ESLint `local/no-japanese-literal` を通過 | `cd frontend && npm run lint` |

## 外部・過去事例の参照と我々への応用

- ADR-127 §4: 二段ゲート（フロント無効化＋バックエンド拒否）
- #1918 のエラーコード方式: `detail: "already_registered"` はフロントの `resolveErrorCode()` で既に翻訳済み。409 時は既存エラーメッセージが表示される
