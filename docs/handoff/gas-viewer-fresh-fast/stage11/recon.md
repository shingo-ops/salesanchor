# recon: テンプレートページ設計のための現状（origin/main 基準・読み取りのみ）
注: パスは全て origin/main の内容。行番号は `git show origin/main:<path>` の行。生の抜粋ファイルは同じフォルダ（desk.txt mob.txt viewers.txt vbt.txt bt.txt components.txt ja.json）。

## 1. ヘッダー
- 【重要な事実】DesktopShell に「上部の帯」は無い。frontend/src/components/DesktopShell.tsx:14-15 の構成コメントは「sidebar-panel + app-body(topbar...)」だが、実際の描画は左サイドバー(:206-394)・本文(:397-402)・右上固定の丸いアバターボタン(:405-412)・アバターを押すと出るユーザーメニュー(:424-481)。topbar の描画は見つからない（検索語: topbar, header → :430 user-drawer-header のみ）。
- MobileShell.tsx:23-27: 「2026-10-13 上部のページ名バー（56px）を削除した（PO 指定）」。下部タブバー(:16-20 受信箱/在庫表/受注管理/「…」)と「…」シート(:12-15, :216)のみ。
- 「ヘッダーのボタン」の実体は各ページの PageLayout の headerAction（frontend/src/components/PageLayout.tsx:8 `headerAction?: React.ReactNode`、:47 で描画）。ボタン部品は frontend/src/components/HeaderButton.tsx（:2 「ページヘッダーアクション用ボタン SSoT (ADR-069)」、variant ghost/primary/secondary/icon :26,:32）。使用例のコメントに `<HeaderButton variant="ghost">{t("nav.templates")}</HeaderButton>` あり(:8)。実使用は SupplierDetailDrawer.tsx:421,449,468 のみ（検索語 HeaderButton）。
- 既存の「テンプレート」ボタン：frontend/src/pages/inbox/InboxPage.tsx:81-91 `<div className="page-header-actions">` 内 `<Button variant="ghost" size="md" onClick={() => navigate("/templates")}>{t("nav.templates")}</Button>`、続けて FAQ ボタン(:92-100)。:79 `showHeaderActions = !isMobile`（スマホでは出さない）。スマホの受信箱は InboxThreadHeaderMobile.tsx:89 の「…」内 `label: t("nav.templates")`。
- 既存の遷移先 /templates は未実装：frontend/src/App.tsx:281-289 `<Route path="/templates" element={<ComingSoonPage title={t("templates.title")} description={t("templates.description")} />}>`。ja.json:2205 `templates: {title:"テンプレート管理", description:"メール・メッセージテンプレート管理"}`。DesktopShell.tsx:385 の「その他」アコーディオンは activePaths=["/templates"] だが moreItems は空(:200)。
- super admin 出し分け：frontend/src/hooks/useSuperAdmin.ts:19-42（GET /me/permissions の is_super_admin。失敗時 false :32）。DesktopShell.tsx:111 で取得。サイドバーの SaaS 管理者専用メニュー：DesktopShell.tsx:193-198 `saasAdminItems`（isSuperAdmin のときだけ。analysis-rules / buyback-prices / fx-rate / viewers）、描画 :363-379（区切り線＋NavLink、アイコン NAV_ICONS.saasAdmin）。MobileShell.tsx:165-192 も isSuperAdmin のときだけ同4項目（resolveItem）。
- ルート側の保護：App.tsx:342 `/super-admin/viewers`。ページ内ガード ViewerAccountsPage.tsx:276-283（!isSuperAdmin なら `superAdmin.accessDenied`）。API 側は `dependencies=[Depends(require_super_admin)]`（backend/app/routers/super_admin_viewers.py:131,140）。

