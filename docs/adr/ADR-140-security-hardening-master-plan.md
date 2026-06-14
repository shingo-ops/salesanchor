# ADR-140: Security Hardening Master Plan（SEC-MASTER）

## ステータス

Proposed（PO合意: 2026-06-14 / Issue #2166）

## 日付

2026-06-14

## コンテキスト

Sales Anchor は B2B SaaS として、顧客情報、受発注、請求、在庫、外部連携トークン、監査ログ、運用ダッシュボード等を扱う。

現状のコードベースには、Nginx入口、Dockerネットワーク分離、Firebase認証、MFA、テナント分離、Audit / RateLimit / SessionGuard、blue-green deploy、DBバックアップ等の基盤が存在する。一方で、セキュリティ改善は個別ADR・個別実装として積み上がっており、Sales Anchor全体を横断するセキュリティ領域定義、KGI、成功条件、recon対象、検証方法が統一されていない。

このまま個別修正を進めると、以下のリスクがある。

- 思いつき修正により、本番可用性や認証導線を壊す。
- セキュリティ改善の完了条件が曖昧になる。
- 危険変更（`migrations/` / `.github/workflows/deploy.yml` / 本番 `scripts/`）に必要なPO承認ゲートが抜ける。
- 入口、認証、DB、CI/CD、外部連携など横断領域の優先順位が曖昧になる。
- Generator が How を自己流に再設計する余地が残る。

そのため、先に Security Hardening Master Plan を定義し、各領域のKGIを明文化したうえで、1領域ずつ `KGI → recon → 設計 → 実装 → 検証` で進める。

## recon / 既存正本

このADRは実装変更ではなく、SEC-MASTER定義の起案である。着手前に以下を確認した。

| 確認対象 | 根拠 | 判断 |
|---|---|---|
| 標準ワークフロー | `docs/STANDARD-WORKFLOW.md:20-37` | 全タスクはKGI→recon→設計。reconはfile:line引用必須。 |
| 不明点プロトコル | `docs/STANDARD-WORKFLOW.md:41-45` | 推測で埋めず、不明はPO相談。 |
| 危険変更ルール | `docs/STANDARD-WORKFLOW.md:57-68` | `migrations/`・`deploy.yml`・本番`scripts/`は人間承認対象。 |
| ADR索引ルール | `docs/adr/FEATURE-INDEX.md:3-10` | 主要機能/横断領域はFEATURE-INDEXに追記する。 |
| 既存セキュリティ関連ADR | `docs/adr/FEATURE-INDEX.md:29-44` | 認証、RLS、Meta/Webhook、SOP、リリース危険変更は既存ADRがある。 |
| SA進捗表 | `docs/plans/sa-progress/00-SA-OVERVIEW.md:12-25` | SAは全8件で、SEC-MASTERは未定義。 |
| SA進め方 | `docs/plans/sa-progress/00-SA-OVERVIEW.md:47-53` | 1件ずつ進め、不可逆変更はShingo GO必須。 |

## 決定

Sales Anchor に `SEC-MASTER` を新しい横断セキュリティ定義として追加する。

SEC-MASTER の目的は、Sales Anchor を「完璧」ではなく、以下を満たす堅牢なSaaS基盤にすることである。

1. 侵入されにくい。
2. 設定ミスで崩れにくい。
3. 万一漏れても被害が広がりにくい。
4. 異常に早く気づける。
5. 復旧できる。
6. セキュリティ変更を標準ワークフローで安全に進められる。

SEC-MASTER の運用SSOTは `docs/security/SEC-MASTER.md` とする。本ADRは意思決定、`docs/security/SEC-MASTER.md` は各領域のKGI・成功条件・recon対象・検証方法を継続管理する実務SSOTとする。

## 全体KGI

Sales Anchor の顧客データ、認証情報、外部連携トークン、受発注・請求・在庫データ、監査ログ、運用情報を安全に扱えるSaaS基盤を構築する。

## 全体成功条件

- Critical / High 相当の既知セキュリティ欠陥が、未対策・未記録のまま残っていない。
- 認証なしで管理者操作できるAPIが 0 件。
- テナント越境アクセスが 0 件。
- 本番必須Secret未設定のまま起動できる経路が 0 件。
- 外部公開すべきでない監視・管理画面の無防備公開が 0 件。
- DBバックアップからの復元手順が検証済み。
- 危険変更（`migrations/` / `.github/workflows/deploy.yml` / 本番 `scripts/`）はPO GOなしに develop へ入らない。
- 各セキュリティ領域に KGI / recon対象 / 受け入れ基準 / 検証方法が存在する。

## セキュリティ領域

SEC-MASTER は以下10領域で管理する。

