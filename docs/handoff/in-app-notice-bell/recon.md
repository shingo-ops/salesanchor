# 調査: アプリ全画面の鈴（未読数＋知らせ一覧）— 最初の知らせ「部屋の外の書き込み」

- 役割: 調査のみ。製品コード・試験・設定は変えていない。基準は origin/main（b492b3f1c）。
- 根拠の書き方: `パス:行`。確かめられなかった事は「未確認」と書く。
- 書かないもの: お客さんの書き込みの本文・Discord の id・URL・秘密の値。

---

## (1) 書いた Discord の人 → お客さん（リード）→ 担当者（users）

### 1-1 割り出しの道筋

前提: 部屋の外の書き込みは「その channel_id に一致する lead が無い」ときに入る（`backend/app/discord_gateway/ticket_channel_writer.py:186-196`）。つまり channel からは lead が引けない。引くのは**書いた人の Discord id** から。

| 段 | 表.列 | 根拠 |
|---|---|---|
| 0 | 書いた人 = `message.author.id`（通知側は bot・webhook・担当者を除外済み） | `backend/app/discord_gateway/outside_ticket_notice.py:81-94` |
| 1a | `tenant_NNN.leads.discord_user_id`（= 書いた人の id） → `leads.id` | 列の追加 `migrations/091_add_leads_discord_messaging_columns.sql:30`／索引（一意でない）`:35-39`／引く既存の形 `backend/app/discord_gateway/ticket_channel_creator.py:90-107`（`_get_lead_state`、`LIMIT 1`） |
| 1b（別の道） | `tenant_NNN.lead_channels(platform='discord', external_id)` → `lead_id` → `leads.id` | 表の定義 `migrations/20260607_120000_create_lead_channels.sql:16-25`（`UNIQUE (platform, external_id)`）／引く既存の形 `backend/app/discord_gateway/dm_writer.py:112-121` |
| 2 | `tenant_NNN.leads.assigned_to`（INTEGER）= 担当者の `public.users.id` | 列 `migrations/003_add_phase1_tenant_tables.sql:92`（FK は付いていない）／同じ意味で使う既存 `backend/app/routers/meta_inbox.py:1022-1026`（`row.get("assigned_to") == current_user.id`）、`backend/app/services/lead_assign_notifier.py:20-31`（assigned_to_user_id を `staff.user_id` で引く） |
| 3（別の道） | `tenant_NNN.companies.lead_id` → `companies.sales_rep_id`（= `staff.id`）→ `staff.user_id` → `public.users.id` | `migrations/028_create_companies.sql:59,80,98,102`、`migrations/019_create_staff_tables.sql:35-38`（`staff.user_id` は `public.users(id)` への1対1）、`backend/app/routers/registration_tokens.py:189`（「companies.lead_id が SSOT」） |
| 4 | 宛先の `public.users.id` と同じ `tenant_id`（`users` は public の1表） | 定義は migrations に無く未確認。試験用の最小定義 `backend/tests/rls_bootstrap.py:235-246` に `tenant_id` 列あり |

既存の関数: 「Discord id → lead」を返す関数は2つあるが、どちらもその場の中の私用関数（`backend/app/discord_gateway/ticket_channel_creator.py:90` の `_get_lead_state`、`backend/app/discord_gateway/dm_writer.py` の lead_channels 引き）。**通知用に再利用できる公開関数は無い**（`backend/app/discord_gateway/outside_ticket_notice.py` 内に lead を引く処理も無い）。

### 1-2 途中で切れる場合（全部）

