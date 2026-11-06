# recon: 閲覧者の契約手続きと請求書 — 現状の記録

> この文書は何か（専門用語なしの1行）:
> 手続きの段階と請求書を足す前に、今のプログラムと本番がどうなっているかを行番号つきで記録したもの。

- 親（設計仕様書）: [docs/specs/viewer-contract-invoicing/README.md](../../specs/viewer-contract-invoicing/README.md)
- 設計: [design.md](./design.md)
- 基準: origin/main 9b96f0764（2026-11-05）。生出力は /tmp/CC報告ファイル/contract-status/ の recon-1105*.txt。

## 1. 既存 ADR の検索

- `git grep -i -l "viewer_accounts\|閲覧者" docs/adr/` の該当: ADR-021、ADR-1003、ADR-1009、ADR-1019。
- docs/adr/FEATURE-INDEX.md は 閲覧・viewer・ドライブ・drive の語で該当なし。「請求」の行（docs/adr/FEATURE-INDEX.md:14）が ADR-101 を指し、「決済・入金確認・PayPal・Wise」の行（同 :15）が ADR-104 を指す（2026-11-06 訂正。行番号は第3回の審査の指摘で再訂正。前の版は「請求書」の語で該当なしと書いていた）。
- 今回変える決まり: 閲覧者の名簿の90日の決まり（docs/handoff/gas-viewer-fresh-fast/review-fable.md:172 の Q7 に答えた docs/handoff/gas-viewer-fresh-fast/design.md:523〜:524。backend/app/tasks/maintenance.py:202 が参照）。実装は §4。ADR-1019 には Q7 も90日も無い（`grep -n "Q7\|90日" docs/adr/ADR-1019*.md` が0件。2026-11-06）。

## 2. 状態の決まりと、状態を読む場所

- 状態の一覧: migrations/20261016_150000_add_viewer_accounts.sql:21（ck_viewer_accounts_status）。
- 履歴の操作の一覧: migrations/20261016_150000_add_viewer_accounts.sql:91（activate・suspend・unsuspend・extend・start_trial）。
- ログイン後の判定: backend/app/auth/viewer_dependencies.py:86・:88・:89。一覧に無い状態は viewer_pending で拒否（同 :93〜:94）。
- ログインの判定: backend/app/routers/viewer.py:190・:195・:202。
- パスワード再発行を送る状態: backend/app/routers/viewer.py:65・:329。
- Discord の受付を通す状態: backend/app/discord_gateway/viewer_trial.py:318。
- 申込コードの再発行を通す状態: backend/app/services/viewer_admin.py:381。
- 本契約にする・延長の前提: backend/app/services/viewer_admin.py:231・:255。
- 停止の解除は、最後の停止記録の前の状態へ戻す: backend/app/services/viewer_admin.py:240 付近（from_status を読む）。新しい状態でも値の追加だけで動く。
- 配信は本契約のみ: backend/app/services/tcg_distribution_svc.py:725（`va.status <> 'active'` は not_contracted）。
- 期限前日の面談案内はお試しのみ: backend/app/discord_gateway/viewer_interview_notice.py:57。
- 閲覧ページの停止の扱い: frontend/src/pages/viewer/ViewerApp.tsx:52・:60、frontend/src/pages/viewer/LoginView.tsx:24。
- 管理画面: frontend/src/pages/super-admin/ViewerAccountsPage.tsx:94（左メニュー）・:441（行のボタン）。ファイルは 922 行。上限は frontend/scripts/check-page-size.js:7 の 1000 行で、便2 の審査で 1043 行が差し戻しになった（release-viewer-billing-form-bin2 の台帳）。

## 3. フォーム

- 鍵の期限: backend/app/services/viewer_billing_form.py:20（BILLING_FORM_TTL 7日）。
- 本契約のみ: 同 :97・:138・:167。
- 送る口: backend/app/routers/super_admin_viewers.py:423〜。鍵を消して作り直す。メールは BackgroundTasks（結果を画面が知らない）。
- 送ったことの記録は無い。鍵の行は作り直しで消える（同 :431 以降と viewer_billing_form.py）。段階の判定に使える記録が今は無い。

## 4. 自動削除と公開ポリシー

