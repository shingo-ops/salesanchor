# Discord リアクション機能 — Recon（現在地把握）

> この文書は、Discord リアクション送受信機能の実装前調査結果です。
> 親仕様書: [docs/specs/discord-reaction/README.md](../../specs/discord-reaction/README.md)

## 既存 ADR 検索結果

| キーワード | 検索コマンド | 該当 ADR |
|-----------|-------------|----------|
| discord | `git grep -i "discord" docs/adr/` | ADR-009（Gateway Worker）, ADR-091（Bot Scope） |
| reaction | `git grep -i "reaction" docs/adr/` | ADR-091:68「将来機能として許容」 |
| meta_messages | `git grep -i "meta_messages" docs/adr/` | ADR-026（message_id TEXT化）, ADR-095（SSOT） |
| emoji | `git grep -i "emoji" docs/adr/` | 該当なし |

## 1. Gateway 実装の現在地

### Intents（`backend/app/discord_gateway/client.py:54`）

```python
intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True
# intents.reactions = True  # M7: リアクション対応時に有効化
```

【事実】`reactions` intent は未設定。コメントで M7 有効化予定が記載済み。

### イベントハンドラ一覧（`backend/app/discord_gateway/client.py`）

| ハンドラ | 行 | 処理 |
|---------|-----|------|
| `on_ready` | L67 | ログのみ |
| `on_resumed` | L74 | no-op |
| `on_disconnect` | L77 | 警告ログ |
| `on_message` | L80 | guild メッセージ → `_process_guild_message` |
| `on_interaction` | L100 | `ticket_open` ボタン |

【事実】`on_raw_reaction_add` / `on_raw_reaction_remove` は存在しない。

### メッセージ処理フロー（`backend/app/discord_gateway/client.py:85`）

```
on_message → bot自身を除外 → DM除外（ADR-146）
→ _process_guild_message → tenant_resolver.resolve(guild_id)
→ ticket channel 判定 → ticket_channel_writer.process_ticket_channel_message()
```

### ticket_channel_writer.py の保存フロー

- `_find_lead_by_ticket_channel()`: `discord_guild_channel_id` → `lead_id` 解決
- `_store_message()`: `meta_messages` に INSERT（`ON CONFLICT (message_id) DO NOTHING`）
- `_save_attachment_to_disk()`: Discord CDN → `/data/attachments/` ダウンロード

## 2. DB構造

### meta_messages テーブル（tenant_NNN スキーマ、RLS有効）

主要カラム（migration 012〜20260622_010000 積み上げ）:

| カラム | 型 | 用途 |
|--------|-----|------|
| id | SERIAL PK | 行ID |
| tenant_id | INTEGER | テナントID |
| lead_id | INTEGER | リードFK |
| platform | VARCHAR(20) | 'discord' / 'line' / 'messenger' |
| message_id | TEXT | **Discord Snowflake ID 格納先**（UNIQUE部分インデックス） |
| sender_id | VARCHAR(100) | Discord user ID |
| sender_name | VARCHAR(200) | 表示名 |
| message_text | TEXT | 本文 |
| direction | VARCHAR(10) | 'inbound' / 'outbound' |
| created_at | TIMESTAMPTZ | 作成日時 |

【事実】`message_id` カラムに Discord message_id が格納済み。`idx_meta_messages_message_id_unique` で高速検索可能。
【事実】リアクション用カラム・テーブルは存在しない（`grep "reaction" migrations/*.sql` = 0件）。

### SSOT方針（ADR-095）

「同じ事実の保管庫は常に1か所」。meta_messages を SSOT の会話ログマスタとして育てる方針（migration 20260622_010000）。
リアクションは 1メッセージ : N リアクション の関係 → 正規化子テーブル `meta_message_reactions` が SSOT 準拠。

## 3. リアルタイム更新経路

【事実】SSE が本番稼働中:

```
Gateway イベント → DB 保存 → sse_pubsub.publish_inbox_update(tenant_id)
→ Redis DB3 "inbox:{tenant_id}" → /api/v1/conversations/stream
→ useInboxSSE → loadMessages() 即時実行
```

- ハートビート: 30秒（`backend/app/routers/meta_inbox.py:1061`）
- 再接続: 指数バックオフ 2秒〜5分（`frontend/src/hooks/useInboxSSE.ts`）
- 通知ペイロード: `event: update, data: {}`（変更合図のみ、デルタなし）

【事実】リアクション保存後に `publish_inbox_update()` を呼べば、既存経路でフロント自動更新。インフラ追加不要。

