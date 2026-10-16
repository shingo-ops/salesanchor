# 段階2 障害記録と保守 API — 便割りの設計

> この文書は何か：AI保守運用24時間化（ADR-1012）の段階2「障害記録と保守 API」を、1便1目的の実装便に分けた設計です。親の設計は [design.md](design.md) §5 段階2（:103-110）。各便の作業指示書（カード）は、この文書を元に便ごとに作ります。

- 親設計: docs/handoff/ai-ops-247/design.md §5 段階2（:103-110）・配線と DB の正本（:63-73）・受け入れ基準（:185-186）・影響範囲のデータ・本番（:230-231）
- 現状調査: docs/handoff/ai-ops-247/recon.md（段階2 の追加調査は下の生出力）
- KGI: docs/specs/ai-ops-247/kgi.md:18-25（段階2 は KGI 1〜6 の物差し＝判定に使う記録を作る段。段階2 だけで○になる KGI は無い）
- 対象ADR: ADR-1012（本テーマ・Proposed）、ADR-1018（public の表の RLS の型）、ADR-135（main マージ＝本番投入可）、ADR-136（危険 PR の GO）、ADR-1003（GO 委任）
- 状態: 設計案作成済み・Opus 自己審査 APPROVE（§9）。PO 承認：段階2 の着手は PO の「次を進める」（2026-10-16）。PO に決めてもらう方向性の点は無い（§3 の変更点はすべて技術判断で、親設計の目的・範囲を変えない）。実装未着手
- 事実の生出力: /tmp/CC報告ファイル/ai-ops-stage2-recon/（現在地）・/tmp/CC報告ファイル/ai-ops-stage2-recon/raw2/（実物の詳細）。2026-10-16 取得。本番は読み取りのみ

## 1. 前提の事実（2026-10-16・origin/main 2bd773fcd 基準）