- 90日の定数: backend/app/tasks/maintenance.py:33。7日の定数: 同 :34。
- お試し: 同 :215。停止: 同 :220〜:225。申込のまま: 同 :231。
- 公開ポリシー: lp/src/pages/privacy.astro:215・:216（90日で消す、請求先も一緒に消す）。利用目的: 同 :177 に請求書の発行はあるが、再登録の防止は無い。委託先の表: 同 :247 に Google はあるが、用途にドライブは無い。
- 本番の件数（2026-11-05 ai_ro）: お試し 21件（うち期限切れ 19件）・本契約 3件。最も古いお試し期限は 2026-09-20 00:14 UTC。今の決まりでは 2026-12-19 に最初の削除が起きる。

## 5. 商材・プラン・税率

- 本番に商材・プラン・契約の表と列は無い（ai_ro の情報スキーマを検索）。
- `sa_products`・`sa_plans`・`tax_rates`・`viewer_invoices` の名前は migrations と backend/app に無い（git grep・該当なし）。
- 税率の保存場所は backend/app と migrations に無い。

## 6. PDF とメール

- B2B の PDF: backend/app/services/invoice_renderer.py:1〜:21（輸出向け。Description・HS コード固定）。登録番号・振込先・消費税の欄は無い。
- 日本語フォントの登録: 同 :49〜。フォントが無いと Helvetica へ落ちる。Docker には IPA ゴシックが入る（backend/Dockerfile:14）。
- B2B の番号: backend/app/routers/invoices.py:263（IN-0001-01 の形）。無効化: 同 :580（番号の頭に [VOID]）。
- 閲覧者の請求先のメール: backend/app/services/auth_mail.py:138〜:152。本文だけで添付は無い。失敗はログだけ。
- 請求先の表の項目: migrations/20261105_120000_create_viewer_billing_profiles.sql:8〜:20（invoice_email は任意）。
- 文面の台帳: backend/app/services/viewer_message_templates.py:43〜:54。

## 7. 会社情報

- 読み出し: backend/app/routers/invoices.py:109〜:128（`{tenant_schema}.tenant_profile`）。
- 画面の権限: backend/app/routers/tenant_profile.py:55・:88（tenant.profile.view／edit）。
- 項目: backend/app/schemas/tenant_profile.py:15〜:38。振込先・登録番号は無い。
- 隠す設定は道で2つある（第4回の審査で訂正）。相談係の道（ai_cloud・ai_reader_cloud）は列の分類表 migrations/20261024_100300_create_ai_cloud_views.sql:573〜:575 で伏せる。Mac の AI の道（ai_ro）は列名の拒否の一覧 migrations/20261017_130100_create_ai_ro_views.sql:23 に当たる列を除くだけで、分類表を読まない（同ファイルに column_class・mask は0件）。
- 本番の会社: テスト株式会社・権限確認用・HIGH LIFE JPN・テストテナント2・Sales Anchor App Review の5件（2026-11-05 ai_ro）。実在の事業者名は HIGH LIFE JPN だけに見えるが、発行元の法人は PO に未確認。
- 会社情報の中身は ai_ro で隠れていて読めない。未確認。
- 請求書に載る項目は 会社名・住所・電話・メール・サイトの5つ（backend/app/services/invoice_renderer.py:509〜:513）。印影の URL は渡していない。
- 会社情報を読む他の処理: PO の PDF（backend/app/services/po_renderer.py:9）、送り状の確認（backend/app/services/label_validation.py:85）。
- 会社情報の表は会社ごとのスキーマに置く（migrations/069_create_tenant_profile.sql:70〜:71）。新しい会社の既定行は backend/app/services/tenant.py:1163〜:1164 が入れる（069 の注記は同ファイル :88。第6回の審査で訂正）。
- 会社別のデータの置き場の決まり: ADR-142 の Context と Decision 1〜3。作成処理は backend/app/services/tenant.py の _TENANT_TABLES_SQL（:195）・_RLS_ENABLE_SQL（:1221）・_RLS_POLICY_SQL（:1274）。手本は own_inventory（:1198・:1266・:1338）。
- 文脈: set_tenant_context は backend/app/auth/dependencies.py:277、表名は同 :409 の tenant_table_ref。最高管理者の口に呼び出しは無い。裏の処理の呼び出しは backend/app/services/google_webhook.py:255、backend/app/discord_gateway/dm_writer.py:94。
- 文脈は接続を返す前に消える。backend/app/database.py:60〜:61 の get_db の finally が clear_tenant_context（backend/app/auth/dependencies.py:361、ADR-131）を呼ぶ。裏の処理は get_db を通らないので自分で呼ぶ（同 :361 の説明）（2026-11-06 訂正。前の版は RESET ALL・DISCARD・pool_reset の grep だけで「無い」と書いていた）。
- 運営の書き込みの文脈（第5回の審査で訂正）: 写す先例は set_operator_context／reset_operator_context（backend/app/auth/dependencies.py:429・:446。使う口は backend/app/routers/super_admin_tenants.py:50・:93、backend/app/routers/super_admin_suppliers.py:69・:73）。backend/app/routers/buyback_prices.py:392・:864 は生の `SET LOCAL`、backend/app/tasks/fx_rate_updater.py:70 は `SET` を直接流す形で、どちらも写さない。会社の口では空にする（backend/app/auth/dependencies.py:254〜:256）。
- 差出人を読む処理の全件（2026-11-06。origin/main を取り込んだ後の HEAD で grep。生出力 /tmp/CC報告ファイル/contract-status/ssot-verify-1106.txt・ssot-verify-1106b.txt・reader-lang-1106.txt。評価役の挙げた場所を設計担当が自分で照合した）:
  - B2B の請求書と見積書: backend/app/routers/invoices.py:109〜:128（company_name・company_name_en・address・phone・email・website を読む）。呼び出し :829・:875・:1007。PDF は backend/app/services/invoice_renderer.py:509〜:513・:579〜:583。見出しは英語（同 :267）、輸出の項目を載せる（同 :11）。
  - 発注書: backend/app/services/po_renderer.py:253〜:273。住所は1行で描く。見出しは「発注書 / Purchase Order」。
  - FedEx の申請書と申請メール: backend/app/services/label_validation.py:82〜:103（company_name・company_name_en・address・phone・email を読む）。呼び出し backend/app/routers/shipping.py:780・:815。英語の会社名を先に使う（label_validation.py:127・:159）。
  - backend/app でこの他に tenant_profile を読む処理は無い（会社情報の口 backend/app/routers/tenant_profile.py と作成処理 backend/app/services/tenant.py:1147〜:1164 を除く）。
