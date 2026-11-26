# design: 「顧客」に切り替える基準（便1）

状態: **KGI は PO 承認済み**（2026-11-25 チャット「1」。K1〜K7 と §3 の前提）。設計審査 1 回目は REVISE（2026-11-25・必須 4 件）。2 回目は REVISE（2026-11-26・必須 3 件＝公開の道の監査の記録・1 か所だけの試験の数え方・一覧の新規作成の選択肢。推奨 4〜6 も本版で直した）。3 回目は REVISE（2026-11-26・必須 1 件＝1 か所だけの試験 (b) の数え方。推奨 2〜5 とあわせて本版で直した）。4 回目は REVISE（2026-11-26・必須 1 件＝カルテの欄を離れたときの保存が古い段階を送り、自動の既存顧客を戻してしまう。推奨 2・3 とあわせて本版で直した）。5 回目は REVISE（2026-11-26・必須 1 件＝リード一覧の編集と編集画面の保存も開いた時点の段階を毎回送る。推奨 2・3 とあわせて本版で直した）。6 回目は REVISE（2026-11-26・必須 1 件＝「開いた時点の値」を何と比べるかが決まっていない。推奨 2〜4 とあわせて本版で直した）。**7 回目は APPROVE**（2026-11-26・クラウドの独立した審査役・推奨 2 件＝表を見張る試験 2 本・同時に押されたときの文、は impl-card に書いた）。必須 2〜4 と推奨は本版で直した。必須 1（「登録済み」の判定のそろえ方）は PO が 2026-11-26「1」で決めた（§3・会社に既定の請求先があること）。調査: [recon.md](recon.md)。ADR: [ADR-1090](../../adr/ADR-1090-customer-conversion-three-conditions.md)（Proposed）。

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

新しい関数 `promote_lead_if_customer(db, tenant_id, lead_id, *, actor_user_id: int | None, via: str) -> bool` を `backend/app/services/customer_conversion.py`（新規）に置く。

- 最初に、そのリードの行を `SELECT ... FROM leads WHERE id = :lead_id FOR UPDATE` で押さえる（PostgreSQL のときだけ。試験の SQLite は FOR UPDATE が使えないので `is_postgresql(db)` で分ける・`registration_tokens.py:240-243` と同じ形）。理由: 入金とフォームの送信が別々の取引で同時に走ると、どちらも相手の書き込みが見えず（READ COMMITTED）、3 つそろっても切り替わらない。行を押さえると後の取引は前の取引の commit を待ち、その後の SQL で相手の書き込みが見える。
- その後で、3 つの条件を 1 本の SQL で確かめる（押さえた後の別の文にする）。条件の SQL はこの関数の中だけに書く。
- 登録済みの判定は同じファイルの `is_registration_completed(db, tenant_id, lead_id) -> bool` に置き、`promote_lead_if_customer` もこれを使う（§4-3 の 3 か所もこれを呼ぶ）。
- テナントの表（leads・companies・company_addresses・invoices・orders）は `tenant_table_ref(db, tenant_id, "<表>")`（`backend/app/auth/dependencies.py:438`）で書き、search_path に頼らない。判定に `public.registration_tokens` は使わない（PO 11/26「1」）。
- 会社（②）は会社の状態（active・archived など）を問わず数える。理由: 自動で戻さない決まり（§3）と合わせ、一度そろった記録の扱いを状態で変えないため。
- そろっていれば `UPDATE leads SET status = 'existing_customer', updated_at = NOW() WHERE id = :lead_id AND status <> 'existing_customer'` を行う。記録の残し方（審査 2 回目の必須 1）: `audit_logs.user_id` は NOT NULL（`backend/app/services/tenant.py:484`）で、登録フォームの送信・配送先/請求先のフォーム・PayPal の戻りと通知はログインした人がいない道。`actor_user_id` があるとき（ログインした人の道）だけ `record_audit_log`（action="auto_convert"・new_data に `{"status": "existing_customer", "via": via}`）を書く。`actor_user_id` が None のときは監査の表に書かず、`logger.info("[customer_conversion] auto_convert tenant=%s lead=%s via=%s")` を残す（今もこれらの公開の道は監査の表に書いていない・`registration_tokens.py` の `record_audit_log` は `create_token` の 1 か所だけ）。架空のシステム利用者は作らない。`via` は表の「道」の英字名（例 `register_form`・`invoice_pay`・`paypal_return`・`paypal_webhook`・`order_paid`・`company_create`・`company_update`・`add_address`・`change_billing`・`lead_merge`・`company_merge`・`invoice_paypal_check`）。
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