| # | 事実 | 出典 |
|---|---|---|
| T1 | Alertmanager の設定は 11 行。受け先は Discord の 1 つだけ（`discord_configs`・`send_resolved: true`）。まとめ方は `alertname`・`job`・`instance`、繰り返しは 4h | `monitoring/alertmanager/alertmanager.yml:1-11` |
| T2 | Alertmanager は prod2 で v0.28.1。秘密はファイルを読み取り専用で差し込む（`./secrets/alertmanager-discord-webhook`） | `docker-compose.monitoring.yml:176-191` |
| T3 | CI で `amtool check-config` を同じ版（v0.28.1）で実行している | `.github/workflows/monitoring-check.yml:70-74` |
| T4 | prod2 の Prometheus は、prod1 の 443 番に IP 直で繋ぎ（`49.212.137.46:443`）、`server_name` で名前を渡して `/metrics` を取っている。prod1 の nginx は `/metrics` を prod2 の IP（`49.212.160.98`）だけに許している。BackendHighLatency が 30 日で 447 回鳴った（段階1 S18）ので、この経路は実際に通っている | `monitoring/prometheus/prometheus.yml:34-45`・`nginx/nginx.conf:246-256`・stage1-design.md §1 S18 |
| T5 | Alertmanager の webhook の公式仕様：`url`／`url_file`・`send_resolved`・`max_alerts`・`timeout`・`http_config`。`http_config.authorization` は `type`（既定 Bearer）と `credentials_file`。`http_config.tls_config.server_name` が使える。送る中身は `version "4"`・`groupKey`・`truncatedAlerts`・`status`・`receiver`・`groupLabels`・`commonLabels`・`commonAnnotations`・`externalURL`・`alerts[]`（各 `status`・`labels`・`annotations`・`startsAt`・`endsAt`・`generatorURL`・`fingerprint`）。route の `continue: true` は、後ろの兄弟の照合を続ける | prometheus.io/docs/alerting/latest/configuration（2026-10-16 に WebFetch で直接確認。Context7 は月の上限で使えず） |
| T6 | webhook を受け取るコードは backend に無い。障害の記録の表も、全体を止めるスイッチの表も無い | raw2/a_ls_backend.txt・raw2/a1_public_tables.txt |
| T7 | migration は生 SQL で migrations/YYYYMMDD_HHMMSS_*.sql（日時＋名前の形） に置き、`scripts/run_all_migrations.sh` に 1 行ずつ登録する。冪等（`IF NOT EXISTS`・`DROP POLICY IF EXISTS`）が必須 | `scripts/run_all_migrations.sh`（末尾 :936 以降）・raw2/a4_conventions.txt |
| T8 | public の表の前例は UUID の主キー・`TIMESTAMPTZ`・`CHECK` で値を縛る形 | `migrations/20260930_150000_create_llm_usage_events.sql:26-53` |
| T9 | 「アプリの接続から読み書きを運用者だけに絞る」RLS の前例。`ENABLE`＋`FORCE`、ポリシーの条件は `current_setting('app.is_operator', true) = 'true'` | `migrations/20261015_130000_add_permissions_rls.sql:1-13`・`docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md:23` |
| T10 | `app.is_operator` を立てる関数・戻す関数がある。本番のアプリの DB ロール `salesanchor_app` は RLS を飛ばせない（`rolbypassrls=f`） | `backend/app/auth/dependencies.py:489`（`set_operator_context`）・同 :504 付近（`reset_operator_context`）・/tmp/CC報告ファイル/celery-unregistered-tasks-fix/k2/explain/result.txt Q6 |
| T11 | 機械用の鍵の前例：env の値と `secrets.compare_digest` で照合し、非 ASCII などの例外は「不一致」に倒す | `backend/app/auth/dependencies.py:41-45`・`:119-128` |
| T12 | bot キーはテナントごとに bcrypt で作る形で、テナントをまたぐ照合の経路が無い（保守 API に流用できない） | `backend/app/routers/bots.py:55-59` |
| T13 | 新しい env を本番に足すには 3 か所を直す：deploy.yml の古い行の削除（`sed -e '/^KEY=/d'`）、deploy.yml の書き込み（`cat >> .env <<'ENV_EOF'`）、compose の backend の `environment` | `.github/workflows/deploy.yml:273`・`:299-331`・`docker-compose.yml:105`・`:118` |
| T14 | 危険パスは `migrations/`・`scripts/`・`.github/workflows/deploy.yml` など。これを含む PR は ADR-136 の GO が要る | `scripts/check-process-artifacts.js:115-124` |
| T15 | 監視の設定を prod2 に配る自動の仕組みは無く、手作業（控え → 置く → main と diff 0 → 再読込）。便7 が毎日ずれを照合する | stage1-design.md §1 S14・§7 U4 |
| T16 | super admin は PO と担当エンジニアだけ。`require_super_admin` は `is_super_admin` が真の利用者だけを通す | `backend/app/auth/dependencies.py:523`・メモリ super_admin_policy |
| T17 | ルーターは `backend/app/main.py` で `include_router` する | `backend/app/main.py:235-243` |

## 2. 便割り（1便1目的・上から順に 1 便ずつ反映して測る）

| 便 | 目的 | 触る場所 | 危険便 |
|---|---|---|---|
| A | 障害記録の表を作る（空のまま） | `migrations/`・`scripts/run_all_migrations.sh` | はい（ADR-136 の GO） |
| B | 保守 API を作る（受け口・読む・注記・止める） | `backend/`・`nginx/nginx.conf`・`.github/workflows/deploy.yml`・`docker-compose.yml` | はい（deploy.yml） |
| C | Alertmanager の受け先に保守 API を足す | `monitoring/alertmanager/alertmanager.yml`・`docker-compose.monitoring.yml`・prod2 の秘密ファイル | いいえ（ただし prod2 への手作業の配置） |

順番の理由：表が無いと API は書けない（A → B）。API が無いと Alertmanager は送り先を失って失敗を数える（B → C）。各便は反映して測ってから次に進む。

### 秘密（鍵）の扱い（全便共通）

