---
mode: handoff
---

# design: 閲覧者の契約手続きの段階と請求書

> この文書は何か（専門用語なしの1行）:
> お試しから本契約までの間に手続きの段階を足し、商材とプラン、請求書の発行、ドライブ保存、名簿を3年残す決まりをどう作るかの設計。

- 親（設計仕様書）: [docs/specs/viewer-contract-invoicing/README.md](../../specs/viewer-contract-invoicing/README.md)
- 現状の記録: [docs/handoff/viewer-contract-stage/recon.md](./recon.md)
- 決めごとの控え: [decisions-draft.md](./decisions-draft.md)
- 関係 ADR: [ADR-1061](../../adr/ADR-1061-viewer-contract-stage-and-invoicing.md)（草案）、閲覧者の名簿の90日の決まり（docs/handoff/gas-viewer-fresh-fast/review-fable.md:172 の Q7 に答えた docs/handoff/gas-viewer-fresh-fast/design.md:523〜:524。backend/app/tasks/maintenance.py:202 が参照）を改訂。ADR-1019 には Q7 も90日も無い（2026-11-06 grep で0件）、ADR-101（B2B 請求書。別の表にする）、ADR-144・ADR-067（金型とトークン）、ADR-027（i18n）、ADR-135・ADR-136（危険な変更の GO）
- 状態: **設計案作成済み・PO の答え（ideal-state 41〜53）と商材とプランの画面（§3-4d）を反映・最新の版はマージ前の審査役 Opus が APPROVE（d683ac870 対象。低の指摘は cad8b72e0 で直した。審査の記録は [review.md](./review.md)）・§7-2 の項目は全部 PO の答えで閉じた・PO の設計承認済み（2026-11-12、ideal-state 54）・便1 は実装済み（PR #5250、2026-11-07 マージ、公開ポリシー v1.8 が本番の LP に出ている）・便2 以降は実装未着手**

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
- 書類に載せる会社情報（会社名・メール・サイト・住所・電話・インボイス登録）と振込先を、国内用・海外用に分けて登録する形への変更（§3-4）。
- B2B の請求書の国内向けか海外向けかを、取引先の既定の請求先の国で自動で決める。決められない取引先には請求書を作らせない（§3-4）。見積書は今回変えない（PO 2026-11-07）。
- 差出人を載せる今の書類のうち、B2B の請求書の読み先を、1つの読み出しの道へ切り替える（§3-4）。見積書の PDF は海外用を読む（PO 2026-11-07）。発注書と FedEx の申請書は切り替えない（PO 2026-11-06「発注書は使わないので破棄、使うのは見積もりと請求書のみ」）。
- 名簿を3年残す変更と公開ポリシーの書き換え。
- 商材とプランの登録画面（PO 2026-11-09「2」で今回作ると決定。中身は PO 2026-11-09「1」: 最高管理者のみ・税率の画面と同じ場所・商材と料金を足せる・名前と金額を後から直せる・消さずに「使わない」へ切り替える・発行済みの請求書の金額は写しのまま）。画面と API の細かい設計は §3-4d（2026-11-11 に足した。便2b）。

対象外（次の機会）:
- 海外用フォルダの画面とトレカの請求書の保存（入れ物の列だけ今回足す）。
- 海外向けの閲覧者の請求書の発行。今の書類は読み先を切り替えるだけで、見た目と項目は変えない。例外は1つ: B2B の請求書の PDF に、その region の行が登録有のときだけ登録番号の1行を足す（PO 2026-11-07「1」。§3-4）。
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
- 配信（backend/app/services/tcg_distribution_svc.py:737）は変えない。active 以外は not_contracted で配らない形（同 :737）なので、contracting は自動で配信なしになる（A34）。
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
- 手続き中の人にも「延長」を出す。支払いが少し遅れる人のための手作業の逃げ道。AI の追加の案で、PO が 2026-11-11「1」で認めた（ideal-state 49）。
- 履歴の操作に start_contract・form_sent・invoice_issued・confirm_payment を足す（migrations/20261016_150000_add_viewer_accounts.sql:91 の決まりを変更）。
- 切り替えの便で、お試しから本契約へ直接移す道を、画面と API とコマンド（backend/app/viewer_admin_cli.py:13）から外す。
- 新しい部品は ViewerAccountsPage.tsx に足さず、別ファイルにする（922 行で上限が近い）。
- 三点ボタンは金型 `MoreMenuButton`（NAV_ICONS.more と ContextMenu を組む）を登録して使う。金型の新設は PO が許可した（PO 2026-11-12「1」。ideal-state 52。ほかの画面でも使える共通の型にする）。ADR-144 §4 に沿って、frontend/src/components/ に本体 MoreMenuButton.tsx・見た目 MoreMenuButton.css（トークンの値だけ）・見本集 MoreMenuButton.stories.tsx の3つ（まだ無いファイル）をそろえる。ContextMenu は画面上の点（x, y）で出す作りなので、ボタンの位置から x, y を出す決め方（例: ボタンの右下）と置き方は実装カードで決める（審査 2026-11-12 の低2件）。

### 3-4. 表（書類に載せる会社情報と振込先の4表は会社ごとのスキーマ、他は public・金額は円の整数）

**sa_products**（商材）
- id、code（一意）、name、seller_tenant_id（発行元の会社。tenants を参照）、default_payment_days（既定の支払日数。既定 3）、is_active、created_at、updated_at。

**sa_plans**（プラン）
- id、product_id、code（商材内で一意）、name、billing_type（one_time／subscription）、billing_interval（month／year。one_time は NULL）、unit_price_jpy（税抜）、is_active、created_at、updated_at。

**sa_plan_features**（プランに含む機能）
- plan_id、feature_key。主キーは2列の組。feature_key に CHECK (feature_key IN ('inventory_view','sheet_distribution')) を付ける。この CHECK が含む機能の一覧の正本（§3-4d）。

**sa_contracts**（契約）
- id、plan_id、viewer_account_id（ON DELETE SET NULL）、tenant_id（将来の導入支援用。今回は常に NULL）、status（in_progress／active／cancelled）、started_at、activated_at、created_at、updated_at。
- 同じ閲覧者・同じプランの in_progress と active は1件まで（部分一意索引）。
- 「契約に進む」で in_progress を作る。
- 閲覧者の状態の正本は viewer_accounts.status（試用・手続き中・本契約・停止）。sa_contracts は「何を売ったか」の記録で、状態の判定には使わない（第5回・第6回の審査）。
- 手続き中の停止・停止解除・手作業の延長では sa_contracts の行を変えない。cancelled にする操作は今回作らない（列の値として予約するだけ）。

**tax_rates**（税率）
- id、rate_percent（NUMERIC(5,2)）、effective_from（DATE・一意）、created_by_user_id、created_at。
- 最初の行（10.00・2019-10-01）は、便2 の本番反映の後に PO が税率の画面で足す（ADR-1007 決定1 の「アプリ画面」）。移行では入れない。
- 請求書は発行日に有効な行を読み、率を写す。後から行を足しても、発行済みは変わらない。
- 画面は最高管理者のみ。行の追加だけで、過去の行は直せない（打ち間違いは明日以降の適用日の行に限り消せる）。
- 足す行の適用日は、今ある最も新しい行の適用日より後で、かつ明日（日本時間）以降でなければ 422。表が空のときだけ過去の日付を入れられる（最初の 2019-10-01 のため）。過去や今日の日付を後から足すと、発行済みの請求書の率と表の上の率が食い違うため止める（第5回・第6回の審査）。

**viewer_invoices**（請求書）
- id、invoice_number（一意）、contract_id（SET NULL）、viewer_account_id（SET NULL）、status（issued／paid／voided）、replaces_invoice_id（再発行元）。
- issued_at、due_date、paid_at、paid_confirmed_by_user_id、voided_at。
- subtotal_jpy、discount_total_jpy、taxable_jpy、tax_rate_percent、tax_amount_jpy、total_jpy。
- bill_to_snapshot、issuer_snapshot（JSONB。発行時点の写し）。issuer_snapshot に選んだ振込先1件と登録番号を含む。
- mail_to、mail_sent_at、mail_error、drive_file_id、drive_web_link、drive_saved_at、drive_error。
- created_by_user_id、created_at、updated_at。
- 有効な請求書（issued）は同じ契約に1件まで（部分一意索引）。
- 番号は年ごとの採番の表 viewer_invoice_number_seq（year INTEGER 主キー、last_number INTEGER NOT NULL）の行を `SELECT … FOR UPDATE` で進める。その年の行が無ければ INSERT … ON CONFLICT DO NOTHING で作ってから進める。同時に発行しても重ならない。

**会社情報の持ち方（1つの情報は1か所。PO 2026-11-06「1」と「2」を、同日の次の言葉で改めた）**
- PO の決定（2026-11-06。ideal-state の 25）: 設計担当の説明「会社名、メール、サイトは、それぞれ1つずつ持ちます」に PO が「→国内と海外で登録できるようにする」と答えた。説明「インボイス登録をしているかどうかと、その番号は、会社に1つだけ持ちます」に PO が「→これも国内と海外で2つ、分社している場合に備えて」と答えた。
- このため、会社名・メール・サイト・住所・電話・インボイス登録の有無と番号を、国内用と海外用で1行ずつ持つ。1つの表 tenant_issuer_profiles に、region ごとに1行で置く。前の版の2つの新しい表（住所の tenant_profile_addresses、登録の tenant_invoice_registration）は作らない。項目が同じ region の単位で揃ったので、1行にまとめれば同じ項目を2つの表に置かずに済む。
- 2026-11-06「2」（メールとサイトは会社に1つ）と「インボイス登録は会社に1つ」は、この言葉で取りやめた。
- 項目ごとの置き場（どこにも2か所目を作らない）:

| 項目 | 置き場 | 国内向けの書類 | 海外向けの書類 |
|---|---|---|---|
| 会社名・メール・サイト・住所・電話・インボイス登録の有無と番号 | tenant_issuer_profiles（新）の region ごとの行 | domestic の行 | overseas の行 |
| 振込先 | tenant_invoice_payment_methods と詳細の2表（新。region ごと） | domestic の行 | overseas の行 |
| 印影の URL・既定の言語 | tenant_profile（今の列。変えない） | 同じ値 | 同じ値 |

- 今の tenant_profile の company_name・company_name_en・email・website・address・phone の6列は、読むだけの古い値として残す（下の tenant_profile の段落）。

**tenant_profile（今の会社情報の表。変える点）**
- company_name・company_name_en・email・website・address・phone の6列は、新しい表 tenant_issuer_profiles に置き換える。画面と API からは書けなくする（TenantProfileUpdate から6項目を外す。backend/app/schemas/tenant_profile.py:31〜:36。extra の設定が無いので、外した項目を送っても無視される）。今の GET /admin/tenant-profile の返す値（TenantProfileResponse。同 :16〜:21）からも6項目を外す。古い値を読む API は新しい GET /admin/issuer-profiles だけにする（口を1つにする）。今の口に残るのは印影の URL と既定の言語の2つ。
- 6列は消さずに、読むだけの古い値として残す。理由: 古い住所は1欄の自由記入で、5欄へ機械で分けられない。会社名の日本語と英語も、どちらを国内用と海外用に入れるかを会社の人が決める。そのため値を写す移行は作らない。PO が新しい欄へ入れ直すまで、今の書類が空にならないように読む。
- 古い値を読むのは「その会社にその region の行が無いとき」だけ（§3-4 の「発行元を読む1つの道」）。新しい値を書くのは新しい表だけ。
- 6列を消す移行は後の便にする。条件は2つ。(1) 本番の全会社で、古い値のどれかがあるのに domestic か overseas のどちらか1つでも行が無い会社が0件（請求書はどちらの region にもなるため両方を数える）。(2) 古い列を読む発注書と FedEx の申請書の口が消されている（PO 2026-11-10 の決定で、どちらも消す。下の「古い6列を消すまでの計画」の（２））。見積書の PDF の口は get_issuer へ切り替えるので、条件に入らない。region ごとに件数を数える。数え方は読み取り専用の鍵で件数だけを数える（中身は出さない）。
- 画面は、国内用と海外用のそれぞれについて、その region の行が無く古い値があるとき、そのタブに「前の会社情報」として古い値を読むだけで見せ、新しい欄へ入れ直す案内を出す。

**古い6列を消すまでの計画**（PO 2026-11-10「古い店は長期的に見て消したほうが良いよね？消す方向で統合計画を」。「店」は「欄」の打ち間違いと読んだ。AI の読み。ideal-state 44・45）:
- 方向: 古い6列は消す。消すまでの間は上の決まりどおり読むだけで残す。
- 順番（前の段が済むまで次へ進まない）:
  （１）この設計の便2・便3: 新しい置き場所（tenant_issuer_profiles）を作り、B2B の請求書・見積書・閲覧者の請求書は get_issuer で読む。
  （２）別の設計: 古い列を読む残りの口を消す。発注書（backend/app/routers/purchase_orders.py:354・:385・:495、backend/app/services/po_renderer.py、その試験、表）と FedEx の申請書（backend/app/routers/shipping.py:780・:815、backend/app/services/label_validation.py:82〜:103 の get_tenant_profile、どこからも読まれていない画面 frontend/src/pages/integrations/FedexLabelValidationTab.tsx）。どちらも画面は無く口だけが残っている（下の「対象外」）。表と中のデータを消すのは元に戻せないので、件数を数えて PO に確かめてから行う（PO 2026-11-10「1」）。
  （３）古い値があり新しい行が無い会社を region ごとに数え、0件にする（上の条件 (1)。入れ直すのは各社の人。0件になるまで待つ）。
  （４）別の便: 古い6列を消す移行。ADR-136 の GO で行う。
- この設計で作るのは（１）だけ。（２）〜（４）は tasks/todo.md に積み、それぞれ別の設計にする。

