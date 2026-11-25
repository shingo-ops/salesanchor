# design: 「顧客」に切り替える基準（便1）

状態: **KGI は PO 承認済み**（2026-11-25 チャット「1」。K1〜K7 と §3 の前提）。設計審査はこれから。調査: [recon.md](recon.md)。ADR: [ADR-1090](../../adr/ADR-1090-customer-conversion-three-conditions.md)（Proposed）。

## 1. 目的（PO の言葉は recon §1）

成約していない人（商談中・追客）が「顧客」として扱われないようにする。
「顧客」になるのは、登録フォームの入力・会社の登録・初回の支払いの 3 つがそろった人だけにする。
3 つがそろったら、段階は人の手を通さず自動で「既存顧客」になる。

## 2. KGI（PO が画面で ○× を付けられる形）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 3 つ（①登録フォーム〔新規登録の種類〕を送った ②その人の会社が登録されている ③その会社に支払い済みの記録が 1 件以上ある〔請求書の入金登録・PayPal での入金・注文一覧の「支払済にする」のどれか〕）がそろった瞬間に、段階が「既存顧客」になる。3 つがそろう順番は問わない | 試験: ③は請求書の入金と注文の支払済の 2 通りそれぞれで、3 つの順番 6 通りすべてで、最後の 1 つが入った直後に status=existing_customer。本番: テスト株式会社の試しのリードで フォーム送信→請求書作成→入金登録 を行い、リード一覧で「既存顧客」になっていること |
| K2 | 3 つのうち 1 つでも欠けていれば「既存顧客」にならない | 試験: 欠けの 7 通り（3 つのうち 0〜2 個）で status が変わらない |
| K3 | 手で「既存顧客」を選べない（リードの編集・一覧・新規作成の選択肢に出ない。画面を通さずに送っても拒否される） | 画面: 3 か所の選択肢に「既存顧客」が無い。試験: PATCH /leads/{id} と POST /leads に existing_customer を送ると 422 |
| K4 | 追客（短期・長期）のカルテは「商談」「連絡先」の 2 タブで、最初は「商談」 | 本番: 追客（短期）の試しのリードを住所で開き、最初のタブが「商談」 |
| K5 | 商談中・追客のカルテでも、下の帯に「請求書を作成」が出る | 本番: 商談中・追客の試しのリードで帯が出ていること（写真） |
| K7 | 登録フォームのリンクは、まだ登録が済んでいない人にだけ出る。登録が済んだ人には出ず、代わりに「配送先を足すフォーム」と「請求先を変えるフォーム」のリンクが出る（段階によらない） | 本番: 登録前の試しのリードでは「登録フォーム」だけ、登録後は「配送先を足す」「請求先を変える」だけがメニューに出る（写真）。試験: 登録済みの人に新規登録のリンクを作ろうとすると 409 already_registered（今の動き・ADR-127 §4）が変わらない |
| K6 | いま「既存顧客」の人の段階は変えない（自動で戻さない） | 本番: 反映の前後で、テナントごとの existing_customer の数が同じ（reader で数える） |

## 3. 決めたこと（PO の決定）と、設計で置いた前提

PO の決定:
- 追客（短期・長期）は見込みのある新規顧客。顧客ではない（11/25）。
- 3 つがそろったら段階を自動で既存顧客にする（11/25「1」）。
- 3 つがそろった人だけを顧客にする。手で付ける道は残さない（11/25）。
- アプリより前の取引先を CSV で入れる入口は次の便（11/25）。

設計で置いた前提（KGI の承認で一緒に確かめる）:
- 「初回の支払い」は、その会社の**請求書の入金**（`invoices.paid_at` あり）か、**注文の支払済**（`orders.paid_at` あり・`orders.company_id` で会社へ）のどちらかが 1 件以上あることで数える。PO 11/25「手動で支払い確認した場合も支払い済みにカウントする」。
  - 手の道は 2 つある: 請求書の詳細画面の「入金登録」（`InvoiceDetailPage.tsx:233`→`invoices.py:885` `pay_invoice`）と、注文一覧の「支払済にする」（`OrdersTable.tsx:146`→`orders.py:571` `set_order_paid`）。
  - 注文の支払済は取り消せる（`OrdersTable.tsx:174`→`paid_at = NULL`・`orders.py:598`）。取り消しても既存顧客から自動で戻さない（下の「自動で戻すことはしない」と同じ）。