## 2. 行クリックでスライドの前例と金型
- 金型の登録先：docs/CC_UI_GOVERNANCE.md:9-15（frontend/src/components/ を先に確認、無ければ止めて PO 許可 :14、金型作法 Xxx.tsx+Xxx.css+Xxx.stories.tsx :15）。禁止事項 :19-29（生select/生input/自作タブ/色直値）。
- frontend/src/components/ の主な金型：Drawer.tsx(:34 `Drawer({open,onClose,title,footer,size:"default"|"wide"})`)、Sheet.tsx(下から出る)、DataTable.tsx、Textarea.tsx、TextField.tsx、Button.tsx、HeaderButton.tsx、Tabs.tsx、SubMenu.tsx、Modal.tsx、ConfirmModal.tsx、Badge.tsx、EmptyState.tsx、Stack.tsx、Callout.tsx、ListRow.tsx、ContentToolbar.tsx、PageLayout.tsx（全一覧は ls で取得済み）。
- 表の金型：DataTable.tsx — `DataTableColumn`(:38, key/header/renderCell :67)、`DataTableProps`(:73) に rowKey(:77)・selectable(:86)・onRowClick(:100, 「Enter/Space キー操作可・セル内ボタンで非発火」:12)。
- 行クリック前例①（閲覧者管理）：ViewerAccountsPage.tsx:410-416 `<DataTable columns data rowKey onRowClick={row => setDetail(row)} emptyState=.../>`、:421-439 `<Drawer open={detail !== null} onClose title footer={<Button variant="primary" ...保存/>}>`、中は :441 `form-grid`/`form-row` に TextField(:443)。コピーは :187-195 `navigator.clipboard.writeText` ＋ copiedKey で2秒「コピーしました」表示。ページは `PageLayout navKey subtitleKey noScroll headerAction` と `hub-shell`＋SubMenu(:386-393)。
- 行クリック前例②（在庫表）：frontend/src/features/inventory/InventoryRowDrawer.tsx:121,172 `<Drawer open size="wide" title=...>`、Tabs 使用(:12,:203)。他の Drawer 利用：features/supplier-master/SupplierDetailDrawer.tsx:285、pages/bots/BotsPage.tsx:271、pages/staff/StaffPage.tsx:307 ほか。
- 複数行編集の金型：ある。frontend/src/components/Textarea.tsx — `Textarea({label,error,size:"sm"|"md"|"lg"})`(:62付近)、`TextareaControl`(:45)、variant "standard"|"karte"|"embedded"|"composer"|"schedule"|"product-edit"(:32)、textStyle "normal"|"code"(:35)。

## 3. 文面の今の置き場所
### backend/app/discord_gateway/viewer_bot_texts.py（全159行）
- 定数（行：名前＝用途／差し込み）
  - :12-15 VIEWER_CUSTOM_ID_PREFIX / OPEN_BUTTON_CUSTOM_ID / CODE_MODAL_CUSTOM_ID / CODE_INPUT_CUSTOM_ID ＝ボタン等の識別子（文面ではない）
  - :17 RECEPTION_MESSAGE ＝受付の部屋のボタン上の文（差し込みなし）
  - :20 OPEN_BUTTON_LABEL ／ :21 CODE_MODAL_TITLE ／ :22 CODE_INPUT_LABEL ＝ボタン名・小窓の題・入力欄名
  - :24 WRONG_SERVER ／ :25 CODE_INVALID ／ :26 TOO_MANY_ATTEMPTS ／ :27 TRY_LATER ／ :28 DISCORD_ALREADY_LINKED ＝エラー応答（差し込みなし）
  - :29 YOUR_ROOM ＝{channel_id}
  - :30-36 ROOM_WELCOME ＝部屋に送る歓迎文 {email} {password}（URL 直書き :33）
  - :37-42 ROOM_RECREATED ＝部屋作り直し文 {email}
  - :64 ROOM_TOPIC ＝部屋の説明 {viewer_id}（viewer_trial.py:34 の正規表現と形を合わせる必要あり）
  - :68 SIGNUP_URL ／ :69-75 SIGNUP_REQUEST ＝申込のお願い {signup_url}（手で送る）
  - :76-81 REISSUE_NOTICE ／ :82-86 REISSUE_NOTICE_NO_INVITE ＝申込コード作り直し案内 {line_name} {code} {expires} {invite_url}
  - :89 NOTICE_EXTENDED {until_date} ／ :90 NOTICE_ACTIVATED ／ :91 NOTICE_SUSPENDED ＝操作直後の自動お知らせ
  - :94-98 INTERVIEW_REQUEST ＝期限前日の面談依頼 {expires_date}