**tenant_issuer_profiles**（書類に載せる会社情報。国内用と海外用。会社ごとのスキーマ）
- 列: id、tenant_id（NOT NULL。RLS の判定に使う。own_inventory と同じ形）、region（domestic／overseas）、company_name、email、website、country_code、postal_code、prefecture_code、state_region、city、address1、address2、phone、is_invoice_registered（BOOLEAN NOT NULL DEFAULT false）、registration_number、updated_by_user_id、created_at、updated_at。
- tenant_id と region の組で一意。会社に最大2行。region は「どちらの書類に載せる行か」だけを表す。住所と電話の決まりは region ではなく country_code で分ける（PO 2026-11-06「1」。前の版の決定を引き継ぐ）。分社して国内用と海外用で別の会社になっても、行ごとに会社名・住所・登録を持てる（PO「分社している場合に備えて」）。
- company_name は必須（NOT NULL・空文字を CHECK で止める）。長さは今の列と同じ 255 まで（tenant_profile.py:31）。会社名を日本語と英語の2つ持たない。その行の書類に載せる名前を1つ持つ。
- email と website は任意。長さは今の列と同じ 255 まで（同 :35〜:36）。
- 列名は取引先の住所の先例（postal_code・prefecture・city・address1・address2。migrations/20260603_010000_add_suppliers_line_and_address.sql:21〜:25）に合わせる。PO の5欄（郵便番号・都道府県・市区町村・住所1・住所2）と同じ並びのため。都道府県は一覧への参照にするので prefecture_code とする。country_code は取引先の住所の表（migrations/030_create_company_contact_subtables.sql:46〜:58）と public.countries（migrations/20260621_010000_create_countries_master.sql:6〜:13）に合わせて ISO 2文字。

住所と電話の決まり（CHECK で止める。画面も同じ決まりで止める）:
- country_code は必須で public.countries を参照する（外部キー。会社ごとの表から public への参照は先例あり: backend/app/services/tenant.py:518・:605）。
- country_code が 'JP' のとき（PO 2026-11-05「郵便番号、都道府県、市区町村、住所1、住所2で、電話番号はむらが出ないようにハイフン禁止」）:
  - postal_code は `^[0-9]{7}$`。prefecture_code は必須。state_region は NULL。
  - phone は `^[0-9]{10,11}$`。桁は今の請求先フォーム（backend/app/services/viewer_billing_form.py:23〜:24）と同じ。
- country_code が 'JP' 以外のとき:
  - postal_code は任意（`^[0-9A-Za-z -]{1,10}$` または NULL）。prefecture_code は NULL。state_region は任意の自由記入（州・地域）。
  - phone は「+」と国番号から始まる形で保存する: `^\+[0-9]{6,15}$`。アプリ共通の電話の決まり（ADR-126、origin/main backend/app/schemas/base.py:16〜:30 の validate_phone の `\+\d{6,15}`＝国際形式）と同じ形にそろえる（PO 2026-11-10「1」。ideal-state 46）。画面と PDF は保存した値をそのまま見せる（「+」を足したり外したりしない）。「+」の無い値は保存させない（DB の CHECK と画面の両方）。
- どちらも city と address1 は必須、address2 は任意。
- 電話のハイフンと空白は、自動で外さずに止める（PO「ハイフン禁止」）。今の請求先フォームは外して受け取る（viewer_billing_form.py:32〜:34）。こちらは発行元を会社の人が登録する欄で、入れた値と保存する値を同じにするため、わざと違う形にする。画面は赤い注意を出して保存させない。
- PDF では「〒」と郵便番号の3桁目の後のハイフンを、表示のときだけ付ける。

都道府県の一覧（1か所に置く。案A を取る）:
- public.prefectures（code CHAR(2) 主キー＝JIS X 0401 の 01〜47、name_ja、name_en、sort_order）を新しく作る。移行は表の形だけで、行は入れない（ADR-1007 決定1）。prefecture_code はこの表への外部キー。
- 47行の正本は docs/handoff/viewer-contract-stage/data/prefectures.sql の1ファイル（JIS X 0401 の番号と名前。ON CONFLICT (code) DO NOTHING）。本番へは「1回だけのデータの変更」（PO の合意 → DRY-RUN → COMMIT、記録を同じ場所に残す。頭で運営の印 `SET LOCAL app.is_operator = 'true'` を張る。この SQL は psql で1回流すだけでアプリの試験を通らないので直接書く）で流す。試験は backend/tests/seed_data.py に読む関数を足して同じファイルから入れる（国の一覧が countries.ts を読む形と同じ。同ファイル :21〜:56）。47行を2か所に書かない。
- 画面の表示は、言語が日本語なら name_ja、それ以外なら name_en を出す。都道府県名は DB のデータで、画面の文言（ADR-027 の t() の対象）ではない。国の名前を countries から出す今の形と同じ扱い。
- 画面の選択肢は API でこの表から読む。画面のコードに都道府県名を書かない。
- 案B（画面の定数ファイル＋DB の CHECK に47個を並べる）は取らない。同じ一覧が2か所になり、揃っているかを確かめる仕組みが今のリポジトリに無いため（国の一覧 frontend/src/constants/countries.ts と public.countries の照合も .github/workflows・scripts に無い。2026-11-06 grep）。

発行元を読む1つの道（get_issuer。backend/app/services/issuer.py に新しい読み出しの処理を1つ作り、差出人を載せる書類はすべてここを通す）:
- 受け取るもの: 会社の番号と region（domestic／overseas）。
- 返すもの: その region の行の会社名・メール・サイト・住所の各欄・電話・インボイス登録の有無と番号。
- その region の行が無いとき: tenant_profile の古い6列を返し、「古い値」の印を付ける。会社名は今の選び方（company_name、空なら company_name_en。backend/app/routers/invoices.py:121）のまま。インボイス登録は無として返す。閲覧者の請求書は古い値を使わず、発行を止める（§3-4b の issuer_profile）。今の書類は古い値で今までどおり出る。
- 行がある region では古い列を読まない。行の中の空の欄（メール・サイト・住所2）を古い列で埋めない。1つの書類に新しい値と古い値を混ぜないため。
- 差出人を読む今の処理は次の3つ（grep 2026-11-06。生出力 /tmp/CC報告ファイル/contract-status/ssot-verify-1106.txt・ssot-verify-1106b.txt・tp-readers-1106.txt）。どれも tenant_profile を直接読んでいる。このうち1つ目の処理で、B2B の請求書の口だけを get_issuer に切り替える。同じ処理を使う見積書の PDF の口（:1007）は get_issuer の海外用へ切り替える（PO 2026-11-07）。発注書と FedEx の2つは切り替えず、今のまま古い列を読む（下の「対象外」）。
  - B2B の請求書と見積書: backend/app/routers/invoices.py:109〜:128 の _fetch_tenant_profile（呼び出し :829・:875・:1007）。PDF は backend/app/services/invoice_renderer.py:509〜:513・:579〜:583。
  - 発注書: backend/app/services/po_renderer.py:253〜:273（住所を1行で描く :371〜:373 付近）。
  - FedEx の申請書と申請メール: backend/app/services/label_validation.py:82〜:103 の get_tenant_profile（呼び出し backend/app/routers/shipping.py:780・:815）。
  - 他に tenant_profile を読むのは会社情報の口（backend/app/routers/tenant_profile.py）と、表の作成（backend/app/services/tenant.py:1147）と、最高管理者の DB の表の一覧（frontend/src/pages/super-admin/components/DbViewerPanel.tsx:147）だけ（git grep 2026-11-06。57行）。
- B2B の請求書がどちらの region を読むか（PO 2026-11-06「顧客情報の住所で自動的にシステムが判断する仕組みに出来る？請求先が日本なら国内向け、海外なら海外向け」。同日の前の案「作る画面でプルダウンで選ぶ」はこの言葉で取りやめた。PO 2026-11-07「見積もりは今回はパス、請求書だけで考える」）:
  - 作るときに、取引先の既定の請求先の住所の国（company_addresses の address_type が billing で is_default が TRUE の行の country_code）で決める。JP なら domestic、JP 以外の国なら overseas。今の請求書は作るときに既に同じ行を読んで請求先の写しを作っている（backend/app/routers/invoices.py:66 の _fetch_address_snapshot。条件 :84〜:86。国は返す値の "country"。:104 付近）。同じ条件を2か所に書かないため、国の判定はこの写しの "country" から行う。新しく住所を読む処理は作らない。
  - 決める処理は1つにする（backend/app/services/issuer.py の decide_issuer_region。請求先の写し（無ければ None）を受けて domestic／overseas か「決められない」を返す。DB を読まない）。呼ぶのは、見積書から請求書を作る口（invoices.py:241。写しを作るのは :268〜:269）と、見積書を経ずに作る口（同 :339。写しは :367〜:368）の2つ。見積書から作るときも、見積書の値は引き継がず、作るときの取引先の国で決める（見積書は今回変えないため）。
  - 決めた値は請求書の行に1つだけ持つ（invoices.issuer_region。値は domestic／overseas）。住所そのものは書類に写さない。会社情報の正本は tenant_issuer_profiles の1か所のまま。
  - 作った後に値は変わらない。理由: 請求書の取引先は作った後に直せない（直す口の項目に company_id が無い。backend/app/schemas/invoice.py:54〜:59）。取引先の住所の国を後で直しても、作り済みの請求書の値は変えない。画面に「国内向け／海外向け」の選択は置かない。詳しい画面に決まった値を読むだけで出す。
  - **決められないときは作らない（PO 2026-11-07「請求書は顧客情報が登録されていないと作れない仕組みにしたいので1」。1 は「作るのを止めて、『請求先の国を入れてください』と案内を出す」）**: 既定の請求先の住所が無いとき、または国が空のとき。2つの口は請求書の行を INSERT する前に止め、422 を返す。detail は理由のキー bill_to_country（画面が t() で文に直す。ADR-027）。作る画面は「請求先の国を入れてください」の案内と、その取引先の画面への道を出す。見積書から作るボタンの側も同じ案内を出す。本番の主な会社で51社のうち3社がこれに当たる（国が空1社・既定の請求先が無い2社。recon §14）。既定の印の無い請求先の住所しか無い取引先も、既定の請求先が無い側に入る（2社にそういう住所があるかは数えていない）。
  - 国が JP 以外のとき、その国が public.countries にあるかは確かめない。取引先の住所の国は今は自由記入で入る（frontend/src/pages/companies/CompaniesPage.tsx:550 は2文字の制限だけ。CompanyAddressModal.tsx:143〜:144 は大文字と2文字を確かめる）。判定は「JP かどうか」だけに使うので、小文字の 'jp' も JP として扱う（大文字にしてから比べる）。本番の主な会社に形の崩れた値は0件（recon §14）。国の欄に違う国が入っていると、その国のとおりに決まる（PO に 2026-11-07 に伝えた）。
  - PDF は今と同じく、出すたびにその時点の会社情報から作る（同 :829・:875 が毎回読む。写しの列は無い）。そのため、会社情報を直した後に出し直すと、決まった側の新しい会社情報が載る。今の動きと同じで、今回は変えない。
  - 前に作った請求書（値が空）は、PDF を出すときに overseas として読む。見出しが英語のため（invoice_renderer.py:267）。移行で値を書き込まない（ADR-1007 決定1）。本番で値が空になる請求書は、主な会社で0件、他の会社で1件（recon §14）。その1件は試しの請求書で、PO の指示で消した（2026-11-09。§7-2 の1つ目）。この扱いが当たる請求書は本番に無い。
  - invoices は会社ごとのスキーマの表（backend/app/services/tenant.py:864）。ADR-142 に従い、全会社へ足す移行と _TENANT_TABLES_SQL を同じ変更で揃える。値は決まった2つなので、相談係の道では隠さない（決まった値しか入らない列の扱い）。
  - B2B の請求書の PDF の登録番号（PO 2026-11-07「1」。1 は「登録があるときだけ、番号を請求書に印刷する」）: 今の PDF に番号を描く処理は無い（origin/main の backend/app/services/invoice_renderer.py を grep して0件。生出力 /tmp/CC報告ファイル/contract-status/invoice-renderer-1107.py）。変える点は3つ。(1) InvoiceRenderData（同 :148〜:152 の tenant_* の並び）の後ろに tenant_registration_number: Optional[str] = None を足す。(2) 発行者の欄の Web の行（同 :260〜:263）の直後に、値があるときだけ同じ字の大きさ 8 で「Registration No.: 番号」の1行を描き、y を 4mm 下げる。今の欄の見出し（TEL:・Email:・Web:）が英語の決まった文字なので、それに揃える。(3) 値を詰める場所は2つに分ける。請求書の PDF を作る口（origin/main の backend/app/routers/invoices.py:829 と :875。今は _fetch_tenant_profile の dict を渡す）を get_issuer(tenant, その請求書の region) に切り替え、渡す dict に registration_number のキーを含める。render_invoice_pdf（invoice_renderer.py:435〜）は get_issuer を呼ばず、受け取った dict から :513 の直後に tenant_registration_number=tenant_profile.get("registration_number") を足すだけにする。get_issuer は登録無の行と古い値のときは None を返すので、そのときは行を描かない。render_quote_pdf（同 :520〜。会社情報を渡すのは :579〜:583）には足さない（見積書は今回変えない）。
  - 見積書（PO 2026-11-07「見積もりは今回はパス」）: 見積書の表と作る口と画面は変えない。quotes に列を足さない。見積書の PDF（invoices.py:972〜。会社情報を読むのは :1007）は、get_issuer(tenant, overseas) で海外用の行を載せる（PO 2026-11-07「1,見積もりは顧客名は必須にしない、成約前の顧客にも使用するため顧客情報がない場合があるので」。1 は「見積書にも新しい海外向けの情報を載せる」）。取引先の国では決めない。理由は PO の言葉のとおり、見積書は取引先の情報が無い場面でも使うため。海外用の行が無い会社では、get_issuer の決まりどおり古い値が載る（今と同じ）。
  - 見積書を取引先なしで作れるようにするか: 今の見積書は、登録済みの取引先と担当者が無いと作れない（origin/main の backend/app/schemas/quote.py:41〜:42 で必須。backend/app/routers/quotes.py:184 で取引先にリードが無いと 422）。PO の言葉「顧客名は必須にしない」はこの今の形と違う。今回の設計には入れず、別の設計で後から進める（PO 2026-11-07「1」。1 は「お客さんなしで見積書を作れる作業は、あとで別に進める」）。生出力: /tmp/CC報告ファイル/contract-status/quote-required-1107.txt。
  - 生出力: /tmp/CC報告ファイル/contract-status/update-paths-1106.txt・update-paths2-1106.txt・reader-country-1106.txt・quote-mentions-1107.txt。