- 鍵は 2 本。どちらも `secrets.token_urlsafe(32)`（256 bit）
  - 受け口の鍵（`OPS_INGEST_TOKEN`）：Alertmanager だけが持つ。受け口の POST 1 本にだけ効く
  - 保守の鍵（`OPS_API_TOKEN`）：AI と応急処置係が持つ。読む・注記する・止める（ON）にだけ効く
- 作るのは PO の `!` スクリプト 1 回（secrets の変更は PO の操作。CLAUDE.md の不可逆操作の一覧）。スクリプトは鍵を作り、`gh secret set` に 2 本を登録し、受け口の鍵を prod2 の `secrets/ops-ingest-token` に置き、保守の鍵を Mac の `~/.claude-access.env` に足す。鍵の値は画面に出さない
- 置く時期：保守の鍵は便B の反映の前、受け口の鍵は便C で作って置く（2026-10-16 便B カード D1・便C カード D1 で改めた。env が空の口は全部拒否＝§2 便B の B6）

### 便A 障害記録の表

表は 3 つ。すべて public・RLS は T9 の型を「読みも運用者だけ」に広げたもの（運用者の旗が立っているときだけ SELECT・INSERT・UPDATE を許す。DELETE のポリシーは作らず、アプリのロールから DELETE の権限も外す＝記録は消せない。2026-10-16 便A カード作成時に FOR ALL から絞った）。テナントの業務データには触れない。tenant_004 の表は読まない（親設計 :230）。

`public.ops_incidents`（1 件の障害＝1 行）

| 列 | 型 | 意味（どの KGI の物差しか） |
|---|---|---|
| id | UUID PK | |
| fingerprint | TEXT NOT NULL | Alertmanager の alert の fingerprint |
| starts_at | TIMESTAMPTZ NOT NULL | alert の startsAt |
| UNIQUE (fingerprint, starts_at) | | 同じ通知の繰り返しを 1 行にまとめる（KGI 2「繰り返しは 1 件」） |
| alertname | TEXT NOT NULL | labels.alertname |
| severity | TEXT | labels.severity（札 page/auto/ticket） |
| labels | JSONB NOT NULL | alert の labels（4KB まで。超えたら受け口で切って `truncated` を立てる） |
| annotations | JSONB NOT NULL | 同 annotations（4KB まで） |
| status | TEXT NOT NULL CHECK (firing/resolved) | 今の状態 |
| first_notified_at | TIMESTAMPTZ NOT NULL | 最初に受けた時刻（KGI 1・5 の「通知時刻」） |
| last_notified_at | TIMESTAMPTZ NOT NULL | 最後に受けた時刻 |
| notify_count | INTEGER NOT NULL DEFAULT 1 | 受けた回数 |
| resolved_at | TIMESTAMPTZ | resolved を受けた時刻（endsAt） |
| recurrence_of | UUID FK → ops_incidents(id) | 同じ fingerprint の前の行（KGI 4・6 の再発） |
| detection_path | TEXT CHECK (alert/human/ai) DEFAULT 'alert' | 最初に気づいた経路（KGI 1） |
| human_noticed_at | TIMESTAMPTZ | 人が気づいた時刻（KGI 1） |
| needs_action | BOOLEAN | 要対応だったか（KGI 2。振り返りで付ける） |
| first_aid_started_at・first_aid_done_at | TIMESTAMPTZ | 応急処置の開始・完了（KGI 3。段階3 が書く） |
| first_aid_result | TEXT CHECK (recovered/not_recovered/escalated) | 応急処置の結果（KGI 3） |
| ai_started_at | TIMESTAMPTZ | AI の着手（KGI 5。段階4 が書く） |
| root_cause | TEXT | 原因（KGI 4 の再発の判定に使う） |
| fix_pr | INTEGER | 修理の PR 番号（KGI 4） |
| review_note | TEXT | 振り返り（KGI 6） |
| created_at・updated_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

`public.ops_incident_events`（追記だけの出来事の記録）