- 「登録フォームの入力」は、**新規登録の種類**（`registration_tokens.type = 'register'`）を使い終えたこと（`used_at` が入っている）で数える。住所を足す・請求先を変える種類は数えない。
- 自動で戻すことはしない。入金済みの請求書は無効にできない（recon §3）。注文の支払済は取り消せるが、取り消しても戻さない。
- 既存顧客から手で別の段階へ変えることは、今までどおりできる（PO は戻す方の決まりを言っていない）。変えた後は、3 つのどれかがもう一度起きたときに確かめ直す。

## 4. 変更の中身

### 4-1. 判定は 1 か所（backend）

新しい関数 `promote_lead_if_customer(db, tenant_id, lead_id) -> bool` を `backend/app/services/customer_conversion.py`（新規）に置く。

- 3 つの条件を 1 本の SQL で確かめる。条件の SQL はこの関数の中だけに書く。
- そろっていれば `UPDATE leads SET status = 'existing_customer', updated_at = NOW() WHERE id = :lead_id AND status <> 'existing_customer'` を行う。監査の記録（`record_audit_log`、action="auto_convert"）を残す。
- 呼んだ側の取引の中で動く（commit は呼び元）。

呼ぶ場所（3 つの条件が書かれる道すべて。2026-11-25 に worktree の `git grep` で数えた・recon §7）:

| 道 | 場所（今の行） | lead_id の求め方 |
|---|---|---|
| 登録フォームの送信 | `backend/app/routers/registration_tokens.py:215` `register_customer` の `mark_token_used` の後・commit 前 | トークンの lead_id |
| 請求書の「入金登録」（手） | `backend/app/routers/invoices.py:899` の後・commit 前 | 請求書の company_id → `companies.lead_id` |
| 請求書の「支払い状況を確認」（PayPal を手で確かめる） | `backend/app/routers/invoices.py:1145` の後・commit 前 | 同上 |
| PayPal の戻り | `backend/app/routers/integrations.py:799` の後・commit 前 | 同上 |
| PayPal の通知 | `backend/app/routers/integrations.py:948` の後・commit 前 | 同上 |
| 注文の「支払済にする」 | `backend/app/routers/orders.py:596`（paid=true のときだけ）の後・commit 前 | 注文の company_id → `companies.lead_id` |
| 会社を作る（リード必須） | `backend/app/routers/companies.py:440` の後・commit 前 | `data.lead_id` |
| 会社のリードを付け替える | `backend/app/routers/companies.py:610`（更新に lead_id が入るときだけ） | 新しい lead_id |
| リードの統合 | `backend/app/routers/leads.py:3241` `merge_leads` の commit 前（会社が残る側へ移る） | 残る側の lead_id |
| 会社の統合 | `backend/app/routers/companies.py:742` `merge_companies` の commit 前（請求書・注文が残る側へ移る） | 残る側の会社の lead_id |

- `backend/app/routers/integrations.py:653`（PayPal 決済テストの会社）は lead_id を書かないので対象外。
- 実装役は着手時に `git grep -n -E "paid_at *= *(\{PAID_AT_SQL\}|NOW)|INSERT INTO companies|UPDATE companies SET|mark_token_used"` をもう一度流し、上の表と食い違えば止めて報告する。

### 4-2. 手で既存顧客にする道を閉じる（backend＋画面）

- `leads.py:490` `update_lead`: 新しい status が existing_customer で、今が existing_customer でなければ 422（`detail="existing_customer_is_automatic"`）。
- `leads.py:401` `create_lead`: status が existing_customer なら 422。
- 画面: 選択肢の一覧から existing_customer を外した「手で選べる段階」の一覧を `frontend/src/constants/leadStatus.ts` に 1 つ足し（例 `MANUAL_LEAD_STATUS_CODES`）、`LeadEditPage.tsx:73`・`LeadFormFields.tsx:44` はそれを使う。今が既存顧客の人の編集画面では、今の値は表示する（選び直しはできない）。`LeadsPage.tsx:143` は絞り込み用なので 7 つのまま。
- 422 の画面の文は `t()` で ja/en 両方に足す（ADR-027）。

### 4-3. カルテ（画面）

