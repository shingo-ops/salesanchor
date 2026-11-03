# 設計: アプリ全画面の鈴（未読数＋知らせ一覧）と Discord の名前呼び

- 状態: 設計案作成済み → 設計審査済み（§10、同一 AI による自己審査。独立した第二者レビューではない）→ **改訂中**（§4-改訂1。PO 2026-11-03 で宛先が変わり、編集ページが加わった。編集ページで何を変えられるかは PO の回答待ち。回答まで実装の合流・PR は止める）
- 調べ: `docs/handoff/in-app-notice-bell/recon.md`（以下 R1）、`docs/handoff/in-app-notice-bell/recon-2.md`（以下 R2）
- 外部仕様: Discord の `allowed_mentions`（Context7 `/discord/discord-api-docs` `developers/resources/message.mdx`、2026-11-03 照会）
- 前の設計: `docs/handoff/discord-outside-ticket-notify/design.md`（部屋の外の書き込みを Discord に1件知らせる。本番反映済み）

## 1. 目的（PO の言葉）

- 「画面の上の鈴の印や知らせの一覧……これも作ってほしい」（2026-11-03 チャット）
- 宛先: 「3」（そのお客さんの担当者）→「管理者と担当に出す、Discordも同様」→「1」（Discord は受け取り口のチャンネルの知らせで、担当者と管理者の名前を呼ぶ）
- 対象の会社: HIGH LIFE JPN から（通知先の webhook を PO が登録する。仕組みは全社共通で、登録の無い会社では Discord 側は何も送らない）

## 2. 受入条件（KGI / KPI）

| 番号 | 基準（○×で判定） | 検証方法 |
|---|---|---|
| K1 | PC（768px 以上）とスマホ（767px 以下）のすべての画面の右上に鈴があり、未読があれば数字が出る。0 件なら数字は出ない。100 件以上は「99+」 | e2e spec（§7-5）を 3 幅で流す。PO が本番で目視 |
| K2 | 鈴を押すと、自分宛ての知らせが新しい順に最大 50 件出る。0 件なら「知らせはありません」 | backend 試験（51 件入れて 50 件・新しい順）＋ e2e |
| K3 | 知らせ 1 件を押すと Discord の書き込みが新しいタブで開き、数字が 1 減る。既読の行は押しても数字は変わらない | backend 試験（既読化で未読数 -1・二度目は不変）＋ e2e |
| K4 | お客さんが部屋の外に書いてから 1 分以内に、宛先の人の鈴の数字が増える（画面の読み直し不要） | 本番: 宛先の人がアプリを開いたまま、担当者以外の人が共有チャンネルに 1 回書く → 1 分以内に +1（PO 目視）。試験: 知らせを作ったとき宛先全員へ `publish_user_change` が呼ばれる |
| K5 | 他の会社の知らせは決して出ない。他の人宛ての知らせも出ない | backend 試験（別テナント・同じテナントの別の人の知らせが一覧・未読数・既読化のどれにも出ない、既読化は 404） |
| K6 | 宛先は「担当者＋その会社の管理者」。担当者が見つからないときは管理者だけ | backend 試験（§4 の表の 6 通り） |
| K7 | Discord の知らせの同じ文の中で、宛先のうち Discord の id が登録されている人の名前が呼ばれる。@everyone・@here・役割は呼ばない | backend 試験（`send_discord_notification` に渡す `mention_user_ids`）＋本番で PO のスマホが鳴る |
| K8 | 書き込みの本文と Discord の id は、知らせの表・API・ログに入らない | backend 試験（作った行の列に本文が無い）＋差分の目視 |

## 3. 対象と対象外

- 対象: 知らせの表、宛先を決める関数、一覧・既読の API、即時反映の合図、両 Shell の鈴と一覧、Discord の名前呼び、試験。
- 対象外: 他の種類の知らせ（担当割当など。表は種類つきで作るので後から足せる）、web push、メール、知らせの削除画面、既読を一括にするボタン、お客さんへの送信（1 行も足さない）。

## 4. 宛先の決め方

書いた人の Discord の id（`message.author.id`）から決める。部屋の外に来る時点でチャンネルからは lead が引けない（R1 1-1、`backend/app/discord_gateway/ticket_channel_writer.py:186-196`）。