| 列 | 型 | 意味 |
|---|---|---|
| id | UUID PK | |
| incident_id | UUID NOT NULL FK → ops_incidents(id) | |
| occurred_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| kind | TEXT NOT NULL CHECK (notified/resolved/annotated/first_aid/ai/halt) | 何が起きたか |
| actor | TEXT NOT NULL CHECK (alertmanager/ops_token/super_admin) | 誰が書いたか |
| detail | JSONB NOT NULL | 中身（8KB まで） |

追記だけにする手段：RLS で UPDATE・DELETE のポリシーを作らない（INSERT と SELECT だけ）。アプリのロールから UPDATE・DELETE の権限も外す。

`public.ops_control`（全停止スイッチ。1 行だけ）

| 列 | 型 | 意味 |
|---|---|---|
| id | SMALLINT PK CHECK (id = 1) | 1 行だけを強制 |
| halt_all | BOOLEAN NOT NULL DEFAULT false | true の間、処置と AI 起動をしない（段階3・4 が読む） |
| changed_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| changed_by | TEXT NOT NULL | ops_token／super_admin の利用者 ID |
| reason | TEXT | |

初めの 1 行は migration で入れない（ADR-155「migration は構造の変更だけ」。2026-10-16 便A カード作成時に変更）。行が無いときは「止めていない（halt_all=false）」として扱い、便B の B5 が最初に ON にするときに 1 行を作る（`INSERT ... ON CONFLICT (id) DO UPDATE`）。

便A の測り方：反映後に、3 表があり、RLS が ENABLE・FORCE で、ポリシーが表ごとに決めた数だけあり、`salesanchor_app` に DELETE の権限が無いこと（PO 実行の読み取り。カード §8）。

### 便B 保守 API

ルーター backend/app/routers/ops.py（新設） を新設し、`/api/v1/ops` に付ける（T17）。DB への読み書きの前に `set_operator_context`、commit の後に `reset_operator_context` を呼ぶ（T10）。

| # | 口 | 鍵 | 動き |
|---|---|---|---|
| B1 | `POST /api/v1/ops/alertmanager` | 受け口の鍵 | webhook の中身（T5）を受け、`alerts[]` の 1 件ごとに `(fingerprint, startsAt)` で ops_incidents を作るか更新する。更新は `last_notified_at`・`notify_count`・`status`・`resolved_at` だけ。新しく作るとき、同じ fingerprint の前の行があれば `recurrence_of` に入れる。1 件ごとに ops_incident_events に `notified`／`resolved` を 1 行足す。全停止スイッチが ON でも記録は続ける（§3 変更点 2） |
| B2 | `GET /api/v1/ops/incidents`（`status`・`since`・`limit` 最大 100） | 保守の鍵 または super admin のログイン | 一覧 |
| B3 | `GET /api/v1/ops/incidents/{id}` | 同上 | 1 件と出来事 |
| B4 | `POST /api/v1/ops/incidents/{id}/events` | 同上 | 注記（`kind` は annotated/first_aid/ai）。決まった列（`human_noticed_at`・`first_aid_*`・`ai_started_at`・`root_cause`・`fix_pr`・`needs_action`・`review_note`・`detection_path`）だけを、許可した名前の一覧で更新する |
| B5 | `GET /api/v1/ops/control`・`POST /api/v1/ops/control/halt` | 同上 | スイッチを読む・ON にする。OFF に戻す `POST /api/v1/ops/control/resume` は super admin のログインだけ（鍵では戻せない。AI が自分で止めを外さないため） |
| B6 | 鍵の照合 | | T11 と同じ形。env が空なら、その鍵の口は全部 401（空の鍵で通らない）。受け口の鍵で B2〜B5 は通らず、保守の鍵で B1 は通らない |

受け付ける大きさの上限：本体 256KB（nginx の `client_max_body_size` を口に付ける）・`alerts[]` 100 件まで。それを超えたら 413。中身の検査は pydantic で、知らない項目は捨てる。

nginx：api.salesanchor.jp の server（`nginx/nginx.conf:289` の block）に `location = /api/v1/ops/alertmanager` を足し、`/metrics` と同じく prod2 の IP だけを許す（`allow 49.212.160.98; deny all;`）。ほかの B2〜B5 は既存の `/api/` の扱いのまま（鍵か super admin のログインで守る）。

