# recon: Discord 自動セットアップ失敗の原因調査

**日付**: 2026-06-14 / 追記 2026-06-15  
**担当**: Hikky-dev  
**ステータス**: Cause F 確定・PR #2224 作成済み

---

## 症状

- /admin/discord-config の「自動セットアップを実行」ボタンを押すと「自動セットアップに失敗しました。」と表示される
- フロントエンドの catch ブロックが非200レスポンスをキャッチしている
- POST /api/v1/admin/discord/auto-setup が 500 を返している

---

## VPS 実機確認結果（2026-06-14）

| 確認項目 | 結果 |
|---------|------|
| 実行日時 | 2026-06-14 |
| backend container 名 | astro-webapp-backend-1 |
| DISCORD_BOT_TOKEN_4 | set（注入済み） |
| Discord roles GET | ✅ 成功（502 なし） |
| Discord channels GET | ✅ 成功（502 なし） |
| Discord channel POST ch_ticket | ❌ HTTP 403 code=50013 Missing Permissions |
| Discord channel POST ch_member | ❌ HTTP 403 code=50013 Missing Permissions |
| Discord channel POST ch_partner | ❌ HTTP 403 code=50013 Missing Permissions |
| DB: tenant_discord_config.guild_id (tenant_id=4) | ✅ 確認済み |
| DB: tenant_discord_ticket_config (tenant_id=4) | ❌ 0 行（初回実行・未保存） |
| 最終 HTTP ステータス | 500 Internal Server Error |

### バックエンドログ（要約）

```
[discord_auto_setup] channel creation failed step=ch_ticket name=ticket-start:
  Discord API エラー: HTTP 403: Missing Permissions code=50013

[discord_auto_setup] channel creation failed step=ch_member name=member-announcements:
  Discord API エラー: HTTP 403: Missing Permissions code=50013

[discord_auto_setup] channel creation failed step=ch_partner name=partner-announcements:
  Discord API エラー: HTTP 403: Missing Permissions code=50013

Database error: POST /api/v1/admin/discord/auto-setup
  NotNullViolationError: null value in column "ticket_button_channel_id"
  violates not-null constraint

INFO: "POST /api/v1/admin/discord/auto-setup HTTP/1.1" 500 Internal Server Error
```

---

## 原因分類

### Cause D（Discord 権限・ロール順問題）

**確定**：Bot が MANAGE_CHANNELS 権限を有効に行使できない状態。

- トークンは有効（roles/channels の GET は成功）
- チャンネル作成 POST で 403 code=50013 Missing Permissions
- 権限ビットマスク 268504082 には MANAGE_CHANNELS(16) が含まれているが、
  Discord のロール階層上 Bot ロールが Member/Partner より下にあると MANAGE_CHANNELS は機能しない

**Discord 側で必要な対応**:
- Discord サーバー設定 → 役職 → Sales Anchor Bot ロールを Member/Partner の上に移動

### Cause E（backend 実装バグ）

**確定**：チャンネル作成が全失敗（初回実行 = DB に既存行なし）の場合、
DB INSERT 時に ticket_button_channel_id NOT NULL 制約違反が起き 500 になる。

実装箇所: `backend/app/routers/discord_auto_setup.py`

- UPSERT の ON CONFLICT COALESCE で UPDATE は安全だが
  初回 INSERT 時に ticket_ch_id に NULL が渡ると NOT NULL 制約に違反する
- migration ファイルで ticket_button_channel_id カラムが NOT NULL のため

**修正方針（migration 不要・コードのみ）**:
- INSERT 前に「既存行が存在しない（cfg is None）かつ NOT NULL カラムが NULL」の場合は INSERT をスキップ
- 部分成功（ロール作成のみ完了等）を 500 でなく正常な partial ステータスで返す

**追加修正（重複作成防止）**:
- 初回失敗→DB未保存の状態で再実行した場合、Discord 上にカテゴリが存在しても
  DB から existing_id が取れないため重複作成されてしまう
- _get_or_create_channel_step に名前+type+parent_id による検索フォールバックを追加して解消

---

## コード解析結果（参考）

### エンドポイント存在確認

| 確認項目 | 結果 |
|---------|------|
| `backend/app/routers/discord_auto_setup.py` が main に存在 | ✅ PR #2155 マージ済み |
| `backend/app/main.py` への router 登録 | ✅ |
| フロントエンド UI DiscordConfigPage | ✅ PR #2163 マージ済み |
| `backend/tests/test_discord_auto_setup.py` | ✅ |

### 権限ビットマスク確認（268504082）

| 権限 | 値 | 含まれるか |
|-----|---|-----------|
| MANAGE_ROLES | 268435456 | ✅ |
| MANAGE_CHANNELS | 16 | ✅（ビット上は正しい） |
| SEND_MESSAGES | 2048 | ✅ |
| VIEW_CHANNEL | 1024 | ✅ |
| READ_MESSAGE_HISTORY | 65536 | ✅ |

→ 権限ビット自体は正しい。Discord ロール順の問題で有効に機能していない。

---

## 追加調査結果（2026-06-15）

### Cause D 解消確認（ロール位置）

Bot API (PATCH /guilds/{guild_id}/roles) で Sales Anchor ロールを pos=4 に移動済み。

| ロール | position（修正後） |
|------|--------------|
| Sales Anchor | 4 |
| Sales Anchor Staff | 3 |
| Partner | 2 |
| Member | 1 |
| @everyone | 0 |

### Cause F（カテゴリ自己ロックアウト）

**確定**：ロール順修正後も auto-setup が 200 partial（全チャンネル 403）のまま。

根本原因：カテゴリ作成時の permission_overwrites に `@everyone deny VIEW_CHANNEL` のみ設定しており、
Bot 自身が VIEW_CHANNEL を持たない状態でカテゴリ内にチャンネルを作成しようとすると
403 Missing Permissions (50013) が発生する。

Discord の権限計算：「チャンネルに permission_overwrites を設定するには、
Bot がそのチャンネル（親カテゴリを含む）で VIEW_CHANNEL を持つ必要がある」

追加症状：
- 重複 Sales Anchor カテゴリが 4 件存在（過去の失敗分）
- これらは Bot が VIEW_CHANNEL を持たないため DELETE も 403

**修正方針**（コードのみ・migration 不要）:
- `GET /users/@me` で bot_user_id を取得
- カテゴリ作成の permission_overwrites に type=1 member overwrite（Bot ユーザー）を追加
  → allow: VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY | MANAGE_CHANNELS
- PR: `backend/app/routers/discord_auto_setup.py`
- テスト: `backend/tests/test_discord_auto_setup.py`（test_category_includes_bot_member_overwrite 追加）

**しんごさんへ必要な手動対応**：
Discord UI から "Sales Anchor" カテゴリ（重複の 4 件）を全て削除してください。
（Bot は既存カテゴリを削除できないため手動が必要）
削除後、auto-setup を再実行すると 200 completed になる予定。

---

## 次アクション（更新版）

### しんごさんへ（Discord 手動対応）

1. Discord → 対象サーバー → テキストチャンネルリスト
2. "Sales Anchor" カテゴリ（4件）をそれぞれ右クリック → チャンネルを削除
3. PR #2224 デプロイ後、`/admin/discord-config` から「自動セットアップを実行」

### Hikky-dev（対応済み）

- Cause D: Bot API で Sales Anchor ロールを pos=4 に昇格（完了）
- Cause E: `_can_upsert` guard で INSERT スキップ（PR #2215、本番反映済み）
- Cause F: カテゴリ permission_overwrites に Bot member overwrite 追加（PR #2224）
