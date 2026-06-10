# design — ADR-126 追補: 公開フォームエラーハンドリング

**仕事名**: adr-126-error-handling  
**日付**: 2026-06-11  
**対象ADR**: ADR-126（追補）  
**担当**: architect

参照: `docs/handoff/adr-126-error-handling/recon.md`

---

## 設計方針（Case イ: 公開エンドポイント内捕捉）

既登録住所（`idx_company_addresses_one_default` 制約違反）に対して 409 + 機械読み取り可能エラーコードを返す。  
グローバルハンドラーは変更しない。理由: `api.ts` 経由でスタッフUI ~16画面に `err.message` として漏れるリスクがあるため。

| 変更箇所 | 変更内容 | 根拠 |
|---------|---------|------|
| `registration_tokens.py` — address INSERT ループ | `try/except SQLAlchemyError` で `idx_company_addresses_one_default` を検知 → 409 + `"already_registered"` | カナリーで UniqueViolationError → 「データベースエラー」露出を検出 |
| `registration_tokens.py` — 全 detail 文字列 | `"無効または期限切れのトークンです"` → `"invalid_token"` / `"リードに紐づく会社が見つかりません"` → `"company_not_found"` | 機械読み取り可能コードに統一（ADR-126 追補） |
| `RegisterPage.tsx` | `rawDetail` 素通しを廃止。`resolveErrorCode(rawDetail, t)` で翻訳済みメッセージを表示 | 内部用語・日本語ハードコードの顧客露出防止 |
| `RegisterAddressPage.tsx` | 同様に `resolveErrorCode` 適用 | 一貫性 |
| `en.json` / `ja.json` | `registration.error.{already_registered,invalid_token,company_not_found,unexpected_error}` 4キー追加 | i18n 必須（ADR-027） |
| グローバルハンドラー (`main.py:529`) | **変更しない** | スタッフUI保護 |

---

## 受け入れ条件と検証方法

| 基準 | 検証方法 |
|------|---------|
| 既登録住所で POST /public/register → 409 + `{"detail": "already_registered"}` | pytest `test_register_duplicate_default_address_returns_409` |
| 409 時にトークンが消費されない（再送可能） | pytest: トークン再利用テスト |
| `resolveErrorCode("already_registered", t)` → i18n 翻訳文字列 | Jest / 目視確認 |
| 未知のエラーコード → `registration.submitError` フォールバック | Jest |
| 既存の `invalid_token` / `company_not_found` 挙動は維持 | pytest 回帰テスト |
| `en.json` と `ja.json` で `registration.error.*` キーが同期 | CI i18n チェック |

---

## 外部・過去事例の参照と我々への応用

- **ADR-126 カナリー（2026-06-11）**: POST /public/register で `UniqueViolationError` が `SQLAlchemyError` グローバルハンドラーに到達し「データベースエラーが発生しました」を顧客に露出。本設計はこれを受けた直接修正。
- **Case イ vs 案ロ（グローバルハンドラー変更）**: `frontend/src/lib/api.ts:90` が `err.message = detail` で ~16 スタッフ画面に生文字列を流すアーキテクチャのため、グローバルハンドラー変更は副作用が大きすぎると判断。公開エンドポイント内捕捉に限定することで影響範囲を最小化。
- **エラーコードパターン（既存踏襲）**: `invalid_token` / `company_not_found` は既に機械読み取り可能コード形式（`verify_registration_token` エンドポイント）。同パターンで統一。
