# パスワード保存（Argon2id）実測と現状の事実

調査役の記録。本番・製品コードには触れていない。外部サイトは見ていない。
基準: origin/main = `9571ce84e1cee9bd99e50c9e29cc6ed8776eb588`（2026-11-06 取得）

## 1. 実測（C）

### 【事実】測定環境
- 実行場所: クラウド実行環境（本番 VPS ではない）
- nproc: 4
- CPU: Intel(R) Xeon(R) Processor @ 2.10GHz
- メモリ: 16,472,088 kB（約 15.7 GiB、測定前の空き約 15 GiB）
- Python 3.12.3 / `python3.12 -m venv /tmp/a2` / argon2-cffi==25.1.0（argon2-cffi-bindings 26.1.0）
- 方法: 設定ごとに別プロセス。warmup 1 回のあと、hash→verify を 20 回ずつ（パスワードは毎回別）。単位 ms。

### 結果

| # | 設定 (m KiB / t / p) | hash 中央値 | hash 最大 | verify 中央値 | verify 最大 | ピーク RSS (KB) |
|---|---|---|---|---|---|---|
| 1 | 19456 / 2 / 1（現行） | 23.6 | 29.1 | 23.7 | 29.0 | 33,728 |
| 2 | 47104 / 1 / 1 | 44.8 | 52.2 | 44.7 | 63.9 | 61,284 |
| 3 | 65536 / 3 / 4 | 48.4 | 60.5 | 49.5 | 101.2 | 80,128 |
| 4 | 65536 / 2 / 1 | 110.0 | 115.3 | 110.6 | 116.1 | 79,616 |
| 5 | 2097152 / 1 / 4 | 977.0 | 1024.2 | 1070.1 | 1143.7 | 2,111,508 |

- (5) はメモリ 15 GiB あったため測れた（測らなかった項目は無い）。
- 【事実】本番 backend コンテナの上限は 512M・CPU 1.0（下記 2-e）。(5) のピーク約 2.0 GiB はこの上限を超える。測定はこの環境で行っただけで、本番ホストでの実測ではない。
- 【事実】(3) は p=4 で 4 コア使うため、1 コア制限のコンテナでは本測定より遅くなりうる（【未確認】本番での値）。

### 測り方の注記
- `/usr/bin/time` がこの環境に無く（`ls /usr/bin/time` で不存在、apt 導入も未実施）、指示の `time -v` の代わりに、親プロセス（python）から子を 1 つ起動して `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` を読んだ。これは `time -v` の「Maximum resident set size」と同じカーネルの値（KB）。設定ごとに親を作り直しており、設定間で混ざっていない。
- ピーク RSS は python 起動分（約 30MB 前後）を含む。

## 2. リポジトリの事実（origin/main 9571ce84e）

### (a) passwords.py と呼び出し元
`backend/app/auth/passwords.py` 全 39 行。要点:
- :14 `_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)`
- :17 `_DUMMY_HASH = _HASHER.hash(secrets.token_urlsafe(16))`（存在しない人でも同じ時間をかけるダミー）
- :20-21 `hash_password(plain)` / :24-35 `verify_password(stored_hash, plain)`（None・壊れた hash は False、例外は出さない）/ :38-39 `needs_rehash(stored_hash)` = `_HASHER.check_needs_rehash`
- 文書冒頭 :1-5: ADR-1013 便2、OWASP 推奨値、async からは `asyncio.to_thread` で呼ぶこと

呼び出し元（テスト除く）:
- hash_password: `backend/app/auth/recovery_codes.py:66` / `backend/app/discord_gateway/viewer_trial.py:345` / `backend/app/routers/auth.py:484, 685, 781` / `backend/app/routers/viewer.py:290, 395` / `backend/scripts/issue_initial_passwords.py:81` / `scripts/setup_review_tenant.py:462`
- verify_password: `backend/app/auth/recovery_codes.py:99` / `backend/app/routers/auth.py:413, 417, 752, 756, 1588` / `backend/app/routers/viewer.py:186, 188, 279`
- needs_rehash: 呼び出しは `backend/app/routers/auth.py:483` の 1 か所のみ（import は :36）。

**needs_rehash で再ハッシュしているか → している（ログイン経路のみ）。** `auth.py:483-488`: ログイン成功後（失敗カウント解除の UPDATE の直後）、`needs_rehash(...)` が真なら `hash_password` で作り直し `UPDATE public.users SET password_argon2_hash` で保存。
- 【事実】`routers/viewer.py` の viewer ログイン（:186-188）には needs_rehash の呼び出しは無い（grep で該当なし）。
- 【事実】`auth.py:1359` 付近の別のログイン完了経路（failed_login_count を 0 にする UPDATE）の近くに needs_rehash の呼び出しは無い（grep の結果は :483 のみ）。この経路がパスワード照合を伴うかは【未確認】。

