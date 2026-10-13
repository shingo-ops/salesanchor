---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — ai-ops-247

> この文書は何か：報知器・応急処置・AI 対応・振り返りの 4 段について、今どうなっているかを実物（コード・本番の監視データ・過去の障害記録）で確かめた記録です。

親: [docs/specs/ai-ops-247/README.md](../../specs/ai-ops-247/README.md)

**仕事名**: ai-ops-247  
**日付**: 2026-10-13  
**対象ADR**: ADR-1012（本テーマ・草案）、ADR-1009、ADR-115、ADR-079、ADR-080、ADR-081、ADR-069、ADR-070、ADR-136、ADR-153、ADR-1004  
**担当**: 設計パートナー（Opus）。読み取りは Sonnet に委任し、生出力を Opus が確認  
**測定基準**: origin/main c0e70ab27（worktree release/ai-ops-247-design）。本番の監視データは 2026-10-13 に Grafana 読み取り専用トークン（ADR-079）で取得

凡例: 【事実】出典あり ／ 【未確認】確かめられていない（不明点リストに載せる）

---

## 既存 ADR の検索

- `docs/adr/FEATURE-INDEX.md` と `git grep -i -e alert -e webhook -e incident docs/adr/` で拾った関連 ADR: ADR-115（デプロイ自動ロールバック）、ADR-079（Claude Code 読み取り専用監視アクセス）、ADR-080/081（監視 VPS 分離）、ADR-069（Uptime Kuma）、ADR-070（Grafana・Kuma→Prometheus 統合）、ADR-153（データ保全）、ADR-1000（外部 API スモーク）、ADR-1004（LLM 使用量台帳）、ADR-1009（Discord 受付）、ADR-136（危険 PR の GO）。
- 「AI が 24 時間保守する」「障害記録」「月次成績表」を決めた ADR は無い【事実：上記 grep の結果に該当なし】。

---

## file:line 引用表

### §1 報知器（感度）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `monitoring/prometheus/alert_rules.yml:8` | Prometheus のルールは 15 本（HighCpuUsage〜F2CleanupAbsent） |
| `monitoring/prometheus/alert_rules.yml:51` | HighDbConnections は `pg_stat_activity_count`（postgres-exporter の指標） |
| `monitoring/prometheus/alert_rules.yml:61` | PostgresDown は `pg_up`（postgres-exporter の指標） |
| `monitoring/prometheus/alert_rules.yml:71` | HighErrorRate は `nginx_http_requests_total`（nginx-exporter の指標） |
| `monitoring/prometheus/alert_rules.yml:81` | High502Rate も `nginx_http_requests_total` |
| `docker-compose.exporters.yml:31` | postgres-exporter は `profiles: ["heavy-exporters"]` |
| `docker-compose.exporters.yml:49` | nginx-exporter も同じ profile |
| `docker-compose.exporters.yml:67` | redis-exporter も同じ profile |
| `monitoring/prometheus/prometheus.yml:74` | 「heavy-exporters は明示指定時のみ起動」とコメント |
| `docs/handoff/infra-exporters-persist/design.md:15` | heavy-exporters を隔離した理由（当時のメモリ 2GB）。本番 VPS の今のメモリ量は repo に一次記録が無く【未確認】（不明点 3・段階0 で確認） |
| `monitoring/loki/rules/jarvis/alerts.yml:32` | Loki ルール BackendErrorSpike（backend のエラーログ） |
| `monitoring/loki/rules/jarvis/alerts.yml:69` | 同じ名前 BackendErrorSpike が postgres のエラーログ用に重複（名前で区別できない） |
| `monitoring/uptime-kuma-monitors.yml:9` | Kuma の監視 7 件（App・API・LP・PostgreSQL・Redis・Meta・Firebase） |
| `monitoring/uptime-kuma-monitors.yml:5` | 「UI での登録は手動」。repo と本番の一致を機械で確かめる手段が無い |
| `monitoring/prometheus/prometheus.yml:79` | Prometheus は Kuma の指標を取り込んでいるが、`monitor_status` を使うルールは 0 本（`grep -c monitor_status monitoring/prometheus/alert_rules.yml` → 0） |
| `backend/app/metrics.py:6` | backend の指標は HTTP 件数・時間・処理中・SSE の 4 種だけ。celery・バックアップ・証明書・Gemini の指標は無い |
| `backend/app/celery_app.py:60` | celery beat の定期処理 19 件。beat 自体が止まったことを知らせる仕組みは無い |
| `monitoring/prometheus/prometheus.yml:63` | pushgateway は既にある（定期処理の「最後に成功した時刻」を送る受け口に使える） |
| `migrations/20260930_150000_create_llm_usage_events.sql` | Gemini 等の呼び出し記録の正本 llm_usage_events（ADR-1004）。失敗率の監視に使える |

