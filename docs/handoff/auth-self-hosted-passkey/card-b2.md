# 実装カード 便2 — 自社ログインの心臓部（backend のみ・既定は Firebase のまま）

> 審査: Fable REVISE（HIGH 3・MEDIUM 6・LOW 4）→ 全13件反映済み（2026-10-13・再審査不要の判定）。
> この文書は何か：ADR-1013 の便2 として、パスワードの照合と自社トークンの発行・確認を backend に作る指示書です。本番では既定の `AUTH_PROVIDER=firebase` のままなので、利用者から見た動きは何も変わりません。

- 設計: docs/handoff/auth-self-hosted-passkey/design.md §3・§4・§6 便2
- 前提: #4225（ADR-1013 改名・列名 password_argon2_hash）は main にマージ済み（37194570b）。便1 の表は PR #4227 で作成中。**本便のマージは便1 の本番反映を確認した後**。本便のコードは便1 未反映でも本番を壊さない（既定 firebase・秘密なしでは新しい表に触れない。§7）
- 危険便: いいえ（コードのみ）。認証なのでコード審査はセキュリティ観点を必須にする
- 担当: 実装 Sonnet／コード審査 Fable（セキュリティ観点込み）／マージ Opus

## 1. 範囲

入れる: パスワード照合（Argon2id）、自社アクセストークンの発行と確認、更新用トークン（発行・入れ替え・使い回し検知・失効）、口座ロック、`POST /api/v1/auth/login`・`POST /api/v1/auth/refresh`、既存 `POST /api/v1/auth/logout` の拡張、`get_current_user` の iss 振り分け、起動時の設定検査、依存 `argon2-cffi`。

入れない（後の便）: 再設定・メール（便3）、`register` の置き換え・`password/change`・漏洩パスワード一覧・画面（便4）、パスキー（便5）、Firebase 撤去（便6）。

## 2. 前提の事実（調査 2026-10-13・origin/main 基準）

| # | 事実 | 出典 |
|---|---|---|
| E1 | `get_current_user` は :72。SMOKE :99-113 → ブラックリスト :116 → JWT キャッシュ :125-133（`cached["email"]` で users を引く）→ IP ロック :136 → Firebase 確認 :143-150（失敗で `record_auth_failure` → 401「無効な認証トークンです」）→ MFA :153-160 → email で users :169-178 → tenant 照合 :181-186 → `cache_jwt_result` :189 | `backend/app/auth/dependencies.py` |
| E2 | 既存テストは `app.auth.dependencies.firebase_auth`・`_init_firebase`・`is_token_blacklisted`・`get_cached_jwt`・`check_auth_rate_limit`・`record_auth_failure` ・`_get_client_ip` を patch している（test_security_hardening.py:192 は `firebase_admin.auth.verify_id_token` をモジュール直で patch）。これらの名前と import は残す | `backend/tests/test_line_import_devices.py:53`・`backend/tests/test_security_hardening.py:169-192`・`backend/tests/test_event_loop_nonblocking.py:170-181` |
| E3 | Settings クラスは無い。各モジュール先頭の `os.getenv` が慣例。起動時に必須の環境変数を検査して止める前例 | `backend/app/main.py:141-180` |
| E4 | `backend/app/models.py` に `Column(` を足すと `.github/workflows/migration-guard.yml` チェック1 が deploy.yml の追記を求める。新しい列はモデルに足さず、`text()` の生 SQL で読み書きする | migration-guard.yml チェック1 |
| E5 | python-jose 3.5.0 は requirements にある（`backend/requirements.txt:14`）が app 内で未使用。`sub` は文字列必須（jose/jwt.py:391-405）。`issuer=` を渡さないと iss を確かめない（:384）。`get_unverified_header` で kid を先に読める（:187） | PyPI・GitHub mpdavis/python-jose 3.5.0（Context7 は月の上限で使用不可） |
| E6 | argon2-cffi 25.1.0。`PasswordHasher(time_cost, memory_cost, parallelism, ...)`。`verify` は不一致で `VerifyMismatchError`、他に `VerificationError`・`InvalidHashError`。`check_needs_rehash` | PyPI・GitHub hynek/argon2-cffi |
| E7 | IP 単位のロック `check_auth_rate_limit(ip)`（:292）・`record_auth_failure(ip)`（:309）が既にある。ブラックリスト `blacklist_token`（:141） | `backend/app/cache.py` |
| E8 | `/api/v1/auth/*` の全リクエストは AuditMiddleware が `public.auth_events` に記録済み（:34・:142-180） | `backend/app/middleware/audit.py` |
| E9 | テストは SQLite。users の DDL は手書き（:1172-1182）で、is_super_admin・last_login・新 4 列が無い | `backend/tests/conftest.py` |
| E10 | 開いている PR #4217 が `backend/app/routers/auth.py`（register の role 2 行削除）・`backend/app/schemas/auth.py`・`backend/tests/conftest.py`・`frontend/api-contract/openapi.json`・`backend/app/models.py` を触る | `gh pr diff 4217` |