- 呼び元の `actor_user_id`: ログインした人の道は `current_user.id`。公開の道（登録フォーム・配送先・請求先・PayPal の戻りと通知）は None。

### 4-2. 手で既存顧客にする道を閉じる（backend＋画面）

- `leads.py:490` `update_lead`: 新しい status が existing_customer で、今が existing_customer でなければ 422（`detail="existing_customer_is_automatic"`）。
- `leads.py:401` `create_lead`: status が existing_customer なら 422。
- 画面: 選択肢の一覧から existing_customer を外した「手で選べる段階」の一覧を `frontend/src/constants/leadStatus.ts` に 1 つ足し（例 `MANUAL_LEAD_STATUS_CODES`）、`LeadEditPage.tsx:73`・`LeadFormFields.tsx:44` はそれを使う。今が既存顧客の人の編集画面では、今の値は表示する（選び直しはできない）。`LeadsPage.tsx:143` の一覧は 2 か所で使われている（審査 2 回目の必須 3）: 絞り込み（`:284`）は 7 つのまま、新規作成の画面（`:349`）は手で選べる段階の一覧に替える。
- 422 の画面の文は `t()` で ja/en 両方に足す（ADR-027）。

- 編集の保存で古い段階を送らない（審査 5 回目の必須 1・4 回目の必須 1 と同じ形の穴）: リード一覧の編集（`frontend/src/pages/leads/LeadsPage.tsx:210` `status: editForm.status`・控えは `toForm` の `:109`）と編集画面（`frontend/src/pages/leads/LeadEditPage.tsx:128` `status: form.status`・控えは `:83`）は、開いた時点の段階を毎回 PATCH で送っている。編集の間に入金などで自動で既存顧客になると、メモを 1 つ直しただけで古い段階が送られ、既存顧客が黙って戻る。直し方: 2 か所とも、`status` は開いた時点の値と違うとき（利用者が選び直したとき）だけ送る。比べる相手（審査 6 回目の必須 1）: 編集画面は `useSeededForm`（`frontend/src/lib/query/useSeededForm.ts:18-22`）がすでに持っている控え `base`（フォームを作った時点の値・利用者が直し始めた後は取り直しが入っても変わらない）を戻り値に足して外に出し、`base.status` と比べる。`leadQ.data.status`（取り直しで新しくなる）とは比べない。一覧の編集は `useRecordDrawer`（`frontend/src/hooks/useRecordDrawer.ts`・`handleRowClick` で `toForm` する所）に、開いた時点の値 `baseForm` を戻り値として足し、`baseForm.status` と比べる。どちらも戻り値を 1 つ足すだけで、今の使い手（`useRecordDrawer` は 9 ファイル・2026-11-26 `git grep`）の動きは変わらない。失注の理由（`buildLostReasonUpdatePayload`・`LeadFormFields.tsx:46-58`）は今のまま（段階を送らなくても、backend の失注の確かめ `leads.py` の `is_lost_transition` は段階が変わるときだけ働くので、今と同じに動く）。画面からリードを直す呼び出しは 8 か所（2026-11-26 `git grep` `patch.*/leads/`）。ほかの 5 か所は古い段階を送らない: ダッシュボード 2 か所（`PriorityProspectsSection.tsx:225`・`WeeklyAdvisorSection.tsx:237`）は次の行動だけ、受信箱の 3 か所（`useInboxState.ts:991`・`:1050`・`:1106`）は決まった段階を送る専用の呼び出し。カルテの保存（`:563`）は §4-3。

### 4-3. カルテ（画面）