### §2 報知器（精度・通知の経路）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `monitoring/alertmanager/alertmanager.yml:2` | 受け先は discord-server-alerts の 1 つだけ。:4 group_wait 30s、:5 group_interval 5m、:6 repeat_interval 4h。抑止（inhibit）設定なし |
| `monitoring/grafana/provisioning/alerting/alerting.yml:23` | Grafana にも別の通知先 discord-ops がある（通知の経路が 2 本） |
| `docker-compose.monitoring.yml:177` | Alertmanager は v0.28.1 |
| `monitoring/prometheus/alert_rules.yml:111` | BackendHighLatency: P99 が 2 秒超を 2 分 |
| `docs/runbooks/claude-monitor-access.md:59` | 監視の読み取り口 GRAFANA_URL（ADR-079） |

本番の発火実績（2026-10-13 取得・直近 14 日・Prometheus の ALERTS を 150 秒刻みで集計。生データ /tmp/CC報告ファイル/ai-ops-recon-raw.md STEP2d）【事実】:

| ルール | 鳴った区間数 | 内容 |
|---|---|---|
| BackendHighLatency | 320 | 1 日に何十回も鳴っては止む |
| HighDiskUsage | 2 | 9/30〜10/2 |
| F2CleanupStale | 1 | 9/29〜10/4。対応の要否の一次記録は repo に無く【未確認】（段階0 で確認） |

- 本番で読める監視対象 8 件はすべて up（同 STEP2 targets）【事実】
- 保存期間: Prometheus 30 日（`docker-compose.monitoring.yml:8`）、Loki 30 日（`monitoring/loki/loki-config.yaml:29`）【事実】
- prod2 で動いている監視設定と repo の差は【未確認】（不明点 3・段階0 で確認）

