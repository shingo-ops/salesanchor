# recon: AI 用「本番 DB を読むだけの道」の現在地

> この文書は何か（専門用語なしの1行）:
> 担当 AI が本番のデータベースを読もうとして止まる理由を、実物の場所（ファイルと行）つきで並べた現状の記録。推測は書かない。

- 親（設計仕様書）: 新テーマの仕様書は未作成。近い領域として [開発の無駄な停止ゼロ](../../specs/dev-continuity/README.md) に連なる（索引: [docs/specs/README.md](../../specs/README.md)）。本件は ADR で設計を持ち込む様式（ADR-113 の handoff）で進める。
- 兄弟: [design.md](design.md) ／ [card-bin3a.md](card-bin3a.md) ／ ADR: [ADR-1024](../../adr/ADR-1024-ai-readonly-db-path.md)
- 基準: origin/main a0ca4bc17c5e347e151fa81577ecd82749d72aef（2026-10-17 の worktree 作成時点）
- 生出力の置き場: /tmp/CC報告ファイル/readonly-db-path/（Mac の一時置き場。リポジトリには入れない）。
  - 便1 の実測: /tmp/CC報告ファイル/readonly-db-path/bin1/check-20261017-135440.out（以下「便1」と書く。行番号はこのファイルの行）
  - 設計審査: /tmp/CC報告ファイル/readonly-db-path/fable-review.md
  - 担当の調査メモ: /tmp/CC報告ファイル/readonly-db-path/recon.md（本文書の元の一部）
- 載せないもの: authorized_keys の鍵の中身・行の原文、IP アドレス、パスワード・トークンの値。

## 既存 ADR の検索結果（STANDARD-WORKFLOW §2 の必須項目）
- 検索: `git grep -il` で docs/adr/ を「読み取り専用」「ai_reader」「readonly」「監視」で引いた。
- 本番 DB への AI の道を直接扱う ADR は、grep 済み・該当なし。
- 関連 ADR: ADR-079（docs/adr/ADR-079-claude-code-monitoring-access.md:1、監視用の読み取り鍵）、ADR-SA-18（docs/adr/ADR-SA-18-app-db-least-privilege.md:1、アプリの DB 最小権限ロール）、ADR-136 の GO 手順（CLAUDE.md:57）、ADR-113（docs/adr/ADR-113-two-mode-dev-flow.md:1）。
- 番号: origin/main の ADR の最大は ADR-1023（docs/adr/ADR-1023-condition-value-rank.md）。開いている PR で ADR-1024 を使うものはなかった（`gh pr list --state open` の files と title を確認）。よって ADR-1024 を使う。

## 事実

### F1 止まる原因 1: 今の道は何でもできる鍵と superuser
- F1-1 今の道は、無制限鍵 manual-only と DB ユーザー jarvis。jarvis は `rolsuper=True`・`rolbypassrls=True`（便1:65）。
- F1-2 CLAUDE.md は「無制限鍵（manual-only）は人間の明示許可があるタスクでのみ使用可。許可は都度・タスク単位」と定める（CLAUDE.md:29-31）。
- F1-3 担当 Sonnet は Opus 経由の許可を伝聞として扱い、manual-only 鍵を使わない（メモリ feedback_subagent_consent_ticket.md:11-27。リポジトリ外: /Users/tanizawashingo/.claude/projects/-Users-tanizawashingo-salesanchor/memory/）。
- F1-4 読み取りの恒久許可は 2026-09-29 に PO が出している（メモリ project_cc_db_path_backlog.md:29-33）。許可があっても道が「何でもできる鍵」のままなので、担当は使わない。
- F1-5 読み取り専用の DB ユーザーは存在しない（便1:64-81 の pg_roles に ai 系のロールなし）。アプリ用の salesanchor_app は SELECT/INSERT/UPDATE/DELETE ができる（migrations/20260605_030000_create_salesanchor_app_role.sql:15-17）。

### F2 止まる原因 2: 既存の制限鍵は DB に届かない
- F2-1 制限鍵は監視 4 コマンドだけ: `ALLOWED_COMMANDS='docker stats --no-stream; free -h; df -h; uptime'`（scripts/setup-claude-monitor-user.sh:21）。
- F2-2 本番 ubuntu の authorized_keys は 5 本（便1:3-7）。内訳は、オプションなしが 3 本、`command=` 固定（監視 4 コマンド）が 1 本、`no-pty` 等だけで `command=` なしが 1 本。ユーザー claude-monitor が別にあり、鍵は読めなかった（便1:10-13）。鍵の原文は本書に載せない。
- F2-3 監視鍵は prod2 と共有の決まり（docs/adr/ADR-079-claude-code-monitoring-access.md:1）。ここに DB 読み取りを足すと役目が混ざる。

