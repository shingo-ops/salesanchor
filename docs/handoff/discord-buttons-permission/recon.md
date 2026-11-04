# recon: リードのカルテの Discord ボタンの出し分けと、Discord 操作の別権限

- 調査日: 2026-11-04（JST）
- 基準: origin/main 7d56ab771（PR #5119 のマージ後）
- 調査者: Claude Opus（設計担当）。観測は下記コマンドとファイルの実物。

## 1. PO の依頼（原文）

> 別途権限として付与できるようにするまず見えないように1

読み: ①まず、押しても断られるボタンを、権限の無い人には見せない（選択肢 1）。②その後、Discord の操作を「別の権限」として役割に付けられるようにする。

## 2. 既存 ADR・仕様の検索

- `git grep -n -i "discord" docs/adr/` の主な該当: ADR-091（docs/adr/ADR-091-discord-bot-scope-definition.md。リードの Discord 連携。KPI5 チャンネル招待・KPI6 外す/キック/BAN・KPI7 ロール再同期）。
- ADR-1007（docs/adr/ADR-1007-migration-structure-only-run-once.md:14・:36・:48-51）: migration は構造だけ。値の投入は「PO の合意、DRY-RUN → COMMIT、docs/handoff/<topic>/ に SQL と記録」。所有者は public.permissions の全部、管理者は system.manage 以外の全部をコードで計算（行が無くても届く）。
- ADR-1007:70: 新しい権限が所有者・管理者に届くまで最大 300 秒（cache.py の TTL）。
- docs/handoff/permission-keys-conditions-categories/design.md §11-6: 「画面のボタンの出し分け」は対象外として PO に別に聞く、と記録済み。本件はその続き。
- 権限を足す migration の前例 migrations/065_seed_central_admin_permissions.sql は ADR-1007 で無効化済み（同ファイル:38-41）。新しい権限は migration ではなくデータの変更で足す。

## 3. 画面（frontend）の実物

`frontend/src/pages/inbox/InboxKartePanel.tsx`（origin/main 7d56ab771）

- :17 `import { usePermissions } from "../../hooks/usePermissions";`
- :102 `const { hasPermission } = usePermissions();`（InboxKartePanel の中。KarteTabContent には渡っていない）
- :257 `canMerge={hasPermission("leads.delete")}`（既存の出し分けの前例）
- :464-475 `function KarteTabContent(...)` は usePermissions を呼んでいない。
- :531-535 チャンネル招待ボタン `<ChannelInviteButton>`。権限の確認なし。
- :536-539 外す/キック/BAN `<DiscordRemoveButtons>`。権限の確認なし。
- :540-547 ロール同期の状態 `<RoleSyncStatusRow>`。状態の表示と再同期ボタンが同じ部品の中（:875-931）。再同期ボタンは :920-926。
- :835-872 ChannelInviteButton → `POST /discord/channel-invite/{leadId}`
- :933-989 DiscordRemoveButtons → `POST /discord/{remove-from-channel|kick|ban}/{leadId}`

`frontend/src/hooks/usePermissions.ts`（origin/main）: `/me/permissions` を写しの置き場（useApiQuery）から読む。`hasPermission(key)` は Set の has。複数の部品で呼んでも通信は 1 回。

試験の前例: `frontend/src/features/secretary/SecretaryChat.test.tsx:35-37` が `vi.mock("../../hooks/usePermissions", ...)` で hasPermission を差し替えている。

Discord ボタンを参照する既存の試験: `grep -rl -E "ChannelInviteButton|DiscordRemoveButtons|RoleSyncStatusRow" frontend/src` → InboxKartePanel.tsx 本体と InboxPage.tsx のみ。試験は無い。

## 4. サーバー（backend）の実物（PR #5119 後）

