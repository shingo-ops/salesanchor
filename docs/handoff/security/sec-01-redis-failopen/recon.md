# SEC-01 PR-C Redis fail-open 検知 recon

> Issue: #2177  
> Parent: #2170 / ADR-140 SEC-MASTER  
> 作成日: 2026-06-14  
> 対象: rate limit / session guard のRedis fail-open検知  
> 方針: 実装変更なし。`file:line` 付きで現在地を固定する。

---

## 0. KGI

Redis不通時に rate limit / session guard が fail-open する状態を、運用上見逃さない。

---

## 1. 参照ADR / 正本確認

| 対象 | file:line | recon結果 |
|---|---|---|
| 標準ワークフロー | `docs/STANDARD-WORKFLOW.md:20-37` | KGI→recon→設計の順。reconはfile:line引用必須。 |
| 不明点プロトコル | `docs/STANDARD-WORKFLOW.md:41-45` | 推測で埋めず、不明は明示してPO相談。 |
| SEC-MASTER | `docs/security/SEC-MASTER.md` | SEC-01ではRedis fail-open検知強化をPR-Cとして扱う。 |
| SEC-01 recon | `docs/handoff/security/sec-01-entry/recon.md` | Redis不通時 fail-open をPR-C候補として特定。 |
| SEC-01 design | `docs/handoff/security/sec-01-entry/design.md` | 即fail-closeではなく、まずメトリクス/ログで検知可能にする方針。 |

---

## 2. Redis接続基盤

| 事実 | file:line | 評価 |
|---|---|---|
| `REDIS_URL` は環境変数から取得し、既定は `redis://redis:6379/0` | `backend/app/cache.py:13-13` | compose上のRedis接続前提。 |
| 起動時 `init_redis()` でRedis pingを行う | `backend/app/cache.py:25-31` | 起動時確認あり。 |
| Redis初期化失敗時はcritical log後 `_redis = None` | `backend/app/cache.py:32-35` | fail-open基盤になる。 |
| `get_redis()` は未接続時Noneを返す | `backend/app/cache.py:45-47` | 呼び出し側がNone時の挙動を決める。 |

---

## 3. RateLimitMiddleware の fail-open

| 事実 | file:line | 評価 |
|---|---|---|
| docstringで「Redis不通時は制限を適用しない（fail-open）」と明記 | `backend/app/middleware/rate_limit.py:3-10` | 意図的fail-open。 |
| `_check_rate_limit()` はRedisなし/Redis不通時にFalseを返す設計 | `backend/app/middleware/rate_limit.py:62-68` | False=超過なし。通過する。 |
| `get_redis()` がNoneならFalseを返す | `backend/app/middleware/rate_limit.py:69-73` | Redis未接続時はrate limit無効。 |
| Redis操作例外時はwarning log後Falseを返す | `backend/app/middleware/rate_limit.py:82-84` | 例外時もrate limit無効。 |
| 超過時のみ429を返す | `backend/app/middleware/rate_limit.py:111-116` | fail-open時はここに到達しない。 |

### 判定

RateLimitMiddleware はRedis不通時に意図的にfail-openする。可用性優先として理解できるが、現状はwarningログのみで、Prometheusメトリクス等の定量検知が見えない。

---

## 4. SessionGuardMiddleware の fail-open

| 事実 | file:line | 評価 |
|---|---|---|
| docstringで「Redis 不通時は fail-open」と明記 | `backend/app/middleware/session_guard.py:18-21` | 意図的fail-open。 |
| `_check_session_ip()` は正常/Redis不通/判定不能をFalseで返す | `backend/app/middleware/session_guard.py:85-91` | False=再認証不要。通過する。 |
| `get_redis()` がNoneならFalseを返す | `backend/app/middleware/session_guard.py:92-96` | Redis未接続時はsession guard無効。 |
| Redis操作例外時はwarning log後Falseを返す | `backend/app/middleware/session_guard.py:141-143` | 例外時もsession guard無効。 |
| Trueの場合のみ401 SESSION_COMPROMISEDを返す | `backend/app/middleware/session_guard.py:165-173` | fail-open時は通過。 |

### 判定

SessionGuardMiddleware もRedis不通時に意図的にfail-openする。RateLimit同様、現状はwarningログのみで、定量検知/アラート接続は見えない。

---

## 5. 認証系Redis fail-open（SEC-02へ引き継ぎ）

SEC-01 PR-Cの直接対象は rate limit / session guard だが、Redis fail-openは認証系にも存在する。

