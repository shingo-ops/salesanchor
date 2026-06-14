# SEC-02 認証・認可セキュリティ design

> Issue: #2187  
> Recon: `docs/handoff/security/sec-02-auth-authz/recon.md`  
> Parent: ADR-140 / SEC-MASTER  
> 作成日: 2026-06-14

---

## 0. KGI

正規ユーザーだけが、許可された操作だけを実行できる状態にする。

---

## 1. recon要約

| ID | 事実 | 根拠 | design判断 |
|---|---|---|---|
| R1 | Firebase verify / MFA / DB user照合 / tenant_id一致検証あり | `backend/app/auth/dependencies.py:142-190` | 認証本体は維持。作り直さない。 |
| R2 | smoke service bypassがある | `backend/app/auth/dependencies.py:34-39`, `95-113` | 本番で意図せず有効にならない検知・制限を設計。 |
| R3 | token blacklist確認はRedis障害時fail-open | `backend/app/cache.py:326-341` | SEC-02 PR-Aで検知metric/log化。後続でfail-close検討。 |
| R4 | auth rate lockout / failure記録もRedis依存 | `backend/app/cache.py:300-323` | SEC-02 PR-Aで検知metric/log化。 |
| R5 | 認証不要routerはmain.pyに明示あり | `backend/app/main.py:189-203` | public router allowlistを固定。 |
| R6 | super-admin routerはmain.pyではdependencyなし、router内保護設計 | `backend/app/main.py:14-55`, `backend/app/main.py:14-23` | CIでrequire_super_admin漏れ検査。 |
| R7 | admin fallbackで全permission付与 | `backend/app/auth/dependencies.py:157-163`, `backend/app/auth/dependencies.py:520-8` | 移行期限/可視化/段階廃止を設計。 |

---

## 2. KPI / 受け入れ基準

| KPI | 内容 | 測定方法 | 合格条件 |
|---|---|---|---|
| KPI-02-1 | 本番でMFA_REQUIREDがfalseのまま運用されない | env checker / startup metric | productionでfalseなら起動失敗またはCritical alert |
| KPI-02-2 | logout済みtokenがRedis障害時に無検知で通らない | unit test + metric | `auth_fail_open_total{component="token_blacklist"}` が増える |
| KPI-02-3 | auth failure lockoutがRedis障害時に無検知で無効化されない | unit test + metric | `auth_fail_open_total{component="auth_lockout"}` が増える |
| KPI-02-4 | smoke service bypassが本番で意図せず有効にならない | startup check / unit test | productionでbypass有効なら明示allow flag必須 |
| KPI-02-5 | 認証不要routerが明示リスト化され、公開理由を持つ | static test | allowlist外public router 0 |
| KPI-02-6 | super-admin routerが中央admin dependencyで保護されている | static test | `super_admin*` router endpointの保護漏れ0 |
| KPI-02-7 | admin permission fallbackが過剰権限として放置されない | metric/log + design deadline | fallback使用回数が可視化される |

---

## 3. 実施順序

### SEC-02 PR-A: auth Redis fail-open 検知

目的:

- token blacklist / auth lockout / auth failure記録のRedis fail-openを観測可能にする。

変更候補:

- `backend/app/metrics.py`
  - `auth_fail_open_total{component,reason}` 追加。
- `backend/app/cache.py`
  - `is_token_blacklisted()` Redis None / exception時にcounter + warning。
  - `check_auth_rate_limit()` Redis None / exception時にcounter + warning。
  - `record_auth_failure()` Redis None / exception時にcounter + warning。

対象外:

- いきなりfail-close化しない。
- logout endpointの挙動変更はPR-B以降。

### SEC-02 PR-B: smoke service bypass production guard

目的:

- `SMOKE_SERVICE_TOKEN` / `SMOKE_SERVICE_EMAIL` が本番で意図せず有効にならないようにする。

候補:

- `ALLOW_SMOKE_SERVICE_BYPASS_IN_PRODUCTION=1` などの明示flagがない場合、本番ではbypass無効またはstartup warning/critical。
- bypass利用時にaudit/metricを出す。

### SEC-02 PR-C: public router allowlist CI

目的:

- 認証不要routerを明示allowlist化し、意図せぬ公開API追加を防ぐ。

候補:

- `backend/tests/security/test_public_router_allowlist.py`
- `main.py` の public router includeを静的/ASTで検査。

### SEC-02 PR-D: super-admin dependency static check

目的:

- main.pyでdependenciesを付けない設計のsuper-admin系routerについて、router内 `require_super_admin` の漏れを検査する。

候補:

- `backend/tests/security/test_super_admin_route_guards.py`
- `backend/app/routers/super_admin*.py`, `product_masters.py`, `parse_review.py`, `inventory_offers.py` などを対象。

### SEC-02 PR-E: permission fallback visibility

目的:

- `User.role='admin'` fallbackで全permission付与される経路を可視化し、段階廃止/承認制にする。

候補:

- fallback使用時にmetric/log。
- 期限付きADR/Issue化。

---

## 4. 技術How

### 4.1 auth fail-open metric

`backend/app/metrics.py` に追加候補:

```python
AUTH_FAIL_OPEN_TOTAL = Counter(
    "auth_fail_open_total",
    "Authentication controls that failed open to preserve availability",
    ("component", "reason"),
)
```

label候補:

| component | reason |
|---|---|
| `token_blacklist` | `redis_unavailable`, `redis_exception` |
| `auth_lockout` | `redis_unavailable`, `redis_exception` |
| `auth_failure_record` | `redis_unavailable`, `redis_exception` |

cardinality抑制:

- IP / user / token hash / path / exception message はlabelに入れない。

### 4.2 smoke bypass guard

候補:

```python
if is_production and smoke_token_configured and not allow_smoke_bypass:
    # fail closed or ignore bypass
```

設計判断:

- 初期は「productionでは明示flagがない限りbypass無効」にする案を推奨。
- いきなりstartup失敗にするか、bypass無効化にするかはPO確認。

### 4.3 static checks

public router allowlist:

- `health.router`
- `auth.router`
- `webhook.router`
- `meta.router`
- `contact.router`
- `registration_tokens.public_router`
- `integrations.public_router`
- `google_calendar.public_router`

上記以外で `include_router(... dependencies=なし)` があればfail。

super-admin guard:

- `super_admin_*` router filesで `require_super_admin` import/useを検査。
- 例外は明示allowlistに入れる。

---

## 5. リスク / 弊害対策

| リスク | 内容 | 対策 |
|---|---|---|
| auth fail-openをfail-closeにするとRedis障害時に全ユーザー認証失敗 | 可用性リスク | 初期は検知のみ。fail-closeは別PRで検討。 |
| smoke bypassをいきなり無効化するとCI smokeが壊れる | CI/CD影響 | production guardに限定し、staging/CIは明示flag。 |
| static checkの誤検知 | routerごとの特殊事情 | allowlistをdocs付きで管理。 |
| admin fallback廃止で既存admin操作が壊れる | 移行リスク | metric→棚卸し→段階廃止。 |

---

## 6. 外部・過去事例の参照と我々への応用

### 事例1: logout token blacklistはRedis依存にしすぎると障害時に弱い

Redis障害時にblacklist確認をskipすると、logout済みtokenや取り消し済みtokenを一時的に許すことになる。

Sales Anchorへの応用:

- まずfail-open発生を観測可能にする。
- 重要操作だけfail-closeにする設計を後続で検討する。

### 事例2: CI用bypassは本番事故になりやすい

テスト用の特別認証は、Secret流出・設定ミス・本番有効化で高リスクになる。

Sales Anchorへの応用:

- bypassはproduction明示許可flagなしでは使えないようにする。
- bypass利用時は必ずaudit/metricを出す。

### 事例3: router依存は増えるほど漏れる

FastAPIのrouter-level dependencyは便利だが、例外routerが増えると漏れやすい。

Sales Anchorへの応用:

- public router / super-admin routerはCIで静的検査する。

---

## 7. Claude Code / Generator への実装ハンドオフ

### 目的

SEC-02 PR-Aとして、認証系Redis fail-openを観測可能にする。

### 対象範囲

- `backend/app/metrics.py`
- `backend/app/cache.py`
- tests
- `docs/handoff/security/sec-02-auth-authz/implementation.md`

### 実装指示

1. `auth_fail_open_total{component,reason}` counterを追加。
2. `is_token_blacklisted()` Redis None / exception時にcounter + warning。
3. `check_auth_rate_limit()` Redis None / exception時にcounter + warning。
4. `record_auth_failure()` Redis None / exception時にcounter + warning。
5. fail-open挙動自体は変更しない。
6. labelsはcomponent/reasonのみ。
7. testsを追加。
8. Nginx/deploy/migrations/scriptsは触らない。

### 受け入れ基準

- KPI-02-2 / KPI-02-3 を満たす。
- 既存認証成功/失敗挙動を変えない。
- metrics cardinalityが増えすぎない。

### 禁止

- token blacklistをいきなりfail-closeへ変更しない。
- smoke bypassを同時変更しない。
- router guard static checkを同時実装しない。
