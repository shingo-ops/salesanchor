# recon: runbook 事実食い違いの修正前調査

- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-runbook-fact-fix
- ブランチ: release/runbook-fact-fix（origin/main 起点）
- HEAD: 2a5512eec25c1fc5feda85907e47ad5976588885
- 範囲: 事実のみ。判定・推測は書かない。確かめられなかった点は「未確認」と書く。値（鍵・トークン）は書かない。
- 記載方針: 不可逆な操作（強制リセット、DROP、rm -rf、force push、ssh、psql 等）のコマンド文字列は書かず、行の場所と短い説明で示す（設計担当の方針）。
- 引用の `パス:行` は上記 HEAD のファイル。

## §1 食い違い一覧（15文書・39行）

出所: /tmp/CC報告ファイル/an-stage1/proto2/inventory/round3-mismatch.txt（転記。依頼文は「37件」、一覧ファイルの表の行数は 39）。
列は「# = 文書内の項番」「行 = 文書の行番号」「主張 = 文書の記述」「実物 = 一覧ファイルが記録した実物」。不可逆操作の文字列は説明に置き換えた（置換は10行目の1か所と、SSH 接続の語）。

#### .github/workflows/README.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 2 | 7 | 通知対象イベントのタイトル（PR作成 等の表） | discord-pr-notify.yml のタイトルは「PR #N が作成されました」「…再オープンされました」「…マージされました」「…クローズされました（未マージ）」「PR #N にレビュー(…)が投稿されました」。README表の文言とは異なる | 不一致 |
| 6 | 50 | 1件以上 fail (failure / timed_out) → Some checks failed | discord-ci-notify.yml: 「Some checks failed」。失敗扱いは failure/timed_out/action_required（action_required が README に無い） | 不一致 |
| 7 | 59 | 必要な Secrets（DISCORD_WEBHOOK_PR を共用） | discord-ci-notify.yml:100 secrets.DISCORD_WEBHOOK_CI を使用（DISCORD_WEBHOOK_PR ではない） | 不一致 |
| 10 | 75 | デプロイ手順: VPSに接続 → pull で取り込み → docker compose の起動に build 付き | deploy.yml: appleboy の SSH 接続用アクション、取り込み方式（fetch のあと作業コピーを origin/main に強制的に合わせる）、.env.secrets.new を .env へ追記、blue-green 切替、docker compose の --no-deps --remove-orphans 付き起動（frontend celery-worker celery-beat discord-gateway gemini-egress）。pull / build 付き起動の方式ではない | 不一致 |
| 11 | 86 | 必要な Secrets は VPS_HOST / VPS_USER / SSH_PRIVATE_KEY の3つ | deploy.yml は上記3つに加え META_VERIFY_TOKEN, META_APP_SECRET, PIPELINE_PAT(:64,:896) など多数を参照 | 不一致 |
| 12 | 1 | このREADMEが扱うワークフローは3本 | 実物 .github/workflows は76エントリ（README除く）。README掲載は3本のみ。未掲載73本 | 不一致 |

#### docs/B-04_incident_response_playbook.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 1 | 3 | 対象: Sales Anchor（jarvis-claude.uk） | deploy.yml:808 jarvis-claude.uk/api/health を確認。CLAUDE.md は Legacy（並行稼働中）。本番は app/api.salesanchor.jp | 不一致 |
| 7 | 30 | DB接続のユーザー名 myapp_user・DB名 myapp_db | deploy.yml:514,815 と backup.sh は jarvis / jarvis_db。myapp_* は .env.example:9-12・backend/app/database.py:8 の既定値のみ | 不一致 |

#### docs/B-13_mgmt-vps-governance.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 1 | 6 | ADR-080 による分離後、… | ADR-080 は docs/adr/README.md:90 でステータスが Proposed（文書は分離済み前提） | 不一致 |
| 11 | 211 | 期待アラート: PostgresDown / HighErrorRate / High502Rate | alert_rules.yml に PostgresDown, HighErrorRate, High502Rate は無い（BackendHighErrorRate 等） | 不一致 |
| 14 | 225 | Grafana → Alerting → Contact points → discord-ops | monitoring 配下に discord-ops は無い（alertmanager receiver は discord-server-alerts 等）。Grafana UI内の設定自体は確認不可 | 不一致 |

#### docs/D-06_firebase_credentials_setup.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 7 | 152 | curl https://jarvis-claude.uk/api/v1/customers | ADR-089 Accepted で customers 廃止。/api/v1/customers のルータ定義は grep で無し（duplicates.py:146 に削除済みコメントのみ） | 不一致 |
| 8 | 166 | /api/v1/admin/tenants | ルータ定義無し（実物は /api/v1/super-admin/tenants） | 不一致 |
| 9 | 181 | /api/v1/dashboard | ルータ定義の grep ヒット無し | 不一致 |
| 11 | 210 | GitHub Secretsで管理 | deploy.yml に firebase 関連secret無し（grep 0件）。ファイルはVPSへ手置き | 不一致 |

