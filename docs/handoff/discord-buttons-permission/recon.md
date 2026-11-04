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

## 7. 段階B の追加調査（2026-11-04 22:10 JST・origin/main 89d3320ed）

### 7-1. PO の決定

> 3

（2026-11-04 チャット。設計の選択肢「5つに分ける：操作ごとに付け外しできる」への回答。）

### 7-2. 本番の DB の再実測（読み取り専用・2026-11-04 22:17 JST・AUDIT sha=d3e32792d066 rows=14 result=ok）

| 項目 | 値 |
|---|---|
| 権限の一覧の件数 | 130（§5-1 の後に状態マスタ・商品カテゴリの 7 行が足された） |
| `leads.discord%` の行 | 0 |
| id の最大 | 53613 |
| 会社（public.tenants） | 1 test-corp・3 perm-check-zzz・4 highlife-jpn・5 test-tenant-2・6 tenant-review（すべて有効） |
| leads.update（id 14）を持つ役割の数 | 001: 5・003: 4・004: 4・005: 4・006: 4（計 21） |
| leads.delete（id 15）を持つ役割の数 | 001: 4・003: 3・004: 3・005: 3・006: 3（計 16） |

役割ごとの内訳は §5-2 と同じ（数が一致）。

読み取りの道の注意: 文字列 `'leads.update'`・`'leads.delete'` は書き込みの語を含むため断られる（`rejected: write keyword is not allowed`、AUDIT sha=5d458450a4b4）。読み取りでは id 14・15 で絞る。

### 7-3. 役割と権限の結び付けの実物

- `backend/app/services/tenant.py:511-516`（`{schema}.role_permissions`）: 列は id・role_id・permission_id。`UNIQUE(role_id, permission_id)`。permission_id は `public.permissions(id) ON DELETE CASCADE`。
- `migrations/003_add_phase1_tenant_tables.sql:199-205`: role_permissions の RLS は roles.tenant_id と `app.tenant_id` で絞る。FORCE は付いていない。
- `migrations/20260607_000000_fix_rls_policy_variable_name.sql:12`: jarvis は BYPASSRLS。
- `backend/app/services/tenant.py:50-185`（DEFAULT_ROLES。終わりは :186 の `]`）: 新しい会社を作るときの役割の初期の権限。マネージャーは leads.update・leads.delete、営業は leads.update を持つ。CS・仕入れ・発送は持たない。オーナーは "ALL"、システム管理者は "ALL_EXCEPT_SYSTEM_MANAGE"。
- `backend/app/services/tenant.py:1600-1655`（seed_system_roles）: 既にある役割（システム以外）の権限は上書きしない。今ある 5 社の役割には DEFAULT_ROLES の変更は届かない。
- `backend/app/services/tenant.py:1540-1580`（_assign_permissions_to_role）: 一覧に無いキーは `SELECT ... WHERE key = :key` が 0 行になり、黙って付かない。

### 7-4. 役割の画面

- `frontend/src/pages/roles/RolesPage.tsx:57-66`（CATEGORY_META）: 「リード」の並び順は 3。新しい区分を作るとアイコンと並び順の登録が要る。
- `frontend/src/pages/roles/RolesPage.tsx:70-78`（MENU_VIEW_KEY）: 「リード」のメニュー表示は leads.view だけを動かす。新しい行はメニュー表示に影響しない。
- `frontend/src/pages/roles/RolesPage.tsx:185-194`（toggleCategory）: 区分の「全選択」は、その区分の全行を付け外しする。

### 7-5. 鍵を見る場所の全数

- サーバー: §4 の 5 本だけ（`git grep -n -E "discord/(kick|ban|remove-from-channel|channel-invite|sync-role)" origin/main -- backend/app`）。
- 画面: `frontend/src/pages/inbox/InboxKartePanel.tsx:533`（招待）・`:538`（外す/Kick/BAN の部品）・`:547`（再同期）。DiscordRemoveButtons（`:936-1000`）は 3 つのボタンを 1 つの条件で出している。
- 試験: `backend/tests/test_permission_catalog.py:115-138`（C5 が招待・再同期の鍵を leads.update と決めている）、`backend/tests/conftest.py:1826`（ALL_TEST_PERMISSIONS）、`frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx`（T1〜T3）。

### 7-6. 観測事実のまとめ（段階B）

- 【事実】新しい 5 行を足し、今 leads.update を持つ 21 役割に 2 つ、leads.delete を持つ 16 役割に 3 つを付けると、付く行は 42 + 48 = 90 行。
- 【事実】今ある会社の役割には、DEFAULT_ROLES を変えても新しい鍵は付かない（§7-3）。データの変更で付ける必要がある。
- 【事実】「点検用（見るだけ）」（001・role 2611）は名前に反して leads.update・leads.delete を持っている（§5-2）。今回はそのまま写す（できることを変えない）。