1. 書いた人の id が `leads.discord_user_id` にも `lead_channels` にも無い（未紐付け）。ticket_channel_creator は入室時に作る（`backend/app/discord_gateway/ticket_channel_creator.py:461-523`）が、入室前に別の場所で書く人はあり得る → 宛先なし。
2. `leads.discord_user_id` が同じテナント内で複数の lead に当たる。索引は一意でなく（`091…:35-39`）、既存の引きは `LIMIT 1` で選び方が決まっていない（`backend/app/discord_gateway/ticket_channel_creator.py:98-101`）。→ 宛先が複数／不定。
3. lead はあるが `leads.assigned_to` が NULL（担当なし）。列は NULL 許容（`003…:92`）。
4. `assigned_to` が指す `public.users` の行が無い／`is_active` でない（FK なし `003…:92`）。非活性の列は `backend/tests/rls_bootstrap.py:240` で存在確認のみ。実データの扱いは未確認。
5. `assigned_to` と `companies.sales_rep_id` の担当が食い違う（2つの道がある）。どちらを正とするかは既存コードでも場面で違う（`backend/app/routers/meta_inbox.py:1022` は assigned_to、`backend/app/routers/analytics.py:1336` は `COALESCE(c.sales_rep_id, l.assigned_to)`）。→ PO 決定「そのお客さんの担当者だけ」の定義に影響。**未決**。
6. `staff.user_id` が NULL（旧データ移行期は NULL 許容）。`019…:38`。この道（3）を使うと切れる。
7. 書いた人の id が担当者本人（staff 表／担当者の役割／管理者）。この場合は通知自体を出さない（下の 1-3）。
8. 別テナントに同じ Discord id の lead がある。通知は `tenant_id` 単位で呼ばれ（`backend/app/discord_gateway/ticket_channel_writer.py:193`）、lead の引きは `tenant_NNN` スキーマ（`_schema()`、`backend/app/discord_gateway/ticket_channel_writer.py:35-36`）内なので他社には当たらない。ただし search_path に頼る書き方は ADR-072 が禁じる（`docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`）。**スキーマ名つきで引くこと**。
9. Redis が無い／30分以内に同じ人が同じチャンネルへ書いた場合は、今の通知は出さない（`backend/app/discord_gateway/outside_ticket_notice.py:95-102`）。アプリ内の知らせを同じ関門に乗せるかは設計の判断（そのままだと「1分以内に数字が増える」を満たさない場合がある）。**未決**。
10. 呼び出し元は処理の最後に `commit` と `reset_tenant_context` が走る（`backend/app/discord_gateway/outside_ticket_notice.py:109-110`、`backend/app/routers/notifications.py:188-189`）。知らせの INSERT は `send_discord_notification` の**前**に同じセッションで行うこと。後だとコンテキストが戻って書けない恐れ。未確認（設計で要確認）。

### 1-3 担当者かどうかを判定する所

`backend/app/discord_gateway/outside_ticket_notice.py`
- 関数 `_is_staff`: `:30-59`
  - (a) staff 表の `discord_user_id` 一致: `:34-41`
  - (b) 担当者の役割（`public.tenant_discord_ticket_config.staff_role_id`）: `:42-56`
  - (c) 管理者権限: `:57-59`
- 呼び出し: `:88-90`（True なら `skipped_staff` で終わり）
- 部屋の親判定 `_parent_is_ticket_room`: `:62-75`、呼び出し `:92-94`
- 送る所 `send_discord_notification(...)`: `:110`（本文は `:106-108`。ここに書き込みの本文は入っていない）

---

## (2) 既存の知らせ・未読の仕組み

| 項目 | 内容 | 根拠 |
|---|---|---|
| notification_channels / notification_logs | **Discord Webhook 送信の設定と送信記録**（宛先は webhook_url）。人（user）単位の列は無い。アプリ内の知らせ一覧には使えない | `migrations/009_add_phase4_tenant_tables.sql:8-33`、使い方 `backend/app/routers/notifications.py:153-191` |
| 知らせの種類の列挙 | `NotificationEventType`（`discord_outside_ticket_post` を含む） | `backend/app/schemas/notification.py:8,21` |
| 担当割当の知らせ | Discord のみ。人への in-app 表は無い | `backend/app/services/lead_assign_notifier.py:1-60` |
| 受信箱の未読 | `meta_messages.seen_at IS NULL` の inbound 数（会話ごと） | `backend/app/routers/meta_inbox.py:943-945`、列 `migrations/041_extend_meta_messages.sql:25,46`。**部屋の外の書き込みは meta_messages に入らない**（保存は lead があるときだけ、`backend/app/discord_gateway/ticket_channel_writer.py:220-248`）ので、これには載らない |
| 画面側の未読数 | 会話一覧を取り直して数える | `frontend/src/components/DesktopShell.tsx:128-140`、`frontend/src/components/MobileShell.tsx:100-113` |
| 担当割当の「新規」バッジ | `leads.assignment_opened_at` | `migrations/20261015_090000_add_leads_assignment_opened_at.sql`、`backend/app/routers/meta_inbox.py:1020-1027` |
| web push | VAPID・購読の表あり。送り口は「知らない機械のログイン許可依頼」専用 | `backend/app/services/web_push.py:111-132,199`、表 `migrations/20261102_090000_add_user_push_subscriptions.sql:5-16`、呼び出し `backend/app/routers/auth.py:56,358` |
| 即時反映（ADR-1016） | SSE 1本。合図は topic と origin だけ。**人宛て（`rt:u:{user_id}`）が既にある**。書き込み API 成功時の自動合図は `WRITE_ROUTE_TOPICS`、裏処理は `publish_change(_sync)`、人宛ては `publish_user_change(_sync)` | `docs/adr/ADR-1016-realtime-change-signal-standard.md`（決定1-9・改訂2026-11-01）、`backend/app/realtime/publisher.py:21-22,69-110`、`backend/app/realtime/topics.py:15-24`、`hub.py:32,43-46` |
| 画面側の受け口 | `useRealtimeRefresh(topics, reload, {debounceMs})`、topic 名は `frontend/src/lib/realtime/topics.ts:2-6`（backend と試験で照合） | 使用例 `frontend/src/features/auth/LoginApprovalWatcher.tsx:12,82` |