- 関数：external_browser_url(:103) / format_jst_date(:121) / format_jst_datetime(:127) / signup_request_text(:133) / reissue_notice_text(:138) / interview_request_text(:157) / reception_message_payload(:45)
### backend/app/discord_gateway/bot_texts.py（全83行・顧客用チケット・英語既定。:3-4）
- :20-23 DEFAULT_WELCOME_TEMPLATE／:26-29 TICKET_BUTTON_MESSAGE・LABEL・CUSTOM_ID・EMOJI／:33-37 CATEGORY_DM・CATEGORY_STOCK_MEMBER・CATEGORY_STOCK_LARGE・CATEGORY_DM_LEGACY（Discord カテゴリ名）／:40-43 GUILD_ONLY・GUILD_NOT_REGISTERED・TICKET_NOT_CONFIGURED・TICKET_CREATE_FAILED／:46-50 CHANNEL_INVITE_TEMPLATE {scale_label} {channel_id}／:52-56 CHANNEL_INVITE_SCALE_LABELS／関数 channel_invite_message(:59) ticket_button_payload(:65)。
### welcome_template（DB に持っている）
- 表 public.tenant_discord_ticket_config（migrations/20260602_120000_add_discord_ticket_config.sql:5-13、テナント単位 tenant_id PK、列 welcome_template TEXT NOT NULL DEFAULT ... :10）。
- API：backend/app/routers/discord_ticket_config.py GET(:97-125) / PUT(:133-208)、既定値は bot_texts.DEFAULT_WELCOME_TEMPLATE(:60,:73)。
- 画面あり：frontend/src/pages/admin/DiscordConfigPage.tsx（welcome_template :36,:135,:231 の state で編集して PUT）。gateway は ticket_channel_creator.py:49-54 で DB から読み、:455 `config.get("welcome_template") or _DEFAULT_WELCOME`、:503 で送る。
### ほかに「お客様に送る文面」を DB に持つ前例
- 上記 welcome_template のみ該当。`git grep -niE template origin/main -- backend/app migrations` で CREATE TABLE に当たったのは public.link_templates（migrations/20260604_090000_create_link_templates.sql:13、channel PK・url_pattern・required_ids・notes。リンクの雛形で、お客様向け文面ではない。super admin CRUD: backend/app/routers/super_admin_link_templates.py:1-10, main.py:602）と tcg_note_master.label_template（migrations/20260919_020000_master_ssot_public_tables.sql:245、商品ラベル雛形）。メール/メッセージ文面の表は見つからない（検索語: template, welcome）。

## 4. 呼び出し元
- viewer_bot_texts：
  - client.py:31 import、:263 `custom_id.startswith(viewer_bot_texts.VIEWER_CUSTOM_ID_PREFIX)` → viewer_trial.handle_interaction(:265)
  - discord_gateway/viewer_trial.py:25（`as T`）：T.CODE_INPUT_LABEL/CUSTOM_ID :69-70, CODE_MODAL_TITLE :77, OPEN_BUTTON_CUSTOM_ID :92, WRONG_SERVER :102,:111, TRY_LATER :108,:172,:188,:203,:244,:258,:304,:311,:377, ROOM_TOPIC :126,:449, YOUR_ROOM :183,:209,:384, ROOM_RECREATED :206, CODE_INVALID :239,:254,:278,:297, TOO_MANY_ATTEMPTS :249, DISCORD_ALREADY_LINKED :372, ROOM_WELCOME :381
  - discord_gateway/viewer_interview_notice.py:15,:80（interview_request_text。client.py:188,:195 の 1 時間ループから）
  - viewer_discord_cli.py:15,:107（OPEN_BUTTON_CUSTOM_ID。受付の部屋へのボタン投稿）
  - routers/super_admin_viewers.py:29,:143（signup_request_text）,:258（reissue_notice_text）
  - services/viewer_room_notice.py:12,:50-56（NOTICE_EXTENDED/ACTIVATED/SUSPENDED）。呼び出し側 super_admin_viewers.py:31 と viewer_admin_cli.py:11
- bot_texts：client.py:28,:274,:289,:301,:317,:332／ticket_channel_creator.py:29,:38／routers/discord_auto_setup.py:48,:249,:263,:418,:610-638,:732,:767／discord_channel_invite.py:33,:140／discord_ticket_config.py:39,:60,:73,:261。
- gateway と backend の両方から使われる：はい。discord-gateway コンテナ（docker-compose.yml:350-352 `python -m app.discord_gateway.main`、`build: ./backend` で同一イメージ・DATABASE_URL と REDIS_URL を持つ docs/handoff/.../design.md:815）は ROOM_WELCOME・ROOM_RECREATED・エラー応答・INTERVIEW_REQUEST を使い、backend は SIGNUP_REQUEST・REISSUE_NOTICE・NOTICE_* を使う。DB から文面を読む場合は両方から読める（gateway は public.tenant_discord_ticket_config を DB から読む前例 ticket_channel_creator.py:49-54）。