#### docs/DATA_CLASSIFICATION.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 1 | 16 | 顧客名・連絡先 → customers テーブル | ADR-089 Accepted（customers テーブル廃止）。docs/adr/README.md:100 | 不一致 |
| 4 | 24 | パスワードハッシュ users.password_hash bcrypt（12ラウンド） | migrations/20260612_150000_drop_password_hash.sql で列廃止、ADR-1013 は argon2-cffi(requirements.txt:50)。bcrypt12は bots.py:58 のbot APIキー用 | 不一致 |
| 11 | 49 | パスワードはbcryptハッシュ | 24行目と同じ（廃止 / argon2） | 不一致 |

#### docs/INCIDENT_RESPONSE.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 3 | 20 | インシデントチャンネルを開設（Slack等） | alertmanager の receiver は discord-server-alerts / discord-recovery-info / ops-api。Slack は alert_rules.yml:2 のコメントのみ | 不一致 |
| 14 | 151 | Slack #jarvis-alerts 自動アラート通知 | 自動アラートは Discord（alertmanager）。#jarvis-alerts は repo 内に存在しない | 不一致 |

#### docs/ops/self-hosted-runner-credential-trap.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 2 | 13 | Claude Max Auto-Pipeline の Checkout Code が失敗 | claude-pipeline.yml は origin/main に存在しない（runner-label-lint.yml:3,35 に言及のみ） | 不一致 |

#### docs/runbooks/discord-gateway-operations.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 2 | 13 | 環境変数 DISCORD_BOT_TOKEN_<TENANT_ID> を1つ以上設定 | docker-compose.yml:362 は共通 DISCORD_BOT_TOKEN 1本（コメント「ADR-146 B方式: 共通 Bot Token」）。テナント別トークンの参照は無し | 不一致 |
| 3 | 24 | VPS systemd unit /etc/systemd/system/sales-anchor-discord-gateway.service | git grep（sales-anchor-discord-gateway と systemctl の discord）はこの文書以外0件。実物は docker-compose.yml:350 `discord-gateway:`（command: python -m app.discord_gateway.main, restart: unless-stopped）。deploy.yml が docker compose の --no-deps 付き起動で discord-gateway を起動 | 不一致 |
| 4 | 37 | WorkingDirectory=/opt/sales-anchor/backend | /opt/sales-anchor はリポジトリ内に存在しない（compose内は /app） | 不一致 |
| 5 | 38 | EnvironmentFile=/etc/sales-anchor/discord-gateway.env | リポジトリ内に該当無し。実物は .env 注入（deploy.yml） | 不一致 |
| 6 | 62 | systemctl の daemon-reload / enable / start | compose運用のため該当しない。systemd運用は実物に無い | 不一致 |
| 7 | 86 | journalctl で確認、systemctl restart で復旧 | compose運用では docker compose logs / restart | 不一致 |
| 9 | 93 | inventory_parser_llm.py の GEMINI_API_KEY | backend/app/services に inventory_parser_llm.py 無し | 不一致 |

#### docs/runbooks/review-tenant-operations.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 1 | 1 | review-tenant-operations Runbook (ADR-028) | ADR-028 は docs/adr/README.md:42 で Superseded | 不一致 |
| 11 | 121 | password_hash列への参照: ADR-138 対応済み | ADR-138 は README.md:158 で Superseded（ADR-1013 が Supersede）。migration 20260612_150000 が列廃止 | 不一致 |

#### docs/runbooks/tenant-deletion-operations.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 10 | 110 | GO記録は GitHub PR コメントまたは Slack | CLAUDE.md の GO 手順は PR コメント。Slack は規定無し | 不一致 |

#### docs/SECURITY_ENHANCEMENT_ROADMAP.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 1 | 4 | 対象: Sales Anchor (https://jarvis-claude.uk) | Legacy。本番は app.salesanchor.jp | 不一致 |
| 3 | 40 | 静的解析CI: Gitleaks/Trivy/Semgrep を GitHub Actions に組込済 | gitleaks/trivy/semgrep の文字列があるのは secret-scan.yml のみ（他は scripts/tests/test-claude-archive.sh）。security-scan.yml は npm audit と pip-audit。3種全ての組込は確認できず | 不一致 |

#### docs/SECURITY.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 3 | 60 | bcryptパスワードハッシュ（12ラウンド） | password_hash列は廃止（migration 20260612_150000）、ADR-1013 は Argon2id。bcryptはbots.py:58のみ | 不一致 |

#### docs/TEST_ADMIN_PASSWORD_CHANGE_PROCEDURE.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 6 | 97 | ブラウザで https://jarvis-claude.uk を開いてログイン | Legacy URL（並行稼働中）。本番は app.salesanchor.jp | 不一致 |

