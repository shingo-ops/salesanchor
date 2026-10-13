# 実装カード 便3 — メール送信の設定を1か所にまとめ、パスワード再設定 API を作る

> この文書は何か：ADR-1013 便3 の作業指示書です。メール送信の設定を1か所にまとめ（PO 決定 y1）、自社のパスワード再設定 API（申請・確定）とそのメールを作ります。本番のログインは Firebase のまま（`AUTH_PROVIDER=firebase`）で、再設定メールは試験用アドレスにしか送りません。

- 設計: docs/handoff/auth-self-hosted-passkey/design.md §2・§3（:76-77）・§3 パスワードの決まり（:88-97）・§6 便3（:156）
- 判断メモ（PO 決定 y1）: docs/handoff/auth-self-hosted-passkey/decision-b3-mail.md §5
- 対象ADR: ADR-1013（本テーマ）、ADR-075（秘密は GitHub Secrets）、ADR-136（危険PRの GO）、ADR-1007（migration は構造のみ。本便は migration なし）
- 状態: 設計案（カード草案）。Fable 審査前。**PO の実装承認前（実装未着手）**
- 危険便: **はい**（`docker-compose.yml`・`.github/workflows/deploy.yml`・secrets）。マージ前に GO 記録（GO 委任中は「POの委任に基づくClaude Opus発行」）
- 担当: 実装 Sonnet／コード審査 Fable（セキュリティ観点込み）／GO・マージ・反映確認 Opus／GUI 作業 PO

## 1. 範囲

入れる:
1. メール送信の設定の読み取りを `mail_config.py` の1か所にまとめ、既存3か所（削除完了通知・発注書メール・問い合わせ通知）をそれに置き換える
2. パスワードの決まり（15〜64 文字・よく使われるパスワードの一覧で拒否）
3. `POST /api/v1/auth/password-reset/request` と `POST /api/v1/auth/password-reset/confirm`
4. 再設定メールの文面（日本語・英語を1通に併記）と送信（FastAPI の BackgroundTasks）
5. 設定の渡し口（deploy.yml が作る .env・compose の environment:）と、設定一覧の文書（`.env.example`・`docs/ENVIRONMENT_VARIABLES.md`）

入れない（理由）:
- 画面（再設定ページ・ログイン画面の金型化）→ 便4（design.md:157）
- `register` の置き換えと招待メール（purpose=invite）→ 便4（design.md:157。判断メモ §5-3 は register にも触れているが、design.md の便割りを優先する）。ただし confirm は design.md:77 のとおり purpose=invite の鍵も受け付ける形で作る
- `password/change` → 便4（画面の置き換え先のため）
- 発注書メールの Reply-To → 入れない。発注書 API を呼ぶ画面・GAS・スクリプトは 0 件、監査記録も 5 テナントとも 0 件（/tmp/CC報告ファイル/auth-b3/po-ui-callers.txt・po-mail-count.txt）。使われ始める時に決める
- Celery の待ち行列での送信 → 使わない（判断メモ §5-3。外部事例 GitHub 2024-04）

## 2. 前提の事実（2026-10-14・origin/main d1dd0ad62 基準）