(1) 担当者の候補を集める（どちらもスキーマ名つき、ADR-072）
- 道 a: `{tenant}.leads WHERE discord_user_id = :uid` の **全件**（`LIMIT 1` にしない。R2 (4)、索引は一意でない `migrations/091_add_leads_discord_messaging_columns.sql:35-39`）の `assigned_to`
- 道 b: `{tenant}.lead_channels WHERE platform='discord' AND external_id = :uid`（`migrations/20260607_120000_create_lead_channels.sql:16-25`）→ `{tenant}.leads.id` の `assigned_to`
- 担当者 = `leads.assigned_to`（受信箱で「担当」として使っている列。`backend/app/routers/meta_inbox.py:1022-1026`）。`companies.sales_rep_id` は使わない（R1 1-2 の 5。受信箱と同じ列に揃える）
- NULL を除き、重複を除く。`public.users` と結び、`users.tenant_id = :tenant_id AND users.is_active` の人だけ残す（`assigned_to` に FK が無い: `migrations/003_add_phase1_tenant_tables.sql:92`）

(2) 管理者を集める
- `{tenant}.user_roles JOIN {tenant}.roles ON roles.id = user_roles.role_id WHERE roles.system_key IN ('owner','admin')` の `user_id`（定義の正本 `backend/app/auth/system_roles.py:17-19`。判定は user_roles を使い users.role は使わない）
- 同じく `public.users` と結び、同じ会社・有効な人だけ（`user_roles.user_id` に FK が無い: `migrations/003_add_phase1_tenant_tables.sql:65`）
- super admin（`users.is_super_admin`）は自動では足さない。既存の約束が「会社の管理者＝owner / admin、super admin は別枠」（R2 1-4、`backend/app/models.py:30-31`）のため。その会社で owner / admin の役割を持っていれば (2) で入る

(3) 宛先 = 担当者 ∪ 管理者（重複を除く）

| 場合 | 担当者の候補（有効な人） | 宛先 |
|---|---|---|
| ① 1 人 | 1 | その人＋管理者 |
| ② 同じ人が複数の lead の担当 | 1（重複除去後） | その人＋管理者 |
| ③ lead が無い（未紐付け） | 0 | 管理者だけ |
| ④ lead はあるが担当なし | 0 | 管理者だけ |
| ⑤ 担当者が無効・別会社・存在しない | 0 | 管理者だけ |
| ⑥ lead が複数あり担当者が別々 | 2 以上 | 管理者だけ（誰の客か決まらないため。PO 決定「見つからないときは管理者だけ」に含める） |

管理者が 0 人で担当者も 0 人なら知らせは作らない（Discord は今までどおり名前を呼ばずに送る）。

### 4-改訂1（PO 2026-11-03 チャット。上の (2)(3) と表を置き換える）

- PO 原文: 「担当者がいれば担当者に、担当者がいなければオーナーに贈る設定、設定もオーナーが編集できるように編集ページが欲しい」
- 新しい宛先: 担当者の候補（有効な人）が 1 人以上 → **担当者だけ**（管理者は足さない）。0 人 → **オーナー**（`roles.system_key = 'owner'` のみ。`admin` は入れない）
- ⑥（担当者が別々に 2 人以上）: **その担当者の全員**。Opus がこう読み、PO に「違えば教えてください」と伝えた（2026-11-03）。PO の明示の確認はまだ
- 編集ページ: オーナーが編集できる。PO 回答「1」（2026-11-03）: **担当者がいないときに受け取る人をオーナーが選べる。最初（未設定）はオーナー**。担当者がいるときに一緒に受け取る人・種類ごとの切り替えは対象外。設定の置き場所・API・画面・K は recon-3 のあと §4-改訂2 で決める
### 4-改訂2（PO 回答「1」2026-11-03 で編集の権限が決まり確定）

