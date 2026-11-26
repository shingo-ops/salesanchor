# 実装カード: 「既存顧客」は 3 つの条件がそろったときだけ自動で付く（ADR-1090）

- 枝: 設計は `release/customer-conversion-rule`、実装は `release/customer-conversion-rule-impl`（origin/main 起点・設計を取り込む）
- 設計: `design.md`（§4 が変更の中身・§7 が試験）・調査: `recon.md`・決定: `docs/adr/ADR-1090-customer-conversion-three-conditions.md`
- 書く人: クラウドの Sonnet。設計に無いことはしない。迷ったら止まって `NEEDS_DECISION:` で返す。
- DB の形は変えない（`migrations/` を触らない）。

## 0. 読んだ節

- `docs/ai-agents/executor-checklist.md`（作業前・commit 前・PR 前）
- ADR-1090 What 1〜8・ADR-072（`tenant_table_ref`・commit 直後の `reset_tenant_context`）・ADR-027（画面の文は `t()`・ja/en 同じキー）・ADR-144（金型）・ADR-1071（失敗の文の理由コード表）

## 受領確認

- 最初の報告で、§2 の触るファイルと §3 の想定分岐を読んだことを 1 行で返す。
- 作業場所: `git fetch origin` → `bash scripts/new-worktree.sh release/customer-conversion-rule-impl` → その場所へ移る → `git merge --no-edit origin/release/customer-conversion-rule`（設計書を取り込む。取り込みはこの 1 回だけ）→ `./scripts/dev/executor-preflight.sh || exit 1`。

## 1. 先に確かめる実物（違っていたら §3 の 1 行目）

| ファイル | 行 | 中身 |
|---|---|---|
| `backend/app/routers/registration_tokens.py` | 86-102 | `type=register` のときの登録済みの SQL（`JOIN companies c ON c.id = ca.company_id` が :91） |
| 同 | 105-120 | `change_billing` のときの同じ SQL（:111） |
| 同 | 240-243 | `if is_postgresql(db): lead_sql += " FOR UPDATE"` |
| 同 | 403・405 | `register_customer` の `mark_token_used` と `db.commit()` |
| 同 | 494・616 | `add_address`・`change_billing` の `mark_token_used` |
| `backend/app/routers/invoices.py` | 885-899 | `pay_invoice` と請求書の UPDATE |
| 同 | 1145 | PayPal を手で確かめる道の UPDATE |
| `backend/app/routers/integrations.py` | 797-813・940-962 | PayPal の戻り・通知の try（UPDATE と commit が同じ try の中） |
| `backend/app/routers/orders.py` | 571・600-608 | `set_order_paid` と UPDATE |
| `backend/app/routers/companies.py` | 440・511・554・620-622・742 | 会社を作る・住所・直す・統合 |
| `backend/app/routers/leads.py` | 392・482・755・862・3316 | `return LeadResponse(...)` の 5 か所 |
| 同 | 401・490・3241 | `create_lead`・`update_lead`・`merge_leads` |
| `backend/app/schemas/lead.py` | 221 | `class LeadResponse(BaseModel):` |
| `frontend/src/pages/inbox/karteLayout.ts` | 114 | `const CUSTOMER_STATUSES: readonly string[] = ["existing_customer", "follow_up_short", "follow_up_long"];` |
| `frontend/src/pages/inbox/InboxKartePanel.tsx` | 255-262・338-346・378-383・403-430・446 | 帯を呼ぶ所・`ActionBar` の引数・大きいボタン・メニュー・統合の条件 |
| `frontend/src/pages/inbox/useInboxState.ts` | 558-563 | カルテの保存で送る中身（外すのは `id`・`lead_code`・`prospect_rank`） |
| `frontend/src/pages/inbox/inbox.types.ts` | 73 | `export interface LeadDetail {` |
| `frontend/src/pages/leads/LeadsPage.tsx` | 143・284・349 | 段階の一覧・絞り込み・新規作成 |
| `frontend/src/pages/leads/LeadEditPage.tsx` | 73 | `const LEAD_STATUSES = [...LEAD_STATUS_CODES]` |
| `frontend/src/pages/leads/LeadFormFields.tsx` | 44 | 同上 |
| `frontend/src/lib/apiErrorReason.ts` | 11-41 | 理由コードの表 |

着手時に design §4-1 の最後の `git grep` をもう一度流し、design §4-1 の表と食い違えば止まる。

## 2. 触るファイル（これだけ）