#### docs/ZERO_TRUST_POLICY.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 9 | 47 | frontend/Redisでread_only | docker-compose.yml:473 の1か所のみ（redisブロック内）。frontendは read_only 無し | 不一致 |
| 10 | 48 | 全サービスにhealthcheck定義 | docker-compose.yml サービス11、healthcheck: 9か所 | 不一致 |

#### scripts/aws-setup/README.md

| # | 行 | 主張 | 実物 | 判定 |
|---|---|---|---|---|
| 11 | 169 | ログ >> /home/ubuntu/backups/s3_backup.log | backup_to_s3.sh と setup-s3-backup.sh のコメントは /var/log/s3_backup.log。ログパスが食い違う | 不一致 |
| 12 | 168 | S3転送の仕組みは日次転送のみ | backup_to_s3.sh は月次Glacierアーカイブ（monthly-archives/、毎月1日）、成功時刻textfile（backup_s3.prom）、Discord失敗通知（DISCORD_WEBHOOK_OPS）も行う。READMEに記載無し | 不一致 |

## §2 確認結果 P1〜P10

### P1 app.salesanchor.jp と jarvis-claude.uk の裏側

ファイル: nginx/nginx.conf（リポジトリ内の nginx 設定。frontend/nginx.conf は server_name localhost のみで、proxy_pass は無い: frontend/nginx.conf:3）

- nginx/nginx.conf:11-13 `server { listen 80; server_name jarvis-claude.uk;`
- nginx/nginx.conf:29-31 `server { listen 443 ssl; server_name jarvis-claude.uk;`
- nginx/nginx.conf:37-38 `location / { return 301 https://app.salesanchor.jp$request_uri;`（jarvis-claude.uk の 443 ブロックの location。proxy_pass は無い）。直前のコメント（nginx/nginx.conf:25-27）は「HTTPS設定 - リダイレクト専用（Phase 5 移行完了・2026-06-10）… 全パスを app.salesanchor.jp へ転送する」。
- nginx/nginx.conf:53-56 `server { listen 80; … server_name app.salesanchor.jp;`
- nginx/nginx.conf:67-71 `server { listen 443 ssl; … server_name app.salesanchor.jp;`
- app 側 443 ブロックの resolver と変数: `resolver 127.0.0.11 valid=5s;` `set $backend backend;` `set $frontend frontend;`（nginx/nginx.conf:92-96 付近）
- app.salesanchor.jp の proxy_pass: nginx/nginx.conf:101,116,131,146,159,179,199,221,295 は `proxy_pass http://$backend:8000;`、:304 は `proxy_pass http://$frontend:8080;`、:233 は `proxy_pass http://49.212.160.98:3000/grafana/;`、:250 は `proxy_pass http://49.212.160.98:3001/;`、:263 は `proxy_pass http://49.212.160.98:9091/metrics/job/sop-health-reporter/;`
- api.salesanchor.jp: nginx/nginx.conf:320（80）と :335（443）が `server_name api.salesanchor.jp;`。proxy_pass は :363,378,393,408,421,441,461,487,502 すべて `http://$backend:8000;`。
- jarvis-claude.uk の server ブロック（nginx/nginx.conf:11-51）に proxy_pass の行は無い。

deploy.yml の jarvis-claude.uk を含む行（全体で1行のみ）:
- .github/workflows/deploy.yml:808 `curl -sf https://jarvis-claude.uk/api/health || echo "External health check warning"`

docker-compose.yml に jarvis-claude の記載は無い（grep 0件）。

### P2 ADR の Status 行

- ADR-146: docs/adr/ に ADR-146 のファイルは HEAD に無い（`ls docs/adr | grep 146` が 0件、`git ls-files | grep -i adr-146` が 0件）。docs/adr/README.md にも ADR-146 の行は無い。ADR-146 への言及は docker-compose.yml:109,346,361 のコメントのみ（例 :361「ADR-146 B方式: 共通 Bot Token（テナント共通 — 1本のみ）」）。docs/adr 配下の言及は 0件。Status は ADR 本文が HEAD に無いため確認できない（ファイルが無いという事実のみ記載）。
- ADR-028: docs/adr/ADR-028-screencast-tenant-isolation.md:5 `| ステータス | Superseded by `scripts/setup_review_tenant.py` + `docs/META_APP_REVIEW_PRE_RECORDING_CHECKLIST.md` |`。docs/adr/README.md:42 は `Superseded`。
- ADR-089: docs/adr/ADR-089-deprecate-customers-unify-to-companies.md:3-4 `## Status` / `Accepted`。docs/adr/README.md:100 は `Accepted`。
- ADR-138 は同番号でファイルが2本ある。
  - docs/adr/ADR-138-remove-password-hash.md:3 `**ステータス**: Superseded by [ADR-1013](./ADR-1013-self-hosted-auth-and-passkey.md)（2026-10-13。移行の便6 が終わるまで、本番の実装は本 ADR のとおり Firebase 専一のまま）`。docs/adr/README.md:158 は `Superseded`。docs/adr/README.md:194（ADR-1013 の行）に `Supersedes ADR-138`。
  - docs/adr/ADR-138-funnel-dashboard-stage1.md:3 `**Status**: Accepted`。docs/adr/README.md:157 は `Accepted`。
