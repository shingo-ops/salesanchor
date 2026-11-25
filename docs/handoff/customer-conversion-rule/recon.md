# recon: 「顧客」に切り替える基準（便1）

調べた日: 2026-11-25（JST）。根拠はすべて `origin/main`（`git show origin/main:<path>`）と本番の読み取り専用の鍵（reader）。

## 0. 既存 ADR の検索

`git grep -n -l -E "existing_customer|既存顧客" origin/main -- docs/adr` の結果:
ADR-015、ADR-108、ADR-1089、ADR-109、ADR-110、ADR-119、ADR-134、ADR-139、karte_reference.html。
関係が深いもの:
- `docs/adr/ADR-109-leads-status-ssot-immutable-codes.md:23`: 段階は 7 つ（lead・negotiating・existing_customer・follow_up_short・follow_up_long・lost・out_of_scope）。**どうなったら既存顧客になるかは決めていない**。
- `docs/adr/ADR-1089-inbox-karte-stage-layout.md` What 2: 「成約後＝existing_customer・follow_up_short・follow_up_long」。**PO の 11/25 の言葉と食い違う**（追客は見込みのある新規顧客）。
- `docs/adr/ADR-097-sa-customer-registration-form.md:13`: 営業の流れは「見積→登録→請求→支払い→発送」を一気に進める。
- `docs/adr/ADR-104-sa-payment-confirmation-status-pnl.md`: 入金で受注を「支払い待ち→仕入れ中」へ自動で進める（既存顧客には触れていない）。

## 1. PO の言葉（2026-11-25 チャット・原文）

- 「追客短期は商談で成約しなかったが、見込みがある場合に割り当てるステータスなのでまだ顧客に切り替えないでほしい、顧客に切り替えるトリガーとしては登録フォームに入力をしてくれて会社情報がDBに登録されて初回の支払いが完了した顧客を対象とする基準にしたい」
- 「「追客（短期）」「追客（長期）」→見込みがある新規顧客である」
- 切り替えの形: 選択肢「段階そのものを自動で「既存顧客」に変える」に「1」。
- 「まず正入りすると3つが揃った人だけを顧客にする。そのうえでアプリを使用する前に取引をしていた顧客をアプリにアップロードするための入口も設けてほしい、CSVで入れられる入口を作ってほしいのだが詳しい要件定義や方法については次便で進める」

## 2. 段階を書き換える道（コードの事実）

- 手で変える: `backend/app/routers/leads.py:490` `update_lead`（PATCH `/leads/{id}`）。`leads.py:519` で status を文字にし、`leads.py:535` は失注のときだけ追加の確認をする。**既存顧客への変更を止める確認は無い**。
- 作るとき: `backend/app/routers/leads.py:401` `create_lead`、`leads.py:443` で `data.status` をそのまま入れる。
- 商談にする: `backend/app/routers/leads.py:828`（`SET status = 'negotiating'`）。
- 統合: `backend/app/routers/leads.py:3241` `merge_leads`。消す側が lead 以外なら 400（status は書き換えない）。
- 画面の選択肢: `frontend/src/constants/leadStatus.ts:9-17` の `LEAD_STATUS_CODES`（7 つ）を、`frontend/src/pages/leads/LeadEditPage.tsx:73`・`LeadFormFields.tsx:44`・`LeadsPage.tsx:143` がそのまま選択肢にしている。
- backend 全体で `existing_customer` を**書き込む**コードは無い（`git grep -n existing_customer origin/main -- backend/app` は読む・数えるだけ）。いまの既存顧客はすべて手で付けたもの。

## 3. 3 つの条件を記録している場所（コードと本番の事実）

| 条件 | 記録の場所 | 書かれる道 |
|---|---|---|
| ① 登録フォームに入力 | `public.registration_tokens`（列: id・tenant_id・lead_id・type・expires_at・used_at・created_by・created_at）。type は register・add_address・change_billing | `backend/app/routers/registration_tokens.py:215` `register_customer`（POST `/public/register`） |
| ② 会社の登録 | `companies.lead_id`（`registration_tokens.py:50` のコメント「companies.lead_id が SSOT」） | フォーム: `registration_tokens.py:270`。ほかに手で作る `backend/app/routers/companies.py:440`、`backend/app/routers/integrations.py:653` |
| ③ 初回の支払い | `invoices.paid_at`（`invoices.company_id` で会社へ） | 手で入金: `backend/app/routers/invoices.py:907` 付近 `pay_invoice`（`UPDATE invoices SET status = 'paid', paid_at = ...`）。PayPal 戻り: `backend/app/routers/integrations.py:799`。PayPal 通知: `integrations.py:948` |

- 受注にも別の支払いの印がある: `backend/app/routers/orders.py:155` `set_order_paid`（手で付け外しできる。説明に「現状は手動フラグ」）。
- 入金済みの請求書は無効にできない（`invoices.py` の void は `status == "paid"` を止める・上の void_invoice の 124 行目相当）。