1. 新規 `backend/app/services/customer_conversion.py`: design §4-1 のとおり。
   - `async def is_registration_completed(db, tenant_id: int, lead_id: int) -> bool`（その人の会社に `address_type = 'billing' AND is_default = TRUE` の行がある）
   - `async def promote_lead_if_customer(db, tenant_id: int, lead_id: int | None, *, actor_user_id: int | None, via: str) -> bool`。`lead_id` が None なら何もせず False。中身は `async with db.begin_nested():` で包み、例外は `logger.error` を残して False。leads の行を（PostgreSQL のときだけ）`FOR UPDATE` で押さえてから、3 つを 1 本の SQL で確かめる。そろえば `UPDATE ... SET status = 'existing_customer', updated_at = NOW() WHERE id = :lead_id AND status <> 'existing_customer'`。書けた行があり `actor_user_id` があれば `record_audit_log(action="auto_convert", table_name="leads", record_id=lead_id, new_data={"status": "existing_customer", "via": via})`、None なら `logger.info("[customer_conversion] auto_convert tenant=%s lead=%s via=%s", ...)`。
   - 表はすべて `tenant_table_ref(db, tenant_id, "<表>")`。`existing_customer` を SET する文はこのファイルにだけ書く。
2. 呼ぶ所（design §4-1 の表の 13 行のうち「会社を作るときの住所」は「会社を作る」と同じ 1 回の呼び出しなので、呼ぶ所は 12 か所。どれも commit の前・その道の書き込みの後）: `registration_tokens.py`・`invoices.py`（2 か所）・`integrations.py`（2 か所）・`orders.py`（`data.paid` が true のときだけ）・`companies.py`（作る・直す・統合）・`leads.py`（統合は残る側を読み直す SELECT の前）。会社から lead_id を求める SQL も `tenant_table_ref` で書く。`actor_user_id` はログインした道が `current_user.id`、公開の道（登録フォーム・配送先・請求先・PayPal の戻りと通知）が None。
3. `registration_tokens.py:86-120` の写し 2 か所を `is_registration_completed` の呼び出しに替える（409 の `already_registered`・`not_registered` は今のまま）。このとき lead から tenant を求める必要があれば、`create_token` の今の `tenant_id` を使う。
4. `leads.py`:
   - `create_lead`: `data.status == "existing_customer"` なら 422 `detail="existing_customer_is_automatic"`。
   - `update_lead`: 新しい status が existing_customer で、今の status が existing_customer でなければ同じ 422。今が existing_customer で同じ値を送るのは通す。
   - `convert_lead`（商談に進める）: 今の status が existing_customer なら 409 `detail="already_existing_customer"`（早い 409 の所と、UPDATE の WHERE に `AND status <> 'existing_customer'` の両方）。試験 1 本。
   - `return LeadResponse(...)` の 5 か所すべてで `registration_completed=await is_registration_completed(db, tenant_id, <その lead の id>)` を入れる。
5. `backend/app/schemas/lead.py`: `LeadResponse` に `registration_completed: bool | None = None`。
6. `frontend/src/lib/apiErrorReason.ts`: 表に `existing_customer_is_automatic: "apiError.existingCustomerIsAutomatic",` を 1 行。`ja.json`・`en.json` の `apiError` に同じキーを足す。ja: 「既存顧客には手で変えられません。登録フォーム・会社・支払いの 3 つがそろうと自動で切り替わります。」 en: "You can't set Existing customer by hand. It switches automatically once the registration form, company and payment are all in place." もう 1 行 `already_existing_customer: "apiError.alreadyExistingCustomer",`。ja: 「この人はすでに既存顧客です。画面を読み込み直してください。」 en: "This person is already an existing customer. Please reload the page."
7. `frontend/src/constants/leadStatus.ts`: `export const MANUAL_LEAD_STATUS_CODES = LEAD_STATUS_CODES.filter((c) => c !== "existing_customer");`（型は `LeadStatusCode[]`）。
8. `LeadEditPage.tsx:73`・`LeadFormFields.tsx:44`: 手で選べる一覧を使う。今の値が existing_customer の人は、その値を選択肢の先頭に足して表示だけする（選び直しで他の段階には変えられる。既存顧客に戻す選択肢は今の値のときだけ見える）。
   - `frontend/src/lib/query/useSeededForm.ts`: 戻り値に `base: F` を足す（`seed !== null && ready ? seed.base : empty`）。ほかは変えない。
   - `LeadEditPage.tsx:128` の保存: `status` は `base.status` と違うときだけ送る（design §4-2）。`leadQ.data.status` とは比べない。
