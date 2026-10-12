# Discord リアクション配線修正 — recon（現在地）

> 実測時の origin/main: 34abf56e883a5fd84daaec51d90f1fa36851f20e（fetch 後・全 file:line は同 SHA の git show による。設計時の 6144412fd との差分は対象ファイルで 0）
> 承認済みKGI: docs/specs/discord-reaction/kgi.md（⑥ 受信箱に出る情報がDiscordと同じか: 絵柄／個数／自分が押したか／押した人の名前 = 4/4、kgi.md:17）

## 事実

1. ID 不一致。フロントは Discord snowflake `msg.message_id` を渡している。
   - frontend/src/pages/inbox/InboxMessageThread.tsx:608（ピル）、:658・:694（ピッカー）で `msg.message_id!` を渡す。
   - frontend/src/pages/inbox/useInboxState.ts:391,401 は `messageId: string`。パスは :398 付近の `/leads/${selectedLeadId}/messages/${encodeURIComponent(messageId)}/reactions`。
   - backend/app/routers/discord_reactions.py:130,223 は `message_id: int`、:100-103 の `_get_discord_message_id` は meta_messages.id → Discord message_id を引く。
   - backend/app/routers/leads.py:990 は内部ID `"id": r["id"]` を返し済み。frontend/src/lib/messages.ts:59 は `id: number`。
2. 存在しない列。backend/app/routers/discord_reactions.py:187 が `bot.discord_bot_user_id` を参照するが、`git grep -n discord_bot_user_id origin/main -- migrations backend/app` のヒットは同行のみ。migrations/099_add_discord_guild_config.sql:6-12 の `tenant_discord_config` に該当列なし。
3. 返却形の不一致。
   - backend/app/routers/leads.py:1046 で `reactors` に表示名の文字列だけを積み、:1049 で `is_bot_reaction` を返している。`is_mine` は無い。
   - frontend/src/lib/messages.ts:54-55 は `is_mine: boolean` と `reactors: MessageReactor[]`（`{user_id, display_name}`）を要求する。
4. カスタム絵文字の取消。frontend/src/pages/inbox/useInboxState.ts:403-405 が `name:id` を1つのパス部分にしている。backend/app/routers/discord_reactions.py の DELETE は `emoji` パス部分と `emoji_id` クエリ（`emoji_id: Optional[str] = None`）。
5. エラー握りつぶし。frontend/src/pages/inbox/InboxMessageThread.tsx:212,224 の catch がコメントのみ。i18n キーは frontend/src/locales/ja.json:1333-1334 に既存（en.json も同行）で、使用箇所なし。
6. DB の書き手が2つ。
   - REST: backend/app/routers/discord_reactions.py:182（挿入）・:199（commit）・:305（commit、取消側）。
   - Gateway: backend/app/discord_gateway/reaction_writer.py:130（`is_bot_reaction` が固定 false）。
   - Gateway は Bot 自身の add を無視する（backend/app/discord_gateway/client.py:237-238）。remove は無視しない。
7. UNIQUE 制約 `uq_reaction_per_user_emoji` は (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id)（migrations/20260927_100000_create_meta_message_reactions.sql:57-58）。emoji_id が NULL の Unicode 絵文字では NULL が区別されるため重複防止が効かない（PostgreSQL の仕様）。書き手が2つだと重複行のリスクがある。
8. SSE。backend/app/discord_gateway/reaction_writer.py:192 が書込後に `publish_inbox_update`。フロントは frontend/src/pages/inbox/useInboxState.ts:469（`useInboxSSE`）から :491 で `loadMessages` を再取得する。
9. 共通金型 Toast。frontend/src/components/loading/Toast.tsx:32 に `toast.error`。`<Toaster />` は frontend/src/App.tsx:159 にマウント済み。利用例: frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx:17（import）,198（`toast.error(t(...))`）。
10. Gateway の intent は reactions が有効（backend/app/discord_gateway/client.py:67）。
11. リアクション関連の既存テスト: 0 件（`ls backend/tests | grep -i react` に該当なし）。テストの型: backend/tests/test_discord_inbox.py:298（`patch("...httpx.AsyncClient")`）。

## ADR 検索（着手前）

```
$ git grep -il reaction origin/main -- docs/adr/
origin/main:docs/adr/ADR-024_meta_integration_structural_fix.md
origin/main:docs/adr/ADR-091-discord-bot-scope-definition.md
$ git grep -n -i reaction origin/main -- docs/adr/FEATURE-INDEX.md
（ヒット 0 件）
```

- 対象 ADR: ADR-091（docs/adr/ADR-091-discord-bot-scope-definition.md。Add Reactions を「将来機能として許容」に分類し、実装済みと記載）。ADR-024 は Meta 連携の構造修正で本件と無関係。
- 既存の関連文書: docs/specs/discord-reaction/{README,ideal-state,kgi}.md（承認済み）、docs/handoff/discord-reaction-fix/{recon,design}.md（2026-09-27・絵文字ピッカーの CDN 表示修正。本便とは別件）。