- ADR-1013（参考）: docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:5 `Accepted（PO 2026-10-13 …実装は便ごとに実装カードと PO の実装承認を経る）`、:8 `Supersedes ADR-138（Firebase 専一）。ADR-032 … と ADR-023 … は便6 完了時に Superseded とする。`
- ADR-080: docs/adr/ADR-080-monitoring-vps-separation.md:5 `| ステータス | Proposed |`。docs/adr/README.md:90 は `Proposed`。

### P3 自社ログイン（AUTH_PROVIDER=self）のパスワード保存

- 表・列: public.users.password_argon2_hash（TEXT NULL）、public.users.password_changed_at（TIMESTAMPTZ NULL）
  - migrations/20261013_160000_add_self_hosted_auth_tables.sql:6 `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_argon2_hash TEXT NULL;`
  - 同 :7 は password_changed_at の追加（:12 の COMMENT に記載）
  - :11 `COMMENT ON COLUMN public.users.password_argon2_hash IS 'Argon2id のハッシュ文字列。NULL はパスワード未設定（ADR-1013）';`
  - :2 コメント `列名 password_argon2_hash: password_hash は 20260612_150000_drop_password_hash.sql が毎デプロイ消すため使わない`
- 方式: backend/app/auth/passwords.py:1 `パスワードのハッシュ化と照合（Argon2id）。ADR-1013 便2。`、:11 `from argon2 import PasswordHasher`、:14 `_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)`、:20-21 `def hash_password(plain: str) -> str: return _HASHER.hash(plain)`
- 関連表（パスワード本体ではない）: public.password_reset_tokens（同 migration :47。token_hash は sha256 32バイト :63）、public.auth_refresh_tokens（:68）、public.webauthn_credentials（:16）。
- 旧列: migrations/20260612_150000_drop_password_hash.sql:9 は users.password_hash 列を削除する文（冪等）。:1-2 のコメント「認証は Firebase Authentication が担当しており DB への password_hash 保存は不要。」
- AUTH_PROVIDER: backend/app/auth/self_tokens.py:20 `DEFAULT_AUTH_PROVIDER = "firebase"  # firebase | self`、:37-38 `def auth_provider() -> str: return os.getenv("AUTH_PROVIDER", DEFAULT_AUTH_PROVIDER)…`、:76-78 `AUTH_PROVIDER must be one of: firebase, self` / `AUTH_JWT_SECRET is required when AUTH_PROVIDER=self`。自社ログインのルータ: backend/app/routers/auth.py:185 `自社ログイン（ADR-1013 便2。AUTH_PROVIDER=self のときだけ有効）`。
- docker-compose*.yml に AUTH_PROVIDER / AUTH_JWT の記載は無い（grep 0件）。
- Firebase モードでパスワードを持つ場所:
  - docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:15 「ログインは Firebase Authentication が全部受け持ち、自社 DB にパスワードは無い（ADR-138・2026-06-12）。」
  - docs/adr/ADR-138-remove-password-hash.md:12 「`public.users.password_hash` 列は bcrypt ハッシュを格納していたが、」、:19 「`public.users.password_hash` 列を物理削除する。」、:28 「登録フローが Firebase 専一になる」
  - docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:26 「移行時は、既存パスワードを Firebase から持ち出さず、使用中の全員に新しいパスワードを発行する。」
  - backend/app/auth/dependencies.py:213 `decoded = await asyncio.to_thread(firebase_auth.verify_id_token, token)`（Firebase ID トークンの検証）
- ADR-1013 の自社保管の決定: docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:24 「パスワードは Argon2id で保管する。長さ 15〜64 文字、漏洩・常用一覧の照合あり、定期変更なし。口座単位で 10 回失敗すると 15 分止める。」
- bcrypt の残り（bot API キー用）: backend/app/routers/bots.py:55-58
  - :55 `def _generate_api_key() -> tuple[str, str]:`
  - :56 `"""(平文APIキー, bcryptハッシュ) のタプルを返す"""`
  - :57 `plain = f"botkey_{secrets.token_urlsafe(32)}"`
  - :58 `hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")`

### P4 Firebase 関係の設定（名前のみ）

