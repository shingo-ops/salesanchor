# SEC-01 PR-C Redis fail-open metrics implementation

> Issue: #2177  
> Recon: `docs/handoff/security/sec-01-redis-failopen/recon.md`  
> Design: `docs/handoff/security/sec-01-redis-failopen/design.md`  
> 実装日: 2026-06-14

---

## 1. 実装内容

Redis不通時にRateLimitMiddleware / SessionGuardMiddlewareがfail-openしたことをPrometheus metricsとwarning logで観測可能にした。

追加メトリクス:

```text
security_fail_open_total{component,reason}
```

label:

- `component`: `rate_limit` / `session_guard`
- `reason`: `redis_unavailable` / `redis_exception`

---

## 2. 変更ファイル

| ファイル | 内容 |
|---|---|
| `backend/app/metrics.py` | `SECURITY_FAIL_OPEN_TOTAL` と `record_security_fail_open()` を追加 |
| `backend/app/middleware/rate_limit.py` | Redis None / exception時にcounter increment + structured warning log |
| `backend/app/middleware/session_guard.py` | Redis None / exception時にcounter increment + structured warning log |
| `backend/tests/security/test_redis_fail_open_metrics.py` | fail-open counter/log unit test追加 |
| `backend/tests/security/__init__.py` | test package marker |
| `docs/handoff/security/sec-01-redis-failopen/implementation.md` | 本実装記録 |

---

## 3. KPI対応

| KPI | 対応 |
|---|---|
| KPI-C1 | rate limit Redis None時に `component=rate_limit,reason=redis_unavailable` をincrement |
| KPI-C2 | rate limit Redis exception時に `component=rate_limit,reason=redis_exception` をincrement |
| KPI-C3 | session guard Redis None時に `component=session_guard,reason=redis_unavailable` をincrement |
| KPI-C4 | session guard Redis exception時に `component=session_guard,reason=redis_exception` をincrement |
| KPI-C5 | `security_fail_open component=<component> reason=<reason>` warning log |
| KPI-C6 | fail-open戻り値は従来どおりFalse。挙動は変えない |
| KPI-C7 | Prometheus default registry経由で `/metrics` に露出 |

---

## 4. 検証方法

```bash
python -m pytest backend/tests/security/test_redis_fail_open_metrics.py -q
```

回帰:

```bash
python -m pytest backend/tests -q
```

metrics確認:

```bash
curl -s https://app.salesanchor.jp/metrics | grep security_fail_open_total
```

注: `/metrics` はNginxでIP制限あり。

---

## 5. 対象外

このPRでは以下を扱わない。

- Redis fail-openをfail-closeへ変更すること。
- token blacklist / auth rate limit のfail-open変更。
- Discord通知。
- Grafana dashboard / alert rule作成。
- Nginx変更。
- deploy.yml変更。

---

## 6. 次の引き継ぎ

SEC-02 認証・認可で以下を扱う。

- `check_auth_rate_limit()` Redis不通時fail-open。
- `record_auth_failure()` Redis不通時に失敗回数を記録しない。
- `is_token_blacklisted()` Redis障害時にログアウト済みtokenを通す可能性。

SEC-08 監視・ログ・検知で以下を扱う。

- `security_fail_open_total` のGrafana panel。
- Redis fail-open発生時のDiscord通知。
- 閾値設計。
