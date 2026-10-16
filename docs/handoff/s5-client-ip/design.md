# 設計 — S5 接続元 IP の決め方を 1 つにする（client-ip）

**日付**: 2026-10-16　**根拠**: [recon.md](recon.md)（docs/handoff/s5-client-ip/recon.md）、ADR-127、ADR-1013、ADR-1019　**仕様書**: [docs/specs/client-ip/README.md](../../specs/client-ip/README.md)、KGI [docs/specs/client-ip/kgi.md](../../specs/client-ip/kgi.md)

## 1. 目的（利用者に見える変化）

- 攻撃者が X-Forwarded-For を毎回変えても、ログイン・パスワード再設定の失敗回数制限（10 回で 15 分ロック）をすり抜けられなくなる。
- 監査記録（auth_events・data_access_events）に残る IP が、利用者が書いた値ではなく本当の接続元になる。
- 普通の利用者の体験は変わらない（今も nginx が付ける本当の接続元が X-Forwarded-For の先頭に来ているため、同じ IP が使われる。recon §3）。

## 2. 変更前 → 変更後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 関数 | 同じ本文の写し 4 つ＋viewer.py の 1 つ（recon §1） | 新モジュール backend/app/client_ip.py の `get_client_ip` 1 つ |
| 読む値 | X-Forwarded-For の先頭 → request.client.host → "unknown" | X-Real-IP（IP として正しい形のときだけ）→ request.client.host → "unknown"。X-Forwarded-For は読まない |

新モジュールの中身（実装はこのとおり）:

```python
"""接続元 IP を決める唯一の関数（docs/specs/client-ip/README.md）。

本番の入口は nginx だけで、nginx は backend 向けのすべての経路で
X-Real-IP を本当の接続元（$remote_addr）で上書きする。
X-Forwarded-For は利用者が自由に書けるため読まない。
"""
import ipaddress

from starlette.requests import HTTPConnection


def get_client_ip(request: HTTPConnection) -> str:
    real = (request.headers.get("x-real-ip") or "").strip()
    if real:
        try:
            return str(ipaddress.ip_address(real))
        except ValueError:
            pass
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
```

- X-Real-IP が無いとき（コンテナ内ヘルスチェックが localhost:8000 を直接叩く場合。recon §3）は request.client.host に戻る。
- IP の形でない X-Real-IP は捨てる（45 文字を超える値で監査記録の INSERT が失敗する問題も起きない。recon §5）。

## 3. 触るファイルと変更内容

| ファイル | 変更 |
|---|---|
| backend/app/client_ip.py | 新規（§2 のとおり） |
| backend/app/auth/dependencies.py | :70-75 の `_get_client_ip` 定義を消し、`from app.client_ip import get_client_ip as _get_client_ip` を import 群に足す（routers/auth.py:17 の import と試験 2 件の patch 先 "app.auth.dependencies._get_client_ip" をそのまま使えるようにする。:152 は変えない） |
| backend/app/middleware/rate_limit.py | :53-57 の定義を消し、`from app.client_ip import get_client_ip` を足し、:104 を `get_client_ip(request)` にする |
| backend/app/middleware/audit.py | :64-69 の定義を消し、同じ import を足し、:151・:194 を `get_client_ip(request)` にする |
| backend/app/middleware/session_guard.py | :58-62 の定義を消し、同じ import を足し、:161 を `get_client_ip(request)` にする |
| backend/app/routers/viewer.py | :53-60 の `_client_ip` を消し、同じ import を足し、:132 を `get_client_ip(request)` にする |
| backend/tests/test_security_hardening.py | :555・:584・:613 の `"X-Forwarded-For"` を `"X-Real-IP"` に替える（同じ値）。session_guard の試験を 1 件足す（§5 T7） |
| backend/tests/test_client_ip.py | 新規（§5 T1〜T6） |

触らない: nginx/nginx.conf、backend/app/routers/line_import_devices.py、backend/app/cache.py（回数制限の本体）、backend/tests/test_real_redis_lockout.py（手動実行用）、migrations、deploy.yml、frontend。

## 4. 対象外とその理由

- nginx の X-Forwarded-For を `$remote_addr` で上書きする変更: backend が X-Forwarded-For を読まなくなれば不要。変更は一度に 1 つ。
- 端末登録 backend/app/routers/line_import_devices.py:36（request.client.host）: 本番では nginx の IP（172.20.0.2）になり、全員が同じ IP として数えられている（recon §3）。共通関数に替えると登録の制限の効き方が変わるため、別便で扱う。
- WAF（Cloudflare 等）の導入: 外部 GUI と費用判断が要る。

## 5. 試験（KGI との対応）

backend/tests/test_client_ip.py（DB 不要。Redis は backend/tests/test_viewer_api.py:66 と同じ形の FakeRedis を `app.cache._redis` に差す）:

- T1: X-Real-IP=10.3.0.1・X-Forwarded-For=6.6.6.6 → "10.3.0.1"。
- T2: X-Real-IP 無し・X-Forwarded-For=6.6.6.6・client=("192.0.2.5", 1) → "192.0.2.5"。
- T3: X-Real-IP が "evil" や 60 文字の文字列 → request.client.host。
- T4: X-Real-IP 無し・client 無し → "unknown"。
- T5（K2）: 実物の `check_auth_rate_limit`・`record_auth_failure`（backend/app/cache.py）を FakeRedis で動かし、`get_current_user` を通る保護された経路へ、Firebase 検証が失敗する偽トークン付きで、X-Real-IP は同じ・X-Forwarded-For は毎回違う値で 10 回送る → 11 回目が 429。Firebase 検証の失敗は既存試験（backend/tests/test_security_hardening.py の TestAuthDependency429）と同じ差し替え方で作る。**変更前のコードでこの試験が落ちること（11 回目が 429 にならない）を先に確かめ、出力を保存する。**
- T6: AuditMiddleware を最小アプリに付け、AsyncSessionLocal を差し替えて INSERT の引数を拾う。X-Real-IP=10.3.0.1・X-Forwarded-For=203.0.113.77 で /api/v1/auth/x に送る → 記録される client_ip が "10.3.0.1"。
- T7（test_security_hardening.py に追加）: SessionGuard で、X-Real-IP は同じ・X-Forwarded-For だけを 5 分以内に別プレフィックスへ変えても 401 にならない。

既存の試験はすべて緑のまま（ローカルで backend/tests/test_security_hardening.py・test_viewer_api.py・test_event_loop_nonblocking.py・test_smoke_auth_least_privilege.py・test_self_auth.py・test_password_reset.py・新規 test_client_ip.py を走らせる。全件は CI）。

## 6. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1: X-Forwarded-For を読む箇所 0・関数定義 1 | `git grep -niE "headers\.get\(\s*[\"']x-forwarded-for" backend/app` が 0 件、`git grep -nE "def (_?get_client_ip\|_get_client_ip_from_request\|_client_ip)\(" backend/app` が 1 件（backend/app/client_ip.py） |
| K2: XFF を毎回変えても 11 回目が 429 | T5 が CI で緑。変更前のコードで T5 が落ちた出力を PR に記す |
| K3: 本番で偽の XFF を付けた要求の監査記録の IP が本当の接続元 | 反映後に recon §8 と同じ手順（トークン無し POST /api/v1/auth/logout、偽 XFF 203.0.113.77）で auth_events.client_ip が nginx 記録の接続元と一致。反映前は 203.0.113.77（recon §8） |
| K4: 401・429 が増えない | 反映後の nginx 記録の 1 時間あたり 401・429 件数が基準（recon §6: 3591 行・約 3.2 時間で 401 が 41・429 が 0）を超えない。超えたら中身（経路・接続元）を見て本変更が原因か切り分ける |
| 既存機能 | CI の Backend Tests 全件緑。反映後の backend ログに Traceback・5xx の増加なし |

表の中の `\|` は表の区切りと区別するための書き方。実際に打つときは `|` にする（`\|` のまま `-E` に渡すと 0 件になる）。

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| X-Real-IP が付かない経路があると、全員が nginx の IP として数えられ、1 人の失敗で全員がロックされる | backend 向け 12 location すべてに X-Real-IP があることを確認済み（recon §3）。本番 nginx -T でも同じ。反映後に K3 で実測 |
| 試験の patch 先が消える | dependencies.py に `_get_client_ip` の名前を import で残す（§3） |
| IPv6 の表記が変わる（ipaddress で正規化） | 記録・キーの文字列が変わるだけで、回数制限は 15 分で戻る。nginx の $remote_addr は既に正規形 |

## 8. 戻し方

PR を Revert して再デプロイ。DB・設定の変更は無い。

## 9. 外部・過去事例の参照と我々への応用

- uvicorn 0.34.0 の既定（本番コンテナで実物を確認。recon §3）: proxy_headers は既定で有効、信頼する送り元は既定で 127.0.0.1 だけ。nginx（172.20.0.2）からの要求では X-Forwarded-For を書き換えない。＝アプリ側で X-Forwarded-For を読むと利用者の値をそのまま信用することになる。
- 社内の過去事例: backend/app/routers/viewer.py の閲覧者ログイン（ADR-1019）は既に X-Real-IP だけを読み、backend/tests/test_viewer_api.py:405-409 で X-Forwarded-For を無視することを試験している。本件はこの方式を全体の正本にする。
- 数値を伴う外部の導入事例は使わない（本件は社内の実測で再現と判定ができるため）。

## 維持の仕組み

- 守り手: backend/tests/test_client_ip.py と backend/tests/test_security_hardening.py の T7（CI の Backend Tests で毎回、X-Forwarded-For を読まないこと・回数制限をすり抜けられないことを検証）。
- 正本は backend/app/client_ip.py の 1 関数。新しく接続元 IP が要る箇所はこれを import する（docs/specs/client-ip/kgi.md の運用方針）。
- K1 の 2 つの grep を受入条件として残す。写しが増えたら次の監査で検出する。
- T1〜T7 が CI の Backend Tests で毎回走る。