- 表の形: backend/app/services/tenant.py:1147〜:1161。tenant_id 列は無い。address は TEXT 1欄、phone は VARCHAR(50)。
- 画面: frontend/src/pages/admin/TenantProfilePage.tsx（263行）。文字の欄は TextFieldControl（同 :26）。管理センターの左メニュー「ビジネス設定」（frontend/src/locales/ja.json:433）に「発行者情報」として既にある（frontend/src/pages/management-center/ManagementCenterPage.tsx:80。道は frontend/src/App.tsx:402）。名前は frontend/src/locales/ja.json:277・:2061。
- 試験で tenant_profile を使う箇所: backend/tests の7ファイル・51か所（test_tenant_profile.py 16、test_inventory_sprint8_migrations.py 13 ほか）。
- 発注書の写しの列（company_name_snapshot・contact_info_snapshot。migrations/063_tenant_rbac_extensions.sql:63・:67）は backend/app に書く処理が無い（grep 0件）。

## 8. Google ドライブ

- 接続は会社に1つ: migrations/20260606_010000_add_google_drive_config.sql:18。folder_id 列: 同 :23。書き込む処理は無い（backend/app/routers/integrations.py:202 と backend/app/services/google_drive_oauth.py:333 は読むだけ）。
- 権限: backend/app/services/google_drive_oauth.py:49（drive.file）。保存: 同 :373。URL からフォルダ番号を取り出す: 同 :98。
- 既存の呼び出し: backend/app/routers/shipping.py:511（失敗はログで続行）。
- テスト保存の口: backend/app/routers/integrations.py:243〜:263。PO が貼ったフォルダの URL から番号を取り、そこへ保存する（同 :254・:263）。
- 本番: HIGH LIFE JPN に1件。接続 2026-06-08。トークンの更新記録なし。送り状 0件。今も保存できるかは、2026-11-06 の PO のテスト保存で「指定したフォルダに保存できた」と確かめた（design §7-1）。
- 訂正（第4回の審査）: folder_id を伏せるのは相談係の道の分類表（migrations/20261024_100300_create_ai_cloud_views.sql:274）で、ai_ro の拒否の一覧には当たらない。前回の「フォルダ未設定」をどちらの道で読んだかは記録が無く未確認。このため本番の値は未確認のまま扱い、§3-8 の分岐は PO の連携ページでの確認とテスト保存で決める。書く処理がコードに無いことだけが事実。
- この表は会社別の RLS が FORCE で付いている（migrations/20261016_010000_add_google_config_rls.sql:11〜:15）。会社の文脈なしの処理からは読めない。
- Google 公式: 6か月使わないトークンは無効。同意画面が Testing だと7日で失効。drive.file は、アプリが作ったファイルか、利用者がアプリに渡したファイルを扱える。人が作ったフォルダへ保存できるかは明記なし。実際に保存できたことは 2026-11-06 の PO のテスト保存で確かめた（design §7-1）。同意画面が Testing か本番公開かは未確認。

