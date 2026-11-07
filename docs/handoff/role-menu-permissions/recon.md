# 役割の画面をメニューごとの3択にする — 現在地（recon）

| 項目 | 内容 |
|------|------|
| 基準 | origin/main `37fa04f7b`（2026-11-07 fetch 後の worktree） |
| 作成 | Opus（設計担当）。読んだのは worktree の実物と本番の読み取り専用 DB |

## 1. 既存 ADR の検索結果

- 検索: `docs/adr/FEATURE-INDEX.md` の「権限 / role / 認証」行（ADR-023 / ADR-032）と、`ls docs/adr | grep -i -E "role|perm|rbac"`。
- 関係するもの:
  - ADR-147（共通6ロール標準化）: ロールの種類と既定の許可。本件はロールの種類も既定の許可も変えない。
  - ADR-144（UI 部品の金型）: 新しい部品は `components/` に Xxx.tsx + `Xxx.css`（var() のみ）+ Xxx.stories.tsx で登録する。正本 `docs/CC_UI_GOVERNANCE.md`。
  - ADR-067（デザイントークン）: 色・寸法は CSS 変数だけ。
  - ADR-027（画面の言葉）: 文字は `t()` 経由。ja.json と en.json に同じ鍵。
- 関係しないもの: ADR-023 / ADR-032（ログインの仕組み）、ADR-1011 / ADR-1034（AI の作業許可の台帳。アプリの役割とは別物）。

## 2. 今の役割の画面

- ファイル: `frontend/src/pages/roles/RolesPage.tsx`（513 行）。試験ファイルは無い（`ls frontend/src/pages/roles` → `frontend/src/pages/roles/RolesPage.tsx` だけ）。
- 区分の並び順とアイコン: `frontend/src/pages/roles/RolesPage.tsx:57-66`（CATEGORY_META）。
- 「メニュー表示」の切替に使う鍵: `frontend/src/pages/roles/RolesPage.tsx:70-78`（MENU_VIEW_KEY）。
- 読み込み:
  - `frontend/src/pages/roles/RolesPage.tsx:113-114` で `/roles` と `/permissions`。
  - `frontend/src/pages/roles/RolesPage.tsx:124-128` で `/roles/{id}/permissions` と編集用の写し（useSeededForm・許可 id の Set）。
- 区分ごとに並べる: `frontend/src/pages/roles/RolesPage.tsx:142-151`。
- 編集できる条件: `frontend/src/pages/roles/RolesPage.tsx:172-173`。`roles.update` を持つこと、かつシステムのロールでないこと。
- 1つずつの切替: `frontend/src/pages/roles/RolesPage.tsx:175-182`。
- 区分まとめての切替: `frontend/src/pages/roles/RolesPage.tsx:185-194`。
- メニュー表示だけの切替: `frontend/src/pages/roles/RolesPage.tsx:197-217`。
- 保存: `frontend/src/pages/roles/RolesPage.tsx:219-232`。編集中の Set を丸ごと `PUT /roles/{id}/permissions` に送る。
- 許可1件ずつの行: `frontend/src/pages/roles/RolesPage.tsx:407-420`。CheckboxControl と `p.description` を使う。

## 3. サーバー側（変えない）

- `GET /permissions`: `backend/app/routers/roles.py:115-126`。全 135 件を返す。`menu.*` も含む。
- `GET /roles/{id}/permissions`: `backend/app/routers/roles.py:386-414`。
- `PUT /roles/{id}/permissions`: `backend/app/routers/roles.py:416-493`。
  - 送った一覧で丸ごと置き換える。
  - システムのロールは 403。
  - 自分以上の優先度のロールは 403。
  - 自分が持たない許可は付けられない。
- 結論: 画面が今と同じ形の一覧を送る限り、サーバーの変更も DB の変更も要らない。

## 4. メニューを出す条件（今の実物）

### 4-1. 左の列（PC）`frontend/src/components/DesktopShell.tsx`

| メニュー | 条件 | 行 |
|---|---|---|
| ダッシュボード | `dashboard.view` | 231 |
| スケジュール | いつも出る（条件なし） | 243-250 |
| 会話 | 各自の設定 `prefs.show_chat_menu`（許可ではない） | 252 |
| 在庫 | `products.view` | 273 |
| 見積・請求 | 各自の設定 `prefs.show_sales_menu` かつ（`quotes.view` か `invoices.view`） | 179-181 |
| リード・顧客 | `leads.view` か `customers.view` | 177 |
| 受注 / 売上 / 報酬 | どれも `orders.view` | 318 / 331 / 344 |
| 管理センター | 11 個の許可のどれか | 186-191 |

### 4-2. 左の列（スマホ）`frontend/src/components/MobileShell.tsx`

