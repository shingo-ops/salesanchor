# card: 自社ログイン中は Firebase の札を断る（1 便で終わり）

状態: カード発行（Opus、2026-11-04）。PO の進める判断は 2026-11-04「2」（design.md の状態の行）。設計: [design.md](./design.md)。根拠: [recon.md](./recon.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」の 3 つだけ。本番・GitHub の secret と Variables には触らない。PR は作らない（Opus が作る）。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルを §1 で全部挙げた。PR は Opus が手元で shingo-cc 名義で作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に変更後のコードを全文で書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED block-firebase-token HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/block-firebase-token-in-self` を origin から取り直し、`docs/handoff/block-firebase-token/card.md` が在ること。
- P2 `git diff --quiet b6b999d01 -- backend/app/auth/dependencies.py backend/tests/test_self_auth.py backend/tests/test_smoke_auth_least_privilege.py` が終了 0 であること（3 つが基準から変わっていない）。
- P3 `grep -c "firebase_closed" backend/app/auth/dependencies.py` が 0 であること。
- P4 `grep -n "verify_id_token" -r backend/app` が `backend/app/auth/dependencies.py:236` の 1 行だけであること。

## 1. 触るファイル（この 3 つだけ）
1. `backend/app/auth/dependencies.py`（2-1 の 2 か所だけ）
2. `backend/tests/test_self_auth.py`（2-2 の import 1 行の書き換えと、末尾への追記だけ）
3. `backend/tests/test_smoke_auth_least_privilege.py`（2-3 の末尾への追記だけ）

触らない: 上の 3 つ以外のすべて（`backend/app/auth/self_tokens.py`・`docs/`・`frontend/`・`.github/` を含む）。上の 3 つの中でも、書いていない行は 1 文字も変えない。

## 2. 変更の中身

### 2-1. `backend/app/auth/dependencies.py`

(a) 変更前（`:210-213`）:

```python
    # ② Redisキャッシュからユーザー情報を取得
    # キャッシュヒット: ブラックリスト未登録 & 既存セッション確認済み → IPロックをスキップ
    # 同一IPの他ユーザーによる攻撃でロックされても、正規ユーザーの操作を巻き添え遮断しない。
    cached = await get_cached_jwt(token)
```

変更後:

```python
    # 自社ログイン中（AUTH_PROVIDER=self）は Firebase の札を受け付けない（docs/handoff/block-firebase-token/design.md）。
    # 自社の札でなければ、②の一時記憶を使わず、③の回数確認の後で 401 にする。
    firebase_closed = self_tokens.auth_provider() == "self"
    is_self_issuer = self_tokens.peek_issuer(token) == self_tokens.ISSUER

    # ② Redisキャッシュからユーザー情報を取得
    # キャッシュヒット: ブラックリスト未登録 & 既存セッション確認済み → IPロックをスキップ
    # 同一IPの他ユーザーによる攻撃でロックされても、正規ユーザーの操作を巻き添え遮断しない。
    cached = await get_cached_jwt(token) if (is_self_issuer or not firebase_closed) else None
```

(b) 変更前（`:230-232`）:

```python
    # 自社トークン（iss=salesanchor）は Firebase 検証に回さず、自社検証へ振り分ける
    if self_tokens.peek_issuer(token) == self_tokens.ISSUER:
        return await _authenticate_self_token(token, client_ip, db)
```

変更後:

```python
    # 自社トークン（iss=salesanchor）は Firebase 検証に回さず、自社検証へ振り分ける
    if is_self_issuer:
        return await _authenticate_self_token(token, client_ip, db)

    # 自社ログイン中は Firebase 検証に進まない（失敗として数え、同じ文言の 401）
    if firebase_closed:
        logger.warning("自社ログイン中に自社以外の札を拒否: ip=%s", client_ip)
        raise await _reject_self_token(client_ip)
```

### 2-2. `backend/tests/test_self_auth.py`

(a) `:7` の 1 行を書き換える。

変更前: `from unittest.mock import AsyncMock, patch`
変更後: `from unittest.mock import AsyncMock, MagicMock, patch`

(b) ファイルの末尾に次をそのまま足す（前に空行を 2 つ）。

```python
# ── 9b. 自社ログイン中は Firebase の札を受け付けない（docs/handoff/block-firebase-token/design.md） ──

FIREBASE_LIKE_TOKEN = "firebase-like-token-not-salesanchor"


async def _current_user_with(db, token, *, cached=None, rate_limited=False):
    """get_current_user を呼び、(利用者, 例外, 一時記憶の偽物, 失敗記録の偽物, Firebase 確認の偽物) を返す。
    Firebase の確認の偽物は、いつも「正しい札」と答える（K1: それでも断ることを確かめる）。"""
    from app.auth.dependencies import get_current_user

    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    get_cached = AsyncMock(return_value=cached)
    record = AsyncMock()
    verify = MagicMock(return_value={"email": EMAIL})
    with patch("app.auth.dependencies._init_firebase"), \
         patch("app.auth.dependencies.MFA_REQUIRED", False), \
         patch("app.auth.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)), \
         patch("app.auth.dependencies.get_cached_jwt", new=get_cached), \
         patch("app.auth.dependencies.check_auth_rate_limit", new=AsyncMock(return_value=rate_limited)), \
         patch("app.auth.dependencies.record_auth_failure", new=record), \
         patch("app.auth.dependencies.cache_jwt_result", new=AsyncMock()), \
         patch("app.auth.dependencies.firebase_auth.verify_id_token", new=verify):
        try:
            user = await get_current_user(_request(), cred, db)
        except HTTPException as exc:
            return None, exc, get_cached, record, verify
    return user, None, get_cached, record, verify


async def test_self_mode_rejects_firebase_token_even_if_firebase_accepts(db_session, password_hash):
    """T1・K1"""
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, _, record, verify = await _current_user_with(db_session, FIREBASE_LIKE_TOKEN)

    assert user is None and exc.status_code == 401
    verify.assert_not_called()
    record.assert_awaited_once()


async def test_self_mode_ignores_cached_firebase_token(db_session, password_hash):
    """T2・K2"""
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, get_cached, _, verify = await _current_user_with(
        db_session, FIREBASE_LIKE_TOKEN, cached={"email": EMAIL}
    )

    assert user is None and exc.status_code == 401
    get_cached.assert_not_awaited()
    verify.assert_not_called()


async def test_self_mode_rate_limit_still_429_for_firebase_token(db_session):
    """T3・K5"""
    user, exc, _, _, verify = await _current_user_with(db_session, FIREBASE_LIKE_TOKEN, rate_limited=True)

    assert user is None and exc.status_code == 429
    verify.assert_not_called()


async def test_self_mode_still_accepts_self_token_from_cache(db_session, password_hash):
    """T4・K3"""
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, get_cached, _, _ = await _current_user_with(db_session, _token(), cached={"email": EMAIL})

    assert exc is None and user.id == USER_ID
    get_cached.assert_awaited_once()


async def test_self_mode_still_accepts_self_token_without_cache(db_session, password_hash):
    """T5・K3"""
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, _, _, verify = await _current_user_with(db_session, _token())

    assert exc is None and user.id == USER_ID
    verify.assert_not_called()


async def test_firebase_mode_still_accepts_firebase_token(db_session, password_hash, monkeypatch):
    """T6・K4（戻し方: AUTH_PROVIDER=firebase なら今までどおり）"""
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
    await _insert_user(db_session, hash_value=password_hash)

    user, exc, _, _, verify = await _current_user_with(db_session, FIREBASE_LIKE_TOKEN)

    assert exc is None and user.email == EMAIL
    verify.assert_called_once()
```

### 2-3. `backend/tests/test_smoke_auth_least_privilege.py`

ファイルの末尾に次をそのまま足す（前に空行を 2 つ）。

```python
async def test_smoke_token_passes_when_auth_provider_self(monkeypatch):
    """T7・K6: 自社ログイン中でも smoke の札は通る（docs/handoff/block-firebase-token/design.md）"""
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    user = _user(False)

    result = await _run(SMOKE_TOKEN, user)

    assert result is user
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/block-firebase-token-in-self

手順2 0. の点検 P1〜P4 を行い、結果をそのまま報告に書く。

手順3 2. の変更を入れる。

手順4 試験を走らせる（依存の入れ方は backend/requirements.txt と backend/requirements-dev.txt があればそれを使う）
    cd ~/sa/backend && python -m pytest tests/test_self_auth.py tests/test_smoke_auth_least_privilege.py tests/test_security_hardening.py -q 2>&1 | tail -30

手順5 差分が 3 ファイルだけであることを確かめる
    cd ~/sa && git diff --stat

手順6 commit する（message は 1 行目 `fix(auth): reject non-self tokens while AUTH_PROVIDER=self`）
    cd ~/sa && git add backend/app/auth/dependencies.py backend/tests/test_self_auth.py backend/tests/test_smoke_auth_least_privilege.py && git commit -m "fix(auth): reject non-self tokens while AUTH_PROVIDER=self"

手順7 commit が在ることを確かめる
    cd ~/sa && git log --oneline -2

手順8 push する
    cd ~/sa && git push origin release/block-firebase-token-in-self

## 4. 想定される分かれ道

- 手順4 で依存が入らず試験を走らせられない: 入れようとした命令と誤りの出力をそのまま報告に書き、手順5・6 へ進む（判定は PR の CI で行う）。
- 手順4 で、今回足した試験が赤: 直さずに、試験名と出力全文を報告に書いて BLOCKED: で止まる（push しない）。
- 手順4 で、今回足していない試験が赤: `git stash` で変更を外して同じ試験を走らせ、外しても赤なら「元から赤」と書いて進む。外すと緑なら BLOCKED: で止まる。
- push が拒まれた: 出力をそのまま書いて BLOCKED: で止まる。force は使わない。

## 5. 報告の形

1 行目に受領確認。続けて P1〜P4 の結果、手順4 の出力の最後の 30 行、手順5 と手順7 の出力、push 後の `git rev-parse HEAD`。最後の行は `DONE` か `BLOCKED: 理由`。秘密の値は書かない。

停止するとき（BLOCKED:）も、ここまでの出力を同じ形で報告に書いてから止まる。報告はこの実行の最後の返事に書く（別の場所には書かない）。

END OF CARD