結論:
- 「人ごとの未読つき知らせ一覧」の**表は無い**（新設が要る）。
- 「1分以内に数字が増える」の配線は、`publish_user_change` に新しい topic を足せば既存のSSEで足りる見込み（中身は topic のみで、画面は API を読み直す）。送り口は処理の中から直接呼ぶ型で、書き込みの口の自動合図にはしない（`backend/app/realtime/topics.py:21` の約束）。USER_TOPICS への追加は ADR-1016 の改訂が要る（`backend/app/auth/` に触れるかは未確認）。
- 現状のSSE 切断・再接続時の取りこぼしの扱いは未確認（読み直しで数を取り直す形なら吸収される）。

---

## (3) 上部の帯・部品・色

### 3-1 Shell（PC / Mobile、ADR-137）

| 項目 | 内容 | 根拠 |
|---|---|---|
| 切り替え | 767px 以下 = MobileShell、768px 以上 = DesktopShell。DOM ごと切り替える | `frontend/src/App.tsx:137-153`、`frontend/src/hooks/useIsMobile.ts:9` |
| PC | `app-shell` → 左サイドバー＋`app-body`。**上部の帯（`.app-topbar`）は今は使われていない**（CSS だけ残る）。右上は `position: fixed` の `.avatar-btn` | `components/DesktopShell.tsx:206-218,402-413`、`topbar.css:6-20,109-121` |
| Mobile | 上部の帯は2026-10-13 に削除済み。下部タブバーと「…」シート | `components/MobileShell.tsx:23-28,214,281` |
| 全画面に共通で置ける場所 | 両 Shell の `<RealtimeProvider>` 直下に `LoginApprovalWatcher` が既に置かれている（全画面で常駐する前例） | `frontend/src/components/DesktopShell.tsx:206-209`、`frontend/src/components/MobileShell.tsx:43-45` |
| 制約 | ページ右上ボタンは `headerAction` 経由。`position: fixed` で直接置くと `.avatar-btn` と同座標で重なり、`check:css-fixed-position` が自動で止める | `frontend/AGENTS.md`（PageLayout ルール節）。**鈴の置き場所は設計で決める**（PC は avatar-btn の左隣か、帯の復活かが選択肢。未決） |

### 3-2 使える部品（金型）

| 部品 | 状態 | 根拠 |
|---|---|---|
| Popover（トリガー・Portal・外側クリックで閉じる・placement） | **使える** | `frontend/src/components/Popover.tsx:1-40` |
| Badge（variant: danger 等、sm/md） | **使える**（数字つきの丸の「未読数」専用の形は無い。children で数字を渡せる） | `frontend/src/components/Badge.tsx:1-60` |
| 未読の丸の既存CSS | `.nav-unread-badge`（サイドバー用。token 参照） | `frontend/src/sidebar.css:285-292`、使用 `frontend/src/components/DesktopShell.tsx:265` |
| Bell の印 | **使える**。`frontend/src/constants/icons.tsx` に `Bell`（`hi(BellIcon)`）と `BellOutline` がある。ただし**公開名での export は未確認**（`reminder: Bell`、`automation: BellOutline` として使われている） | `frontend/src/constants/icons.tsx:115,157,243,375` |
| Drawer（右スライド、Esc・背景クリック・フォーカストラップ、`mobileInset`） | **使える**（スマホで一覧を出すのに向く） | `frontend/src/components/Drawer.tsx:1-50` |
| トースト | あり（`<Toaster />`） | `frontend/src/App.tsx:169` |
| 一覧の行の部品（知らせ1件の行） | 無い → 新しく要る | — |

### 3-3 色・寸法の約束

