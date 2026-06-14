# ADR-140: Security Hardening Master Plan（SEC-MASTER）

## ステータス

Proposed（PO合意済み・定義追加PR対象 / Issue #2166）

## 日付

2026-06-14

## コンテキスト

Sales Anchor は B2B SaaS として、顧客情報、受発注、請求、在庫、外部連携トークン、監査ログ、運用ダッシュボード等を扱う。

既存実装には、Nginx 入口、Docker ネットワーク分離、Firebase 認証、MFA、テナント分離、Audit / RateLimit / SessionGuard、blue-green deploy、DB バックアップ等の基盤が存在する。一方で、セキュリティ改善は個別 ADR・個別 PR として積み上がっており、領域ごとの KGI・成功条件・recon 対象・検証方法が統一定義されていない。

この状態で個別修正を進めると、思いつき修正で本番可用性や認証導線を壊す、危険変更（`migrations/` / `deploy.yml` / production `scripts/`）に必要な PO 承認ゲートが抜ける、Generator が How を自己流に再設計する、といったリスクがある。

そのため、先に Security Hardening Master Plan を定義し、各領域の KGI を明文化したうえで、1領域ずつ `KGI → recon → 設計 → 実装 → 検証` で進める。

## 参照ルール

- 正本: `docs/STANDARD-WORKFLOW.md`
- ADR索引: `docs/adr/FEATURE-INDEX.md`
- 運用SSOT: `docs/security/SEC-MASTER.md`
- 起案Issue: #2166

関連ADR候補:

- ADR-023 / ADR-032: Firebase / 認証3層同期
- ADR-024 / ADR-025 / ADR-041 / ADR-026: Meta / Webhook
- ADR-050 / ADR-056: release / human-in-the-loop / 自動merge
- ADR-072: tenant schema prefix / reset_tenant_context
- ADR-075: GitHub Secrets 一元管理ポリシー
- ADR-115: デプロイ安全策
- ADR-121 / ADR-112: 標準ワークフロー / process-artifacts gate
- ADR-131 / ADR-132: テナントコンテキスト保護
- ADR-135: 危険変更の develop 入口関所 / develop=出荷可能

## 決定

Sales Anchor に `SEC-MASTER` を横断セキュリティ定義として追加する。

`SEC-MASTER` の目的は、Sales Anchor を「完璧」ではなく、以下を満たす堅牢な SaaS 基盤にすることである。

1. 侵入されにくい。
2. 設定ミスで崩れにくい。
3. 万一漏れても被害が広がりにくい。
4. 異常に早く気づける。
5. 復旧できる。
6. セキュリティ変更を標準ワークフローで安全に進められる。

## 全体KGI

Sales Anchor の顧客データ、認証情報、外部連携トークン、受発注・請求・在庫データ、監査ログ、運用情報を安全に扱える SaaS 基盤を構築する。

## 全体成功条件

- Critical / High 相当の既知セキュリティ欠陥が、未対策・未記録のまま残っていない。
- 認証なしで管理者操作できる API が 0 件。
- テナント越境アクセスが 0 件。
- 本番必須 Secret 未設定のまま起動できる経路が 0 件。
- 外部公開すべきでない監視・管理画面の無防備公開が 0 件。
- DB バックアップからの復元手順が検証済み。
- 危険変更（`migrations/` / `deploy.yml` / production `scripts/`）は PO GO なしに develop へ入らない。
- 各セキュリティ領域に KGI / recon 対象 / 受け入れ基準 / 検証方法が存在する。

## セキュリティ領域定義

