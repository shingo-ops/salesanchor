---
mode: handoff
---

# design: 閲覧者の契約手続きの段階と請求書

> この文書は何か（専門用語なしの1行）:
> お試しから本契約までの間に手続きの段階を足し、商材とプラン、請求書の発行、ドライブ保存、名簿を3年残す決まりをどう作るかの設計。

- 親（設計仕様書）: [docs/specs/viewer-contract-invoicing/README.md](../../specs/viewer-contract-invoicing/README.md)
- 現状の記録: [recon.md](./recon.md)
- 決めごとの控え: [decisions-draft.md](./decisions-draft.md)
- 関係 ADR: [ADR-1061](../../adr/ADR-1061-viewer-contract-stage-and-invoicing.md)（草案）、ADR-1019（Q7 を改訂）、ADR-101（B2B 請求書。別の表にする）、ADR-144・ADR-067（金型とトークン）、ADR-027（i18n）、ADR-135・ADR-136（危険な変更の GO）
- 状態: **設計案作成済み・第2回の審査（Opus の審査役と Fable）は REVISE で、指摘を 2026-11-06 に反映済み・再審査待ち（[review.md](./review.md)）・PO 未承認・実装未着手**

## 1. 目的（PO の言葉から）

- 成約から入金までの間も在庫表を見てもらい、入金で本契約にする。
- 手続きの抜けを画面で防ぐ。
- 請求書を発行し、記録を自動で残す。
- お試しまで進んだ人の再登録を防ぐ。

## 2. 対象と対象外

対象:
- 新しい状態、段階のボタン、三点メニュー、見られる期限の自動延長。
- 商材・プラン・契約の表、税率の表と画面。
- 閲覧者の請求書（国内）の発行、PDF、メール添付、ドライブ保存、再発行、入金確認。
- 国内用・海外用の請求書情報の登録（§3-4）。
- 名簿を3年残す変更と公開ポリシーの書き換え。

対象外（次の機会）:
- 海外用フォルダの画面とトレカの請求書の保存（入れ物の列だけ今回足す）。
- 海外の請求書の発行。今の B2B の請求書は会社情報を読むまま変えない。海外用の請求書情報は、登録できるが今回はどの請求書にも出ない。
- 商材とプランの登録画面。今回は最初の1件を移行で入れ、足すときは行の追加で行う。**PO の確認項目（§7-2）**。
- サブスクの自動請求、オンライン決済、軽減税率。
- 今の本契約 3件の契約記録の作成。
- 請求書の記録の自動削除。最初の期限が来るのは7年以上先。

## 3. 変更前と変更後

### 3-1. 状態

| 状態 | 表示 | 在庫表 | 配信 |
|---|---|---|---|
| trial | お試し | 期限まで | なし |
| contracting（新） | 契約手続き中 | 期限まで | なし |
| active | 本契約 | 期限なし | あり |

- 見られる期限は、今の trial_expires_at の1列を使う。別の列を作らない（1つの情報は1か所）。列の説明を「お試しと契約手続き中の、見られる期限」に直す。
- 期限切れのログインは、新しい理由 viewer_contract_expired で止める。文言は「閲覧期限が過ぎています。担当者にご連絡ください。」（ja・en）。
- 配信（backend/app/services/tcg_distribution_svc.py:725）は変えない。
- 面談案内（viewer_interview_notice.py:57）は変えない。

状態を読む次の場所へ contracting を足す。漏れると新しい状態の人が止まる。
- backend/app/auth/viewer_dependencies.py:86〜:94
- backend/app/routers/viewer.py:65・:190・:195
- backend/app/discord_gateway/viewer_trial.py:318
- backend/app/services/viewer_admin.py:255・:381
- frontend/src/pages/viewer/ViewerApp.tsx:52・:60、LoginView.tsx:24
- frontend/src/pages/super-admin/ViewerAccountsPage.tsx:94 と状態の表示名
- フォーム: backend/app/services/viewer_billing_form.py:97・:138・:167。許す状態を1つの定数にまとめ、contracting と active にする。
- カードで全件 grep を指示する（§9）。

### 3-2. 期限の自動延長

- フォーム送信: 期限 = max(今の期限, 鍵の期限)。鍵の期限は3日（viewer_billing_form.py:20 を変更）。
- 請求書の発行と再発行: 期限 = max(今の期限, 支払期限の日本時間 23:59:59)。
- 短くはしない。PO の「延長」を、短くしないと読んだ。お試しが10日残る人に3日期限のフォームを送っても、10日は残る。
- 入金確認: 本契約へ。期限は判定に使われなくなる。
- 履歴は viewer_status_changes に残す。actor は操作した人。
- **起きる空白（PO に見せる）**: 「契約に進む」を押しただけでは期限は動かない。お試しが切れている人は、フォームを送るまで見られない。フォームの期限を過ぎて請求書がまだなら、発行するまで見られない。手作業の延長で埋められる。
- 部屋への延長のお知らせは送らない。フォームと請求書の案内に期限が書いてあるため。

### 3-3. 操作の流れ

| 今の段階 | 行に出すもの | 三点 |
|---|---|---|
| お試し | 契約に進む・延長 | なし |
| 手続き中・フォーム未送信 | フォームを送る | なし |
| 手続き中・送信済み・未発行 | 請求書を作成 | フォームを再送信 |
| 手続き中・発行済み | 入金確認 | フォームを再送信・請求書を再発行 |

- 段階は、履歴と請求書の行から決める。段階の列は作らない。
  - 「フォーム送信済み」は viewer_status_changes の新しい操作 form_sent の有無。
  - 「発行済み」は有効な請求書（status = issued）の有無。