docker-compose.yml（他の docker-compose*.yml に firebase / GOOGLE_APPLICATION の記載は 0件）:
- backend サービス（docker-compose.yml:63 開始）: :68 `GCP_PROJECT_ID=${GCP_PROJECT_ID}`、:69 環境変数 GOOGLE_APPLICATION_CREDENTIALS にコンテナ内の資格ファイルのパスを設定、:143 でサーバー上の同名の資格ファイルを読み取り専用で mount（ファイル名は docker-compose.yml:69 と :143 を参照）
- celery-worker サービス（docker-compose.yml:215 開始）: :221 `GCP_PROJECT_ID=${GCP_PROJECT_ID}`、:222 環境変数 GOOGLE_APPLICATION_CREDENTIALS にコンテナ内の資格ファイルのパスを設定、:267 でサーバー上の同名の資格ファイルを読み取り専用で mount（ファイル名は docker-compose.yml:222 と :267 を参照）
- frontend サービスの build args（docker-compose.yml:179 開始）: :183 `VITE_FIREBASE_API_KEY: ${VITE_FIREBASE_API_KEY}`、:184 `VITE_FIREBASE_AUTH_DOMAIN: ${VITE_FIREBASE_AUTH_DOMAIN}`
- backend のコード: backend/app/auth/dependencies.py:62 `cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")`、:65 `firebase_admin.initialize_app(cred)`、:67 `firebase_admin.initialize_app()`（パス未設定時）
- ホスト側の置き場所: docker-compose.yml:143 と :267 に書かれた相対パス（compose ファイルと同じディレクトリ）。
- git 管理の確認: `git ls-files | grep -i firebase` の結果（HEAD）は次の14件。資格ファイルそのもの（docker-compose.yml:143 と :267 が指すファイル）は含まれない。
  - .github/workflows/rotate-qa-firebase.yml
  - docs/D-06_firebase_credentials_setup.md
  - docs/FIREBASE_API_KEY_RESTRICTION_GUIDE.md
  - docs/FIREBASE_CUSTOM_AUTH_DOMAIN_SETUP.md
  - docs/handoff/design-system-recon/evidence-20260910/modal-fixture-mock-firebase.ts
  - docs/runbooks/external-evidence/firebase/.gitkeep
  - frontend/src/lib/__storybook-mocks__/firebase-app.ts
  - frontend/src/lib/__storybook-mocks__/firebase-auth.ts
  - frontend/src/lib/firebase-auth.ts
  - frontend/src/lib/firebase.ts
  - frontend/src/lib/firebaseErrorMessage.test.ts
  - frontend/src/lib/firebaseErrorMessage.ts
  - scripts/smoke/external-firebase.sh
  - scripts/snapshot/firebase.sh
- deploy.yml の secrets.* に firebase を含む名前は無い（P8 の一覧）。

### P5 アラート名と receiver 名

monitoring/prometheus/alert_rules.yml の `alert:`（32個、行番号つき）:
HighCpuUsage:8, HighMemoryUsage:20, HighDiskUsage:32, CriticalDiskUsage:44, ServiceDown:58, BackendHighErrorRate:71, BackendHighLatency:83, BackendWorkerSaturated:95, BackendSseConnectionsHigh:107, F2CleanupStale:120, F2CleanupAbsent:130, KumaMonitorDown:144, CertExpiringSoon:156, CertInvalid:168, CeleryHeartbeatStale:183, CeleryTaskFailuresHigh:195, CeleryQueueBacklog:207, ViewerInventoryStale:221, ViewerInventoryStaleOnHold:232, BackupLocalStale:247, BackupS3Stale:260, BackupTimestampAbsent:272, MonitoringConfigDrift:286, MonitoringConfigCheckStale:299, ContainerUnhealthy:314, ContainerStateStale:326, ContainerHealthcheckMissing:338, ClockSkew:354, ClockSyncStopped:367, RecoveryCheckFailed:382, RecoveryCheckPassed:393, RecoveryCheckStale:404

monitoring/alertmanager/alertmanager.yml:
- :2 `receiver: discord-server-alerts`（既定）
- route 内: :10 `- receiver: discord-recovery-info`、:13 `- receiver: discord-server-alerts`、:15 `- receiver: ops-api`
- receivers: :17 `- name: discord-server-alerts`、:21 `- name: ops-api`、:31 `- name: discord-recovery-info`
- PostgresDown / HighErrorRate / High502Rate の名前は上の `alert:` 一覧に無い。discord-ops は monitoring 配下に無い。

### P6 docker-compose.yml のサービス（services: は :3）

| サービス | 開始行 | healthcheck | read_only |
|---|---|---|---|
| nginx | 5 | あり :21 | なし |
| certbot | 42 | なし | なし |
| backend | 63 | あり :154 | なし |
| frontend | 179 | あり :188 | なし |
| celery-worker | 215 | あり :282 | なし |
| celery-beat | 306 | あり :322 | なし |
| discord-gateway | 350 | あり :373 | なし |
| gemini-egress | 405 | あり :409 | なし |
| redis | 450 | あり :456 | あり :473 `read_only: true` |
| postgres | 480 | あり :490 | なし |
| gha-exporter | 518 | なし | なし |

サービス数 11、healthcheck あり 9、なし 2（certbot, gha-exporter）。read_only は redis の1か所。抽出方法: 4スペース字下げの `healthcheck:` / `read_only:` を awk で行番号つきで抽出。