env：`OPS_INGEST_TOKEN`・`OPS_API_TOKEN` を T13 の 3 か所に足す。

便B の測り方：pytest（B1 の冪等・繰り返しの合算・再発の結び付き・resolved・鍵の取り違え 401・空の鍵 401・上限 413・RLS で operator 以外は 0 行）。反映後に、Mac から受け口を叩いて 403（nginx の IP 制限）、保守の鍵で B2 が 200 と空の一覧。

### 便C Alertmanager の受け先を足す

変更後の `monitoring/alertmanager/alertmanager.yml`（Discord はそのまま残す）:

```yaml
route:
  receiver: discord-server-alerts
  group_by: ["alertname", "job", "instance"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: discord-server-alerts
      continue: true
    - receiver: ops-api
receivers:
  - name: discord-server-alerts
    discord_configs:
      - webhook_url_file: /etc/alertmanager/secrets/discord-webhook
        send_resolved: true
  - name: ops-api
    webhook_configs:
      - url: https://49.212.137.46/api/v1/ops/alertmanager
        send_resolved: true
        max_alerts: 100
        timeout: 10s
        http_config:
          authorization:
            type: Bearer
            credentials_file: /etc/alertmanager/secrets/ops-ingest-token
          tls_config:
            server_name: api.salesanchor.jp
```

- IP 直と `server_name` は T4 の Prometheus と同じ形（名前で引くと Cloudflare など途中の経路で送り元の IP が変わり、nginx の IP 制限に当たるおそれがあるため）
- `docker-compose.monitoring.yml` の alertmanager に `./secrets/ops-ingest-token:/etc/alertmanager/secrets/ops-ingest-token:ro` を足す
- CI：T3 の `amtool check-config` に加え、`amtool config routes test` で「任意の alert が discord-server-alerts と ops-api の両方に届く」ことを確かめる段を足す（`.github/workflows/monitoring-check.yml`。危険パスではない）
- 配置：段階1 と同じ手作業（控え → 置く → main と diff 0 → 再読込）。実行するのは PO の `!` スクリプト 1 回（段階1 の無制限鍵の例外は段階1 の完了で失効した。docs/specs/ai-ops-247/kgi.md:43）。便7 の照合の対象 6 本に alertmanager.yml が含まれるので、ずれは毎日見張られる

便C の測り方：prod2 で `amtool alert add`（擬似アラート 1 件）→ Discord に 1 件・ops_incidents に 1 行。同じ擬似アラートを 2 回目に送ると、行は増えずに `notify_count` が 2。resolved を送ると `resolved_at` が入る。

## 3. 親設計からの変更点と理由

1. 鍵：親設計は「bot キーの流用か新設かをカードで比較」（design.md:106）。bot キーはテナント単位で照合の経路が無い（T12）ため、専用の鍵 2 本を新設する。1 本にしない理由は、外に近い Alertmanager の鍵が漏れても、読む・止めるには使えないようにするため
2. 全停止スイッチ：親設計は「中継・応急処置・AI 起動のすべてがこれを見る」（design.md:108）。段階2 では「スイッチを ON にしても記録は続ける」にする。理由は、止めている間に何が起きたかの記録が無いと、振り返り（KGI 6）ができないため。中継は Discord への通知を指し、それは Alertmanager の側で動き、スイッチを見ない（止めると人が気づけなくなる）。処置と AI 起動を見る側は段階3・4 で作るので、受け入れ基準「ON で処置・AI 起動が 0 件」（design.md:186）の検証は段階3・4 の受け入れに移す（§6）
3. 秘密の配り方：受け口の鍵を prod2 のファイルで渡す（T2 の Discord の webhook と同じ形）

## 4. 段階2 の前に決めると書いた未解決事項（stage1-design.md §7）の扱い