- 色・余白・z-index はデザイントークンのみ。直値は禁止（ADR-067、`frontend/AGENTS.md` の「CSS 変数／ダークモード」節）。色トークンを足すときは `:root` と `:root.force-dark` の両方。
- 使える既存トークン: `--accent`/`--accent-hover`/`--on-accent`（`topbar.css:116-134`）、`--color-error`/`-bg`/`-border`（`tokens.css:600-602`、ダーク側 `:648-650`）、`--bg-surface`・`--border`（`topbar.css:9-10`）、z-index `--z-topbar:100`・`--z-sidebar-overlay:210`・`--z-drawer:301`・`--z-toast:500`（`tokens.css:128-136`）。
- 文字は i18n（ja.json と en.json の同一キー、`t("key")`）。ハードコード日本語は ESLint が止める（ADR-027）。
- 部品の新設は `components/` の金型を先に確認（ADR-144、`docs/CC_UI_GOVERNANCE.md`）。画面を変えたら `frontend/tests-e2e/` の該当 spec も同じ PR で更新（`frontend/AGENTS.md`）。

---

## (4) 新しい表を置く場所・移行の決まり

| 項目 | 決まり | 根拠 |
|---|---|---|
| 各社の表（`tenant_NNN`）か public か | ADR-072: tenant スキーマの表は**スキーマ名つき**で書く。search_path に頼らない。`commit()` の後は `reset_tenant_context()` が必須 | `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`、`backend/AGENTS.md`「マルチテナント運用」 |
| 各社の表の作り方 | `DO $$ … pg_namespace` を走査する形で全テナントへ。`{schema}` プレースホルダは禁止 | `backend/AGENTS.md`「Migration 適用経路」、手本 `migrations/20260607_120000_create_lead_channels.sql:10-40` |
| public の表の例 | 人単位（`user_id` つき）で public に置いた最近の前例: `public.user_push_subscriptions`（RLS なし、`salesanchor_app` に GRANT） | `migrations/20261102_090000_add_user_push_subscriptions.sql:1-3,33-39` |
| S1 RLS | 監査 S1（機微11表）。public の表に会社別 RLS を付ける段階導入。型は「自社行のみ」「読取は全行・書込だけ止める」「付けない（理由を ADR に残す）」 | `docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md:20-40`、`docs/specs/tenant-rls/README.md:7-12`（各社スキーマの表は RLS の対象外＝スキーマで分離済み）、`docs/specs/tenant-rls/kgi.md:17-27` |
| 他社の知らせを出さない守り | 各社スキーマに置けば、スキーマの分離＋ `tenant_id` 条件の二重になる（通知側の前例: `backend/app/routers/notifications.py:158-163` が `tenant_id` を条件に入れる多重防御）。public に置くなら `tenant_id` 列と RLS（自社行のみ）が要る。**どちらにするかは設計判断で未決**。判断材料: 宛先の `users` は public（`users` に書込の RLS あり、ADR-1018 段階③ 便C）、知らせの元データ（lead）は各社スキーマ |
| 追加専用 | 列・表の追加は可。削除・リネーム・型変更は PO 確認 | `backend/AGENTS.md`「Migration は additive-only」 |
| 登録・検査 | ファイル名 migrations/YYYYMMDD_HHMMSS_name.sql の形。`.github/workflows/deploy.yml` に実行行を足す（登録しないと本番に当たらない）。migration-guard が検査。`.github/workflows/migration-test.yml` に最小定義が要る場合あり。AI用の閲覧ビューの分類 `migrations/20261024_100300_create_ai_cloud_views.sql:461-468`（`notification_channels/logs` は列ごと mask）も新しい表で確認が要る | `backend/AGENTS.md`「Migration 適用経路」 |
| PO 確認 | `migrations/`・`.github/workflows/deploy.yml` を含む PR は「GO #PR番号」まで main にマージしない（ADR-135/136、ADR-1003） | `AGENTS.md`「ブランチと作業場所」 |

---

## (5) 関係する ADR・資料

調べ方: `git grep -i -l "通知|notification|bell|未読" -- docs/adr`（結果は多数。うち今回に関係するものだけ）。