| # | 事実 | 出典 |
|---|---|---|
| F1 | SMTP の「設定がそろっているか」の判定が3か所に重複（HOST・USER・PASSWORD・MAIL_FROM の4つ） | `backend/app/services/email_sender.py:40-46`・`backend/app/services/po_mailer.py:33-40`・`backend/app/routers/contact.py:41-47` |
| F2 | 値の読み取りも3か所に重複。`int(os.getenv("SMTP_PORT", "587"))` は、値が空文字だと ValueError になる | `backend/app/services/email_sender.py:58-62`・`backend/app/routers/contact.py:58-62`・`backend/app/services/po_mailer.py:76-90` |
| F3 | 問い合わせ通知の宛先は `os.getenv("CONTACT_NOTIFY_EMAIL", "support@salesanchor.jp")`。値が空文字で設定されると既定値に戻らず宛先が空になる | `backend/app/routers/contact.py:27` |
| F4 | deploy.yml は .env の秘密の行を一度消し（:258-283）、heredoc で書き足す（:291-316）。Secret が未登録なら `KEY=`（空文字）で書かれる | `.github/workflows/deploy.yml:258-316`・同 :289-290 のコメント |
| F5 | backend は `.env` 全行を `docker run --env-file` で受け取る。ロールバック経路は compose で backend を起動する。celery-worker は compose の `environment:` だけで受け取る | `scripts/blue-green-cutover.sh:92`・`.github/workflows/deploy.yml:659-662`・`docker-compose.yml:65-124`・`:201-239` |
| F6 | 本番の .env・backend・celery-worker に SMTP_・MAIL_ の名前は 0 件 | /tmp/CC報告ファイル/auth-b3/（判断メモ §2） |
| F7 | deploy.yml の起動は main への push だけ（workflow_dispatch なし） | `.github/workflows/deploy.yml:3-5` |
| F8 | 再設定用の表 `public.password_reset_tokens`（purpose は reset／invite、token_hash は 32 バイト、UNIQUE）は便1 で本番に作成済み | `migrations/20261013_160000_add_self_hosted_auth_tables.sql:47-66` |
| F9 | 既存部品: `self_tokens._hash_token`（sha256）・`self_tokens.rp_origin()`・`self_tokens._as_utc`・`passwords.hash_password`・`routers/auth.py` の `_require_app_origin`・`_get_client_ip`・`check_auth_rate_limit`／`record_auth_failure`（IP 単位・Redis 不通時は通す） | `backend/app/auth/self_tokens.py:49,141,145`・`backend/app/auth/passwords.py:20`・`backend/app/routers/auth.py:193`・`backend/app/cache.py:292-320` |
| F10 | パスワードの決まり（15〜64 文字・一覧）はまだ実装されていない。`backend/app/auth/` に data フォルダも無い | `git ls-tree origin/main backend/app/auth/`（7 ファイルのみ） |
| F11 | テスト用の SQLite には `auth_refresh_tokens` だけが作られ、`public.` を外す置換がある。`password_reset_tokens` は無い | `backend/tests/conftest.py:182-183`・`:1194-1208` |
| F12 | backend のイメージは backend/ を丸ごと入れる。`.dockerignore` は `*.md`・`tests/` を除く（`.txt` は入る） | `backend/Dockerfile:24`・`backend/.dockerignore` |
| F13 | nginx は `/api/v1/auth/` を IP ごと 10 回/分・burst 5 に制限 | `nginx/nginx.conf:6`・`:96-98`・`:292-294` |
| F14 | 監査記録は `record_audit_log(db, tenant_id, user_id, action, table_name, record_id, old_data, new_data)` | `backend/app/services/audit.py:277-286` |
| F15 | 設定の読み方は毎回 `os.getenv`（設定クラスは無い） | `backend/app/auth/self_tokens.py:35-54` |

## 3. 触るファイル（これ以外は触らない）

新規:
- `backend/app/services/mail_config.py`
- `backend/app/services/auth_mail.py`
- `backend/app/auth/password_policy.py`
- `backend/app/auth/data/common-passwords.txt`
- `backend/app/auth/data/README.md`
- `backend/tests/test_mail_config.py`
- `backend/tests/test_password_policy.py`
- `backend/tests/test_password_reset.py`

変更:
- `backend/app/services/email_sender.py`
- `backend/app/services/po_mailer.py`
- `backend/app/routers/contact.py`
- `backend/app/routers/auth.py`
- `backend/app/cache.py`
- `backend/tests/conftest.py`
- `docker-compose.yml`
- `.github/workflows/deploy.yml`
- `.env.example`
- `docs/ENVIRONMENT_VARIABLES.md`
- `docs/handoff/auth-self-hosted-passkey/card-b3.md`（このカード。報告欄の追記のみ）

## 4. 作り方

### 4.1 mail_config.py（新設・F1〜F3）

```python
"""メール送信の設定の読み取り口（ADR-1013 便3・PO 決定 y1）。

SMTP_* と MAIL_FROM を読むのはこのファイルだけ。毎回 os.getenv で読む（テストで差し替えるため・キャッシュしない）。
空文字は「未設定」と同じに扱う（deploy.yml は未登録の Secret を空文字で .env に書くため）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_SMTP_PORT = 587
DEFAULT_CONTACT_NOTIFY_EMAIL = "support@salesanchor.jp"


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    user: str
    password: str
    mail_from: str


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def smtp_settings() -> SmtpSettings | None:
    """HOST・USER・PASSWORD・MAIL_FROM がそろっていれば設定を返す。1つでも空なら None（送らずログだけ）。"""
    host, user, password, mail_from = _env("SMTP_HOST"), _env("SMTP_USER"), _env("SMTP_PASSWORD"), _env("MAIL_FROM")
    if not (host and user and password and mail_from):
        return None
    port_raw = _env("SMTP_PORT")
    port = int(port_raw) if port_raw.isdigit() else DEFAULT_SMTP_PORT
    return SmtpSettings(host=host, port=port, user=user, password=password, mail_from=mail_from)


def contact_notify_email() -> str:
    return _env("CONTACT_NOTIFY_EMAIL") or DEFAULT_CONTACT_NOTIFY_EMAIL
```