## 9. 画面の部品

- メニュー: frontend/src/components/ContextMenu.tsx。三点アイコン: NAV_ICONS.more（frontend/src/pages/inbox/InboxThreadHeaderMobile.tsx:175〜:187 は生の button）。
- 三点ボタン単体の金型は frontend/src/components に無い（ファイル名と more の grep）。docs/CC_UI_GOVERNANCE.md:13〜:14 により PO の許可を得て登録してから使う。
- 入力: TextField・Select・Checkbox・Modal は金型あり（docs/CC_UI_GOVERNANCE.md:10・:25、frontend/src/components/Modal.tsx）。

## 10. 外部の決まりの確認

- 消費税: 国税庁 タックスアンサー6303（標準10%）。端数処理は1請求書・税率ごとに1回。
- 請求書の写しの保存: 7年（インボイス Q&A 問79）。写しは記載事項が確認できる程度の記録でよい（同 問78）。docs/handoff/viewer-customer-sheet/recon.md:73 の確認済み記録。
- 発行元の国内用: インボイスの登録なし（2026-11-05 PO「2」。PO の回答で、公表サイトの照合はしていない）。
- 登録番号の形は T＋数字13桁で、適格請求書発行事業者の番号。適格請求書を交付できるのは登録した事業者だけ。登録は任意（国税庁 公表サイト「登録番号とは」、タックスアンサー6498）。課税事業者であることと、インボイスの登録は別の事柄。発行元が課税事業者かは未確認。
- Wise（公式ヘルプ・2026-11-05 確認）: 支払いリンク・QR・Wisetag で依頼できる。円の入金用の口座情報は本人名義の口座からのみ。JPY の受取は Swift の一覧で、対象の登録国に日本の記載なし。
- PayPal（日本の公式ヘルプ help293・2026-11-05 確認）: 相手のメール等か PayPal.Me で支払える。友達への送金はビジネスのアカウントで受け取れない。
- 個人情報: 個人情報保護委員会ガイドライン通則編。3-4-1（使う必要がなくなったら遅滞なく消す努力義務）、3-1-1（目的の具体的な特定）、3-1-2（変更は関連のある範囲で、通知か公表）、3-1-3（目的外は原則本人の同意）。再登録防止で名簿を持つ場合の直接の記述は、読めた範囲（ページ前半）に無い。未確認。
- Context7 は月間上限で利用不可。上記は公式ページを直接確認した。

## 12. 第2回の審査のあとに確かめたこと（2026-11-06。生出力 /tmp/CC報告ファイル/contract-status/fix-facts-1106.txt・fix-facts-1106b.txt・fix-facts-1106c.txt）

- 住所を5つに分けた先例: 取引先 public.suppliers の postal_code・prefecture・city・address1・address2（migrations/20260603_010000_add_suppliers_line_and_address.sql:21〜:25）。
- 国の一覧: public.countries（migrations/20260621_010000_create_countries_master.sql:6〜:13）と画面の frontend/src/constants/countries.ts。両者を照合する仕組みは .github/workflows と scripts に無い（grep で該当なし）。
- 都道府県の一覧は backend/app・frontend/src/constants・migrations に無い。frontend/src に「北海道」の語は0件。
- 会社の電話の決まり: backend/app/schemas/base.py:16〜:23（`+\d{6,15}`・`\d{10,15}`・`0\d{9,10}`、区切り記号は外す）。ADR-126 §6。
- 会社ごとの表から public への外部キーの先例: backend/app/services/tenant.py:518（role_permissions → public.permissions）、:605（staff → public.users）。
- 変更の履歴: 会社ごとの audit_logs（tenant.py:484〜:494、old_data・new_data は JSONB）と record_audit_log（backend/app/services/audit.py:277）。
- 部品の金型: frontend/src/components/ に TextField・Select・Tabs・Toggle・Checkbox・Modal・CountryCombobox がある。
- 会社情報の口: GET・PUT /api/v1/admin/tenant-profile（backend/app/routers/tenant_profile.py:52〜:53・:85〜:86、backend/app/main.py:478）。閲覧者の運営の口: /super-admin/viewers/…（backend/app/routers/super_admin_viewers.py:347〜:374）。
- 他テーマの境界: docs/specs/profile-account-settings/README.md（オーナー専用の設定はプロフィールのページに統合）、docs/specs/quote-invoice/ideal-state.md（B2B の支払い方法は PayPal と Wise）。

