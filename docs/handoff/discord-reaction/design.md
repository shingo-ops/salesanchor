# Discord リアクション機能 — 設計書

> この文書は、受信箱で Discord リアクションを送受信する機能の設計です。
> 親仕様書: [docs/specs/discord-reaction/README.md](../../specs/discord-reaction/README.md)
> Recon: [recon.md](recon.md)
> ADR: [ADR-009](../../adr/ADR-009-discord-gateway.md) M7, [ADR-091](../../adr/ADR-091-discord-bot-scope-definition.md)

## 目的

受信箱だけで Discord リアクションの確認・操作を完結させる（Discord を開かなくてよい状態）。

## 対象と対象外

| 対象 | 対象外 |
|------|--------|
| guild チケットチャンネルのリアクション送受信 | DM チャンネル（ADR-146 F7） |
| Unicode 絵文字 + サーバーカスタム絵文字 | 外部サーバー絵文字（Use External Emojis 未承認） |
| Bot 名義でのリアクション送信 | ユーザー名義での送信 |
| リアクション追加・取消の双方向同期 | メッセージ削除・編集の同期 |
| 既存 SSE 経路でのリアルタイム更新 | WebSocket 新設 |

## KGI（PO 承認済み 2026-09-04）

| # | 合格条件 | 検証方法 |
|---|---------|---------|
| 1 | 絵文字パレットで Unicode + カスタム絵文字を選べる | Playwright: パレット開く → 2種のタブ確認 |
| 2 | 受信箱→Discord 反映（10件） | Playwright + Discord API で検証 |
| 3 | 受信箱取消→Discord 消去（10件） | 同上 |
| 4 | 顧客 Discord→受信箱 表示（10件） | Gateway ログ + 画面確認 |
| 5 | 顧客取消→受信箱 消去（10件） | 同上 |
| 6 | 表示情報一致（絵柄/個数/自分が押したか/押した人） | 横並べスクリーンショット比較 |
| 7 | Discord 不要で完結 | 操作フロー確認 |
| 8 | 手動リロード不要 | SSE イベント受信 → 自動更新確認 |

## DB 設計（SSOT: ADR-095 準拠）

### 新規テーブル: `{schema}.meta_message_reactions`

```sql
CREATE TABLE IF NOT EXISTS {schema}.meta_message_reactions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT current_setting('app.tenant_id', true)::INTEGER,
    meta_message_id INTEGER NOT NULL REFERENCES {schema}.meta_messages(id) ON DELETE CASCADE,
    emoji_name TEXT NOT NULL,          -- Unicode: '👍', Custom: 'custom_name'
    emoji_id TEXT,                     -- Custom emoji Snowflake ID (NULL for Unicode)
    emoji_animated BOOLEAN DEFAULT FALSE,
    reactor_discord_user_id TEXT NOT NULL,
    reactor_display_name TEXT,
    is_bot_reaction BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_reaction_per_user_emoji
        UNIQUE (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id)
);

CREATE INDEX idx_mmr_meta_message_id ON {schema}.meta_message_reactions (meta_message_id);
CREATE INDEX idx_mmr_tenant ON {schema}.meta_message_reactions (tenant_id);

ALTER TABLE {schema}.meta_message_reactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY mmr_tenant_policy ON {schema}.meta_message_reactions
    USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
```

**SSOT 根拠**: 1メッセージ : Nリアクション の正規化子テーブル。meta_messages.id をFK。データ分散なし。

### 触らないテーブル

- `meta_messages` — カラム追加なし（JSONB 埋め込みは SSOT 違反）
- `lead_attachments` — 無関係
- `public.*` — tenant スキーマに閉じる

## Gateway 変更

### client.py 変更（`backend/app/discord_gateway/client.py`）

**変更1: Intent 追加（L58）**
```python
# 変更前
# intents.reactions = True  # M7: リアクション対応時に有効化

# 変更後
intents.reactions = True
```

**変更2: イベントハンドラ追加（L98 付近に新規）**
```python
async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    """Process reaction add events from guild channels."""
    if not payload.guild_id:
        return  # DM は対象外
    if payload.user_id == self.user.id:
        return  # Bot 自身のリアクションは無視（ループ防止）
    await self._process_reaction(payload, action="add")

async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
    """Process reaction remove events from guild channels."""
    if not payload.guild_id:
        return
    await self._process_reaction(payload, action="remove")

async def _process_reaction(self, payload, action: str):
    guild_id = str(payload.guild_id)
    tenant_id = await self.tenant_resolver.resolve(guild_id)
    if not tenant_id:
        return
    await self.reaction_writer.process_reaction(
        tenant_id=tenant_id,
        channel_id=str(payload.channel_id),
        message_id=str(payload.message_id),
        user_id=str(payload.user_id),
        emoji=payload.emoji,
        member=payload.member,
        action=action,
    )
```

