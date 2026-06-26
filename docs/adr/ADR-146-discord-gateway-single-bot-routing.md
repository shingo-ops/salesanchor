# ADR-146: Discord「顧客受信」を「共通bot1台＋guild_id振り分け」(B方式)へ全面移行する

## Status

Proposed

## Context

SalesAnchor を「自社(004)だけでなく他テナントにも同仕様で提供するSaaS」にするのがゴール。
Discord受信について、現状は **A方式（テナントごとに専用bot・専用トークンを起動）** だが、これは新テナント追加のたびに「botアプリ作成→トークン発行→Secrets登録→PR→デプロイ」が必要で、SaaS拡大に不向き。
POの望む形は **B方式（共通bot1台が全テナントのサーバーを受信し、サーバー番号(guild_id)でテナントを判定して振り分け）**。新テナントは「共通botを自サーバーに招待＋管理画面でボタン1回」で使える。

### 確定事実（recon・実機・file:line）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | 現状はA方式。鍵 `DISCORD_BOT_TOKEN_{n}` の数だけGatewayを起動し、各Gatewayは起動時に1テナント固定 | `config.py:35-42` / `main.py:104` / `client.py:67` |
| F2 | 受信時のテナント判定は「起動時に紐づいたtenant_id（=トークン由来）」のみ。guild_idからの逆引きは存在しない | `client.py:244` / `dm_writer.py:69` / `ticket_channel_writer.py:68` |
| F3 | `tenant_discord_config.guild_id` に UNIQUE制約なし（PKはtenant_id） | `migrations/099_add_discord_guild_config.sql:6-11` |
| F4 | 稼働中の鍵は `DISCORD_BOT_TOKEN_4` 1本のみ（deploy.yml・docker-compose.yml 確認済み） | `deploy.yml:217,249` / `docker-compose.yml:98` |
| F5 | 004のDiscordは**テスト確認のみ・実顧客は未使用** | PO確認 |
| F6 | 006用は004本番とは別のテストサーバー・bot1台（現状で混線リスクなし） | PO確認 |
| F7 | B方式ではDMはguild_idを持たず逆引き不可（DMは対象外と決定済み） | `client.py:234-244` / PO決定 |
| F8 | 在庫取得は事実上停止中（`supplier_discord_routing` 0行で全件 `ignored_routing`、最後の実解析は2026-05-29）。かつ `on_message` 経路では在庫処理に未到達（`ticket_channel_writer.py:112` が必ず True 返却）。在庫は `on_resumed` 時のみ処理 | recon INV-1 / 本番DB SELECT |

## Decision

**Discord「顧客受信」をB方式へ全面移行する。在庫取得は本ADRのスコープ外（別プロジェクト）。**

- 既存の唯一のbot（アプリ1個・トークン1本）を**そのまま「顧客共通bot」に昇格**させる。新規にbotを作らない。
- **共通botは"顧客サーバー"にのみ参加させる**（在庫サーバーには入れない）。これによりレールを物理分離する（PO決定）。
- 受信時に `message.guild.id → tenant_discord_config 逆引き → tenant確定` に作り替える。
- **DMは受信対象から外す**（F7・PO決定済み）。
- **在庫取得は今回スコープ外**: 在庫経路コード（`inbound_writer` / `_process_message` / `_resume_missed_messages`）は**削除せず休眠のまま残す**。在庫の取り込み方式は予定の在庫移行プロジェクトで設計する（F8: 現在停止中のため作り込み無駄を回避）。
- **PR #2605（`DISCORD_BOT_TOKEN_6` 追加）はcloseする**（同一トークンで2台起動＝二重ログインで004本番断絶のため）。

### なぜ PR #2605 をマージしてはいけないか

botアプリが1個＝トークンが1本（F4）。#2605 が入れる「006用の鍵」に設定できる値は **004と同じ唯一のトークン** しかない。同一トークンで2つのGatewayを同時起動すると Discord上で **同一botの二重ログイン** となり、**本番004側のDiscord接続が落ちる**。A方式で006を動かす道は最初から成立しない。**マージ禁止・PRはclose。**

### KGI / KPI