## 3. 触るファイル

| ファイル | 変更 |
|---|---|
| `backend/requirements.txt` | `argon2-cffi==25.1.0` を 1 行追加 |
| backend/app/auth/passwords.py（新設） | §4.1 |
| backend/app/auth/self_tokens.py（新設） | §4.2・§4.3 |
| `backend/app/routers/auth.py` | §4.4（login・refresh 追加、logout 拡張。register は触らない） |
| `backend/app/auth/dependencies.py` | §4.5（④ の前に振り分けを 1 か所足す。他の段は変えない） |
| `backend/app/main.py` | §4.6（起動時検査 1 か所） |
| `backend/tests/conftest.py` | SQLite の users DDL に列を足す、新表 auth_refresh_tokens の SQLite 版 DDL を足す（§5） |
| backend/tests/test_self_auth.py（新設） | §5 |
| docs/handoff/auth-self-hosted-passkey/card-b2.md（新設） | 本カードの写し（設計者が渡した版をそのまま置く） |
| `frontend/api-contract/openapi.json` | 再生成: `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`（`.github/workflows/api-contract-check.yml:35` と同じ）。`frontend/src/api/generated/` は .gitignore 対象なのでコミットしない |

触らない: `backend/app/models.py`（E4）・`backend/app/middleware/`・`backend/app/cache.py`・`migrations/`・`frontend/src/`・`.github/`・`docker-compose.yml`・`nginx/`・`register` の処理。

## 4. 作り方

### 4.1 passwords.py

- `_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)`（OWASP の Argon2id 推奨値。設計 §2 の文字列 `m=19456,t=2,p=1` と一致させる）
- `hash_password(plain: str) -> str`
- `verify_password(stored_hash: str | None, plain: str) -> bool`: `stored_hash` が None なら `_DUMMY_HASH` で照合して False。`VerifyMismatchError`・`VerificationError`・`InvalidHashError` は False（例外を外に出さない）
- `_DUMMY_HASH`: import 時に `_HASHER.hash(secrets.token_urlsafe(16))` で 1 回作る（存在しない人・停止中の人でも同じ時間をかけるため）
- `needs_rehash(stored_hash: str) -> bool`
- 照合は CPU を使うので、呼ぶ側は `await asyncio.to_thread(verify_password, ...)` で呼ぶ

### 4.2 self_tokens.py — 設定とアクセストークン

定数（既定値と名前だけ。**環境変数は import 時に固定せず、呼び出し時に `os.getenv` で読む関数にする**＝テストの `monkeypatch.setenv` が効くように）:

```
DEFAULT_AUTH_PROVIDER = "firebase"            # firebase | self
DEFAULT_RP_ORIGIN = "https://app.salesanchor.jp"
ISSUER = "salesanchor"
ACCESS_TOKEN_TTL_SECONDS = 900
REFRESH_ABSOLUTE_TTL = timedelta(days=30)
REFRESH_COOKIE_NAME = "sa_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"
MIN_SECRET_LENGTH = 32
LOGIN_FAIL_LIMIT = 10
LOGIN_LOCK_DURATION = timedelta(minutes=15)
```

