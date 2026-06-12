# Design: password_hash 列廃止

**PO決定**: 2026-06-12 Shingo  
**実装担当**: Hikky-dev  
**関連 recon**: `docs/handoff/password-hash-removal/recon.md`

---

## What / Why

| 項目 | 内容 |
|---|---|
| **What** | `public.users.password_hash` 列を完全廃止（コード除去 + DROP COLUMN migration） |
| **Why** | ログインは Firebase Authentication が担当しており password_hash は認証に不使用。不要なパスワードハッシュの保管は攻撃面の無駄な拡大・混乱の元になる |
| **PO判断** | 2026-06-12 Shingo 承認 |

## 変更方針

| 基準 | 検証方法 |
|---|---|
| 書き込みコードが消える | `grep -r password_hash backend/ scripts/` → 0件 |
| ユーザー登録が正常動作 | `POST /register` のテストが PASS |
| ログインが正常動作 | Firebase 経由（既存フローに変更なし） |
| review テナントセットアップが正常動作 | `setup_review_tenant.py` が password_hash なしで完走 |
| 本番相当環境での動作確認 | 本番適用前に Shingo が素振り確認 |

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `backend/app/models.py` | `password_hash` 列定義を削除 |
| `backend/app/routers/auth.py` | `hash_password` import 除去・User 作成時の `password_hash` 引数除去・スキーマ `password` フィールド除去に対応 |
| `backend/app/auth/utils.py` | `hash_password` / `verify_password` 関数を削除。bcrypt import を削除 |
| `backend/app/schemas/auth.py` | `UserRegister.password` フィールドを削除（Firebase が認証担当のため不要） |
| `backend/scripts/setup_review_tenant.py` | `password_hash` 引数・DB INSERT/UPDATE の対応列を削除 |
| `backend/tests/test_password_gen.py` | `TestHashAndVerify` クラスを削除 |
| `migrations/20260612_150000_drop_password_hash.sql` | `ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash`（冪等） |

## デプロイ順序

1. migration が先行実行（`deploy.yml` 経由）→ DB から列が消える
2. 新コード（password_hash 参照なし）がデプロイ
3. 旧コードとの競合ウィンドウは migration 実行〜コンテナ再起動の数秒のみ（ユーザー登録は管理者操作のため許容範囲）

## 本番適用条件（ADR-135 準拠）

- develop マージは CI 緑で可（PO GO 不要）
- **本番適用（main → デプロイ）は Shingo GO 後**
- 素振り確認内容: ①ログイン ②ユーザー作成（`POST /register`）③ `setup_review_tenant.py` 完走

## Scope 外

- `UserLogin` スキーマ（`password` フィールドあり）: 対応する `/login` エンドポイントが存在しない dead code だが、API 後方互換性のため本件では除去しない
- bcrypt ライブラリの requirements からの削除: `setup_review_tenant.py` で `bcrypt` を直接 import している可能性を考慮し本件では残留
