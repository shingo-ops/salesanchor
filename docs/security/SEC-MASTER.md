# SEC-MASTER — Security Hardening Master Plan

> **これは何？** Sales Anchor 全体のサイバーセキュリティを、思いつき修正ではなく `KGI → recon → 設計 → 実装 → 検証` で堅牢化するための運用SSOT。  
> **ADR**: `docs/adr/ADR-140-security-hardening-master-plan.md`  
> **Issue**: #2166  
> **初版**: 2026-06-14  
> **この文書の役割**: ADR-140 は意思決定、この文書は各SEC領域のKGI・成功条件・recon対象・検証方法を継続管理する実務SSOT。

---

## 0. 原則

SEC-MASTER は「完璧なセキュリティ」を約束しない。目標は、Sales Anchor を以下の状態に近づけ続けることである。

1. 侵入されにくい。
2. 設定ミスで崩れにくい。
3. 万一漏れても被害が広がりにくい。
4. 異常に早く気づける。
5. 復旧できる。
6. セキュリティ変更を標準ワークフローで安全に進められる。

進行は `docs/STANDARD-WORKFLOW.md` に従う。

- Phase 1: KGI設定（定量的な成功条件・PO承認ゲート）
- Phase 2: 現在地把握（file:line recon・推測禁止・ADR確認）
- Phase 3: 実現方法の設計（技術How / KPI / 弊害対策 / 計画 / 継続）
- Phase 4: 実装
- Phase 5: 検証ゲート

---

## 1. 全体KGI

Sales Anchor の顧客データ、認証情報、外部連携トークン、受発注・請求・在庫データ、監査ログ、運用情報を安全に扱えるSaaS基盤を構築する。

### 全体成功条件

| ID | 成功条件 | 検証方法 |
|---|---|---|
| G-01 | Critical / High 相当の既知セキュリティ欠陥が、未対策・未記録のまま残っていない | 各SEC領域のrecon/design/issue一覧で確認 |
| G-02 | 認証なしで管理者操作できるAPIが 0 件 | router dependency / `require_super_admin` / permission lint |
| G-03 | テナント越境アクセスが 0 件 | RLS / tenant context / IDORテスト |
| G-04 | 本番必須Secret未設定のまま起動できる経路が 0 件 | startup fail-close test / env smoke |
| G-05 | 外部公開すべきでない監視・管理画面の無防備公開が 0 件 | Nginx設定 / 外部curl / Basic認証 or IP制限確認 |
| G-06 | DBバックアップからの復元手順が検証済み | restore drill / runbook / 記録 |
| G-07 | 危険変更はPO GOなしに develop へ入らない | PR本文 / CODEOWNERS / process-artifacts gate |
| G-08 | 各SEC領域に KGI / recon対象 / 受け入れ基準 / 検証方法が存在する | この文書と各handoffで確認 |

---

## 2. セキュリティ領域一覧

| ID | 領域 | 優先度 | 最初の状態 |
|---|---|---:|---|
| SEC-01 | 入口セキュリティ | P0 | 次に着手 |
| SEC-02 | 認証・認可セキュリティ | P0 | SEC-01後 |
| SEC-03 | DB・テナント分離セキュリティ | P0 | SEC-02後 |
| SEC-04 | バックエンドAPIセキュリティ | P1 | 待機 |
| SEC-05 | フロントエンドセキュリティ | P1 | 待機 |
| SEC-06 | インフラ・Dockerセキュリティ | P1 | 待機 |
| SEC-07 | CI/CD・GitHubセキュリティ | P1 | 待機 |
| SEC-08 | 監視・ログ・検知 | P1 | 待機 |
| SEC-09 | バックアップ・復旧セキュリティ | P1 | 待機 |
| SEC-10 | 外部連携セキュリティ | P1 | 待機 |

---

## 3. SEC-01 入口セキュリティ

### KGI

外部から到達できる入口を最小化し、IP偽装・過剰公開・TLS/CSP不備による攻撃面を潰す。

### 対象

- Nginx
- TLS / HSTS / CSP / CORS
- proxy headers
- rate limit
- monitoring exposure
- `app.salesanchor.jp` / `api.salesanchor.jp` / `monitor.salesanchor.jp`

### 成功条件

| ID | 成功条件 | 検証方法 |
|---|---|---|
| SEC01-G1 | 公開ポートは原則 80/443 のみ | `docker-compose.yml` / VPS firewall recon |
| SEC01-G2 | HTTP は HTTPS に強制リダイレクト | Nginx設定 / curl |
| SEC01-G3 | `X-Forwarded-For` 偽装が backend の rate limit / audit / session guard に影響しない | Nginx設定 / backend IP取得処理 / spoof test |
| SEC01-G4 | API専用ドメインは `/api/` 以外を 404 | Nginx設定 / curl |
| SEC01-G5 | Grafana / Uptime Kuma / status 系は認証またはIP制限あり | Nginx設定 / 外部アクセス検証 |
| SEC01-G6 | Nginxセキュリティヘッダーが検証済み | curl header snapshot |