読み取り関数（毎回 os.getenv）:
- `auth_provider() -> str`: `os.getenv("AUTH_PROVIDER", DEFAULT_AUTH_PROVIDER).strip().lower()`
- `_secret() -> str`・`_secret_previous() -> str`: `AUTH_JWT_SECRET`・`AUTH_JWT_SECRET_PREVIOUS`（既定 ""）
- `rp_origin() -> str`: `AUTH_RP_ORIGIN`（既定 DEFAULT_RP_ORIGIN）
- `cookie_secure() -> bool`: `AUTH_COOKIE_SECURE` が "false" 以外なら真
- 呼ぶ側（routers/auth.py・dependencies.py）は `from app.auth import self_tokens` でモジュールを参照し、`self_tokens.xxx()` で呼ぶ（名前を個別 import しない）

- `_kid(secret) -> str`: `hashlib.sha256(secret.encode()).hexdigest()[:8]`（鍵そのものを出さずに鍵を見分ける印）
- `is_issuance_enabled() -> bool`: `auth_provider() == "self" and bool(_secret())`（設計 §3：無効にするのは login・refresh・passkey/login の 3 系統だけ）
- `is_verification_enabled() -> bool`: `bool(_secret())`（便2〜便5 は両方のトークンを受ける。本番の便2 時点では秘密が無いので自社トークンは全部拒否される）
- `validate_settings() -> None`: `auth_provider()` が firebase/self 以外 → `RuntimeError`。`self` なのに `_secret()` が空 → `RuntimeError`。`_secret()` か `_secret_previous()` が空でなく `MIN_SECRET_LENGTH` 未満 → `RuntimeError`。メッセージに秘密の値を入れない
- `create_access_token(user_id: int, email: str, amr: str | None) -> str`: claims は `iss=ISSUER`・`sub=str(user_id)`・`email`・`jti=uuid4().hex`・`iat`・`exp=iat+900`、`amr` が None でなければ `amr=[amr]`。`jwt.encode(claims, _secret(), algorithm="HS256", headers={"kid": _kid(_secret())})`
- `peek_issuer(token) -> str | None`: `jwt.get_unverified_claims` で iss を読む。例外は None（振り分けにだけ使い、信用はしない）
- `decode_access_token(token) -> dict`: `jwt.get_unverified_header` の kid が `_kid(_secret())` なら今の鍵、`_secret_previous()` があり `_kid(_secret_previous())` と一致すれば前の鍵、どちらでもなければ `JWTError`。`jwt.decode(token, key, algorithms=["HS256"], issuer=ISSUER, options={"require_exp": True, "require_iat": True, "require_sub": True, "require_jti": True, "require_iss": True})`。`algorithms` は必ず `["HS256"]` だけ（none や RS 系を受けない）

### 4.3 self_tokens.py — 更新用トークン（表 public.auth_refresh_tokens・生 SQL）

