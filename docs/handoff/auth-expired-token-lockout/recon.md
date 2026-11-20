# 期限切れの札で接続元が止まる件 — 現在地（recon）

調べた日: 2026-11-20〜21（JST）。コードは origin/main `77971367b` を読んだ。本番は reader 鍵の道（ADR-1024）で読んだ。

## 1. 既存の ADR（`git grep -il -E "brute|ブルートフォース|record_auth_failure|AUTH_FAIL_MAX|auth_fail_ip" -- docs/adr docs/specs` の結果）

- docs/adr/ADR-127-auth-lockout-bystander-fix.md — 接続元の回数止め（IP ロック）を札の一時記憶の確認の後ろに回した。回数止めの本体（`check_auth_rate_limit`・`record_auth_failure`）は変えていない。
- docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:24 — 口座単位で 10 回失敗すると 15 分止める（これは口座の止め。接続元の止めとは別）。
- docs/adr/FEATURE-INDEX.md に回数止めの行は無い（`grep -n -i -E "brute|ブルート|レート|rate"` で 0 件）。
- 期限切れの札を回数に数えるかを決めた ADR は無い。

## 2. 起きたこと（本番の記録 `ai_ro.public__auth_events`・接続元は md5 の先頭 8 字で伏せた `d7c69f3f`）

| 時刻（JST 2026-11-20） | 行き先 | 結果 |
|---|---|---|
| 23:39:15.84〜23:39:18.44 | 普通の API 11 回（conversations/stream・events/stream・staff/me×4・me/permissions×2・conversations ほか） | 11 回とも 401 |
| 23:39:19.88 | /api/v1/auth/refresh | 200（user_id 3） |
| 23:39:20.00〜23:39:20.40 | auth/recovery-codes/status・push-public-key・devices・passkeys ほか 6 回 | すべて 429 |
| 23:39:26.25 | /api/v1/auth/logout | 200 |
| 23:39:29.41・23:39:31.49 | /api/v1/auth/login | 429 `rate_limited` |

- 端末の名乗り: `Mozilla/5.0 (Linux; Android 10; K)`。この接続元の 24 時間の記録はこの 21 行だけ。
- 過去 30 日の 429 は 2026-11-20 の 8 件（接続元 1 つ）だけ。

## 3. 札が期限切れだった根拠（事実）

- 札の寿命は 900 秒（backend/tests/test_self_auth.py:132 `expires_in == 900`）。
- この Android の札の組（family 先頭 `45dda681`・機械 12）の更新札は 2 本だけ。
  - id 5379: 作成 2026-11-19 01:48:44（ログイン）・使用 2026-11-20 23:39:19
  - id 6034: 作成 2026-11-20 23:39:19（上の 200 の取り直し）
- つまり 23:39:15 に送られた札は、2026-11-19 01:48 に出たものしか無い。約 46 時間前で、900 秒を過ぎている。
- 札の秘密（AUTH_JWT_SECRET）を入れ替えた記録は、2026-11-17 以降の git log に無い（`git log --since=2026-11-17 -i --grep="AUTH_JWT_SECRET\|secret rotat\|鍵の入れ替え"` で 0 件）。サーバーの値そのものは読んでいない（未確認）。

## 4. 回数の数え方（コード）

- backend/app/cache.py:307-308 — `AUTH_FAIL_MAX = 10`・`AUTH_FAIL_LOCKOUT_TTL = 900`。
- backend/app/cache.py:311-325 — `check_auth_rate_limit`。数が 10 以上なら止める。
- backend/app/cache.py:328-339 — `record_auth_failure`。1 回目に 900 秒の期限を付け、あとは数を足すだけ。
- backend/app/auth/dependencies.py:47-52 — `_reject_self_token` は必ず `record_auth_failure` を呼んでから 401 を返す。
- backend/app/auth/dependencies.py:58-64 — 札の読み解き（`self_tokens.decode_access_token`）で出た `JWTError` は、種類を分けずに `_reject_self_token` に渡す。期限切れ（`ExpiredSignatureError`）もここで数えられる。
- backend/app/auth/dependencies.py:220-224 — 一時記憶に無い札は、読み解きの前に回数止めを見て、10 以上なら 429。
- backend/app/routers/auth.py:395-397 — ログインも同じ回数止めを見て 429 `too_many_attempts`。
- 数えないもの: ログアウト済みの札（dependencies.py:187-191）・失効した組の札（同 :197-201）・Authorization の無い頼み・/auth/refresh の 401（routers/auth.py:514-531 は `record_auth_failure` を呼ばない）。

## 5. 札の部品の確かめる順番（公式の中身）

- backend/requirements.txt:17 `python-jose[cryptography]==3.5.0`。
- PyPI の python_jose-3.5.0 の `jose/jwt.py`:159 で `jws.verify`（署名の確認）を先にし、:174 の `_validate_claims` の中（:496-497）で期限を見る。署名が合わないと `JWTError` になり、期限の確認まで進まない。
- `jose/exceptions.py`:25 `class ExpiredSignatureError(JWTError)`。
- 自社の `decode_access_token`（backend/app/auth/self_tokens.py:111-120）は、kid が今の秘密か一つ前の秘密に合わないと、読み解く前に `JWTError("unknown kid")` を出す。
- よって `ExpiredSignatureError` が出る札は「自社の秘密で署名された本物で、期限だけが切れた札」に限られる。
- Context7（/websites/deepwiki_mpdavis_python-jose）も同じ例外の階層を示す。

## 6. ふだんの 401 の量（14 日・`event_type='auth_failure' AND status_code=401`）

- 1 日 8〜145 件。同じ接続元で 15 分に 10 件以上の区切りは 169 個。そのうち 429 になったのは 11/20 の 1 回だけ。
- 169 個の中身は /auth/refresh の 401 が 1027 件で最多。これは数えない道（§4）。普通の API の 401 は札を持たない頼みが多いとみられるが、記録に札の有無の列は無い（未確認）。

## 7. 既存の試験

- backend/tests/test_self_auth.py:340-455 — `get_current_user` の自社の札の試験。`record_auth_failure` は AsyncMock で置き換えているが、呼ばれた回数は見ていない。期限切れの札の試験は無い。
- backend/tests/test_security_hardening.py:77-100 — 回数止めの数のしきい値の試験。
- backend/tests/test_real_redis_lockout.py — 本物の Redis が要る手動の試験（CI では動かない・ファイル冒頭の説明）。