- 発注書と FedEx の申請書: 対象外。切り替えない（PO 2026-11-06「発注書は使わないので破棄、使うのは見積もりと請求書のみ」）。
  - 2つとも今は作る画面が無い。発注書の画面は 2026-10-11 に「使っていない画面」として消した（commit 7a2f39c20「refactor: remove unused purchase-orders page」）。口（backend/app/routers/purchase_orders.py:354・:385・:495）だけが残る。FedEx の申請書の画面（frontend/src/pages/integrations/FedexLabelValidationTab.tsx:57）は origin/main のどこからも読み込まれていない（git grep 2026-11-06）。口（backend/app/routers/shipping.py:780・:815）だけが残る。
  - 2つの残った口は今のまま tenant_profile の古い列を読む。古い6列は読むだけで残すので、2つの動きは変わらない。
  - 発注書を消す作業（残った口・po_renderer.py・その試験・表）は、この設計に入れない。別の設計で行う。表とその中のデータを消すのは元に戻せないため、件数を数えて PO に確かめてから行う。
  - FedEx の申請書も消す（PO 2026-11-10「1」。ideal-state 45）。発注書と同じく、この設計には入れず別の設計で、件数を数えてから消す。下の「古い6列を消すまでの計画」の（２）。
  - 生出力: /tmp/CC報告ファイル/contract-status/dropdown-recon-1106.txt〜dropdown-recon4-1106.txt。
- 古い住所は1欄の文字、新しい住所は欄ごとの値。get_issuer は欄を決まった順でつないだ1つの文字も返し、今の書類は描き方を変えずにそれを載せる（新しい PDF の配置は閲覧者の請求書だけ）。
- 閲覧者の請求書は domestic を読む。発行時に get_issuer の結果を issuer_snapshot に写す。発行後に会社情報を直しても発行済みは変わらない。
- 今の書類の写しの列（purchase_orders の company_name_snapshot・contact_info_snapshot。migrations/063_tenant_rbac_extensions.sql:63・:67）は、アプリから書く処理が無い（backend/app の grep で0件）。今回は触らない。

インボイス登録の有無と番号（tenant_issuer_profiles の is_invoice_registered と registration_number。region ごと。PO 2026-11-06「これも国内と海外で2つ、分社している場合に備えて」）
- 画面の欄の名前は「インボイス登録番号」（PO 2026-11-10〜11「1」。ideal-state 47）。番号の形「T＋13桁」は民間の解説（弥生・マネーフォワード・freee）で確かめた。国税庁の本文では確かめていない。
- 登録の有無（PO 2026-11-05「課税事業者登録の有無もDBに登録してフロントでも編集できるようにして、登録している場合はTから始まる13桁の番号も登録するようにする、無の場合は入力欄をグレーアウトさせて入力させないイメージ」）: 有なら registration_number は必須で `^T[0-9]{13}$`。無なら NULL。DB の CHECK でも止める。画面は無のとき番号の欄を disabled にする。
- 国内用の行と海外用の行で、それぞれ別に持つ。片方を直してももう片方は変わらない。
- 今の HIGH LIFE JPN は無（2026-11-05 PO「2」）。行が無いときは無として扱う。
- PDF の登録番号の行は、その書類の region の行が有のときだけ出す。

会社ごとのスキーマの新しい4表（会社情報・振込先の一覧・銀行の詳細・Wise の詳細）に共通の決まり:
- **SSOT の境界**: 書類に載せる会社名・メール・サイト・住所・電話・インボイス登録は tenant_issuer_profiles、振込先は tenant_invoice_payment_methods（一覧）と tenant_invoice_payment_bank・tenant_invoice_payment_wise（種類ごとの詳細。同じ項目を一覧と詳細の両方に持たない。例外は外部キーで種類を合わせるための method_type と、RLS で会社を分けるための tenant_id。どちらも外部キーで一覧の値と一致させる）、印影と既定の言語は tenant_profile が唯一の正本。同じ項目を2つの表に持たない。書類はすべて get_issuer を通して読む。tenant_profile の古い6列は読むだけで、書く道は無い（2026-11-06 PO の言葉。ideal-state の 25）。どちらの region かは書類の issuer_region が唯一の正本で、決める処理は decide_issuer_region の1つだけ。
- 置き場は会社ごとのスキーマ（tenant_NNN.tenant_issuer_profiles、tenant_NNN.tenant_invoice_payment_methods、tenant_NNN.tenant_invoice_payment_bank、tenant_NNN.tenant_invoice_payment_wise）。会社別のデータはそこに置く決まり（ADR-142 の Context）で、会社情報（tenant_profile）も同じ場所にある。
- ADR-142 の Decision 2 と 3 に従い、次を同じ変更で揃える。既存の全会社へ足す移行と、backend/app/services/tenant.py の _TENANT_TABLES_SQL（:195）・_RLS_ENABLE_SQL（:1221）・_RLS_POLICY_SQL（:1274）の3か所。ポリシー名は `<表名>_tenant_isolation`、条件は own_inventory と同じ（tenant.py:1338〜:1340）。権限は一括付与に任せる。既定の行は入れない。発行元の行が無ければ発行を止める。
- 次の口は発行元の会社の番号で set_tenant_context を張る: 作成画面の材料（invoice-draft。get_issuer と振込先を読む）、発行、再発行、もう一度送る、もう一度保存、入金確認、裏のメールとドライブ。発行の処理は表名は tenant_table_ref で書く（backend/app/auth/dependencies.py:277・:409）。commit の後は reset する（同 :339、ADR-072）。
- 文脈を張る順番は次で固定する。set_tenant_context は最後に `SET app.is_operator = ''` を流す（dependencies.py:297〜:299）ので、先に運営の印を張ると消える。
  （１）set_tenant_context（発行元の会社の番号）
  （２）set_operator_context(db)（backend/app/auth/dependencies.py:429。説明文に「そのセッション変数を設定する唯一の経路」。SQLite では何もしない :441）
  （３）書き込み
  （４）commit
  （５）reset_operator_context(db)（同 :446）で運営の印を外し、続けて読むなら reset_tenant_context（同 :339。中で set_tenant_context を呼ぶので運営の印も '' に戻る）
- 生の `SET LOCAL` を text() で流さない。pytest は SQLite でも動くので文の誤りになる（同 :264〜:274 の説明）。
- 運営の印は接続に残る（SET。SET LOCAL ではない）。（５）と、接続を返す前の clear_tenant_context で消す。commit の後に裏で行うメール・ドライブの結果の書き込みは、裏の処理の頭で（１）（２）を張る。最高管理者の口には前例が無い（super_admin の口の grep で該当なし）。会社の番号を引数で受けて文脈を張る処理は裏の処理にある（backend/app/services/google_webhook.py:255、backend/app/discord_gateway/dm_writer.py:94）ので、この形を発行の処理に写す。
- 文脈は接続を返す前に消える（backend/app/database.py:60〜:61 の get_db が clear_tenant_context を呼ぶ。backend/app/auth/dependencies.py:361。ADR-131）。裏の処理は get_db を通らないので、処理の終わりで clear_tenant_context を呼ぶ（同 :361 の説明にある BackgroundTasks の形）。新しい public の表の SQL は public. を付けて書く。
- 画面は今の会社情報のページ（frontend/src/pages/admin/TenantProfilePage.tsx）を直す。管理センターの左のメニュー「ビジネス設定」（frontend/src/locales/ja.json:438 の managementCenter.sectionBusiness）の「発行者情報」から開くページ（frontend/src/pages/management-center/ManagementCenterPage.tsx:80、frontend/src/App.tsx:408）。同じページは /admin/tenant-profile（App.tsx:379、frontend/src/pages/admin/AdminHubPage.tsx:25）と、見積・請求書の作成画面のボタン（frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:219）からも開く。名前は「発行者情報」から「会社情報」に変える（PO 2026-11-10「1」。ideal-state 43）。直す文言は origin/main の frontend/src/locales/ja.json の3つ（:282 メニューの tenantProfile、:2056 ページの見出し title、:2067 保存の知らせ saved「会社情報を保存しました」）と、en.json の同じキー3つ（英語は「Company information」に揃える）。キーの名前は変えない。説明文（ja.json:2057「発注書 PDF / メールの差出人欄に表示される会社情報を設定します」）は「見積書と請求書の PDF に載せる会社情報と振込先を設定します」に直す（発注書は使わないため。PO 2026-11-06）。行番号は 2026-11-11 の origin/main（bfe2e4e7a）で数えた。名前を変えるとこの入口すべてに効く。新しいメニューは作らない。並びは上から、印影・既定の言語（今の欄。会社名の日本語と英語・メール・サイト・住所と電話の自由記入の6欄は外す）、「書類に載せる会社情報」（国内用と海外用を Tabs で切り替える。タブの中は、会社名・メール・サイト・国・5欄・電話・インボイス登録の有無と番号）、「振込先」。英語の今の文言は en.json:282 "Issuer Profile"、:2056 title "Issuer Profile"、:2057 subtitle、:2067 saved "Issuer profile saved"。新しい英語は「Company information」「Configure the company information and payee accounts printed on quote and invoice PDFs」「Company information saved」。権限は今の tenant.profile.view／edit（同ページ :8〜:9）。テナントオーナー専用の設定はこのページに置く決まり（docs/specs/profile-account-settings/README.md の境界）に合う。部品は §3-4a。

**振込先の3表**（PO 2026-11-05「振込先は複数登録できるようにできる？初めにプルアダウンでWise、PayPal、銀行口座で選択するプルダウンを表示させておいて、選択した値によって入力欄が変化する仕組み」「登録ページで登録請求書発行時はプルダウンで選択をイメージしている」）
2段の形（PO 2026-11-10「１」。根拠と外部事例は evidence-payment-methods.md）: 振込先の一覧の表1つと、種類ごとの詳細の表2つ（銀行・Wise）を1対1でつなぐ。3表とも会社ごとのスキーマに置き、置き場・RLS・作成処理への反映は tenant_issuer_profiles と同じ（ポリシー名は表ごとに `<表名>_tenant_isolation`）。
- 種類は bank と wise の2つだけ。PayPal は振込先に入れない（PO 2026-11-09「PayPal→API連携で発行するから不要？」。PayPal の正本は今の public.tenant_paypal_config だけで、この表に PayPal の値を写さない）。Wise の支払いリンクも持たない（PO 2026-11-09「オーダーごとに異なるのでマスタには適さない」）。
- 種類の一覧の正本は、一覧の表の method_type の CHECK（'bank','wise'）の1か所。種類の表は作らない（PO 2026-11-09「1」）。画面の選択肢の文字は t() のキー（種類ごとに1つ）で出す。

**tenant_invoice_payment_methods**（一覧。どの請求書の選択肢に出すかを決める表）
- id、tenant_id（NOT NULL）、region（domestic／overseas）、method_type（NOT NULL。bank／wise）、display_name（プルダウンに出す名前。必須・空文字は CHECK で止める）、sort_order、is_active（既定 true）、updated_by_user_id、created_at、updated_at。
- UNIQUE (id, tenant_id, method_type)。詳細の表が「行の id・会社・種類の組」を外部キーで指すためだけに置く（下の1対1の決まり）。
- 制約には名前を付ける（UNIQUE・外部キー・CHECK）。移行を2回流しても壊れないようにするため。会社ごとの表では、同じ名前の制約が会社の数だけできる。このため「もう有るか」の確かめは名前（conname）だけでなくスキーマ（connamespace）でも絞る。名前だけで確かめると2社目から追加が飛ばされる。先例: migrations/20261103_120000_create_ai_job_assignments.sql:35（UNIQUE (id, job_key)）と :45（FOREIGN KEY (choice_id, job_key)）。どちらの列も NOT NULL（同 :28・:41）。もう1つの先例 migrations/20261022_100000_products_format_in_work_fk.sql:56。主キーがそのまま外部キーになる1対1の詳細の表は、会社ごとのスキーマに先例がある（backend/app/services/tenant.py:303・:324・:643）。

**tenant_invoice_payment_bank**（銀行口座の詳細。一覧の行1つに1行）
- payment_method_id（主キー）、method_type（NOT NULL・CHECK で 'bank' だけ・既定 'bank'）、tenant_id（NOT NULL）、account_holder、bank_name、bank_branch、bank_account_type、bank_account_number、swift_code（任意）、bank_address（任意）、created_at、updated_at。
- 必須（NOT NULL と空文字の CHECK）: account_holder・bank_name・bank_branch・bank_account_type・bank_account_number。swift_code と bank_address は空で保存できる（PO 2026-11-09「1」）。