- 生のトークン: `secrets.token_urlsafe(32)`。保存は `hashlib.sha256(raw.encode()).digest()`（32 バイト）だけ
- 時刻は Python の `datetime.now(timezone.utc)` を渡す（SQL の now() に頼らない。SQLite と揃えるため）。`created_at`・`family_created_at` も INSERT で明示的に渡す
- `_as_utc(value) -> datetime | None`: None は None。str なら `datetime.fromisoformat`、tz 無しなら UTC を付ける。**RETURNING・SELECT で得た時刻は必ずこれを通してから比較・加算する**（SQLite の `text()` は str で返すため）
- `family_id` は `str(uuid4())` を渡す（Postgres の UUID 列・SQLite の TEXT 列の両方で通る）
- `issue_refresh_token(db, user_id, user_agent, family_id=None, family_created_at=None) -> tuple[str, datetime]`: family が無ければ `uuid4()` と今の時刻で作る。`expires_at = family_created_at + REFRESH_ABSOLUTE_TTL`（入れ替えても延びない）。`user_agent_hash` は UA の sha256（UA が無ければ NULL）。戻り値は（生トークン, expires_at）
- `rotate_refresh_token(db, raw, user_agent) -> tuple[int, str, datetime] | None`:
  1. 1 文で失効させて取り出す（競合しても 2 回使えない）: `UPDATE public.auth_refresh_tokens SET revoked_at = :now, last_used_at = :now WHERE token_hash = :h AND revoked_at IS NULL AND expires_at > :now RETURNING user_id, family_id, family_created_at, created_at`
  2. 行が返らなければ: `SELECT revoked_at FROM public.auth_refresh_tokens WHERE token_hash = :h`。行があり `revoked_at` が入っていれば使い回し → `UPDATE ... SET revoked_at = :now WHERE family_id = :f AND revoked_at IS NULL`（同じ組を全部失効）。どの場合も None。**同時に 2 つのタブが同じ Cookie で refresh した場合も 2 本目は使い回し扱いで組ごと失効する。これは仕様として受け入れる（猶予は作らない。design.md の使い回し検知どおり）。画面側（便4）で refresh を 1 本に直列化する**
  3. users を引く（`SELECT id, email, is_active, password_changed_at FROM public.users WHERE id = :uid`）。いない・`is_active` が偽・`password_changed_at` が更新用トークンの `created_at` より後 → None
  4. 同じ family で `issue_refresh_token` → （user_id, 新しい生トークン, expires_at）を返す
- `revoke_refresh_token(db, raw) -> None`: ハッシュが一致する行を `revoked_at = :now`（無ければ何もしない）

### 4.4 routers/auth.py

共通:
- `_require_app_origin(request)`: `request.headers.get("origin")` が `self_tokens.rp_origin()` と完全一致しなければ `HTTPException(403)`。login・refresh に付ける（logout には付けない。今の Firebase 画面のログアウトの動きを変えないため。design.md の logout の Origin 照合は便4 で付ける）
- 発行経路が無効（`not is_issuance_enabled()`）のときは login・refresh とも `HTTPException(404)`
- 失敗の文言は 1 種類だけ: `detail="invalid_credentials"`（存在しない・停止中・パスワード違い・未設定・ロック中を区別しない）
- Cookie の付け方: `response.set_cookie(REFRESH_COOKIE_NAME, raw, httponly=True, secure=self_tokens.cookie_secure(), samesite="strict", path=REFRESH_COOKIE_PATH, max_age=<expires_at までの秒数>)`。消すときは同じ name・path で `delete_cookie`

`POST /login`（本文 `{"email": EmailStr, "password": str}`。password は 1〜1024 文字の検証だけ）:
1. 発行経路の確認（無効なら 404）→ Origin 照合（403）→ IP ロック（`check_auth_rate_limit(ip)` が真なら 429。IP の取り方は `dependencies._get_client_ip` を使う）
2. `email.strip().lower()` で `SELECT id, email, is_active, password_argon2_hash, failed_login_count, locked_until FROM public.users WHERE lower(email) = :email`
3. いない・`is_active` が偽・`locked_until` が今より後 → `await asyncio.to_thread(verify_password, None, password)`（ダミー照合）→ `record_auth_failure(ip)` → 401（ロック中は回数を増やさない）
4. 照合失敗 → SQL 側で加算: `UPDATE public.users SET failed_login_count = failed_login_count + 1 WHERE id = :id RETURNING failed_login_count`（同時ログインで取りこぼさない）。返り値が `LOGIN_FAIL_LIMIT` 以上なら `UPDATE ... SET locked_until = :now + 15分, failed_login_count = 0 WHERE id = :id`。commit → `record_auth_failure(ip)` → 401
5. 照合成功 → `failed_login_count = 0`・`locked_until = NULL`・`last_login = now`。`needs_rehash` が真なら `password_argon2_hash` を作り直す。更新用トークンを発行。commit。本文 `{"access_token": ..., "token_type": "bearer", "expires_in": 900}`＋Cookie。アクセストークンの `amr` は `"pwd"`
6. commit は `await db.commit()` のみ。`reset_tenant_context` は不要（tenant 依存の無い endpoint は linter 対象外。`scripts/lint_tenant_schema.py:257-260`）
7. タイミング差について: 存在する email の誤パスワードは DB 書込の分だけ応答が遅く、存在の推定材料になり得る。利用者 10 人規模のため受け入れる（Argon2 照合は両方で必ず 1 回行う）

