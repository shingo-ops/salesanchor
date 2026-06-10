# recon — ADR-126 追補: 公開フォームエラーハンドリング

**仕事名**: adr-126-error-handling  
**日付**: 2026-06-11  
**対象ADR**: ADR-126（追補）  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/registration_tokens.py:226` | `for addr in data.addresses:` ループ — try/except 追加対象 |
| `backend/app/routers/registration_tokens.py:259` | `except SQLAlchemyError as e:` — `idx_company_addresses_one_default` 検知で 409 返却 |
| `backend/app/routers/registration_tokens.py:134` | `detail="invalid_token"` — 機械読み取り可能コードに変更済み |
| `backend/app/routers/registration_tokens.py:183` | `detail="invalid_token"` — 機械読み取り可能コードに変更済み |
| `backend/app/routers/registration_tokens.py:201` | `detail="company_not_found"` — 機械読み取り可能コードに変更済み |
| `backend/app/routers/registration_tokens.py:353` | `detail="company_not_found"` — add_address エンドポイント |
| `backend/app/main.py:529` | グローバル `SQLAlchemyError` ハンドラー — **変更しない**（スタッフUI影響回避） |
| `frontend/src/pages/register/RegisterPage.tsx:211` | `resolveErrorCode(rawDetail, t)` 呼び出し箇所 |
| `frontend/src/pages/register/RegisterPage.tsx:63` | `resolveErrorCode` 関数定義（`KNOWN_ERROR_CODES` セット使用） |
| `frontend/src/pages/register/RegisterAddressPage.tsx:225` | 同様の `body?.detail` 素通し — `resolveErrorCode` に切り替え |
| `frontend/src/locales/en.json:2327` | `registration.error.*` 4キー追加箇所 |
| `frontend/src/locales/ja.json:2327` | `registration.error.*` 4キー追加箇所（ja） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | グローバルハンドラー変更でスタッフUIへの影響 | `frontend/src/lib/api.ts:90` `err.message = detail` 経由で ~16画面に漏れる。公開エンドポイント内捕捉のみとし、グローバルハンドラーは不変 | ✅ 解消済み |
| 2 | `IntegrityError` vs `SQLAlchemyError` の捕捉型 | `asyncpg.UniqueViolationError` は `IntegrityError`（`SQLAlchemyError` のサブクラス）経由で `e.orig` にセット。`SQLAlchemyError` で捕捉後 `str(orig)` にインデックス名を検出 | ✅ 解消済み |
| 3 | トークン消費タイミング | `mark_token_used` は `db.commit()` 直前。409 例外は commit 前に発生するためトークンは消費されない | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
