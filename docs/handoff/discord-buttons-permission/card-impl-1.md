# 実装カード 1: リードのカルテの Discord ボタンを権限で出し分ける（段階A）

- 設計: docs/handoff/discord-buttons-permission/design.md §2（設計合格・自己審査）
- PO の承認: 2026-11-04「別途権限として付与できるようにするまず見えないように1」（選択肢 1 = まず見えないようにする）
- ブランチ: release/discord-buttons-permission（このブランチに続けてコミットする。新しいブランチを作らない）
- 基準: origin/main 7d56ab771

## やること（これ以外はしない）

`frontend/src/pages/inbox/InboxKartePanel.tsx`

1. `function KarteTabContent(` の中の `const { t } = useTranslation();` の直後に `const { hasPermission } = usePermissions();` を 1 行足す（import は既に :17 にある）。
2. `<ChannelInviteButton leadId={leadDetail.id} />` を囲む条件の先頭に `hasPermission("leads.update") &&` を足す。
3. `<DiscordRemoveButtons ... />` を囲む条件の先頭に `hasPermission("leads.delete") &&` を足す。
4. `function RoleSyncStatusRow(` の引数に `canResync` を足す（型 `canResync: boolean`）。中の再同期の `<Button ...>{t("leads.discordRoleResync")}</Button>` を `{canResync && ( ... )}` で囲む。状態の文字・結果の文字は変えない。
5. `<RoleSyncStatusRow` の呼び出しに `canResync={hasPermission("leads.update")}` を足す。

新しい試験 `frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx`

- usePermissions の差し替えは `frontend/src/features/secretary/SecretaryChat.test.tsx:35-37` の形を写す。
- 描き方: まず InboxKartePanel を描く形を試す。準備が重い（多くの API の差し替えが要る）ときに限り、`KarteTabContent` の宣言に `export` を 1 語足して直接描いてよい。
- leadDetail は discord_user_id・discord_guild_channel_id・estimated_scale="Small"・discord_role_sync_status="success" を持つ形にする。
- T1 権限なし: 招待・再同期・外す・キック・BAN の文字が無い。状態の文字（t("leads.discordRoleSyncStatus")）は在る。
- T2 leads.update だけ: 招待・再同期は在る。外す・キック・BAN は無い。
- T3 leads.update と leads.delete: 5 つとも在る。
- 文字は ja.json の既存の鍵を i18n 経由で引く（試験の中に日本語を直書きしない）。鍵の名前は InboxKartePanel.tsx の中の t("...") を読んで使う。

## 触らない

backend・migrations・DB・ja.json/en.json・CSS・components/ の部品・ChannelInviteButton と DiscordRemoveButtons の中身・ほかの出し分け。

## 点検（全部の生出力をファイルに残す）

- `cd frontend && npx vitest run src/pages/inbox/InboxKartePanel.discordButtons.test.tsx`
- `cd frontend && npx tsc --noEmit -p .`
- `cd frontend && npx eslint src/pages/inbox/InboxKartePanel.tsx src/pages/inbox/InboxKartePanel.discordButtons.test.tsx`
- `git diff origin/main...HEAD --name-only` が、docs/handoff/discord-buttons-permission/ と上の 2 ファイルだけ。

## 想定分岐

- InboxKartePanel を描くのに 10 個を超える API の差し替えが要る → KarteTabContent に export を足す方へ切り替える（カード内で許可済み）。
- 鍵の文字列が ja.json に見つからない、または型の誤りがカードの外の変更を要する → 止めて `NEEDS_DECISION:` で報告する。
- 既存の試験が赤になる → 直さずに止めて `BLOCKED:` で報告する。

## 報告

docs/handoff/discord-buttons-permission/impl-report-1.md に、変更の diff、点検 4 つの生出力、コミットの sha を書き、同じブランチに push する。最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <内容>` のどれか。
