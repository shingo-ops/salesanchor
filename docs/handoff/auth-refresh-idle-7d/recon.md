# recon: 7 日使わなければログインし直し（ADR-1084）

調べた版: origin/main 5e01ab36c（2026-11-21）。

## 1. 既存 ADR の検索

- `git grep -n -i -E "30 ?日|30 days|REFRESH_ABSOLUTE|放置|idle|自動ログアウト|auto.?logout" origin/main -- docs/adr docs/specs/auth-login` → 札の寿命に触れるのは docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md:37（「refresh 30 日・アクセストークン 900 秒」の記述）だけ。使っていない日数で切る決まりの ADR は 0 件。
- 関連: docs/adr/ADR-1013-self-hosted-auth-and-passkey.md（自社ログイン。札の表は public.users.id にだけぶら下げる・:23）、docs/adr/ADR-1083-expired-token-not-counted-as-bruteforce.md（期限切れの札を回数止めに数えない）。
- docs/specs/auth-login/README.md に札の寿命の記述は無い（同じ grep で 0 件）。

## 2. 今の仕組み（事実）

- 入館証（アクセストークン）15 分: /Users/tanizawashingo/salesanchor/backend/app/auth/self_tokens.py:23 `ACCESS_TOKEN_TTL_SECONDS = 900`
- 引換券（更新トークン）は組の作成から 30 日で必ず切れる: backend/app/auth/self_tokens.py:24 `REFRESH_ABSOLUTE_TTL = timedelta(days=30)`、:167-168 `expires_at = family_start + REFRESH_ABSOLUTE_TTL`
- 取り替え: backend/app/auth/self_tokens.py:208-215 の UPDATE 1 文で、今の券を失効させて取り出す。条件は `token_hash = :h AND revoked_at IS NULL AND expires_at > :now`。成功すると :248-255 で同じ組の新しい券を出す（新しい券の created_at は今）。
- 使い回しの検知: backend/app/auth/self_tokens.py:217-232。取り出せず、券が失効済みなら組ごと失効させる。失効していない券（期限切れなど）なら組は触らず None。
- 使っていない日数で切る仕組みは無い（self_tokens.py に idle・inactivity の語 0 件）。
- 表の形: migrations/20261013_160000_add_self_hosted_auth_tables.sql:68-81。`created_at TIMESTAMPTZ NOT NULL DEFAULT now()` がある。新しい列は要らない。
- 機械の覚え: backend/app/auth/devices.py:31-32 `DEVICE_COOKIE_MAX_AGE = 180 * 24 * 3600`・`DEVICE_IDLE_DAYS = 180`。ログイン時は backend/app/routers/auth.py:431・:1190 で find_trusted_device（devices.py:185-201・取り消されておらず 180 日以内に使った機械か）を見る。引換券とは別の Cookie（sa_device）なので、7 日でログインし直しても、180 日以内に使った機械なら「知らない機械」の許可は要らない。
- 画面: frontend/src/lib/auth/selfAuth.ts:199 で更新が 401 なら expireSession（:68-72）→ ログイン画面。画面の変更は要らない。
- 今ある試験: backend/tests/test_self_auth.py:217（取り替え）・:230（使い回しで組ごと失効）・:257（30 日で切れる）・:270（取り替えで期限が延びない）。

## 3. 本番の今の数（reader 鍵・2026-11-21 16:12 JST）

`ai_ro.public__auth_refresh_tokens` で、失効しておらず期限内の券:

| 口座 | 生きている券 | うち 7 日以上使われていない | 最後に使われた時刻（UTC） |
|---|---|---|---|
| 1 | 3 | 3 | 2026-11-09 00:50 |
| 3 | 1 | 0 | 2026-11-21 07:05 |
| 87 | 748 | 419 | 2026-11-21 06:01 |
| 計 | 752 | 422 | |

- 口座 87 は直近 11 日間、毎日 28〜151 回ログインしている（組の作成数）。どの仕組みがログインしているかは、まだ確かめていない。毎回新しい組で入るので、7 日の決まりで止まらない（7 日以上前の券を使い回していない）。
- 7 日の決まりを入れると、422 本の「誰も使っていない券」が使えなくなる。