- 請求先が未入力のときは「請求書を作成」を押せなくし、「フォームの入力待ち」と出す。宛先が無いと請求書を作れないため。
- 手続き中の人にも「延長」を出す。支払いが少し遅れる人のための手作業の逃げ道。PO の言葉には無い追加で、§7-2 で確認する。
- 履歴の操作に start_contract・form_sent・invoice_issued・confirm_payment を足す（migrations/20261016_150000_add_viewer_accounts.sql:91 の決まりを変更）。
- 切り替えの便で、お試しから本契約へ直接移す道を、画面と API とコマンド（backend/app/viewer_admin_cli.py:13）から外す。
- 新しい部品は ViewerAccountsPage.tsx に足さず、別ファイルにする（922 行で上限が近い）。
- 三点ボタンは金型 `MoreMenuButton`（NAV_ICONS.more と ContextMenu を組む）を登録して使う。金型の新設は PO の許可が要る（§7-2）。

### 3-4. 表（請求書情報の3表は会社ごとのスキーマ、他は public・金額は円の整数）

**sa_products**（商材）
- id、code（一意）、name、seller_tenant_id（発行元の会社。tenants を参照）、default_payment_days（既定の支払日数。既定 3）、is_active、created_at、updated_at。

**sa_plans**（プラン）
- id、product_id、code（商材内で一意）、name、billing_type（one_time／subscription）、billing_interval（month／year。one_time は NULL）、unit_price_jpy（税抜）、is_active、created_at、updated_at。

**sa_plan_features**（プランに含む機能）
- plan_id、feature_key。主キーは2列の組。今回は inventory_view・sheet_distribution。

**sa_contracts**（契約）
- id、plan_id、viewer_account_id（ON DELETE SET NULL）、tenant_id（将来の導入支援用。今回は常に NULL）、status（in_progress／active／cancelled）、started_at、activated_at、created_at、updated_at。
- 同じ閲覧者・同じプランの in_progress と active は1件まで（部分一意索引）。
- 「契約に進む」で in_progress を作る。

**tax_rates**（税率）
- id、rate_percent（NUMERIC(5,2)）、effective_from（DATE・一意）、created_by_user_id、created_at。
- 最初の行は 10.00・2019-10-01。
- 請求書は発行日に有効な行を読み、率を写す。後から行を足しても、発行済みは変わらない。
- 画面は最高管理者のみ。行の追加だけで、過去の行は直せない（打ち間違いは未来の適用日の行に限り消せる）。

**viewer_invoices**（請求書）
- id、invoice_number（一意）、contract_id（SET NULL）、viewer_account_id（SET NULL）、status（issued／paid／voided）、replaces_invoice_id（再発行元）。
- issued_at、due_date、paid_at、paid_confirmed_by_user_id、voided_at。
- subtotal_jpy、discount_total_jpy、taxable_jpy、tax_rate_percent、tax_amount_jpy、total_jpy。
- bill_to_snapshot、issuer_snapshot（JSONB。発行時点の写し）。issuer_snapshot に選んだ振込先1件と登録番号を含む。
- mail_to、mail_sent_at、mail_error、drive_file_id、drive_web_link、drive_saved_at、drive_error。
- created_by_user_id、created_at、updated_at。
- 有効な請求書（issued）は同じ契約に1件まで（部分一意索引）。
- 番号は年ごとの採番の表 viewer_invoice_number_seq（year INTEGER 主キー、last_number INTEGER NOT NULL）の行を `SELECT … FOR UPDATE` で進める。その年の行が無ければ INSERT … ON CONFLICT DO NOTHING で作ってから進める。同時に発行しても重ならない。

**tenant_invoice_profiles**（請求書情報の発行元。国内の請求書用と海外の請求書用。PO 2026-11-05「海外と国内で請求書情報を別途登録できるように」「2」、2026-11-06「1、インボイス登録の有無と番号を会社に1つだけ持つ」）
- 国内用と海外用は1つの表に置く（PO 2026-11-06「1」）。region（domestic／overseas）は「どちらの請求書に載せる行か」だけを表す。住所と電話の決まりは region ではなく country_code で分ける。
- 列: id、tenant_id（NOT NULL。RLS の判定に使う。own_inventory と同じ形）、region、issuer_name、country_code、postal_code、prefecture_code、state_region、city、address1、address2、phone、email、website、updated_by_user_id、created_at、updated_at。
- tenant_id と region の組で一意。会社に最大2行。
- 列名は取引先の住所の先例（postal_code・prefecture・city・address1・address2。migrations/20260603_010000_add_suppliers_line_and_address.sql:21〜:25）に合わせる。PO の5欄（郵便番号・都道府県・市区町村・住所1・住所2）と同じ並びのため。都道府県は一覧への参照にするので prefecture_code とする。country_code は取引先の住所の表（migrations/030_create_company_contact_subtables.sql:46〜:58）と public.countries（migrations/20260621_010000_create_countries_master.sql:21〜:28）に合わせて ISO 2文字。
- 項目は今の請求書に載る5つ（recon §7）を細かくしたもの。登録の有無と番号は次の表に置く。振込先はその次の表に置く。

住所と電話の決まり（CHECK で止める。画面も同じ決まりで止める）:
- country_code は必須で public.countries を参照する（外部キー。会社ごとの表から public への参照は先例あり: backend/app/services/tenant.py:516・:603）。
- country_code が 'JP' のとき（PO 2026-11-05「郵便番号、都道府県、市区町村、住所1、住所2で、電話番号はむらが出ないようにハイフン禁止」）:
  - postal_code は `^[0-9]{7}$`。prefecture_code は必須。state_region は NULL。
  - phone は `^[0-9]{10,11}$`。桁は今の請求先フォーム（backend/app/services/viewer_billing_form.py:23〜:24）と同じ。
- country_code が 'JP' 以外のとき:
  - postal_code は任意（`^[0-9A-Za-z -]{1,10}$` または NULL）。prefecture_code は NULL。state_region は任意の自由記入（州・地域）。
  - phone は国番号から始まる数字だけで `^[0-9]{6,15}$`。桁は会社の電話の決まり（ADR-126 §6、backend/app/schemas/base.py:16〜:23 の `+\d{6,15}`）と同じ。画面とPDFでは頭に「+」を付けて見せる。保存する値には付けない。