### P7 health の道と tenants の道

- health: backend/app/routers/health.py:16 `@router.get("/health")`、backend/app/main.py:240 `app.include_router(health.router, prefix="/api", tags=["health"])` → 実パス GET /api/health
- super-admin の tenants: backend/app/routers/super_admin_tenants.py:30 `router = APIRouter()`、:38 `@router.delete("/super-admin/tenants/{tenant_id}")`、:104 `@router.delete("/super-admin/tenants/{tenant_id}/physical")`。backend/app/main.py:653-655 `app.include_router(super_admin_tenants.router, prefix="/api/v1", tags=["super-admin"],)` → 実パス DELETE /api/v1/super-admin/tenants/{tenant_id}、DELETE /api/v1/super-admin/tenants/{tenant_id}/physical。同ファイルに get / post の定義は無い（`@router.` の grep は上記2行のみ）。
- admin の tenants: backend/app/routers/admin.py:21 `@router.post("/tenants", response_model=TenantResponse, status_code=201)`、backend/app/main.py:261-266 `admin.router, prefix="/api/v1/admin", … dependencies=[Depends(get_current_tenant), Depends(require_super_admin)]` → 実パス POST /api/v1/admin/tenants。
- dashboard: backend/app/routers/dashboard.py:66-67 `@router.get("/dashboard", …`、backend/app/main.py:374 `dashboard.router, prefix="/api/v1", tags=["dashboard"]` → 実パス GET /api/v1/dashboard。

D-06 の該当箇所（文書側のメソッドと実物のメソッドの対比）:

| D-06 の行 | 文書の記述 | 文書側の HTTP メソッド | 実物の定義 | 実物のメソッド |
|---|---|---|---|---|
| 152 | `curl -H "Authorization: Bearer $TOKEN" https://jarvis-claude.uk/api/v1/customers`（docs/D-06_firebase_credentials_setup.md:152） | -X 指定なし（curl の既定で GET） | /api/v1/customers のルート定義は backend/app 内に無い（下記） | 該当なし |
| 166 | `curl -X POST … https://jarvis-claude.uk/api/v1/admin/tenants -d '{…}'`（同ファイル :164-168 のブロック） | `-X POST` あり | backend/app/routers/admin.py:21 と backend/app/main.py:261-266 | POST /api/v1/admin/tenants（一致） |
| 181 | `curl -H "Authorization: Bearer $TOKEN" https://jarvis-claude.uk/api/v1/dashboard`（同ファイル :180-181） | -X 指定なし（curl の既定で GET） | backend/app/routers/dashboard.py:66-67 と backend/app/main.py:374 | GET /api/v1/dashboard（一致） |

- 一覧（§1）の D-06 第8行「ルータ定義無し」、第9行「ヒット無し」は、上の定義の存在と食い違う。
- /api/v1/customers の GET: `grep -rn '"/customers\|'"'"'/customers\|/api/v1/customers' backend/app --include='*.py'` のヒットは2件のみ。
  - backend/app/routers/duplicates.py:146 コメント「旧 `POST /api/v1/customers/{master_id}/merge` は撤去済み。」（移管先は同 :147 `POST /api/v1/companies/{master_id}/merge` (routers/companies.py)）
  - backend/app/auth/dependencies.py:629 `@router.post("/customers", dependencies=[Depends(require_permission("customers.create"))])`（require_permission の docstring 内の使用例。dependencies.py:622-630 の docstring 内で、実際のルート定義ではない）
  - GET /customers のルート定義は 0件。backend/app/main.py:312 に「ADR-089 Sprint 3: customers 廃止済み」のコメント。

### P8 Discord 通知と deploy.yml

discord-pr-notify.yml（secret は全箇所 `secrets.DISCORD_WEBHOOK_PR`: :21,61,92,160,198）:
- :33 `🔵 PR #${PR_NUMBER} が作成されました`
- :68 `🔄 PR #${PR_NUMBER} が再オープンされました`
- :131 `$EMOJI PR #${PR_NUMBER} にレビュー($STATUS)が投稿されました`（:102-120 の case: approved=`✅`/`承認`、changes_requested=`⚠️`/`修正要求`、commented=`💬`/`コメント`、その他=`📝`/review state の文字列）
- :170 `🎉 PR #${PR_NUMBER} がマージされました`
- :205 `❌ PR #${PR_NUMBER} がクローズされました（未マージ）`
- :5 `types: [opened, closed, reopened]`、:7 `types: [submitted]`

