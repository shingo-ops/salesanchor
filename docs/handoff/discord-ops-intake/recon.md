<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — discord-ops-intake

> この文書は何か：Discord の監視通知を AI に受けさせる設計の前に、「今どうなっているか」を実物で確かめた記録です。

親: [docs/specs/discord-ops-intake/README.md](../../specs/discord-ops-intake/README.md)

**仕事名**: discord-ops-intake  
**日付**: 2026-10-13  
**対象ADR**: ADR-080（監視VPS分離・Proposed）、ADR-069（Uptime Kuma）、ADR-136（危険PRのGO）。本テーマ専用の ADR は未作成  
**担当**: 設計パートナー（Opus。調査の実行は Sonnet）  
**基準**: origin/main `67f2e4352`

---

## 既存 ADR 検索の結果

- `git grep -l -i -e alert -e webhook origin/main -- docs/adr/` → ADR-018/024/025/026/034/035/038/042/046/069/070/075/077/080/081/082/089/091/095/098/101/107/115/119/131/132/134/141/153/159/SA-17
- 本テーマに直接関係するもの:
  - ADR-080: `docs/adr/ADR-080-monitoring-vps-separation.md:105`「アプリVPSダウン時でも Uptime Kuma が検知・Discord 通知できる」（ステータス Proposed、同:5）
  - ADR-069: `docs/adr/ADR-069-uptime-kuma-activation.md:44`「Discord Webhook 通知設定」
  - ADR-091 は返信送信の話で監視通知とは無関係（`docs/adr/ADR-091-discord-bot-scope-definition.md:102`）
- `docs/adr/FEATURE-INDEX.md` に監視・アラートの行は無い
- 設計仕様書索引 `docs/specs/README.md` に Discord・監視の領域は無い → 新規テーマ（STANDARD-WORKFLOW §1.8）

## file:line 引用表（リポジトリ内）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `monitoring/alertmanager/alertmanager.yml:2` | 受信先は `discord-server-alerts` の 1 つだけ |
| `monitoring/alertmanager/alertmanager.yml:3` | group_by は alertname / job / instance。group_wait 30s・group_interval 5m・repeat_interval 4h（:4-6） |
| `monitoring/alertmanager/alertmanager.yml:10` | webhook URL はファイル `/etc/alertmanager/secrets/discord-webhook` から読む。:11 で `send_resolved: true`（解消通知も送る） |
| `docker-compose.monitoring.yml:180` | 上記ファイルの実体は `./secrets/alertmanager-discord-webhook`（リポジトリ外の秘密ファイル） |
| `monitoring/grafana/provisioning/alerting/alerting.yml:28` | Grafana の通知先 URL は環境変数 `GF_DISCORD_WEBHOOK_URL` |
| `monitoring/grafana/provisioning/alerting/alerting.yml:29` | 本文は summary・description・`重要度:`（severity）の固定テンプレート（:29-33） |
| `docker-compose.monitoring.yml:46` | `GF_DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL:-}` |
| `monitoring/prometheus/alert_rules.yml:44` | 本文に入る可変値はラベル `instance` と数値だけ（:44-45 CriticalDiskUsage） |
| `monitoring/loki/rules/jarvis/alerts.yml:1` | Loki ルールも固定文の summary/description（件数のみ・ログ本文は入らない） |
| `backend/app/services/review_mail_notifier.py:126` | 外部メールの差出人（:126）・件名（:127）を Discord 本文に入れる → 外部の第三者が書ける文字が入る |
| `backend/app/tasks/priority_scoring_check.py:189` | 例外メッセージ `error_message[:200]` を本文に入れる |
| `.github/workflows/discord-ci-notify.yml:102` | PR タイトルを embed に入れる |
| `scripts/backup_to_s3.sh:56` | バックアップ失敗通知は `DISCORD_WEBHOOK_OPS`（固定文＋日時） |

## file:line 引用表（リポジトリ外・実機）

リポジトリ外のためバッククォートを付けない。

| 引用先 | 確認内容 |
|---|---|
| ~/.claude/plugins/cache/claude-plugins-official/discord/0.0.4/server.ts:806 | `if (msg.author.bot) return` — ボット・webhook の投稿を最初に捨てる |
| 同 server.ts:285-291 | チャンネル（group）の `allowFrom` が空なら誰の発言も通す。`requireMention` 既定 true |
| 同 server.ts:446, 452 | `claude/channel` と `claude/channel/permission`（承認の中継）を無条件に宣言 |
| 同 server.ts:750-754 | 承認ボタンを押せるのは DM 許可リスト `allowFrom` の人だけ |
| 同 server.ts:53-60 | トークンは `DISCORD_BOT_TOKEN`（~/.claude/channels/discord/.env） |