- `karteLayout.ts:114` の成約後の一覧を `["existing_customer"]` だけにする。追客（短期・長期）は商談中と同じ見せ方（`NEGOTIATING_LAYOUT`）にする。ADR-1089 What 2 を直す。
- `InboxKartePanel.tsx:380-383`: 帯（下の固定のボタンの列）はすべての段階で出す（審査 3 回目の推奨 4。リンクのメニューは帯の中にあり、帯が無いと K7 の「段階によらない」が守れないため）。大きいボタンは段階で決める:

  | 段階 | 大きいボタン |
  |---|---|
  | lead | 「商談に進める」（今のまま） |
  | negotiating・follow_up_short・follow_up_long・existing_customer | 「請求書を作成」 |
  | lost・out_of_scope | 出さない（「⋯」のメニューだけを出す） |

- `ActionBar`（`InboxKartePanel.tsx:338-346`）に `registrationCompleted: boolean` を足し、呼ぶ所（`:255-262`）で `leadDetail.registration_completed === true` を渡す。値が無い（undefined・null）ときは「まだ登録が済んでいない」として扱う。
- メニューの「統合」は今も `canMerge && status === "lead"`（`InboxKartePanel.tsx:446`）で出し分けている。帯を広げても統合が出るのは lead だけのまま（審査 3 回目の推奨 5 は今のコードで満たされている）。この行は変えない。
- メニューのリンク（PO 11/25「登録フォーム入力済みの顧客に対して再度登録フォームを発行すると重複したデータが発生する原因になるのでSSOTさせるためにフォーム登録済みの顧客には再発行はしない、変更が必要な場合は元のデータに追加していく形」）:
  - 登録がまだ: 「登録フォームのリンク」だけを出す。
  - 登録が済んだ: 「登録フォームのリンク」を出さない。「配送先を足すリンク」（add_address・配送先を 1 行足す）と「請求先を変えるリンク」（change_billing・前の請求先を残したまま新しい行を足して既定にする・ADR-127 §1）を出す。段階によらない（今は請求先を変えるリンクが既存顧客だけ・`InboxKartePanel.tsx:421`）。
  - 「登録が済んだ」の判定は backend の 1 つの関数に置き、新規登録のリンクを断る所（`registration_tokens.py:86-102`）・請求先を変えるリンクを未登録で断る所（`registration_tokens.py:105-120`・今は同じ SQL の写し）・カルテのデータの 3 か所がそれを呼ぶ。カルテのデータ: `LeadResponse`（`backend/app/schemas/lead.py:221`）に `registration_completed: bool | None = None` を足し、`leads.py` で `LeadResponse` を返す 5 か所（`:392` 詳細・`:482` 作る・`:755` 直す・`:862` 商談に進める・`:3316` 統合）すべてで値を入れる（一覧 `:298` は入れない＝None のまま。リードごとに問い合わせが増えるのを避ける。カルテは一覧の値を使わず詳細 `:392` を読む）。理由: カルテは直した後の返り値を手元の控えに書き戻す（`frontend/src/pages/inbox/useInboxState.ts:563-564`）ので、直す道で値が抜けるとメニューが「登録前」に戻ってしまう。画面の型 `LeadDetail`（`frontend/src/pages/inbox/inbox.types.ts:73`）にも `registration_completed?: boolean | null` を足す。画面は自分で判定しない。判定の中身は「その人の会社に既定の請求先がある」（PO 11/26「1」・§3）。
