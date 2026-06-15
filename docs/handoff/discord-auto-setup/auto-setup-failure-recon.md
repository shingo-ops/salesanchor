# recon: Discord 自動セットアップ失敗の原因調査

**日付**: 2026-06-14  
**担当**: Hikky-dev  
**ステータス**: VPS実機確認完了・原因確定

---

## 症状

- `/admin/discord-config` の「自動セットアップを実行」ボタンを押すと「自動セットアップに失敗しました。」と表示される
- エラーは `DiscordConfigPage.tsx:222-224` の catch ブロック → `t("discordAutoSetup.requestFailed")`
- `POST /api/v1/admin/discord/auto-setup` が 500 を返している

---

## VPS 実機確認結果（2026-06-14）

| 確認項目 | 結果 |
|---------|------|
| 実行日時 | 2026-06-14 |
| backend container 名 | `astro-webapp-backend-1` |
| DISCORD_BOT_TOKEN_4 | **set**（注入済み） |
| Discord roles GET | ✅ 成功（502 なし） |
| Discord channels GET | ✅ 成功（502 なし） |
| Discord channel POST (ch_ticket) | ❌ HTTP 403 code=50013 Missing Permissions |
| Discord channel POST (ch_member) | ❌ HTTP 403 code=50013 Missing Permissions |
| Discord channel POST (ch_partner) | ❌ HTTP 403 code=50013 Missing Permissions |
| DB: `tenant_discord_config`.guild_id (tenant_id=4) | ✅ `1515681337158271187` |
| DB: `tenant_discord_ticket_config` (tenant_id=4) | ❌ 0 行（初回実行・未保存） |
| 最終 HTTP ステータス | **500 Internal Server Error** |

### バックエンドログ（要約）

```
[discord_auto_setup] channel creation failed step=ch_ticket name=ticket-start:
  Discord API エラー: HTTP 403: {"message": "Missing Permissions", "code": 50013}

[discord_auto_setup] channel creation failed step=ch_member name=member-announcements:
  Discord API エラー: HTTP 403: {"message": "Missing Permissions", "code": 50013}

[discord_auto_setup] channel creation failed step=ch_partner name=partner-announcements:
  Discord API エラー: HTTP 403: {"message": "Missing Permissions", "code": 50013}

Database error: POST /api/v1/admin/discord/auto-setup
  - NotNullViolationError: null value in column "ticket_button_channel_id"
    violates not-null constraint

INFO: "POST /api/v1/admin/discord/auto-setup HTTP/1.1" 500 Internal Server Error
```

---

## 原因分類

### Cause D（Discord 権限・ロール順問題）

**確定**：Bot が MANAGE_CHANNELS 権限を有効に行使できない状態。

- トークンは有効（roles/channels の GET は成功）
- チャンネル作成 POST で 403 code=50013 "Missing Permissions"
- 権限ビットマスク `268504082` には MANAGE_CHANNELS(16) が含まれているが、
  Discord のロール階層上 Bot ロールが Member/Partner より**下**にあると MANAGE_CHANNELS は機能しない

**Discord 側で必要な対応**:
- Discord サーバー設定 → 役職 → "Sales Anchor Bot" ロールを Member/Partner の**上**に移動

### Cause E（backend 実装バグ）

**確定**：チャンネル作成が全失敗（初回実行 = DB に既存行なし）の場合、
DB INSERT 時に `ticket_button_channel_id NOT NULL` 制約違反が起き 500 になる。

- `discord_auto_setup.py:295-324` の UPSERT は ON CONFLICT COALESCE で UPDATE は安全だが
  初回 INSERT 時に `ticket_ch_id=None` が渡ると NOT NULL 制約に違反する
- migration `20260602_120000_add_discord_ticket_config.sql` の
  `ticket_button_channel_id VARCHAR(32) NOT NULL` が原因

**修正方針**（migration 不要・コードのみ）:
- INSERT 前に「既存行が存在しない かつ NOT NULL カラムが NULL」の場合は INSERT をスキップ
- 部分成功（ロール作成のみ完了等）を 500 でなく正常な `partial` ステータスで返す

---

## コード解析結果（参考）

### エンドポイント存在確認

| 確認項目 | 結果 |
|---------|------|
| `backend/app/routers/discord_auto_setup.py` が main に存在 | ✅ PR #2155 (commit `5b1499f1`) |
| `backend/app/main.py` への router 登録 | ✅ `discord_auto_setup.router, prefix="/api/v1"` |
| フロントエンド UI (`DiscordConfigPage.tsx`) | ✅ PR #2163 (commit `e6ed661b`) |
| migration 登録 (`run_all_migrations.sh:187`) | ✅ |

### 権限ビットマスク確認（`discord_oauth.py:47` = `268504082`）

| 権限 | 値 | 含まれるか |
|-----|---|-----------|
| MANAGE_ROLES | 268435456 | ✅ |
| MANAGE_CHANNELS | 16 | ✅（ビット上は正しい） |
| SEND_MESSAGES | 2048 | ✅ |
| VIEW_CHANNEL | 1024 | ✅ |
| READ_MESSAGE_HISTORY | 65536 | ✅ |

→ 権限ビット自体は正しい。Discord ロール順の問題で有効に機能していない。

---

## 次アクション

### しんごさんへ（Discord 設定・即時対応）

Discord の「サーバー設定 → 役職」を開き:
- "Sales Anchor Bot" ロールを "Member"（`small_role_name`）と "Partner"（`large_role_name`）の**上**に移動

移動後、もう一度「自動セットアップを実行」を試す。

### Hikky-dev（コード修正 PR）

- **対象ファイル**: `backend/app/routers/discord_auto_setup.py:295-324`
- **修正内容**: 初回実行（`cfg is None`）かつ NOT NULL カラムが None のとき INSERT をスキップし `partial` で正常返却
- **テスト**: `backend/tests/test_discord_auto_setup.py` — 「初回・全チャンネル失敗時に 500 でなく 200 partial を返す」ケースを追加
- **migration 変更なし**（NOT NULL は残す）

→ Cause D（Discord 設定）が解消されれば Cause E の INSERT 問題は踏まなくなるが、
  Cause E を放置すると他テナント初回実行でも 500 になるため別途修正する。