## 実測（2026-10-12〜13・PO の Mac・Claude Code 2.1.296）

| # | 何を | 結果 |
|---|---|---|
| M1 | channels 利用可否（fakechat） | debug ログに `Channel notifications re-registered after reconnect`・`blocked by org policy` なし → 利用可 |
| M2 | Discord ボット DM 往復 | PO の DM「テスト」が受付セッションに届き、ボットが返信（メッセージ id 1559228685209309288） |
| M3 | webhook 投稿の扱い | 検証チャンネル 1559230296975474959 に webhook 投稿（HTTP 204）→ 受付に届かず。同チャンネルの PO 発言「人の発言テスト」は届き、ボットが返信 → webhook は捨てられると確定 |
| M4 | 後片付け | fakechat の `bun server.ts` が正常終了ログの後も残り port 8787 を保持（2 回観測）→ 手順書 F-4「正常終了なら残らない」と異なる |
| M5 | プラグインの有効範囲 | `-s user` で入れると他の全 Claude セッションでもプラグインの MCP サーバーが起動する（fakechat の残骸が 22:30 起動・親なしで観測）→ `~/discord-test` の local スコープのみに変更済み |
| M6 | Developer Portal | Public Bot OFF は Installation の Install Link を「なし」にしないと保存エラー（同時に Intent も未保存→`Used disallowed intents` でログイン失敗） |

## 本番 Discord サーバーの実物（Discord API 読み取り・2026-10-13 03 時台 JST）

| チャンネル | ID | 直近の投稿元 webhook | 実測 |
|---|---|---|---|
| 🚨│サーバー監視アラート（カテゴリ「アラート」） | 1527986848490717245 | 1528064418448146552「サーバー監視」 | 直近 50 件すべてこの webhook（2026-10-12 08:22〜17:58 UTC）。49 件は content 空・embed 1 件（title `[FIRING:1] <alertname> (<severity>)` / `[RESOLVED] ...`、description は Alertmanager 既定テンプレート、fields なし）。1 件は embed なしの「tasks/todo.md に 40 件の未更新タスク」通知。発火と解消を繰り返していたのは BackendHighLatency・BruteForceAttempt・SustainedAuthFailure |
| api（同カテゴリ） | 1544914659595915325 | 1544914720987807804「Deploy Bot」 | 1 件（2026-09-04「FedEx live smoke 失敗」・embed なし） |
| 検証用サーバーのテストチャンネル | 1559230296975474959 | 1559230387799068754（試験用） | 試作の擬似アラート |
| approval-test | 1559254677768380537 | 1559254844735361134（試験用・許可外） | 試作の承認チャンネル |

- ボット（SA Bug Intake）は上記 4 チャンネルとも読める（HTTP 200）。権限は閲覧・送信・履歴・添付・リアクション・公開スレッド作成・スレッド内送信。管理者なし（2026-10-13 実測）
- 「検証用サーバー」と呼んでいたものは本番 Sales Anchor サーバー内のチャンネルだった

## 公式仕様（Context7 は月間上限で利用不可のため公式資料を直接確認・2026-10-13）

- https://code.claude.com/docs/en/channels-reference 「Test during the research preview」: 自作・改変した channel は `--dangerously-load-development-channels plugin:<name>@<marketplace>` が必要。起動時に全画面の確認が出る。`-p` では無視される
- 同「Gate inbound messages」: 送信者単位で絞る（部屋単位ではなく）
- 同「Relay permission prompts」: v2.1.234 以降、承認の中継は登録済み channel にだけ送られる。auto mode では分類器が判断し、中継の対話は開かない
- https://code.claude.com/docs/en/channels 「Research preview」: 通知はセッションが開いている間だけ届く

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 監視アラートチャンネルに投稿している webhook の ID（Alertmanager 用・Grafana 用・Uptime Kuma 用が同じか別か） | 自前版プラグインが「捨てた webhook の ID」をログに出す → 本番チャンネルで 1 件観測して確定（URL は露出させない） | 実装時に解消（設計 §4 手順 2） |
| 2 | Uptime Kuma の通知設定（リポジトリ外・Kuma の DB） | 同上の観測で ID が分かれば足りる | 実装時に解消 |
| 3 | auto mode の受付セッションで承認中継が働くか | 公式: auto mode では中継の対話が開かない → 受付は manual（default）モードで動かす前提で設計 | ✅ 解消（設計で回避） |

**未解決ゼロ確認**: 設計判断に必要な不明点は解消済み。#1・#2 は実装手順の中で観測して埋める（設計は ID の値に依存しない）。