- `karteLayout.ts:114` の成約後の一覧を `["existing_customer"]` だけにする。追客（短期・長期）は商談中と同じ見せ方（`NEGOTIATING_LAYOUT`）にする。ADR-1089 What 2 を直す。
- `InboxKartePanel.tsx:380-383`: 商談中・追客でも帯を出す。大きいボタンは「請求書を作成」。
- メニューのリンク（PO 11/25「登録フォーム入力済みの顧客に対して再度登録フォームを発行すると重複したデータが発生する原因になるのでSSOTさせるためにフォーム登録済みの顧客には再発行はしない、変更が必要な場合は元のデータに追加していく形」）:
  - 登録がまだ: 「登録フォームのリンク」だけを出す。
  - 登録が済んだ: 「登録フォームのリンク」を出さない。「配送先を足すリンク」（add_address・配送先を 1 行足す）と「請求先を変えるリンク」（change_billing・前の請求先を残したまま新しい行を足して既定にする・ADR-127 §1）を出す。段階によらない（今は請求先を変えるリンクが既存顧客だけ・`InboxKartePanel.tsx:421`）。
  - 「登録が済んだ」の判定は、新規登録のリンクを断る今の判定（`registration_tokens.py:86-102`・会社に既定の請求先がある）と同じものを使う。この判定を backend の 1 つの関数に移し、リンクを断る所と、カルテのデータ（`GET /leads/{id}` の返り値に `registration_completed` を足す）の両方がそれを呼ぶ。画面は自分で判定しない。
  - 元のデータは消さず、足していく形は今の backend のまま（add_address は行を足す・change_billing は前の行を既定から外して新しい行を足す）。

### 4-4. 触らないもの

- 数え方（analytics・dashboard・goals・reports）の式。成約数は existing_customer を数えるまま（基準が厳しくなるので、意味が「3 つがそろった人」になる）。
- 今の既存顧客のデータ（テスト株式会社 151 人。HIGH LIFE JPN は 0 人）。
- DB の表の形（migration なし）。
- CSV の取り込み（次の便）。

## 5. 代わりの案と選ばなかった理由

- 見せ方だけを 3 条件で決め、段階は手のまま: PO が「1」（段階を自動で変える）を選んだ。
- 手で付ける道を残す: PO が「3つが揃った人だけ」と決めた。
- 夜にまとめて全員を確かめる定期の仕事: 入金からカルテが変わるまで遅れる。3 つが書かれる道は数が限られる（recon §3）ので、その場で確かめる方が早く、見張る物が増えない。

## 6. 危ないことと対処

| 危ないこと | 対処 |
|---|---|
| 条件を書く道を 1 つ見落とし、そろっても既存顧客にならない | 実装前に `companies.lead_id`・`invoices.paid_at`・`registration_tokens.used_at` を書く道を git grep で全部数え、カードに一覧で書く。試験で道ごとに 1 本 |
| 手で既存顧客を付けていた担当者が困る | HIGH LIFE JPN で既存顧客を付けた人は今 0 人（recon §4）。画面の 422 の文で「支払いがそろうと自動で切り替わります」と出す |
| 既存顧客にだけ AI が対応しない決まり（ADR-015）への影響 | 2026-11-25 `git grep -n existing_customer -- backend/app` で、AI の返事の道に既存顧客を見て分ける箇所は 0 件（数え方・型の定義だけ）。今回の変更で AI の動きは変わらない |
| 成約数が減って見える | 今の HIGH LIFE JPN は既存顧客 0 人なので、今の数は変わらない |

## 7. 受入の確かめ方（KGI の検証方法の詳しい手順）

- backend 試験: `backend/tests/test_customer_conversion.py`（新規）。K1 の 6 通り・K2 の 7 通り・K3 の 2 本・各道 1 本。
- frontend 試験: karteLayout の追客 2 段階・帯の出し分け・選択肢に既存顧客が無いこと。
- 本番: テスト株式会社の試しのリード（TST-KARTE-3 を使い回すか、新しく作るかは実装カードで決める）。K6 は反映の前後で reader で数える。

## 8. 外部事例

不要。理由: 社内の業務の決まり（何をもって顧客とするか）を PO が決めたもので、外の数値で正しさを確かめる種類の話ではないため。

## 9. 維持の仕組み

- 判定の条件は `customer_conversion.py` の 1 か所だけ。ほかの場所に同じ条件を書かない（ADR-1090 に書く）。
- 試験 `test_customer_conversion.py` が CI で毎回走る。手で既存顧客を付ける道が増えれば K3 の試験が落ちる。
- 次の便（CSV の取り込み）も、この関数を通して既存顧客にする。

## 10. 未決事項

- なし（KGI と §3 の前提は 2026-11-25 PO 承認済み）。
