# SEC-01 PR-D rate bucket 見直し design

> Issue: #2179  
> Recon: `docs/handoff/security/sec-01-rate-bucket/recon.md`  
> Parent: #2170 / ADR-140 SEC-MASTER  
> 作成日: 2026-06-14  
> 対象: RateLimitMiddleware のbucket選択

---

## 0. KGI

未検証JWT payload emailにより rate limit bucket が任意分散される余地をなくし、入口レート制限の信頼性を高める。

---

## 1. recon要約

| ID | 事実 | 根拠 | design判断 |
|---|---|---|---|
| R1 | RateLimitMiddlewareは署名検証なしでJWT payload emailを読む | `backend/app/middleware/rate_limit.py:41-52` | user bucket判定に使わない。 |
| R2 | emailが取れれば `user:<email>` bucketへ入る | `backend/app/middleware/rate_limit.py:97-103` | 偽JWTでbucket分散可能。 |
| R3 | emailが取れなければ `ip:<client_ip>` bucket | `backend/app/middleware/rate_limit.py:104-109` | 未認証bucketとして維持。 |
| R4 | 認証本体はFirebase検証/MFA/DB照合/tenant検証あり | `backend/app/auth/dependencies.py` | 認証突破問題ではない。 |
| R5 | Nginx rate limitも存在する | `nginx/nginx.conf:6-10` | 即Criticalではないがbackend制御は改善する。 |
| R6 | 正規ユーザー画面は1ページ10〜20リクエスト飛ぶことがある | `backend/app/middleware/rate_limit.py:26-29` | 全IP bucket化は副作用注意。 |

---

## 2. KPI / 受け入れ基準

| KPI | 内容 | 測定方法 | 合格条件 |
|---|---|---|---|
| KPI-D1 | 偽JWTのemailを変えてもrate limit bucketを分散できない | unit test | 偽JWTはuser bucketに入らない |
| KPI-D2 | 署名未検証JWTは認証済みuser bucketとして扱わない | unit test | 未検証BearerはIP bucket |
| KPI-D3 | Authorizationなしと不正Bearerは同じ未認証bucket方針になる | unit test | 同一IPなら同じbucket key系統 |
| KPI-D4 | 署名検証済み/キャッシュ済みtokenのみuser bucketを使える | unit test | `get_cached_jwt()` hit時のみuser bucket |
| KPI-D5 | 正規ユーザーの通常操作で429が増えすぎない設計になっている | smoke/E2E | 主要画面操作で429なし |
| KPI-D6 | 既存Nginx rate limitとの二重制御が破綻しない | config review + smoke | Nginx/Backend双方が期待通り |
| KPI-D7 | bucket選択を単体テストで検証できる | test coverage | bucket selectorのテストあり |

---

## 3. 採用案

**案B: 署名検証済みtoken cacheがある場合だけuser bucketを使い、それ以外はIP bucket。**

理由:

- 偽JWT payload emailによるbucket分散を防げる。
- 既に認証済みの正規ユーザーは、JWT検証cacheを通じてuser bucketを維持できる。
- 初回cache miss時はIP bucketになるが、認証Dependency通過後にJWT cacheが入るため、以後の通常操作ではuser bucketへ寄る。
- Firebase検証をRateLimitMiddleware内で重複実行しない。

---

## 4. 技術How

### 4.1 bucket selectorを分離する

`rate_limit.py` 内にbucket選択helperを作る。

例:

```python
async def _rate_limit_identity(request: Request) -> tuple[str, int, int]:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token:
        cached = await get_cached_jwt(token)
        if cached and cached.get("email"):
            return f"user:{cached['email']}", AUTHED_RATE_LIMIT, AUTHED_WINDOW_SEC

    client_ip = get_trusted_client_ip(request)
    return f"ip:{client_ip}", UNAUTHED_RATE_LIMIT, UNAUTHED_WINDOW_SEC
```

### 4.2 `_decode_jwt_email()` を廃止または用途変更

署名未検証payloadをrate limit bucket決定に使わない。

- 削除する、またはテスト互換のため内部で未使用化。
- audit等のログ用途とは別に扱う。

### 4.3 Redis fail-openとの関係

`get_cached_jwt()` 自体もRedis依存で、Redis不通時はNoneを返す。つまりRedis不通時はIP bucketへ寄る。ただし `_check_rate_limit()` もRedis不通ならPR-C設計通りfail-openする。

PR-Dではfail-open挙動は変えない。PR-Cのmetricsで観測する。

---

## 5. 変更対象ファイル

