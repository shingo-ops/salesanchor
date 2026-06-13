# design: Discord Bot招待後サーバー初期構築ウィザード

**日付**: 2026-06-14  
**ブランチ**: `feature/morimoto/discord-auto-setup-design`  
**recon参照**: `docs/handoff/discord-auto-setup/recon.md`  
**ADR参照**: ADR-091（対象外→本機能で拡張）/ ADR-009 / ADR-072

---

## 外部・過去事例参照

| 事例 | 参考内容 | 我々への応用 |
|------|---------|------------|
| MEE6 / Carl-bot (ADR-091記載) | Bot招待時に `scope=bot applications.commands` + `response_type=code` で guild_id取得 | 既に採用済み。自動セットアップはこのフローの直後に発火させる |
| Typeform Bot / Zapier Discord App | Bot招待後に「チャンネルを選択またはBot側で作成」というウィザードUI | Sales Anchor版: 「自動セットアップ実行」1ボタンで全作成し、後から手動調整可能にする |
| Discord Developer Portal の `/guilds/{id}/channels` ガイド | `type=4`でカテゴリ、`type=0`でテキストチャンネル | 小規模な新規REST呼び出し3本で実現可能 |

---

## 1. Bot招待後の画面遷移（設計）

```
[既存] POST /discord/oauth/start
  ↓ Discord OAuth2 招待
[既存] GET /discord/oauth/callback → guild_id 保存
  ↓ リダイレクト
[既存] /channels?discord_status=connected
  ↓ バナー「Bot接続完了」表示
[新規] バナー内または接続カードに「Discordサーバーを初期セットアップ」ボタン
  ↓ ボタン押下
[新規] POST /api/v1/admin/discord/auto-setup
  ↓ ステップごとに結果返却
[新規] 完了画面: 作成したチャンネル/ロール一覧 + Botロール順ガイドへのリンク
```

### UI配置方針

- **ボタン配置**: DiscordConfigPage (`/admin/discord-config`) の guild_id カード下部
- **理由**: `/channels?discord_status=connected` はリダイレクト先でありバナーのみの責務。恒久的な設定ボタンは DiscordConfigPage に置くべき
- **接続前は無効**: `guild_id` 未設定時はボタンを disabled 表示
- **2回目以降**: 「再セットアップ（上書き）」として同じボタンを使用。冪等動作

---

## 2. 自動セットアップで作成するDiscordオブジェクト

### 作成順序（依存関係順）

```
Step 1: ロール作成
  1a. Sales Anchor Staff ロール
  1b. Partner ロール（large_role_name の値）
  1c. Member ロール（small_role_name の値）

Step 2: カテゴリ作成
  2a. "Sales Anchor" カテゴリ（@everyone: view_channel=False）

Step 3: チャンネル作成（カテゴリ配下）
  3a. "ticket-start" テキストチャンネル（全員閲覧可）
  3b. "member-announcements" テキストチャンネル（Member以上が閲覧可）
  3c. "partner-announcements" テキストチャンネル（Partner以上が閲覧可）

Step 4: チケットボタン投稿
  4a. ticket-start チャンネルに「チケットを開く」ボタン投稿
```

### 作成オブジェクト詳細

| # | オブジェクト | Discordでの名前 | 権限設定 | 保存先 |
|---|------------|--------------|---------|--------|
| 1a | ロール | Sales Anchor Staff | Bot自動付与用（管理側） | `tenant_discord_ticket_config.staff_role_id` |
| 1b | ロール | `large_role_name`（デフォルト: Partner） | Bot自動付与（Large顧客） | ロール名で照合（IDは不保存） |
| 1c | ロール | `small_role_name`（デフォルト: Member） | Bot自動付与（Small顧客） | ロール名で照合（IDは不保存） |
| 2a | カテゴリ | Sales Anchor | @everyone view禁止 | `tenant_discord_ticket_config.ticket_category_id` |
| 3a | テキストCh | ticket-start | @everyone view可、Staff role送信可 | `tenant_discord_ticket_config.ticket_button_channel_id` |
| 3b | テキストCh | member-announcements | Member以上 view/read可、Staff送信可 | `tenant_discord_ticket_config.small_channel_id` |
| 3c | テキストCh | partner-announcements | Partner以上 view/read可、Staff送信可 | `tenant_discord_ticket_config.large_channel_id` |
| 4a | ボタンメッセージ | "チケットを開く" | — | audit_log のみ |