- 同じ条件を別に書いている: 118（リード・顧客）、121-122（見積・請求）、128（ダッシュボード）、283（会話）、302（在庫）、316（受注）。

### 4-3. 管理センター `frontend/src/pages/management-center/ManagementCenterPage.tsx`

| 区切り | メニュー（表示名の鍵） | 条件 | 行 |
|---|---|---|---|
| チーム | スタッフ `nav.staff` | `staff.view` | 37 |
| チーム | ロール `nav.roles` | `roles.view` か `roles.create` | 38 |
| チーム | チーム `nav.teams` | `teams.view` | 39 |
| チーム | シフト `nav.shifts` | `shifts.view` | 40 |
| チーム | 報酬設定 `nav.commissionSettings` | `orders.view` | 41 |
| チーム | レポート `nav.reports` | いつも出る | 42 |
| チーム | 会社ポリシー `nav.tenantPolicy` | `tenant.profile.edit` か `.view` | 43-44 |
| データ | 仕入先・状態マスタ・単位・メモマスタ | `suppliers.view` | 51 / 52 / 55 / 56 |
| データ | 状態 `nav.conditionsMaster` | `conditions.view` | 53 |
| データ | 商品区分 `nav.productCategories` | `product_categories.view` | 54 |
| データ | データ管理 `nav.dataManagement` | `erp.view` | 57 |
| 連携 | Googleドライブ・FedEx・DHL・UPS・PayPal | `erp.view` | 65-69 |
| 連携 | Discord設定・Discordお知らせ | `tenant.profile.edit` か `.view` | 70-73 |
| 事業 | 会社情報 `nav.tenantProfile` | `tenant.profile.edit` か `.view` | 80-81 |
| 事業 | 連絡手段 `nav.channels` | `channels.view` | 82 |
| 事業 | 連絡手段の名簿 `nav.channelMasters` | `tenant.profile.edit` | 83 |
| 事業 | Bot `nav.bots` | `bots.view` | 84 |
| 事業 | 通知 `nav.notifications` | `notifications.manage` | 85 |
| 事業 | ログイン申請 `nav.tenantLoginRequests` | オーナーだけ（`isTenantOwner`） | 86 |

- 観測: 同じ許可の条件が、PC・スマホ・管理センターの3か所に別々に書かれている。

## 5. 本番の許可（読み取り専用 DB・2026-11-07 07:42Z）

- `SELECT key, category FROM ai_ro.public__permissions ORDER BY key;` → 135 行（AUDIT 行 `rows=135 result=ok`）。
- 生の結果: `/private/tmp/claude-501/-Users-tanizawashingo-salesanchor/63979ab3-7f03-4149-aa62-8a09424a06bb/scratchpad/roleui/perms.txt`。
- `menu.*` は 19 件。コードで使われていない（`git grep -n -E "[\"'\`]menu\.[a-z_]+[\"'\`]" -- frontend/src backend/app` → 0 件）。
- 名前が `.view` で終わらない「見る」許可: `buddy.view_own`、`staff_reports.view_own`、`staff_reports.view_team`、`system.audit_view`。
- 営業ロール（tenant_001）が持つ許可: `menu.*` 11 件、`leads.convert/create/discord_invite/discord_resync/update/view`、`dashboard.view`、`reports.view`、`deals.create/update/view`、`orders.create/update/view`、`goals.view`、`customers.create/update/view`。
  - 生の結果: `/private/tmp/claude-501/-Users-tanizawashingo-salesanchor/63979ab3-7f03-4149-aa62-8a09424a06bb/scratchpad/roleui/rolecat.txt`。
  - 観測: 区分の中で一部だけ持つ形がある（例: リードは削除や BAN を持たない）。3択だけでは表せない。

## 6. 使える部品（`frontend/src/components/`）

- 3択の切替の金型は無い。似たもの:
  - `Toggle`（2択）、`IconToggleButton`（押す/押さない）、`Tabs`、`ChoiceCardGroup`（縦のカード型ラジオ）、`CheckboxControl`、`Badge`（neutral/info/success/warning/danger/purple）、`Button`（primary/secondary/ghost/danger/outline/tab）。
- アイコン: `frontend/src/constants/icons.tsx:163-167` に `STATUS_ICONS.check`（✓）と `STATUS_ICONS.error`（✕）。斜め線は未登録。`@heroicons/react` 2.2.0 に `SlashIcon` がある（`frontend/node_modules/@heroicons/react/24/outline/SlashIcon.js`）。
- 色の変数: `frontend/src/tokens.css:619-624`（`--color-error*` / `--color-success*`）、`frontend/src/index.css:19,26`（`--bg-subtle` / `--text-muted`）。暗い画面用は `frontend/src/tokens.css:667-672`。

## 7. 未確認

- なし。