| ID | 領域 | KGI |
|---|---|---|
| SEC-01 | 入口セキュリティ | 外部から到達できる入口を最小化し、IP偽装・過剰公開・TLS/CSP不備による攻撃面を潰す。 |
| SEC-02 | 認証・認可セキュリティ | 正規ユーザーだけが、許可された操作だけを実行できる状態にする。 |
| SEC-03 | DB・テナント分離セキュリティ | テナント越境・DB過剰権限・migration事故を防ぎ、1テナントの事故が他テナントへ波及しない状態にする。 |
| SEC-04 | バックエンドAPIセキュリティ | 公開APIと内部APIの境界を明確化し、入力改ざん・IDOR・署名不備・SQL注入を防ぐ。 |
| SEC-05 | フロントエンドセキュリティ | ブラウザ上でトークン・個人情報・管理機能が不必要に露出しない状態にする。 |
| SEC-06 | インフラ・Dockerセキュリティ | サーバー侵害・コンテナ脱出・不要公開・権限過多を防ぐ。 |
| SEC-07 | CI/CD・GitHubセキュリティ | CI/CD経由のSecret漏洩・無承認本番変更・危険変更混入を防ぐ。 |
| SEC-08 | 監視・ログ・検知 | 攻撃・誤操作・大量取得・認証異常に早く気づける状態にする。 |
| SEC-09 | バックアップ・復旧セキュリティ | 壊れても戻せる、漏れても切り戻せる、鍵を失っても復旧方針がある状態にする。 |
| SEC-10 | 外部連携セキュリティ | 外部サービス連携トークンの漏洩・過剰権限・callback改ざん・Webhook偽装を防ぐ。 |

## 実施順序

| Phase | 内容 | 完了条件 |
|---|---|---|
| Phase 0 | SEC-MASTER ADR / SA定義追加 / Issue化 | 本ADR、FEATURE-INDEX、SA進捗表、`docs/security/SEC-MASTER.md` が追加される。 |
| Phase 1 | SEC-01 入口セキュリティ recon & design | Nginx/TLS/proxy/rate limit/monitoring公開範囲のfile:line reconと設計が揃う。 |
| Phase 2 | SEC-02 認証・認可 recon & design | Firebase/MFA/JWT/admin/super-admin/smoke bypassのreconと設計が揃う。 |
| Phase 3 | SEC-03 DB・テナント分離 recon & design | RLS/search_path/app.tenant_id/DB role/migration安全性のreconと設計が揃う。 |
| Phase 4 | SEC-04〜SEC-10 を順次 recon & design | 各領域を1件ずつ進める。 |
| Phase 5 | 各領域ごとに小PRで実装 | 危険変更はPO GO付きでfeature branch待機。 |
| Phase 6 | 継続監査・定期棚卸し | セキュリティKGIの定期測定・棚卸しを運用化する。 |

## 受け入れ基準

- `docs/adr/FEATURE-INDEX.md` に `security / hardening / cyber security / SEC-MASTER` の行が追加される。
- `docs/plans/sa-progress/00-SA-OVERVIEW.md` に SEC-MASTER が追加される。
- `docs/security/SEC-MASTER.md` が追加され、10領域のKGI・成功条件・recon対象・検証方法が定義される。
- このPRでは実装変更を行わない。
- 最初の実装対象は SEC-01 とする。

## 対象外

このADR/定義追加PRでは、以下を対象外とする。

- Nginx設定の変更。
- backend / frontend の実装変更。
- DB migration。
- `.github/workflows/deploy.yml` の変更。
- 本番 `scripts/` の変更。
- 実サーバー `.env` / Firewall / SSH の直接変更。

## リスクと対策

| リスク | 対策 |
|---|---|
| SEC-MASTERが大きすぎて一括実装になる | 10領域に分解し、SEC-01から1件ずつ進める。 |
| Secret fail-close 等で本番起動を壊す | 実装PRでは事前に `.env` 実値存在確認・feature branch検証・PO GOを必須にする。 |
| proxy header修正でログ/RateLimitのIPが変わる | SEC-01でNginxとbackendの受け渡し仕様をreconし、受け入れテストを設計する。 |
| DB権限強化でmigration/admin処理が壊れる | SEC-03で別PR化し、migration smokeを必須にする。 |
| 監視画面制限で運用アクセスが不便になる | Basic認証 / IP制限 / VPN の方式をPO確認事項にする。 |

## 関連

- Issue #2166
- `docs/security/SEC-MASTER.md`
- `docs/STANDARD-WORKFLOW.md`
- `docs/adr/FEATURE-INDEX.md`
- ADR-023 / ADR-032: 認証・Firebase
- ADR-024 / ADR-025 / ADR-041 / ADR-026: Meta / Webhook
- ADR-050 / ADR-056: リリース / human-in-the-loop
- ADR-072 / ADR-131 / ADR-132: テナントコンテキスト / RLS周辺
- ADR-121 / ADR-112: SOP / process-artifacts gate
- ADR-135: リリース相乗り防止 / 危険変更ゲート

## 次アクション

1. 本ADRをPO承認する。
2. SEC-01 入口セキュリティの `docs/handoff/security/sec-01-entry/recon.md` を作成する。
3. SEC-01のreconでは、最低限以下をfile:lineで確認する。
   - `nginx/nginx.conf`
   - `docker-compose.yml`
   - `backend/app/main.py`
   - `backend/app/middleware/rate_limit.py`
   - `backend/app/middleware/session_guard.py`
   - `backend/app/middleware/audit.py`
4. SEC-01設計で、X-Forwarded-For偽装対策、監視画面保護、Secret fail-closeの実装順を確定する。