`POST /refresh`（本文なし）:
1. 発行経路の確認（404）→ Origin 照合（403）
2. Cookie が無い → 401。`rotate_refresh_token` が None → Cookie を消して 401
3. 成功 → users の email を引き、アクセストークンを発行（`amr=None`。更新では元のログイン方法を表に持たないため付けない）。commit。本文は login と同じ形＋新しい Cookie

`POST /logout`（既存 :137-153 を拡張）:
- 今の処理（Bearer をブラックリストへ）はそのまま
- Cookie `sa_refresh` があれば `revoke_refresh_token` して commit し、Cookie を消す。発行経路が無効でも行う（無害なので）

### 4.5 dependencies.py（`get_current_user` の ③ IP ロックの直後、Firebase 確認の直前に足す）

```
if peek_issuer(token) == ISSUER:
    return await _authenticate_self_token(token, client_ip, db)
```

`_authenticate_self_token`（同じファイルに新設）:
1. `is_verification_enabled()` が偽 → `record_auth_failure(client_ip)` → 401「無効な認証トークンです」（既存と同じ文言）
2. `decode_access_token` が失敗（`JWTError` 系）→ `record_auth_failure` → 401（同じ文言）
3. `SELECT id, email, is_active, password_changed_at FROM public.users WHERE id = :id`（`int(claims["sub"])`。変換できなければ 401）。`password_changed_at` は `_as_utc` を通し、`iat` は `datetime.fromtimestamp(claims["iat"], timezone.utc)` に直して比較
4. いない・`is_active` が偽 → 401。`claims["email"]` と users.email が一致しない → 401。`password_changed_at` があり `claims["iat"]` がそれより前 → 401
5. ORM の `User` を id で取り、`cache_jwt_result(token, {"email": user.email})` → return user（MFA 判定と JWT の tenant_id 照合は自社トークンでは行わない。テナントは既存どおり DB の user.tenant_id）

SMOKE・ブラックリスト・キャッシュ・IP ロックの順序と、Firebase の分岐（:143 以降）は 1 文字も変えない（ADR-127 auth-lockout-bystander-fix）。自社トークンも成功後 5 分は JWT キャッシュで通るため、パスワード変更後の締め出しは最大 5 分遅れる（design.md で受け入れ済み）。

### 4.6 main.py

既存の起動時検査（:141-180 付近）と同じ場所で `self_tokens.validate_settings()` を呼ぶ。本番は環境変数が無い＝firebase・秘密なしなので、何も起きない。

## 5. テスト（backend/tests/test_self_auth.py・SQLite）

conftest.py の users DDL に `last_login TIMESTAMP`・`password_argon2_hash TEXT`・`password_changed_at TIMESTAMP`・`failed_login_count INTEGER NOT NULL DEFAULT 0`・`locked_until TIMESTAMP` を足す（既にある列は足さない）。auth_refresh_tokens の SQLite 版（BYTEA→BLOB、UUID→TEXT、TIMESTAMPTZ→TIMESTAMP、BIGSERIAL→INTEGER PRIMARY KEY AUTOINCREMENT）を足す。`public.auth_refresh_tokens` を conftest.py:160-181 の `public.` 書き換え一覧に足す（今は無い）。テストファイルの先頭で `sqlite3.sqlite_version_info >= (3, 35)` を assert する（RETURNING のため。満たさなければ skip ではなく失敗）。テストでは monkeypatch.setenv で `AUTH_PROVIDER=self`・`AUTH_JWT_SECRET`（32 文字以上のテスト値）を設定する。