- `SMTP_PASSWORD` の値をログ・例外文・repr に出さない（`SmtpSettings` の `password` は `field(repr=False)` にする）。

### 4.2 既存3か所の置き換え（動きは今と同じ。未設定ならログだけ）

- `email_sender.py`: `_smtp_configured()` を消し、`_send` の先頭で `settings = smtp_settings()`。None ならいまと同じログを出して return。:58-62 の読み取りを `settings.host` 等に置き換える。
- `contact.py`: `_smtp_configured()` を消し、同じ形に置き換える。:27 の `ADMIN_EMAIL` 定数をやめ、送信時に `contact_notify_email()` を呼ぶ（F3 の空文字の穴をふさぐ）。
- `po_mailer.py`: `_smtp_configured()` を消す。`send_po_email_sync` の中を次の形にする（テスト用の上書き `smtp_overrides` の動きは変えない）:

```python
    overrides = smtp_overrides or {}
    base = smtp_settings()
    if not (overrides or base):
        logger.info(...)  # いまと同じ文言
        return SendResult(success=False, skipped=True)

    def _g(key: str, default: str = "") -> str:
        if overrides.get(key):
            return overrides[key]
        if base is None:
            return default
        return str({"smtp_host": base.host, "smtp_port": base.port, "smtp_user": base.user,
                    "smtp_password": base.password, "mail_from": base.mail_from}[key])
```

- 3ファイルとも `os.getenv("SMTP_` と `os.getenv("MAIL_FROM` が 0 件になること（§7）。
- `tests/test_po_mailer.py`・`tests/test_email_tasks.py`・`tests/test_event_loop_nonblocking.py` は変えずに通ること。

### 4.3 パスワードの決まり（新設・design.md:88-97）

- `backend/app/auth/data/common-passwords.txt`: SecLists の `Passwords/Common-Credentials/100k-most-used-passwords-NCSC.txt` を、取り込む時点のコミット SHA を固定した raw URL から取得する。大きさが 2 MB を超えたら取り込まず `BLOCKED:`。
- `backend/app/auth/data/README.md`: 出典 URL・コミット SHA・`wc -l` の件数・取得日・ライセンス（MIT）を書く。
- `backend/app/auth/password_policy.py`:

```python
MIN_LENGTH = 15
MAX_LENGTH = 64

def check_password(plain: str) -> str | None:
    """問題なければ None。だめなら理由のコード（password_too_short／password_too_long／password_too_common）。"""
```

  - 長さは Python の `len()`（文字数）で数える。一覧は起動後の最初の呼び出しで1回だけ読み、小文字の集合で持つ（`functools.lru_cache`）。照合は `plain.lower()`。
  - 文字の種類の混在は求めない。

### 4.4 cache.py（申請の回数制限・design.md:76）

```python
PASSWORD_RESET_REQUEST_MAX = 3
PASSWORD_RESET_REQUEST_WINDOW = 3600  # 1時間

async def count_password_reset_request(email_lower: str) -> int:
    """email（小文字）のハッシュ単位で申請回数を数え、今回を含む回数を返す。Redis 不通時は 0（既存の auth と同じく通す）。"""
```

- キーは `pw_reset_req:{sha256(email_lower) の hex 先頭 32 文字}`。初回の incr で expire 3600。ユーザーが存在するかどうかに関係なく数える。

### 4.5 auth_mail.py（新設・再設定メール）

```python
def send_password_reset_email(to_addr: str, reset_url: str) -> None:
    """BackgroundTasks から呼ぶ同期関数。例外は外に出さずログに残す（応答はもう返っている）。"""
```