- カルテの欄を離れたときの保存（審査 4 回目の必須 1）: 今は手元の控えを丸ごと PATCH で送っている（`frontend/src/pages/inbox/useInboxState.ts:558-563`・外すのは `id`・`lead_code`・`prospect_rank` だけ）。控えには開いた時点の `status` が入っているので、開いている間に入金などで自動で既存顧客になると、欄を 1 つ直しただけで古い段階が送られ、既存顧客が黙って戻る。直し方: 送る中身から外す項目に `status` と `registration_completed` を足す。カルテの欄に段階を変える入力は無い（`InboxKartePanel.tsx` の `handleCardFieldChange` の呼び出しは email〜cs_memo の項目だけ・2026-11-26 `git grep`）。段階を変える道は今の専用の呼び出し（商談に進める `useInboxState.ts:991`・対象外 `:1050`・`:1106`）のままで、これは変えない。
- `LeadUpdate`（`backend/app/schemas/lead.py:154`）は今、知らない項目を捨てる設定。上の直しで画面は `registration_completed` を送らなくなるので、後で知らない項目を断る設定に変えても保存は落ちない（審査 4 回目の推奨 3）。
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
| 条件を書く道を 1 つ見落とし、そろっても既存顧客にならない | 実装前に `companies.lead_id`・`company_addresses`・`invoices.paid_at`・`orders.paid_at` を書く道を git grep で全部数え（§4-1 の grep）、カードに一覧で書く。試験で道ごとに 1 本 |
| 手で既存顧客を付けていた担当者が困る | HIGH LIFE JPN で既存顧客を付けた人は今 0 人（recon §4）。画面の 422 の文で「支払いがそろうと自動で切り替わります」と出す |
| 既存顧客にだけ AI が対応しない決まり（ADR-015）への影響 | 2026-11-25 `git grep -n existing_customer -- backend/app` で、AI の返事の道に既存顧客を見て分ける箇所は 0 件（数え方・型の定義だけ）。今回の変更で AI の動きは変わらない |
| 行を押さえる順が道で逆になる（会社を直す道は会社→リード `companies.py:610`、リードの統合はリード→会社 `leads.py:3187`）。まれに PostgreSQL がデッドロックで片方を止める | 止まった側は SAVEPOINT が戻るだけで、入金・住所の記録は残る（判定の失敗は `logger.error`）。切り替えはそのとき抜け、3 つのどれかが次に書かれたときに確かめ直される。既知のこととして残す |
| 公開の道（フォーム・PayPal）の切り替えは監査の表に残らない | `logger.info` に tenant・lead・via を残す（§4-1）。リードの `updated_at` も変わる |
| 開いたままの古い画面で「商談に進める」「対象外」を押すと、その間に自動で既存顧客になった人が戻る（審査 6 回目の推奨 2）。手で既存顧客には戻せない | 商談に進める専用の道（`backend/app/routers/leads.py` の `convert_lead`・`WHERE status != 'negotiating'`）は、今が existing_customer なら 409 `already_existing_customer` で断る（§4-2 と同じ `leads.py` の変更）。受信箱の 3 か所（`useInboxState.ts:991`・`:1050`・`:1106`）は段階を名指しで送る PATCH で、利用者が選んだ操作と区別できないため、本便では直さず既知のこととして残す。起きたときは会社・請求先・支払いのどれかが次に書かれたときに確かめ直される（§4-1）|
| 成約数が減って見える | 今の HIGH LIFE JPN は既存顧客 0 人なので、今の数は変わらない |

## 7. 受入の確かめ方（KGI の検証方法の詳しい手順）