discord-ci-notify.yml:
- :44 コメント `check_suite の conclusion: success / failure / neutral / cancelled / skipped / timed_out / action_required / stale`
- :47-52 `success)` → 通知する、title_status `All checks passed`（:50）
- :53 `failure|timed_out|action_required)` → 通知する、title_status `Some checks failed`（:57）。失敗 check の抽出（:61）は conclusion が failure / timed_out / action_required
- :65 `cancelled|skipped|neutral|stale)` → should_notify=false（:66 コメント「cancelled は通知しない」）、:68 `*)` → should_notify=false
- :11-12 冒頭コメント「failure (1 件でも fail): 赤 embed … その他 (cancelled / timed_out): グレー embed」（:53 の case 分岐と文言が異なる）
- :126 タイトル `${EMOJI} PR #${PR_NUMBER} — ${TITLE_STATUS}`
- secret: :100 `WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_CI }}`、:36,78 `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`

deploy.yml が参照する secrets.* の名前一覧（名前のみ。`grep -o -h "secrets\.[A-Za-z0-9_]*" | sort | uniq -c` の結果。括弧は出現数、無印は1）:
ADMIN_DATABASE_URL, ADMIN_NOTIFICATION_DISCORD_WEBHOOK, ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK, AUTH_PASSWORD_RESET_ALLOWLIST, AUTH_VIEWER_JWT_SECRET, CONTACT_NOTIFY_EMAIL, DESIGN_SITE_SMOKE_CRED(2), DESIGN_SITE_VIEWER_CRED, DISCORD_BOT_TOKEN, DISCORD_WEBHOOK_OWNER_PING(2), ERROR_REPORT_AGENT_TOKEN, FEDEX_SMOKE_API_TOKEN(2), FEDEX_SMOKE_ENABLED, FEDEX_SMOKE_USER_EMAIL, GEMINI_API_KEY, GOOGLE_CALENDAR_CLIENT_ID, GOOGLE_CALENDAR_CLIENT_SECRET, GOOGLE_CALENDAR_REDIRECT_URI, GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_REDIRECT_URI, MAIL_FROM, META_APP_ID, META_APP_SECRET, META_OAUTH_REDIRECT_URI, META_VERIFY_TOKEN, METADATA_FERNET_KEY, OPS_API_TOKEN, OPS_INGEST_TOKEN, PIPELINE_PAT(3), REVIEW_MAIL_DISCORD_WEBHOOK, REVIEW_MAIL_IMAP_HOST, REVIEW_MAIL_IMAP_PASSWORD, REVIEW_MAIL_IMAP_PORT, REVIEW_MAIL_IMAP_USER, REVIEW_MAIL_WEBMAIL_URL, SALESANCHOR_APP_PASSWORD(2), SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER, SSH_PRIVATE_KEY(13), VITE_FUNNEL_DASHBOARD, VPS_HOST(16), VPS_USER(15)

- grep の結果に出た `secrets.new`（5件）は `.env.secrets.new` というファイル名の一部（例 deploy.yml:323,363,367,370,371）で、GitHub secret ではない。
- `secrets.X`（1件）は deploy.yml:270 のコメント内の例示（`${{ secrets.X }}` 自体は GitHub Actions が SSH 送信前に展開する）。
- `GITHUB_TOKEN` は deploy.yml に0件。

deploy.yml の主な段階（ステップ名と行）:
- :27 Checkout / :33 Detect backend / migration changes / :61 Check previous deploy completed / :79 Setup Node.js / :89 Build LP / :95 Setup SSH agent / :100 Add VPS to known_hosts / :105 Rsync LP build to VPS / :123 Setup design-site htpasswd / :144 Rsync design-site to VPS / :159 Check free disk space / :195 Pre-deploy DB backup
- :230 Deploy to VPS (code + env + docker compose):
  - deploy.yml:253（取り込み方式：origin の main を fetch する行）
  - deploy.yml:254（取り込み方式：fetch のあと作業コピーを origin/main に強制的に合わせる行）
  - :323 `.env.secrets.new` を here-document で生成、:370 それを `.env` へ追記
  - :415 `if docker compose build; then`（3回失敗で :423 のメッセージ）
  - :430-431 `echo "Step 3b: Blue-green backend cutover..."` / `bash scripts/blue-green-cutover.sh`
  - :447 celery-worker を `docker compose stop -t 60` で停止
  - :453 `docker compose up -d --no-deps --remove-orphans frontend celery-worker celery-beat discord-gateway gemini-egress`
  - :456 `docker compose up -d --no-deps node-exporter promtail`
- :479 Recreate nginx（:490 は nginx コンテナを強制的に作り直す up 行）/ :498 Bootstrap salesanchor_app role（:541 `BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh`）/ :563 Run database migrations（:577 `bash scripts/run_all_migrations.sh`）/ :584 Post-deploy smoke tests / :605 FedEx Rates live smoke / :649 Finalize / :796 Verify deployment（:808 jarvis-claude.uk の curl）/ :892 Stamp main deploy date / :1032 Emergency block /design/ on smoke FAIL / :1050 Deployment Failure Notification
- 文字列 `git pull` は deploy.yml:188,219,245 のコメントのみ（コマンドとしては無い）。

### P9 バックアップ