9. `LeadsPage.tsx`: 絞り込み（:284）は 7 つのまま。新規作成（:349）は手で選べる一覧。編集の保存（:210）: `status` は `baseForm.status` と違うときだけ送る（design §4-2）。`frontend/src/hooks/useRecordDrawer.ts` に `baseForm` の state を足し、`handleRowClick` で `toForm` の結果を `editForm` と同じに入れ、`closeDrawer` で `emptyForm` に戻し、戻り値に足す（ほかは変えない）。失注の理由（`buildLostReasonUpdatePayload`）は今のまま。
10. `karteLayout.ts:114`: `["existing_customer"]` だけにする。`karteLayout.test.ts` の追客の期待を「商談中と同じ見せ方」に直す。
11. `inbox.types.ts:73` の `LeadDetail` に `registration_completed?: boolean | null;`。
12. `InboxKartePanel.tsx`（design §4-3）:
    - 帯はすべての段階で出す。大きいボタン: lead＝今のまま／negotiating・follow_up_short・follow_up_long・existing_customer＝「請求書を作成」／lost・out_of_scope＝出さない（`return null` をやめ、大きいボタンだけを省く）。
    - `ActionBar` に `registrationCompleted: boolean` を足し、呼ぶ所で `leadDetail.registration_completed === true` を渡す。
    - メニュー: `registrationCompleted` が false なら「登録フォームのリンク」だけ。true なら「配送先を足すリンク」と「請求先を変えるリンク」だけ。`status === "existing_customer"` での出し分けはやめる。
    - 統合の行（:445-455）は変えない。
    - `useInboxState.ts:558-563` のカルテの保存で、送る中身から外す項目に `status` と `registration_completed` を足す（design §4-3・段階を変える専用の呼び出しは変えない）。
13. 試験（design §7）:
    - 新規 `backend/tests/test_customer_conversion.py`（K1 の 6 通り×③の 2 通り・K2 の 7 通り・K3 の 2 本・道ごとに 1 本・手で請求先を入れた人・判定が例外でも入金が残る・公開の道で監査の表に書かない・1 か所だけの試験 (a)(b)・`registration_completed` が 5 か所の返り値で入り、一覧では None）。
    - 新規 `backend/tests/test_customer_conversion_pg.py`（`test_assistant_karte_pg.py` と同じ形）。
    - `backend/tests/test_analytics.py:625,692,770,830,967-973` を、作った後に SQL で `UPDATE leads SET status = 'existing_customer'` する形へ。ほかに API で existing_customer を送る試験があれば同じ。
    - 画面: `karteLayout.test.ts`・帯とメニューの出し分けの試験（`InboxKartePanel.discordButtons.test.tsx` と同じ置き方で新規）・`MANUAL_LEAD_STATUS_CODES` に既存顧客が無いこと・カルテの保存の PATCH に `status`・`registration_completed` が入らないこと（新規 `frontend/src/pages/inbox/useInboxState.blurSave.test.tsx`・`useInboxState.cache.test.tsx` と同じ置き方）・段階を選び直さない保存で PATCH に `status` が入らず、選び直すと入ること。編集画面は直し始めた後に取り直しで段階が existing_customer に変わる場合も入らないこと（新規 `frontend/src/pages/leads/LeadEditPage.statusSave.test.tsx` と、`LeadsPage.temperature.test.tsx` と同じ置き方の新規 `frontend/src/pages/leads/LeadsPage.statusSave.test.tsx`）。

触らない: `migrations/`・`.github/`・`scripts/`・数え方（analytics・dashboard・goals・reports）の式・CSS・連絡先タブ・`karte-visual-gate.spec.ts` の基準画像。

## 3. 想定分岐

| 起きたこと | すること |
|---|---|
| §1 の行が違う（main が進んだ） | 中身が同じ場所を探して合わせる。中身が違えば止まって `NEEDS_DECISION:` |
| grep の道が design §4-1 の表（呼ぶ所 12 か所）より多い・少ない | 止まって `NEEDS_DECISION:`（道の一覧を添える） |
| SQLite の試験で `begin_nested` が使えない・外の取引まで戻る | 止まる（設計は SAVEPOINT だけ戻る前提） |
| 公開の道で `tenant_id` が手元に無い | トークンの `tenant_id`・その道で今使っている値を使う。無ければ止まる |
| `register_customer` の会社作り（:240 の FOR UPDATE）と判定の FOR UPDATE が同じ行を 2 回押さえる | 同じ取引の中なので待たない。そのまま |
| 今ある試験が `status="existing_customer"` を API で送って 422 で落ちる | §2-13 の形で直す。試験の目的（数え方）は変えない |
| 画面試験（Karte Visual Gate）の基準画像が帯の変化で落ちる | 想定外。止まって報告（基準画像は Opus が決める） |
| eslint・i18n の見張りに止められる | 直し方が設計の範囲で決まらなければ止まる。見張りを外さない |

## 4. 終わり方

1. `cd backend && pytest -q tests/test_customer_conversion.py tests/test_analytics.py tests/test_api_error_reason_sync.py`・`cd frontend && npm run lint && npx tsc --noEmit && npx vitest run src/pages/inbox src/pages/leads src/constants src/lib src/hooks` を流し、生の出力をそのまま報告に貼る。
2. commit（1 つか、backend と frontend の 2 つ）→ `git push -u origin HEAD`。
3. PR は作らない（Opus が作る）。最後の行に `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。