調べ（Opus が手元で読み取りのみ。クラウドの調べ担当は2回とも結果を出さずに終了したため。生出力 /tmp/CC報告ファイル/in-app-notice-bell/recon3-local-{1,2,3}.txt）:
- 通知の設定ページは既にある: `frontend/src/pages/notifications/NotificationsPage.tsx`（管理センターの「通知」、`frontend/src/pages/management-center/ManagementCenterPage.tsx:85` で `notifications.manage` を持つ人だけに出す）。API は `backend/app/routers/notifications.py:67-143`、編集は `require_permission("notifications.manage")`
- owner は権限キーを全部自動で持つ（`backend/app/auth/system_roles.py` `compute_permission_keys`）。admin は運営用で会社の人には見せない（同 `TENANT_HIDDEN_SYSTEM_KEYS`）。他の役割にも owner が `notifications.manage` を付けられる
- 複数を選ぶ金型 `frontend/src/components/MultiSelect.tsx`（stories・test あり）
- 利用者の一覧 API `GET /staff`（`backend/app/routers/staff.py:532`）

案:
- 置き場所: 新しいページは作らず、既存の通知の設定ページに1区画「担当者がいないときに受け取る人」を足す（設定を1か所に集める）
- 保存: 各社スキーマに新しい表 `{tenant}.notice_fallback_recipients (user_id INTEGER PRIMARY KEY, updated_by INTEGER, updated_at TIMESTAMPTZ DEFAULT now())`。行が0件 = 未設定 = オーナー全員。public.tenant_settings に列を足さない（宛先の元データ・知らせの表と同じ各社スキーマに揃える）
- API: `GET /api/v1/notice-fallback-recipients`（今の設定と「未設定ならオーナー」の印）、`PUT`（user_id の一覧で丸ごと置き換え。同じ会社・有効な人以外は 422）
- 宛先を決めるとき: 設定の人のうち有効な人が0人になっていたら、オーナーへ戻す（知らせが消えないように）
- 編集の権限: 既存の `notifications.manage` に揃える（PO「1」。GET も PUT も `require_permission("notifications.manage")`。画面の区画も `hasPermission("notifications.manage")` のときだけ出す）
- 候補の一覧: `GET /staff` は使わない（`staff.view` が要り、`discord_user_id` も返すため。`backend/app/routers/staff.py:532-533`、`backend/app/schemas/staff.py:157`）。`GET /api/v1/notice-fallback-recipients` が `{ selected: [user_id], defaulted_to_owner: bool, candidates: [{ user_id, name }] }` を返す。candidates は同じ会社・有効な `public.users` で、名前は既存の書き方 `COALESCE(NULLIF(u.full_name, ''), u.username)`（`backend/app/services/viewer_message_templates.py:212`）をそのまま使う。`public.users.full_name` は担当者登録で書かれる（`backend/app/routers/staff.py:100-107`）。有効の判定は `public.users.is_active`。Discord の id・メールは返さない
- 画面: `MultiSelect`（layout="popover"）。文言は全部 t()（`notices.fallback.title` / `.help` / `.defaultOwner` / `.clear` / `.count` / `.saved`、ja/en 同じキー）。保存ボタンは既存の `Button`。色・余白はトークンのみ
- 宛先の関数（実装済み `backend/app/services/user_notices.py`）を直す: 担当者が1人以上 → 担当者だけ（⑥の別々の担当者は全員）。0人 → 設定の人（有効な人だけ）。設定が0件か、有効な人が0人 → `system_key='owner'` の有効な人全員。admin は足さない。Discord の名前呼びも同じ宛先
- 表: 各社スキーマ `{tenant}.notice_fallback_recipients`。まだどこにも適用されていない `migrations/20261103_150000_create_user_notices.sql` に足す（同じ DO $$ 走査）。新しい会社の作成経路（`backend/app/services/tenant.py` `_TENANT_TABLES_SQL`）にも足す。AI 閲覧用の view には足さない
- 試験に足す: 宛先（担当者あり→担当者だけ／担当者なし・設定なし→オーナー／設定あり→設定の人／設定の人が全員無効→オーナー／admin は入らない）、API（`notifications.manage` が無い人は 403、別会社・無効な人の id は 422、candidates に Discord の id とメールが無い）、e2e（区画が出る・選んで保存）

- K6 はこの改訂で次に置き換える: 「担当者がいれば担当者だけ。いなければ通知の設定ページで選んだ人。選んでいない・選んだ人が全員無効ならオーナー」。K9 を足す: 「`notifications.manage` を持つ人だけが、通知の設定ページで受け取る人を選んで保存でき、保存後の次の知らせからその人に届く」（検証: backend 試験＋e2e＋本番で PO 目視）実装済みの宛先関数（`backend/app/services/user_notices.py`）と試験は改訂に合わせて直す（Sonnet に依頼）

