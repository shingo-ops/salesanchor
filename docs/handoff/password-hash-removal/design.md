# Design: password_hash 列廃止

**PO決定**: 2026-06-12 Shingo  
**実装担当**: Hikky-dev  
**関連 ADR**: ADR-138  
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
| ユーザー登録が正常動作 | `POST /api/v1/auth/register` で `password` フィールド不要・409 or 400 が返る（500なし） |
| ログインが正常動作 | Firebase 経由で ID token 取得 → 認証済みエンドポイント 200 |
| smoke 全グリーン | `/api/v1/leads` `/api/v1/companies` `/api/v1/deals` が 200 |
| DB 列が消える | `information_schema.columns` で `password_hash` が 0 行 |

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `backend/app/models.py` | `password_hash` 列定義を削除 |
| `backend/app/routers/auth.py` | `hash_password` import 除去・User 作成時の `password_hash` 引数除去 |
| `backend/app/auth/utils.py` | `hash_password` / `verify_password` 関数を削除。bcrypt import を削除 |
| `backend/app/schemas/auth.py` | `UserRegister.password` フィールドを削除 |
| `backend/scripts/setup_review_tenant.py` | `password_hash` 引数・DB INSERT/UPDATE の対応列を削除 |
| `backend/tests/test_password_gen.py` | `TestHashAndVerify` クラスを削除 |
| `migrations/20260612_150000_drop_password_hash.sql` | `ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash`（冪等） |

## デプロイ順序（構造による保証）

通常 CI/CD パイプラインでは以下の順で実行される（deploy.yml:321-423 で確認済み）:

1. **blue-green cutover** (`deploy.yml:322`): 新コード（`password_hash` 参照なし）が本番に切替
2. **`run_all_migrations.sh`** (`deploy.yml:423`): DROP COLUMN 実行

DROP 系 migration は新コード稼働後に列が消えるため、**500 エラーウィンドウは発生しない**。  
この保証はパイプラインの構造（ステップ順序）に依存しており、人間の手順書遵守には依存しない。

> ⚠️ 注: 手動での `run_all_migrations.sh` 実行（CI を経由しない場合）は旧コードが稼働中に  
> 列を消す可能性があり危険。migration は必ず CI/CD パイプライン経由で実行すること。

## 本番適用条件（ADR-135 準拠）

- develop マージは CI 緑で可（PO GO 不要）
- **本番適用（main → デプロイ）は Shingo GO 後**（GO: Shingo 2026-06-13）

## Scope 外

- `UserLogin` スキーマ（`password` フィールドあり）: 対応する `/login` エンドポイントが存在しない dead code だが、API 後方互換性のため本件では除去しない
- bcrypt ライブラリの requirements からの削除: 本件では残留（別 PR）

## 外部・過去事例の参照と我々への応用

Firebase Authentication のような外部 IdP に認証を委譲する際、DB 側のパスワードハッシュを  
残したまま運用するケースは「攻撃面の二重管理」として OWASP Credential Storage の  
ベストプラクティスに反する。本件は Firebase 移行完了後に DB 側ハッシュを削除する  
「攻撃面最小化」の標準的アプローチに沿っている。  
Firebase 公式ドキュメントでも「認証情報は Firebase のみで管理し、アプリ DB には保存しない」  
構成が推奨されている。
