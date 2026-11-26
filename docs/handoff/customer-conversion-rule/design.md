# design: 「顧客」に切り替える基準（便1）

状態: **KGI は PO 承認済み**（2026-11-25 チャット「1」。K1〜K7 と §3 の前提）。設計審査 1 回目は REVISE（2026-11-25・必須 4 件）。必須 2〜4 と推奨は本版で直した。必須 1（「登録済み」の判定のそろえ方）は PO が 2026-11-26「1」で決めた（§3・会社に既定の請求先があること）。調査: [recon.md](recon.md)。ADR: [ADR-1090](../../adr/ADR-1090-customer-conversion-three-conditions.md)（Proposed）。

## 1. 目的（PO の言葉は recon §1）

成約していない人（商談中・追客）が「顧客」として扱われないようにする。
「顧客」になるのは、登録フォームの入力・会社の登録・初回の支払いの 3 つがそろった人だけにする。
3 つがそろったら、段階は人の手を通さず自動で「既存顧客」になる。

## 2. KGI（PO が画面で ○× を付けられる形）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 3 つ（①登録が済んでいる〔その人の会社に既定の請求先がある。登録フォームで入れた・会社の画面で手で入れたのどちらも〕 ②その人の会社が登録されている ③その会社に支払い済みの記録が 1 件以上ある〔請求書の入金登録・PayPal での入金・注文一覧の「支払済にする」のどれか〕）がそろった瞬間に、段階が「既存顧客」になる。3 つがそろう順番は問わない | 試験: ③は請求書の入金と注文の支払済の 2 通りそれぞれで、3 つの順番 6 通りすべてで、最後の 1 つが入った直後に status=existing_customer。本番: テスト株式会社の試しのリードで フォーム送信→請求書作成→入金登録 を行い、リード一覧で「既存顧客」になっていること |
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
- 「登録フォームの入力」（登録が済んでいる）は、**その人の会社に既定の請求先がある**こと（`company_addresses.address_type = 'billing' AND is_default = TRUE`・`companies.lead_id` で人へ）で数える。PO 2026-11-26「1」（選択肢「会社に請求先が入っている」で見る）。フォームで入れた人も、会社の画面で手で入れた人も、2026-04-23 に移した HIGH LIFE JPN の 49 人も登録済みになる。登録フォームのリンクを隠す判定（K7・ADR-127 §4 の 409）と同じ 1 つの判定を使う。
- 自動で戻すことはしない。入金済みの請求書は無効にできない（recon §3）。注文の支払済は取り消せるが、取り消しても戻さない。
- 既存顧客から手で別の段階へ変えることは、今までどおりできる（PO は戻す方の決まりを言っていない）。変えた後は、3 つのどれかがもう一度起きたときに確かめ直す。

## 4. 変更の中身

### 4-1. 判定は 1 か所（backend）

新しい関数 `promote_lead_if_customer(db, tenant_id, lead_id) -> bool` を `backend/app/services/customer_conversion.py`（新規）に置く。

- 最初に、そのリードの行を `SELECT ... FROM leads WHERE id = :lead_id FOR UPDATE` で押さえる（PostgreSQL のときだけ。試験の SQLite は FOR UPDATE が使えないので `is_postgresql(db)` で分ける・`registration_tokens.py:240-243` と同じ形）。理由: 入金とフォームの送信が別々の取引で同時に走ると、どちらも相手の書き込みが見えず（READ COMMITTED）、3 つそろっても切り替わらない。行を押さえると後の取引は前の取引の commit を待ち、その後の SQL で相手の書き込みが見える。
- その後で、3 つの条件を 1 本の SQL で確かめる（押さえた後の別の文にする）。条件の SQL はこの関数の中だけに書く。
- 登録済みの判定は同じファイルの `is_registration_completed(db, tenant_id, lead_id) -> bool` に置き、`promote_lead_if_customer` もこれを使う（§4-3 の 3 か所もこれを呼ぶ）。
- テナントの表（leads・companies・company_addresses・invoices・orders）は `tenant_table_ref(db, tenant_id, "<表>")`（`backend/app/auth/dependencies.py:438`）で書き、search_path に頼らない。判定に `public.registration_tokens` は使わない（PO 11/26「1」）。
- 会社（②）は会社の状態（active・archived など）を問わず数える。理由: 自動で戻さない決まり（§3）と合わせ、一度そろった記録の扱いを状態で変えないため。
- そろっていれば `UPDATE leads SET status = 'existing_customer', updated_at = NOW() WHERE id = :lead_id AND status <> 'existing_customer'` を行う。監査の記録（`record_audit_log`、action="auto_convert"）を残す。
- 呼んだ側の取引の中で動く（commit は呼び元）。
- 失敗の切り離し: 関数の中身は `async with db.begin_nested():`（SAVEPOINT・`backend/app/routers/assistant.py:215` と同じ形）で包み、判定が例外を出したら SAVEPOINT だけを戻して `logger.error` を残し、False を返す。入金・フォームの記録は消さない（PayPal の戻りと通知は記録と commit が 1 つの try の中にあり、包まないと入金の記録ごと rollback される・`integrations.py:797-813`・`:940-962`）。切り替え損ねた人は、3 つのどれかが次に書かれたときに確かめ直される。

呼ぶ場所（3 つの条件が書かれる道すべて。2026-11-25 に worktree の `git grep` で数えた・recon §7）:

| 道 | 場所（今の行） | lead_id の求め方 |
|---|---|---|
| 登録フォームの送信 | `backend/app/routers/registration_tokens.py:217` `register_customer` の `mark_token_used`（`:403`）の後・commit（`:405`）の前 | トークンの lead_id |
| 請求書の「入金登録」（手） | `backend/app/routers/invoices.py:885` `pay_invoice` の請求書の UPDATE（`:899`）と受注の UPDATE の後・commit 前 | 請求書の company_id → `companies.lead_id` |
| 請求書の「支払い状況を確認」（PayPal を手で確かめる） | `backend/app/routers/invoices.py:1145` の UPDATE と受注の UPDATE の後・commit 前 | 同上 |
| PayPal の戻り | `backend/app/routers/integrations.py:799` の後・commit 前 | 同上 |
| PayPal の通知 | `backend/app/routers/integrations.py:948` の後・commit 前 | 同上 |
| 注文の「支払済にする」 | `backend/app/routers/orders.py:571` `set_order_paid` の UPDATE（`:600-608`）の後・commit 前。`data.paid` が true のときだけ（`:596` は SET 句を組む行） | 注文の company_id → `companies.lead_id` |
| 会社を作る（リード必須） | `backend/app/routers/companies.py:440` の後・commit 前 | `data.lead_id` |
| 会社を作るときの住所 | `backend/app/routers/companies.py:511` `_replace_addresses`（上の「会社を作る」と同じ呼び出しで足りる・commit 前に 1 回） | `data.lead_id` |
| 会社を直す（リードの付け替え・住所の入れ替え） | `backend/app/routers/companies.py:554` `update_company`。更新に lead_id が入るとき、または `addresses` が入るとき（`:620-622`）。commit 前に 1 回 | 直した後の会社の lead_id |
| 配送先を足すフォーム | `backend/app/routers/registration_tokens.py:423` `add_address` の `mark_token_used`（`:494`）の後・commit 前 | トークンの lead_id |
| 請求先を変えるフォーム | `backend/app/routers/registration_tokens.py:512` `change_billing` の `mark_token_used`（`:616`）の後・commit 前 | トークンの lead_id |
| リードの統合 | `backend/app/routers/leads.py:3241` `merge_leads` の `_execute_lead_merge` の後、残る側を読み直す SELECT（`:3269` 付近）の**前**（返事の段階が古くならないように） | 残る側の lead_id |
| 会社の統合 | `backend/app/routers/companies.py:742` `merge_companies` の commit 前（請求書・注文が残る側へ移る） | 残る側の会社の lead_id |

- `backend/app/routers/integrations.py:653`（PayPal 決済テストの会社）は lead_id を書かないので対象外。
- 配送先を足す・請求先を変えるフォームは、今の決まりでは登録済みの人にしか出ないので、新しく①を満たすことは無い。それでも `company_addresses` を書く道をすべて表に入れ、「書く道＝呼ぶ道」を grep で照らせる形にする。
- 実装役は着手時に `git grep -n -E "paid_at *= *(\{PAID_AT_SQL\}|NOW)|INSERT INTO companies|UPDATE companies SET|mark_token_used|company_addresses"` をもう一度流し（`company_addresses` は INSERT・UPDATE・DELETE の行だけを見る）、上の表と食い違えば止めて報告する。

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
  - 「登録が済んだ」の判定は backend の 1 つの関数に置き、新規登録のリンクを断る所（`registration_tokens.py:86-102`）・請求先を変えるリンクを未登録で断る所（`registration_tokens.py:105-120`・今は同じ SQL の写し）・カルテのデータ（`GET /leads/{id}` の返り値に `registration_completed` を足す）の 3 か所がそれを呼ぶ。画面は自分で判定しない。判定の中身は「その人の会社に既定の請求先がある」（PO 11/26「1」・§3）。
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

- backend 試験: `backend/tests/test_customer_conversion.py`（新規）。K1 の 6 通り・K2 の 7 通り・K3 の 2 本・各道 1 本。会社の画面で手で請求先を入れた人（フォームを使っていない人）も、支払いで既存顧客になる試験 1 本。判定が例外を出しても入金の記録が残る試験 1 本。
- 1 か所だけの試験（ADR-1090 受入条件の最後の行を ○× にする）: `backend/app` の中で `status = 'existing_customer'` を書く SQL と、登録済みの判定の SQL（`address_type = 'billing'` と `is_default`）が、決めた関数のファイルにしか無いことを、ファイルを読んで数える試験 1 本。
- frontend 試験: karteLayout の追客 2 段階・帯の出し分け・選択肢に既存顧客が無いこと。
- 本番: テスト株式会社の試しのリード（TST-KARTE-3 を使い回すか、新しく作るかは実装カードで決める）。K6 は反映の前後で reader で数える。

## 8. 外部事例

不要。理由: 社内の業務の決まり（何をもって顧客とするか）を PO が決めたもので、外の数値で正しさを確かめる種類の話ではないため。

## 9. 維持の仕組み

- 判定の条件は `customer_conversion.py` の 1 か所だけ。ほかの場所に同じ条件を書かない（ADR-1090 に書く）。
- 試験 `test_customer_conversion.py` が CI で毎回走る。手で既存顧客を付ける道が増えれば K3 の試験が落ちる。条件の SQL を別の場所に写せば「1 か所だけの試験」が落ちる。
- 次の便（CSV の取り込み）も、この関数を通して既存顧客にする。

## 10. 未決事項

- なし。設計審査 1 回目の必須 1（「登録済み」をどの記録で決めるか）は、PO が 2026-11-26「1」で「会社に既定の請求先がある」に決めた。決める前の本番の数（2026-11-25 18:36 JST・reader）: HIGH LIFE JPN は「請求先あり・フォームの記録なし」49 人・「フォームの記録だけ」1 人、テスト株式会社は「両方あり」3 人・「請求先だけ」1 人。