- どちらも city と address1 は必須、address2 は任意。
- 電話のハイフンと空白は、自動で外さずに止める（PO「ハイフン禁止」）。今の請求先フォームは外して受け取る（viewer_billing_form.py:32〜:34）。こちらは発行元を会社の人が登録する欄で、入れた値と保存する値を同じにするため、わざと違う形にする。画面は赤い注意を出して保存させない。
- PDF では「〒」と郵便番号の3桁目の後のハイフンを、表示のときだけ付ける。

都道府県の一覧（1か所に置く。案A を取る）:
- public.prefectures（code CHAR(2) 主キー＝JIS X 0401 の 01〜47、name_ja、name_en、sort_order）を新しく作り、移行で47行を入れる。prefecture_code はこの表への外部キー。
- 画面の選択肢は API でこの表から読む。画面のコードに都道府県名を書かない。
- 案B（画面の定数ファイル＋DB の CHECK に47個を並べる）は取らない。同じ一覧が2か所になり、揃っているかを確かめる仕組みが今のリポジトリに無いため（国の一覧 frontend/src/constants/countries.ts と public.countries の照合も .github/workflows・scripts に無い。2026-11-06 grep）。

発行元の選び方:
- 閲覧者の請求書は region が domestic の行だけを読む。会社情報（tenant_profile）へ読みに行かない。自動で写さない。
- 国内用の行の country_code は 'JP' と決まってはいない。日本以外の住所でも国内用に使える（決まりは住所の国で効く）。

**tenant_invoice_registration**（インボイス登録の有無と番号。会社に1行。PO 2026-11-06「インボイス登録の有無と番号を会社に1つだけ持つ」）
- 列: id、tenant_id（NOT NULL・一意）、is_invoice_registered（BOOLEAN NOT NULL DEFAULT false）、registration_number、updated_by_user_id、created_at、updated_at。
- 登録の有無（PO 2026-11-05「課税事業者登録の有無もDBに登録してフロントでも編集できるようにして、登録している場合はTから始まる13桁の番号も登録するようにする、無の場合は入力欄をグレーアウトさせて入力させないイメージ」）: 有なら registration_number は必須で `^T[0-9]{13}$`。無なら NULL。DB の CHECK でも止める。画面は無のとき番号の欄を disabled にする。
- 国内用と海外用の請求書の両方がこの1行を読む。2026-11-05 の「全部の項目を分ける」（PO「2」）のうち、この2項目だけは 2026-11-06 の PO の答えで会社に1つに改めた。
- 今の HIGH LIFE JPN は無（2026-11-05 PO「2」）。行が無いときは無として扱う。
- PDF の登録番号の行は、有のときだけ出す。

2つの表に共通の決まり:
- **SSOT の境界**: 会社名・住所などは会社情報にもある。PO がこのリスクを聞いたうえで分ける形を選んだ（2026-11-05「2」）。請求書情報はこの2表が正本、会社情報は PO の PDF・送り状・今の B2B の請求書の正本。片方を直してももう片方は変わらない。画面の説明文にそう書く。B2B の請求書をこの表へ移すかは海外の請求書の設計で決める。
- 置き場は会社ごとのスキーマ（tenant_NNN.tenant_invoice_profiles、tenant_NNN.tenant_invoice_registration）。会社別のデータはそこに置く決まり（ADR-142 の Context）で、会社情報（tenant_profile）も同じ場所にある。
- ADR-142 の Decision 2 と 3 に従い、次を同じ変更で揃える。既存の全会社へ足す移行と、backend/app/services/tenant.py の _TENANT_TABLES_SQL（:195）・_RLS_ENABLE_SQL（:1206）・_RLS_POLICY_SQL（:1259）の3か所。ポリシー名は `<表名>_tenant_isolation`、条件は own_inventory と同じ（tenant.py:1323〜:1325）。権限は一括付与に任せる。既定の行は入れない。発行元の行が無ければ発行を止める。
- 発行の処理は発行元の会社の番号で set_tenant_context を張り、表名は tenant_table_ref で書く（backend/app/auth/dependencies.py:363・:495）。commit の後は reset する（同 :425、ADR-072）。最高管理者の口には前例が無い（super_admin の口の grep で該当なし）。会社の番号を引数で受けて文脈を張る処理は裏の処理にある（backend/app/services/google_webhook.py:255、backend/app/discord_gateway/dm_writer.py:94）ので、この形を発行の処理に写す。
- 文脈は接続を返す前に消える（backend/app/database.py:60〜:61 の get_db が clear_tenant_context を呼ぶ。backend/app/auth/dependencies.py:447。ADR-131）。裏の処理は get_db を通らないので、処理の終わりで clear_tenant_context を呼ぶ（同 :447 の説明にある BackgroundTasks の形）。新しい public の表の SQL は public. を付けて書く。
- 画面は今の会社情報のページ（frontend/src/pages/admin/TenantProfilePage.tsx）に「請求書情報」の区切りを足す。会社に1つの「インボイス登録」の欄を上に置き、その下で国内用と海外用を Tabs で切り替える。テナントオーナー専用の設定はこのページに置く決まり（docs/specs/profile-account-settings/README.md の境界）に合う。権限は今の tenant.profile.view／edit（同ページ :8〜:9）。部品は §3-4a。