### recon対象ファイル

- `nginx/nginx.conf`
- `docker-compose.yml`
- `backend/app/main.py`
- `backend/app/middleware/rate_limit.py`
- `backend/app/middleware/session_guard.py`
- `backend/app/middleware/audit.py`

### 想定リスク

- proxy header修正により監査ログのIP表記が変わる。
- 監視画面にBasic認証/IP制限を足すことで運用アクセスが不便になる。
- レート制限を強めすぎると正規ユーザーを巻き添えにする。

---

## 4. SEC-02 認証・認可セキュリティ

### KGI

正規ユーザーだけが、許可された操作だけを実行できる状態にする。

### 対象

- Firebase Authentication
- MFA
- JWT検証
- admin / super-admin
- role / permission
- smoke service bypass

### 成功条件

| ID | 成功条件 | 検証方法 |
|---|---|---|
| SEC02-G1 | 本番MFA必須 | env / auth dependency recon / auth test |
| SEC02-G2 | JWT検証なしで保護APIを通過できない | router dependency map / API test |
| SEC02-G3 | admin / super-admin 操作の依存漏れがCIで検出される | static lint / router scan |
| SEC02-G4 | smoke service bypass は用途・ユーザー・トークンが限定される | auth dependency recon / env check |
| SEC02-G5 | 権限不足時は 403 で fail-close | permission test |

### recon対象ファイル

- `backend/app/auth/dependencies.py`
- `backend/app/main.py`
- `backend/app/routers/**`
- `frontend/src/**` のroute guard / admin UI
- `.github/workflows/**` のauth/permission lint有無

---

## 5. SEC-03 DB・テナント分離セキュリティ

### KGI

テナント越境・DB過剰権限・migration事故を防ぎ、1テナントの事故が他テナントへ波及しない状態にする。

### 対象

- PostgreSQL
- RLS
- schema prefix
- search_path
- `app.tenant_id`
- DB role
- migrations

### 成功条件

| ID | 成功条件 | 検証方法 |
|---|---|---|
| SEC03-G1 | tenant_id をURLやクライアント入力から信用しない | auth dependency / router scan |
| SEC03-G2 | RLS / `app.tenant_id` / `search_path` が設計どおり機能 | DB smoke / tenant-cross test |
| SEC03-G3 | commit後の tenant context reset / schema prefix 方針が守られる | ADR-072 lint / router scan |
| SEC03-G4 | アプリ用DBロールは必要最小権限 | DB role recon |
| SEC03-G5 | migration は危険変更としてPO GO対象 | PR gate / CODEOWNERS / release process |

### recon対象ファイル

- `backend/app/database.py`
- `backend/app/auth/dependencies.py`
- `backend/app/routers/**`
- `migrations/**`
- `scripts/run_all_migrations.sh`
- `.github/workflows/deploy.yml`

---

## 6. SEC-04 バックエンドAPIセキュリティ

### KGI

公開APIと内部APIの境界を明確化し、入力改ざん・IDOR・署名不備・SQL注入を防ぐ。

### 成功条件

- 認証不要API一覧が明文化されている。
- Webhook / OAuth callback は署名・state・one-time token等で保護されている。
- ID指定APIで他テナントデータにアクセスできない。
- raw SQL はbind parameterまたは安全なschema helperを使う。
- PDF/CSV等の出力に機密情報が過剰混入しない。

### recon対象ファイル

- `backend/app/main.py`
- `backend/app/routers/**`
- `backend/app/services/**`
- `backend/app/models.py`
- `backend/tests/**`

---

## 7. SEC-05 フロントエンドセキュリティ

### KGI

ブラウザ上でトークン・個人情報・管理機能が不必要に露出しない状態にする。

### 成功条件

- UI上の権限表示とAPI側権限が一致する。
- XSSにつながるHTML注入がない。
- エラー画面にSecretや内部スタックを出さない。
- 外部script / connect先はCSPと整合する。
- Firebase公開設定にSecret相当の値を混入しない。

### recon対象ファイル

- `frontend/src/**`
- `frontend/nginx.conf`
- `frontend/Dockerfile`
- `nginx/nginx.conf`
- `frontend/package.json`

---

## 8. SEC-06 インフラ・Dockerセキュリティ

### KGI

サーバー侵害・コンテナ脱出・不要公開・権限過多を防ぐ。

### 成功条件

- Firewallで必要ポートのみ開放されている。
- SSHは鍵認証・root login無効・不要ユーザーなし。
- コンテナは原則non-root / no-new-privileges。
- DB/Redisは外部公開されない。
- 永続volumeと秘密ファイルの権限が最小。

