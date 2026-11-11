# 会社と連絡先の「状態」を1か所へ — 現在地の記録（recon）

> この文書は何か（専門用語なしの1行）:
> 会社と連絡先の「有効・無効・アーカイブ・重複確認待ち」が、今どこに何か所書かれていて、本番に何件あるかを、ファイルの行番号と本番の件数で記録したもの。

- 基準: origin/main a88194893（2026-11-11 取得・作業場所 release/status-ssot-contact-company）。本番は読み取り専用の鍵（ai_ro）で件数と制約だけ取得（2026-11-11 13:51 JST）。
- 生出力: /tmp/CC報告ファイル/english-literal-i18n/merge-desc/ssot/ と /tmp/CC報告ファイル/english-literal-i18n/merge-desc/ の各 txt（recon1〜6・ssot*・prod-*）

## 0. 既存ADR・仕様書の検索結果

- 【事実】ADR-120（`docs/adr/ADR-120-status-presentation-ssot.md`）: 状態 → 見た目の決め方は `frontend/src/utils/statusPresentation.ts` 1か所。ページが自前で色・名前を決めることを禁じる。
- 【事実】ADR-109（`docs/adr/ADR-109-leads-status-ssot-immutable-codes.md`）: 見込み客の状態は「DBには変わらない記号・名前は辞書（i18n）」。今回のPO方針「値はDBに1か所」と向きが違う（§5）。
- 【事実】ADR-027（`docs/adr/ADR-027-ui-internationalization.md`）: 画面の文字は t() を通す。
- 【事実】ADR-1007（`docs/adr/ADR-1007-migration-structure-only-run-once.md`）決定1: migration は構造だけ。行の値は1回だけのデータ変更（PO合意・DRY-RUN→COMMIT）で入れる。
- 【事実】ADR-1008（`docs/adr/ADR-1008-person-ssot-users-id.md`）: 会社ごとの表から public の表へ外部キーを張る前例。`migrations/075_create_goals.sql:55`（`REFERENCES public.users(id)`）。
- 【事実】前例の設計: `docs/handoff/channel-master-shared/design.md`（全社1つの名簿 public.channel_masters・作る便→行を入れる→付け替えの3段）。表の作り `migrations/20261106_190000_create_public_channel_masters.sql:13-60`（RLS は ADR-145 の写し）。読み口1か所 `backend/app/services/channel_masters.py:1-13`。
- 【事実】会社と連絡先の状態に触れるADRは0件（`git grep -l -i -E "company.?status|contact.?status" -- docs/adr` の出力なし・recon7.txt）。ADR-120 は statusPresentation.ts の中で contact/company を扱う。

## 1. DB（本番の今）

- 【事実】状態は各行の1列。会社 `companies.status`・連絡先 `contacts.status`、VARCHAR(20) DEFAULT 'active'、CHECK で4つの値だけ許す。
  - 会社を作るときの定義: `backend/app/services/tenant.py:224`、連絡先: `backend/app/services/tenant.py:255`（どちらも `CHECK (status IN ('active','inactive','archived','pending_dedup_review'))`）
  - 経緯の migration: 015・028・037（037 で連絡先にも pending_dedup_review を足した。`backend/app/schemas/contact.py:31-33` の注記）
- 【事実】本番の制約（ai_ro・prod-constraints.txt）: tenant_001/003/004/005/006 の companies・contacts 計10表すべてに companies_status_check / contacts_status_check（上と同じ4値）。
- 【事実】本番の件数（prod-status-counts.txt）:

| 会社の領域 | 会社 | 連絡先 |
|---|---|---|
| tenant_001 | active 1 | active 1 |
| tenant_004 | active 51 | active 52 |
| tenant_003・005・006 | 0行 | 0行 |

- 【事実】状態の名前（有効など）は DB のどこにも無い。名前は画面の辞書だけにある（§3）。

## 2. サーバー（backend）

- 【事実】4つの値は Python の列挙にもう1回書かれている: `backend/app/schemas/company.py:33-37`（CompanyStatus）、`backend/app/schemas/contact.py:26-36`（ContactStatus）。受け取り時の検査に使う（`backend/app/schemas/company.py:134`・`:159`、`backend/app/schemas/contact.py:109`・`:138`）。
- 【事実】値で動きが変わる所（仕組みが記号に頼る所）:
  - `backend/app/routers/companies.py:765` まとめる先が archived なら 409（受け付けない）
  - `backend/app/routers/companies.py:978-985` まとめる先が pending_dedup_review なら active に上げる
  - `backend/app/routers/companies.py:1015-1019` 上げたことを記録に残す