### (b) pepper・HIBP・pwned・common-passwords・password_policy
- pepper: コード中に無し。`git grep -i pepper -- backend ':!backend/tests'` の一致は `backend/app/auth/data/common-passwords.txt` の中の単語（drpepper 等）だけ。
- HIBP / pwned: backend 配下（tests 除く）に該当なし。
- common-passwords: `backend/app/auth/data/common-passwords.txt`（99,840 行、README は `data/README.md`）
- password_policy: `backend/app/auth/password_policy.py`
  - :11-12 `MIN_LENGTH = 15` / `MAX_LENGTH = 64`（文字数）
  - :17-21 一覧を初回に 1 回読み、小文字の frozenset で保持
  - :24-32 `check_password`: 短い→`password_too_short`、長い→`password_too_long`、小文字化して一覧にあれば `password_too_common`。文字種の混在は求めない（:4）
  - 照合件数: 一覧の 99,840 行（空行除去・重複除去前の行数。frozenset の実件数は【未確認】）
  - 使用箇所: `routers/auth.py:656, 777` / `routers/viewer.py:284, 366` / `discord_gateway/viewer_trial.py:334`

### (c) ログイン失敗の回数制限・ロック
- 口座単位: `backend/app/auth/self_tokens.py:29-30` `LOGIN_FAIL_LIMIT = 10`、`LOGIN_LOCK_DURATION = timedelta(minutes=15)`。`routers/auth.py:308-330` `_count_login_failure` が `users.failed_login_count` を +1 し、上限で `locked_until` を設定して count を 0 に戻す。ロック中判定 `auth.py:407-408`。成功時に解除 `auth.py:478`（他に :690, :788, :1359）。
- IP 単位（Redis）: `backend/app/cache.py:307-308` `AUTH_FAIL_MAX = 10`、`AUTH_FAIL_LOCKOUT_TTL = 900`（15 分）。`check_auth_rate_limit`（:311、Redis 不通時は fail-open :324）、`record_auth_failure`（:329-）。呼び出し `routers/auth.py:392, 653, 734, 1082, 1101, 1562` ほか。
- 全体の rate limit ミドルウェア: `backend/app/middleware/rate_limit.py:30, 34` 認証済み 300 回/分、未認証 IP 60 回/分。
- リカバリコード: `backend/app/auth/devices.py:38` `RECOVERY_MAX_FAILED_ATTEMPTS = 5`。
- slowapi: backend 配下に該当なし。

### (d) bcrypt
- `backend/requirements.txt:10` `bcrypt==4.2.1`
- 利用箇所は `backend/app/routers/bots.py:18` (import)・`:59` `bcrypt.hashpw(..., bcrypt.gensalt(rounds=12))`（bot の API キー用）の 1 か所のみ。`backend/app/schemas/bot.py:7`・`migrations/020_...sql:39` は同じ bot の api_key_hash の記述。
- パスワード（ユーザー）の保存には使われていない（passwords.py は argon2 のみ）。
- 【事実】`bcrypt.checkpw` は backend 配下の grep で見つからない（bot の API キー照合がどこで行われるかは【未確認】）。
- 補足: `.github/workflows/qa-smoke.yml:30`・`scripts/qa/reset-tenant.sh:21`・`scripts/qa/seed-tenant.sql:24` に「bcrypt 済 password hash (fallback)」というコメントがある。

### (e) 本番 backend の worker 数と CPU/メモリ
- worker 数: `backend/Dockerfile:39` `CMD ["uvicorn", "app.main:app", ..., "--workers", "1"]`。:37-38 に「workers=1: ADR-081 C項」。docker-compose.yml の backend に command の上書きは無く、WEB_CONCURRENCY・gunicorn の設定も無い（grep で該当なし）。
- 制限: `docker-compose.yml:173-177`（backend、:63 開始）`deploy.resources.limits` で `memory: 512M` / `cpus: "1.0"`。
- 【未確認】本番ホストが実際にこの compose をそのまま使っているか、ホストの実 CPU 数・メモリ（本番へは触れていない）。
- 【事実】別途 `docker-compose.ai-reader*.yml` 等は ai 用で、backend ではない。

## 3. 【未確認】まとめ
- 本番ホストでの Argon2 の所要時間（本測定はクラウド環境）
- 本番の実 CPU・メモリ
- common-passwords.txt の重複除去後の件数
- viewer ログイン・auth.py:1359 付近の経路での再ハッシュ要否
- bot API キーの照合方法