- 送信は `mail_config.smtp_settings()` で設定を取り、`smtplib.SMTP(host, port, timeout=15)` → `starttls()` → `login()` → `send_message()`（既存の email_sender.py と同じ手順）。
- 設定が None なら `[auth_mail] SMTP not configured, skipping password reset mail` とだけログに出す。
- **ログ・例外文に `reset_url`・鍵・宛先の全文を出さない**（宛先は `@` の前を伏せた形、例 `t***@gmail.com`）。
- 件名: `【Sales Anchor】パスワード再設定 / Password reset`
- 本文（プレーンテキスト・UTF-8・日本語→英語の順。差し込みは `reset_url` だけ）:

```
Sales Anchor のパスワード再設定の申請を受け付けました。
下のリンクから 30 分以内に新しいパスワードを設定してください。

{reset_url}

このリンクは 1 回だけ使えます。
心当たりがない場合は、このメールを破棄してください。パスワードは変わりません。

---------------------------------------------
We received a request to reset your Sales Anchor password.
Please set a new password within 30 minutes using the link below.

{reset_url}

This link can be used only once.
If you did not request this, please ignore this email. Your password will not change.
---------------------------------------------

Sales Anchor
```

- `reset_url` は `f"{self_tokens.rp_origin()}/reset-password?token={raw}"`（画面は便4 で作る。便3 の間はリンク先の画面はまだ無い）。

### 4.6 routers/auth.py（2つの口）

共通: 2つとも `_require_app_origin(request)` を通す（design.md:69）。`_require_issuance_enabled()` は**通さない**（design.md:103。Firebase のままでも動く）。

**`POST /password-reset/request`**（入力 `{"email": EmailStr}`）
1. `_require_app_origin`
2. `email = data.email.strip().lower()`。`count_password_reset_request(email)` が `PASSWORD_RESET_REQUEST_MAX` を超えたら 429 `too_many_attempts`
3. `SELECT id, tenant_id, email, is_active FROM public.users WHERE lower(email) = :email`
4. 送る条件: 行がある・`is_active` が真・**送信許可の判定**（下）を通る。条件を満たさなければ 5〜6 を飛ばす
5. 同じ人の未使用の reset 鍵を `used_at = now` で使えなくする → `raw = secrets.token_urlsafe(32)` を作り、`purpose='reset'`・`token_hash=_hash_token(raw)`・`expires_at=now+30分` で INSERT → commit
6. `background_tasks.add_task(send_password_reset_email, row.email, reset_url)`
7. どの場合も 200 `{"status": "accepted"}`（存在・停止・許可外の区別を応答に出さない）

送信許可の判定（design.md:156・審査 MEDIUM-6）:
- `self_tokens.auth_provider() == "self"`（便4 で切替後）なら全員に送る
- それ以外（今の firebase）は、環境変数 `AUTH_PASSWORD_RESET_ALLOWLIST`（カンマ区切り・前後の空白を除き小文字で比較）に載った email だけ。**未設定・空なら誰にも送らない**（設定漏れで実ユーザーに届かない側に倒す）

**`POST /password-reset/confirm`**（入力 `{"token": str(1〜256文字), "new_password": str(1〜1024文字)}`）
1. `_require_app_origin`。`check_auth_rate_limit(ip)` が真なら 429
2. `check_password(new_password)` が理由を返したら 422 `{"detail": <理由のコード>}`（鍵の照合より前。鍵を消費しない）
3. `UPDATE public.password_reset_tokens SET used_at = :now WHERE token_hash = :h AND used_at IS NULL AND expires_at > :now RETURNING user_id, purpose`（1文で消費するので、同じ鍵を同時に2回使っても1回しか通らない）
4. 行が無い → `record_auth_failure(ip)` → 400 `invalid_or_expired_token`（無い・期限切れ・使用済みを区別しない）
5. `SELECT id, tenant_id, is_active FROM public.users WHERE id = :uid`。`is_active` が偽なら commit（鍵は消費済みのまま）して 400 `invalid_or_expired_token`
6. `hash_password` は `asyncio.to_thread` で呼ぶ → `UPDATE public.users SET password_argon2_hash = :h, password_changed_at = :now, failed_login_count = 0, locked_until = NULL WHERE id = :uid`
7. その人の有効な更新用トークンを全部失効: `UPDATE public.auth_refresh_tokens SET revoked_at = :now WHERE user_id = :uid AND revoked_at IS NULL`
8. `record_audit_log(db, tenant_id=row.tenant_id, user_id=row.id, action="update", table_name="users", record_id=row.id, new_data={"event": "password_reset_confirmed", "purpose": purpose})`（パスワード・鍵は入れない）
9. commit → 200 `{"status": "password_updated"}`。自動ログインはしない（トークンも Cookie も出さない）