## 4. フロントエンド挿入点

### InboxMessageThread.tsx メッセージバブル構造

```
L455: <div className="inbox-msg-row outbound|inbound">
L456:   <div className="msg-bubble">
          L465-469: message_tag
          L470-473: error
          L475-513: 添付画像 or テキスト本文
          L516-531: 翻訳結果
          ← ★ リアクション表示挿入点（L532後、L533前）
L533:     <div className="msg-time">
            L534: タイムスタンプ
            L536-547: msg-translate-btn
            ← ★ リアクション追加ボタン挿入点（L547後）
L548:     </div>
L549:   </div>
L550: </div>
```

### CSS クラス構造（InboxPage.css）

| クラス | 行 | 用途 |
|--------|-----|------|
| `.inbox-messages` | L521 | リストコンテナ |
| `.msg-bubble` | L535 | バブル本体（max-width 70%） |
| `.msg-time` | L561 | タイムスタンプ |
| `.msg-translate-btn` | L570 | 翻訳ボタン |

リアクション CSS 追加位置: `InboxPage.css:622`（`.msg-translate-btn` ブロック末尾直後）

### useInboxState.ts

- `loadMessages()`: L318-347 — `getMessages(leadId)` → `setMessagesData(data)`
- `submitSend()`: L616-658
- リアクション送信関数: L658直後に `submitReaction` useCallback 追加
- Return型: L127 に `sendReaction` / `deleteReaction` 追記

### Message 型（frontend/src/lib/messages.ts）

L63 `attachment_type` フィールド直後に `reactions` フィールド追加

### バックエンド `/leads/{lead_id}/messages`（leads.py:906-1064）

- SELECT クエリ: L952-965 に reactions JOIN 追加
- レスポンス構築: L988-1010 の messages リスト内に reactions 含める

## 5. デザインシステム・金型

### 既存金型（使用可）

| 金型 | ファイル | 用途 |
|------|---------|------|
| `Button` | `frontend/src/components/Button.tsx` | iconOnly prop でリアクション追加ボタン |
| `Badge` | `frontend/src/components/Badge.tsx` | リアクションカウント表示 |
| `HeaderButton` | `frontend/src/components/HeaderButton.tsx` | variant="icon" |

### 新設必要（PO許可済み 2026-09-27）

| 金型 | 用途 |
|------|------|
| `Popover` | 絵文字パレット表示 |
| `Tooltip` | リアクションホバー時の「誰が押したか」表示 |

### デザイントークン（tokens.css）

- `--size-icon-btn-sm: 28px` — リアクション追加ボタンサイズ
- `--comp-badge-radius: var(--radius-full)` — ピル型バッジ
- `--comp-badge-height-sm: 20px` — リアクションピル高さ
- `--z-dropdown: 50` — ポップオーバー z-index
- `--transition-fast: 150ms ease` — ホバートランジション

## 6. 絵文字ピッカーライブラリ

| 候補 | サイズ(gzip) | カスタム絵文字 | メンテ | 推奨 |
|------|-------------|--------------|--------|------|
| emoji-picker-react@4.22.2 | 73KB | `customEmojis` prop 正式対応 | 2026-09 活発 | **推奨** |
| emoji-mart@5.6.0 | 38KB+88KB data | `custom` prop 対応 | 2024-04 停滞 | — |
| frimousse@0.4.0 | 9.6KB | 間接的のみ（自前構築要） | 2026-09 活発 | — |

推奨: `emoji-picker-react@4.22.2`（カスタム絵文字API最直接・型定義整備・活発メンテ）

## 7. discord.py 2.4.0 リアクション API（Context7 MCP 確認済み）

| 機能 | API | 備考 |
|------|-----|------|
| 受信 | `on_raw_reaction_add(payload)` | キャッシュ非依存、`RawReactionActionEvent` |
| 受信取消 | `on_raw_reaction_remove(payload)` | 同上 |
| Intent | `intents.reactions = True` | 非Privileged（Portal設定不要） |
| 送信 | `PUT /channels/{id}/messages/{id}/reactions/{emoji}/@me` | 204 No Content |
| 取消 | `DELETE /channels/{id}/messages/{id}/reactions/{emoji}/@me` | 204 No Content |
| 絵文字一覧 | `GET /guilds/{id}/emojis` | カスタム絵文字取得 |

## 未確認事項

| # | 項目 | 確認方法 |
|---|------|---------|
| 1 | Developer Portal の Add Reactions チェック状態 | PO がブラウザで確認（リポジトリ外） |