| ADR・資料 | 関係 |
|---|---|
| ADR-1016 即時反映の標準（`docs/adr/ADR-1016-realtime-change-signal-standard.md`） | 人宛て合図（改訂 2026-11-01）。「数字が1分以内に増える」の配線 |
| ADR-1055 新しい機械のログイン許可（`docs/adr/ADR-1055-new-device-login-approval.md`） | web push・人宛て合図・`user_push_subscriptions` の前例 |
| ADR-072 tenant スキーマ修飾（`docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`） | 表の置き場所・書き方 |
| ADR-1018 public 機微表の RLS 段階導入（`docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md`） | S1 RLS |
| ADR-137（Shell の DOM 切り替え） | 同番号が3本あり（`docs/adr/ADR-137-fedex-etd-paperless-trade.md`、`docs/adr/ADR-137-nginx-config-deploy-reliability.md`、`docs/adr/ADR-137-v-company-stats-ssot-filter.md`）、題名からは Shell の話に見えない（3本とも本文は未読）。コード上の ADR-137 参照は `frontend/src/App.tsx:139`、`frontend/src/components/DesktopShell.tsx:9`、`frontend/src/components/MobileShell.tsx:4`。ADR 本体は未確認 |
| ADR-027 i18n／ADR-067 デザイントークン／ADR-144 UI ガバナンス | 画面側の守り（`frontend/AGENTS.md`） |
| ADR-025 Meta 連携の運用堅牢化（`docs/adr/ADR-025_meta_integration_operational_hardening.md`） | 本文に「通知」。今回との直接の関係は未確認 |
| ADR-1003 GO 委譲／ADR-135・136 | migration を含む PR の手順 |
| 設計 `docs/handoff/discord-outside-ticket-notify/design.md`（担当者判定は §4-2、`:59-70`）・`docs/handoff/discord-outside-ticket-notify/recon.md` | 今ある Discord 通知の設計。通知先（notification_channels）は全社 0 件と記録（`docs/handoff/discord-outside-ticket-notify/design.md:43`、当時の値。**今の値は未確認**） |
| 参考 `docs/handoff/realtime-standard/`、`docs/handoff/notify-assign-routing/` | 即時反映・担当割当通知の資料 |

---

## まとめ: 既存で使えるもの／新しく要るもの

### 既存を使える

| 項目 | 根拠 |
|---|---|
| 部屋の外の書き込みを捕まえる入口 | `backend/app/discord_gateway/outside_ticket_notice.py:78-112`、呼び出し `backend/app/discord_gateway/ticket_channel_writer.py:193` |
| 担当者を除く判定 | `backend/app/discord_gateway/outside_ticket_notice.py:30-59` |
| Discord id → lead の引き方（形） | `backend/app/discord_gateway/ticket_channel_creator.py:90-107`、`backend/app/discord_gateway/dm_writer.py:112-121` |
| lead → 担当者（`assigned_to`＝users.id） | `003…:92`、`backend/app/routers/meta_inbox.py:1022` |
| 人宛ての即時反映（SSE `rt:u:`） | `backend/app/realtime/publisher.py:97-110`、`backend/app/realtime/topics.py:15-24`、`frontend/src/features/auth/LoginApprovalWatcher.tsx:82` |
| 全画面に常駐する差し込み場所 | `frontend/src/components/DesktopShell.tsx:206-209`、`frontend/src/components/MobileShell.tsx:43-45` |
| Popover／Badge／Drawer／Bell の印／トークン | 3-2・3-3 |
| テナント文脈の作法（ADR-072） | `backend/app/services/lead_assign_notifier.py:20-31` |

### 新しく要る

1. 知らせの表（人ごと・未読つき・種類・リンク先・作成日時。置き場所は各社スキーマか public かを決める）＋ migration＋ `.github/workflows/deploy.yml` 登録＋ AI閲覧ビューの分類。
2. 「Discord id → lead → 担当者」を返す公開関数（1-2 の切れる場合の扱いを含める）。
3. API: 一覧（新しい順 最大50件）・未読数・既読にする（押したら未読が1減る）。呼べる人は本人だけ。
4. 新しい topic の追加（ADR-1016 の改訂、`backend/app/realtime/topics.py`／`frontend/src/lib/realtime/topics.ts` の両方）。
5. 画面: 鈴＋未読数（両 Shell）、一覧（Popover か Drawer）、知らせ1件の行、i18n（ja/en）、e2e spec。
6. 書き込み元の jump_url を保存するか、保存せず組み立て直すかの決め（本文・id は保存しない方針との整合）。

### PO・設計に確認が要る点（未決）

- 「担当者」を `leads.assigned_to` で決めるか、`companies.sales_rep_id` も含めるか（1-2 の5）。
- 担当なし・未紐付け・複数当たりのときの扱い（出さない／管理者に出す、など）。
- 知らせを今の30分の重複抑えに合わせるか（1-2 の9）。
- 鈴を置く場所（PC は avatar-btn との重なりに注意）。

DONE
