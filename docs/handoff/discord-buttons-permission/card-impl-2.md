# 実装カード 2: Discord の 5 つの操作を別々の権限の鍵に付け替える（段階B のコード）

- 設計: docs/handoff/discord-buttons-permission/design.md §3（設計合格・自己審査）
- PO の承認: 2026-11-04 チャット「3」（5 つに分ける）
- ブランチ: release/discord-permission-keys（このブランチに続けてコミットする。新しいブランチを作らない）
- 基準: origin/main 89d3320ed
- **合流の条件**: data-change-1 の本実行と事後確認（README「実行結果」）が合格してから main へ合流する。PR は先に作ってよいが、それまでは合流しない。

## 新しい鍵（この 5 つ以外の名前を作らない）

| 鍵 | ボタン・道 |
|---|---|
| leads.discord_invite | チャンネル招待・POST /discord/channel-invite/{lead_id} |
| leads.discord_resync | ロール再同期・POST /discord/sync-role/{lead_id} |
| leads.discord_remove_channel | チャンネルから外す・POST /discord/remove-from-channel/{lead_id} |
| leads.discord_kick | Kick・POST /discord/kick/{lead_id} |
| leads.discord_ban | BAN・POST /discord/ban/{lead_id} |

## やること（これ以外はしない）

### サーバー

1. `backend/app/routers/discord_channel_invite.py:63` `require_permission("leads.update")` → `require_permission("leads.discord_invite")`
2. `backend/app/routers/discord_role_resync.py:43` `require_permission("leads.update")` → `require_permission("leads.discord_resync")`
3. `backend/app/routers/discord_remove.py:80`（remove-from-channel）`"leads.delete"` → `"leads.discord_remove_channel"`
4. `backend/app/routers/discord_remove.py:143`（kick）`"leads.delete"` → `"leads.discord_kick"`
5. `backend/app/routers/discord_remove.py:193`（ban）`"leads.delete"` → `"leads.discord_ban"`
6. `backend/app/services/tenant.py` の DEFAULT_ROLES
   - 「マネージャー」の permissions（:77 の leads の行）の後ろに、5 つの鍵を足す。
   - 「営業」の permissions（:107 の leads の行）の後ろに、`"leads.discord_invite", "leads.discord_resync"` の 2 つを足す。
   - ほかの役割には足さない。

### サーバーの試験

7. `backend/tests/conftest.py` の ALL_TEST_PERMISSIONS の `"leads.view", ... "leads.convert",` の行の次に、5 つの鍵を 1 行で足す。
8. `backend/tests/test_permission_catalog.py`
   - `_REASSIGNED_ROUTES` から discord の 2 行（channel-invite・sync-role）を消す。ほかの 2 行は残す。
   - 新しい一覧 `_DISCORD_ROUTES`（上の表の 5 本。パスは `/api/v1/discord/...`）と、試験 `test_discord_routes_require_own_keys`（C6）を足す。中身は `test_reassigned_routes_require_catalog_keys` と同じ確かめ方（道が 1 本だけ見つかり、鍵の集合が `[{key}]`）。
9. `backend/tests/test_system_roles.py` の TestDefaultRoles に `test_discord_keys_in_default_roles` を足す。
   - マネージャーは 5 つとも持つ。
   - 営業は invite・resync を持ち、remove_channel・kick・ban を持たない。
   - CS・仕入れ・発送は 5 つとも持たない。

### 画面 `frontend/src/pages/inbox/InboxKartePanel.tsx`

