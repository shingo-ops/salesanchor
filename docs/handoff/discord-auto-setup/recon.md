# recon: Discord Bot招待後サーバー初期構築ウィザード

**日付**: 2026-06-14  
**ブランチ**: `feature/morimoto/discord-auto-setup-design`  
**KGI**: Bot招待後、Discord側でカテゴリ・チャンネル・ロール・チケットボタンを手作業なしに Sales Anchor から自動構築できること

---

## 既存ADR検索結果

| ADR | 関連度 | 概要 |
|-----|--------|------|
| `docs/adr/ADR-091-discord-bot-scope-definition.md` | **HIGH** | Bot担当業務7項目定義。**対象外**に「Discord サーバーの初期構築・チャンネル設計（人手で行う）」と明記 → 本機能はこれを拡張する |
| `docs/ADR-009_discord_gateway.md` | HIGH | Discord Gateway常駐アーキテクチャ。Bot permissions・接続設計の根拠 |
| `docs/adr/ADR-072` (CLAUDE.md参照) | MEDIUM | write endpoint の `reset_tenant_context()` 必須ルール（新規APIエンドポイントに適用） |
| `docs/adr/FEATURE-INDEX.md` | 参照済み | Discord セクションなし（ADR-091が正準） |

**grep確認**: `git grep -i "auto.setup\|初期構築\|wizard\|bootstrap" docs/adr/` → 該当なし（既存ADR設計なし）

---

## コード実証（file:line 引用）

### 1. Bot招待後の現在フロー

| ステップ | ファイル:行 | 内容 |
|---------|------------|------|
| OAuth開始 | `backend/app/routers/discord_oauth.py:78-105` | `POST /discord/oauth/start` → invite_url発行 |
| コールバック受信 | `backend/app/routers/discord_oauth.py:113-186` | `GET /discord/oauth/callback` → guild_id保存 |
| guild_id保存先 | `backend/app/routers/discord_oauth.py:159-170` | `public.tenant_discord_config` に upsert |
| リダイレクト先 | `backend/app/routers/discord_oauth.py:186` | `/channels?discord_status=connected` |
| フロント受信 | `frontend/src/pages/channels/ChannelsPage.tsx:119-129` | `discord_status=connected` → success バナー表示のみ |

**ギャップ**: コールバック後はバナー表示のみ。初期構築ステップなし。

### 2. 既存Botパーミッション

| ファイル:行 | 内容 |
|------------|------|
| `backend/app/routers/discord_oauth.py:47` | `_DISCORD_PERMISSIONS = "268504082"` |

268504082 を展開すると:
- `MANAGE_CHANNELS` (1 << 4) ✅ → カテゴリ・チャンネル作成に必要
- `MANAGE_ROLES` (1 << 28) ✅ → ロール作成・付与に必要
- `VIEW_CHANNEL` (1 << 10) ✅
- `SEND_MESSAGES` (1 << 11) ✅ → チケットボタン投稿に必要
- `READ_MESSAGE_HISTORY` (1 << 16) ✅

**追加パーミッション不要**: 既存の268504082で自動セットアップに必要な全操作をカバー済み。

### 3. 既存DB（保存先）

| テーブル | ファイル:行 | 列 |
|---------|------------|-----|
| `public.tenant_discord_config` | `migrations/099_add_discord_guild_config.sql:6-11` | `tenant_id`, `guild_id`, `connected_by_staff_id`, `created_at`, `updated_at` |
| `public.tenant_discord_ticket_config` | `migrations/20260602_120000_add_discord_ticket_config.sql` | `tenant_id`, `ticket_category_id`, `ticket_button_channel_id`, `staff_role_id`, `welcome_template`, `small_channel_id`, `large_channel_id`, `small_role_name`, `large_role_name` |

**自動セットアップで埋める列**: `ticket_category_id`, `ticket_button_channel_id`, `staff_role_id`, `small_channel_id`, `large_channel_id` の5列。既存テーブルで過不足なし（migration不要）。

### 4. 既存のDiscord REST基盤

| ファイル:行 | 内容 |
|------------|------|
| `backend/app/services/discord_rest.py:34-136` | `discord_api_request()`: 429/5xx リトライ・指数バックオフ実装済み |
| `backend/app/services/discord_role_sync.py:82-105` | `_get_or_create_role()`: ロール名で検索→なければ作成（冪等） |
| `backend/app/discord_gateway/ticket_channel_creator.py:98-217` | `get_or_create_ticket_channel()`: プライベートチャンネル冪等作成の実装例 |
| `backend/app/routers/discord_ticket_config.py:219-313` | `deploy_ticket_button()`: チケットボタン投稿の実装例 |

### 5. カテゴリ・チャンネル作成のDiscord API

現在使われていない操作（自動セットアップで新規追加）:

| 操作 | Discord API | 備考 |
|------|-------------|------|
| カテゴリ作成 | `POST /guilds/{guild_id}/channels` `type=4` | `discord.py` では `guild.create_category_channel()` |
| テキストチャンネル作成 | `POST /guilds/{guild_id}/channels` `type=0` | `category_id` を指定 |
| ロール作成 | `POST /guilds/{guild_id}/roles` | `discord_role_sync.py:97` に実装済み |

### 6. 既存手入力設定との関係

| 設定項目 | 手入力（現在） | 自動セットアップ後 |
|---------|--------------|-----------------|
| Guild ID | OAuth callback で自動 | 変わらず |
| ticket_category_id | `/admin/discord-config` で手入力 | 自動生成IDが上書き |
| ticket_button_channel_id | 同上 | 自動生成IDが上書き |
| staff_role_id | 同上（任意） | 自動生成IDが上書き |
| small_channel_id | 同上 | 自動生成IDが上書き |
| large_channel_id | 同上 | 自動生成IDが上書き |
| small_role_name / large_role_name | 同上（デフォルト: Member/Partner） | 変わらず（ロール作成時の名前として使用） |
| ウェルカムメッセージ | 同上 | 変わらず（チケット作成時に使用） |

**方針**: 自動セットアップはID列のみ書き込む。ロール名・ウェルカムメッセージは手入力のまま流用。自動セットアップ後も手動上書き可能。

### 7. Botロール順ガイド

| ファイル:行 | 内容 |
|------------|------|
| `docs/runbooks/discord-role-order-guide.md` | 非エンジニア向けBotロール順設定ガイド（PR #2145でマージ済み） |

---

## 不明点・推測ゼロの状態確認

| 項目 | 状態 | 根拠 |
|------|------|------|
| 自動セットアップに必要なBot権限 | **明確** | 既存268504082で足りる（上記展開済み） |
| 保存先テーブル | **明確** | tenant_discord_ticket_config の既存列で十分 |
| 冪等処理パターン | **明確** | ticket_channel_creator.py と discord_role_sync.py に先例あり |
| `reset_tenant_context` 必要 | **明確** | 新規書込エンドポイントはADR-072準拠 |
| migration必要か | **明確・不要** | 既存テーブルの既存列を使うのみ |
