# 実装カード — S5 接続元 IP の決め方を 1 つにする

**設計**: docs/handoff/s5-client-ip/design.md（審査 APPROVE: docs/handoff/s5-client-ip/review-opus.md）　**根拠**: docs/handoff/s5-client-ip/recon.md
**ブランチ・作業場所**: release/s5-client-ip-ssot（/Users/tanizawashingo/worktrees/salesanchor/release-s5-client-ip-ssot）
**承認**: 2026-10-16 PO「y」（S5 着手）＋ ccopusgo 委任。区分 B（危険パスなし）。

## 手順（この順で）

1. **赤を確認**: 先に backend/tests/test_client_ip.py の T5（下記）だけを書き、変更前のコードで走らせて落ちることを確認する。出力を /tmp/CC報告ファイル/s5-ip/impl/t5-red.txt に保存。
2. backend/app/client_ip.py を新規作成（design §2 のコードそのまま）。
3. 下表の置き換え。
4. T1〜T4・T6 と T7 を書き、design §5 の試験一式を走らせて全部緑にする。出力を /tmp/CC報告ファイル/s5-ip/impl/ に保存。
5. K1 の 2 つの grep を走らせ、件数を保存（0 件・1 件）。
6. コミット（コード＋試験のみ）。

## 置き換え（変更前 → 変更後）

| 場所（行は 2026-10-16 時点で確認済み） | 変更前 | 変更後 |
|---|---|---|
| backend/app/auth/dependencies.py:70-75 | `def _get_client_ip(request: Request) -> str:` …（X-Forwarded-For 先頭 → client.host → "unknown"） | 定義を削除。import 群に `from app.client_ip import get_client_ip as _get_client_ip` を足す。:152 の呼び出しは変えない |
| backend/app/middleware/rate_limit.py:53-57 | `def _get_client_ip(...)` 定義 | 削除。`from app.client_ip import get_client_ip` を足す |
| backend/app/middleware/rate_limit.py:104 | `client_ip = _get_client_ip(request)` | `client_ip = get_client_ip(request)` |
| backend/app/middleware/audit.py:64-69 | `def _get_client_ip_from_request(...)` 定義 | 削除。`from app.client_ip import get_client_ip` を足す |
| backend/app/middleware/audit.py:151・:194 | `client_ip = _get_client_ip_from_request(request)` | `client_ip = get_client_ip(request)` |
| backend/app/middleware/session_guard.py:58-62 | `def _get_client_ip(...)` 定義 | 削除。`from app.client_ip import get_client_ip` を足す |
| backend/app/middleware/session_guard.py:161 | `client_ip = _get_client_ip(request)` | `client_ip = get_client_ip(request)` |
| backend/app/routers/viewer.py:53-60 | `def _client_ip(...)` 定義（X-Real-IP → client.host → "unknown"） | 削除。`from app.client_ip import get_client_ip` を足す |
| backend/app/routers/viewer.py:132 | `ip = _client_ip(request)` | `ip = get_client_ip(request)` |
| backend/tests/test_security_hardening.py:555・:584・:613 | `"X-Forwarded-For": <値>` | `"X-Real-IP": <同じ値>` |

削除後に使われなくなった import（例: `Request` が他で使われていない場合）だけを消す。他の行は触らない。

（追補 2026-10-16: backend/tests/test_real_redis_lockout.py:137 も `"X-Forwarded-For"` → `"X-Real-IP"`。CI で走る試験だった。）

## 新しい試験

backend/tests/test_client_ip.py（DB 不要。FakeRedis は backend/tests/test_viewer_api.py:66 と同じ形をこのファイル内に置き、monkeypatch で `app.cache._redis` に差す）:

- T1: X-Real-IP=10.3.0.1・X-Forwarded-For=6.6.6.6 → "10.3.0.1"
- T2: X-Real-IP 無し・X-Forwarded-For=6.6.6.6・client=("192.0.2.5", 1) → "192.0.2.5"
- T3: X-Real-IP="evil" / 60 文字 → client.host
- T4: X-Real-IP 無し・client 無し → "unknown"
- T5（K2）: 実物の check_auth_rate_limit・record_auth_failure を FakeRedis で動かす。get_current_user（backend/app/auth/dependencies.py）を使う最小アプリまたは既存の保護経路へ、検証が失敗する偽 Bearer トークン、X-Real-IP 固定・X-Forwarded-For 毎回別の値で 10 回送る（各回 401）→ 11 回目が 429。検証失敗の作り方は backend/tests/test_security_hardening.py の TestAuthDependency429 の差し替え方に合わせる
- T6: AuditMiddleware を最小アプリに付け、`app.middleware.audit.AsyncSessionLocal` を差し替えて INSERT の引数を拾う。X-Real-IP=10.3.0.1・X-Forwarded-For=203.0.113.77 で /api/v1/auth/x に送る → client_ip が "10.3.0.1"

backend/tests/test_security_hardening.py に追加:

- T7: SessionGuard で X-Real-IP は同じ・X-Forwarded-For だけを 5 分以内に別プレフィックスへ変えても 401 にならない

## 走らせる試験（ローカル、backend で）

`python3 -m pytest tests/test_client_ip.py tests/test_security_hardening.py tests/test_viewer_api.py tests/test_event_loop_nonblocking.py tests/test_smoke_auth_least_privilege.py tests/test_self_auth.py tests/test_password_reset.py -q --tb=short --no-cov -p no:cacheprovider`（DB が要る試験が skip/エラーになる場合はそのまま報告。全件は CI）

## 触らない

nginx/nginx.conf、backend/app/routers/line_import_devices.py、backend/app/cache.py、migrations/、.github/、frontend/、docs/（このカード以外の文書も）。

## 想定分岐（迷ったら止めて報告）

- 行番号がずれている／定義の本文が recon §1 と違う → 止めて NEEDS_DECISION。
- T5 が変更前のコードで落ちない（既に 429 になる） → 止めて報告（設計の前提が違う）。
- 循環 import が起きる → 止めて報告。
- 既存試験が赤になる → 原因の生出力を保存して報告（試験を書き換えて緑にしない。上表の 3 行を除く）。