### F3 止まる原因 3: 止める仕組みが文字の並びで判定する
- F3-1 psql-write-guard の本体は /Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh:88-153（リポジトリ外）。文字パターンは 5 つ（:99-103）。`psql -c` 内の書き込みキーワードも止める（:113-119）。permit チケットで通る（:125-150）。
- F3-2 担当が調査メモ（recon.md）を書こうとしたとき、本文の文字に反応して拒否された（担当の報告。生出力: /tmp/CC報告ファイル/readonly-db-path/）。

### F4 DB 側の入口（pg_hba）
- F4-1 pg_hba は、`local` と、ループバック宛の `host` が trust（便1:49-54）。それ以外の host は scram-sha-256（便1:55）。アドレスは本書に載せない。
- F4-2 postgres はポートを公開していない（docker-compose.yml:475-511 の postgres サービスに `ports:` なし、`networks: backnet` のみ）。
- F4-3 つまり postgres コンテナの中に入れる者は、パスワードなしで jarvis（superuser）になれる。コンテナ内の psql を読み取り専用ユーザーで動かしても、`\c` で jarvis に切り替えられ、`\!` でシェルも動く。
- F4-4 trust に依存する既存の処理がある: scripts/backup.sh:28 の `pg_dump -U`、.github/workflows/deploy.yml:482 の `psql -U jarvis`、scripts/run_all_migrations.sh:25 の `PSQL="psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1"`。trust の廃止は別の仕事（ADR-1024 の「後で足すもの」）。

### F5 アプリの接続とテナントの壁（RLS）
- F5-1 アプリ（backend）の接続は `salesanchor_app`（`rolsuper=False`・`rolbypassrls=False`）、接続先は host=postgres、db=jarvis_db（便1:58-62, 81）。パスワードは出力していない。
- F5-2 RLS が有効な表: public 19 表（うち 19 が FORCE）、tenant_001/003/004/005/006 の各 58 表（うち各 1 表が FORCE）（便1:83-90）。FORCE の表では、BYPASSRLS がないと 0 行になる。
- F5-3 スキーマと表の数: public 109、tenant_001 99、tenant_003 69、tenant_004 91、tenant_005 69、tenant_006 69（便1:112-120）。
- F5-4 `default_transaction_read_only` は off、`statement_timeout` は 0（制限なし）（便1:94-99）。
- F5-5 PostgreSQL は 16.13（便1:91-93）。定義済みの役割 pg_read_all_data がある（便1:71）が、今回は付けない（ADR-1024）。
- F5-6 テナントのスキーマを作る処理: backend/app/services/tenant.py:1634 `create_tenant_schema`。新しいテナントが増えると、ai_ro のビューも作り直しが要る（未確認 U7: 作り直しの呼び出し元）。
- F5-7 SECURITY DEFINER の関数は、トリガ関数だけ（backend/app/services/tenant.py:1474、migrations/044_create_meta_page_routing_trigger.sql:40）。拡張は pg_trgm のみ（migrations/068_add_inventory_search_indexes.sql:12）。

### F6 秘密の列の所在（ai_ro で外す対象の例）
- F6-1 `password_argon2_hash`: public.users（migrations/20261013_160000_add_self_hosted_auth_tables.sql:6）。viewer_accounts にも同名の列がある（Fable 審査の記述。実装の最初に全表を機械的に洗い出す）。
- F6-2 `*_encrypted` の列を持つ migration: migrations/040_create_tenant_meta_config.sql、migrations/076_add_google_calendar_config.sql、migrations/20260608_080000_add_carrier_credentials.sql、migrations/20260609_100000_add_carrier_account_number.sql、migrations/20260610_071110_add_paypal_config.sql、migrations/20261001_150000_create_discord_channel_webhooks.sql（`grep -rln "_encrypted" migrations` の結果）。
- F6-3 復号の鍵 `METADATA_FERNET_KEY` は backend コンテナの環境変数（docker-compose.yml:78）。同じコンテナに `DATABASE_URL`（:66）と `ADMIN_DATABASE_URL`（:67）もある。暗号文と鍵が同じ場所に揃うため、台本は backend コンテナで動かさない（ADR-1024）。
- F6-4 列の完全な一覧は、この recon では確定していない。ビュー生成の実装で、情報スキーマから拒否リストに当たる列を機械的に洗い出す（card-bin3a.md 項目 1）。

### F7 migration の実行と、ビューを作る場所の候補
- F7-1 全 migration の実行は scripts/run_all_migrations.sh。「新マイグレーションは末尾の『ここから追加』セクションに追加」（:15）。末尾は `run_sql migrations/20261017_120000_line_conditions_value_rank.sql`（:963）。
- F7-2 `run_sql` は `docker exec -i astro-webapp-postgres-1 psql -U jarvis …` で jarvis（superuser）として流す（:25, :61-66）。`run_py` は `ADMIN_DATABASE_URL`（未設定なら `DATABASE_URL`）で動く（:49-59）。
- F7-3 よって、ビューの持ち主を jarvis にするには、`run_sql` の SQL ファイル（またはそれを流す形）が適する。ビューを何枚作るかは、テナントのスキーマが増減するので、SQL を実行時に生成する必要がある（候補: `DO` ブロックで情報スキーマを走査する SQL ファイル。確定は実装担当。未確認 U8）。
- F7-4 migration の実行ユーザー（U4）は、`run_sql` が jarvis であること（F7-2）で解消。