### §3 応急処置

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docker-compose.yml:198` | celery-worker に healthcheck が無い（:249 restart: unless-stopped のみ） |
| `docker-compose.yml:274` | celery-beat に healthcheck が無い |
| `docker-compose.yml:311` | discord-gateway に healthcheck が無い |
| `docker-compose.yml:359` | gemini-egress に healthcheck が無い |
| `docker-compose.yml:137` | backend は healthcheck あり。ただし unhealthy になっても自動で再起動する仕組み（autoheal 等）は repo に無い（grep autoheal → 0 件） |
| `.github/workflows/deploy.yml:610` | デプロイ後のヘルスチェック失敗で直前の版へ自動ロールバック（ADR-115）。:697 で成否を Discord へ |
| `backend/app/celery_app.py:174` | 機械の自動回復は「抽出ジョブの停滞回収」（10 分ごと）の 1 件だけ |
| `backend/app/tasks/tcg_extraction_recovery.py:261` | 上記の処理本体 |

### §4 過去の障害と最初に気づいた経路

| 日付 | 障害 | 出典 | 報知器が先に鳴ったか |
|---|---|---|---|
| 2026-06-13 | 本番 DB の列を手で消して 500 が 5 分 | `docs/handoff/incident-20260613-password-hash/incident-report.md` | ×（作業者本人が気づいた） |
| 2026-09-02 | FedEx スモークのタイムアウトでデプロイ失敗 | `docs/handoff/incident-fedex-smoke-timeout/recon.md` | ×（デプロイの失敗で判明。利用者影響の報知器ではない） |
| 2026-06（ADR-1000 起票 2026-06-18） | PayPal 請求書の誤った完了表示 | `docs/handoff/incident-paypal-invoicing-false-complete/recon.md` | ×（人が気づいた） |
| 2026-10-02 | prod1 ディスク満杯で DB 停止（とされる） | repo に一次記録なし。本番の発火実績で HighDiskUsage が 9/30〜10/2 に鳴っていたことだけが【事実】（§2） | 【未確認】障害の時刻・Discord への到達とも段階0 で確認（不明点 6） |
| 2026-10-03 | 商品の表の列番号上限（1600）到達。復旧に PR 5 本 | `docs/adr/ADR-1005-migration-run-once-ledger.md:18` | ×（障害は本番で初めて見つかった。同 :19） |

→ 一次記録のある 4 件では、報知器が先に鳴ったのは 0 件【事実：上表の出典】。2026-10-02 の 1 件は【未確認】（段階0 で確認）。

### §5 振り返り（PDCA）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docs/INCIDENT_RESPONSE.md:3` | 障害の分類表はあるが、障害ごとの記録を溜める場所（表・DB）は無い |
| `backend/app/routers/bots.py:55` | アプリには bot 用の API キー発行がある（テナント単位）。保守 AI 用に流用できるかは【未確認】（不明点 4） |
| `frontend/src/components/DataTable.tsx` | 表の金型はある（Card・Badge・Callout・EmptyState・Tabs も同じ場所にある） |
| `docs/CC_UI_GOVERNANCE.md:9` | 金型が無い部品は作らず止まり、PO の許可を得てから登録する。グラフの金型は `frontend/src/components/` に無い（`ls frontend/src/components \| grep -i chart` → 0 件） |

- リポジトリは PUBLIC（`gh repo view shingo-ops/salesanchor --json visibility` → PUBLIC）。障害記録を repo や Issue に置くと外部に見える【事実】。

### §6 AI 対応（24 時間）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docs/adr/ADR-1009-discord-ops-intake.md` | Mac 上の常駐受付（C）。Accepted |
| `docs/handoff/discord-ops-intake/design.md:209` | 試作の実測 E1〜E6。E4（担当の許可確認の中継）は ×、設計変更後の E4' は ○。E7〜E10 と KGI の測定は未実施 |
| `tools/claude-channels/intake/agents/ops-worker.md:4` | 担当 ops-worker の道具は読む・Discord 返信・提案のみ。:5 permissionMode dontAsk、:6 background |
| `tools/claude-channels/README.md:39` | 番人は 5 分ごとに受付の停止を確認し通知。自動再起動はしない |
| `ops/launchd/jp.salesanchor.ops-intake-watchdog.plist` | 番人は Mac の launchd で動く（Mac が眠ると止まる） |

公式仕様（Context7 は月間上限で使えなかったため、起動指示に従い公式ページを直接確認。2026-10-13 取得。要点 /tmp/CC報告ファイル/ai-ops-external-research.md §A）【事実】:

- routines（https://code.claude.com/docs/en/routines）: research preview。Pro/Max/Team/Enterprise。API で起動する /fire がある（routine ごとの専用トークン・ヘッダ `anthropic-beta: experimental-cc-routine-2026-04-01`）。トークンは Web で作る（"The CLI cannot currently create or revoke tokens."）。上限に達すると "additional runs are rejected until your usage window resets"。送った文は `<routine-fire-payload>` に包まれ「信用しないデータ」として渡る。上限は routine ごとに 1 時間 30 回、アカウントで 1 時間 100 回（超えると失敗）。「Routines draw down subscription usage the same way interactive sessions do.」。公式の使い道の例に「Alert triage」（監視ツールが閾値を超えたら API を呼ぶ）がある。許可確認なしで動く。push 先は claude/ で始まるブランチ。
- cloud environments（https://code.claude.com/docs/en/cloud-environments）: 外向き通信は HTTP/HTTPS の代理を通る。Custom で行き先ドメインを限定できる。network secrets（Pro/Max のみ）は鍵を VM の外で付けるため、AI から鍵が見えない。
- GitHub Actions（https://code.claude.com/docs/en/github-actions）: CLAUDE_CODE_OAUTH_TOKEN で「Claude subscription」の枠で動く（Pro/Max/Team/Enterprise）。"runs in automation mode on any GitHub event"。repository_dispatch を名指しした記述は無い【事実：同ページ】。
- 契約: ホームの .claude.json の oauthAccount に organizationType=claude_max、organizationRateLimitTier=default_claude_max_20x、hasExtraUsageEnabled=False（生出力 /tmp/CC報告ファイル/ai-ops-facts-2.md F1）。
- 使用量の枠がいつ戻るか（日時）は repo・上記資料に記録が無い【未確認】。段階5 の起動前に PO の使用量画面で確認する。
- 規約（https://www.anthropic.com/legal/consumer-terms §3-7）: 自動・非人間のアクセスは「API キー経由か、Anthropic が明示的に許す場合」を除き禁止。routines の公式ページが監視ツールからの起動を使い道として載せていることを「明示的に許す場合」の根拠とする。規約本文に routines を名指しした一文は見つけていない【事実：上記ページを確認】。また legal-and-compliance ページ（https://code.claude.com/docs/en/legal-and-compliance）は "Advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code" と書く。監視からの常時起動がこの「ordinary」に入るかを明言した一文は無い【未確認】（不明点 7）。

---

## 段階0 実測（2026-10-13 21:11 JST・PO 手元実行・読み取り専用）

根拠: PO 実行の読み取り script 出力（repo 外保存）。比較基準の origin/main は b905eab150a0865564c91d5e4fac9e4a5cb0969a。サーバーは prod1（アプリ）・prod2（監視）と表記する（repo は PUBLIC のため接続先は書かない）。

【事実】

| 項目 | 実測 |
|---|---|
| Prometheus ルール | repo 15 本・prod2 ファイル 15 本・稼働中 15 本。ルール名・ファイル内容とも一致（稼働中とファイルの差＝reload 漏れも無し） |
| Loki ルール（ファイル） | repo 6 本・prod2 ファイル 4 本。repo のみ: BackendErrorSpike・DiscordDmWriterError・DiscordGatewayReconnectFailure。prod2 のみ: DatabaseError。内容は不一致 |
| Loki ルール（稼働中 API の応答） | 0 本 |
| 通知設定ファイル | alertmanager.yml・prometheus.yml・docker-compose.monitoring.yml は prod2 と一致。grafana の alerting.yml は prod2 で読めず判定不能 |
| Alertmanager | v0.28.1（repo 記載と一致）。起動 2026-07-18 |
| Grafana | 管理アラートルール 0 件。contact point は discord 1 件 |
| Uptime Kuma | 通知先 discord 1 件（有効）。監視 4 項目すべてに紐付け |
| 空きメモリ（available） | prod1 1133MB（swap 415/2047MB 使用）・prod2 2541MB（swap なし） |
| HighDiskUsage 発火区間（UTC） | 2026-09-30T10:55〜10-01T03:39、10-01T06:30〜10-02T11:44 |
| 後者区間の送信 | Prometheus→Alertmanager 破棄 0・エラー 0 |
| Alertmanager→Discord | 送信試行 累計 3967・失敗 累計 0（7/18 起動以降。10/2 を含む） |
| F2CleanupStale | 2026-09-28T00:00Z〜10-03T19:00Z 連続発火（雑音候補。KGI 2 の精度に影響） |
| 現在の状態 | 発火中アラート 0・サイレンス 0 |