### recon対象ファイル/環境

- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- VPS firewall / SSH設定（実サーバー確認が必要）
- Docker daemon / volume permissions（実サーバー確認が必要）

---

## 9. SEC-07 CI/CD・GitHubセキュリティ

### KGI

CI/CD経由のSecret漏洩・無承認本番変更・危険変更混入を防ぐ。

### 成功条件

- GitHub Secrets をログ出力しない。
- `deploy.yml` / `migrations/` / production scripts はPO GO対象。
- branch protection / CODEOWNERS / required checks がセキュリティ方針と一致する。
- security lint / dependency scan / secret scan が導入されている。
- 書類のみPRと危険変更PRの判定が自動化されている。

### recon対象ファイル

- `.github/workflows/**`
- `.github/CODEOWNERS`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `scripts/**`
- `docs/STANDARD-WORKFLOW.md`

---

## 10. SEC-08 監視・ログ・検知

### KGI

攻撃・誤操作・大量取得・認証異常に早く気づける状態にする。

### 成功条件

- 認証失敗・403・管理操作・書き込み操作が記録される。
- 大量アクセス/大量エクスポートが検知される。
- Redis不通・rate limit fail-open がアラート化される。
- 監視画面自体が保護されている。
- 重要アラートはDiscord等に通知される。

### recon対象ファイル

- `backend/app/middleware/audit.py`
- `backend/app/middleware/rate_limit.py`
- `backend/app/middleware/session_guard.py`
- `monitoring/**`
- `nginx/nginx.conf`
- `.github/workflows/deploy.yml`

---

## 11. SEC-09 バックアップ・復旧セキュリティ

### KGI

壊れても戻せる、漏れても切り戻せる、鍵を失っても復旧方針がある状態にする。

### 成功条件

- pre-deploy DB backup が動作している。
- 復元テストが定期的に実施される。
- 暗号鍵のバックアップ・ローテーション手順がある。
- 自動ロールバックの成功/失敗が通知される。
- インシデント時の手順が文書化されている。

### recon対象ファイル/環境

- `scripts/backup.sh`
- `.github/workflows/deploy.yml`
- `docs/operations/**`
- VPS backup directory（実サーバー確認が必要）
- Secret/key backup storage（PO確認が必要）

---

## 12. SEC-10 外部連携セキュリティ

### KGI

外部サービス連携トークンの漏洩・過剰権限・callback改ざん・Webhook偽装を防ぐ。

### 対象

- Meta / Facebook / Instagram
- Discord
- Google Drive / Google Calendar
- FedEx
- Gemini
- OAuth / Webhook / API tokens

### 成功条件

- 各連携のToken/Secret/Scope一覧が明文化されている。
- OAuth state はone-timeかつ期限付き。
- Webhook署名検証がある。
- トークン保存時は暗号化される。
- トークンローテーション・無効化手順がある。

### recon対象ファイル

- `backend/app/routers/meta*.py`
- `backend/app/routers/webhook.py`
- `backend/app/routers/discord_*.py`
- `backend/app/routers/google_calendar.py`
- `backend/app/routers/integrations.py`
- `backend/app/services/**`
- `docker-compose.yml`
- `.github/workflows/deploy.yml`

---

## 13. 運用ルール

1. SEC領域は **1件ずつ** 進める。
2. 各SEC領域の着手前に、`docs/adr/FEATURE-INDEX.md` と `git grep -i "<keyword>" docs/adr/` 相当のADR確認を行う。
3. reconは `docs/handoff/security/sec-XX-<name>/recon.md` に保存し、必ず `file:line` 引用を含める。
4. 設計は `docs/handoff/security/sec-XX-<name>/design.md` に保存し、KGI・recon・ADR・検証方法を相互参照する。
5. 実装PRは小さく分ける。
6. `migrations/` / `.github/workflows/deploy.yml` / 本番 `scripts/` を触る場合は、Shingoの明示GOなしに develop へ入れない。
7. 実サーバー値（`.env` / firewall / SSH / Grafana設定等）はGitHubからは見えないため、recon上は「GitHubでは不明」と明記し、実機確認で埋める。

---

## 14. 次の着手

次は SEC-01 入口セキュリティを開始する。

作成予定:

- `docs/handoff/security/sec-01-entry/recon.md`
- `docs/handoff/security/sec-01-entry/design.md`

SEC-01の最初の論点:

1. `X-Forwarded-For` 偽装対策
2. Grafana / Uptime Kuma / status 画面の保護
3. Nginx / backend のrate limit責務分担
4. TLS / CSP / CORS / API-only domain の再確認
5. Secret fail-close は SEC-01 と SEC-02 の境界論点として扱う