10. :533 `hasPermission("leads.update")` → `hasPermission("leads.discord_invite")`
11. :538-540 の DiscordRemoveButtons の条件と呼び出しを次の形にする。
    - 前: `{hasPermission("leads.delete") && leadDetail.discord_user_id && (<DiscordRemoveButtons leadId={leadDetail.id} hasChannel={!!leadDetail.discord_guild_channel_id} />)}`
    - 後: `{leadDetail.discord_user_id && (hasPermission("leads.discord_remove_channel") || hasPermission("leads.discord_kick") || hasPermission("leads.discord_ban")) && (<DiscordRemoveButtons leadId={leadDetail.id} hasChannel={!!leadDetail.discord_guild_channel_id} canRemove={hasPermission("leads.discord_remove_channel")} canKick={hasPermission("leads.discord_kick")} canBan={hasPermission("leads.discord_ban")} />)}`
12. `function DiscordRemoveButtons(`（:936 付近）の引数に `canRemove: boolean; canKick: boolean; canBan: boolean` を足す。
    - 「チャンネルから外す」の条件 `{hasChannel && (` → `{hasChannel && canRemove && (`
    - Kick の `<Button ...>{t("leads.discordKick")}</Button>` を `{canKick && ( ... )}` で囲む。
    - BAN の `<Button ...>{t("leads.discordBan")}</Button>` を `{canBan && ( ... )}` で囲む。
    - 見出しの文字・確認の文・結果の文・handleAction は変えない。
13. :547 `canResync={hasPermission("leads.update")}` → `canResync={hasPermission("leads.discord_resync")}`

### 画面の試験 `frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx`

14. T1〜T3 を新しい鍵で書き直す。
    - T1 権限なし: 今のまま（5 つが無い・状態の文字は在る）。
    - T2 は「leads.update と leads.delete だけ」で 5 つとも無いことを確かめる形に変える（古い鍵ではもう出ない）。
    - T3 は新しい 5 つの鍵で 5 つとも在る。
15. T4 を足す: 新しい鍵を 1 つだけ持つとき、そのボタンだけが在り、ほかの 4 つは無い（5 通り。`it.each` でよい）。
    - remove_channel だけのときは、見出し（t("leads.discordRemove")）と「チャンネルから外す」だけが在る。

## 触らない

migrations・DB・ja.json/en.json・CSS・components/ の部品・RolesPage・ChannelInviteButton の中身・ほかの出し分け（:257 の canMerge など）・docs/handoff 以外の docs・.claude-pipeline/。

## 点検（全部の生出力をファイルに残す）

- `cd backend && python -m pytest tests/test_permission_catalog.py tests/test_system_roles.py -q`
- `cd frontend && npx vitest run src/pages/inbox/InboxKartePanel.discordButtons.test.tsx`
- `cd frontend && npx tsc --noEmit -p .`
- `cd frontend && npx eslint src/pages/inbox/InboxKartePanel.tsx src/pages/inbox/InboxKartePanel.discordButtons.test.tsx`
- `git grep -n 'require_permission("leads.update")\|require_permission("leads.delete")' -- backend/app/routers/discord_*.py` が 0 件。
- `git diff origin/main...HEAD --name-only` が、docs/handoff/discord-buttons-permission/ と、上の 9 ファイル（routers 3・tenant.py・conftest.py・test_permission_catalog.py・test_system_roles.py・InboxKartePanel.tsx・同 test）だけ。

## 想定分岐

- 行番号がずれていたら、上に書いた前の文字列で探して直す。前の文字列が見つからなければ止めて BLOCKED: で返す。
- `require_permission` が 1 つの道に複数付いていたら、変えずに止めて BLOCKED: で返す。
- C3（`test_registered_keys_are_collected`）など既存の試験が落ちたら、直さずに止めて BLOCKED: で返す（このカードの範囲外）。
- ローカルで pytest が DB などの準備で動かないときは、CI の結果で判定する。その旨を報告に書く。
- DEFAULT_ROLES の役割の名前が上と違ったら止めて BLOCKED: で返す。

## 報告

- `docs/handoff/discord-buttons-permission/impl-report-2.md` に、変えたファイル・点検の生出力のパス・想定分岐に当たったかを書き、コミットする。
- 最後の行は `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。