【事実】Discord の監視チャンネルに 2026-09-30 19:55〜10-02 20:44 JST の間の HighDiskUsage 通知が表示されていた（根拠: PO 目視 2026-10-13・PO 回答 "y"）。

【未確認】

- Loki の稼働中 0 本が「実際に未読込」か「テナント指定（auth_enabled:false 時の fake テナント等）による見え方」かは未切り分け。段階1の最初に確認する。
- F2CleanupStale の連続発火に対する対応の要否の一次記録。
- grafana の alerting.yml の repo と prod2 の一致（prod2 で読めない）。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | クラウドの AI セッションから VPS へ SSH（22 番）で入れるか | 公式に記述なし。設計では SSH を使わず、HTTPS の受け口だけにする（design §5 段階4）。SSH 可否は確かめない | ✅ 設計で回避 |
| 2 | Alertmanager v0.28.1 が `http_headers` を受け付けるか | 設計では Alertmanager から routines を直接呼ばず、保守 API（prod1 の backend）が呼ぶ（design §5 段階2・4）。保守 API への認証は Bearer（`authorization`）だけを使う | ✅ 設計で回避（段階2 カードで `amtool check-config` を必須確認にする） |
| 3 | prod2 で動いているルール・Alertmanager の版・Kuma の通知先・prod1/prod2 の空きメモリ | 本番の読み取りを Sonnet に委任したが、自動の安全装置に止められた（「Credential Exploration」。言い換え再試行はしていない）。段階0 で PO に読み取り専用の script を `!` で 1 回実行してもらう | ⏳ 段階0 で解消（解消まで段階1 のカードは発行しない） → 【更新 2026-10-13】閉じた（上記「段階0 実測」。Loki ルールの差と稼働 0 本は段階1 へ） |
| 4 | アプリの bot API キーを保守 AI 用に流用できるか | テナント単位のキー（`backend/app/routers/bots.py:55`）。段階2 の設計カードで、保守専用の範囲を絞ったキーを新設するか流用するかを比較する | ⏳ 段階2 カードで解消 |
| 5 | クラウドの AI が Grafana の読み取り専用トークンで必要な問い合わせをできるか | 段階4 の試作で 1 回試す（network secrets に Viewer トークンを登録） | ⏳ 段階4 試作で解消 |
| 6 | 2026-10-02 の HighDiskUsage が Discord に届いたか | Discord の監視チャンネル履歴を段階0 で確認 | ⏳ 段階0 で解消 → 【更新 2026-10-13】機械側は送信失敗 0 まで確認（上記「段階0 実測」）。Discord 表示は PO 目視待ち → 【閉じた 2026-10-13】PO 目視で Discord の監視チャンネルに 2026-09-30 19:55〜10-02 20:44 JST の HighDiskUsage 通知が表示されていたことを確認 |
| 7 | 監視からの routines の常時起動が、サブスクの「ordinary, individual usage」の範囲に入るか | 公式文書に明言なし。段階4 の前に PO 判断を仰ぐ（Anthropic への問い合わせ・案 D/E への切替を含む）。それまで段階4 の実装カードは発行しない | ⏳ 段階4 前に解消 |

**未解決の状態**: 未解決 3 件（#4・#5・#7。#3・#6 は 2026-10-13 に閉じた）。いずれも該当する段階のカード発行前に解消する条件にした（design §5）。本 recon と design は「設計案」であり、各段階の実装可否は解消後に判断する。

---

## 補足

- 生データ: /tmp/CC報告ファイル/ai-ops-recon-raw.md（監視設定・本番発火実績・過去障害）、ai-ops-external-research.md（公式仕様・外部事例）、ai-ops-facts-2.md（契約・版）、mcp-inventory-mac.md / mcp-inventory-repo.md（MCP の棚卸し）。
- Context7: 「Monthly quota exceeded」で使えなかった。起動指示の代替手順どおり公式ページを直接確認した。