**tenant_invoice_payment_methods**（振込先。PO 2026-11-05「振込先は複数登録できるようにできる？初めにプルアダウンでWise、PayPal、銀行口座で選択するプルダウンを表示させておいて、選択した値によって入力欄が変化する仕組み」「登録ページで登録請求書発行時はプルダウンで選択をイメージしている」）
- 振込先の正本はこの表だけ。1つの振込先を1行とする。region（domestic／overseas）でどちらの請求書の選択肢に出すかを分ける。置き場、RLS、作成処理への反映は tenant_invoice_profiles と同じ（ポリシー名 tenant_invoice_payment_methods_tenant_isolation）。
- id、tenant_id（NOT NULL）、region（domestic／overseas）、method_type（bank／wise／paypal）、display_name（プルダウンに出す名前）、account_holder、bank_name、bank_branch、bank_account_type、bank_account_number、swift_code、bank_address、wise_currency、wise_payment_link、wise_account_note、paypal_email、paypal_me_url、sort_order、updated_by_user_id、created_at、updated_at。
- CHECK で種類ごとの必須を止める。bank: display_name・account_holder・bank_name・bank_branch・bank_account_type・bank_account_number。wise: display_name・account_holder・wise_currency（3文字の通貨コード）・wise_payment_link。paypal: display_name・paypal_email。他の種類の列は NULL。
- 登録時に種類を変えると、他の種類の入力値は保存しない。
- 消せる。発行済みの請求書は写しを持つので変わらない。
- 請求書から振込先の行へ外部キーは張らない。理由: 請求書は public の1つの表で、振込先は会社ごとに別のスキーマの表にある。外部キーは参照先の表を1つに決める必要があり、会社の数だけある表を1本の外部キーで指せない。会社ごとの表から public を指す向きの外部キーは先例がある（tenant.py:516・:603）が、今回は逆向き。発行時の写し（issuer_snapshot）に振込先の全項目と行の id を残す。
- 変更の履歴: 振込先と2つの請求書情報の表を足す・直す・消すたびに、会社ごとの audit_logs（tenant.py:484〜:494）へ record_audit_log（backend/app/services/audit.py:277）で1行残す。old_data と new_data には全項目を入れ、口座番号だけは下4桁にする（全桁を履歴に広げないため）。画面に履歴の一覧は今回作らない。
- 編集できる人: tenant.profile.edit を持つ人（請求書情報と同じ）。オーナーだけに絞るかは PO に確かめる（§7-2）。
- Wise の項目の根拠: 利用者は支払いリンク・QR・Wisetag で依頼できる。Wise を持たない人がリンクを開くと、金額・通貨・送金先の銀行情報が見える（Wise ヘルプ How do I request money?）。口座情報は通貨で項目が違うので、任意の自由記入（wise_account_note）にする。
- 画面の注意書き: Wise の円の入金用の口座情報は本人名義の口座からの入金専用で、お客さんの振込先に使えない（Wise ヘルプ Paying to our Wise JPY pay-in account）。
- PayPal の項目の根拠: 支払う人は相手のメールアドレス等か PayPal.Me リンクで送れる（PayPal 日本のヘルプ help293）。ビジネスのアカウントは友達への送金を受け取れない（同）。
- 発行元の Wise の画面の確認（PO 2026-11-05）: 日本円の支払いリンクを作れる。口座は通貨ごとに分かれている。このため Wise は通貨ごとに1行で登録する。
- 未確認: お客さんがそのリンクから払った日本円が実際に入金されるか。公式の通貨の案内で JPY は Swift のみの受取に載り、対象の登録国に日本が無い（Wise ヘルプ 2897238）。テストの支払いで確かめる。
- 手数料が引かれて入金額が請求額より少ない場合の扱いは設計しない。入金確認は今の設計のまま入金日だけを記録する。

**viewer_invoice_lines**（明細）
- id、invoice_id（CASCADE）、line_type（item／discount）、description、amount_jpy、sort_order。ADR-101 の2表に分ける形に合わせる。

既存の表への追加:
- tenant_google_drive_config: overseas_folder_id（今回は使わない）。既存の folder_id を国内用と定める（どこからも書かれていないことを確認済み。recon §8）。

ai_ro: 新しい個人情報の列と、tenant_invoice_profiles・tenant_invoice_registration・tenant_invoice_payment_methods の全項目（決まった値しか入らない列を除く）は隠す設定にする。migrations/20261024_100300_create_ai_cloud_views.sql:300・:573 と同じ形（会社ごとの表は 'tenant_*' の行で足す）。個人情報の表の一覧（migrations/20261031_210000_create_ops_case.sql:102）にも足す。

最初の行（移行で入れる）:
- 商材「在庫解析ツール」、プラン「在庫解析の閲覧とシート配信」、買い切り、200,000円（税抜）、機能2つ、既定の支払日数 3。発行元の会社は HIGH LIFE JPN（2026-11-05 PO「1」）。

RLS（ADR-1018 の段階①の型）: 新しい public の表（sa_products・sa_plans・sa_plan_features・sa_contracts・tax_rates・viewer_invoices・viewer_invoice_lines・viewer_invoice_number_seq・prefectures）は、読むのは全行可、書くのは `app.is_operator='true'` のときだけにする。ENABLE と FORCE を付ける（ADR-1018 Decision 3）。
- 理由: どの表も書くのは運営（最高管理者の画面と、その発行に続く裏の処理）だけ。閲覧者や会社の人が書く経路は無い。請求書は金額と宛先を持ち、アプリの書き間違いを DB で止める価値がある。
- 閲覧者の名簿と請求先（migrations/20261105_120000_create_viewer_billing_profiles.sql:2）は RLS を付けていない。こちらは閲覧者本人のフォームから書くので型が違う。
- 書く処理は `SET LOCAL app.is_operator = 'true'` を張る（先例 backend/app/routers/buyback_prices.py:392、backend/app/routers/super_admin_suppliers.py:61）。裏の処理は自分で張る（先例 backend/app/tasks/fx_rate_updater.py:70）。
- RLS で弾かれた UPDATE は誤りにならず0行になる。書く処理は更新した行数が1でなければ誤りとして止める。
- 権限は migrations/20261105_120000_create_viewer_billing_profiles.sql の GRANT と同じ形で salesanchor_app に渡す。

### 3-4a. 画面の部品（金型）

| 使う場所 | 金型（frontend/src/components/） |
|---|---|
| 文字の欄（会社名・郵便番号・市区町村・住所・電話・メール・サイト・番号・口座の項目） | TextField.tsx |
| 国 | CountryCombobox.tsx（frontend/src/pages/register/ にある同名の部品ではなく components の方） |
| 都道府県・振込先の種類・作成画面のプランと振込先・口座の種類 | Select.tsx |
| 国内用と海外用の切り替え | Tabs.tsx |
| インボイス登録の有無 | Toggle.tsx |
| デフォルトとして保存 | Checkbox.tsx |
| 請求書の作成・入金確認・再発行 | Modal.tsx |
| 行の三点ボタン | 新設の MoreMenuButton（§3-3・§7-2） |