**tenant_invoice_payment_wise**（Wise の詳細。一覧の行1つに1行）
- payment_method_id（主キー）、method_type（NOT NULL・CHECK で 'wise' だけ・既定 'wise'）、tenant_id（NOT NULL）、account_holder、wise_currency、wise_email、iban、swift_bic、bank_name、bank_address、note、created_at、updated_at。
- 必須: account_holder・wise_currency（CHECK `^[A-Z]{3}$`）・wise_email。任意: iban・swift_bic・bank_name・bank_address・note（PO 2026-11-09 の提案「名義、IBAN、SWIFT/BIC、銀行名と住所、メールアドレス」。メールで送金してもらう運用と読み（AI の読み。ideal-state の読みの記録）、メールを必須にする）。
- 通貨ごとに1行（口座は通貨ごとに分かれている。PO 2026-11-05 の Wise の画面の確認）。

1対1の決まり（DB で止めるもの・処理で止めるもの）:
- 種類の食い違いは DB で止める。詳細の表は (payment_method_id, tenant_id, method_type) で一覧の (id, tenant_id, method_type) を外部キーで指す（ON DELETE CASCADE）。3列とも NOT NULL にする。理由: CHECK は NULL を通し、外部キーも既定（MATCH SIMPLE）では列のどれかが NULL だと確かめない。NULL を許すと種類の食い違いが通ってしまう。詳細の method_type は CHECK で1つの値に固定されるので、bank の一覧の行に Wise の詳細は付けられない。1行に2つの詳細も付けられない（詳細の主キーが payment_method_id）。
- 一覧の行の種類は後から変えられない（変えると外部キーが切れて誤りになる）。種類を変えるときは消して作り直す。画面も同じ動きにする（種類を変えると、他の種類の入力値は保存しない）。API は PUT で今と違う method_type が来たら 422（payment_method.type_immutable）を返し、何も書かない。
- 「一覧の行に詳細が必ずある」ことは、書く口を1つにして守る。足す・直すは1つの取引の中で一覧と詳細の両方を書き、どちらかが失敗したら全部戻す。読む口は一覧と詳細をつないで読み、詳細の無い一覧の行は選択肢に出さず、発行も止める（409 payment_method）。DB の遅らせる見張り（CONSTRAINT TRIGGER の DEFERRABLE）は使わない。理由: リポジトリの migrations と backend/app に先例が0件（2026-11-10 git grep）。
- 消せる。一覧の行を消すと詳細も消える（CASCADE）。発行済みの請求書は写しを持つので変わらない。使わなくするだけなら is_active を false にする。
  - （ADR-1079 で改める）消すと隠れるが行は残る（deleted_at を入れる）。直すと新しい版を足す。一覧と詳細の行は DB の見張りが消すことと中身を直すことを断る。種類や地域を変えるのは「消す＋足す」。見張りが断ったとき（P0001）は 500 にせず 409 か 422 の理由コードに置き換える。正: docs/handoff/invoice-create-portfolio/design.md §3-8
- 請求書から振込先の行へ外部キーは張らない。理由: 請求書は public の1つの表で、振込先は会社ごとに別のスキーマの表にある。外部キーは参照先の表を1つに決める必要があり、会社の数だけある表を1本の外部キーで指せない。会社ごとの表から public を指す向きの外部キーは先例がある（tenant.py:518・:605）が、今回は逆向き。発行時の写し（issuer_snapshot）に振込先の全項目と行の id を残す。
- 変更の履歴: 会社情報と振込先の3表（一覧・銀行・Wise）を足す・直す・消すたびに、会社ごとの audit_logs（tenant.py:484〜:494）へ record_audit_log（backend/app/services/audit.py:277）で1行残す。一覧と詳細は1つの記録にまとめる。old_data と new_data には全項目を入れ、bank_account_number と iban だけは下4桁にする（全桁を履歴に広げないため。表示の伏せ方は PCI DSS の「見せるのは下4桁まで」を手本にする。evidence-payment-methods.md）。画面に履歴の一覧は今回作らない。
- 編集できる人: tenant.profile.edit を持つ人（会社情報と同じ）。オーナーだけに絞らない（PO 2026-11-10「1」。ideal-state 41）。
- Wise のメール送金の公式の決まり（Wise ヘルプ How can I send money to an email address?）: 受け取る側は7日以内に受け取りの手続きをする。100万円を超える送金、USD の Global Swift あて、Swift の口座情報あてはメールで送れない。閲覧者の請求書は 220,000円で、この上限の内側。
- 画面の注意書き: Wise の円の入金用の口座情報は本人名義の口座からの入金専用で、お客さんの振込先に使えない（Wise ヘルプ Paying to our Wise JPY pay-in account）。
- 未確認: お客さんがメール送金で払った日本円が実際に入金されるか。テストの支払いで確かめる（§11 の⑥）。
- 手数料が引かれて入金額が請求額より少ない場合の扱いは設計しない。入金確認は今の設計のまま入金日だけを記録する。

**viewer_invoice_lines**（明細）
- id、invoice_id（CASCADE）、line_type（item／discount）、description、amount_jpy、sort_order。ADR-101 の2表に分ける形に合わせる。

既存の表への追加:
- tenant_google_drive_config: overseas_folder_id（今回は使わない）。既存の folder_id を国内用と定める（どこからも書かれていないことを確認済み。recon §8）。

隠す設定（相談係の道 ai_cloud・ai_reader_cloud。ADR-1052 決定5。Mac の AI の道 ai_ro は口座番号だけ隠す。下の段落）: 新しい個人情報の列と、tenant_issuer_profiles・tenant_invoice_payment_methods・tenant_invoice_payment_bank・tenant_invoice_payment_wise の全項目（決まった値しか入らない列を除く）は隠す設定にする。新しい移行ファイルは作らず、既存の migrations/20261024_100300_create_ai_cloud_views.sql の :300・:573 と同じ形の行を足す（会社ごとの表は 'tenant_*' の行で足す）。このファイルは scripts/migration-guard/reference-allowlist.tsv:7 に sha256 で登録されているので、同じ変更で sha256 と理由の欄を直す。個人情報の表の一覧（migrations/20261031_210000_create_ops_case.sql:102）にも足す。
- Mac の AI の道 ai_ro からも、口座番号だけを隠す（PO 2026-11-11「2」。ideal-state 48）。これは ADR-1052 の「Mac の道は変えない」を、口座番号の2列に限って改める決定で、ADR-1061 に書く。会社名・メール・電話・宛先の写しなど他の項目は ai_ro では今までどおり見える（今ある請求先の表 viewer_billing_profiles と同じ扱い）。
  - 隠す列: tenant_invoice_payment_bank.bank_account_number と tenant_invoice_payment_wise.iban。
  - 隠し方: 列名の拒否の一覧（正規表現）に `account_number` と `^iban$` を足す。新しい拒否の一覧は `^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential|account_number|^iban$`。
  - 今この2つに当たる列: account_number を含む列は tenant_carrier_credentials.account_number_encrypted だけで、既に `_encrypted$` で隠れている。iban の列は無い（2026-11-11 origin/main の migrations と backend/app/services/tenant.py を git grep。4行。生出力 /tmp/CC報告ファイル/contract-status/deny-columns-1111.txt）。足しても今見えている列は減らない。
  - 拒否の一覧は今5か所に同じ文字で書かれている（origin/main）: (a) migrations/20261017_130100_create_ai_ro_views.sql:23（ai_ro を作る SQL。scripts/run_all_migrations.sh の終わりで毎回作り直す） (b) migrations/20261024_100000_create_ai_cloud_meta.sql:76（相談係の道を作る処理の中。run_all_migrations.sh:1199 で毎回流れる） (c) backend/app/ops/readonly_query.py:42 の DENY_COLUMN_RE（Mac の読み取りの道が結果の列を落とす） (d) backend/tests/ops/test_ai_cloud_views.py:43 (e) backend/tests/ops/test_ai_ro_views.py:30。
  - 変え方: (a)(b)(c) の3か所を同じ変更で新しい一覧に直す。試験の (d)(e) は自分で文字を持たず、(c) の DENY_COLUMN_RE を import して使う形に直す（書く場所を5か所から3か所に減らす）。SQL の2か所は Python から読めないので、新しい試験 backend/tests/ops/test_deny_column_regex_sync.py で (a)(b) のファイルを読み、`deny constant text := '…'` の文字が DENY_COLUMN_RE.pattern と同じことを確かめる（A46）。
  - (a)(b) は毎回流れる SQL なので、新しい移行ファイルは作らない。反映は便2 の配備の後の作り直しで起きる。(a)(b) は scripts/migration-guard/reference-allowlist.tsv に載っていない（登録は 20261024_100300 の1行だけ。2026-11-11 確認）。
  - 相談係の道（ai_cloud）では、この2列は今までの「隠す設定」より前に拒否の一覧で列ごと外れる。値が見えない点は同じ。

最初の行（移行では入れない。ADR-1007 決定1）:
- 中身: 商材「在庫解析ツール」、プラン「在庫解析の閲覧とシート配信」、買い切り、200,000円（税抜）、機能2つ、既定の支払日数 3。発行元の会社は HIGH LIFE JPN（2026-11-05 PO「1」）。
- 入れ方: 便2b の本番反映の後、PO が「商材とプラン」の画面（§3-4d）で入れる（§4 の（２）。前の版の「1回だけのデータの変更」の案から変えた。PO 2026-11-11「1」で決まった。ideal-state 51）。発行元の会社は画面の選択肢から会社名で選ぶ。
- 試験は自分で行を用意する（試験の fixture）。本番の値を試験から読まない。

RLS（ADR-1018 の段階①の型。会社ごとの4表は今の会社ごとの表と同じく ENABLE だけで FORCE は付けない。tenant.py に FORCE は0件）: 新しい public の表（sa_products・sa_plans・sa_plan_features・sa_contracts・tax_rates・viewer_invoices・viewer_invoice_lines・viewer_invoice_number_seq・prefectures）は、読むのは全行可、書くのは `app.is_operator='true'` のときだけにする。ENABLE と FORCE を付ける（ADR-1018 Decision 3）。
- 理由: どの表も書くのは運営（最高管理者の画面と、その発行に続く裏の処理）だけ。閲覧者や会社の人が書く経路は無い。請求書は金額と宛先を持ち、アプリの書き間違いを DB で止める価値がある。
- 閲覧者の名簿と請求先（migrations/20261105_120000_create_viewer_billing_profiles.sql:2）は RLS を付けていない。こちらは閲覧者本人のフォームから書くので型が違う。
- 書く処理は set_operator_context で運営の印を張り、終わりに reset_operator_context で外す（先例 backend/app/routers/super_admin_tenants.py:50・:93、backend/app/routers/super_admin_suppliers.py:69・:73）。backend/app/tasks/fx_rate_updater.py:70 は接続の間ずっと効く `SET app.is_operator = 'true'` を直接流す古い形で、写さない。
- 決まりは2本に分ける（先例 migrations/20260628_170000_add_app_fx_rates.sql:51〜:63）。読む決まり `FOR SELECT USING (true)` と、書く決まり `FOR ALL USING (運営の印) WITH CHECK (運営の印)`。1本の FOR ALL で読みも通す形にすると DELETE が通るので取らない。
- 運営の印が無いときの動き（PostgreSQL 16 公式文書 Row Security Policies 5.9。2026-11-06 確認。Context7 は月の上限で使えず、公式文書を直接読んだ）:
  - INSERT は WITH CHECK に当たり、誤り（new row violates row-level security policy）で止まる。
  - UPDATE と DELETE は USING で行が見えず、誤りにならず0行になる。書く処理は変えた行数が1でなければ誤りとして止める。
- 外部キーの確かめは RLS を通らない（同文書「Referential integrity checks … always bypass row security」）。名簿を消したときの SET NULL が FORCE の RLS の下で効くかは、文書に直接の記載が無いので A14 で確かめる。
- 権限は migrations/20261105_120000_create_viewer_billing_profiles.sql の GRANT と同じ形で salesanchor_app に渡す。

### 3-4a. 画面の部品（金型）

| 使う場所 | 金型（frontend/src/components/） |
|---|---|
| 文字の欄（会社名・郵便番号・市区町村・住所・電話・メール・サイト・番号・口座の項目） | TextField.tsx（今のページの TextFieldControl。TenantProfilePage.tsx:26） |
| 国 | CountryCombobox.tsx（frontend/src/pages/register/ にある同名の部品ではなく components の方） |
| 都道府県・振込先の種類・作成画面のプランと振込先・口座の種類 | Select.tsx |
| 国内用と海外用の切り替え | Tabs.tsx |
| インボイス登録の有無 | Toggle.tsx |
| デフォルトとして保存 | Checkbox.tsx |
| 請求書の作成・入金確認・再発行 | Modal.tsx |
| 「前の会社情報」（古い値を読むだけで見せる欄） | Textarea.tsx（今のページの TextareaControl。TenantProfilePage.tsx:25）を readOnly で使う |
| 入れ直しの案内 | Callout.tsx |
| 自由に書く欄（Wise の note・bank_address） | Textarea.tsx |
| 行の三点ボタン | 新設の MoreMenuButton（§3-3。PO 2026-11-12「1」） |

- 新しい画面の部品は別ファイルに置く: IssuerProfileSection.tsx（書類に載せる会社情報の区切り。国内用と海外用のタブ）、InvoiceRegistrationField.tsx（タブの中の登録の欄）、PaymentMethodList.tsx、PaymentMethodForm.tsx、TaxRatesPage.tsx、ViewerInvoiceCreateModal.tsx、ViewerPaymentConfirmModal.tsx、SaProductsPage.tsx（§3-4d）。
- 色と寸法はトークンだけ（ADR-067）。文字はすべて t()（ADR-027）。生の select・input・自作タブは使わない（ADR-144）。

### 3-4b. API の約束（ADR-113 の「契約・API 仕様」）

会社の人（今の会社情報と同じ口。/api/v1 の下。権限 tenant.profile.view で読む・tenant.profile.edit で書く）:

| 方法 | 道 | 中身 |
|---|---|---|
| GET | /admin/issuer-profiles | 国内用と海外用の行（無い方は null）と、古い6列の値（読むだけ） |
| PUT | /admin/issuer-profiles/{region} | 片方の行を丸ごと保存。決まり違いは 422 と欄ごとの理由 |
| PUT | /admin/tenant-profile（今の口） | 印影・既定の言語。会社名の2つ・メール・サイト・address・phone は受け取らない（項目から外す） |
| GET | /admin/invoice-payment-methods?region= | 振込先の一覧（sort_order 順） |
| POST | /admin/invoice-payment-methods | 1件足す。種類ごとの必須が無いと 422 |
| PUT | /admin/invoice-payment-methods/{id} | 1件直す |
| DELETE | /admin/invoice-payment-methods/{id} | 1件消す |
| GET | /prefectures | 都道府県の一覧（ログイン済みなら誰でも） |
| PUT | /integrations/google-drive/folder | 国内用の保存先。drive_url を受け、extract_folder_id で番号を取り folder_id に入れる。番号が取れなければ 422。権限は今の連携の口と同じ require_tenant_admin（backend/app/routers/integrations.py:196） |

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
| DELETE | /super-admin/tax-rates/{id} | 明日（日本時間）以降の適用日の行だけ消せる。それ以外は 409 |

- 運営の閲覧者の一覧（GET /super-admin/viewers。super_admin_viewers.py:196）に、行ごとの contract_status・invoice_id・invoice_number・invoice_status・due_date・mail_status（sent／failed／none）・drive_status（saved／failed／none）を足す。行のボタン（作成・入金確認・もう一度送る・もう一度保存）は viewer_accounts.status・form_sent・invoice_status・mail_status・drive_status で出し分ける。contract_status は sa_contracts.status を表示に使うだけで、ボタンの判定には使わない（§3-1。停止中の手続き中の人にボタンを出さないため）。

送る項目と返す項目（型は Pydantic。名前は DB の列名と同じにする）:

| 道 | 送る | 返す |
|---|---|---|
| PUT /admin/issuer-profiles/{region} | company_name・email・website・country_code・postal_code・prefecture_code・state_region・city・address1・address2・phone・is_invoice_registered・registration_number（無のとき番号を送っても NULL で保存） | 保存した行の全項目と updated_at |
| POST・PUT /admin/invoice-payment-methods | 一覧の項目（region・method_type・display_name・sort_order・is_active）と、method_type と同じ名前の入れ物に詳細の項目（bank: {account_holder…bank_address}、wise: {account_holder…note}）。method_type と違う名前の入れ物が来たら 422 | 保存した行の全項目（一覧と詳細を1つにまとめた形） |
| GET /prefectures | なし | code・name_ja・name_en・sort_order の配列 |
| GET /super-admin/viewers/{viewer_id}/invoice-draft | なし | plans（id・name・unit_price_jpy）・bill_to・payment_methods（id・display_name・method_type。domestic の行。Wise は wise_currency が JPY の行だけ）・default_due_date・tax_rate_percent |
| POST /super-admin/viewers/{viewer_id}/invoices | plan_id・payment_method_id・discounts（description・amount_jpy の配列）・due_date・save_default | 請求書の行（id・invoice_number・金額の6項目・status・mail_status・drive_status） |
| POST …/confirm-payment | paid_at（日付） | 請求書・契約・閲覧者の新しい状態 |

- 誤りの形は今の口と同じ（detail に理由）。発行と再発行の前の確かめで、発行元の行・振込先・文面・発行日に有効な税率の行のどれかが足りないときは 409 と足りない項目の一覧を返す。一覧は項目の名前（キー）の配列で返し、画面が t() で文に直す（ADR-027。detail に日本語の文を入れない）。キーは issuer_profile（国内用の行）・registration_number（国内用の行で登録が有のとき）・payment_method・mail_template・tax_rate の5つ。会社名は行の必須の列なので、行があれば空にならない。もう一度送るで文面が無いときは今の口と同じ 503。

### 3-4d. 商材とプランの登録画面・税率の画面の置き場

PO の決定（2026-11-09「2」で今回作る。中身は 2026-11-09「1」）: 最高管理者のみ・税率の画面と同じ場所・商材と料金を足せる・名前と金額を後から直せる・消さずに「使わない」へ切り替える・発行済みの請求書の金額は写しのまま。

置き場（2026-11-11 に PO の決めた運営のメニューの組み替えに合わせて直した。組み替えは本番反映済み。設計 docs/handoff/super-admin-settings-hub/design.md、PO 2026-11-11「1、LINE解析に入っているマスタも全体設定に移動させてくれ」）:
- 税率の画面と商材とプランの画面は、左メニュー「全体設定」の中の小さなメニュー「金額の設定」に置く。項目の正本は frontend/src/pages/super-admin/settings/settingsNav.ts:11〜:15（fx-rate・tax-rates・sa-products）で、今回この並びは変えない。前の版の「閲覧者の一覧の見出しのボタンから開く」案は取らない。
- 道は /super-admin/settings/tax-rates と /super-admin/settings/sa-products。今は frontend/src/App.tsx:327〜:344 で2つとも「準備中」の画面（ComingSoonPage）を出している。この2つの element を TaxRatesPage と SaProductsPage に差し替えるだけで、道とメニューは足さない。
- 2つの画面は全体設定の中（SettingsHubPage の Outlet）に出るので、一覧へ戻るボタンは置かない（小さなメニューで移れる）。
- 全体設定の入口（SettingsHubPage）が、最高管理者でない人には中身を出さず「権限がありません」を出す。そのうえで、2つの画面の中でも useSuperAdmin を使い、最高管理者でなければ「権限がありません」（superAdmin.accessDenied）を出す（FxRatePage と同じ二重の守り）。
- 画面の見出しの名前は、メニューと同じ nav.superAdminTaxRates・nav.superAdminSaProducts のキーを使う（言葉の正本を2つに分けない）。
- テンプレートの画面（/super-admin/users/viewer-templates）は利用者管理の側のまま、閲覧者の一覧の見出しの「テンプレート」ボタンから開く（変えない）。

商材とプランの画面（SaProductsPage.tsx）:
- 一覧: 商材ごとに1行（DataTable）。列は 名前・コード・発行元の会社・既定の支払日数・状態（Badge で「使う」「使わない」）・プランの数。使わないの行も出す（灰色の Badge）。
- 商材の行を押すと Drawer が開き、その商材の項目とプランの一覧を出す。プランの列は 名前・コード・請求の種類（1回だけ／毎月／毎年）・金額（税抜の円）・含む機能・状態。
- 足す: 見出しの「商材を足す」ボタンと Drawer の中の「プランを足す」ボタンで Modal を開く。
- 直す: 行の「直す」ボタンで同じ Modal を開く。後から直せるのは、商材は 名前・既定の支払日数・使う/使わない、プランは 名前・金額・含む機能・使う/使わない。コード・発行元の会社・請求の種類と間隔は作った後は直せない（欄を読むだけで見せる）。請求書の写しと契約の記録の意味が後から変わらないため。
- 消すボタンは作らない（PO「消さずに使わないへ」）。
- 使わないにした商材のプラン、使わないにしたプランは、請求書の作成画面の選択肢（GET …/invoice-draft の plans）に出さない。作った請求書の金額は写し（viewer_invoices の金額の列）なので、プランの金額を直しても変わらない。
- 部品（frontend/src/components/ の金型だけ）: PageLayout・DataTable・Drawer・Modal・TextField（コード・名前・日数・金額）・Select（発行元の会社・請求の種類）・Checkbox（含む機能。1つずつ）・Toggle（使う/使わない）・Badge・Button・EmptyState・LoadingBlock・Callout（誤りの知らせ）。生の select・input は使わない（ADR-144）。色と寸法はトークンだけ（ADR-067）。
- 文字はすべて t()（ADR-027）。キーは superAdmin.saProducts.* と superAdmin.taxRates.* に置き、ja.json と en.json に同じキーを足す。含む機能の名前は superAdmin.saProducts.features.inventory_view・…sheet_distribution（日本語は「在庫の閲覧」「シートの配布」。英語は "Inventory view"・"Sheet distribution"）。

含む機能の一覧の正本:
- sa_plan_features.feature_key の CHECK（'inventory_view','sheet_distribution'）を正本にする。API は値をこの2つに限り（Pydantic の Literal）、画面は t() の名前を出すだけで一覧を別に持たない。機能を足すときは CHECK を変える移行と Literal と2つの言葉のファイルを同じ便で直す。A45 の試験で Literal と CHECK の並びが同じことを確かめる。

API（/api/v1 の下。すべて dependencies=[Depends(require_super_admin)]。今の backend/app/routers/super_admin_viewers.py:199 と同じ付け方。書く処理は app.is_operator='true' を付けて行う §3-4 の RLS の決まりに従う）:

| 方法 | 道 | 送る | 返す・誤り |
|---|---|---|---|
| GET | /super-admin/sa-products | なし | products（id・code・name・seller_tenant_id・seller_tenant_name・default_payment_days・is_active・plans[id・code・name・billing_type・billing_interval・unit_price_jpy・is_active・feature_keys]）。使わないの行も含む。sellers（public.tenants の id・tenant_name・is_active。発行元の選択肢） |
| POST | /super-admin/sa-products | code・name・seller_tenant_id・default_payment_days | 作った商材。code が重なると 409 sa_product.code_taken。seller_tenant_id が無い会社なら 422 sa_product.seller_not_found |
| PUT | /super-admin/sa-products/{id} | name・default_payment_days・is_active | 直した商材。code・seller_tenant_id を送ると 422 sa_product.immutable |
| POST | /super-admin/sa-products/{id}/plans | code・name・billing_type・billing_interval・unit_price_jpy・feature_keys | 作ったプラン。商材内で code が重なると 409 sa_plan.code_taken。one_time で billing_interval を送る、subscription で送らないと 422 sa_plan.billing_interval_mismatch |
| PUT | /super-admin/sa-plans/{id} | name・unit_price_jpy・is_active・feature_keys | 直したプラン。code・billing_type・billing_interval を送ると 422 sa_plan.immutable。feature_keys は丸ごと入れ替える（1つの取引で消して入れ直す） |

- 値の決まり: code は英小文字・数字・ハイフン・下線の1〜50字。name は1〜100字。default_payment_days は1〜90の整数。unit_price_jpy は0以上の整数（税抜）。feature_keys は0個以上で重なり無し。
- 誤りの detail はキー（例 sa_product.code_taken）で返し、画面が t() で文にする（§3-4b と同じ）。
- PUT の受け取りの形（直せない項目の扱い）: 2つの PUT の受け取りの形は、直せない項目（商材は code・seller_tenant_id、プランは code・billing_type・billing_interval）も「省いてよい欄」として持つ。処理の最初で、どれかが送られていたら何も書かずに 422（sa_product.immutable／sa_plan.immutable）を返す。表に無い欄が来たら受け付けない（model_config = ConfigDict(extra="forbid")。今の書き方 backend/app/routers/ops.py:352 と同じ）。直せない項目を形から外すだけだと、送られても黙って捨てられ 422 にならないため。
- DELETE の道は作らない。
- 一覧の発行元の会社の名前は public.tenants を読むだけで、別に写さない（配線とデータの正本は tenants）。super_admin_tenants.py には今 DELETE の道しか無いので、会社の一覧は GET /super-admin/sa-products の sellers で一緒に返し、新しい会社一覧の口は作らない。

税率の画面（TaxRatesPage.tsx）の置き場と道は上のとおり（/super-admin/settings/tax-rates）。中身は §3-4 の tax_rates と §3-4b の /super-admin/tax-rates のとおり。

### 3-4c. 他のテーマとの境界

- 見積もりと B2B の請求書（docs/specs/quote-invoice/ideal-state.md、ADR-101）: B2B は会社ごとの invoices の表に issuer_region の1列を足す以外は触らない（§3-4）。そちらにある PayPal と Wise の支払い方法（同 ideal-state.md の支払い方法の段落）とこの振込先の表を1つにするかは、海外の請求書の設計で決める。それまでは閲覧者の請求書だけがこの表を読む。
- 会社のプロフィールとアカウント設定（docs/specs/profile-account-settings/README.md の境界）: テナントオーナー専用の設定はプロフィールのページに統合する決まりに合わせ、会社情報のページを直して区切りを足す。独立した画面は作らない。

### 3-5. 請求書の作成と計算

作成画面（Modal）の項目:
- プラン（Select）、宛先（請求先の表示のみ）、振込先（Select。国内用に登録した行から1つ選ぶ。必須。既定の選択は持たない。Wise は通貨が JPY の行だけを出す）、値引きの行（名目と金額。行を足せる）、支払期限（既定は発行日＋既定日数。直せる）、□デフォルトとして保存、計算結果。
- 振込先が1件も無いときは発行できない。登録ページへの案内を出す。
- PDF の振込先の欄は選んだ種類の項目だけを出す。Wise はメールと、入っていれば IBAN・SWIFT/BIC・銀行名・銀行の住所を文字で載せる。PayPal は振込先に無い。

計算:
1. 小計 = プランの税抜金額。
2. 値引き合計 = 値引きの行の合計。小計を超えると作れない。
3. 課税対象 = 小計 − 値引き合計。
4. 税額 = 課税対象 × 税率。1円未満は切り捨て（PO 2026-11-12「1」。ideal-state 53）。請求書ごと・税率ごとに1回。
5. 合計 = 課税対象 + 税額。

- 「初月無料」は、名目を「初月無料」とした値引きの行で登録する。今の買い切りプランでは月の概念が無いので、専用の計算は作らない。
- %指定の値引きは作らない。金額で入れる（PO 2026-11-12「1」。ideal-state 53）。
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

