# Recon: password_hash 列廃止

**調査日**: 2026-06-12  
**調査者**: Hikky-dev  
**PO決定**: Shingo 2026-06-12

---

## 書き込み箇所（全4箇所）

| ファイル | 行 | 操作 |
|---|---|---|
| `backend/app/routers/auth.py:80` | `password_hash=hash_password(data.password)` | ユーザー登録時にハッシュを生成して保存 |
| `backend/scripts/setup_review_tenant.py:302` | `password_hash = :hash` | review テナント再付け替え時に UPDATE |
| `backend/scripts/setup_review_tenant.py:314` | `SET password_hash = :hash` | review テナント既存ユーザー更新 |
| `backend/scripts/setup_review_tenant.py:324` | `INSERT INTO ... password_hash ...` | review テナント新規ユーザー作成 |

## 読み取り箇所

**0箇所**。`verify_password` 関数（`backend/app/auth/utils.py:24`）は定義のみで呼び出し元なし。

## 関連定義

| ファイル | 行 | 内容 |
|---|---|---|
| `backend/app/models.py:29` | `password_hash = Column(String(255), nullable=False)` | ORM モデル定義 |
| `backend/app/auth/utils.py:19` | `def hash_password(password: str) -> str` | bcrypt ハッシュ生成関数（呼び出し元: auth.py, setup_review_tenant.py のみ） |
| `backend/app/auth/utils.py:24` | `def verify_password(password: str, hashed: str) -> bool` | bcrypt 検証関数（呼び出し元: **なし**） |
| `backend/app/schemas/auth.py:22` | `password: str = Field(min_length=8, max_length=72)` | UserRegister スキーマの password フィールド（hash_password の引数のみに使用） |
| `backend/tests/test_password_gen.py:52-66` | `class TestHashAndVerify` | hash_password / verify_password のユニットテスト |

## 認証フロー確認

- **ログイン**: `frontend/src/contexts/AuthContext.tsx:37` → `signInWithEmailAndPassword(auth, email, password)` → Firebase Authentication 直通
- **バックエンドでの検証**: `backend/app/auth/dependencies.py:142` → `firebase_auth.verify_id_token(token)` → Firebase ID トークン検証のみ
- **DB の password_hash は認証に一切使用されていない**（確認: 2026-06-12）

## 影響テーブル

- `public.users`（マルチテナント共通テーブル）
- tenant スキーマ側には password_hash 列なし

## 今回の学び（ORM モデル定義経由の暗黙 SELECT）

`models.py:29` に `password_hash = Column(String(255), nullable=False)` が定義されていた。  
SQLAlchemy は ORM モデルを使う全クエリで定義済み列を自動的に SELECT に含める。  
そのため「書き込みコードを全て除去した」だけでは不十分で、  
**モデル定義が残っている限り全認証済みリクエストが `SELECT ... password_hash ...` を発行し続ける**。

今回、migration（DROP COLUMN）を先行実行した状態で旧コード（モデル定義あり）が稼働し  
`UndefinedColumnError: column users.password_hash does not exist` → 全エンドポイント 500 が発生した。

**今後の列削除 recon における必須確認項目**:  
`grep -rn "Column\|field\|column" backend/app/models.py` で ORM モデル定義を確認し、  
書き込み箇所だけでなく **モデル定義の削除も変更リストに含める**こと。