scripts/backup_to_s3.sh:
- cron 例（コメント）:13-14 `# cron登録（毎日 3:30 = backup.sh完了後）:` / `#   30 3 * * * TZ=Asia/Tokyo /path/to/scripts/backup_to_s3.sh >> /var/log/s3_backup.log 2>&1`
- 月次: :138 `# 5. 月次アーカイブ（毎月1日のバックアップをGlacierに永久保存）`、:139 `if [ "$(date +%d)" = "01" ]; then`、:140 `MONTHLY_KEY="monthly-archives/$(date +%Y-%m)/${FILENAME}"`、:142-143 `aws s3 cp … --storage-class GLACIER`、:151-154 サイズ照合（一致で「月次アーカイブ完了（検証OK）」、不一致で ERROR）。:78 `RETENTION_DAYS=90  # S3上の保持日数（monthly-archives/ は対象外）`、:123 コメント「monthly-archives/ は別プレフィックスのため、このステップの影響なし（永久保存）」
- 成功時刻ファイル: :159 `# 6. 成功時刻を node-exporter の textfile に書く（ADR-1012 段階1 便6。見張り BackupS3Stale が読む）`、:162 `TEXTFILE_DIR="${BACKUP_TEXTFILE_DIR:-/home/ubuntu/node_exporter_textfile}"`、:171 `backup_s3_last_success_timestamp $(date +%s)`、:172 一時ファイルを `${TEXTFILE_DIR}/backup_s3.prom` へ移動、:176 `write_success_timestamp || true`
- 失敗通知: :48 コメント `.env を読み込み（DISCORD_WEBHOOK_OPS 等を環境変数に反映）`、:56-71 `notify_failure()`（DISCORD_WEBHOOK_OPS が空なら何もしない。本文 `[ALERT] S3バックアップ失敗: <日時>`）、:73 `trap 'notify_failure' ERR`

scripts/aws-setup/setup-s3-backup.sh:
- :127 `echo "  2. cronに登録（毎日3:30実行）:"`、:129 `echo "     30 3 * * * /home/ubuntu/salesanchor/scripts/backup_to_s3.sh >> /var/log/s3_backup.log 2>&1"`

scripts/aws-setup/README.md:
- :159 `#### Step 2-6: cron登録`、:168 `0 3 * * * /home/ubuntu/salesanchor/scripts/backup.sh >> /home/ubuntu/backups/cron.log 2>&1`、:169 `30 3 * * * /home/ubuntu/salesanchor/scripts/backup_to_s3.sh >> /home/ubuntu/backups/s3_backup.log 2>&1`、:187-188 ログ確認の tail（cron.log と s3_backup.log）
- 月次 / textfile / DISCORD / webhook の記載は 0件。Glacier は :212 の1行（「100GB超えるなら、Glacier Deep Archiveへの移行を検討してください」）のみ。

scripts/aws-setup/s3-lifecycle.json:14-18 `"_comment": "monthly-archives/ は永久保存のため削除ルールを意図的に設定しない。Glacierストレージクラスで保持。"`、`"ID": "MonthlyArchivesNoExpiry"`、`"Prefix": "monthly-archives/"`

scripts/aws-setup 配下のファイル: README.md, iam-policy.json, s3-bucket-policy.json, s3-lifecycle.json, setup-s3-backup.sh（iam-policy.json / s3-bucket-policy.json は今回未読）。

### P10 GEMINI_API_KEY を使う backend のファイル（tests 除く）

- backend/app/services/gemini_extraction_svc.py:10（docstring `GEMINI_API_KEY 環境変数必須`）、:262 `api_key = os.getenv("GEMINI_API_KEY", "").strip()`、:265 エラー文言、:386 docstring
- backend/app/services/message_translator.py:117 `key = os.getenv("GEMINI_API_KEY", "").strip()`、:119 `raise LLMConfigError("GEMINI_API_KEY が未設定です。翻訳機能は無効化されます。")`
- backend/app/services/llm_errors.py:20 docstring `GEMINI_API_KEY が未設定 / 空。`
- backend/app/tools/reextract_v6_with_v102.py:98 `api_key = os.getenv("GEMINI_API_KEY", "").strip()`、:100 `raise RuntimeError("GEMINI_API_KEY が未設定です。")`
- backend/app/services/inventory_parser_llm.py: ファイル無し（`ls backend/app/services | grep inventory_parser` が 0件）。
- docker-compose.yml:95（backend サービス内）`GEMINI_API_KEY=${GEMINI_API_KEY:-}`、:230（celery-worker サービス内）同、:229 コメント `GEMINI_API_KEY: Gemini 翻訳 API キー（未設定だと LLMConfigError で全翻訳スキップ）`
- tests での参照ファイルの例: backend/tests/test_tcg_gemini_extraction.py, test_reextract_v6_with_v102_pg.py, test_gemini_error_redact.py（他にもあるかは未確認）。