## 5. DB にデータを入れるルール
- ADR-155（docs/adr/ADR-155-product-master-ssot-csv-app.md:26-28 決定1・2）: マスタの値の操作(INSERT/UPDATE/DELETE)は migration 禁止、更新はCSV取込とアプリ画面の2経路のみ。保護対象は商品マスタ4表(:29-33)で、migration-guard チェック7(:32)で CI がブロック。
- ADR-1007（docs/adr/ADR-1007-migration-structure-only-run-once.md:14,:31-36 決定1）: migration は構造だけ。値の投入・上書きは migration から外す。値の変更はアプリ画面/CSV、アプリのコード、PO合意の1回限り(DRY-RUN→COMMIT、docs/handoff/<topic>/ に記録)。
- CLAUDE.md(/Users/tanizawashingo/salesanchor/CLAUDE.md)「データ手動 DB INSERT の原則禁止（ADR-025）」。
- 前例：ADR-1019 設計 D6 は「migration では表だけを作り、1行の登録は専用スクリプトで行う（migration でデータを入れない）」（docs/handoff/gas-viewer-fresh-fast/design.md:277）。link_templates の seed も無効化済み（migrations/20260604_090000_create_link_templates.sql:22-25）。
- 範囲：viewer_accounts は public（migrations/20261016_150000_add_viewer_accounts.sql:6、冒頭コメント :2 「RLS は付けない: テナントを持たない public の表」）。viewer_discord_config も public（migrations/20261017_100000_add_viewer_discord_config.sql:2）。閲覧者管理 API は require_super_admin のみ（super_admin_viewers.py:131）= 全体共通・super admin 専用。welcome_template はテナント別（tenant_id PK）。

## 6. 既存 ADR
- FEATURE-INDEX.md（docs/adr/FEATURE-INDEX.md）に「テンプレート」「template」で当たる行は ADR-101（:14 見積/請求のテンプレSSOT）と ADR-135（:39 PRテンプレ）のみ。閲覧者文面のテンプレートは見つからない（検索語: テンプレ, template）。
- `git grep -il "テンプレート\|template" origin/main -- docs/adr` は14ファイル。内容的に関係しそうなのは ADR-101(見積・請求の雛形)のみ。他は ADR-081/011/135/039/035/144/123/116/107/034/029/015/013/1016 で、workflow・PR テンプレ等で本件と無関係に見える（各ファイルの該当数は出力済み。個別の中身は精読していない＝未確認）。
- ADR-1019（docs/adr/ADR-1019-inventory-viewer-separate-accounts.md）には「段10」「文面」の語が見つからない。段10 の設計は docs/handoff/gas-viewer-fresh-fast/design.md:798-（## 段10）。文面の正本を viewer_bot_texts.py に置く決定：design.md:808（現状）, :820（「正本は viewer_bot_texts.py に置く」）, :838（「文面は全部 viewer_bot_texts.py に置く（1か所）。管理画面は API が返す出来上がりの文を表示・コピーするだけで、フロントに文面を持たない（二重管理を作らない）。前例：顧客用 welcome_template を API が返す」）。viewer_bot_texts.py:1「SSOT」。
- DB に移す＝この決定の変更になる（設計時に ADR-1019 段10 への追記/改訂が必要）。

## 7. i18n（frontend/src/locales/ja.json）
- "nav": ja.json:206〜（nav.templates="テンプレート"、nav.superAdminViewers="閲覧者管理" :264）。
- "templates": ja.json:2205（title「テンプレート管理」, description「メール・メッセージテンプレート管理」）— 既存の仮ページ用。
- "superAdmin": ja.json:2446〜、直下キー: title, subtitle, accessDenied, tabs, knowledge, supplierQuality, diagnostics, suppliersAdmin, conditionsAdmin, viewers(:2667), fxRate, inbound, phaseSwitch, inventoryOffers, masters。superAdmin.viewers 内は subtitle, colEmail, colLineName, colStatus ..., detailTitle, copy, copied など（ページ用のキー群の前例）。
- ja.json と en.json は同一キー必須（CLAUDE.md i18n 強制 ADR-027）。ページ名は PageLayout navKey=`nav.xxx`（PageLayout.tsx:27）。