- 必須項目（国内用の行。登録が有のときは登録番号も。振込先は作成画面で1つ選んだ行）が無いときは、発行を止めて、足りない項目を画面に出す。
- フォントが日本語で登録できないときは発行を止める。Helvetica に落とすと文字が化けるため。新しい PDF の処理では代わりのフォントを使わない。
- メールの失敗: 行に「送信失敗」と「もう一度送る」を出す。SMTP 未設定も失敗として扱う。今のフォームのメールのように黙って捨てない。
- ドライブの失敗: 行に「未保存」と「もう一度保存」を出す。発行とメールは止めない。
- PDF はデータベースに持たない。写しの行から同じものを作り直す。見た目を後で変えると作り直しの見た目も変わるため、原本はドライブのファイルとメールとする。写しの保存の要件は、記載事項が確かめられる記録でよい（国税庁 インボイス Q&A 問78。viewer-customer-sheet design §3-4）。
- PDF の処理は B2B の invoice_renderer.py に足さず、新しいファイルにする。B2B は輸出向けで項目が違うため。フォント登録の処理だけ共用する。
- メールの添付は auth_mail.py に新しい関数を足す（MIMEMultipart("mixed")）。文面は viewer_message_templates の台帳に invoice_send・invoice_reissue を足す。宛先は請求先の invoice_email、無ければ名簿のメール。**文面は PO が文面ページで保存するまで送れない**（発行の前は 409 で止める。もう一度送るは既存の 503 と同じ動き。§3-4b）。

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
  - 今あるフォルダへ保存できた → 上の形のまま。**こちらに決まった（2026-11-06 PO のテスト保存。§7-1）**。
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
- 公開と効き始めの順番（PO 2026-11-07「2」）: ポリシーには「大事な変更は14日前までに知らせる」（lp/src/pages/privacy.astro §12.1）とある。LP は main へのマージで本番に出る（.github/workflows/deploy.yml の Build LP）。消す処理の変更も同じマージで本番に入るが、今の決まり（90日）で最初に消える日は 2026-12-19（recon §4 の本番件数。2026-11-07 の数え直しで停止の人は0件）。それより前は今の決まりでも消える行が無いので、新しい決まりが実際に違いを生むのは 2026-12-19 から。ポリシーの改訂日から 2026-12-19 までが14日以上あれば約束を守れる。改訂日はマージの日にする。ポリシーの文面そのものも §12.1 に合うよう、効力発生日は「改訂日から14日以上あと、かつ 2026-12-19 以前」にする（審査 2026-11-07 の指摘(1)で直した。前の版は効力発生日 12-01 とマージ期限 12-05 が食い違っていた）。便1 のカードは効力発生日 2026-12-01 で書き、2026-11-17 までにマージする。（済み：PR #5250、2026-11-07T16:13:29Z マージ）間に合わないときは、マージの前に効力発生日を「マージの日＋14日」に直す。それが 2026-12-19 より後になる（マージが 2026-12-05 より後になる）なら止めて PO に戻す。
- 知らせ方（§12.1 の4つ: 画面の通知・登録アドレスへのメール・サイト掲載・14日の期間）: §12.1 の対象は "Users"（取引先会社の担当者）と "End Users" と定義されている（privacy.astro の冒頭）。閲覧者はどちらの定義にも書かれていない。閲覧者にはメールを送らず、サイトに載せるだけにする（PO 2026-11-07「2」）。
- 停止の人で停止の記録が無い行は消さない（今と同じ）。
- お試しから契約手続き中への状態（contracting）は便2で作る。便1の消す条件は trial と suspended だけを直し、contracting は便2の指示書で足す。

## 4. 便の順番

| 便 | 中身 | 利用者に見える変化 | 期限 |
|---|---|---|---|
| 1 | 3年残す・公開ポリシー | ポリシーの文 | 済み（PR #5250、2026-11-07T16:13:29Z マージ。効力発生日 2026-12-01・改訂日 2026-11-08・v1.8） |
| 2 | 状態・表・税率画面・会社情報のページの住所と登録と振込先・今の書類の読み先の切り替え・フォーム3日 | 会社情報のページと税率の画面 | |
| 3 | 請求書（作成・PDF・メール・ドライブ・再発行・入金確認） | まだ押せない（手続き中の人がいない） | |
| 4 | ボタンの切り替え・三点・直接移す道の削除 | 全部 | PO の入力とテストの後 |
| 2b | 商材とプランの登録画面（§3-4d） | 最高管理者の「商材とプラン」の画面 | 便2 の後・便3 の前 |

- 便2 は 2-1（契約手続き中の状態の土台：状態を足す移行・状態を読む全部の場所・フォーム3日と期限の自動延長・送った記録）と、2-2 以降（表・税率の画面・会社情報のページ）に分けて作る（1便1目的。移行を戻すときの範囲を小さくするため。指示書 card-2-1.md の D1）。
- 便2 の移行は危険な変更に当たる。ADR-136 の手順で GO を記録する。
- 便2 の本番反映の後、便3 の前に行うこと（ADR-1007 決定1 の道。移行では値を入れない）:
  （１）都道府県47行を「1回だけのデータの変更」で入れる（PO の合意 → DRY-RUN → COMMIT）。
  （２）便2b の本番反映の後、PO が「商材とプラン」の画面で最初の商材・プラン・機能を入れる（前の版の「1回だけのデータの変更」で入れる案から変えた。画面で入れられるようになったため。PO 2026-11-11「1」で決まった。ideal-state 51）。
  （３）PO が税率の画面で 10%・2019-10-01 の行を足す。
- 便2 の本番反映の後に PO が行うこと: 会社情報のページで国内用と海外用の会社名・メール・サイト・住所・電話を入れ直す。入れ直すまで今の書類は古い値で出る（§3-4）。
- 便4 の前に PO が行うこと: インボイス登録と振込先の入力、文面2つの保存、保存先の指定。
- 古い6列（会社名の2つ・メール・サイト・住所・電話）を消す移行は、§3-4 の「古い6列を消すまでの計画」の（２）（３）が済んでから、別の便で行う。

## 5. 代替案と選んだ理由

- 期限を別の列にする案 → 取らない。同じ意味の値が2つになる。
- 段階を列で持つ案 → 取らない。履歴と請求書の行と食い違う恐れがある。
- B2B の invoices を使う案 → 取らない。会社ごとの表で、閲覧者は会社の外にいる。PO の方針（docs/handoff/viewer-customer-sheet/design.md §3-4）。
- 税率をプランに持つ案 → 取らない。税率の変更でプランを全部直すことになる。
- 振込先と登録番号を会社情報に足す案（PO の最初の答え）→ PO が国内用と海外用を分けると決めたので置き換えた。
- 請求書のためだけの発行元の表（会社名・住所・電話・メール・サイト）を会社情報と別に持つ案（前の版）→ 取らない（PO 2026-11-06「1」）。同じ会社名と住所が2か所になり、直し忘れで書類ごとに食い違う。
- メールとサイトを会社に1つ、インボイス登録を会社に1つにする案（前の版。PO 2026-11-06「2」）→ 取りやめた。PO が同日に国内用と海外用で分けると改めた（ideal-state の 25）。分社すると会社名・登録番号が国内と海外で別になるため。
- 古い住所を新しい5欄へ機械で写す移行 → 取らない。1欄の自由記入を欄に分ける決まりが無く、誤って分けると書類の住所が壊れる。PO が入れ直す。
- 国内用と海外用を別の表にする案 → 取らない（PO 2026-11-06「1」）。同じ種類の欄が2つの表に分かれ、直す場所が2か所になる。
- 住所の表と登録の表を分けたまま、会社名・メール・サイトの表をもう1つ足す案 → 取らない。どれも region ごとに1つの値で、同じ単位の項目が3つの表に分かれる。1行にまとめると、書類が読む行が1つになる。
- 作る画面のプルダウンで国内向けか海外向けを選ぶ案（前の版）→ 取りやめた（PO 2026-11-06「顧客情報の住所で自動的にシステムが判断する仕組みに出来る？」）。人が選ぶと、取引先の国と食い違う書類ができる。
- 取引先の国を、PDF を出すたびに読み直して決める案 → 取らない。取引先の国を後で直すと、作り済みの書類の会社情報が入れ替わる。作るときに1回決めて書類に持つ。
- 都道府県を画面の定数と DB の CHECK に並べる案 → 取らない（§3-4 の案B）。
- 請求書の PDF をデータベースに持つ案 → 取らない。表が太る。ドライブとメールに原本がある。ドライブが切れたまま発行した場合は写しの行で足りる。
- 振込先を1つの表に全種類の欄を並べる案（前の版）→ 取りやめた（PO 2026-11-10「１」）。種類が違う欄が空のまま並び、必須の決まりを1本の長い CHECK で書くことになる。GitLab は同じ形（1表に種類の列）を新しい表で使わないと決めている（evidence-payment-methods.md の F1）。
- 種類ごとに完全に別の表（一覧を持たない）にする案 → 取らない。請求書の選択肢・並び順・使う/使わないを2か所で持つことになり、種類が増えるたびに読む口が増える。
- 種類ごとの欄を1列の JSON にまとめる案 → 取らない。必須や形の決まりを DB の CHECK で止めにくく、口座番号の伏せ方も項目名で決められない。
- 一覧に詳細が必ずあることを DB の遅らせる見張り（CONSTRAINT TRIGGER）で止める案 → 取らない。リポジトリに先例が0件（2026-11-10 git grep）。書く口を1つにして1つの取引で両方を書き、A44 の試験で守る。
- PayPal を振込先の表に入れる案（前の版）→ 取りやめた（PO 2026-11-09）。PayPal は API で請求書を出すので、口座の値を持つ必要が無い。持つと public.tenant_paypal_config と2か所になる。

## 6. リスクと対処

- **3年保持と個人情報の決まり**: 今の公開ポリシーは90日で消すと書いており、申込済みの人はその前提で登録した。再登録防止は今の利用目的に無い。ガイドライン 3-1-2 は、変更は関連のある範囲で通知か公表が要ると定める。関連のある範囲と言えるかは**未確認**。専門家の確認は行わないと PO が決めた（2026-11-07「2」）。
- **古い値が残る間**: 入れ直すまで、今の書類は古い値で出て、閲覧者の請求書は発行できない。画面に入れ直す案内を出す。古い6列を消すのは数えてから（§4）。
- **今の書類の住所の書き方が変わる**: 入れ直した後は、欄を決まった順でつないだ文字が載る。電話はハイフンなしになる。B2B の請求書の見た目を、切り替えの前と後で比べる（A41）。会社名・メール・サイトも、その region の行を入れた後はその行の値に変わる。その region の行が登録有のときだけ、B2B の請求書に登録番号の1行が載る（PO 2026-11-07、ideal-state 29）。見積書には載らない。発注書と FedEx の申請書は切り替えないので変わらない。
- **ドライブが切れている**: 発行とメールは進み、「未保存」と出る。週1回の見守りで知らせる。
- **メールが届かない**: 「送信失敗」と出す。届いたかの確認は SMTP の受付までで、相手の受信は分からない。
- **二重発行**: 有効な請求書は契約に1件まで（部分一意索引）。
- **切り替え前に誤って手続き中へ移す**: 便4 まで「契約に進む」の道を画面に出さない。
- **別のメールかつ別の Discord の再登録**: 防げない。recon で確認済みの限界。
- **振込先の書き換えによる詐欺**: 振込先を差し替えた請求書で、お金を別の口座へ送らせる手口がある（日本航空 2017年 約3.8億円など。evidence-payment-methods.md の F3・F4）。対処: 振込先を直せる人を絞る（§7-2 の確認項目）、足す・直す・消すを全部 audit_logs に残す（A32）、発行済みの請求書は写しで固定し後から変わらない（A26）。直したときに他の人へ知らせる仕組みは今回作らない（Xero でも利用者から要望が出ている段階。F5）。
- **他の会社の振込先が見える**: 会社ごとのスキーマと RLS で分ける（A21）。外の事例では RLS の付け忘れで 1,645 件中 170 件のアプリの表が外から読めた（F6）。新しい4表は A22 で全会社の RLS の有無を比べる。

## 7. PO に決めてもらうこと

### 7-1. 設計の前提（答えが無いと設計合格にならない）

- ~~請求書の発行元の会社~~ → HIGH LIFE JPN に決定（2026-11-05 PO「1」）。
- ~~発行元がインボイスの登録事業者か~~ → 登録なしと回答（2026-11-05 PO「2」）。番号は有のときだけ必須にする形に決定。
- ~~登録の有無の欄が指すもの~~ → インボイスの登録（T の番号を持つ登録）とする。PO が 2026-11-06 に「インボイス登録」と書いたため。画面の欄の名前は「インボイス登録番号」に決まった（§7-2）。
- ~~テスト保存の結果~~ → 今あるフォルダへ保存でき、指定したフォルダにファイルがあった（2026-11-06 PO「1」。選択肢の「1. 保存でき、指定したフォルダにファイルがあった」）。§3-8 の分岐は「今あるフォルダへ保存できた → 上の形のまま」に決まる。Picker は足さない。設計担当は画面を見ていないので、PO の報告を根拠とする。

- ~~発行元（HIGH LIFE JPN）が消費税の課税事業者か~~ → 消費税を納めていると回答（2026-11-06 PO「1」。PO の回答で、申告書の照合はしていない）。§3-5 の常に10%を足す形のまま。