## 5. 表

置き場所: **各社スキーマ** `{tenant}.user_notices`。理由:
- 元のデータ（lead・roles・user_roles）が各社スキーマにある
- スキーマの分離で他社の行に届かない（K5）。public に置くと `tenant_id` 列と RLS（ADR-1018）の追加が要り、守りが増える分だけ間違いの入口が増える
- 各社スキーマの表は RLS の対象外（`docs/specs/tenant-rls/README.md:7-12`）

```sql
-- migrations/2026110X_HHMMSS_create_user_notices.sql（DO $$ … pg_namespace の全テナント走査。手本 migrations/20260607_120000_create_lead_channels.sql:10-40）
CREATE TABLE IF NOT EXISTS {各テナント}.user_notices (
  id           BIGSERIAL PRIMARY KEY,
  user_id      INTEGER NOT NULL,          -- 宛先の public.users.id
  kind         TEXT NOT NULL,             -- 'discord_outside_ticket_post'
  actor_name   TEXT,                      -- 書いた人の Discord の表示名（今の Discord 通知の文と同じもの）
  channel_name TEXT,                      -- 書かれたチャンネル名
  link_url     TEXT,                      -- 書き込みへのリンク（message.jump_url。今の Discord 通知の文と同じもの）
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  read_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_user_notices_user_created ON {各テナント}.user_notices (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_notices_user_unread ON {各テナント}.user_notices (user_id) WHERE read_at IS NULL;
```

- 本文・Discord の id の列は作らない（K8）。`link_url` は書き込みの場所（サーバー・チャンネル・書き込みの番号）で、書いた人の id は含まない
- 新しいテナントでも同じ表ができるよう、テナント作成時の表の作り方（`backend/app/services/tenant.py` のテナント表作成）にも足す。実装者は作成経路を確かめ、足す場所が見つからなければ止める
- `.github/workflows/deploy.yml` に実行行を足す。`migration-test.yml` の最小定義が要るかを確かめる
- AI 用の閲覧ビュー（`migrations/20261024_100300_create_ai_cloud_views.sql`）には足さない（人の名前を含むため）。分類表に「足さない」を書く形があれば従う
- 保存期間: 今回は消さない（一覧は 50 件まで）。件数の見回りは §9

## 6. 動きの順番（`backend/app/discord_gateway/outside_ticket_notice.py`）

今の流れ（R1 1-3、R2 (5)）: 除外判定 `:81-94` → 30 分の重複抑え `:95-102` → 本文を組む `:106-108` → `send_discord_notification` `:110`（中で commit と `reset_tenant_context`、`backend/app/routers/notifications.py:188-189`）。

変更後:
1. 除外判定と 30 分の重複抑えはそのまま。**鈴も同じ関門に乗せる**（同じ人・同じチャンネルの 30 分以内の 2 件目は鈴も増えない）。PO が Discord 側で選んだ「まとめる時間 30 分」と揃えるため。最初の 1 件は 1 分以内に出るので K4 は満たす
2. 宛先を決める（§4。読むだけ・スキーマ名つき）
3. 宛先の Discord の id を引く: `{tenant}.staff WHERE user_id = ANY(:ids)` の `discord_user_id`、数字だけ（前例 `backend/app/services/lead_assign_notifier.py:32-35,46`）。無い人は呼ばない
4. `send_discord_notification(db, tenant_id, EVENT_TYPE, NOTICE_TITLE, body, mention_user_ids=…)`。引数は既にあり、`content` に `<@id>` を並べ `allowed_mentions={"parse": [], "users": [...]}` で送る作りも既にある（`notifications.py:153-154,171-175`）。呼ぶ人は最大 50 人で切る（`allowed_mentions.users` の上限 100、本文 2000 文字に対し 1 人 約 22 文字）
5. `{tenant}.user_notices` に宛先の人数分 INSERT（スキーマ名つき）→ `commit` → `reset_tenant_context()`（ADR-072）
6. commit の後に、宛先 1 人ずつ `publish_user_change(_sync)(user_id, "notices")`（`backend/app/realtime/publisher.py:97-110`。gateway の処理が async かどうかで呼ぶ方を選ぶ）
7. 4 と 5 は互いに独立させる: Discord が失敗しても鈴は作る（`send_discord_notification` は失敗を握って警告だけ: `notifications.py:186-187,190-191`）。5 が失敗したときは警告を残し、例外を外へ出さない（今の書き込み処理を止めない）