- backend 試験: `backend/tests/test_customer_conversion.py`（新規）。K1 の 6 通り（②を最後にする順番の作り方: 請求書は `company_id` が必須〔`backend/app/schemas/invoice.py:78`〕で、会社を作るときもリードが必須なので、先に別のリード X の会社に請求先と入金を入れ、最後に `update_company` で会社の lead_id を本人へ付け替える〔`companies.py:103` の `lead_id` は直せる列〕。X は 3 つがそろった時点で既存顧客になってよい。確かめるのは付け替えた直後に本人が既存顧客になること）・K2 の 7 通り・K3 の 2 本・各道 1 本。会社の画面で手で請求先を入れた人（フォームを使っていない人）も、支払いで既存顧客になる試験 1 本。判定が例外を出しても入金の記録が残る試験 1 本。ログインした人がいない道（登録フォームの送信・PayPal の戻り）で切り替わり、監査の表に書かずに済む試験 1 本（審査 2 回目の必須 1）。
- 今ある試験の直し（審査 2 回目の推奨 4）: `backend/tests/test_analytics.py:625,692,770,830,967-973` は API から status=existing_customer を送ってリードを作っており、422 で落ちる。試験の下ごしらえで、作った後に SQL で直接 `UPDATE leads SET status = 'existing_customer'` を入れる形に替える（数え方の試験の目的は変えない）。ほかにも API で existing_customer を送る試験があれば同じに直す（実装役が `git grep -n existing_customer -- backend/tests frontend/src` で数える）。SQL で直接入れている試験（例 `backend/tests/test_lead_merge_pg.py:639` の `env.lead(status="existing_customer")` は `:165-171` で直接 INSERT）は 422 にならないので直さない。`*_pg.py`・`*_rls.py` は PostgreSQL の試験の場所（CI の `.github/workflows/test.yml:240-242`）でだけ動き、手元の SQLite では飛ばされる。直した結果は CI の PostgreSQL の試験で確かめる（手元で通っただけで済ませない）。
- PostgreSQL の試験（審査 2 回目の推奨 6）: `backend/tests/test_customer_conversion_pg.py`（新規・`test_assistant_karte_pg.py` と同じ形で、CI の `RLS_TEST_DATABASE_URL`・`RLS_ADMIN_DATABASE_URL` があるときに動く・`.github/workflows/test.yml:240-242`）。FOR UPDATE の分岐が通ること、2 本の取引（入金とフォーム送信）を順に重ねて最後に既存顧客になること、`tenant_table_ref` で別テナントの表を見ないことを確かめる。
- 1 か所だけの試験（ADR-1090 受入条件の最後の行を ○× にする・審査 2 回目の必須 2 で数える形を絞った）: `backend/app` の `.py` を読み、(a) 正規表現 `SET\s+status\s*=\s*'existing_customer'` に合う行が `services/customer_conversion.py` にだけあること（読む側の `WHERE status = 'existing_customer'` は数えない）、(b) 登録済みの判定の写しが残っていないこと。数える形（審査 3 回目の必須 1 で直した）: `backend/app/routers/registration_tokens.py` に、今の写し 2 か所（`:91`・`:111`）だけにある文字列 `JOIN companies c ON c.id = ca.company_id` が 0 件、かつ同じファイルに `is_registration_completed(` が 2 件あること（2026-11-26 `git grep` で、この文字列は `backend/app` の中でこの 2 行だけ）。`change_billing` の `:563` の `AND address_type = 'billing'` は、前の請求先を既定から外す UPDATE で、登録済みの判定ではないので数えない（`address_type = 'billing'` の件数では数えない）。会社の画面の請求先の読み書き（`companies.py:869,887` など）・`erp.py`・`duplicates.py`・`tasks/reports.py` の `address_type = 'billing'` は住所を読む・選ぶ処理で、登録済みの判定ではないので数えない。
- frontend 試験: karteLayout の追客 2 段階・帯の出し分け・選択肢に既存顧客が無いこと。カルテの欄を離れたときの保存で送る中身に `status` と `registration_completed` が入らないこと（控えに `status: "negotiating"` がある状態で保存し、PATCH の中身を確かめる・審査 4 回目の必須 1）。リード一覧の編集と編集画面で、段階を選び直さずに保存したとき PATCH に `status` が入らず、選び直したときは入ること（審査 5 回目の必須 1）。編集画面は、直し始めた後に取り直しで段階が existing_customer に変わっても、段階を選び直さない保存の PATCH に `status` が入らないこと（審査 6 回目の必須 1）。backend は、今が existing_customer の人に商談に進める（`/convert`）を送ると 409 になること。
- 本番: テスト株式会社の試しのリード（TST-KARTE-3 を使い回すか、新しく作るかは実装カードで決める）。K6 は反映の前後で reader で数える。

## 8. 外部事例

不要。理由: 社内の業務の決まり（何をもって顧客とするか）を PO が決めたもので、外の数値で正しさを確かめる種類の話ではないため。

## 9. 維持の仕組み

- 判定の条件は `customer_conversion.py` の 1 か所だけ。ほかの場所に同じ条件を書かない（ADR-1090 に書く）。
- 試験 `test_customer_conversion.py` が CI で毎回走る。手で既存顧客を付ける道が増えれば K3 の試験が落ちる。条件の SQL を別の場所に写せば「1 か所だけの試験」が落ちる。
- 次の便（CSV の取り込み）も、この関数を通して既存顧客にする。

## 10. 未決事項

- なし。設計審査 1 回目の必須 1（「登録済み」をどの記録で決めるか）は、PO が 2026-11-26「1」で「会社に既定の請求先がある」に決めた。決める前の本番の数（2026-11-25 18:36 JST・reader）: HIGH LIFE JPN は「請求先あり・フォームの記録なし」49 人・「フォームの記録だけ」1 人、テスト株式会社は「両方あり」3 人・「請求先だけ」1 人。