- ~~見積書と B2B の請求書を作る画面のプルダウンで選ぶ形~~ → 取引先の既定の請求先の国で自動で決める形に改めた（2026-11-06 PO「顧客情報の住所で自動的にシステムが判断する仕組みに出来る？請求先が日本なら国内向け、海外なら海外向け」）。対象は請求書だけ（2026-11-07 PO「見積もりは今回はパス、請求書だけで考える」）。
- ~~国内向けか海外向けかを決められない取引先の扱い~~ → 請求書を作らせず、請求先の国を入れる案内を出す（2026-11-07 PO「請求書は顧客情報が登録されていないと作れない仕組みにしたいので1」）。
- ~~見積書の PDF に載せる自社の会社情報~~ → 海外用の行を載せる（2026-11-07 PO「1,見積もりは顧客名は必須にしない、成約前の顧客にも使用するため顧客情報がない場合があるので」）。
- ~~B2B の請求書の PDF にインボイスの登録番号の行を足すか~~ → 登録有のときだけ足す（2026-11-07 PO「1」。1 は「登録があるときだけ、番号を請求書に印刷する」）。設計審査（2026-11-07）で §2 と A29 の食い違いとして見つかった。
- ~~見積書を取引先なしで作れるようにするか~~ → 別の設計で後から進める（2026-11-07 PO「1」）。今は登録済みの取引先と担当者が必須で、PO の言葉「顧客名は必須にしない」と違う。tasks/todo.md に積んだ。
- ~~会社名・メール・サイトとインボイス登録を会社に1つ~~ → 国内用と海外用で1つずつ持つ形に改めた（2026-11-06 PO「国内と海外で登録できるようにする」「これも国内と海外で2つ、分社している場合に備えて」）。
- 発注書と FedEx の申請書は切り替えない（PO 2026-11-06「発注書は使わないので破棄、使うのは見積もりと請求書のみ」。2026-11-06 回答）。
- ~~FedEx の申請書も消すか~~ → 消す（PO 2026-11-10「1」。選択肢の「1. FedEx も消す」）。発注書と同じく別の設計で、件数を数えてから消す（§3-4 の「古い6列を消すまでの計画」）。

### 7-2. 承認のときに一緒に確かめること

- ~~前に作った請求書（国内向けか海外向けかの値が空）を、海外向けとして読む扱い。~~ → 確かめる対象が無くなった。本番の請求書は試しの1枚だけで、PO の指示で消した（PO 2026-11-09「アプリで作った請求書はテストデータだけだから消して良い」。同日 16:19 に消し、読み取り専用の鍵で0件を確かめた。記録 docs/handoff/viewer-contract-stage/delete-test-invoice/）。
- ~~成功条件の11番の見出し~~ → 「請求書に載せる自社情報と振込先を、国内用と海外用で分けて持てる」に変える（PO 2026-11-09「2」）。
- ~~状態の表示名「契約手続き中」。~~ → このまま（PO 2026-11-09「1」）。
- ~~手続き中の人にも手作業の「延長」を出す。~~ → 出す（PO 2026-11-11「1」。ideal-state 49）。
- ~~税率の画面と「商材とプラン」の画面を、閲覧者の一覧の見出しのボタンから開く（AI の案）。~~ → 左メニュー「全体設定」の中に置く（PO 2026-11-11 のメニューの組み替え。ideal-state 50。§3-4d）。
- ~~最初の商材・プラン・機能は、便2b の「商材とプラン」の画面で PO が入れる（前の版は「1回だけのデータの変更」で AI が入れる案。§4 の（２））。~~ → PO が画面で入れる（PO 2026-11-11「1」。ideal-state 51。他の案は「AI が最初の1件だけ直接入れる」「画面ができてから考える」）。
- ~~三点ボタンの金型を新設する。~~ → 共通の型として新設する（PO 2026-11-12「1」。ideal-state 52。他の案は「行の中に直す・消すのボタンを並べる」「作る直前に決める」）。
- ~~商材とプランの登録画面は今回作らない。~~ → 今回作る（PO 2026-11-09「2」）。中身は §2（PO 2026-11-09「1」）。
- ~~税の端数は切り捨て。値引きは金額のみ。~~ → このまま（PO 2026-11-12「1」。ideal-state 53。他の案は「端数は四捨五入」「値引きを割合でも入れられるようにする」）。
- ~~3年保持を始める前に、専門家に確かめるか。~~ → 確かめずに進める（PO 2026-11-07「2」）。新しいポリシーを公開し、14日以上たってから新旧の決まりで結果に差が出るようにする（消す処理の変更自体はマージの時点で本番に入る。§3-9）。
- ~~閲覧者に改訂をメールで知らせるか（審査 2026-11-07 の指摘(2)）。~~ → メールは送らず、サイトに載せるだけにする（PO 2026-11-07「2」。他の案は「24人全員にメール」「契約中の4人だけにメール」）。
- ~~振込先の銀行口座に海外送金の欄（SWIFT コード・銀行の住所）を入れる。~~ → 入れる。どちらも任意（空で保存できる）（PO 2026-11-09「1」）。
- ~~Wise と PayPal の入力項目（§3-4）。~~ → Wise は名義・通貨・メールが必須、IBAN・SWIFT/BIC・銀行名・銀行の住所・メモが任意。支払いリンクは持たない。PayPal は振込先に入れない（PO 2026-11-09 の言葉と提案。ideal-state 31〜33）。表は一覧と種類ごとの詳細の2段（PO 2026-11-10「１」）。
- ~~書類に載せる会社情報と振込先を直せる人を tenant.profile.edit を持つ人のままにするか、オーナーだけにするか。~~ → いまのまま tenant.profile.edit を持つ人（PO 2026-11-10「1」。ideal-state 41）。
- ~~都道府県の一覧を新しい表にする（§3-4 の案A）。~~ → 案A のとおり public.prefectures の1か所に置く（PO 2026-11-10「1」。ideal-state 42）。
- ~~管理センターのメニューとページの名前を「発行者情報」から「会社情報」に変える。~~ → 変える（PO 2026-11-10「1」。ideal-state 43）。§3-4 の画面の段落。
- ~~古い住所と電話を消すのは、全社が入れ直したのを数えた後の別の便にする。~~ → 古い6列は消す方向で、統合の計画を立てる（PO 2026-11-10「古い店は長期的に見て消したほうが良いよね？消す方向で統合計画を」。ideal-state 44）。計画は §3-4 の「古い6列を消すまでの計画」。発注書に加えて FedEx の申請書も消す（PO 2026-11-10「1」。ideal-state 45）。
- ~~海外の住所の電話は国番号つきの数字だけで保存し、見せるときに「+」を付ける。~~ → アプリ共通の決まり（ADR-126）に揃え、「+」付きで保存する（PO 2026-11-10「1」。ideal-state 46）。§3-4 の住所と電話の決まり・A28。
- ~~画面の欄の名前「インボイス登録」。~~ → 「インボイス登録番号」（PO 2026-11-10〜11「1」。ideal-state 47）。
- ~~Mac の AI の道（ai_ro）からは振込先の口座番号が全桁見えることを受け入れるか。~~ → 口座番号だけ隠す（PO 2026-11-11「2」。ideal-state 48）。§3-4 の隠す設定・A46。