## 13. 書類ごとに国内向けか海外向けかを選ぶ形の確認（2026-11-06。生出力 /tmp/CC報告ファイル/contract-status/dropdown-recon-1106.txt〜dropdown-recon4-1106.txt）

- 見積書と請求書の PDF は、出すたびにその時点の会社情報から作る。backend/app/routers/invoices.py:829 前後（請求書 PDF）・:875 前後（PayPal の写し PDF）・:1007 前後（見積書 PDF）が毎回 `_fetch_tenant_profile` を読む。発行元の写しの列は無い。
- 見積書から請求書を作る口は backend/app/routers/invoices.py:235〜:332。見積書の値を INSERT で引き継ぐ形（company_id・contact_id・currency 等）。直接作る口は同 :333。下書きを直す口は同 :446。
- quotes と invoices は会社ごとのスキーマの表（backend/app/services/tenant.py:798・:864）。
- 見積書と請求書の作る画面は、選択の部品として SelectControl を既に使う（frontend/src/pages/quote-create/QuoteCreatePage.tsx:24・:159、frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:20・:303）。
- 発注書の画面は 2026-10-11 の commit 7a2f39c20 で消えた。frontend/src/pages に purchase-orders は無い。口（backend/app/routers/purchase_orders.py:354・:385・:495）だけが残る。
- FedEx の申請書の画面（frontend/src/pages/integrations/FedexLabelValidationTab.tsx:57）は、origin/main のどのファイルからも読み込まれていない。口（backend/app/routers/shipping.py:780・:815）だけが残る。
- 取引先の住所の国は company_addresses.country_code CHAR(2)（migrations/030_create_company_contact_subtables.sql:55）。NOT NULL が無く、空を許す。仕入先（suppliers）に国の列は無い（tenant.py:968 の表定義）。
- 本番で国が空の取引先が何件あるかは、まだ数えていない（reader 鍵が要る）。

## 14. 取引先の国で国内向けか海外向けかを自動で決める形の確認（2026-11-06〜07。生出力 /tmp/CC報告ファイル/contract-status/reader-country-1106.txt・update-paths-1106.txt・update-paths2-1106.txt・tp-readers-1106.txt）

- 請求書が請求先の写しを作る処理は backend/app/routers/invoices.py:66 の _fetch_address_snapshot。company_addresses の address_type と is_default = TRUE（:84〜:86）で1行を読み、country_code を "country" として返す（:104 付近）。呼び出しは :268〜:269（見積書から作る :241）・:367〜:368（直接作る :339）・:1003〜:1004（見積書の PDF :972）の6か所。
- 見積書を作る口は backend/app/routers/quotes.py:146。今は請求先の住所を読まない。
- 見積書と請求書の取引先は作った後に直せない。直す口の項目に company_id が無い（backend/app/schemas/quote.py:54〜:61、backend/app/schemas/invoice.py:54〜:59）。
- 取引先の国の入れ方: frontend/src/pages/companies/CompaniesPage.tsx:550 は2文字の制限だけ（大文字にしない）。CompanyAddressModal.tsx:143〜:144 は大文字にして2文字か空かを確かめる。
- tenant_profile を読む場所は backend/app と frontend/src で57行（git grep origin/main）。差出人として読むのは invoices.py・po_renderer.py・label_validation.py の3つ。他は会社情報の口・表の作成・最高管理者の DB の表の一覧だけ。
- 本番の件数（2026-11-06。読み取り専用の鍵で件数だけを数えた。中身は出していない）:

| 会社 | 取引先 | 見積書 | 請求書 | 既定の請求先なし | 請求先の国が空 | JP | JP 以外 | 形の崩れ |
|---|---|---|---|---|---|---|---|---|
| 主な会社 | 51 | 0 | 0 | 2 | 1 | 0 | 48 | 0 |
| 他の会社1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| 他の会社2〜4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

- このため、主な会社の51社のうち48社は自動で決まり、すべて海外向けになる。3社は決められない。
- §13 の「本番で国が空の取引先が何件あるかは、まだ数えていない」は、この節で数えた。
