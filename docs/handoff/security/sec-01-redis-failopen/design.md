# SEC-01 PR-C Redis fail-open 検知 design

> Issue: #2177  
> Recon: `docs/handoff/security/sec-01-redis-failopen/recon.md`  
> Parent: #2170 / ADR-140 SEC-MASTER  
> 作成日: 2026-06-14  
> 対象: rate limit / session guard のRedis fail-open検知

---

## 0. KGI

Redis不通時に rate limit / session guard が fail-open する状態を、運用上見逃さない。

---

## 1. recon要約

| ID | 事実 | 根拠 | design判断 |
|---|---|---|---|
| R1 | RateLimitMiddlewareはRedis未接続時にFalseを返し通過させる | `backend/app/middleware/rate_limit.py:69-73` | counter/logを追加。fail-closeにはしない。 |
| R2 | RateLimitMiddlewareはRedis例外時もwarning後Falseで通過 | `backend/app/middleware/rate_limit.py:82-84` | counter/logを追加。 |
| R3 | SessionGuardMiddlewareはRedis未接続時にFalseを返し通過させる | `backend/app/middleware/session_guard.py:92-96` | counter/logを追加。fail-closeにはしない。 |
| R4 | SessionGuardMiddlewareはRedis例外時もwarning後Falseで通過 | `backend/app/middleware/session_guard.py:141-143` | counter/logを追加。 |
| R5 | Prometheus Counter基盤がある | `backend/app/metrics.py:5-12` | `security_fail_open_total` を追加。 |
| R6 | `/metrics` は既に提供されている | `backend/app/metrics.py:60-62` | 新counterは同endpointへ露出。 |
| R7 | Nginx `/metrics` はIP制限あり | `nginx/nginx.conf:218-227` | 既存保護を維持。 |
| R8 | token blacklistもRedis障害時fail-open | `backend/app/cache.py:86-101` | SEC-02へ引き継ぎ。PR-Cでは扱わない。 |

---

## 2. KPI / 受け入れ基準

| KPI | 内容 | 測定方法 | 合格条件 |
|---|---|---|---|
| KPI-C1 | Redis未接続時の rate limit fail-open がメトリクスでカウントされる | unit test | `security_fail_open_total{component="rate_limit",reason="redis_unavailable"}` が増える |
| KPI-C2 | Redis例外時の rate limit fail-open がメトリクスでカウントされる | mock test | `component="rate_limit",reason="redis_exception"` が増える |
| KPI-C3 | Redis未接続時の session guard fail-open がメトリクスでカウントされる | unit test | `component="session_guard",reason="redis_unavailable"` が増える |
| KPI-C4 | Redis例外時の session guard fail-open がメトリクスでカウントされる | mock test | `component="session_guard",reason="redis_exception"` が増える |
| KPI-C5 | fail-open時に構造化warningログが出る | pytest caplog | component/reasonを含むwarningが記録される |
| KPI-C6 | 正常Redis時の挙動は変えない | existing tests / smoke | 既存rate limit/session guard挙動が維持される |
| KPI-C7 | `/metrics` に新counterが露出する | TestClient or curl | `security_fail_open_total` が出力される |

---

## 3. 実装方針

### 採用案

Prometheus Counter + structured warning log を追加する。

```python
SECURITY_FAIL_OPEN_TOTAL = Counter(
    "security_fail_open_total",
    "Security controls that failed open to preserve availability",
    ("component", "reason"),
)
```

labelは以下に限定する。

| label | 値 | 理由 |
|---|---|---|
| component | `rate_limit`, `session_guard` | middleware単位で十分。 |
| reason | `redis_unavailable`, `redis_exception` | 原因分類として十分。 |

ユーザーID、IP、path、exception文字列などはlabelに入れない。cardinality爆発を避ける。

### helper案

`backend/app/metrics.py` に以下を追加する。

```python
def record_security_fail_open(component: str, reason: str) -> None:
    SECURITY_FAIL_OPEN_TOTAL.labels(component, reason).inc()
```

middleware側はmetrics importに失敗しても本体挙動を壊さない設計にする。

---

## 4. 変更対象ファイル

| ファイル | 変更方針 |
|---|---|
| `backend/app/metrics.py` | `SECURITY_FAIL_OPEN_TOTAL` と `record_security_fail_open()` を追加。 |
| `backend/app/middleware/rate_limit.py` | Redis None / exception時にcounter increment + structured warning log。 |
| `backend/app/middleware/session_guard.py` | Redis None / exception時にcounter increment + structured warning log。 |
| `backend/tests/security/test_redis_fail_open_metrics.py` | counter/logのunit test追加。 |
| `docs/handoff/security/sec-01-redis-failopen/implementation.md` | 実装記録。 |

---

## 5. 対象外

このPR-C実装では以下を扱わない。

- Redis fail-openをfail-closeへ変更すること。
- token blacklist / auth rate limit のfail-open変更。
- Discord通知。
- Grafana dashboard / alert rule作成。
- Nginx変更。
- deploy.yml変更。

理由:

- fail-close化は可用性への影響が大きい。
- token blacklist / auth rate limit はSEC-02認証・認可で扱う。
- 通知/ダッシュボードはSEC-08監視・ログ・検知で扱う。

---

## 6. 技術How

### 6.1 `metrics.py`

追加:

```python
SECURITY_FAIL_OPEN_TOTAL = Counter(
    "security_fail_open_total",
    "Security controls that failed open to preserve availability",
    ("component", "reason"),
)


def record_security_fail_open(component: str, reason: str) -> None:
    SECURITY_FAIL_OPEN_TOTAL.labels(component, reason).inc()
```

### 6.2 `rate_limit.py`

Redis None時:

```python
if not r:
    record_security_fail_open("rate_limit", "redis_unavailable")
    logger.warning("security_fail_open component=rate_limit reason=redis_unavailable")
    return False
```

例外時:

```python
except Exception:
    record_security_fail_open("rate_limit", "redis_exception")
    logger.warning("security_fail_open component=rate_limit reason=redis_exception")
    return False
```

### 6.3 `session_guard.py`

同様に `component=session_guard` で記録する。

---

## 7. リスクと弊害対策

| リスク | 内容 | 対策 |
|---|---|---|
| metrics importの循環 | middlewareからmetricsをimportすることで循環する可能性 | `app.metrics` はmiddlewareに依存しないため基本問題なし。問題があれば小さな `app.security.metrics` に分離。 |
| counterがrequestごとに増えすぎる | Redis outage時に高頻度で増える | これは検知目的として許容。labelを限定してcardinalityを抑える。 |
| warning logが大量化 | Redis outage時にログが増える | 初期は許容。必要ならSEC-08でrate-limited logging設計。 |
| fail-closeではないため防御停止は残る | 可用性優先のまま | KPIは「見逃さない」。fail-close判断は別設計。 |
| 認証blacklist fail-openが残る | SEC-01範囲外 | SEC-02へ明示引き継ぎ。 |

---

## 8. 検証計画

### unit test

```bash
python -m pytest backend/tests/security/test_redis_fail_open_metrics.py -q
```

テスト観点:

1. `get_redis()` がNoneのとき、RateLimitがFalseを返し、counterが増える。
2. Redis操作が例外を投げたとき、RateLimitがFalseを返し、counterが増える。
3. `get_redis()` がNoneのとき、SessionGuardがFalseを返し、counterが増える。
4. Redis操作が例外を投げたとき、SessionGuardがFalseを返し、counterが増える。
5. warning logにcomponent/reasonが含まれる。

### metrics exposure

```bash
curl -s https://app.salesanchor.jp/metrics | grep security_fail_open_total
```

注: `/metrics` はIP制限あり。実行場所に注意。

### regression

```bash
python -m pytest backend/tests -q
```

---

## 9. 外部・過去事例の参照と我々への応用

### 事例1: fail-openは可用性優先の設計として使われる

認証/レート制限/セッション防御の周辺では、依存コンポーネント障害時に全ユーザーを止めるか、防御を一時的に弱めてサービス継続するかの選択がある。

Sales Anchorへの応用:

- いきなりfail-closeにしない。
- まずfail-open発生を測定可能にする。
- 測定後、SEC-08でアラート化し、SEC-02で認証系だけfail-close/限定fail-openを検討する。

### 事例2: metrics labelのcardinality管理

Prometheusでは、IP/path/user/exception messageをlabelに入れるとseriesが爆発する。

Sales Anchorへの応用:

- labelはcomponent/reasonのみ。
- 詳細はログに寄せる。

### 事例3: 観測できないセキュリティ制御は運用上存在しないに近い

制御が落ちていても誰も気づけなければ、攻撃時に防御層として期待できない。

Sales Anchorへの応用:

- `security_fail_open_total` をSEC-08でGrafana/Discordアラートに接続する。

---

## 10. SEC-02 / SEC-08への引き継ぎ

### SEC-02 認証・認可へ

以下はSEC-01 PR-Cでは扱わず、SEC-02でrecon/KPI/design対象にする。

- `check_auth_rate_limit()` Redis不通時fail-open。
- `record_auth_failure()` Redis不通時に失敗回数を記録しない。
- `is_token_blacklisted()` Redis障害時にログアウト済みtokenを通す可能性。

### SEC-08 監視・ログ・検知へ

以下はSEC-08で扱う。

- `security_fail_open_total` のGrafana panel。
- Redis fail-open発生時のDiscord通知。
- 閾値設計。
- rate-limited logging。

---

## 11. Claude Code / Generator への実装ハンドオフ

### 目的

Redis不通時にRateLimitMiddleware / SessionGuardMiddlewareがfail-openしたことを、Prometheus metricsとwarning logで観測可能にする。

### 実装指示

1. `backend/app/metrics.py` に `SECURITY_FAIL_OPEN_TOTAL` と `record_security_fail_open()` を追加する。
2. `backend/app/middleware/rate_limit.py` の `_check_rate_limit()` で、Redis None時と例外時に `record_security_fail_open("rate_limit", reason)` を呼ぶ。
3. `backend/app/middleware/session_guard.py` の `_check_session_ip()` で、Redis None時と例外時に `record_security_fail_open("session_guard", reason)` を呼ぶ。
4. warning logは `security_fail_open component=<component> reason=<reason>` を含める。
5. testsを追加する。
6. fail-open挙動自体は変えない。戻り値は従来どおりFalse。
7. `deploy.yml`, `nginx`, `migrations`, 本番`scripts` は触らない。

### 受け入れ基準

- KPI-C1〜C7を満たす。
- 既存rate limit/session guardの正常系を壊さない。
- 新counter labelはcomponent/reasonのみ。

### 禁止

- Redis障害時にリクエスト拒否へ変更しない。
- token blacklist / auth rate limit を同時変更しない。
- Discord通知を同時実装しない。