### 4.7 conftest.py（F11）

- `public.password_reset_tokens` → `password_reset_tokens` の置換を :182-183 の並びに足す
- :1194-1208 の並びに SQLite 版の表を足す（BYTEA→BLOB、BIGSERIAL→INTEGER PRIMARY KEY AUTOINCREMENT、`token_hash` UNIQUE、`purpose` の CHECK も同じ値で付ける）

### 4.8 設定の渡し口（危険パス）

`.github/workflows/deploy.yml`:
- :258-283 の sed 削除に次の 7 行を足す（`-e '/^COMPOSE_FILE=/d'` の前）: `SMTP_HOST`・`SMTP_PORT`・`SMTP_USER`・`SMTP_PASSWORD`・`MAIL_FROM`・`CONTACT_NOTIFY_EMAIL`・`AUTH_PASSWORD_RESET_ALLOWLIST`
- :291-316 の heredoc に同じ 7 行を `KEY=${{ secrets.KEY }}` の形で足す（`COMPOSE_FILE=` の行の前）
- コメント1行: `# ADR-1013 便3: メール送信（mail_config.py が読む）と再設定の送信許可。未登録の Secret は空文字＝送らない`

`docker-compose.yml`:
- backend の `environment:`（:65-124。ロールバック経路のため）に 7 行: `SMTP_HOST=${SMTP_HOST:-}`・`SMTP_PORT=${SMTP_PORT:-587}`・`SMTP_USER=${SMTP_USER:-}`・`SMTP_PASSWORD=${SMTP_PASSWORD:-}`・`MAIL_FROM=${MAIL_FROM:-}`・`CONTACT_NOTIFY_EMAIL=${CONTACT_NOTIFY_EMAIL:-}`・`AUTH_PASSWORD_RESET_ALLOWLIST=${AUTH_PASSWORD_RESET_ALLOWLIST:-}`
- celery-worker の `environment:`（:201-239）に、削除完了通知（`backend/app/tasks/email_tasks.py:44`）が使う 5 行: `SMTP_HOST`・`SMTP_PORT`・`SMTP_USER`・`SMTP_PASSWORD`・`MAIL_FROM`（同じ書き方）
- それぞれコメント1行（既存の「この行が無いと .env に値があっても os.getenv が空になる」と同じ趣旨）

`.env.example`: :50-53 の後に `MAIL_FROM=`・`CONTACT_NOTIFY_EMAIL=`・`AUTH_PASSWORD_RESET_ALLOWLIST=` を足す。
`docs/ENVIRONMENT_VARIABLES.md`: :102-105 の例を SendGrid からさくら（`salesanchor.sakura.ne.jp`・`587`・送信用アドレス・パスワード）に直し、`MAIL_FROM`・`CONTACT_NOTIFY_EMAIL`・`AUTH_PASSWORD_RESET_ALLOWLIST` の行を足す（読み取り口は `backend/app/services/mail_config.py` と書く）。

### 4.9 テスト（先に書いて、修正前に失敗することを確かめる）

`test_mail_config.py`:
- 4つのどれかが空・空白だけ → None／4つそろう → 値が入る／`SMTP_PORT` が空・`abc` → 587／`CONTACT_NOTIFY_EMAIL` が空 → `support@salesanchor.jp`／`repr(settings)` にパスワードが出ない

`test_password_policy.py`:
- 14 文字は too_short・15 文字は通る・64 文字は通る・65 文字は too_long・一覧の先頭の語（大文字にしたもの）は too_common・一覧の件数が README の件数と一致