### 新規ファイル: `backend/app/discord_gateway/reaction_writer.py`

```python
"""Write Discord reaction events to the database."""

class ReactionWriter:
    async def process_reaction(self, tenant_id, channel_id, message_id,
                                user_id, emoji, member, action):
        # 1. meta_messages から discord message_id で行を特定
        # 2. action="add" → INSERT INTO meta_message_reactions
        # 3. action="remove" → DELETE FROM meta_message_reactions
        # 4. sse_pubsub.publish_inbox_update(tenant_id) で通知
```

### client.py の setup_hook に追加

```python
self.reaction_writer = ReactionWriter(self.database_url)
await self.reaction_writer.initialize()
```

## REST API 設計

### POST `/api/v1/leads/{lead_id}/messages/{message_id}/reactions`

受信箱→Discord にリアクション送信。

```json
Request:  { "emoji_name": "👍", "emoji_id": null }
Response: { "success": true }
```

処理:
1. meta_messages から message_id で Discord message_id を取得
2. lead から discord_guild_channel_id を取得
3. `discord_rest.discord_api_request("PUT", f"/channels/{channel_id}/messages/{discord_msg_id}/reactions/{emoji}/@me", bot_token)`
4. `meta_message_reactions` に INSERT（is_bot_reaction=true）
5. `publish_inbox_update(tenant_id)`

### DELETE `/api/v1/leads/{lead_id}/messages/{message_id}/reactions/{emoji}`

受信箱からリアクション取消。

処理:
1. Discord API で `DELETE /reactions/{emoji}/@me`
2. `meta_message_reactions` から DELETE
3. `publish_inbox_update(tenant_id)`

### GET `/api/v1/discord/guilds/{guild_id}/emojis`

カスタム絵文字一覧取得（絵文字パレット用）。

処理: `discord_rest.discord_api_request("GET", f"/guilds/{guild_id}/emojis", bot_token)`

### `/leads/{lead_id}/messages` レスポンス拡張（`backend/app/routers/leads.py:952-965`）

既存の messages 取得後に reactions を別クエリで取得してマージ:

```python
# L1010 直後に追加
reaction_rows = await conn.fetch(
    f"SELECT meta_message_id, emoji_name, emoji_id, emoji_animated, "
    f"reactor_discord_user_id, reactor_display_name, is_bot_reaction "
    f"FROM {tenant_id}.meta_message_reactions "
    f"WHERE meta_message_id = ANY($1)",
    [msg["id"] for msg in messages]
)
# グループ化して各 message に reactions キーとして追加
```

## フロントエンド設計

### 金型新設

#### Popover（`frontend/src/components/Popover.tsx` + `frontend/src/components/Popover.css` + `frontend/src/components/Popover.stories.tsx`）

- トリガー要素の位置に対してフローティング表示
- `placement: 'top' | 'bottom' | 'left' | 'right'`
- 外側クリックで閉じる
- z-index: `var(--z-dropdown)`
- トークン: `--space-2` padding, `--radius-2` border-radius, `--shadow-lg` box-shadow

#### Tooltip（`frontend/src/components/Tooltip.tsx` + `frontend/src/components/Tooltip.css` + `frontend/src/components/Tooltip.stories.tsx`）

- ホバーで表示、150ms delay
- テキストのみ（HTML なし）
- z-index: `var(--z-dropdown)`
- トークン: `--color-surface-overlay` 背景, `--color-text-on-emphasis` 文字色

### InboxMessageThread.tsx 変更

**リアクション表示（L532後に挿入）:**
```tsx
{msg.reactions && msg.reactions.length > 0 && (
  <div className="msg-reaction-bar">
    {groupedReactions.map(r => (
      <Tooltip key={r.key} content={r.reactorNames.join(', ')}>
        <button
          className="msg-reaction-pill"
          data-mine={r.isMine}
          onClick={() => r.isMine ? deleteReaction(msg.message_id, r) : sendReaction(msg.message_id, r)}
        >
          {r.emoji} <span className="msg-reaction-count">{r.count}</span>
        </button>
      </Tooltip>
    ))}
    <Popover content={<EmojiPicker onSelect={emoji => sendReaction(msg.message_id, emoji)} />}>
      <button className="msg-reaction-add-btn" aria-label={t('addReaction')}>
        <SmilePlus size={16} />
      </button>
    </Popover>
  </div>
)}
```