- U1〜U4・U6・U7：段階2 の表と API の設計に影響しない（見張りの条件・配り方の話）。段階1 の残件として扱いを変えない
- U5（Alertmanager を通らない直通通知を寄せるか）：段階2 の前提にしない。理由：直通の 2 経路（Kuma の既存 4 件・`scripts/backup_to_s3.sh:56-70`）は監視基盤そのものとバックアップの失敗で、障害記録に入らなくても Discord で人に届く。寄せると Alertmanager が止まったときに通知も止まる。段階3 で、応急処置の対象にするときに決める
- U8（Discord のコンテナのログが Loki に無い）：段階2 の前提にしない。理由：段階2 は Alertmanager から来るものを記録するだけで、ログの集め方に依存しない。Discord の 2 本のルールが鳴らない問題は、段階1 の残件のまま
- U16（bash の試験を CI で走らせるか）：段階2 の前提にしない。便C の `amtool config routes test` は CI に入れる（§2 便C）

## 5. 弊害と対処

| 弊害 | 起きること | 対処 |
|---|---|---|
| 保守 API が落ちている | Alertmanager の ops-api への送信が失敗し、再送を続ける | Discord は別の子ルートで先に送るので、人への通知は止まらない（`continue: true`）。Alertmanager の失敗の指標 `alertmanager_notifications_failed_total{integration="webhook"}` を段階1 の見張りに足すかは、便C の後に雑音を見て決める（§7 V3） |
| 受け口への大量の送信 | 表が膨らむ | nginx で prod2 の IP 以外は拒む。本体 256KB・100 件の上限。同じ (fingerprint, startsAt) は 1 行 |
| 鍵の漏れ | 受け口の鍵：偽の障害を書かれる。保守の鍵：読まれる・止められる | 鍵は 2 本に分ける（§3-1）。保守の鍵では止めを外せない（B5）。漏れたら PO の `!` スクリプトで作り直す（§8 の手順） |
| RLS の書き忘れ | アプリの接続から運用者以外が読める | RLS は表を作る migration と同じファイルで付ける。pytest で operator 以外は 0 行を確かめる |
| prod1 のメモリ | 受け口の処理が増える | 1 通知 = DB に数行。5 分ごとのまとめ（T1）で多くても 1 時間に十数回 |
| ADR-1018 との食い違い | public の表に RLS の型が増える | T9 の運用者の型の読みを絞った形で、ADR-1018 の段階①の型の範囲。ADR-1018 の表の一覧（機微 11 表）には入れず、ADR-1012 の段階2 で管理する |

## 6. 受け入れ基準（段階2 全体）

| 基準 | 検証方法 |
|---|---|
| 便A: 3 表が本番にあり、RLS が ENABLE・FORCE、ポリシーが ops_incidents 3・ops_incident_events 2・ops_control 3、`salesanchor_app` は 3 表とも DELETE なし・ops_incident_events は UPDATE もなし | PO 実行の読み取り（pg_class・pg_policies・has_table_privilege）の生出力。運用者の旗の有無で行が見える・見えないことは CI の pytest（便A カード §5）で確かめる |
| 便B: pytest で、同じ通知 2 回 = 1 行で notify_count 2・resolved で resolved_at・同じ fingerprint の再発で recurrence_of・鍵の取り違えと空の鍵で 401・上限超えで 413 | CI の pytest（PG の RLS のテストの段を含む） |
| 便B: 反映後、Mac から受け口は 403、保守の鍵で一覧が 200 | Opus が Mac から curl（鍵の値は出さない） |
| 便C: Alertmanager の通知 1 件が障害記録 1 件になり、繰り返しは同じ記録にまとまる（親設計 design.md:185） | prod2 の擬似アラート（amtool）1 件を 2 回送り、resolved を 1 回送る。Discord に届いた投稿と、保守の鍵での B3 の応答の生出力 |
| 便C: Discord への通知は今までどおり届く | 同じ擬似アラートの Discord の投稿時刻 |
| スイッチ: 保守の鍵で ON、super admin のログインで OFF、保守の鍵で OFF は 403、ON の間も記録は続く | pytest と、本番での 1 回の切り替え（PO に時刻を伝える） |
| 親設計 design.md:186「ON で処置・AI 起動が 0 件」 | 段階3・4 の受け入れ基準に移す（§3-2）。段階2 では確かめない |