> **注**: Member/Partner ロールのIDはDBに保存しない。`discord_role_sync.py` が名前で照合する既存設計（`_get_or_create_role()`）を維持する。

---

## 3. 作成済みの場合の冪等動作

```python
# 擬似コード
if tenant_discord_ticket_config.ticket_category_id is not None:
    # Discord APIで実在確認
    category = await get_channel(ticket_category_id)
    if category exists and category.type == CATEGORY:
        skip creation  # 冪等
    else:
        re-create  # Discord側で削除された場合
```

| ケース | 動作 |
|--------|------|
| 設定IDがあり、Discordにも存在する | スキップ（ID変更なし） |
| 設定IDがあるが、Discordに存在しない | 再作成 → ID上書き保存 |
| 設定IDがない | 新規作成 → ID保存 |
| ロール（名前ベース）が存在する | スキップ（`_get_or_create_role`と同一） |
| ロール名が存在しない | 新規作成 |

---

## 4. 作成したIDの保存先

### 書き込みテーブル（既存、migration不要）

```
public.tenant_discord_ticket_config
  ticket_category_id       ← 2a カテゴリID
  ticket_button_channel_id ← 3a ticket-start チャンネルID
  staff_role_id            ← 1a Sales Anchor Staff ロールID
  small_channel_id         ← 3b member-announcements チャンネルID
  large_channel_id         ← 3c partner-announcements チャンネルID
```

> **Migration不要の根拠**: recon.md §3参照。既存5列に過不足なし。

---

## 5. 新規APIエンドポイント設計

### `POST /api/v1/admin/discord/auto-setup`

**権限**: `tenant.profile.edit`  
**認証**: JWT必須（channels.manage が適切だが既存権限体系に合わせて profile.edit）

**Request**: なし（tenant_id はJWTから）

**Response**:
```json
{
  "status": "completed",  // or "partial" or "failed"
  "steps": [
    { "step": "role_staff",   "status": "created", "discord_id": "123..." },
    { "step": "role_partner", "status": "skipped" },
    { "step": "role_member",  "status": "created", "discord_id": "456..." },
    { "step": "category",     "status": "created", "discord_id": "789..." },
    { "step": "ch_ticket",    "status": "created", "discord_id": "012..." },
    { "step": "ch_member",    "status": "created", "discord_id": "345..." },
    { "step": "ch_partner",   "status": "created", "discord_id": "678..." },
    { "step": "button",       "status": "posted",  "discord_id": "901..." }
  ],
  "role_order_guide_url": "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/discord-role-order-guide.md"
}
```

**エラー時** (Bot権限不足など):
```json
{
  "status": "partial",
  "steps": [
    { "step": "role_staff", "status": "failed", "error": "Missing Permissions" },
    ...
  ],
  "error_hint": "Bot ロールの権限を確認してください"
}
```

**実装ファイル（新規）**: `backend/app/routers/discord_auto_setup.py`

**内部実装方針**:
1. `public.tenant_discord_config` から `guild_id` を取得
2. `DISCORD_BOT_TOKEN_{tenant_id}` からBotトークン取得
3. `discord_rest.discord_api_request()` を使ってロール・カテゴリ・チャンネルを順番に作成
4. 各ステップの結果を `tenant_discord_ticket_config` に upsert（ADR-072: commit後 `reset_tenant_context`）
5. ステップ結果を全件返す

---

## 6. Bot権限不足時のエラー表示

| HTTPステータス | Discord APIエラー | 表示 |
|--------------|----------------|------|
| 403 Missing Permissions | MANAGE_CHANNELS | 「Botにチャンネル管理権限がありません。Discordのサーバー設定でBotロールを確認してください。」 |
| 403 Missing Permissions | MANAGE_ROLES | 「Botにロール管理権限がありません。Discordのサーバー設定でBotロールを確認してください。」 |
| 403 Missing Permissions | 原因不明 | 「Bot権限が不足しています。Botを一度サーバーから削除して再招待してください。」 |
| 404 Unknown Guild | guild_id が古い | 「Discordサーバーが見つかりません。再接続してください。」 |
| 429 Rate Limit | — | `discord_rest.py` が自動リトライ。最大5回後にエラー |

**UI表示**: 各ステップのカードにエラーを表示し、「再試行」ボタンを表示する。

---

## 7. Botロール順ガイドへの導線

自動セットアップ完了後、UIに以下を表示:

```
✅ セットアップ完了
次のステップ: Sales Anchor Bot ロールを Partner / Member より上に移動してください。

[ロール順設定ガイドを見る → ]
```

- リンク先: `docs/runbooks/discord-role-order-guide.md` のGitHub URL
- 設計上: APIレスポンスの `role_order_guide_url` フィールドとして返す（UI側が `t()` を使って表示）
- i18nキー: `discordAutoSetup.roleOrderGuidePrompt`, `discordAutoSetup.roleOrderGuideLink`

---

## 8. 失敗時のリトライ導線

- **部分失敗**（一部ステップが失敗）: `status: "partial"` で返す
- **UI**: 失敗したステップを赤で表示、「再試行」ボタンを表示
- **再試行**: 同じ `POST /api/v1/admin/discord/auto-setup` を再度呼ぶ（冪等のため安全）
- **全ステップ成功済み**: 「再セットアップ」ボタンを表示（2回目以降）

---

## 9. MVP対象 / 対象外

### MVP対象（本設計PRの実装スコープ）

| # | 項目 |
|---|------|
| ✅ | `POST /api/v1/admin/discord/auto-setup` エンドポイント（backend） |
| ✅ | ロール3種作成（Sales Anchor Staff / Partner / Member） |
| ✅ | カテゴリ1種作成 |
| ✅ | テキストチャンネル3種作成 |
| ✅ | チケットボタン投稿 |
| ✅ | 作成IDを `tenant_discord_ticket_config` に保存 |
| ✅ | 冪等動作（スキップまたは再作成） |
| ✅ | 完了後のBotロール順ガイドへのリンク |
| ✅ | DiscordConfigPage に「初期セットアップ」ボタン（フロント） |
| ✅ | エラー時のステップ別表示とリトライUI |

### MVP対象外

| 項目 | 理由 |
|------|------|
| カテゴリ名・チャンネル名のカスタマイズUI | 設定項目が増えすぎる。固定名で十分 |
| 音声チャンネルの作成 | ADR-009 NG3 準拠 |
| チャンネル権限の詳細カスタマイズ | 固定権限で十分（後から手動変更可能） |
| 既存チャンネルの削除・リネーム | 意図せぬ削除リスクが高い |
| Member/Partner ロールIDのDB保存 | `discord_role_sync.py` の名前ベース照合で十分 |
| `ウェルカムメッセージ` の自動設定 | 既存のデフォルト値を使う |

---

## 10. 受け入れ基準と検証方法

| 基準 | 検証方法 |
|------|---------|
| Bot招待後にセットアップボタンが表示される | Playwright: `/admin/discord-config` でボタン存在確認 |
| ボタン押下でDiscord上にカテゴリ・チャンネル・ロールが作成される | Discord API モックでstepごとの作成確認。実機: Discordサーバーで目視確認 |
| 作成IDが `tenant_discord_ticket_config` に保存される | pytest: DB検証（既存パターン準拠） |
| 2回目のセットアップが冪等 | pytest: 同一テナントに2回呼び出し、Discordオブジェクト作成回数が1回のこと |
| Bot権限不足時に503/partial レスポンス | pytest: Discord API 403モックでエラーハンドリング確認 |
| 完了後にBotロール順ガイドへのリンクが表示される | Playwright: 完了レスポンス後のUI確認 |

---

## 11. 実装 PR 構成案

| PR | 内容 |
|----|------|
| PR-A (Backend) | `backend/app/routers/discord_auto_setup.py` 新規 + `app/main.py` に登録 |
| PR-B (Frontend) | `DiscordConfigPage.tsx` に「初期セットアップ」ボタン追加 + i18nキー追加 |

> PR-AとPR-Bは独立して進められる（BackendはAPIクライアントでテスト可能、FrontendはモックAPIで開発可能）。

---

## 関連リンク

- `docs/handoff/discord-auto-setup/recon.md` — 本設計の前提コード実証
- `docs/runbooks/discord-role-order-guide.md` — Botロール順設定ガイド
- `docs/adr/ADR-091-discord-bot-scope-definition.md:172-174` — 拡張する「対象外」定義
- `backend/app/services/discord_role_sync.py:82` — `_get_or_create_role()` の実装参考
- `backend/app/discord_gateway/ticket_channel_creator.py:98` — チャンネル冪等作成の実装参考
- `backend/app/routers/discord_ticket_config.py:219` — チケットボタン投稿の実装参考