ログ: 宛先の人数・呼んだ人数だけ。id・名前・本文は出さない。

## 7. 画面と API

### 7-1 API（新しい router。`current_user` の本人分だけ）
- `GET /api/notices` → `{ items: [{id, kind, actor_name, channel_name, link_url, created_at, read_at}], unread_count }`。新しい順・最大 50 件。`user_id = current_user.id`、テナントは `current_user.tenant_id` からスキーマ名を引く（`tenant_table_ref`、前例 `backend/app/services/lead_assign_notifier.py:13,26-27`）。テナントの無い人は空
- `POST /api/notices/{id}/read` → 本人の行だけ `read_at = now()`（既読なら変えない）。他人・他社の id は 404。返り値 `{unread_count}`
- 既存の router の前置き・認証の依存関数は実装者が既存の router に揃える

### 7-2 即時反映（ADR-1016）
- 人宛ての topic に `notices` を足す: `backend/app/realtime/topics.py` と `frontend/src/lib/realtime/topics.ts` の両方（照合試験あり、R1 (2)）
- ADR-1016 に改訂を 1 節足す（人宛て topic `notices` の追加と、送り口は §6-6 の 1 か所だけ）

### 7-3 鈴の置き場所
- PC（DesktopShell）: 右上の `.avatar-btn`（`frontend/src/components/DesktopShell.tsx:402-413`、`position: fixed`）の **左隣**。重なり検査（`check:css-fixed-position`）に止められないよう、鈴とアバターを 1 つの固定の入れ物に並べる。アバターの見た目・動きは変えない
- スマホ（MobileShell）: 画面の右上に同じ鈴を置く。実装者は MobileShell の右上に既に固定の部品があるかを先に確かめ、あれば止めて報告する（NEEDS_DECISION）
- 全画面に常駐させる差し込み場所は既存の前例に倣う（`DesktopShell.tsx:206-209`、`frontend/src/components/MobileShell.tsx:43-45` の `RealtimeProvider` 直下）

### 7-4 部品（金型を使う。ADR-144・ADR-067・ADR-027）
- 新しい部品 `NoticeBell`（鈴のボタン＋数字＋一覧）。中身は既存の金型: `Popover`（`frontend/src/components/Popover.tsx`）、`Badge`（`frontend/src/components/Badge.tsx`、variant danger、sm）、印は `constants/icons.tsx` の `BellOutline`（:157）
- 一覧の 1 行は新しい部品 `NoticeRow`（押せる行。未読は太字＋左に丸）。色・余白・角・z-index はトークンだけ（直値禁止）。足りないトークンがあれば `:root` と `:root.force-dark` の両方に足す
- 文字はすべて `t()`。ja.json / en.json に同じキー:
  - `notices.bellLabel`（「お知らせ」、未読数つき aria-label は `notices.bellLabelUnread` 「お知らせ（未読 {{count}} 件）」）
  - `notices.title`「お知らせ」、`notices.empty`「知らせはありません」
  - `notices.kind.discord_outside_ticket_post`「{{actor}} さんが #{{channel}} に書き込みました」
- 時刻は既存の相対時刻の表示があれば使い、無ければ `ja` の日時の形（既存の日付表示の関数を探して使う）
- 読み込み: 画面を開いたとき 1 回＋ `useRealtimeRefresh(["notices"], reload)`（前例 `frontend/src/features/auth/LoginApprovalWatcher.tsx:12,82`）。鈴を開いたときも 1 回読み直す
- 押したとき: `window.open(link_url, "_blank", "noopener")` → `POST …/read` → 返った `unread_count` で数字を更新。`link_url` が `https://discord.com/` で始まらないときは開かない