## 7. 未解決事項

- V1: （解決 2026-10-16）便A の本番確認は SET ROLE を使わず、カタログ（pg_policies・has_table_privilege）を読む形にした。旗の有無での見え方は CI の pytest で確かめる
- V2: 保守の鍵を AI（段階4 のクラウドの routines）に渡す方法。段階4 の設計で決める。段階2 では Mac の `~/.claude-access.env` にだけ置く
- V3: Alertmanager の webhook の失敗を見張るルールを足すか。便C の反映後 7 日の失敗の数を見て決める
- V4: 障害記録を見る画面（月次成績表）は親設計 §5 段階6 の範囲。段階2 では API だけを作る

## 8. 戻し方

- 便C：alertmanager.yml を控えに戻して再読込（Discord だけの元の形）。prod2 の秘密ファイルは残しても害は無い
- 便B：PR の revert を main にマージ。env は残っても使う口が無い
- 便A：表を消す migration（DROP TABLE は不可逆操作。PO 確認）。表が空のうち、または段階2 をやめるときだけ
- 鍵の作り直し：PO の `!` スクリプトをもう一度実行（新しい値で上書き）→ deploy → prod2 で Alertmanager を再読込

## 9. 自己審査（Opus。同一 AI による審査で、独立した第二者レビューではない）

判定：APPROVE（設計として実装に渡せる。便ごとのカードは別に作り、card-lint を通す）

| 観点 | 結果 | 根拠 |
|---|---|---|
| 親設計の目的・範囲と合う | ○ | §3 の変更 3 点は、親設計が「カードで決める」とした点と、検証の時期の移し替え |
| 正本の 1 か所化（親設計 :63-73） | ○ | 障害の記録はアプリ DB の 3 表だけ。Discord は表示。repo（PUBLIC）に置かない |
| 事実に根拠がある | ○ | §1 T1〜T17 に file:line と生出力 |
| 受け入れ基準が○×で判定できる | ○ | §6 は件数・HTTP の番号・列の値で判定 |
| 実装の範囲が明確 | ○ | 便ごとに触る場所（§2 の表） |
| 未確認に依存する合格が無い | ○ | V1 は便A の確かめ方の手段の話で、合否の条件は変わらない。T5 は公式の文書を直接読んだ |
| 外部の仕様 | ○ | Alertmanager の webhook と continue は公式の文書（T5） |

## 10. 外部・過去事例の参照と我々への応用

- 親設計 docs/handoff/ai-ops-247/design.md §7 の事例を引き継ぐ。段階2 に直接効くのは、AWS 2025-10 の教訓（全体を止める 1 か所のスイッチ）。応用：ops_control の 1 行（便A）と、止めを外せるのは人だけ（便B の B5）
- Alertmanager の公式の webhook の仕様（T5）。応用：fingerprint と startsAt で 1 件を決める（便B の B1）
- 過去事例（社内）：SMOKE_SERVICE_TOKEN の照合（T11）と、bot キーの限界（T12）。応用：鍵の照合の形を流用し、用途ごとに鍵を分ける
- 段階2 のために新しく外部事例は調べていない。理由：段階2 は既存の部品（Alertmanager の webhook・PostgreSQL の RLS・FastAPI の Bearer）を公式の仕様どおりに繋ぐ作業で、成否は §6 の実測で判定するため

## 維持の仕組み

- 守り手：CI の pytest（便B の受け口の冪等と鍵の分離）・monitoring-check.yml の `amtool config routes test`（便C）・便7 の毎日の照合（alertmanager.yml の本番と repo のずれ）
- 担当：障害記録の表と保守 API は ADR-1012 のテーマとして Opus が設計し、変更は便ごとのカード → PR → 審査 → GO → 反映の順。本番の表を手で書き換えない（書き込みは保守 API の 1 か所から）
- 見直し：便C の後 7 日で V3 を判断する。段階3 の設計の前に U5 を読み直す
