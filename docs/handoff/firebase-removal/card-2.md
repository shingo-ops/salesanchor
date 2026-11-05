# card: 便2 サーバーから Firebase を外す（backend・運用スクリプト・backend の CI の段）

状態: カード発行（Opus、2026-11-05）。PO の承認は 2026-11-04「1」（design.md の状態の行）と 2026-11-05「1」（サーバー側の作業を始める）。設計: [design.md](./design.md) §5-2。根拠: [recon.md](./recon.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret と Variables には触らない。PR は作らない（Opus が作る）。
基準: origin/main `3175aca5eef356a365b2d231cdfe3cc3f3eab116`。下の行番号はすべてこの時点のもの。行がずれていたら、行番号ではなく「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。
画面（`frontend/src`）には触らない。`frontend/api-contract/openapi.json` は手順8 のコマンドで作り直すだけで、手で書かない。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルを §1 で全部挙げた。消すファイルも §1 に挙げ、`find … -delete` で消す。PR は Opus が手元で shingo-cc 名義で作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に変更前と変更後の文を書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED firebase-removal-bin2 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/firebase-removal-bin2` を origin から取り直し、`docs/handoff/firebase-removal/card-2.md` が在ること。
- P2 `git diff --quiet 3175aca5eef356a365b2d231cdfe3cc3f3eab116 HEAD -- backend scripts .github/workflows/test.yml frontend/api-contract` が終了 0（基準から変わっていない）。
- P3 `sed -n '13p' backend/requirements.txt` が `firebase-admin==6.6.0`。
- P4 `sed -n '212p' backend/app/auth/dependencies.py` が `    firebase_closed = self_tokens.auth_provider() == "self"`。
- P5 `sed -n '21p;33p' backend/app/auth/self_tokens.py` が `DEFAULT_AUTH_PROVIDER = "firebase"  # firebase | self` と `_VALID_PROVIDERS = ("firebase", "self")` の 2 行。
- P6 `scripts/setup_single_test_user.py` と `scripts/setup_test_users.py` が在り、`git grep -n "setup_single_test_user\|setup_test_users" -- . ':!docs'` が 0 件（消すファイルを呼ぶ所が無い）。
- P7 `git grep -n "set_tenant_claim" -- backend scripts` が `backend/app/auth/utils.py:13` の 1 件だけ。

## 1. 触るファイル

書き換える（backend/app）:
1. `backend/app/auth/dependencies.py`（2-1）
2. `backend/app/auth/self_tokens.py`（2-2）
3. `backend/app/auth/utils.py`（2-3）
4. `backend/app/services/invite.py`（2-4）
5. `backend/app/routers/auth.py`（2-5）
6. `backend/app/routers/staff.py`（2-6）
7. 注記だけ: `backend/app/main.py`・`backend/app/cache.py`・`backend/app/line_device_admin.py`・`backend/app/middleware/session_guard.py`・`backend/app/routers/leads.py`・`backend/app/routers/line_import_devices.py`・`backend/app/services/review_mail_notifier.py`・`backend/app/schemas/auth.py`（2-7）

書き換える（その他）:
8. `backend/requirements.txt`（2-8）
9. `backend/scripts/CLAUDE.md`（2-9）
10. `scripts/setup_review_tenant.py`（2-10）
11. `scripts/setup_tenant.py`（2-11 注記だけ）
12. `.github/workflows/test.yml`（2-12 段を 1 つ足すだけ）
13. `frontend/api-contract/openapi.json`（手順8 のコマンドで作り直すだけ）
14. 試験: `backend/tests/conftest.py`（2-13）と、2-14 に挙げる 17 ファイル

消す（手順5、`find … -delete`）:
- `scripts/setup_single_test_user.py`
- `scripts/setup_test_users.py`

触らない: 上に挙げた以外のすべて。特に便3 の `.github/workflows/deploy.yml`・`docker-compose*.yml`・`.env.example`・`backend/.dockerignore`・`.gitignore`・`nginx/`・`scripts/detect-external-api-change.js`・`scripts/tests/test-detect-external-api-change.js`、便4 の `backend/app/services/tenant.py`・`backend/tests/conftest.py:512`・`backend/tests/rls_bootstrap.py`・`backend/tests/ops/test_ai_cloud_views.py`・`backend/tests/test_export_inventory_for_sheet.py`・`backend/tests/test_staff_create_users.py:152-232`、`migrations/`、`frontend/src`、`docs/`。上のファイルの中でも、書いていない行は 1 文字も変えない。

## 2. 変更の中身

### 2-1. `backend/app/auth/dependencies.py`

(a) 1 行目 `import asyncio` を消す。

(b) 8 行目 `import firebase_admin`、11 行目 `from firebase_admin import auth as firebase_auth`、12 行目 `from firebase_admin import credentials` を消す。

(c) 40-41 行目の 2 行を消す（後ろの空行は 1 つ残し、`security = HTTPBearer()` と `# CI/CD スモークテスト用…` の間が空行 1 つになるようにする）:
```python
# MFA強制フラグ（本番では必ずTrue）
MFA_REQUIRED = os.getenv("MFA_REQUIRED", "true").lower() == "true"
```

(d) 45 行目
変更前: `# 一致した場合は Firebase 検証・MFA チェックをスキップし SMOKE_SERVICE_EMAIL のユーザーを返す。`
変更後: `# 一致した場合は札の検証をスキップし SMOKE_SERVICE_EMAIL のユーザーを返す。`

(e) 50 行目 `# Firebase Admin SDK の初期化（スレッドセーフ）` から 70 行目 `        _firebase_initialized = True` までを消す（`import threading`・`_firebase_init_lock`・`_firebase_initialized`・`def _init_firebase` の全部）。消した後、`_SMOKE_SERVICE_EMAIL: str = …` の行と `_INVALID_TOKEN_DETAIL = "無効な認証トークンです"` の行の間は空行 2 つにする。

(f) `get_current_user` の docstring（143-153 行目）
変更前:
```python
    """
    Firebase IDトークンを検証し、対応するDBユーザーを返す。
    全認証付きエンドポイントの共通Dependency。

    フロー:
      ① ブラックリスト確認（ログアウト済みトークンを拒否・免除ルートより必ず前）
      ② Redisキャッシュからユーザー情報を取得
         ヒット → IPロック判定をスキップして通過（巻き添え防止）
         ミス   → ③へ
      ③ IPブルートフォース確認（キャッシュミス時のみ）
      ④ Firebase検証 → MFAチェック → DB検索 → 結果をキャッシュ
         Firebase検証失敗時: IPに失敗記録を追加
    """
    _init_firebase()

```
変更後（`_init_firebase()` の行と、その後ろの空行 1 つも消す）:
```python
    """
    自社アクセストークン（ADR-1013）を検証し、対応するDBユーザーを返す。
    全認証付きエンドポイントの共通Dependency。

    フロー:
      ① ブラックリスト確認（ログアウト済みトークンを拒否・免除ルートより必ず前）
      ② Redisキャッシュからユーザー情報を取得（自社トークンのときだけ）
         ヒット → IPロック判定をスキップして通過（巻き添え防止）
         ミス   → ③へ
      ③ IPブルートフォース確認（キャッシュミス時のみ）
      ④ 自社トークンは自社検証へ。自社以外の札は、失敗として数えて 401
    """
```
（`token = cred.credentials` の行が docstring の閉じの直後に来る。）

(g) 162 行目
変更前: `    # Firebase 検証・MFA チェックをスキップして SMOKE_SERVICE_EMAIL のユーザーを返す。`
変更後: `    # 札の検証をスキップして SMOKE_SERVICE_EMAIL のユーザーを返す。`

(h) 174 行目
変更前: `        # 構造ガード（fail-closed）: この経路は Firebase・MFA を通らないため、`
変更後: `        # 構造ガード（fail-closed）: この経路は札の検証を通らないため、`

(i) 210 行目から 293 行目（`    return user` まで。`get_current_tenant` の前の空行は残す）
変更前（210-218 行目と 228 行目と 235-293 行目。間の 219-234 行目は (i) の変更後にそのまま書いてある）:
```python
    # 自社ログイン中（AUTH_PROVIDER=self）は Firebase の札を受け付けない（docs/handoff/block-firebase-token/design.md）。
    # 自社の札でなければ、②の一時記憶を使わず、③の回数確認の後で 401 にする。
    firebase_closed = self_tokens.auth_provider() == "self"
    is_self_issuer = self_tokens.peek_issuer(token) == self_tokens.ISSUER
    ...
    cached = await get_cached_jwt(token) if (is_self_issuer or not firebase_closed) else None
    ...
    # ③ キャッシュミス時のみIPブルートフォース確認（Firebase検証前のゲート）
    ...
    # 自社トークン（iss=salesanchor）は Firebase 検証に回さず、自社検証へ振り分ける
    if is_self_issuer:
        return await _authenticate_self_token(token, client_ip, db)

    # 自社ログイン中は Firebase 検証に進まない（失敗として数え、同じ文言の 401）
    if firebase_closed:
        logger.warning("自社ログイン中に自社以外の札を拒否: ip=%s", client_ip)
        raise await _reject_self_token(client_ip)

    # ④ キャッシュミス: Firebase検証
    try:
        decoded = await asyncio.to_thread(firebase_auth.verify_id_token, token)
    ...（293 行目の `    return user` まで）
```
変更後（210 行目から 293 行目を、次の文で置き換える）:
```python
    # 自社の札でなければ、②の一時記憶を使わず、③の回数確認の後で 401 にする（docs/handoff/firebase-removal/design.md §5-2）。
    is_self_issuer = self_tokens.peek_issuer(token) == self_tokens.ISSUER

    # ② Redisキャッシュからユーザー情報を取得
    # キャッシュヒット: ブラックリスト未登録 & 既存セッション確認済み → IPロックをスキップ
    # 同一IPの他ユーザーによる攻撃でロックされても、正規ユーザーの操作を巻き添え遮断しない。
    cached = await get_cached_jwt(token) if is_self_issuer else None
    if cached:
        email = cached["email"]
        result = await db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if user:
            return user

    # ③ キャッシュミス時のみIPブルートフォース確認（札の検証前のゲート）
    if await check_auth_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="認証試行が上限に達しました。しばらく時間をおいてから再試行してください",
        )

    # ④ 自社トークン（iss=salesanchor）は自社検証へ振り分ける
    if is_self_issuer:
        return await _authenticate_self_token(token, client_ip, db)

    # 自社以外の札は受け付けない（失敗として数え、同じ文言の 401）
    logger.warning("自社以外の札を拒否: ip=%s", client_ip)
    raise await _reject_self_token(client_ip)
```

(j) 741 行目
変更前: `    sid の無いトークン（本便より前の発行・Firebase・smoke）は 403 session_upgrade_required`
変更後: `    sid の無いトークン（本便より前の発行・smoke）は 403 session_upgrade_required`

(k) `cache_jwt_result`（110 行目で使う）・`os`・`secrets`・`select`・`text` の import は残す。手順9 の ruff が「使っていない」と言った import だけを消す。

### 2-2. `backend/app/auth/self_tokens.py`

(a) 21 行目 `DEFAULT_AUTH_PROVIDER = "firebase"  # firebase | self` を消す。
(b) 33 行目 `_VALID_PROVIDERS = ("firebase", "self")` を消す（後ろの `_ALGORITHM = "HS256"` は残す）。
(c) 39-40 行目の関数と、その後ろの空行 2 つを消す:
```python
def auth_provider() -> str:
    return os.getenv("AUTH_PROVIDER", DEFAULT_AUTH_PROVIDER).strip().lower()
```
(d) 69-71 行目
変更前:
```python
def is_issuance_enabled() -> bool:
    """login・refresh・passkey/login を有効にするか。"""
    return auth_provider() == "self" and bool(_secret())
```
変更後:
```python
def is_issuance_enabled() -> bool:
    """login・refresh・passkey/login を有効にするか（秘密があれば有効）。"""
    return bool(_secret())
```
(e) 79-88 行目
変更前:
```python
def validate_settings() -> None:
    """起動時検査。メッセージに秘密の値は入れない。"""
    provider = auth_provider()
    if provider not in _VALID_PROVIDERS:
        raise RuntimeError("AUTH_PROVIDER must be one of: firebase, self")
    if provider == "self" and not _secret():
        raise RuntimeError("AUTH_JWT_SECRET is required when AUTH_PROVIDER=self")
    for name, value in (("AUTH_JWT_SECRET", _secret()), ("AUTH_JWT_SECRET_PREVIOUS", _secret_previous())):
```
変更後:
```python
def validate_settings() -> None:
    """起動時検査。メッセージに秘密の値は入れない。"""
    if os.getenv("ENVIRONMENT", "development") == "production" and not _secret():
        raise RuntimeError("AUTH_JWT_SECRET is required in production")
    for name, value in (("AUTH_JWT_SECRET", _secret()), ("AUTH_JWT_SECRET_PREVIOUS", _secret_previous())):
```
（その下の 2 行 `if value and len(value) < MIN_SECRET_LENGTH:` と `raise RuntimeError(...)` は変えない。）

### 2-3. `backend/app/auth/utils.py`

5 行目 `from firebase_admin import auth as firebase_auth` と、その後ろの空行 1 つを消す。13-15 行目の `def set_tenant_claim` の 3 行と、その後ろの空行 2 つを消す。`logger` と `generate_password` は残す。

### 2-4. `backend/app/services/invite.py`

19-21 行目の関数と、その後ろの空行 2 つを消す:
```python
def invite_enabled() -> bool:
    """初回設定の鍵とメールを作るか。AUTH_PROVIDER=self のときだけ（firebase の間は作らない）。"""
    return self_tokens.auth_provider() == "self"
```
`from app.auth import self_tokens` は残す（`_hash_token`・`rp_origin` で使う）。

### 2-5. `backend/app/routers/auth.py`

(a) 6 行目 `import os` を消す（使う所は 601 行目だけで、(f) で消える）。
(b) 55 行目
変更前: `from app.services.invite import create_invite_token, invite_enabled, invite_url`
変更後: `from app.services.invite import create_invite_token, invite_url`
(c) 79-80 行目
変更前:
```
      ⑤ AUTH_PROVIDER=self のとき、初回設定の鍵（purpose=invite・72時間）を作り、
         commit の後に初回設定メールを送る（firebase の間は鍵もメールも作らない）
```
変更後:
```
      ⑤ 初回設定の鍵（purpose=invite・72時間）を作り、
         commit の後に初回設定メールを送る
```
(d) 165 行目
変更前: `    invite_raw = await create_invite_token(db, user.id) if invite_enabled() else None`
変更後: `    invite_raw = await create_invite_token(db, user.id)`
（168 行目の `if invite_raw is not None:` は残す。）
(e) 186 行目 `    Firebase IDトークンの残存有効期限（最大1時間）をTTLとする。` を
`    アクセストークンの残存有効期限より長い 1 時間を TTL とする。` に変える。
(f) 597-602 行目の関数 `_password_reset_allowed` の全部と、その後ろの空行 2 つを消す。
(g) 617 行目（docstring）
変更前: `    """再設定メールの申請。存在・停止・許可外の区別を応答に出さない（常に 200）。"""`
変更後: `    """再設定メールの申請。存在・停止の区別を応答に出さない（常に 200）。"""`
(h) 624 行目
変更前: `    if row is not None and row.is_active and _password_reset_allowed(email):`
変更後: `    if row is not None and row.is_active:`
(i) 見出しの注記 3 か所:
- 204 行目 `# ── 自社ログイン（ADR-1013 便2。AUTH_PROVIDER=self のときだけ有効） ────────────` → `# ── 自社ログイン（ADR-1013 便2） ────────────`
- 574 行目 `# ── パスワード再設定（ADR-1013 便3。AUTH_PROVIDER に関係なく動く） ─────────────` → `# ── パスワード再設定（ADR-1013 便3） ─────────────`
- 712 行目 `# ── パスワード変更（ADR-1013 便4a。AUTH_PROVIDER に関係なく動く） ─────────────` → `# ── パスワード変更（ADR-1013 便4a） ─────────────`

### 2-6. `backend/app/routers/staff.py`

(a) 44 行目
変更前: `from app.services.invite import create_invite_token, invite_enabled, invite_url`
変更後: `from app.services.invite import create_invite_token, invite_url`
(b) 642-643 行目
変更前:
```python
        # 新しく利用者ができたときだけ、AUTH_PROVIDER=self なら初回設定の鍵を同じトランザクションで作る
        invite_raw = await create_invite_token(db, user_id) if user_created and invite_enabled() else None
```
変更後:
```python
        # 新しく利用者ができたときだけ、初回設定の鍵を同じトランザクションで作る
        invite_raw = await create_invite_token(db, user_id) if user_created else None
```
(c) 264-272 行目（`    実装メモ:` から `      経路を再導入する（その際は `ORDER BY` も維持）。` まで）
変更後:
```
    実装メモ:
      staff は users.id と staff.user_id の一致だけで引く（ADR-1008）。
      決定性は `ORDER BY` で確保する。
```

### 2-7. 注記だけの所（コードは変えない）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `backend/app/main.py:183` | `    # ADR-1013: 自社ログインの設定検査（既定 firebase・秘密なしなら何も起きない）` | `    # ADR-1013: 自社ログインの設定検査（本番で秘密が無ければ起動を止める）` |
| `backend/app/cache.py:306` | `# 認証失敗: IP単位、10回で15分ロック（Firebase token validation failure）` | `# 認証失敗: IP単位、10回で15分ロック（token validation failure）` |
| `backend/app/line_device_admin.py:4` | `an API key, password or Firebase token. No arbitrary SQL/command execution.` | `an API key, password or login token. No arbitrary SQL/command execution.` |
| `backend/app/middleware/session_guard.py:37` | `# セッション追跡の有効期間: 1時間（Firebase JWTの最大有効期限と合わせる）` | `# セッション追跡の有効期間: 1時間` |
| `backend/app/routers/leads.py:1241` | `    # firebase_uid 列追加は別 follow-up（F9-S4 拡張版）。現状は user_id (DB id) のみ。` | `    # 記録するのは user_id (DB id) だけ。` |
| `backend/app/routers/line_import_devices.py:1` | `"""Initial approval uses Firebase; device credentials can only import Android LINE."""` | `"""Initial approval uses an app login; device credentials can only import Android LINE."""` |
| `backend/app/services/review_mail_notifier.py:14` | `  - メール本文・添付・Firebase oobCode は Discord に投稿しない。` | `  - メール本文・添付・再設定リンクのコードは Discord に投稿しない。` |
| `backend/app/schemas/auth.py:19` | `    上流のFirebase Auth側で担保される。パスワードは受け取らない` | `    初回設定メールが届くことで担保される。パスワードは受け取らない` |

`backend/app/main.py:184` の `self_tokens.validate_settings()` の呼び出しは残す。

### 2-8. `backend/requirements.txt`

13 行目 `firebase-admin==6.6.0` を消す。ほかの行は変えない。

### 2-9. `backend/scripts/CLAUDE.md`

9 行目
変更前: `実行するたびに新パスワードが生成され Firebase + DB 両方を更新する。`
変更後: `ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 を付けて実行したとき（または利用者を新しく作ったとき）に新パスワードが生成され、DB（public.users のパスワード）を更新する。`

### 2-10. `scripts/setup_review_tenant.py`（終わりの条件: このファイルの `firebase` が大小無視で 0 件）

(a) docstring
- 18 行目 `  - firebase-credentials.json がコンテナ内 /app に存在すること` を消す。
- 24 行目 `  - 既存 Firebase ユーザーがいる場合、パスワードは変更しない（デフォルト）。` → `  - 既存ユーザーにパスワードがある場合、パスワードは変更しない（デフォルト）。`
- 37 行目 `              ADR-138 対応（password_hash 廃止 → Firebase 専一認証）` → `              ADR-138 対応（password_hash 廃止）`
- 39 行目 `              ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 で明示許可した場合のみ変更可` の次の行に 1 行足す:
  `  2026-11-05: ADR-1013 便6 対応（自社ログインのパスワード password_argon2_hash を書く）`

(b) 55-56 行目の 2 行を消す:
```python
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials, exceptions as fb_exceptions
```

(c) 92 行目 `# ---…` から 131 行目（`_firebase_update_password` の最後の `    )`）までと、その後ろの空行を消し、次で置き換える（`# DB: テナント` の見出しの前は空行 2 つ）:
```python
# ---------------------------------------------------------------------------
# パスワード
# ---------------------------------------------------------------------------

def _should_write_password(has_password: bool, reset: bool) -> bool:
    """パスワードを書くか。リセット指定のときと、まだパスワードが無いときだけ書く。"""
    return reset or not has_password


async def _has_password(engine) -> bool:
    """review 用の利用者がいて、自社ログインのパスワードを持っているか。"""
    async with engine.begin() as conn:
        # ADR-1018 段階③便C: public.users の読み書きは運営文脈で行う
        await conn.execute(text("SET app.is_operator = 'true'"))
        row = (await conn.execute(
            text("SELECT password_argon2_hash FROM public.users WHERE email = :email"),
            {"email": REVIEW_EMAIL},
        )).first()
    return row is not None and row[0] is not None
```

(d) `_create_staff_record`（223-286 行目）
- 231 行目 `    firebase_uid: str,` を消す。
- 256 行目 `                primary_email, role_id, status, firebase_uid` → `                primary_email, role_id, status`
- 261 行目 `                :email, :rid, 'active', :fbuid` → `                :email, :rid, 'active'`
- 273 行目 `            "fbuid": firebase_uid,` を消す。

(e) `_setup_user`（289-372 行目）
- 289 行目 `async def _setup_user(engine, tenant_id: int, firebase_uid: str) -> int:` → `async def _setup_user(engine, tenant_id: int, password_hash: str | None) -> int:`
- 296 行目 `    ADR-138: 認証は Firebase 専一。password_hash は保存しない。` → `    password_hash を渡したときだけ、自社ログインのパスワード（password_argon2_hash）を書き、古いセッションを切る。`
- 350-352 行目の 3 行（`# Firebase カスタムクレームを新テナントに更新`・`firebase_auth.set_custom_user_claims(...)`・`logger.info("  Firebase: tenant_id=%d クレーム設定完了", tenant_id)`）を、次の文で置き換える（字下げは 8 つ）:
```python
        if password_hash is not None:
            # 自社ログインのパスワード（ADR-1013）。password_changed_at を進めると更新用トークンが切れる
            await conn.execute(
                text("""
                    UPDATE public.users
                    SET password_argon2_hash = :h,
                        password_changed_at = :at,
                        failed_login_count = 0,
                        locked_until = NULL
                    WHERE id = :uid
                """),
                {"h": password_hash, "at": datetime.now(timezone.utc).replace(microsecond=0), "uid": user_id},
            )
            logger.info("  public.users: パスワードを設定 (id=%d)", user_id)
```
- 369 行目 `            firebase_uid=firebase_uid,` を消す。

(f) `main()`
- 438 行目 `    from app.auth.utils import generate_password` の次の行に足す: `    from app.auth.passwords import hash_password`
- 452-461 行目
変更前:
```python
        if reset_password:
            logger.warning(
                "ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 検出:"
                " Firebase パスワードをリセットします (email=%s)", REVIEW_EMAIL
            )
        else:
            logger.info(
                "通常モード: 既存 Firebase ユーザーのパスワードは変更しません。"
                " パスワードリセットが必要な場合は ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 を付けて再実行してください。"
            )
```
変更後:
```python
        if reset_password:
            logger.warning(
                "ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 検出:"
                " パスワードをリセットします (email=%s)", REVIEW_EMAIL
            )
        else:
            logger.info(
                "通常モード: 既存ユーザーのパスワードは変更しません。"
                " パスワードリセットが必要な場合は ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 を付けて再実行してください。"
            )
```
- 469-491 行目（`        # 3. Firebase ユーザー準備` から `        await _setup_user(engine, tenant_id, firebase_uid)` まで）
変更後:
```python
        # 3. パスワード準備（新しく作るとき・パスワードが無いとき・リセット指定のときだけ）
        new_password: str | None = None
        password_hash: str | None = None
        has_password = await _has_password(engine)
        if _should_write_password(has_password, reset_password):
            new_password = generate_password()
            password_hash = hash_password(new_password)
        else:
            logger.info("既存ユーザーのため password update skipped (email=%s)", REVIEW_EMAIL)

        # 4. DB ユーザー登録・テナント付け替え・パスワード設定（冪等）
        await _setup_user(engine, tenant_id, password_hash)
```
- 493 行目以降（`# 5. Demo データシード` から最後まで）は変えない。

### 2-11. `scripts/setup_tenant.py`（注記だけ）

- 29 行目 `  - Firebase ユーザーの作成は別途実施すること（このスクリプトは DB 操作のみ）` → `  - ログインできる利用者は、管理画面で担当者を追加すると初回設定メールで作られる（このスクリプトは DB 操作のみ）`
- 471 行目 `        logger.info("  1. Firebase ユーザーを作成する（管理画面または Firebase Console 経由）")` → `        logger.info("  1. 管理画面で担当者を追加する（初回設定メールが届く）")`

### 2-12. `.github/workflows/test.yml`

job `pytest-run` の段 `Install dependencies`（164-166 行目）の直後、段 `Generate Fernet key for tests` の前に、次の段を足す（字下げは今の段と同じ 6 つ。前後に空行 1 つ）:
```yaml
      - name: Firebase removal check (K2 K4)
        working-directory: backend
        run: |
          if python -c "import firebase_admin" 2>/dev/null; then
            echo "K2 NG: firebase_admin is importable"
            exit 1
          fi
          echo "K2 OK: firebase_admin is not installed"
          python -c "import google.oauth2.credentials, google.oauth2.service_account, google.auth.transport.requests, googleapiclient.discovery, googleapiclient.http, googleapiclient.errors, google_auth_oauthlib.flow, gspread, google.genai, google.generativeai"
          echo "K4 OK: google libraries import"
```

### 2-13. `backend/tests/conftest.py`

1707 行目 `        await conn.execute(text("DELETE FROM audit_logs"))` の直後に 1 行足す:
```python
        await conn.execute(text("DELETE FROM password_reset_tokens"))
```
理由: これまで `AUTH_PROVIDER=self` の試験だけが初回設定の鍵を作っていた。便2 の後は担当者の追加・register のたびに鍵ができ、表全体の件数を数える試験（`backend/tests/test_password_reset.py:210`・`:311`・`:328`）が他の試験の残りで赤になるのを防ぐ。512 行目の `firebase_uid` は便4 なので触らない。

### 2-14. 試験 17 ファイル

共通: 次の 2 種類の行は、下に挙げたファイルにあれば消す。
- `monkeypatch.setenv("AUTH_PROVIDER", "self")` の行
- `patch("app.auth.dependencies._init_firebase")` の部分（`with` の並びの中なら、その 1 項目と後ろの `, \` または `,` を消す）

(1) `backend/tests/test_self_auth.py`
- 38 行目 `    monkeypatch.setenv("AUTH_PROVIDER", "self")` を消す。
- 184-188 行目
変更前:
```python
async def test_login_and_refresh_404_when_provider_firebase(http, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
```
変更後（下の 2 つの assert はそのまま）:
```python
async def test_login_and_refresh_404_when_no_secret(http, monkeypatch):
    monkeypatch.delenv("AUTH_JWT_SECRET")
```
- 352 行目 `    with patch("app.auth.dependencies._init_firebase"), \` → `    with patch("app.auth.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)), \` とし、その次の行（今の 353 行目 `         patch("app.auth.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)), \`）を消す。
- 463-472 行目
変更前:
```python
def test_validate_settings_accepts_default_firebase_without_secret(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
    monkeypatch.delenv("AUTH_JWT_SECRET")
    assert self_tokens.validate_settings() is None


def test_validate_settings_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "okta")
    with pytest.raises(RuntimeError):
        self_tokens.validate_settings()
```
変更後:
```python
def test_validate_settings_accepts_no_secret_outside_production(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("AUTH_JWT_SECRET")
    assert self_tokens.validate_settings() is None
```
- 475-478 行目
変更前:
```python
def test_validate_settings_rejects_self_without_secret(monkeypatch):
    monkeypatch.delenv("AUTH_JWT_SECRET")
```
変更後（下の `with pytest.raises(RuntimeError):` の 2 行はそのまま）:
```python
def test_validate_settings_rejects_production_without_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("AUTH_JWT_SECRET")
```
- 604-610 行目
変更前:
```python
async def test_password_change_firebase_revokes_refresh_but_issues_nothing(
    http, db_session, password_hash, as_user, monkeypatch
):
    await _insert_user(db_session, hash_value=password_hash)
    cookie = await _login_cookie(http)
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
```
変更後（下は変えない）:
```python
async def test_password_change_without_secret_revokes_refresh_but_issues_nothing(
    http, db_session, password_hash, as_user, monkeypatch
):
    await _insert_user(db_session, hash_value=password_hash)
    cookie = await _login_cookie(http)
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
```
- 628-717 行目（9b の節の全部。ファイルの最後まで）を次で置き換える:
```python
# ── 9b. 自社以外の札は受け付けない（docs/handoff/firebase-removal/design.md §5-2） ──

FOREIGN_TOKEN = "foreign-token-not-salesanchor"


async def _current_user_with(db, token, *, cached=None, rate_limited=False):
    """get_current_user を呼び、(利用者, 例外, 一時記憶の偽物, 失敗記録の偽物) を返す。"""
    from app.auth.dependencies import get_current_user

    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    get_cached = AsyncMock(return_value=cached)
    record = AsyncMock()
    with patch("app.auth.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)), \
         patch("app.auth.dependencies.get_cached_jwt", new=get_cached), \
         patch("app.auth.dependencies.check_auth_rate_limit", new=AsyncMock(return_value=rate_limited)), \
         patch("app.auth.dependencies.record_auth_failure", new=record), \
         patch("app.auth.dependencies.cache_jwt_result", new=AsyncMock()):
        try:
            user = await get_current_user(_request(), cred, db)
        except HTTPException as exc:
            return None, exc, get_cached, record
    return user, None, get_cached, record


async def test_rejects_foreign_token(db_session, password_hash):
    """T1・K1"""
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, _, record = await _current_user_with(db_session, FOREIGN_TOKEN)

    assert user is None and exc.status_code == 401
    assert exc.detail == "無効な認証トークンです"
    record.assert_awaited_once()


async def test_ignores_cached_foreign_token(db_session, password_hash):
    """T2・K2"""
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, get_cached, _ = await _current_user_with(
        db_session, FOREIGN_TOKEN, cached={"email": EMAIL}
    )

    assert user is None and exc.status_code == 401
    get_cached.assert_not_awaited()


async def test_rate_limit_still_429_for_foreign_token(db_session):
    """T3・K5"""
    user, exc, _, _ = await _current_user_with(db_session, FOREIGN_TOKEN, rate_limited=True)

    assert user is None and exc.status_code == 429


async def test_still_accepts_self_token_from_cache(db_session, password_hash):
    """T4・K3"""
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, get_cached, _ = await _current_user_with(db_session, _token(), cached={"email": EMAIL})

    assert exc is None and user.id == USER_ID
    get_cached.assert_awaited_once()


async def test_still_accepts_self_token_without_cache(db_session, password_hash):
    """T5・K3"""
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, _, _ = await _current_user_with(db_session, _token())

    assert exc is None and user.id == USER_ID
```
- この置き換えの後、`MagicMock` を使う所が無くなったら、ruff（手順9）の言うとおりに import から外す。

(2) `backend/tests/test_passkeys.py`
- 51 行目 `    monkeypatch.setenv("AUTH_PROVIDER", "self")` を消す。
- 355-358 行目
変更前:
```python
# ── T6 firebase では 404 ──────────────────────────────────────

async def test_login_routes_are_404_when_provider_is_firebase(http, redis, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
```
変更後（下は変えない）:
```python
# ── T6 秘密が無ければ 404 ──────────────────────────────────────

async def test_login_routes_are_404_without_secret(http, redis, monkeypatch):
    monkeypatch.delenv("AUTH_JWT_SECRET")
```

(3) `AUTH_PROVIDER=self` の行を消すだけ: `backend/tests/test_passkey_login_enroll.py:44`・`backend/tests/test_new_device_approval.py:79`・`backend/tests/test_users_rls.py:358`・`backend/tests/test_register_invite.py:32`。

(4) `_init_firebase` の patch を消すだけ: `backend/tests/test_new_device_approval.py:115`（`         patch("app.auth.dependencies._init_firebase"), \` の行を消す。前の行が `with` を含むなら、次の行の頭に `with ` を移して文を正しく保つ）。

(5) `backend/tests/test_viewer_isolation.py`
- 5 行目 `get_current_user は override しない。patch するのは _init_firebase・is_token_blacklisted・check_auth_rate_limit の3つだけ。` → `get_current_user は override しない。patch するのは is_token_blacklisted・check_auth_rate_limit の2つだけ。`
- 100 行目 `        patch("app.auth.dependencies._init_firebase"),` を消す。
- 116-117 行目 `    p1, p2, p3 = _patches()` と `    with p1, p2, p3:` → `    p1, p2 = _patches()` と `    with p1, p2:`
- 151 行目 `    p1, p2, p3 = _patches()` → `    p1, p2 = _patches()`。その下の `with (` の中の `        p3,` の 1 行を消す。
- ファイルの中で `p3` がほかに残っていないことを `grep -n "p3" backend/tests/test_viewer_isolation.py` で確かめる（0 件）。

(6) `backend/tests/test_event_loop_nonblocking.py`
- 175-206 行目の関数 `test_get_current_user_verify_id_token_does_not_block_loop` の全部と、その前の空行 2 つを消す（ファイルの最後の関数。消した後のファイルは改行 1 つで終わる）。
- 使わなくなった import は ruff（手順9）の言うとおりに外す。

(7) `backend/tests/test_smoke_auth_least_privilege.py`
- 3 行目 `DB・Redis・Firebase には接続しない（すべてモック）。` → `DB・Redis には接続しない（すべてモック）。`
- 30 行目 `    with patch("app.auth.dependencies._init_firebase"), patch(` から 45 行目 `    ):` までを次で置き換える:
```python
    with patch("app.auth.dependencies._get_client_ip", return_value="127.0.0.1"), patch(
        "app.auth.dependencies._SMOKE_SERVICE_TOKEN", token
    ), patch(
        "app.auth.dependencies._SMOKE_SERVICE_EMAIL", email
    ), patch(
        "app.auth.dependencies.is_token_blacklisted", AsyncMock(return_value=False)
    ), patch(
        "app.auth.dependencies.get_cached_jwt", AsyncMock(return_value=None)
    ), patch(
        "app.auth.dependencies.check_auth_rate_limit", AsyncMock(return_value=False)
    ), patch(
        "app.auth.dependencies.record_auth_failure", AsyncMock()
    ):
```
- 74-75 行目
変更前:
```python
async def test_smoke_disabled_when_env_empty_falls_through_to_firebase():
    # token 空 → 不活性。Firebase 検証に入り（失敗して）401。
```
変更後:
```python
async def test_smoke_disabled_when_env_empty_falls_through_to_reject():
    # token 空 → 不活性。自社以外の札として断られて 401。
```
- 82 行目 `async def test_smoke_mismatched_token_falls_through_to_firebase():` → `async def test_smoke_mismatched_token_falls_through_to_reject():`
- 89-91 行目
変更前:
```python
async def test_smoke_token_passes_when_auth_provider_self(monkeypatch):
    """T7・K6: 自社ログイン中でも smoke の札は通る（docs/handoff/block-firebase-token/design.md）"""
    monkeypatch.setenv("AUTH_PROVIDER", "self")
```
変更後（下は変えない）:
```python
async def test_smoke_token_passes_after_foreign_tokens_are_rejected():
    """T7・K6: 自社以外の札を断るようにした後も smoke の札は通る"""
```

(8) `backend/tests/test_client_ip.py`
- 57-71 行目（`    with patch("app.auth.dependencies._init_firebase"), patch(` から、`                statuses.append(resp.status_code)` まで）
変更後（`with` を外して字下げを 1 段浅くし、札の文を変える）:
```python
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(11):
            resp = await client.get(
                "/api/protected",
                headers={
                    "Authorization": "Bearer invalid-token",
                    "X-Real-IP": "10.3.0.1",
                    "X-Forwarded-For": f"6.6.{i}.{i + 1}",
                },
            )
            statuses.append(resp.status_code)
```
- 使わなくなった `patch` の import は ruff（手順9）の言うとおりに外す。

(9) `backend/tests/test_security_hardening.py`
- 185 行目 `        """無効なFirebaseトークンで record_auth_failure が呼ばれる。"""` → `        """自社以外の無効な札で record_auth_failure が呼ばれる。"""`
- 191-192 行目
変更前:
```python
             patch("app.auth.dependencies.record_auth_failure", new_callable=AsyncMock) as mock_record, \
             patch("firebase_admin.auth.verify_id_token", side_effect=Exception("invalid token")):
```
変更後:
```python
             patch("app.auth.dependencies.record_auth_failure", new_callable=AsyncMock) as mock_record:
```
- 201 行目 `                    headers={"Authorization": "Bearer invalid-firebase-token"},` → `                    headers={"Authorization": "Bearer invalid-token"},`
- 211 行目 `        前提: 同一IPで他ユーザーが AUTH_FAIL_MAX 回 Firebase検証失敗 → IPロック成立。` → `        前提: 同一IPで他ユーザーが AUTH_FAIL_MAX 回 札の検証に失敗 → IPロック成立。`

(10) `backend/tests/test_line_import_devices.py`
- 36 行目 `    for bad in ['firebase-token', 'sali1_short', TOKEN+'\n']:` → `    for bad in ['not-a-device-key', 'sali1_short', TOKEN+'\n']:`
- 52 行目 `    # Fake Firebase token is rejected before the approval service can be called.` → `    # A device key is not an app login token; it is rejected before the approval service can be called.`
- 53 行目の長い 1 行から、`patch('app.auth.dependencies._init_firebase'), ` と `patch('app.auth.dependencies.firebase_auth.verify_id_token', side_effect=ValueError('invalid')), ` の 2 項目を消す（ほかの項目と `as approve:` は変えない）。
- 59 行目 `def test_approval_requires_existing_firebase_admin(client):` → `def test_approval_requires_existing_super_admin(client):`

(11) `backend/tests/test_password_reset.py`
- 55 行目 `    monkeypatch.setenv("AUTH_PROVIDER", "firebase")` と 59 行目 `    monkeypatch.setenv("AUTH_PASSWORD_RESET_ALLOWLIST", EMAIL)` を消す。
- 170 行目 `async def test_request_allowlisted_active_user_sends(http, db_session, sender):` → `async def test_request_active_user_sends(http, db_session, sender):`
- 187-201 行目の 2 つの試験（`test_request_empty_allowlist_firebase_sends_nothing`・`test_request_unset_allowlist_sends_nothing`）を、後ろの空行 2 つと一緒に消す。
- 206 行目 `    ok = await _request(http)  # 許可リストに載っているが is_active=false` → `    ok = await _request(http)  # 利用者はいるが is_active=false`
- 214-221 行目の試験 `test_request_self_provider_sends_without_allowlist` を、後ろの空行 2 つと一緒に消す（170 行目の試験と同じことを確かめているため）。
- 337-339 行目
変更前:
```python
# ── 本番設定のまま（firebase・秘密なし）でも 404 にならない ─────────

async def test_endpoints_not_404_with_firebase_and_no_secret(http, db_session, sender):
```
変更後（下は変えない）:
```python
# ── 秘密が無くても 404 にならない ─────────

async def test_endpoints_not_404_without_secret(http, db_session, sender):
```

(12) `backend/tests/test_register_invite.py`
- 3-4 行目
変更前:
```
self のとき: purpose=invite の鍵が 1 行・送信関数の呼び出し 1 回。
firebase のとき: 鍵 0 行・送信 0 回。
```
変更後:
```
purpose=invite の鍵が 1 行・送信関数の呼び出し 1 回。
```
- 32 行目 `    monkeypatch.setenv("AUTH_PROVIDER", "self")` を消す。
- 37-40 行目の fixture `provider_firebase` の全部（`@pytest.fixture` の行から `    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)` まで）と、後ろの空行 2 つを消す。
- 136-143 行目の試験 `test_register_firebase_creates_user_only` を、前の空行 2 つと一緒に消す。

(13) `backend/tests/test_staff_create_users.py`（152-232 行目は便4 なので触らない）
- 236 行目 `# ── 初回設定メール（ADR-1013 便4a。新しく利用者ができたときだけ・AUTH_PROVIDER=self のときだけ） ──` → `# ── 初回設定メール（ADR-1013 便4a。新しく利用者ができたときだけ） ──`
- 263 行目と 291 行目の `    monkeypatch.setenv("AUTH_PROVIDER", "self")` を消す。
- 277-286 行目の試験 `test_new_user_gets_no_invite_when_firebase`（`@pytest.mark.asyncio` の行から `    assert invite_sender.call_count == 0` まで）を、後ろの空行 2 つと一緒に消す。

(14) `backend/tests/test_review_mail_notifier.py`
- 87 行目 `    def test_no_firebase_reset_link(self) -> None:` → `    def test_no_reset_link(self) -> None:`
- 88 行目 `        """Firebase パスワード再設定リンクは含まれてはならない。"""` → `        """パスワード再設定リンクは含まれてはならない。"""`
- 101・329・369 行目の `noreply@firebase.com` を `noreply@auth.example.com` に変える（3 か所）。
- 324 行目 `        Firebase パスワード再設定メールを受信した場合でも、IMAP から取得するのは` → `        パスワード再設定メールを受信した場合でも、IMAP から取得するのは`
- 366 行目 `        # Firebase 再設定リンク全体は含まない` → `        # 再設定リンク全体は含まない`

(15) `backend/tests/test_setup_review_tenant.py`
- 1-7 行目
変更後:
```python
"""setup_review_tenant.py の単体テスト。

DB をモックして以下を検証:
- パスワードを書くのは、リセット指定のときと、まだパスワードが無いときだけ
- ALLOW_REVIEW_TENANT_PASSWORD_RESET の読み取り
- Firebase の部品を使っていない
- customers テーブル参照が存在しない
"""
```
- 26-32 行目（`    # firebase_admin を先にモック` から `    sys.modules.setdefault("firebase_admin.exceptions", MagicMock())` まで）を消す。
- 44-83 行目の 2 つの試験（`test_existing_user_no_reset_flag_skips_password_update`・`test_existing_user_with_reset_flag_calls_password_update`）を、次で置き換える:
```python
    def test_existing_password_without_reset_flag_is_kept(self):
        """既存のパスワードがあり、リセット指定なし → 書かない。"""
        mod = _load_module()
        assert mod._should_write_password(has_password=True, reset=False) is False

    def test_existing_password_with_reset_flag_is_written(self):
        """既存のパスワードがあり、リセット指定あり → 書く。"""
        mod = _load_module()
        assert mod._should_write_password(has_password=True, reset=True) is True

    def test_no_password_is_written_without_flag(self):
        """パスワードが無い（新しく作る） → 指定なしでも書く。"""
        mod = _load_module()
        assert mod._should_write_password(has_password=False, reset=False) is True

    def test_no_password_with_reset_flag_is_written(self):
        """パスワードが無く、リセット指定あり → 書く。"""
        mod = _load_module()
        assert mod._should_write_password(has_password=False, reset=True) is True

    def test_script_has_no_firebase(self):
        """スクリプトに Firebase の文字が無い（便2 の終わりの条件）。"""
        assert "firebase" not in _SCRIPT_PATH.read_text(encoding="utf-8").lower()
```
- 85 行目以降の試験は変えない。使わなくなった `MagicMock`・`patch`・`sys` の import は ruff（手順9）の言うとおりに外す。

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/firebase-removal-bin2 && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P7 を流し、結果をそのまま報告に貼る
    cd ~/sa && git diff --quiet 3175aca5eef356a365b2d231cdfe3cc3f3eab116 HEAD -- backend scripts .github/workflows/test.yml frontend/api-contract; echo "P2 exit=$?"
    cd ~/sa && sed -n '13p' backend/requirements.txt | tail -1
    cd ~/sa && sed -n '212p' backend/app/auth/dependencies.py | tail -1
    cd ~/sa && sed -n '21p;33p' backend/app/auth/self_tokens.py | tail -2
    cd ~/sa && ls scripts/setup_single_test_user.py scripts/setup_test_users.py | tail -2 && git grep -n "setup_single_test_user\|setup_test_users" -- . ':!docs' | wc -l
    cd ~/sa && git grep -n "set_tenant_claim" -- backend scripts | tail -5

手順3 部品を入れる（firebase-admin を入れない状態で入れ直す）
    cd ~/sa/backend && python -m pip install -q uv && uv pip install --system -r requirements.txt -r requirements-dev.txt 2>&1 | tail -3

手順4 §2 の変更をする（2-1 から 2-14 の順。ファイルごとに変更前の文で場所を探す）

手順5 2 つのファイルを消す
    cd ~/sa && find scripts -maxdepth 1 -type f \( -name setup_single_test_user.py -o -name setup_test_users.py \) -delete && ls scripts/setup_single_test_user.py scripts/setup_test_users.py 2>&1 | tail -2

手順6 firebase-admin を外した部品で入れ直す（手順3 の環境に firebase-admin が残っていれば外す）
    cd ~/sa/backend && uv pip uninstall --system firebase-admin 2>&1 | tail -2; uv pip install --system -r requirements.txt -r requirements-dev.txt 2>&1 | tail -3

手順7 K2・K4 の確かめ（2-12 と同じ中身）
    cd ~/sa/backend && python -c "import firebase_admin" 2>&1 | tail -1
    cd ~/sa/backend && python -c "import google.oauth2.credentials, google.oauth2.service_account, google.auth.transport.requests, googleapiclient.discovery, googleapiclient.http, googleapiclient.errors, google_auth_oauthlib.flow, gspread, google.genai, google.generativeai" && echo "K4 OK" | tail -1

手順8 API の説明文を作り直す
    cd ~/sa/backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -3 && cd ~/sa && git diff --stat -- frontend/api-contract/openapi.json | tail -2

手順9 ruff（使っていない import はここで言われた所だけを外し、もう一度流して 0 件にする）
    cd ~/sa/backend && ruff check . 2>&1 | tail -30

手順10 触った試験を流す
    cd ~/sa/backend && python -m pytest -q tests/test_self_auth.py tests/test_passkeys.py tests/test_passkey_login_enroll.py tests/test_new_device_approval.py tests/test_users_rls.py tests/test_register_invite.py tests/test_viewer_isolation.py tests/test_event_loop_nonblocking.py tests/test_smoke_auth_least_privilege.py tests/test_client_ip.py tests/test_security_hardening.py tests/test_line_import_devices.py tests/test_password_reset.py tests/test_staff_create_users.py tests/test_review_mail_notifier.py tests/test_setup_review_tenant.py tests/test_password_gen.py 2>&1 | tail -15

手順11 全部の試験を流す（SQLite）
    cd ~/sa/backend && python -m pytest -q -x -p no:cacheprovider 2>&1 | tail -15

手順12 残りの文字の確かめ
    cd ~/sa && git grep -n -i firebase -- backend/app | tail -5
    cd ~/sa && git grep -n "AUTH_PROVIDER\|AUTH_PASSWORD_RESET_ALLOWLIST\|_init_firebase\|firebase_auth\|firebase_admin\|invite_enabled\|auth_provider()" -- backend scripts ':!scripts/detect-external-api-change.js' ':!scripts/tests' | tail -5
    cd ~/sa && git grep -n -i firebase -- scripts/setup_review_tenant.py scripts/setup_tenant.py backend/scripts backend/requirements.txt | tail -5
    cd ~/sa && git grep -l -i firebase -- backend/tests | tail -10
期待: 1 つめは `backend/app/services/tenant.py:616` の 1 行だけ。2 つめと 3 つめは 0 行。4 つめは `backend/tests/conftest.py`・`backend/tests/ops/test_ai_cloud_views.py`・`backend/tests/rls_bootstrap.py`・`backend/tests/test_export_inventory_for_sheet.py`・`backend/tests/test_setup_review_tenant.py`・`backend/tests/test_staff_create_users.py` の 6 つだけ。

手順13 変わったファイルを確かめる
    cd ~/sa && git status --short | tail -40 && git diff --stat | tail -3

手順14 記録して送る
    cd ~/sa && git add -A backend scripts .github/workflows/test.yml frontend/api-contract/openapi.json && git commit -q -m "refactor(auth): remove Firebase from the server (firebase-removal bin2)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/firebase-removal-bin2 2>&1 | tail -3

## 4. 想定される分かれ道

- P1〜P7 のどれかが外れた → 実装せず `BLOCKED: P番号 と見えたもの`。
- 手順7 で `import firebase_admin` が通る → requirements-dev.txt など別の所から入っている。`uv pip show firebase-admin` の `Required-by` を報告して `BLOCKED: K2 firebase-admin が別の部品から入る`。
- 手順7 で K4 の import が 1 つでも失敗 → 失敗した部品の名前を報告して `BLOCKED: K4 と部品の名前`（requirements.txt に足すかは Opus が決める）。
- 手順8 で openapi.json の差分に、説明文（description）以外の変化（道筋・型・必須の印）がある → 差分の該当部分を報告して `BLOCKED: openapi の形が変わった`。
- 手順10・11 で、§2 で変えていない試験が赤 → `git stash` で変更を退かして同じ試験を流し、もともと赤かを確かめる。もともと赤なら試験名と最後の 15 行を報告して先に進む。変更で赤になったなら、赤の試験名と最後の 30 行を報告して `BLOCKED: と試験名`。
- 手順11 で、表全体の件数を数える試験（`password_reset_tokens` の COUNT）が他の試験の残りで赤 → 2-13 の 1 行が入っているかを確かめ、入っていて赤なら `BLOCKED: 鍵の残り`。
- 手順12 で期待と違う行が出た → 行をそのまま報告し、§2 の書き漏れか、§1 の触らない所かを書いて `BLOCKED: 残り`。
- 変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名と行 変更前の文が一致しない`。
- `scripts/tests/test-detect-external-api-change.js` は Firebase の語を期待しているが、CI では流れず便3 で直す。今回は触らない。

## 5. 報告の形

- 1 行目: 受領確認（`RECEIVED firebase-removal-bin2 HEAD=…`）。
- 手順2・7・8・9・10・11・12・13・14 の出力（tail の範囲）をそのまま貼る。
- §4 の分かれ道に入ったら、どれに入ったかと見えたもの。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