### F8 コンテナと切替
- F8-1 backend のコンテナ名は `astro-webapp-backend-1`（scripts/run_all_migrations.sh:23）。blue-green の切替で一時的に `backend-green` から rename される（scripts/blue-green-cutover.sh:159-161）。切替中は固定名が一瞬なくなる。専用コンテナならこの影響を受けない。
- F8-2 ネットワークは `backnet`（docker-compose.yml:551-553）。postgres は backnet のみ（:503-504）。
- F8-3 backend の requirements: `psycopg2-binary==2.9.10`・`asyncpg==0.31.0`（backend/requirements.txt:5-6）。台本は同期接続の psycopg2 を使える（U5 解消）。
- F8-4 `backend/app/ops/` は origin/main に存在しない（新規）。`backend/tests/` は存在する。

### F9 記録（ログ）
- F9-1 promtail のジョブは docker・nginx_error・ssh_auth・containers の 4 本（monitoring/promtail/promtail.yml:16, 25, 41, 56）。Loki の保持は 30 日（monitoring/loki/loki-config.yaml:29。Loki は prod2）。
- F9-2 台本が stderr に出す 1 行は、SSH 経由で Mac に戻るだけで、VPS 側には残らない（Fable 審査 §1-4 の記述。実機の K テストで確認）。そのためサーバー側の記録は DB の `log_statement=all` に頼る（ADR-1024）。
- F9-3 postgres コンテナのログは json-file、20m×5 世代（docker-compose.yml:495-499）。

### F10 sshd
- F10-1 `ForceCommand` の設定はない。`command=` で縛っている（便1:15-29）。`PermitRootLogin no`・`PasswordAuthentication no`（便1:18-19）。`AcceptEnv LANG LC_*`（便1:26）。
- F10-2 `/etc/ssh/sshd_config.d/*.conf` は読めなかった（便1:29「読めない」）。PermitUserEnvironment 等の上書きの有無は未確認（K テストで `sshd -T` を測る）。

### F11 ガバナンス
- F11-1 CODEOWNERS には `migrations/` と `scripts/` が @shingo-ops で入っている（.github/CODEOWNERS:21, 23）。`backend/app/ops/` や ai-reader の compose 定義は入っていない（追加が要る）。
- F11-2 CODEOWNERS 必須レビューが Branch Protection で有効かは未確認（PO が GUI で確認する。`gh api` で設定を変えない）。
- F11-3 危険パス（`migrations/`・`deploy.yml`・本番 `scripts/`）を含む実装は PO の GO が出るまで main にマージしない（CLAUDE.md:56-57、docs/STANDARD-WORKFLOW.md §5）。

## 未確認（実装担当が最初に確認。推測で埋めない）
| # | 内容 | 確かめ方 |
|---|---|---|
| U4 | migration の実行ユーザー | 解消済み: `run_sql` は jarvis（F7-2） |
| U5 | 同期接続の部品 | 解消済み: psycopg2-binary（F8-3） |
| U6 | Mac の接続元が固定か（`from=` を付けられるか） | PO に確認。未定のうちは `from=` なし |
| U7 | 新しいテナントが増えたときにビューを作り直す呼び出し元 | tenant.py:1634 周辺を読む。当面は「次回デプロイまで読めない」（fail-closed） |
| U8 | ビュー生成を SQL で書くか Python で書くか | card-bin3a.md 項目 1 の最初の確認 |
| U9 | `pg_read_all_data` を付けない `ai_reader` が `pg_authid` を読めないこと | K テスト（実機） |
| U10 | ビューの持ち主の権限で行の制限が外れること（`security_invoker` を付けない前提） | K テスト（実機） |
| U11 | `log_statement` を `ai_reader` 自身が戻せないこと | K テスト（実機） |
| U12 | `docker compose run -T` が標準入力を通すこと | K テスト（実機） |
| U13 | `/etc/ssh/sshd_config.d/*.conf` の中身 | `sshd -T`（PO `!`） |
| U14 | Branch Protection で CODEOWNERS 必須が有効か | PO が GUI で確認 |
| U15 | 専用 compose ファイルから、本体の compose が作る backnet に繋げる書き方 | 実装担当が `docker compose config` で確認 |

## 推測しないこと
- PostgreSQL の仕様（ビューと行の制限、`log_statement` の変更権限、`pg_authid` の読み取り）は、公式ドキュメントで確認していない（Context7 が月次上限で使えなかった）。実機の K テストで測る。
- OpenSSH の `restrict`・`expiry-time`・`command=` は、手元 Mac の man ページ（OpenSSH_10.2p1）で確認した（Fable 審査 §1-1, §5）。VPS 側の版は未確認。