- 新しい画面の部品は別ファイルに置く: InvoiceProfileSection.tsx（請求書情報の区切り）、InvoiceRegistrationField.tsx、PaymentMethodList.tsx、PaymentMethodForm.tsx、TaxRatesPage.tsx、ViewerInvoiceCreateModal.tsx、ViewerPaymentConfirmModal.tsx。
- 色と寸法はトークンだけ（ADR-067）。文字はすべて t()（ADR-027）。生の select・input・自作タブは使わない（ADR-144）。

### 3-4b. API の約束（ADR-113 の「契約・API 仕様」）

会社の人（今の会社情報と同じ口。/api/v1 の下。権限 tenant.profile.view で読む・tenant.profile.edit で書く）:

| 方法 | 道 | 中身 |
|---|---|---|
| GET | /admin/invoice-profiles | 国内用と海外用の行（無い方は null）と、インボイス登録の1行 |
| PUT | /admin/invoice-profiles/{region} | 片方の行を丸ごと保存。決まり違いは 422 と欄ごとの理由 |
| PUT | /admin/invoice-registration | 登録の有無と番号。無のとき番号を送っても NULL で保存 |
| GET | /admin/invoice-payment-methods?region= | 振込先の一覧（sort_order 順） |
| POST | /admin/invoice-payment-methods | 1件足す。種類ごとの必須が無いと 422 |
| PUT | /admin/invoice-payment-methods/{id} | 1件直す |
| DELETE | /admin/invoice-payment-methods/{id} | 1件消す |
| GET | /prefectures | 都道府県の一覧（ログイン済みなら誰でも） |

運営（最高管理者。今の閲覧者の口 backend/app/routers/super_admin_viewers.py と同じ /super-admin/viewers の下）:

| 方法 | 道 | 中身 |
|---|---|---|
| POST | /super-admin/viewers/{viewer_id}/contract | 契約に進む（手続き中の契約を作る） |
| GET | /super-admin/viewers/{viewer_id}/invoice-draft | 作成画面の材料（プラン・宛先・発行元の振込先の一覧・既定の期限） |
| POST | /super-admin/viewers/{viewer_id}/invoices | 発行。plan_id・payment_method_id・値引きの行・due_date・save_default を受ける |
| POST | /super-admin/viewer-invoices/{id}/reissue | 再発行 |
| POST | /super-admin/viewer-invoices/{id}/resend-mail | もう一度送る |
| POST | /super-admin/viewer-invoices/{id}/resave-drive | もう一度保存 |
| POST | /super-admin/viewer-invoices/{id}/confirm-payment | 入金確認（paid_at を受ける） |
| GET・POST | /super-admin/tax-rates | 税率の一覧と追加 |
| DELETE | /super-admin/tax-rates/{id} | 未来の適用日の行だけ消せる。それ以外は 409 |

- 誤りの形は今の口と同じ（detail に理由）。発行で発行元の行・振込先・文面が足りないときは 409 と足りない項目の一覧を返す。

### 3-4c. 他のテーマとの境界

- 見積もりと B2B の請求書（docs/specs/quote-invoice/ideal-state.md、ADR-101）: B2B は会社ごとの invoices の表のまま触らない。そちらにある PayPal と Wise の支払い方法（同 ideal-state.md の支払い方法の段落）とこの振込先の表を1つにするかは、海外の請求書の設計で決める。それまでは閲覧者の請求書だけがこの表を読む。
- 会社のプロフィールとアカウント設定（docs/specs/profile-account-settings/README.md の境界）: テナントオーナー専用の設定はプロフィールのページに統合する決まりに合わせ、会社情報のページに区切りを足す。独立した画面は作らない。

### 3-5. 請求書の作成と計算

作成画面（Modal）の項目:
- プラン（Select）、宛先（請求先の表示のみ）、振込先（Select。国内用に登録した行から1つ選ぶ。必須。既定の選択は持たない。Wise は通貨が JPY の行だけを出す）、値引きの行（名目と金額。行を足せる）、支払期限（既定は発行日＋既定日数。直せる）、□デフォルトとして保存、計算結果。
- 振込先が1件も無いときは発行できない。登録ページへの案内を出す。
- PDF の振込先の欄は選んだ種類の項目だけを出す。Wise と PayPal はリンクとメールを文字で載せる。

計算:
1. 小計 = プランの税抜金額。
2. 値引き合計 = 値引きの行の合計。小計を超えると作れない。
3. 課税対象 = 小計 − 値引き合計。
4. 税額 = 課税対象 × 税率。1円未満は切り捨て。請求書ごと・税率ごとに1回。
5. 合計 = 課税対象 + 税額。

- 「初月無料」は、名目を「初月無料」とした値引きの行で登録する。今の買い切りプランでは月の概念が無いので、専用の計算は作らない。
- %指定の値引きは作らない。金額で入れる。
- 番号は `VI-2026-0001` の形（年・発行順の連番）。B2B の番号とは別の並び。
- 「デフォルトとして保存」は、チェックして発行したときだけ sa_products.default_payment_days を更新する。発行済みの期限は変えない。

### 3-6. 発行の順番と失敗のとき

同じ処理の中で確定する（まとめて commit）:
1. 請求書と明細の行を作る。発行時点の宛先・発行元・税率を写す。
2. 見られる期限を延ばす。履歴を残す。

commit の後、裏で順に行う:
3. PDF を作る。
4. メールで添付して送る。結果を mail_sent_at か mail_error に残す。
5. ドライブへ保存する。結果を drive_* に残す。