| ファイル | 変更方針 |
|---|---|
| `backend/app/middleware/rate_limit.py` | 未検証JWT payload decodeによるuser bucket選択を廃止。cached verified JWTのみuser bucket。 |
| `backend/tests/security/test_rate_limit_identity.py` | bucket選択unit test追加。 |
| `docs/handoff/security/sec-01-rate-bucket/implementation.md` | 実装記録。 |

### 触らない

| ファイル | 理由 |
|---|---|
| `nginx/nginx.conf` | PR-Dはbackend bucket選択のみ。 |
| `.github/workflows/deploy.yml` | 不要。 |
| `migrations/` | DB変更なし。 |
| auth dependency | 認証本体は変えない。 |

---

## 6. テスト設計

### unit test候補

1. Authorizationなし → `ip:<trusted_ip>` bucket。
2. 不正Bearer / 偽JWT → `ip:<trusted_ip>` bucket。
3. 偽JWT email A/B を変えてもuser bucketにならない。
4. `get_cached_jwt()` が `{"email": "user@example.com"}` を返す時だけ `user:user@example.com` bucket。
5. `get_cached_jwt()` がNoneならIP bucket。

### コマンド

```bash
python -m pytest backend/tests/security/test_rate_limit_identity.py -q
```

回帰:

```bash
python -m pytest backend/tests -q
```

---

## 7. リスクと対策

| リスク | 内容 | 対策 |
|---|---|---|
| 初回cache miss時に正規ユーザーもIP bucketになる | 認証直後の数リクエストでIP制限を受ける可能性 | Nginx general limitもあり、backend未認証IP 60/min。通常操作で問題が出るかsmoke確認。 |
| Redis不通時はcached JWTが使えない | user bucketへ寄れない | PR-C metricsでfail-open検知。Redis障害時の挙動は別途SEC-08/SEC-02。 |
| `get_cached_jwt()` がblacklistより先に使われる | blacklist済みtokenでもcacheが残る可能性 | rate limit bucket識別に使うだけで認証許可ではない。認証本体のblacklist確認は維持。 |
| user bucketのemail値がcache由来でも古い可能性 | TTL 5分 | rate limit識別のみなので許容。 |

---

## 8. 外部・過去事例の参照と我々への応用

### 事例1: JWTは署名検証前のpayloadを信用しない

JWT payloadはbase64url decodeできるが、署名検証前は攻撃者が任意に作れる。

Sales Anchorへの応用:

- 未検証payloadをrate limitの権限/緩和判定に使わない。
- verified cache hit時だけuser bucketを使う。

### 事例2: rate limitは認証前・認証後で責務が違う

認証前はIPやdevice fingerprintのような外部信号に寄せ、認証後はuser id/email単位で細かく制御するのが一般的。

Sales Anchorへの応用:

- Middleware段階ではverified cacheがなければIP bucket。
- 認証済みと確認できるcacheがあればuser bucket。

### 事例3: セキュリティ改善は正規ユーザー体験とトレードオフ

全IP bucket化は攻撃耐性を上げるが、NAT配下の正規ユーザーを巻き込む。

Sales Anchorへの応用:

- user bucketを完全廃止せず、verified cache条件にする。

---

## 9. Claude Code / Generator への実装ハンドオフ

### 目的

RateLimitMiddlewareで未検証JWT payload emailをuser bucketに使う挙動を廃止し、偽JWTによるbucket分散を防ぐ。

### 実装指示

1. `backend/app/middleware/rate_limit.py` を変更する。
2. `_decode_jwt_email()` によるbucket決定をやめる。
3. Bearer tokenがある場合は `app.cache.get_cached_jwt(token)` を確認する。
4. `get_cached_jwt(token)` がemailを返す場合のみ `user:<email>` bucketを使う。
5. それ以外は `get_trusted_client_ip(request)` による `ip:<ip>` bucketを使う。
6. Firebase検証をmiddleware内で新たに実行しない。
7. fail-open挙動は変更しない。
8. testsを追加する。
9. Nginx/deploy/migrations/scriptsは触らない。

### 受け入れ基準

- KPI-D1〜D7を満たす。
- 偽JWT emailを変えてもbucket分散できない。
- verified cache hit時だけuser bucket。
- 正常系の既存rate limit挙動を壊さない。

### 禁止

- Firebase Admin SDK verifyをRateLimitMiddlewareに追加しない。
- 認証本体を変更しない。
- Redis fail-openを同時変更しない。
- Nginx rate limitを同時変更しない。