## 8. 受入条件

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | お試しの行に「契約に進む」が出て「本契約にする」が出ない。押すと手続き中になる | Evaluator（Playwright）＋ frontend テスト |
| A2 | 手続き中・未送信で「請求書を作成」「入金確認」が出ない | frontend テスト＋ Evaluator |
| A3 | 送信済みで「請求書を作成」と三点、発行後に「入金確認」と三点 | frontend テスト＋ Evaluator |
| A4 | フォーム送信で期限が3日後になり、残りが長い人は短くならない | backend pytest |
| A5 | 発行で期限が支払期限の 23:59:59（日本時間）になる | backend pytest |
| A6 | 期限切れの手続き中はログインが 403 viewer_contract_expired。行は残る | backend pytest（viewer_api） |
| A7 | 200,000円→220,000円。値引き 20,000円→198,000円。端数は切り捨て: 33,333円→税 3,333円（3,333.3 の 0.3 を捨てる）・合計 36,666円。小計超えの値引きは 422 | backend pytest |
| A8 | メールに PDF が1つ添付され、本文にリンクが無い | backend pytest＋本番でテスト用の閲覧者に送る |
| A9 | 保存が成功すると drive_file_id が入り、国内用フォルダにある | 本番で PO がドライブを目視 |
| A10 | 保存の失敗で発行は成立し、「未保存」と「もう一度保存」が出る。再保存で1件だけになる | backend pytest＋ Evaluator |
| A11 | 再発行で前が voided、新しい番号。有効な請求書は1件 | backend pytest |
| A12 | 入金確認で本契約になり、期限切れの日時でも見られる | backend pytest＋本番確認 |
| A13 | 期限切れ 3年以内の行は残り、3年を過ぎた行は消える。本契約は消えない | backend pytest（掃除の処理） |
| A14 | 名簿を消しても請求書の行が残り、viewer_account_id が NULL になる | backend pytest（実 PostgreSQL・salesanchor_app・運営の印なし。FORCE の RLS の下で SET NULL が効くことを確かめる） |
| A15 | 税率の行を足すと、適用日以降の請求書だけ変わる。発行済みは変わらない。表が空でないとき、今日以前の日付と最新行以前の日付は 422。今日以前の適用日の行の削除は 409 | backend pytest＋ Evaluator |
| A39 | 発行と再発行の前の確かめで、足りない項目ごとに 409 とキーの配列（§3-4b の5つ）が返る。画面は t() で文にして出し、detail に日本語の文が無い | backend pytest＋ frontend テスト＋ Evaluator |
| A16 | チェックして発行すると次回の既定が変わり、チェックなしは変わらない。発行済みの期限は変わらない | backend pytest＋ Evaluator |
| A17 | プランと機能の行を足すと、作成画面の選択肢に出る | backend pytest＋ Evaluator |
| A18 | 新しい個人情報の列と会社ごとの新しい4表の値が、相談係の道（ai_reader_cloud）で伏せて見える（masked）。Mac の道（ai_ro）では bank_account_number と iban の2列だけが列ごと出ない（PO 2026-11-11「2」）。他の列は今と同じ | backend pytest（実 PostgreSQL で ai_cloud の見せ方を通して読み、隠す列が masked。ai_ro の見せ方にこの2列が無く、同じ表の他の列はある）＋本番で ai_reader_cloud の道から1件読み、ai_ro の道で2列が無いことを列の一覧で確かめる（値は読まない）。CI に専用の手順名は無い（.github/workflows の grep 2026-11-06） |
| A19 | 画面の文字はすべて t()。生の部品なし | CI（i18n・UI のガバナンス） |
| A20 | 会社名・メール・サイト・住所・電話・インボイス登録を国内用と海外用に別々に保存でき、片方を直してももう片方は変わらない。閲覧者の請求書は国内用の行を載せる。発行の後に会社情報を直しても発行済みは変わらない。書ける場所がそれぞれ1つだけ（tenant_issuer_profiles の外に会社名・メール・サイト・住所・電話・登録を書く道が0件。tenant_profile の古い6列は読むだけで、更新の口へ送っても値が変わらない。古い6列は移行の間だけ残すもので、この判定から除く） | backend pytest（information_schema で列名を確かめる。会社情報の更新の口へ古い6項目を送り、値が変わらないことを確かめる。region ごとに別の値で保存し、片方の更新で他方が変わらない）＋ Evaluator |
| A21 | 別の会社の文脈では住所・登録・振込先の行が読めない | backend pytest（RLS の点検） |
| A22 | 新しく作った会社と既存の会社で、会社ごとの新しい4表（会社情報・振込先の一覧・銀行・Wise）の列・制約・RLS・ポリシーの差が0 | backend pytest（実 PostgreSQL。新しい会社を作る処理で1社作り、既存の1社と4表ぶん比べ、差の行数が0。比べるのは information_schema.columns の column_name・data_type・is_nullable・character_maximum_length、pg_constraint の種類と定義、pg_class.relrowsecurity・relforcerowsecurity（どちらも ENABLE あり・FORCE なし）、pg_policies の名前と条件。列の既定値（会社の番号が入りうる。tenant.py:486）と、定義の中のスキーマ名は比べない） |
| A23 | 最高管理者の画面から発行しても、発行元の会社の会社情報（get_issuer）・振込先と Google の接続を読め、public の表へ書ける。commit の後の裏の書き込み（mail_*・drive_*）も入る | backend pytest（実 PostgreSQL で salesanchor_app の権限。§3-4 の（１）〜（５）の順。順を逆にすると書けないことも確かめる）＋ Evaluator |
| A24 | 登録が無のとき番号の欄が入力できず、値を送っても保存されない。有のとき T＋13桁以外は保存できない。PDF の番号の行は有のときだけ出る | backend pytest＋ frontend テスト＋ Evaluator |
| A25 | 振込先を種類ごとに複数登録でき、種類を変えると入力欄が変わる。種類ごとの必須が無いと保存できない（DB の NOT NULL と CHECK でも止まる）。銀行の SWIFT と銀行の住所、Wise の IBAN・SWIFT/BIC・銀行名・銀行の住所・メモは空で保存できる。method_type に bank と wise 以外は入らない | backend pytest＋ frontend テスト＋ Evaluator |
| A26 | 作成画面で選んだ振込先だけが PDF に載る。発行後に振込先を直しても消しても、発行済みの内容は変わらない。振込先が0件なら発行できない。作成画面に JPY 以外の Wise は出ない | backend pytest＋ Evaluator |
| A27 | 住所の国が日本のとき、郵便番号7桁以外・都道府県なし・電話にハイフンや空白・10〜11桁以外は保存できない（画面と DB の CHECK の両方） | backend pytest＋ frontend テスト＋ Evaluator |
| A28 | 住所の国が日本以外のとき、郵便番号なし・州の自由記入で保存でき、電話は「+」と数字6〜15桁だけ通る（「+」なし・ハイフン・空白は画面と DB の CHECK の両方で止まる）。保存した値と PDF の電話の文字が同じ | backend pytest＋ frontend テスト |
| A29 | インボイス登録の有無と番号を国内用と海外用で別々に持てる。有の行は番号が無いと保存できず、無の行は番号が NULL になる。国内用の請求書の issuer_snapshot に国内用の行の番号が写る。B2B の請求書の PDF は、その region の行が有のときだけ番号を載せる | backend pytest（CHECK で止まる・国内用だけ有の会社で、国内向けの PDF に番号があり海外向けの PDF に無い・発行の写しに番号がある）＋ frontend テスト（無のとき番号の欄が disabled）＋ Evaluator |
| A30 | 都道府県の選択肢が DB の47行から出て、画面のコードに都道府県名が無い | backend pytest（試験の seed で47行・API が47行を返す・frontend/src を読んで「北海道」が0件）。CI に専用の手順名は作らず、backend の試験の中で確かめる |
| A31 | DB の動き: 運営の印なしで新しい public の9表へ書くと、INSERT は RLS の誤りで止まり、UPDATE と DELETE は0行になる。運営の印ありなら書ける。処理の動き: 行を直す処理（契約・請求書・税率の削除・採番）は、変えた行数が1でないと誤りで止まる | backend pytest（実 PostgreSQL・salesanchor_app。DB の動きは9表それぞれ。処理の動きは UPDATE・DELETE を持つ処理ごと。都道府県・明細・機能の表には UPDATE の処理が無いので処理の動きの対象外） |
| A32 | 住所・登録・振込先を足す・直す・消すと audit_logs に1行ずつ残り、口座番号と IBAN は下4桁だけ | backend pytest |
| A44 | 振込先の1対1: bank の一覧の行に Wise の詳細を付けると DB の誤りで止まる。1つの一覧の行に詳細を2行付けられない。一覧の種類を直すと誤りで止まる（API は 422 payment_method.type_immutable）。詳細の method_type か tenant_id を NULL にすると NOT NULL で止まる。詳細の tenant_id が一覧と違うと外部キーで止まる。一覧を消すと詳細も消える（ADR-1079 で「一覧も詳細も DB が消すことを断る」に改める。invoice-create-portfolio/design.md K25）。詳細の書き込みが失敗すると一覧の行も残らない。詳細の無い一覧の行は選択肢に出ず、発行は 409 payment_method で止まる | backend pytest（実 PostgreSQL・salesanchor_app） |
| A33 | 番号の採番を同時に2つ走らせても番号が重ならない | backend pytest（実 PostgreSQL・2接続） |
| A34 | 閲覧者に結び付いた配信先（viewer_account_id あり）で、契約手続き中（contracting）の閲覧者には配信されず、理由が not_contracted になる。入金確認で active になると配信される。配信の処理（tcg_distribution_svc.py:737 の `va.status <> 'active'`）は変えない | backend pytest（contracting の人の配信先の行の reason） |
| A35 | 日本語のフォントが登録できないとき、発行が止まり請求書の行が作られない | backend pytest（フォントの読み込みを失敗させる） |
| A36 | メールの送信に失敗したとき（SMTP 未設定を含む）、発行は成立し、行に「送信失敗」と「もう一度送る」が出る。再送の成功で mail_sent_at が入る | backend pytest＋ Evaluator |
| A37 | 公開ポリシーの閲覧者の保存期間が3年、請求書の記録が7年、Google の用途にドライブ、利用目的に再登録の防止が載り、改訂日が入る | 本番の LP を PO が目視＋ lp のビルド |
| A38 | 週1回の接続の見守りが動き、トークンの更新に失敗すると Discord の運用通知に1件出る | backend pytest（更新を失敗させる）＋本番の実行記録 |
| A40 | 差出人を読む処理が get_issuer の1つだけになる（対象外の発注書と FedEx の申請書を除く）。get_issuer は backend/app/services/issuer.py に置く。backend/app で tenant_profile を読む SQL は、このファイルと例外の4つ（会社情報の口 backend/app/routers/tenant_profile.py、会社を作る処理 backend/app/services/tenant.py の表の作成と既定の行の INSERT、対象外の backend/app/services/po_renderer.py と backend/app/services/label_validation.py）の外に0件 | backend pytest（backend/app の .py を読んで「tenant_profile」を含む行を数え、上の5ファイル以外で0件なら合格。ソースを読む試験の先例 backend/tests/test_tenant_loop_migration_guard.py） |
| A41 | B2B の請求書は、その請求書の region（値が空の前の請求書は overseas）の行の会社名・メール・サイト・住所・電話を載せる。その region の行が無い会社では、切り替え前と同じ古い値が載る（会社名は company_name、空なら company_name_en）。見積書の PDF は海外用の行（無ければ古い値）を載せる。発注書・FedEx の申請書と申請メールは切り替えず、切り替え前と同じ文字が載る | backend pytest（行あり・行なしの2通りで PDF の文字を pdfminer.six で読む。先例 backend/tests/test_po_renderer.py:81〜:89。発注書と FedEx は切り替え前の試験がそのまま通る） |
| A42 | 国内用の行が無いと、閲覧者の請求書は 409 issuer_profile で止まり、古い値では発行されない。国内用と海外用のタブのそれぞれで、その行が無く古い値があるとき、古い値（読むだけ）と入れ直しの案内が出る | backend pytest＋ frontend テスト＋ Evaluator |
| A43 | 請求書を作ると、取引先の既定の請求先の国が JP（小文字も含む）なら domestic、JP 以外なら overseas が請求書に入る。見積書から作った請求書も、作るときの取引先の国で決まる。作った後に取引先の国を直しても請求書の値は変わらない。作る画面に国内向けか海外向けかの選択は無い。既定の請求先が無いか国が空の取引先では、請求書の行が増えずに 422 bill_to_country で止まり、画面に請求先の国を入れる案内と取引先の画面への道が出る。見積書の表と作る口は変わらない | backend pytest（JP・jp・US・既定の請求先なし・国が空の5通りを、見積書から作る口と直接作る口の両方で。止まったときに請求書の件数が増えない。取引先の国を直した後に請求書の値が同じ）＋ frontend テスト（選択が無い・案内と道が出る・詳しい画面に値が出る）＋ Evaluator |
| A45 | 商材とプランの画面（§3-4d）: 最高管理者だけが開け、他の人には「権限がありません」が出て API は 403。商材とプランを足せる。名前・金額・支払日数・含む機能・使う/使わないを直せる。コード・発行元・請求の種類と間隔は直せず API は 422 *.immutable。コードの重なりは 409。消すボタンと DELETE の道が無い。使わないにした商材とプランは請求書の作成画面の選択肢に出ない。プランの金額を直しても発行済みの請求書の金額は変わらない。API の feature_keys の Literal の並びと sa_plan_features の CHECK の並びが同じ。部品は金型だけ・文字は t() | backend pytest（実 PostgreSQL。最高管理者と他の人の2通り・immutable・409・使わないの行が invoice-draft に出ない・発行後にプランの金額を直して請求書の金額が同じ・Literal と CHECK の比較）＋ frontend テスト＋ Evaluator |
| A46 | 列名の拒否の一覧が1つにそろう: migrations/20261017_130100_create_ai_ro_views.sql と migrations/20261024_100000_create_ai_cloud_meta.sql の `deny constant text := '…'` の文字が、backend/app/ops/readonly_query.py の DENY_COLUMN_RE.pattern と同じ。試験の2ファイル（test_ai_cloud_views.py・test_ai_ro_views.py）は拒否の一覧の文字を自分で持たず DENY_COLUMN_RE を import する。新しい一覧は account_number と ^iban$ を含む | backend pytest（新しい backend/tests/ops/test_deny_column_regex_sync.py。2つの SQL ファイルを読み、文字の一致を確かめる。試験の2ファイルに正規表現の文字が無いことも数える） |
## 9. 実装カードへ送ること

- 状態を読む場所の全件 grep（`'trial'`・`"trial"`・`'active'`・`"active"`）を最初に行い、結果をカードの表と照合する。表に無い場所が出たら止まる。
- 会社情報（get_issuer）・振込先と Google の接続を最高管理者の画面から読むときは §3-4 の形にする。SQLite の試験では文脈の設定が何もしないので、A21・A23 は実 PostgreSQL で確かめる（dependencies.py の set_tenant_context の説明）。
- 実在のお客さんには送らない。確認は PO のテスト用の閲覧者で行う。
- カードには、直すファイルごとに file:line・変更前と変更後のコード・触らない範囲を必ず書く（docs/STANDARD-WORKFLOW.md の設計の粒度）。KPI への分け方もカードで書く。

## 10. 外部・過去事例の参照と我々への応用

- 社内事例: B2B 請求書の発行時点の写し（migrations/20260604_160000_add_invoice_snapshot_columns.sql:31・:46）と2表の形（ADR-101）。同じ考え方を使う。
- 社内事例: 送り状のドライブ保存は失敗をログだけで流す（backend/app/routers/shipping.py:511）。今回は記録として必須なので、失敗を画面に出す形に変える。
- 外部の決まり: 国税庁 6303・インボイス Q&A 問78・問79、個人情報保護委員会 通則編、Google の公式説明（recon §8・§10）。
- 他社の導入事例（振込先の表の形と守り）: evidence-payment-methods.md に 5W2H と数値で残した（2026-11-10 調べ）。要点: Stripe は「種類の値＋種類と同じ名前の詳細」の形（F2）、GitLab は1表に種類の列を並べる形を新しい表で禁止（F1）、振込先の差し替え詐欺の被害額（F3・F4）、RLS の付け忘れの漏れ（F6）。表の形そのものの速さや失敗率を数で比べた公開の調べは見つからなかった（同ファイルの「見つからなかったもの」）。
- それ以外の他社の導入事例: 該当なし。理由: 手続きと帳票の決まりで、法令と公式の説明と社内の既存の形で根拠が足りるため。

## 11. 接触面分析（逆参照の grep 2026-11-06。生出力 /tmp/CC報告ファイル/contract-status/contact-surface-1106.txt）

| 面 | 触れるもの | 対処 |
|---|---|---|
| ①人 | PO（国内用と海外用の会社情報の入れ直し・登録・振込先・文面・保存先の入力、テストの支払い）、会社情報を直す各社の人 | 便2 の後と便4 の前に PO が行うこと（§4）。入れ直すまで画面に案内を出す（§3-4） |
| ②エージェント | 実装役は design.md・カードを読む。.claude/agents・docs/ai-agents・AGENTS.md に viewer_accounts の語は0件 | 実装カードに §9 の全件 grep と止まる条件を書く。周知の追加は不要 |
| ③機械 | 名簿の掃除 purge_viewer_accounts（backend/app/celery_app.py の定時登録、backend/tests/test_viewer_purge.py）。会社の表の作成 _TENANT_TABLES_SQL（backend/tests/test_rls_tenant_meta_config.py・test_roles_system_key_ddl.py）。移行の点検（.github/workflows/migration-guard.yml・migration-test.yml・schema-check.yml） | 掃除の試験を3年の条件に直す（A13）。会社の表の差の試験を足す（A22）。移行は migration-test で全会社へ流す |
| ④データ | public に新しい9表。全会社のスキーマに4表と、invoices に issuer_region の1列（quotes には足さない）。tenant_profile の company_name・company_name_en・email・website・address・phone は書けなくなり読むだけ（差出人の読み出しのうち切り替えるのは invoices.py だけ。po_renderer.py・label_validation.py は今のまま古い列を読む。試験 backend/tests の7ファイル・51か所 grep 2026-11-06）。tenant_google_drive_config に1列（読む処理: integrations.py・google_drive_oauth.py・carrier_credentials.py。試験 test_google_config_rls.py） | 既存の列は変えない。invoices.issuer_region は NULL 可で、作り済みの請求書は空のまま（PDF では overseas として読む）。新しく作る請求書から値が入る。tenant_004 本番の行は増えるだけ |
| ⑤本番 | 便1（掃除の条件）と便2（移行）は本番の DB を変える | 便1 は済み（PR #5250、2026-11-07T16:13:29Z マージ）。便2 は ADR-136 の GO。直前のバックアップを確かめる |
| ⑥外部 | 閲覧者（メール・ログインの期限）、Google ドライブ、Wise、公開ポリシー（lp/src/pages/privacy.astro） | 実在のお客さんには送らない（§9）。ドライブは今あるフォルダへ保存する形に決まった（2026-11-06 PO のテスト保存。§3-8）。Wise は円の入金をテストの支払いで確かめる |

## 維持の仕組み

- 守り手: .github/workflows/process-artifacts-gate.yml
- 対象: 1つの情報を1か所に置く決めごと（§3-1・§3-4。差出人は get_issuer の1つの道だけで読む。A40 の grep の試験で守る）と、請求書を名簿の削除から切り離す決めごと（§3-9）。
- 振込先の守り（2026-11-10 origin/main で確かめた既存の見張り）: 全会社のスキーマの表・列・列の型の差を止める .github/workflows/schema-check.yml（scripts/db/sync_tenant_schema.py:162〜:184 が比べるのは表・列・型だけ。外部キー・CHECK・RLS の差は止めない。RLS などの数は記録に出すだけ :467〜:481）、会社の表の読み書きの決まりを止める .github/workflows/lint-tenant-schema.yml（ADR-072 の strict）、移行の参照の登録を止める migration-guard。種類の食い違いと必須は DB の外部キーと CHECK が毎回の書き込みで止める。会社ごとの表の RLS の有無を数える専用の点検は無い（scripts/check_public_tenant_rls.py は public の表だけを見る）。このため外部キー・CHECK・RLS の差は A22 と A44 の試験だけで止める。
- 列名の拒否の一覧（ai_ro・ai_cloud・Mac の読み取りの道）は、Python の DENY_COLUMN_RE を正本にし、SQL の2か所が同じ文字であることを A46 の試験が CI で毎回確かめる。片方だけ直すと試験が赤になる。
- 含む機能の一覧は sa_plan_features の CHECK を正本にし、API の Literal との一致を A45 の試験が確かめる。
- 補足: 状態の漏れは受入条件のテスト、列の隠し忘れは相談係の道の分類表（migrations/20261024_100300_create_ai_cloud_views.sql）と A18 の試験で止める。金額と期限の決まりは backend のテストで守る。