- 必須項目（会社名・住所。登録が有のときは登録番号も。振込先は作成画面で1つ選んだ行）が国内用の請求書情報に無いときは、発行を止めて、足りない項目を画面に出す。
- フォントが日本語で登録できないときは発行を止める。Helvetica に落とすと文字が化けるため。新しい PDF の処理では代わりのフォントを使わない。
- メールの失敗: 行に「送信失敗」と「もう一度送る」を出す。SMTP 未設定も失敗として扱う。今のフォームのメールのように黙って捨てない。
- ドライブの失敗: 行に「未保存」と「もう一度保存」を出す。発行とメールは止めない。
- PDF はデータベースに持たない。写しの行から同じものを作り直す。見た目を後で変えると作り直しの見た目も変わるため、原本はドライブのファイルとメールとする。写しの保存の要件は、記載事項が確かめられる記録でよい（国税庁 インボイス Q&A 問78。viewer-customer-sheet design §3-4）。
- PDF の処理は B2B の invoice_renderer.py に足さず、新しいファイルにする。B2B は輸出向けで項目が違うため。フォント登録の処理だけ共用する。
- メールの添付は auth_mail.py に新しい関数を足す（MIMEMultipart("mixed")）。文面は viewer_message_templates の台帳に invoice_send・invoice_reissue を足す。宛先は請求先の invoice_email、無ければ名簿のメール。**文面は PO が文面ページで保存するまで送れない**（既存の 503 と同じ動き）。

### 3-7. 再発行と入金確認

再発行:
- 前の行を voided にし、voided_at を入れる。同じ処理の中で新しい番号の行を作る。replaces_invoice_id で結ぶ。
- 値引き・期限・振込先は作成画面で入れ直せる。
- 案内のメールに「前の請求書（番号）は無効です」と書く。
- ドライブの前のファイルは消さず、名前の頭に「無効_」を付ける。失敗しても発行は止めない。

入金確認:
- 入金日を入れて確定する（既定は今日）。
- 請求書を paid、契約を active、閲覧者を active にする。1つの処理で行う。
- 部屋へ notice_activated を送る（今の本契約にするときと同じ）。
- 取り消しの操作は作らない。

### 3-8. ドライブ

- 保存先は発行元の会社の接続（tenant_google_drive_config）。この表は会社別の RLS があるので、裏の処理でも発行元の会社の文脈を張ってから読む（recon §8）。
- folder_id の本番の値は未確認（隠す列）。PO が連携ページで確かめる。
- 画面は今の連携ページ（GoogleDriveIntegrationPage.tsx）に「国内用の保存先フォルダ」を足す。URL を貼ると extract_folder_id（google_drive_oauth.py:98）で番号を取り、folder_id に入れる。
- 空なら、最初の保存のときに「Sales Anchor 請求書（国内）」を作って番号を入れる。
- **前提の分岐（PO のテスト保存で決まる。§7-1）**
  - 今あるフォルダへ保存できた → 上の形のまま。
  - 保存できない → Google のフォルダ選択（Picker）を足す。drive.file で渡されたファイルを扱うのが公式の形のため。追加の設計を書いて審査し直す。
  - 接続自体が切れている → PO が接続し直す。同意画面が Testing なら7日で切れるので、本番公開の手続きを別に行う。
- ファイル名は `請求書_VI-2026-0001_<発行日>.pdf`。宛名は入れない（ファイル一覧に個人名を出さない）。
- 接続の見守り: 週1回、トークンを更新して確かめ、失敗したら Discord の運用通知へ出す。6か月使わないと切れる対策も兼ねる。

### 3-9. 名簿を3年残す（最優先・先に本番へ）

`purge_viewer_accounts`（backend/app/tasks/maintenance.py:201）を次に変える。

| 対象 | 消す条件 |
|---|---|
| お試し・手続き中 | 見られる期限 + 3年を過ぎた |
| 停止 | 最後の停止記録と見られる期限の遅い方 + 3年を過ぎた |
| 申込のまま | 7日（変更なし） |
| ログイン記録 | 90日（変更なし） |
| 本契約 | 消さない |

- 手続き中の人の見られる期限は支払期限まで延びるので、数え始めの決定（お試し期限切れ・停止・支払期限切れの最後）と一致する。
- 名簿を消しても請求書の行は残る（viewer_account_id が NULL になる）。
- 公開ポリシー（lp/src/pages/privacy.astro）を同じ便で直す。
  - :215・:216 の期間を3年に。
  - :177 付近の利用目的に「お試しの再登録の防止」を足す。
  - 請求書の記録は7年残すと書く。
  - :247 の Google の用途にドライブを足す。
  - 改訂の日付と履歴を足す。

## 4. 便の順番

| 便 | 中身 | 利用者に見える変化 | 期限 |
|---|---|---|---|
| 1 | 3年残す・公開ポリシー | ポリシーの文 | **2026-12-19 より前** |
| 2 | 状態・表・税率画面・請求書情報の画面・フォーム3日 | 請求書情報と税率の画面 | |
| 3 | 請求書（作成・PDF・メール・ドライブ・再発行・入金確認） | まだ押せない（手続き中の人がいない） | |
| 4 | ボタンの切り替え・三点・直接移す道の削除 | 全部 | PO の入力とテストの後 |

- 便2 の移行は危険な変更に当たる。ADR-136 の手順で GO を記録する。
- 便4 の前に PO が行うこと: 国内用の請求書情報の入力、文面2つの保存、保存先の指定。

## 5. 代替案と選んだ理由

- 期限を別の列にする案 → 取らない。同じ意味の値が2つになる。
- 段階を列で持つ案 → 取らない。履歴と請求書の行と食い違う恐れがある。
- B2B の invoices を使う案 → 取らない。会社ごとの表で、閲覧者は会社の外にいる。PO の方針（docs/handoff/viewer-customer-sheet/design.md §3-4）。
- 税率をプランに持つ案 → 取らない。税率の変更でプランを全部直すことになる。
- 振込先と登録番号を会社情報に足す案（PO の最初の答え）→ PO が国内用と海外用を分けると決めたので置き換えた。
- 国内用と海外用を別の表にする案 → 取らない（PO 2026-11-06「1」）。同じ種類の欄が2つの表に分かれ、直す場所が2か所になる。
- 登録の有無と番号を国内用と海外用で別々に持つ案 → 取らない（PO 2026-11-06「会社に1つだけ持つ」）。登録は会社に1つの事実で、2か所にあると食い違う。
- 都道府県を画面の定数と DB の CHECK に並べる案 → 取らない（§3-4 の案B）。
- 違う項目だけ分ける案 → PO が取らなかった（「2」）。
- 請求書の PDF をデータベースに持つ案 → 取らない。表が太る。ドライブとメールに原本がある。ドライブが切れたまま発行した場合は写しの行で足りる。

