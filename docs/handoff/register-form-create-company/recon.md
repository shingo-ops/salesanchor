# recon: 受信箱の登録フォームが会社を作らない件

- 調べた日: 2026-11-22（JST）。土台: origin/main 2560f963f。本番の数は reader 鍵の道（ADR-1024）で読んだ。
- 既存 ADR の検索: `git grep -n -i "登録フォーム\|registration" -- docs/adr/` と `docs/adr/FEATURE-INDEX.md` の会社の行 → ADR-097（顧客登録フォーム）・ADR-126（請求先名）・ADR-127（登録リンクの段階）。新しい ADR は不要（ADR-097 §3 がすでに「自動生成」と決めている）。

## 1. 決まり（ADR）

- `docs/adr/ADR-097-sa-customer-registration-form.md:41` 「既存リード情報＋顧客入力B/D ＝ 同期した顧客マスタを自動生成」。
- 同 §6（61-66 行）: 会社はリードの子。会社を作る道は受信箱から送る登録フォームでお客様が登録する道だけ。画面の「新規登録」は撤去（#5667 で本番済み）。

## 2. 今の作り（事実）

- `backend/app/routers/registration_tokens.py:239-249`: 送信を受けると `SELECT id, billing_display_name FROM companies WHERE lead_id = :lead_id` を読み、無ければ `404 company_not_found` で止まる。会社を作る行は無い。
- 会社を作る SQL は main 全体で 2 か所だけ（`git grep -n -i "INSERT INTO companies" -- backend/app`）:
  - `backend/app/routers/companies.py:409`（`POST /companies`。画面の入口は #5667 で撤去済み。フロントから呼ぶ所は 0 件: `git grep -n -E "post\(\s*[\"'\`]/companies[\"'\`]" -- frontend/src` が 0 行）。
  - `backend/app/routers/integrations.py:653`（PayPal の試し用）。
- リードの商談化 `backend/app/routers/leads.py:794-860` は leads を更新するだけで会社を作らない。
- 会社の表（`backend/app/services/tenant.py:200-230`）: 必ず入れる欄は `company_code`（VARCHAR(20)・テナント内で重複不可）・`lead_id`・`name`。`status` は既定 `'active'`。`lead_id` に重複を止める決まりは無い（233 行は索引だけ）。
- 会社の番号の付け方の前例: `backend/app/routers/companies.py:397` 仮に `CO-PEND-<8桁>` で入れ、455-459 行で `CO-{id:05d}` に直す。
- フォームの画面 `frontend/src/pages/register/RegisterPage.tsx:147-150` は請求先名（billing_display_name）が空だと送らない。送る本文は 211-221 行。
- フォームを開く時の読み取り `backend/app/routers/registration_tokens.py:189-197` は会社が無ければ会社名を空で返す（画面は 289 行で会社名の行を出さないだけ）。
- この送信の試験は backend に無い（`git grep -l -E "register_customer|company_not_found" -- backend/tests` が 0 件。`backend/tests/test_viewer_isolation.py` は道の一覧だけ）。

## 3. 本番の数（読むだけ・2026-11-22 06:58 JST ごろ）

- 会社: tenant_004 に 51 件（すべて lead_id あり・最後の作成 2026-06-08）、tenant_001 に 1 件、003・005・006 は 0 件。
- tenant_004 のリードは 56 件。会社の無いリードは 5 件（id 35・36・45・46・148）。5 件とも `company_name` が空で `customer_name` は入っている。
- 会社名の出どころ: 会社 51 件のうち 50 件で `companies.name = leads.company_name = leads.customer_name`。違う 1 件は試し用（CANARY_TEST）。
- 登録リンク: `public.registration_tokens` に register 4 件（使用 1 件）・add_address 1 件。最後の発行は 2026-06-19。

## 4. 未確認

- 本番のフォームを実際に送る試しはしていない（本番のデータを書くため）。