| 対象 | file:line | 事実 | 引き継ぎ |
|---|---|---|---|
| auth rate limit | `backend/app/cache.py:55-69` | `check_auth_rate_limit()` はRedis不通時False。認証ロックが効かない。 | SEC-02 認証・認可で扱う。 |
| auth failure記録 | `backend/app/cache.py:72-83` | `record_auth_failure()` はRedis不通時return。失敗回数が記録されない。 | SEC-02。 |
| token blacklist | `backend/app/cache.py:86-101` | `is_token_blacklisted()` はRedis障害時False。ログアウト済みtokenが通る可能性。 | SEC-02で高優先度。 |
| blacklist登録 | `backend/app/cache.py:143-163` | 登録失敗時Falseを返す。呼び出し元で503想定。 | SEC-02で確認。 |

### 判定

Redis fail-openは入口セキュリティだけでなく認証・認可にも関係する。PR-Cでは入口middlewareの検知に絞り、認証ロック/ブラックリストはSEC-02へ正式引き継ぎする。

---

## 6. 既存メトリクス基盤

| 事実 | file:line | 評価 |
|---|---|---|
| `prometheus_client` の Counter/Gauge/Histogram を使用 | `backend/app/metrics.py:5-7` | 新counter追加可能。 |
| HTTP request counterがある | `backend/app/metrics.py:8-12` | 既存counterパターンあり。 |
| request duration histogramがある | `backend/app/metrics.py:14-18` | 既存histogramパターンあり。 |
| in-flight gaugeがある | `backend/app/metrics.py:20-23` | 既存gaugeパターンあり。 |
| `/metrics` endpointを提供 | `backend/app/metrics.py:60-62` | Prometheus scrape可能。 |
| Nginx `/metrics` はIP制限あり | `nginx/nginx.conf:218-227` | メトリクス公開は制限済み。 |

### 判定

Prometheus counterを追加する土台はある。PR-C実装では `backend/app/metrics.py` に security fail-open counter を追加し、middlewareからincrementするのが自然。

---

## 7. 不明点

| 不明点 | 理由 | 次の取得手段 |
|---|---|---|
| Prometheus/Grafana上でどのalert ruleがあるか | `monitoring/**` の詳細未確認 | SEC-08またはPR-C実装前に確認 |
| Redis fail-openログが現在どこへ集約されるか | logging集約設定が未確認 | 実機 / Docker logging / Grafana Loki有無確認 |
| Discord通知へ繋げる既存共通関数があるか | 通知系サービス未調査 | SEC-08で確認。PR-C初期はcounter/logに限定 |

---

## 8. KPI / 受け入れ基準

| KPI | 内容 | 測定方法 |
|---|---|---|
| KPI-C1 | Redis未接続時の rate limit fail-open がメトリクスでカウントされる | unit test + `/metrics` snapshot |
| KPI-C2 | Redis例外時の rate limit fail-open がメトリクスでカウントされる | mock test |
| KPI-C3 | Redis未接続時の session guard fail-open がメトリクスでカウントされる | unit test + `/metrics` snapshot |
| KPI-C4 | Redis例外時の session guard fail-open がメトリクスでカウントされる | mock test |
| KPI-C5 | fail-open時に構造化warningログが出る | pytest caplog |
| KPI-C6 | 正常Redis時の挙動は変えない | existing middleware tests / smoke |
| KPI-C7 | `/metrics` に新counterが露出する | `curl` or TestClient |

---

## 9. リスク判定

| ID | 危険度 | 項目 | 根拠 | 対応方針 |
|---|---|---|---|---|
| REDIS-R1 | Medium | RateLimitがRedis未接続/例外時に無効化される | `rate_limit.py:69-84` | 即fail-closeせずcounter/log追加。 |
| REDIS-R2 | Medium | SessionGuardがRedis未接続/例外時に無効化される | `session_guard.py:92-143` | 即fail-closeせずcounter/log追加。 |
| REDIS-R3 | High候補 | Token blacklistがRedis障害時に通過する | `cache.py:86-101` | SEC-02へ引き継ぎ。 |
| REDIS-R4 | Medium | fail-openがwarning logのみで定量化されない | `rate_limit.py`, `session_guard.py` | Prometheus counter追加。 |
| REDIS-R5 | Low-Medium | fail-open counterが高頻度で増えすぎる可能性 | middlewareごとにrequest単位 | labelsを限定しcardinalityを抑える。 |

---

## 10. recon結論

Redis不通時のfail-openは、RateLimitMiddlewareとSessionGuardMiddlewareで明示的に採用されている。可用性を優先する設計として即fail-closeにはしない。

ただし、現状はwarning logのみで、どれだけfail-openが発生しているかを運用上測定しにくい。PR-Cでは以下を設計する。

1. `security_fail_open_total` のようなPrometheus counterを追加。
2. labelは `component` と `reason` 程度に限定し、cardinalityを抑える。
3. RateLimit / SessionGuard のRedis None / exceptionでcounterを増やす。
4. warning logを構造化し、component/reasonを含める。
5. 認証ロック/blacklist系Redis fail-openはSEC-02へ引き継ぐ。