`test_password_reset.py`（`test_self_auth.py` の fixture の作り方に合わせる。送信関数は patch して呼ばれた引数だけ見る）:
1. 許可リストに載った使用中の人 → 200・鍵が1行（purpose=reset・期限 30 分）・送信関数が1回呼ばれ、URL が `https://app.salesanchor.jp/reset-password?token=` で始まる
2. 許可リストが空（AUTH_PROVIDER=firebase）→ 200・鍵 0 行・送信 0 回
3. 存在しない email・`is_active=false` → 200・同じ本文・鍵 0 行・送信 0 回
4. `AUTH_PROVIDER=self` なら許可リストが空でも送る
5. 4 回目の申請 → 429（存在しない email でも同じ）
6. Origin が違う → 403（request・confirm とも）
7. 2 回申請すると、1 回目の鍵は使えない（confirm で 400）
8. confirm 成功 → 200・`password_argon2_hash` が新しいパスワードで照合できる・`password_changed_at` が入る・`failed_login_count=0`・`locked_until` NULL・その人の更新用トークンが全部 `revoked_at` あり・監査記録 1 行・トークンも Cookie も返さない
9. 同じ鍵で 2 回目 → 400／期限切れ → 400／でたらめな鍵 → 400（3つとも同じ本文）
10. 短いパスワード → 422 `password_too_short`・鍵は未使用のまま（`used_at` NULL）
11. purpose=invite の鍵でも confirm できる
12. `AUTH_PROVIDER=firebase`・`AUTH_JWT_SECRET` 未設定でも 2 つの口が 404 にならない

## 5. 確かめ方（担当が実行し、生の最終行を報告に貼る）

1. §4.9 のテストを先に書き、修正前に失敗することを確かめる（最終行を貼る）
2. 修正後: `cd backend && python -m pytest -q tests/test_mail_config.py tests/test_password_policy.py tests/test_password_reset.py tests/test_self_auth.py tests/test_po_mailer.py tests/test_email_tasks.py tests/test_event_loop_nonblocking.py` が全件成功
3. `cd backend && python -m pytest -q tests -k "auth or mail or contact"` の最終行（PostgreSQL 実機必須の error は件数とテスト名を書く）
4. `git grep -n 'os.getenv("SMTP_\|os.getenv("MAIL_FROM\|os.getenv("CONTACT_NOTIFY' -- backend/app` が `backend/app/services/mail_config.py` 以外 0 件（mail_config は `_env` 経由なので 0 件でもよい）
5. `docker compose -f docker-compose.yml config` が成功し、backend に 7 つ・celery-worker に 5 つの名前が出る（値は空でよい。出力は伏せずに件数だけ報告）
6. `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deploy.yml'))"` が成功。追加した 7 名が sed 削除と heredoc の両方に 1 回ずつ（`grep -c` で各 2）
7. `git diff origin/main...HEAD --name-only` が §3 の一覧と一致

## 6. 分岐ごとの対処

| 状況 | 対処 |
|---|---|
| SecLists の一覧が 2 MB を超える・取得できない | 取り込まず `BLOCKED:`（設計者へ戻す） |
| 追加テストが修正前でも通る | テストが的外れ。`NEEDS_DECISION:` |
| `test_po_mailer.py` などの既存テストを変えないと通らない | 変えずに `NEEDS_DECISION:`（動きを変えてしまっている） |
| deploy.yml に .env を作る場所が :258-316 以外にもある（`grep -n "ENV_EOF"` が 2 行より多い・別の heredoc がある） | 足さずに `NEEDS_DECISION:` |
| `record_audit_log` が SQLite のテストで動かない | 既存テストの監査の差し替え方を探して合わせる。見つからなければ `NEEDS_DECISION:` |
| BackgroundTasks を使うと既存の依存（`get_db` の後始末）と順番がぶつかる | 送信関数は DB に触らない形にしてあるので、ぶつかった場合は `BLOCKED:` |
| §3 以外のファイルを触る必要が出た | 止まって `NEEDS_DECISION:` |
| フックに止められた | 言い換えて再試行しない。`BLOCKED:` |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| SMTP の設定を読むのは mail_config.py の1か所 | §5-4 の grep が 0 件 |
| 未設定・空文字では送らずログだけ（今と同じ） | test_mail_config・既存の test_po_mailer の idle テスト |
| 再設定は、許可リストの人・使用中の人にだけ届き、他は同じ応答で何も起きない | test_password_reset 1〜4 |
| 申請は email ごと 1 時間 3 回まで | test_password_reset 5 |
| 鍵は 1 回だけ・30 分だけ使え、確定でその人の他の端末のログインが切れる | test_password_reset 7〜9 |
| パスワードは 15〜64 文字・一覧に載るものは拒否 | test_password_policy・test_password_reset 10 |
| 本番のログインの動きは変わらない | 反映後、login（正しい形の本文）が 404・logout（トークンなし）が 401 のまま |
| 設定が backend・celery-worker・ロールバック経路のすべてに渡る | §5-5・§5-6 |
| K5（反映後・§8 ④）: 試験用アドレスの Gmail 受信箱に届き、SPF・DKIM・DMARC が pass | PO が Gmail の「メッセージのソースを表示」で確認 |