### 7-5 試験
- backend: §4 の 6 通り、K2・K3・K5・K7・K8、30 分の関門で鈴も 1 件だけ、Discord 失敗でも鈴は作る
- e2e: `frontend/tests-e2e/visual-language/notice-bell.spec.ts`（API はモック）。鈴に 3 → 開くと 3 行・新しい順 → 1 行押すと 2、0 件で数字なし、100 件で「99+」。3 幅の project で流れる

## 8. 代替案と選んだ理由

| 案 | 採否 | 理由 |
|---|---|---|
| 表を public に置き RLS | 不採用 | §5。守りの追加が要り、元データは各社スキーマ |
| 既存の `notification_logs` を流用 | 不採用 | 送り先 webhook の記録で、人の列が無い（R1 (2)） |
| 鈴は 30 分の関門の外で毎回増やす | 不採用 | Discord と数が食い違う。PO は 30 分のまとめを選んでいる |
| 担当者に `companies.sales_rep_id` も使う | 不採用 | 受信箱の「担当」と食い違う道を増やす（R1 1-2 の 5） |
| 鈴は一覧の画面（ページ）にする | 不採用 | PO の言葉は「画面の上の鈴」。全画面から 1 押しで見える Popover にする |

## 9. 危険と対処・維持の仕組み

| 危険 | 対処 |
|---|---|
| 他社・他人の知らせが出る | スキーマの分離＋ `user_id = current_user.id`。試験 K5 を CI で毎回 |
| 書き込みの本文や id が漏れる | 列を作らない。試験 K8 |
| 鈴の処理の失敗で Discord の書き込み処理が止まる | §6-7。例外を外へ出さない試験 |
| 表が増え続ける | 1 通知 = 宛先の人数行。30 分の関門があるので増え方は Discord の通知数×宛先数。1 か月後に件数を数え、1 万行を超えたら古い既読を消す仕組みを別に設計する |
| 名前を呼ぶ人が多すぎる | 50 人で切る |

- 守り手: backend 試験・e2e spec（CI で毎回）、ADR-1016 の topic 照合試験、`check:css-fixed-position`、i18n・トークンの検査

戻し方: 本 PR の revert（表は残るが読まれなくなるだけ。表を消すのは PO 確認）。Discord の名前呼びだけ止めたいときは通知先の設定画面で種類のチェックを外す。

## 外部・過去事例の参照と我々への応用

- 外部の数値つき事例: 今回は使わない。鈴と未読数は一般的な形で、設計の成否は §2 の試験と本番の目視で直接確かめられるため、外の数字で成功を証明する必要が無い。
- 社内の過去事例: 人宛ての即時反映は「知らない機械のログイン許可」で本番動作済み（ADR-1055、`frontend/src/features/auth/LoginApprovalWatcher.tsx`）。Discord の名前呼びは担当割当の知らせで本番動作済み（`backend/app/services/lead_assign_notifier.py:46,60`）。どちらも同じ部品を使い回す。
- Discord 公式（Context7、2026-11-03）: webhook は `allowed_mentions` を渡さないと利用者の名前だけ解釈する。呼ぶ名前は本文（`content`）に書く必要があり、`embeds` の中では鳴らない。本人が通知を切っていると鳴らないことがある（K7 の本番確認はこの限界つき）。

## 10. 設計審査（Architect、同一 AI による自己審査）

- 判定: **APPROVE**
- 確かめた点:
  - 既存の仕組みとの整合: 宛先の列（`assigned_to`）は受信箱と同じ。管理者の定義は `system_roles.py:17-19` の正本どおり。Discord の名前呼びは既存の引数を使い、新しい送り口を作らない。即時反映は ADR-1016 の人宛て合図の型どおり
  - 根拠: すべての前提に R1・R2 の行番号か Context7 の出典がある
  - 受入条件: K1〜K8 はすべて試験か画面で○×が付く。K4・K7 の本番確認は PO の目視（K7 は本人の通知設定に左右される限界を明記）
  - 実装範囲: 触るものは §3・§5〜§7 に列挙。決めていない枝（テナント作成経路が見つからない、スマホ右上に既存の固定部品）は止める条件として書いた
- 未解決: 無し（事業判断が要る点は PO の決定で埋まっている。super admin の扱いは既存の約束に従った）
- 危険な道: `migrations/` と `deploy.yml` を含むため、ADR-135/136 の GO（委任 GO）を経てから合流する