必ず入れるテスト（名前は例）:
1. hash → verify が真、違うパスワードは偽、壊れたハッシュは偽（例外が出ない）、None は偽
2. login 成功: 200・本文に access_token・Cookie が HttpOnly／SameSite=Strict／Path=/api/v1/auth・last_login が入る・failed_login_count が 0
3. 誤ったパスワード・存在しない email・is_active 偽・パスワード未設定は、すべて 401 で `detail` が同じ
4. 10 回失敗で locked_until が入り、正しいパスワードでも 401。期限を過去にすると成功
5. `AUTH_PROVIDER=firebase` のとき login と refresh は 404
6. `AUTH_PROVIDER=self` で Origin が違う・無いとき login と refresh は 403
6b. 同じ Cookie で 2 回 refresh すると 2 回目は 401 で、同じ family の行が全部失効している（同時タブの仕様の固定）
7. refresh: 入れ替わる（古い Cookie で 2 回目は 401）・使い回しで同じ family が全部失効・family_created_at から 30 日を過ぎたら 401・password_changed_at が後なら 401
8. logout で更新用トークンが失効し Cookie が消える
9. get_current_user: 自社トークンで利用者が返る・別の鍵で署名したものは 401・前の鍵（`AUTH_JWT_SECRET_PREVIOUS`）で署名したものは受ける・email 不一致は 401・iat が password_changed_at より前なら 401・`AUTH_JWT_SECRET` が無いと自社トークンは 401・alg を none にしたトークンは 401
10. validate_settings: 不正な AUTH_PROVIDER・self で秘密なし・短い秘密で RuntimeError
11. 既存の Firebase 経路のテスト（E2 のファイル）が全部そのまま通る

## 6. 分岐ごとの対処

| 起きたこと | 対処 |
|---|---|
| #4217 が先に main に入り `routers/auth.py`・`tests/conftest.py`・`openapi.json` が衝突 | routers/auth.py と conftest.py は両方を残す（#4217 の変更はそのまま、本便の追加もそのまま）。openapi.json は main を採ってから再生成。それ以外の衝突は止まって報告 |
| conftest の DDL を変えたら既存テストが落ちる | 止まって、落ちたテスト名と生出力を報告 |
| sqlite_version の assert が CI で落ちる | 止まって報告（別の書き方を勝手に選ばない） |
| フックに止められた | 言い換えて再試行せず止まって報告 |
| 本カードに無い部品・列・表が要る | 作らずに止まって報告 |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| §5 のテストが全部緑・既存の backend テストも全部緑 | `cd backend && python -m pytest -q` の最終行を貼る（CI「pytest」も緑） |
| 本番の挙動が変わらない | 本番の環境変数に AUTH_PROVIDER・AUTH_JWT_SECRET が無いこと（`docker-compose.yml`・`.github/workflows/deploy.yml` に新しい変数を足していない＝`git diff` で確認）。デプロイ後、`POST https://app.salesanchor.jp/api/v1/auth/login`（Origin あり・なしとも）が 404（デプロイ前の基準値も 404・2026-10-13 19:37 JST。`/health` 200・トークンなし `POST /api/v1/auth/logout` 401 も前後で同じ）（発行経路が無効。404 判定は Origin 照合より先）で、今のログイン画面からのログインと既存 API が今どおり動く（API の health と、既存の認証付き API が 401／200 を今どおり返す） |
| 触ったファイルが §3 だけ | `git diff origin/main --name-only` |
| 秘密を出していない | ログ・例外メッセージ・テスト出力に秘密の値が出ない（gitleaks 緑） |

## 8. PR

- タイトル: `feat: self-hosted login core behind AUTH_PROVIDER switch (ADR-1013 stage 2)`
- `### 標準ワークフロー確認` に recon・design・ADR-1013・本カード
- Draft にしない。マージは設計者