### CSS 追加（InboxPage.css:622後）

```css
.msg-reaction-bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-1);
}
.msg-reaction-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border-secondary);
  background: var(--color-surface-secondary);
  font-size: var(--font-2xs);
  cursor: pointer;
  transition: var(--transition-fast);
}
.msg-reaction-pill[data-mine="true"] {
  border-color: var(--color-border-brand);
  background: var(--color-surface-brand-subtle);
}
.msg-reaction-pill:hover {
  background: var(--color-surface-hover);
}
.msg-reaction-count {
  font-size: var(--font-2xs);
  color: var(--color-text-secondary);
}
.msg-reaction-add-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--size-icon-btn-sm);
  height: var(--comp-badge-height-sm);
  border-radius: var(--radius-full);
  border: 1px dashed var(--color-border-secondary);
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: var(--transition-fast);
}
.msg-reaction-add-btn:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
}
```

### i18n キー追加

```json
{
  "addReaction": "リアクションを追加",
  "removeReaction": "リアクションを取り消す",
  "reactedBy": "リアクションした人",
  "emojiPicker": "絵文字を選択",
  "customEmojis": "サーバー絵文字",
  "reactionSendFailed": "リアクションの送信に失敗しました",
  "reactionDeleteFailed": "リアクションの取り消しに失敗しました"
}
```

### 絵文字ピッカー

ライブラリ: `emoji-picker-react@4.22.2`
- `React.lazy()` で動的 import（初期バンドルに含めない）
- `customEmojis` prop に `GET /discord/guilds/{guild_id}/emojis` の結果をマッピング
- ラッパーコンポーネント: `frontend/src/pages/inbox/EmojiPickerWrapper.tsx`

## 外部・過去事例の参照と我々への応用

Discord リアクション同期は Slack/Discord ブリッジツール（例: Zapier, IFTTT）で一般的に実現される機能であり、技術的に枯れたパターン。Sales Anchor の要件は CRM 受信箱への統合であり、ブリッジツールでは不十分（CRM データとの紐付けが必要）。discord.py の公式ドキュメントとサンプルコードに `on_raw_reaction_add` の使用例が掲載されており、実装パターンは確立済み。独自の外部事例調査は不要と判断（理由: 枯れた API の標準的な使用であり、アーキテクチャ上の新規判断を伴わないため）。

## 受入条件と検証方法

| # | 基準 | 検証方法 | 担当 |
|---|------|---------|------|
| AC-1 | migration が全 tenant スキーマに適用される | `BEGIN; migration; SELECT COUNT(*) FROM meta_message_reactions; ROLLBACK;` | CI |
| AC-2 | Gateway が REACTION_ADD を受信し DB に保存する | 開発環境で Discord リアクション → DB 確認 | Evaluator |
| AC-3 | Gateway が REACTION_REMOVE を受信し DB から削除する | 同上 | Evaluator |
| AC-4 | REST API でリアクション送信→Discord 反映 | curl + Discord 目視 | Evaluator |
| AC-5 | REST API でリアクション取消→Discord 消去 | 同上 | Evaluator |
| AC-6 | フロントにリアクション表示（絵柄/個数/押した人） | Playwright スクリーンショット | Evaluator |
| AC-7 | 絵文字パレットで Unicode + カスタム選択可 | Playwright 操作 | Evaluator |
| AC-8 | SSE でリアルタイム更新（リロード不要） | Playwright: リアクション追加後に自動表示確認 | Evaluator |
| AC-9 | i18n: ja/en 全キー存在 | ESLint i18n チェック | CI |
| AC-10 | Popover/Tooltip が components/ に金型登録済み | ファイル存在確認 | CI |

## 維持の仕組み

- 守り手: `backend/app/discord_gateway/client.py` の `intents.reactions = True`（無効化されるとリアクション受信が停止）
- 守り手: `frontend/scripts/check-i18n-keys.js`（i18n キーの ja/en 同一性）
- 守り手: `.github/workflows/test.yml`（migration 適用チェック・ESLint・型チェック）
- 対象: リアクション送受信の双方向同期が壊れると、受信箱で Discord リアクションが見えなくなる
- 関所なしの項目: Discord Developer Portal の `Add Reactions` チェック状態は CI で検査不可（人手で守る。理由: リポジトリ外の設定）