| 道 | 求める鍵 | 場所 |
|---|---|---|
| POST /discord/channel-invite/{id} | leads.update | backend/app/routers/discord_channel_invite.py:63 |
| POST /discord/sync-role/{id} | leads.update | backend/app/routers/discord_role_resync.py:43 |
| POST /discord/remove-from-channel/{id} | leads.delete | backend/app/routers/discord_remove.py:80 |
| POST /discord/kick/{id} | leads.delete | backend/app/routers/discord_remove.py:143 |
| POST /discord/ban/{id} | leads.delete | backend/app/routers/discord_remove.py:193 |

権限の判定 `require_permission`（backend/app/auth/dependencies.py:658-688）に super admin の素通しは無い。

## 5. 本番の DB（読み取り専用・ai_ro の写し）

### 5-1. リードの権限（2026-11-04 18:43 JST）

| id | key | category | description |
|---|---|---|---|
| 12 | leads.view | リード | リード一覧の閲覧 |
| 13 | leads.create | リード | リードの登録 |
| 14 | leads.update | リード | リード情報の編集 |
| 15 | leads.delete | リード | リードの削除 |
| 16 | leads.convert | リード | リードの案件化 |

Discord 専用のリードの権限は無い（`key LIKE '%discord%'` は id 4991 central.supplier_discord_routing.edit の 1 件だけ。中央マスタ用で無関係）。

### 5-2. 役割ごとの保有（5 社・2026-11-04 18:43 JST・AUDIT rows=37 result=ok）

| 役割 | 001 | 003 | 004 | 005 | 006 |
|---|---|---|---|---|---|
| オーナー | 更新・削除（2人） | 更新・削除（0人） | 更新・削除（1人） | 更新・削除（1人） | 更新・削除（1人） |
| システム管理者 | 更新・削除（0人） | 更新・削除（0人） | 更新・削除（0人） | 更新・削除（0人） | 更新・削除（0人） |
| マネージャー | 更新・削除（0人） | 更新・削除（0人） | 更新・削除（0人） | 更新・削除（0人） | 更新・削除（1人） |
| 営業 | 更新のみ（0人） | 更新のみ（0人） | 更新のみ（2人） | 更新のみ（0人） | 更新のみ（2人） |
| CS | なし（0人） | なし（1人） | なし（0人） | なし（1人） | なし（0人） |
| 仕入れ | なし | なし | なし | なし | なし |
| 発送 | なし | なし | なし | なし | なし |
| 点検用（見るだけ）（001のみ） | 更新・削除（1人） | — | — | — | — |
| スモーク専用（004のみ） | — | — | なし（1人） | — | — |

（「更新」= leads.update、「削除」= leads.delete。かっこは割り当て人数。）

### 5-3. 権限の編集画面の表示の出どころ

- `GET /permissions`（backend/app/routers/roles.py:114-122）が `SELECT id, key, resource, action, description, category FROM public.permissions ORDER BY category, key`。
- `frontend/src/pages/roles/RolesPage.tsx:145-149` が category でまとめ、:416 で `p.description` をそのまま表示する。
- つまり新しい権限を 1 行足すと、category「リード」の中に description の文が出る。画面のコードの変更は要らない（i18n の鍵も要らない。表示文の正本は DB の description）。

## 6. 観測事実のまとめ

- 【事実】5 つの Discord ボタンは、権限を見ずに誰にでも出ている（§3）。
- 【事実】サーバーは invite・resync に leads.update、外す・キック・BAN に leads.delete を求める（§4）。
- 【事実】今、権限が無いのにボタンが見えている実在の人: CS 2 人（003・005）、スモーク専用 1 人（004）。営業 4 人（004・006）は外す・キック・BAN が見えるが押すと断られる。
- 【事実】新しい権限は public.permissions への 1 行のデータの変更で足し、所有者・管理者には行なしで届く（ADR-1007）。
- 【未確認】営業が外す・キック・BAN を押して断られた回数（記録を読んでいない。設計の判断には使わない）。