## 8. 反映の順番と PO の作業

① **コードと渡し口の反映**（このカードの PR）: Opus が GO 記録を書いてマージ → deploy。Secret が未登録なので値は空 → 何も送られない。反映後に §7「本番のログインの動きは変わらない」と、本番 backend・celery-worker に 7／5 の名前が空で入っていることを確かめる（値は表示しない）。

② **PO の GUI 作業**（さくらのコントロールパネル・GitHub）:
1. 送信に使うアドレスを決める。おすすめは `support@salesanchor.jp`（問い合わせ通知・削除完了通知の差出人と同じにする）。さくらに無ければ作る。**パスワードには `$`・`#`・引用符・空白を使わない**（.env の読み取りで壊れるため）
2. さくらで salesanchor.jp の DKIM を有効にし、表示された TXT レコードを DNS（ns1.dns.ne.jp＝さくらのドメイン設定）に登録する
3. DNS に `_dmarc.salesanchor.jp` の TXT `v=DMARC1; p=none; rua=mailto:<1 のアドレス>` を登録する
4. 試験用の Gmail アドレスを1つ用意する（使用中の 10 人とは別）
5. GitHub の Secrets に登録する: `SMTP_HOST`=`salesanchor.sakura.ne.jp`、`SMTP_PORT`=`587`、`SMTP_USER`=1 のアドレス、`SMTP_PASSWORD`=1 のパスワード、`MAIL_FROM`=1 のアドレス、`AUTH_PASSWORD_RESET_ALLOWLIST`=4 の Gmail アドレス、`CONTACT_NOTIFY_EMAIL`=問い合わせ通知を受けたいアドレス（空なら support@salesanchor.jp）
6. 終わったら、Opus に 4 の Gmail アドレスを知らせる

③ **設定の反映**: deploy は main への push でしか動かない（F7）。Opus が handoff.md の更新 PR（docs のみ）をマージして deploy を走らせる。反映後、本番 backend に `SMTP_HOST` が入ったこと（値は件数だけ）を確かめる。

④ **K5 の確認**:
1. 試験ユーザーを本番の public.users に1人作る（tenant 6 `tenant-review`・email＝② 4 の Gmail・`is_active=true`・パスワードなし。design.md:156）。本番データの書き込みなので、Opus が直前の状態を記録してから行う
2. Opus が本番 API に `POST /api/v1/auth/password-reset/request`（Origin ヘッダ付き）を1回送る
3. PO が Gmail の受信箱（迷惑メールではない）に届いたこと、「メッセージのソースを表示」で SPF・DKIM・DMARC が PASS であることを確かめる
4. 届かない・FAIL のときは、さくらの送信ログと国外IPフィルター（判断メモ §3）を確かめる。直らなければ Secret の `SMTP_HOST` を空にして再 deploy（送信停止）

## 9. 戻し方

- 送信だけ止める: Secret の `SMTP_HOST`（または `MAIL_FROM`）を空にして deploy → mail_config が None を返し、3つの既存通知と再設定メールはログだけになる
- 全部戻す: この PR の revert を main にマージして deploy。再設定の 2 つの口が消え、設定の読み方が元の3か所に戻る。`password_reset_tokens` の行は残るが使われない（表は便1 のもの）
- 試験ユーザー: `UPDATE public.users SET is_active = false WHERE id = <作った id>`（行は消さない。監査記録が参照するため）

## 10. PR

- ブランチ: release/auth-b3-mail（origin/main 起点）
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon・設計・このカード・ADR-1013・設計仕様書 docs/specs/auth-login/README.md・触るファイル（§3 全件）・削除するファイル なし
- 危険パスを含むため Draft で起票し、`### GO記録`（GO 発行者・日時・HEAD・対象・変更3行サマリ・直前バックアップ確認）を書いてから Ready・マージ
- マージは Opus が CI・Fable 審査を確かめてから行う

## 11. 報告欄（担当が追記）