- SEC-01 入口セキュリティ: Nginx, TLS, CSP, CORS, proxy headers, rate limit, monitoring exposure。KGI は外部入口を最小化し、IP偽装・過剰公開・TLS/CSP不備による攻撃面を潰すこと。
- SEC-02 認証・認可セキュリティ: Firebase, MFA, JWT, admin, super-admin, role/permission, smoke service bypass。KGI は正規ユーザーだけが許可された操作だけを実行できる状態にすること。
- SEC-03 DB・テナント分離セキュリティ: PostgreSQL, RLS, schema prefix, search_path, app.tenant_id, DB role, migrations。KGI はテナント越境・DB過剰権限・migration事故を防ぐこと。
- SEC-04 バックエンドAPIセキュリティ: FastAPI routers, public endpoints, webhook, OAuth callback, input validation, IDOR, SQL injection, file generation。KGI は公開APIと内部APIの境界を明確化し、入力改ざん・IDOR・署名不備・SQL注入を防ぐこと。
- SEC-05 フロントエンドセキュリティ: React/Vite, token handling, XSS, route guard, error exposure, external scripts。KGI はブラウザ上でトークン・個人情報・管理機能が不必要に露出しない状態にすること。
- SEC-06 インフラ・Dockerセキュリティ: VPS, firewall, SSH, Docker daemon, containers, networks, volumes, OS packages。KGI はサーバー侵害・コンテナ脱出・不要公開・権限過多を防ぐこと。
- SEC-07 CI/CD・GitHubセキュリティ: GitHub Actions, Secrets, deploy.yml, branch protection, CODEOWNERS, process gate。KGI はCI/CD経由のSecret漏洩・無承認本番変更・危険変更混入を防ぐこと。
- SEC-08 監視・ログ・検知: Audit log, auth failures, bulk access, rate limit, Grafana, Uptime Kuma, Discord alerts。KGI は攻撃・誤操作・大量取得・認証異常に早く気づける状態にすること。
- SEC-09 バックアップ・復旧セキュリティ: DB backup, restore drill, rollback, key backup, incident runbook。KGI は壊れても戻せる、漏れても切り戻せる、鍵を失っても復旧方針がある状態にすること。
- SEC-10 外部連携セキュリティ: Meta, Discord, Google, FedEx, Gemini, OAuth, webhook, API tokens。KGI は外部サービス連携トークンの漏洩・過剰権限・callback改ざん・Webhook偽装を防ぐこと。

各領域の詳細な成功条件・recon対象・検証方法は `docs/security/SEC-MASTER.md` をSSOTとする。

## 実施順序

- Phase 0: SEC-MASTER ADR / SA定義追加 / Issue化
- Phase 1: SEC-01 入口セキュリティ recon & design
- Phase 2: SEC-02 認証・認可 recon & design
- Phase 3: SEC-03 DB・テナント分離 recon & design
- Phase 4: SEC-04〜SEC-10 を順次 recon & design
- Phase 5: 各領域ごとに小PRで実装
- Phase 6: 継続監査・定期棚卸し

## 受け入れ基準

- `docs/adr/FEATURE-INDEX.md` に `security / hardening / SEC-MASTER` の行が追加される。
- SA進捗/定義ファイルに `SEC-MASTER` が追加される。
- `docs/security/SEC-MASTER.md` に各SEC領域の KGI / 成功条件 / recon対象 / 検証方法が定義される。
- 最初の実装対象は SEC-01 とする。
- 危険変更を含む場合は PO GO コメントを必須にする。

## リスクと対策

- Secret fail-close により本番起動失敗の可能性。
  - 先に現行 `.env` 実値の存在確認を行い、feature branch で検証する。
- proxy header 修正によりログ / RateLimit の IP が変わる可能性。
  - Nginx・backend の両方で受け渡し仕様をテストする。
- Grafana / Uptime Kuma 制限により監視アクセスが不便になる可能性。
  - Basic認証 / 許可IP / VPN のいずれにするか PO と合意する。
- DB権限強化により migration / admin 処理が失敗する可能性。
  - SEC-03 で別PR化し、migration smoke を必須にする。

## 結果

本ADRでは実装変更を行わない。まず Security Hardening の全体KGI、10領域定義、SAロードマップ上の扱い、ADR索引の導線を確定する。

実装は後続の SEC-01 以降で、各領域ごとに `KGI → recon → 設計 → 実装 → 検証` の単位で進める。
