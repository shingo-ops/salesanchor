# SEC-MASTER: Sales Anchor Security Hardening Master Plan

> ADR: `docs/adr/ADR-140-security-hardening-master-plan.md`  
> Issue: #2166  
> Status: Definition / PO agreed  
> Scope: Sales Anchor 全体のサイバーセキュリティ KGI・領域定義・検証単位

## 0. 目的

Sales Anchor を「完璧」ではなく、以下を満たす堅牢な SaaS 基盤にする。

1. 侵入されにくい。
2. 設定ミスで崩れにくい。
3. 万一漏れても被害が広がりにくい。
4. 異常に早く気づける。
5. 復旧できる。
6. セキュリティ変更を標準ワークフローで安全に進められる。

## 1. 全体KGI

Sales Anchor の顧客データ、認証情報、外部連携トークン、受発注・請求・在庫データ、監査ログ、運用情報を安全に扱える SaaS 基盤を構築する。

## 2. 全体成功条件

| ID | 成功条件 | 検証方法 |
|---|---|---|
| G1 | Critical / High 相当の既知セキュリティ欠陥が、未対策・未記録のまま残っていない | SEC領域別recon + Issue/ADR記録 |
| G2 | 認証なしで管理者操作できるAPIが 0 件 | router recon + admin/super-admin依存CI |
| G3 | テナント越境アクセスが 0 件 | DB/RLS/API IDOR テスト |
| G4 | 本番必須Secret未設定のまま起動できる経路が 0 件 | startup fail-close test |
| G5 | 外部公開すべきでない監視・管理画面の無防備公開が 0 件 | Nginx/monitoring recon + 外部到達確認 |
| G6 | DBバックアップからの復元手順が検証済み | restore drill 記録 |
| G7 | 危険変更は PO GO なしに develop へ入らない | process-artifacts gate / PR確認 |
| G8 | 各SEC領域に KGI / recon対象 / 受け入れ基準 / 検証方法が存在する | 本ファイル + 後続 design doc |

## 3. 領域定義

### SEC-01 入口セキュリティ

対象: Nginx, TLS, CSP, CORS, proxy headers, rate limit, monitoring exposure

KGI: 外部から到達できる入口を最小化し、IP偽装・過剰公開・TLS/CSP不備による攻撃面を潰す。

受け入れ基準:

- 公開ポートは原則 80/443 のみ。
- HTTP は HTTPS に強制リダイレクト。
- `X-Forwarded-For` 偽装が backend の rate limit / audit / session guard に影響しない。
- API専用ドメインは `/api/` 以外を 404。
- Grafana / Uptime Kuma / status 系は認証またはIP制限あり。
- Nginxセキュリティヘッダーが検証済み。

recon対象:

- `nginx/nginx.conf`
- `docker-compose.yml`
- `backend/app/middleware/rate_limit.py`
- `backend/app/middleware/audit.py`
- `backend/app/middleware/session_guard.py`
- monitoring関連 compose / prometheus / grafana / uptime kuma 設定

検証方法:

- file:line recon
- curl による HTTP→HTTPS / API以外404 / header確認
- 偽装 `X-Forwarded-For` リクエストで backend 側の採用IPを確認
- 監視画面の未認証アクセス確認

### SEC-02 認証・認可セキュリティ

対象: Firebase, MFA, JWT, admin, super-admin, role/permission, smoke service bypass

KGI: 正規ユーザーだけが、許可された操作だけを実行できる状態にする。

受け入れ基準:

- 本番 MFA 必須。
- JWT 検証なしで保護 API を通過できない。
- admin / super-admin 操作の依存漏れが CI で検出される。
- smoke service bypass は本番で用途・ユーザー・トークンが限定される。
- 権限不足時は 403 で fail-close。

recon対象:

- `backend/app/auth/dependencies.py`
- `backend/app/main.py`
- `backend/app/routers/**`
- auth / role / permission 関連テスト

検証方法:

- router include と endpoint dependency の file:line recon
- admin/super-admin依存漏れの静的検査
- JWTなし / tenant user / admin / super-admin のAPI smoke

### SEC-03 DB・テナント分離セキュリティ

対象: PostgreSQL, RLS, schema prefix, search_path, app.tenant_id, DB role, migrations

KGI: テナント越境・DB過剰権限・migration事故を防ぎ、1テナントの事故が他テナントへ波及しない状態にする。

受け入れ基準:

- tenant_id を URL やクライアント入力から信用しない。
- RLS / `app.tenant_id` / `search_path` が設計どおり機能する。
- commit 後の tenant context reset / schema prefix 方針が守られる。
- アプリ用DBロールは必要最小権限。
- migration は危険変更として PO GO 対象。

recon対象:

- `backend/app/database.py`
- `backend/app/auth/dependencies.py`
- `migrations/**`
- `scripts/run_all_migrations.sh`
- DB role bootstrap / SA-18 関連 deploy 設定

検証方法:

- RLS / search_path / tenant context の file:line recon
- 異なるtenantのIDOR APIテスト
- migration smoke
- DB role権限の実DB確認

### SEC-04 バックエンドAPIセキュリティ

対象: FastAPI routers, public endpoints, webhook, OAuth callback, input validation, IDOR, SQL injection, file generation

KGI: 公開APIと内部APIの境界を明確化し、入力改ざん・IDOR・署名不備・SQL注入を防ぐ。

受け入れ基準:

- 認証不要API一覧が明文化されている。
- Webhook / OAuth callback は署名・state・one-time token等で保護される。
- ID指定APIで他テナントデータにアクセスできない。
- raw SQL は bind parameter または安全な schema helper を使う。
- PDF / CSV 等の出力に機密情報が過剰混入しない。

recon対象:

- `backend/app/main.py`
- `backend/app/routers/**`
- `backend/app/services/**`
- PDF / CSV renderer / exporter

検証方法:

- public router 一覧化
- webhook署名 / OAuth state テスト
- IDORテスト
- raw SQL grep + bind確認

### SEC-05 フロントエンドセキュリティ

対象: React/Vite, token handling, XSS, route guard, error exposure, external scripts

KGI: ブラウザ上でトークン・個人情報・管理機能が不必要に露出しない状態にする。

受け入れ基準:

- UI上の権限表示とAPI側権限が一致する。
- XSSにつながるHTML注入がない。
- エラー画面に Secret や内部スタックを出さない。
- 外部 script / connect 先は CSP と整合する。
- Firebase 公開設定に Secret 相当の値を混入しない。

recon対象:

- `frontend/src/**`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- Vite env / Firebase config

検証方法:

- dangerous HTML API grep
- route guard / role guard recon
- Playwright による権限画面確認
- CSP と外部接続先の突合

### SEC-06 インフラ・Dockerセキュリティ

対象: VPS, firewall, SSH, Docker daemon, containers, networks, volumes, OS packages

KGI: サーバー侵害・コンテナ脱出・不要公開・権限過多を防ぐ。

受け入れ基準:

- Firewall で必要ポートのみ開放。
- SSH は鍵認証・root login 無効・不要ユーザーなし。
- コンテナは原則 non-root / no-new-privileges。
- DB / Redis は外部公開されない。
- 永続 volume と秘密ファイルの権限が最小。

recon対象:

- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- VPS実機設定（GitHubだけでは不明）

検証方法:

- compose / Dockerfile file:line recon
- VPS上の firewall / sshd / docker group / open port 確認
- image scan

### SEC-07 CI/CD・GitHubセキュリティ

対象: GitHub Actions, Secrets, deploy.yml, branch protection, CODEOWNERS, process gate

KGI: CI/CD経由のSecret漏洩・無承認本番変更・危険変更混入を防ぐ。

受け入れ基準:

- GitHub Secrets をログ出力しない。
- `deploy.yml` / `migrations/` / production `scripts/` は PO GO 対象。
- branch protection / CODEOWNERS / required checks がセキュリティ方針と一致する。
- security lint / dependency scan / secret scan が導入されている。
- 書類のみPRと危険変更PRの判定が自動化されている。

recon対象:

- `.github/workflows/**`
- `.github/CODEOWNERS`
- PR template / process-artifacts gate
- GitHub rulesets（UI/API確認が必要）

検証方法:

- workflow file:line recon
- ruleset / branch protection確認
- dummy PRで危険変更検出

### SEC-08 監視・ログ・検知

対象: Audit log, auth failures, bulk access, rate limit, Grafana, Uptime Kuma, Discord alerts

KGI: 攻撃・誤操作・大量取得・認証異常に早く気づける状態にする。

受け入れ基準:

- 認証失敗・403・管理操作・書き込み操作が記録される。
- 大量アクセス / 大量エクスポートが検知される。
- Redis不通・rate limit fail-open がアラート化される。
- 監視画面自体が保護されている。
- 重要アラートは Discord 等に通知される。

recon対象:

- `backend/app/middleware/audit.py`
- `backend/app/middleware/rate_limit.py`
- monitoring stack
- Discord notification scripts / env

検証方法:

- 監査ログ投入テスト
- Redis停止時挙動確認
- Grafana / Uptime Kuma 到達制限確認
- Discord通知 smoke

### SEC-09 バックアップ・復旧セキュリティ

対象: DB backup, restore drill, rollback, key backup, incident runbook

KGI: 壊れても戻せる、漏れても切り戻せる、鍵を失っても復旧方針がある状態にする。

受け入れ基準:

- pre-deploy DB backup が動作する。
- 復元テストが定期的に実施される。
- 暗号鍵のバックアップ・ローテーション手順がある。
- 自動ロールバックの成功/失敗が通知される。
- インシデント時の手順が文書化されている。

recon対象:

- `.github/workflows/deploy.yml`
- `scripts/backup.sh`
- restore docs / operations docs
- key rotation docs

検証方法:

- backup artifact / storage確認
- staging restore drill
- rollback dry run
- runbook review

### SEC-10 外部連携セキュリティ

対象: Meta, Discord, Google, FedEx, Gemini, OAuth, webhook, API tokens

KGI: 外部サービス連携トークンの漏洩・過剰権限・callback改ざん・Webhook偽装を防ぐ。

受け入れ基準:

- 各連携の Token / Secret / Scope 一覧が明文化されている。
- OAuth state は one-time かつ期限付き。
- Webhook 署名検証がある。
- トークン保存時は暗号化される。
- トークンローテーション・無効化手順がある。

recon対象:

- Meta / Discord / Google / FedEx / Gemini 関連 routers / services
- OAuth state service
- encryption service
- deploy secret injection

検証方法:

- scope / secret / token inventory
- webhook signature tests
- OAuth state replay test
- token rotation runbook確認

## 4. 実施ルール

- 1 PR で全領域を実装しない。
- 各領域は `KGI → file:line recon → 設計 → 小PR実装 → 検証` の単位で進める。
- `migrations/`、`deploy.yml`、production `scripts/` を含む場合は PO GO 必須。
- 不明点は推測で埋めず、不明として PO に確認する。

## 5. 初回実施対象

最初の実装対象は `SEC-01 入口セキュリティ` とする。

理由:

- IP偽装対策は rate limit / audit / session guard の土台である。
- 監視画面公開範囲は攻撃者に内部構成を与えやすい。
- Secret fail-close は設定ミスによる本番事故を早期に防ぐ。

SEC-01 の recon / design は後続PRまたは `docs/handoff/security-sec-01/` に切り出す。
