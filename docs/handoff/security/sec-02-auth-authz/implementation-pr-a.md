# SEC-02 PR-A auth Redis fail-open metrics implementation

> Issue: #2187  
> Recon: `docs/handoff/security/sec-02-auth-authz/recon.md`  
> Design: `docs/handoff/security/sec-02-auth-authz/design.md`  
> 実装日: 2026-06-14

---

## 1. 実装内容

認証系Redis fail-openをPrometheus metricsとwarning logで観測可能にした。

追加メトリクス:

```text
auth_fail_open_total{component,reason}
```

label:

- `component`: `token_blacklist` / `auth_lockout` / `auth_failure_record`
- `reason`: `redis_unavailable` / `redis_exception`

---

## 2. 変更ファイル

| ファイル | 内容 |
|---|---|
| `backend/app/metrics.py` | `AUTH_FAIL_OPEN_TOTAL` と `record_auth_fail_open()` を追加 |
| `backend/app/cache.py` | blacklist / auth lockout / auth failure record のRedis fail-open時にcounter + structured warning log |
| `backend/tests/security/test_auth_fail_open_metrics.py` | Redis unavailable / exception のunit test追加 |
| `docs/handoff/security/sec-02-auth-authz/implementation-pr-a.md` | 本実装記録 |

---

## 3. KPI対応

| KPI | 対応 |
|---|---|
| KPI-02-2 | `token_blacklist` Redis fail-openをmetric/logで記録 |
| KPI-02-3 | `auth_lockout` と `auth_failure_record` Redis fail-openをmetric/logで記録 |

---

## 4. 検証方法

```bash
python -m pytest backend/tests/security/test_auth_fail_open_metrics.py -q
```

回帰:

```bash
python -m pytest backend/tests -q
```

metrics確認:

```bash
curl -s https://app.salesanchor.jp/metrics | grep auth_fail_open_total
```

注: `/metrics` はNginxでIP制限あり。

---

## 5. 対象外

このPRでは以下を扱わない。

- Redis fail-openをfail-closeへ変更すること。
- smoke service bypass production guard。
- public router allowlist CI。
- super-admin guard static check。
- permission fallback visibility。
- Nginx変更。
- deploy.yml変更。
- migrations。
- 本番scripts。

---

## 6. 残リスク

- Redis障害時の防御停止そのものは残る。
- logout済みtokenをRedis障害時に拒否する設計は後続PRで検討する。
- metricsをGrafana/alertへ接続するのはSEC-08対象。