- 【事実】連絡先をまとめると記録に残す: `backend/app/routers/contacts.py:869`・`:875`（record_audit_log）。
- 【事実】状態の一覧を画面に渡す API は無い（画面は値を自前で持つ・§3）。
- 【事実】分析（analytics）の中で会社・連絡先の状態を読む所は0件（recon4.txt の検索結果なし）。

## 3. 画面（frontend）

- 【事実】見た目の決め方1か所（ADR-120）: `frontend/src/utils/statusPresentation.ts:164-176`。連絡先と会社で別の辞書キーを指す（連絡先 `contacts.statusCode.*`、会社 `customers.status_*`）。
- 【事実】ADR-120 を通らずに選択肢を自前で並べる所（8か所）:
  - `frontend/src/pages/contacts/ContactFormFields.tsx:39-44`
  - `frontend/src/pages/contacts/ContactEditPage.tsx:185-190`
  - `frontend/src/pages/contacts/ContactsPage.tsx:338-340`（3つだけ・重複確認待ちが無い）
  - `frontend/src/pages/company-detail/CompanyContactsTab.tsx:200-202`（3つだけ）
  - `frontend/src/pages/companies/CompanyFormFields.tsx:28-33`
  - `frontend/src/pages/company-detail/CompanyBasicTab.tsx:89-92`
  - `frontend/src/pages/companies/CompaniesPage.tsx:511-514`
  - `frontend/src/components/MergeContactModal.tsx:233`（辞書キーを値から直接組み立てる）
- 【事実】値を直接書いた比較・初期値: `frontend/src/pages/companies/CompaniesPage.tsx:352`・`:428`、`frontend/src/pages/contacts/ContactsPage.tsx:236`・`:395`・`:411`、`frontend/src/pages/contacts/ContactEditPage.tsx:196`、`frontend/src/pages/company-detail/CompanyBasicTab.tsx:125`、`frontend/src/pages/design-system/DesignSystemPage.tsx:191`、`frontend/src/components.css:271`（`.status-badge.status-pending_dedup_review`）。
- 【事実】同じ名前の辞書キーが重なっている（ja.json）:
  - 「重複確認待ち」: `frontend/src/locales/ja.json:1161`（customers.status_pending_dedup）・`:1278`（contacts.statusPendingDedupOption）・`:1299`（contacts.statusCode.pending_dedup_review）
  - 「有効・無効・アーカイブ」: `frontend/src/locales/ja.json:1133-1135`（customers.status_*）と `:1297-1298`（contacts.statusCode.*）
- 【事実】まとめる画面の文に仕組みの言葉が残る（ja/en 6キー・`frontend/src/locales/ja.json:2522`・`:2526`・`:2532`・`:2533`・`:2591`・`:2597`）:
  - mergeCompany.selectMaster「マージ先（master）の顧客情報を選択」
  - mergeCompany.reasonLabel「マージ理由（任意 / audit_logs に記録）」
  - mergeCompany.confirmDesc3「master 側が pending_dedup_review だった場合、自動的に active に昇格します。」
  - mergeCompany.confirmDesc4「監査ログ (audit_logs) に操作内容が記録されます。」
  - mergeContact.reasonLabel「統合理由（任意 / audit_logs に記録）」
  - mergeContact.confirmDesc3「監査ログ (audit_logs) に操作内容が記録されます。」
  - 使う所: `frontend/src/components/MergeCompanyModal.tsx:296`、`frontend/src/components/MergeContactModal.tsx:294`。前例: mergeLead は「まとめる理由（任意・記録に残ります）」で仕組みの言葉なし。
- 【事実】本番の画面（2026-11-11 AI が Chrome で目視・保存なし）: 連絡先の編集の状態の選択肢は 有効/無効/アーカイブ/重複確認待ち。一覧の札「重複確認待ち」は該当0件で見えない（visual/badge.txt）。

## 4. まとめ（同じ4つの値が書かれている場所の数）

| 置き場 | 何か所 |
|---|---|
| DB の CHECK（本番） | 10表 |
| 会社を作る処理 | 2か所（tenant.py:224・:255） |
| サーバーの列挙 | 2か所 |
| 画面の見た目表（ADR-120） | 1か所に2組 |
| 画面で自前に並べる所 | 8か所 |
| 名前の辞書キー | 4つの値に対し 11キー（ja・en それぞれ） |

## 5. 未確認・ずれ

- 【未確認】見込み客の状態（ADR-109）を同じ形に寄せるか。今回の対象外とし、PO に別テーマとして確認する（design §9）。
- 【事実】ADR-109 の「名前は辞書」と、PO 方針（2026-11-11）「値は DB に1か所・分析の材料に使える状態」は向きが違う。今回の会社・連絡先は新しい ADR で「名前も DB」と決める（design §8）。