## 6. リスクと対処

- **3年保持と個人情報の決まり**: 今の公開ポリシーは90日で消すと書いており、申込済みの人はその前提で登録した。再登録防止は今の利用目的に無い。ガイドライン 3-1-2 は、変更は関連のある範囲で通知か公表が要ると定める。関連のある範囲と言えるかは**未確認**。専門家の確認は未実施。PO の判断項目（§7-2）。
- **会社名が2か所になる**: 会社情報と請求書情報で値がずれることがある。正本の役割を §3-4 で固定し、画面に説明を出す。PO はこのリスクを聞いて選んだ。
- **ドライブが切れている**: 発行とメールは進み、「未保存」と出る。週1回の見守りで知らせる。
- **メールが届かない**: 「送信失敗」と出す。届いたかの確認は SMTP の受付までで、相手の受信は分からない。
- **二重発行**: 有効な請求書は契約に1件まで（部分一意索引）。
- **切り替え前に誤って手続き中へ移す**: 便4 まで「契約に進む」の道を画面に出さない。
- **別のメールかつ別の Discord の再登録**: 防げない。recon で確認済みの限界。

## 7. PO に決めてもらうこと

### 7-1. 設計の前提（答えが無いと設計合格にならない）

- ~~請求書の発行元の会社~~ → HIGH LIFE JPN に決定（2026-11-05 PO「1」）。
- ~~発行元がインボイスの登録事業者か~~ → 登録なしと回答（2026-11-05 PO「2」）。番号は有のときだけ必須にする形に決定。
- 登録の有無の欄が指すもの。PO の言葉は「課税事業者登録」、T の番号はインボイスの登録番号（recon §10）。名前を PO に確かめる。
- テスト保存の結果（接続が生きているか・今あるフォルダへ保存できるか）。

### 7-2. 承認のときに一緒に確かめること

- 状態の表示名「契約手続き中」。
- 手続き中の人にも手作業の「延長」を出す。
- 三点ボタンの金型を新設する。
- 商材とプランの登録画面は今回作らない。
- 税の端数は切り捨て。値引きは金額のみ。
- 3年保持を始める前に、専門家に確かめるか。
- 振込先の銀行口座に海外送金の欄（SWIFT コード・銀行の住所）を入れる。
- Wise と PayPal の入力項目（§3-4）。
- 振込先と請求書情報を直せる人を tenant.profile.edit を持つ人のままにするか、オーナーだけにするか。
- 都道府県の一覧を新しい表にする（§3-4 の案A）。
- 海外の住所の電話は国番号つきの数字だけで保存し、見せるときに「+」を付ける。

## 8. 受入条件

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | お試しの行に「契約に進む」が出て「本契約にする」が出ない。押すと手続き中になる | Evaluator（Playwright）＋ frontend テスト |
| A2 | 手続き中・未送信で「請求書を作成」「入金確認」が出ない | frontend テスト＋ Evaluator |
| A3 | 送信済みで「請求書を作成」と三点、発行後に「入金確認」と三点 | frontend テスト＋ Evaluator |
| A4 | フォーム送信で期限が3日後になり、残りが長い人は短くならない | backend pytest |
| A5 | 発行で期限が支払期限の 23:59:59（日本時間）になる | backend pytest |
| A6 | 期限切れの手続き中はログインが 403 viewer_contract_expired。行は残る | backend pytest（viewer_api） |
| A7 | 200,000円→220,000円。値引き 20,000円→198,000円。端数は切り捨て。小計超えの値引きは 422 | backend pytest |
| A8 | メールに PDF が1つ添付され、本文にリンクが無い | backend pytest＋本番でテスト用の閲覧者に送る |
| A9 | 保存が成功すると drive_file_id が入り、国内用フォルダにある | 本番で PO がドライブを目視 |
| A10 | 保存の失敗で発行は成立し、「未保存」と「もう一度保存」が出る。再保存で1件だけになる | backend pytest＋ Evaluator |
| A11 | 再発行で前が voided、新しい番号。有効な請求書は1件 | backend pytest |
| A12 | 入金確認で本契約になり、期限切れの日時でも見られる | backend pytest＋本番確認 |
| A13 | 期限切れ 3年以内の行は残り、3年を過ぎた行は消える。本契約は消えない | backend pytest（掃除の処理） |
| A14 | 名簿を消しても請求書の行が残る | backend pytest |
| A15 | 税率の行を足すと、適用日以降の請求書だけ変わる。発行済みは変わらない | backend pytest＋ Evaluator |
| A16 | チェックして発行すると次回の既定が変わり、チェックなしは変わらない。発行済みの期限は変わらない | backend pytest＋ Evaluator |
| A17 | プランと機能の行を足すと、作成画面の選択肢に出る | backend pytest＋ Evaluator |
| A18 | 新しい列の値が ai_ro で読めない | CI（ai_ro の点検）＋本番の読み取り |
| A19 | 画面の文字はすべて t()。生の部品なし | CI（i18n・UI のガバナンス） |
| A20 | 国内用と海外用を別々に保存でき、請求書は国内用の値を載せる。海外用や会社情報を直しても閲覧者の請求書は変わらない | backend pytest＋ Evaluator |
| A21 | 別の会社の文脈では請求書情報の行が読めない | backend pytest（RLS の点検） |
| A22 | 新しく作った会社と既存の会社で、請求書情報の3表の列・制約・RLS・ポリシーの差が0 | backend pytest（実 PostgreSQL。新しい会社を作る処理で1社作り、既存の1社と information_schema.columns・pg_constraint・pg_class.relrowsecurity と relforcerowsecurity・pg_policies を3表ぶん並べて比べ、差の行数が0） |
| A23 | 最高管理者の画面から発行しても、発行元の会社の請求書情報と Google の接続を読める | backend pytest（実 PostgreSQL で salesanchor_app の権限）＋ Evaluator |
| A24 | 登録が無のとき番号の欄が入力できず、値を送っても保存されない。有のとき T＋13桁以外は保存できない。PDF の番号の行は有のときだけ出る | backend pytest＋ frontend テスト＋ Evaluator |
| A25 | 振込先を種類ごとに複数登録でき、種類を変えると入力欄が変わる。種類ごとの必須が無いと保存できない（DB の CHECK でも止まる） | backend pytest＋ frontend テスト＋ Evaluator |
| A26 | 作成画面で選んだ振込先だけが PDF に載る。発行後に振込先を直しても消しても、発行済みの内容は変わらない。振込先が0件なら発行できない。作成画面に JPY 以外の Wise は出ない | backend pytest＋ Evaluator |
| A27 | 住所の国が日本のとき、郵便番号7桁以外・都道府県なし・電話にハイフンや空白・10〜11桁以外は保存できない（画面と DB の CHECK の両方） | backend pytest＋ frontend テスト＋ Evaluator |
| A28 | 住所の国が日本以外のとき、郵便番号なし・州の自由記入で保存でき、電話は数字6〜15桁だけ通る。PDF の電話は頭に「+」が付く | backend pytest＋ frontend テスト |
| A29 | インボイス登録の有無と番号は会社に1行だけで、国内用と海外用の請求書の両方に同じ番号が載る | backend pytest（2行目の INSERT が一意制約で止まる）＋ Evaluator |
| A30 | 都道府県の選択肢が DB の47行から出て、画面のコードに都道府県名が無い | backend pytest（47行）＋ CI の grep（frontend/src に「北海道」が0件） |
| A31 | 運営の文脈なしで新しい public の表へ書くと0行で、書く処理は誤りとして止まる。運営の文脈ありなら書ける | backend pytest（実 PostgreSQL・salesanchor_app） |
| A32 | 振込先と請求書情報を足す・直す・消すと audit_logs に1行ずつ残り、口座番号は下4桁だけ | backend pytest |
| A33 | 番号の採番を同時に2つ走らせても番号が重ならない | backend pytest（実 PostgreSQL・2接続） |
## 9. 実装カードへ送ること