- **KGI**: 新テナントが共通botを招待し管理画面でボタン1回押すだけで受信箱が機能する。鍵追加・PR・デプロイ不要。004の受信箱に新テナントのメッセージが混ざらない。
- **K1**: bot 1台へ統合
- **K2**: guild_idでテナントを判定し正しい受信箱へ振り分け
- **K3**: 1サーバー＝1テナント（UNIQUE制約でDBレベル保証）
- **K4**: 新テナント増設は招待＋ボタンのみ（鍵/PR/デプロイ不要）
- **K5**: 既存004は無傷・混線なし

## Consequences

### 変更一覧

| 箇所 | 変更概要 | 危険度 |
|---|---|---|
| `discord_gateway/config.py` | 鍵スキャンループ廃止 → 単一 `DISCORD_BOT_TOKEN` 読込 | コード（要デプロイ） |
| `discord_gateway/main.py` | テナント別タスク生成廃止 → 単一Gateway起動 | コード（要デプロイ） |
| `discord_gateway/client.py` | `self.tenant` 起動時固定廃止 → 受信時に guild_id逆引きでtenant確定（DB非同期クエリ追加） | コード（要デプロイ） |
| `migrations/` | `tenant_discord_config` に `UNIQUE(guild_id)` 追加 | ★migration＝GO必須 |
| 本番DB | 004の guild_id を `tenant_discord_config` に INSERT（共通botに004を担当させる） | ★本番INSERT＝GO必須（004 guild_id はPO取得） |
| `deploy.yml` / `docker-compose.yml` | `DISCORD_BOT_TOKEN_{n}` 群を `DISCORD_BOT_TOKEN` 1本へ統合 | ★deploy.yml＝GO必須 |

### 実装前に閉じる確認

1. ~~トークン唯一性の裏取り~~（**解決済み**: `DISCORD_BOT_TOKEN_4` のみ確認 → F4確定）
2. **004の本番guild_id** ← PO取得（004サーバー右クリック→IDコピー）
3. ~~guild_id未登録サーバー受信時の挙動と在庫解析経路への影響~~（**解決済み**: recon B-2/INV-1 で在庫経路は `supplier_discord_routing` で独立動作・共通botを顧客サーバーのみに参加させるためレール物理分離。未登録guild＝無視+ログのみで在庫に影響なし）

### リスクと対策

- **二重ログイン事故**: deploy.yml の `DISCORD_BOT_TOKEN_{n}` 全削除と新 `DISCORD_BOT_TOKEN` 追加を同一デプロイで原子的に行う（旧A方式との混在ゼロ）。
- **本番フルデプロイ**: mainマージで gateway が再起動（低トラフィック帯にマージ）。004のDiscordはテスト専用（F5）なので受信停止の実害は小。
- **取り違え**: `UNIQUE(guild_id)` で1サーバー＝1テナントをDBレベルで保証。
- **在庫経路の休眠**: 在庫コードは削除せず温存。共通botを顧客サーバーのみに参加させる運用制約で `on_resumed` 補完が在庫サーバーに触れないようにする。

### ロールバック

- コード/compose/deploy.yml: revert PR → 次デプロイで旧A方式に戻る。
- `UNIQUE(guild_id)`: downマイグレーションで除去。
- 004 guild行: `DELETE FROM public.tenant_discord_config WHERE tenant_id = 4`（INSERT前にスナップショット保存）。

## Alternatives Considered

- **A方式維持**: 新テナント追加ごとにbot作成・鍵・PR・デプロイが必要。SaaS拡大に不向き。かつF4よりトークン1本のため複数テナント同時起動が二重ログインで破綻。→却下。
- **A+B併存**: 004はA方式のまま・新テナントのみB方式。しかしトークン1本で004専用Gatewayと共通Gatewayが同一トークンで二重ログイン→技術的に不成立（F4）。→却下。
- **DMもBで受信**: guild_idを持たないDMはtenant逆引き不能。別ルーティング設計が必要で複雑化。→不採用（PO決定）。
- **専用在庫bot同時作成**: 在庫は現在停止中（F8）かつ移行プロジェクト予定あり。今作ると移行設計と競合する。→今回は不採用。