## 4. 本番の数（2026-11-25 09:1x JST・reader）

| | テスト株式会社（tenant 1） | HIGH LIFE JPN（tenant 4） |
|---|---|---|
| リード | 475（既存顧客151・失注319・リード3・商談中1・追客短期1） | 56（56 とも リード） |
| 会社の登録があるリード | 既存顧客151のうち2 | 51（うち 49 社は 2026-04-23 に一度だけ移したデータ・#93/#109） |
| 登録フォーム register の入力済み | 3 | 1 |
| 請求書 / 入金済み | 0 / 0 | 0 / 0 |
| 受注 / 支払済 | 0 / 0 | 0 / 0 |

- 取引データを取り込む入口は無い（`@router.post` で import/upload/csv/bulk を含む道は `tcg_review_csv.py:51,64` だけ）。

## 5. 画面への影響（コードの事実）

- `frontend/src/pages/inbox/karteLayout.ts:114` `CUSTOMER_STATUSES = ["existing_customer", "follow_up_short", "follow_up_long"]` → 追客のカルテが「顧客」タブで開く。
- `frontend/src/pages/inbox/InboxKartePanel.tsx:380-383`: 下の操作の帯は、リードなら「商談にする」、既存顧客なら「請求書を作成」。**それ以外（商談中・追客）は `if (!primaryLabel) return null`（383 行目）で帯ごと出ない**。登録フォームのリンクを作るメニュー（同 401-420 行目）も、この帯の中にある。
  - → 新しい基準では「既存顧客になる前に、登録フォームを送り、請求書を作る」必要がある。商談中・追客で帯が出ないままだと、受信箱から先へ進めない。
- `frontend/src/pages/inbox/InboxKartePanel.tsx:421`: 請求先を変えるリンクは既存顧客だけ。
- `frontend/src/pages/inbox/useInboxState.ts:1011-1013` `handleCreateInvoice` は `/invoices/new` へ移るだけ（段階を見ない）。backend の請求書作りも段階を見ない（`git grep existing_customer origin/main -- backend/app/routers/invoices.py` は 0 件）。
- `frontend/src/pages/inbox/inbox.types.ts:24`: 受信箱の「既存顧客」タブは status = existing_customer で並べる。

## 6. 数え方への影響（コードの事実）

- `backend/app/routers/analytics.py:1129`「成約定義: leads.status = 'existing_customer'」ほか、成約数・成約率は existing_customer を数える（`analytics.py:116,519,539,577,593,1052,1090,1181,1214,1749` など）。式は変えない。新しい基準では、成約は「3 つがそろった人」の数になる。
- `docs/adr/ADR-015.md:88-101`: 既存顧客には AI が対応しない。基準が厳しくなるので、AI が対応しない相手は減る（どこで判定しているかは便1 の実装前に確かめる・未確認）。

## 7. 追加の調べ（2026-11-25・worktree の git grep）

- 支払いを書く道: `backend/app/routers/invoices.py:899`（入金登録）・`invoices.py:1145`（支払い状況を確認）・`backend/app/routers/integrations.py:799`・`integrations.py:948`・`backend/app/routers/orders.py:596`（支払済にする。`orders.py:598` で取り消し）。
- 画面のボタン: `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:233`（入金登録）・`frontend/src/pages/orders/OrdersTable.tsx:146`（支払済にする）・`OrdersTable.tsx:174`（取り消し）。
- 会社の lead_id を書く道: `backend/app/routers/companies.py:440`（作る・lead_id 必須 `backend/app/schemas/company.py:116`）・`companies.py:610`（更新。`companies.py:103` の更新できる列に lead_id あり）・`registration_tokens.py:270`。`integrations.py:653` は lead_id を書かない。
- 統合: `backend/app/routers/leads.py:3241` `merge_leads`（会社を残る側へ移す・`reassigned_companies`）、`companies.py:742` `merge_companies`。
- 登録済みの判定（新規登録のリンクを断る）: `backend/app/routers/registration_tokens.py:86-102`（会社に既定の請求先の住所がある）。
- カルテの帯: `frontend/src/pages/inbox/InboxKartePanel.tsx:378-383`（帯はリードと既存顧客だけ）・`InboxKartePanel.tsx:401-431`（メニュー: 登録・住所を足す・請求先を変える〔既存顧客だけ〕）。カルテのリードは `frontend/src/pages/inbox/useInboxState.ts:381` で `GET /leads/{id}`（`backend/app/routers/leads.py:372` `get_lead`）。
- AI の返事の道で既存顧客を見て分ける箇所: `git grep -n existing_customer -- backend/app` で 0 件（`schemas/lead.py:35`・`services/lead_conversion_factors.py:27`・`services/tenant.py:2284` は定義と数え方）。