- 状態を読む場所の全件 grep（`'trial'`・`"trial"`・`'active'`・`"active"`）を最初に行い、結果をカードの表と照合する。表に無い場所が出たら止まる。
- 請求書情報と Google の接続を最高管理者の画面から読むときは §3-4 の形にする。SQLite の試験では文脈の設定が何もしないので、A21・A23 は実 PostgreSQL で確かめる（dependencies.py の set_tenant_context の説明）。
- 実在のお客さんには送らない。確認は PO のテスト用の閲覧者で行う。

## 10. 外部・過去事例の参照と我々への応用

- 社内事例: B2B 請求書の発行時点の写し（migrations/20260604_160000_add_invoice_snapshot_columns.sql:31・:46）と2表の形（ADR-101）。同じ考え方を使う。
- 社内事例: 送り状のドライブ保存は失敗をログだけで流す（backend/app/routers/shipping.py:511）。今回は記録として必須なので、失敗を画面に出す形に変える。
- 外部の決まり: 国税庁 6303・インボイス Q&A 問78・問79、個人情報保護委員会 通則編、Google の公式説明（recon §8・§10）。
- 他社の導入事例: 該当なし。理由: 手続きと帳票の決まりで、法令と公式の説明と社内の既存の形で根拠が足りるため。

## 11. 接触面分析（逆参照の grep 2026-11-06。生出力 /tmp/CC報告ファイル/contract-status/contact-surface-1106.txt）

| 面 | 触れるもの | 対処 |
|---|---|---|
| ①人 | PO（請求書情報・振込先・文面・保存先の入力、テストの支払い）、HIGH LIFE JPN の会社情報を直す人 | 便4 の前に PO が行うこと（§4）。画面に「会社情報とは別」と書く（§3-4） |
| ②エージェント | 実装役は design.md・カードを読む。.claude/agents・docs/ai-agents・AGENTS.md に viewer_accounts の語は0件 | 実装カードに §9 の全件 grep と止まる条件を書く。周知の追加は不要 |
| ③機械 | 名簿の掃除 purge_viewer_accounts（backend/app/celery_app.py の定時登録、backend/tests/test_viewer_purge.py）。会社の表の作成 _TENANT_TABLES_SQL（backend/tests/test_rls_tenant_meta_config.py・test_roles_system_key_ddl.py）。移行の点検（.github/workflows/migration-guard.yml・migration-test.yml・schema-check.yml） | 掃除の試験を3年の条件に直す（A13）。会社の表の差の試験を足す（A22）。移行は migration-test で全会社へ流す |
| ④データ | public に新しい9表。全会社のスキーマに3表。tenant_google_drive_config に1列（読む処理: integrations.py・google_drive_oauth.py・carrier_credentials.py。試験 test_google_config_rls.py） | 既存の列は変えない。新しい列は NULL 可で今は使わない。tenant_004 本番の行は増えるだけ |
| ⑤本番 | 便1（掃除の条件）と便2（移行）は本番の DB を変える | 便1 は 2026-12-19 より前。便2 は ADR-136 の GO。直前のバックアップを確かめる |
| ⑥外部 | 閲覧者（メール・ログインの期限）、Google ドライブ、Wise・PayPal、公開ポリシー（lp/src/pages/privacy.astro） | 実在のお客さんには送らない（§9）。ドライブはテスト保存で分岐（§3-8）。Wise は円の入金をテストの支払いで確かめる |

## 維持の仕組み

- 守り手: .github/workflows/process-artifacts-gate.yml
- 対象: 1つの情報を1か所に置く決めごと（§3-1・§3-4）と、請求書を名簿の削除から切り離す決めごと（§3-9）。
- 補足: 状態の漏れは受入条件のテスト、列の隠し忘れは ai_ro の点検で止める。金額と期限の決まりは backend のテストで守る。
