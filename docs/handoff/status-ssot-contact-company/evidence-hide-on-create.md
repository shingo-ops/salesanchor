# 「重複確認待ち」を作る画面で出さない案の根拠（origin/main 2026-11-11 取得）
生: pdr_all.txt（221行・全出現）/ create_paths.txt / inserts.txt / insert_detail.txt

## 1 自動で付ける道は今の本番コードに無い
- 新規作成の道は5本。どれも自動では付けない:
  - backend/app/routers/companies.py:404 画面の選択値（無指定なら active: backend/app/schemas/company.py:134）
  - backend/app/routers/contacts.py:439 同上（backend/app/schemas/contact.py:109）
  - backend/app/routers/registration_tokens.py:322 'active' 固定
  - backend/app/routers/integrations.py:653,671 状態を書かない→DB既定 'active'（migrations/028_create_companies.sql:78, backend/app/services/tenant.py:223）
- 自動で付けたのは移行用の使い捨てスクリプトだけ（scripts/_archive/data_migration/migrate_customers_from_sheet.py:72,198 2026-04-23 CT-00030/00032 の2件）
- 試験用の種データ scripts/qa/seed-tenant.sql に 0件
## 2 外す動きは「まとめる」操作だけ
- backend/app/routers/companies.py:978-980 まとめ先が重複確認待ちなら有効に上げる
## 3 画面の出方
- 作る: CompaniesPage.tsx:514 出す / ContactsPage.tsx:337-341 出さない / CompanyContactsTab.tsx:198-204 出さない
- 直す: CompanyFormFields.tsx:32（CompaniesPage.tsx:573 編集の引き出し）/ CompanyBasicTab.tsx:92 / ContactEditPage.tsx:189 / ContactFormFields.tsx:43（ContactsPage 編集の引き出し）
- 解消の欄は直す画面だけ: CompanyBasicTab.tsx:124-125 / ContactEditPage.tsx:196 / 一覧の操作 ContactsPage.tsx:395
## 未確認
- 本番で今この状態の会社・連絡先が何件あるか（読み取り鍵は会社・連絡先の表を読めない: 42501）。作る画面から外しても既存の記録は変わらないため、判断には影響しない。

## 訂正（2026-11-12）
- CompanyContactsTab.tsx:151-154 の小窓は新規と編集の共用（title = contactForm.id === null ? newContact : editContact）。
  → 「作る3・直す4」は誤り。正しくは 作るだけ2（CompaniesPage.tsx:436-439 / ContactsPage.tsx:289-292）・直すだけ4・共用1。
- 共用の小窓は直すときも「重複確認待ち」を出さない（CompanyContactsTab.tsx:198-204 の選択肢は3つ）。
- 画面名（ja.json）: 顧客情報=会社 / 担当者=連絡先 / 新規登録 / 顧客情報編集 / 担当者編集 / 基本情報タブ / 担当者管理タブ

## 作る画面の ID 系の項目（2026-11-12 origin/main）
- 会社の新規登録の小窓: company_code・fedex_account・website ほか（create_inputs.txt）
- 担当者の新規登録（2か所）: contact_code（担当者一覧のみ）・primary_email・primary_phone ほか。連絡手段ID・Discord ID は作る小窓に無い
- 連絡手段ID: 登録後に ContactChannelForm（CompanyContactsTab.tsx:226-230 contactId 必須）で入れる。重複確認は既存 contacts.py:346-382 / ja contactChannel.duplicateWarning
- 会社コード・担当者コードは DB で一意（migrations/028_create_companies.sql:84, 029_create_contacts.sql:46）。重なると 409 conflict_constraint（companies.py:501-507, contacts.py:507-513）→ 画面は「同じものがすでに登録されているか、関係するデータと合わないため…」で、どの項目か示さない
- 赤枠の部品: TextField.tsx:14,49 invalid / :26,77,96-101 error（role=alert）

## 2026-11-12 重複の警告 recon（origin/main cee9633b9 時点）
- 会社のメール・電話は会社の表に無く、住所の表 company_addresses の email・telephone（請求先 billing・届け先 delivery）にある（backend/app/services/tenant.py の companies 定義・company_addresses 定義。作る画面は CompaniesPage.tsx:227-264 で billing と delivery の両方を送る）。
- メールは保存時に小文字にそろえる（backend/app/schemas/base.py:32-38 validate_email_loose は value.lower()）。
- 電話は保存時に空白・ハイフン・かっこを取る（base.py:16-29 validate_phone は re.sub(r"[\s\-\(\)]","",...)）。+81 と 0 始まりは別の文字のまま。
- 会社名・担当者名・ウェブサイト・FedEx口座はそろえずにそのまま保存（companies.py:406-432・contacts の INSERT）。normalized_name は画面から送られた値だけで、作る画面は送っていない（CompaniesPage.tsx の payload に無い）。
- 保存前の重複確認の前例は1つ: GET /contacts/channel-duplicate（contacts.py:346-382）。同じ会社内でなく領域全体を完全一致で見て、1件だけ返す。
- 会社コード・担当者コードは領域内で重ならない決まりが DB にある（tenant.py の UNIQUE (tenant_id, company_code)・UNIQUE (tenant_id, contact_code)）。
