# ADR-146: Discord受信を「共通bot1台＋guild_id振り分け」(B方式)へ全面移行する

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

## Decision

**Discord受信をB方式へ全面移行する。**

- 既存の唯一のbot（アプリ1個・トークン1本）を**そのまま「共通bot」に昇格**させる。新規にbotを作らない。
- 受信時に `message.guild.id → tenant_discord_config 逆引き → tenant確定` に作り替える。
- **DMは受信対象から外す**（F7・PO決定済み）。
- **PR #2605（`DISCORD_BOT_TOKEN_6` 追加）はcloseする**（同一トークンで2台起動＝二重ログインで004本番断絶のため）。

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

### 実装前に閉じる確認（§9）

1. ~~トークン唯一性の裏取り~~（**解決**: deploy.yml + docker-compose.yml で `DISCORD_BOT_TOKEN_4` のみ確認済み）
2. **004の本番guild_id** ← PO取得（004サーバー右クリック→IDコピー）
3. guild_id未登録サーバー受信時の挙動設計（無視/ログ）および在庫解析経路 `inbound_writer.py` への影響確認（設計recon）

### リスクと対策

- **二重ログイン事故**: deploy.yml の `DISCORD_BOT_TOKEN_{n}` 全削除と新 `DISCORD_BOT_TOKEN` 追加を同一デプロイで原子的に行う（旧A方式との混在ゼロ）。
- **本番フルデプロイ**: mainマージで gateway が再起動（低トラフィック帯にマージ）。004のDiscordはテスト専用（F5）なので受信停止の実害は小。
- **取り違え**: `UNIQUE(guild_id)` で1サーバー＝1テナントをDBレベルで保証。

### ロールバック

- コード/compose/deploy.yml: revert PR → 次デプロイで旧A方式に戻る。
- `UNIQUE(guild_id)`: downマイグレーションで除去。
- 004 guild行: `DELETE FROM public.tenant_discord_config WHERE tenant_id = 4`（INSERT前にスナップショット保存）。

## Alternatives Considered

- **A方式維持**: 新テナント追加ごとにbot作成・鍵・PR・デプロイが必要。SaaS拡大に不向き。かつF4よりトークン1本のため複数テナント同時起動が二重ログインで破綻。→却下。
- **A+B併存**: 004はA方式のまま・新テナントのみB方式。しかしトークン1本で004専用Gatewayと共通Gatewayが同一トークンで二重ログイン→技術的に不成立（F4）。→却下。
- **DMもBで受信**: guild_idを持たないDMはtenant逆引き不能。別ルーティング設計が必要で複雑化。→不採用（PO決定）。
