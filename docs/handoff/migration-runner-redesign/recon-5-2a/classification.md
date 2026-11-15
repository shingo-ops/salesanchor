---
mode: handoff
---

# 5-2 の分け表 — ひな形に全件を流した後も本番 003 と違う 147 件を、足す・外す・本番の癖・差ではない に分ける

Opus の設計判断（PO の言葉ではない）。§5-6（`docs/handoff/migration-runner-redesign/design.md`）の「1A で最初にすること」の分け方の表。
材料は前調査 5-2a の結果（`docs/handoff/migration-runner-redesign/recon-5-2a/q1-run.md`・`docs/handoff/migration-runner-redesign/recon-5-2a/q2-diff.md`）と、本番 5 社の構造だけの読み取り（`docs/handoff/migration-runner-redesign/recon-5-2a/prod-reads/`）。
1行ごとの分けは `docs/handoff/migration-runner-redesign/recon-5-2a/classification.tsv`（147行＋見出し1行。列＝分け・種類・分け方・名前）。分けた台本は `docs/handoff/migration-runner-redesign/recon-5-2a/prod-reads/classify.py.txt`（読むだけ・DBにつながない）。

## 1. 何を分けたか

- 対象: `q2-diff.md` の組 (A)「本番 003 対 ひな形に登録全件を流した後」の差の全件 147 件（`docs/handoff/migration-runner-redesign/recon-5-2a/q2-diff.md:306-456`。内訳 本番だけ 102・ひな形だけ 26・中身が違う 19、同 `:458-470`）。
- 対象にしない物: 組 (B) で全件を流すと有る・本番と同じになる物（印1 有る 589・印3 本番と同じ 53、同 `:1948-1958`）。手順（登録の移行）が作るので、ひな形を「流した後の形」に合わせれば揃う（§5-6 の CI 検査で守る）。
- 分けの基準（§5-6「ひな形にだけ余計な物を0」「003 の癖は写さない」に従う）:
  - 本番の 5 社（001・003・004・005・006）全部にあり、コードが使う物 → ひな形に足す（A）。
  - 本番の 5 社のどれにも無い物 → ひな形から外す（B）。
  - 本番の一部の会社だけにある物、使っていない機能の物、名前だけ違う物 → 本番の癖として写さない（C）。
  - 意味が同じで書き方だけ違う物 → 差ではない（D）。
  - 006（ひな形で作った会社）と同じで、動きが変わらない物 → ひな形のまま（E）。

## 2. 分けごとの件数（`classification.tsv` を数えた値。未分類 0）

| 分け | 件数 | 中身 | 根拠 |
|---|---|---|---|
| A1 ひな形に足す | 8 | 注文の表の 8 列（`invoice_id`・`currency`・`shipping_carrier`・`shipping_fee`・`tracking_number`・`shipped_at`・`delivered_at`・`shipping_country`） | 本番 5 社全部に同じ型・既定値である（`prod-reads/prod-cols.txt`）。コードが読む: `backend/app/routers/orders.py:251-254`・`backend/app/tasks/reports.py:112`。作る手順 `migrations/005_add_phase2_tenant_tables.sql:157-164` は登録に無い |
| A2 ひな形に足す | 11 | 予定の表示設定の表 `calendar_owner_settings`（5 列・主キー・索引・人への外部キー・`share_mode` の制約・表の印） | 本番 5 社全部にある（`prod-reads/prod-5co.txt`）。`backend/app/routers/calendar.py` が使い、`backend/app/main.py:732` で道が登録されている。作る手順 `migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql` は `scripts/run_all_migrations.sh` に行が無い |
| A3 ひな形に足す・直す | 8 | `calendar_events.category` 列（varchar(50)・NOT NULL・既定 'meeting'）とその制約、`close_reasons_type_check`、`leads_initiative_check`、`idx_bots_status`、`close_reasons.is_active` を boolean 既定 true に・`close_reasons.created_at` を NOT NULL に・`deal_close_reasons.is_primary` を boolean 既定 false に | 型と制約は本番 5 社全部が同じ（`prod-reads/prod-cols.txt`・`prod-reads/prod-5co.txt`）。`idx_bots_status` は 001・003・004・005 にあり 006 に無い（索引なので足しても読み書きの結果は変わらない） |
| B1 ひな形から外す | 17 | 会社ごとの仕入先の表 `suppliers`（13 列・主キー・索引・方針・表の印・連番） | 本番 5 社のどれにも無い。仕入先は `public.suppliers` 1 つにまとめると決まっている（`docs/handoff/supplier-ssot-phase2/design.md:36`・`:156`「PO 決定で撤回」）。会社ごとの表を消す手順は登録の外で、手で流した（`migrations/20260918_030000_supplier_ssot_phase2.sql:24`・`:34`）。そのため登録全件を流しても使い捨て側には残る |
| B2 ひな形から外す | 5 | 外部キー 5 本（`deal_close_reasons_lead_id_fkey`・`quotes_lead_id_fkey`・`purchase_order_items_order_item_id_fkey`・`bots_owner_staff_id_fkey`・`tenant_meta_config_connected_by_staff_id_fkey`） | 本番 5 社のどれにも無い（`prod-reads/prod-5co.txt` に行が無い）。ひな形にだけあると、新しい会社でだけ削除が止まる等、今の会社と動きが変わる。本番に足すかは別の話として扱う（この段では触らない） |
| C1 本番の癖（写さない） | 57 | 使っていない機能の 4 表（`badge_definitions`・`buddy_pairs`・`buddy_feedbacks`・`user_badges`）と `staff_ui_preferences.show_buddy_menu` | 本番 5 社全部にあるが、`backend/app/main.py` にこの機能の道の登録が無い（`buddy`・`badge` で検索して 0 件）。消す手順 `migrations/079_remove_buddy_badges.sql` は登録に無い。下の §4 の (3) |
| C2 本番の癖（写さない） | 19 | 001・003 だけにある索引 13・制約 2・連番 3 と、`leads.lead_code` の既定値 | 001・003 にだけある（`docs/handoff/migration-runner-redesign/recon-5-0-opus-prod.md` §3・§5、`prod-reads/prod-5co.txt`、`prod-reads/prod-cols.txt`）。`lead_code` はコードが作る（`backend/app/routers/leads.py:457-461`） |
| C3 本番の癖（直さない） | 6 | 外部キーの名前だけ違う 3 組（会社→リード・連絡先→リード・商品→仕入先） | 001〜005 は古い名前、006 はひな形と同じ名前（`prod-reads/prod-5co.txt`・`prod-reads/prod-con2.txt`）。どの列を指すかは同じ |
| D1 差ではない | 12 | 方針の条件が `current_tenant_id()` か `current_setting('app.tenant_id', true)::integer` か | `migrations/014_create_current_tenant_id_function.sql:5`（同じ値を返す包み） |
| D2 差ではない | 1 | 発行元の電話番号の制約 | 書き出しのファイルでは記号 `\` が 2 つに見えたが、本番 5 社を直接読むと全部 1 つ（`prod-reads/prod-con2.txt`: `double_bs=False`・`single_bs=True`） |
| E ひな形のまま | 3 | `companies.tenant_id`・`contacts.tenant_id` の既定値、`trg_lead_playbook_updated_at` | 006（ひな形で作った会社）と同じ（`prod-reads/prod-cols.txt`・`prod-reads/prod-5co.txt`） |
| 合計 | 147 | | |

## 3. 外部キーの指し先の置き場所

- 5-2a の書き出し（`docs/handoff/migration-runner-redesign/recon-5-2a/q1-run.md:103`）は `pg_get_constraintdef` の結果の `tenant_003` を `X` に置き換えている。会社の中の表を指す外部キーは `REFERENCES X.<表>`（46 本）、それ以外は置き場所なし（25 本。`users` 13・`products` 5・`suppliers` 2・`customer_statuses` 2・`countries`・`permissions`・`prefectures` 各1）で出る（`q1-shape/constraints.tsv` を数えた値）。そのため置き場所の違いは「`X.` が付くか付かないか」として比べの対象に入っている。例: 仕入先を指す 2 本は、ひな形の直後は `X.suppliers`、全件を流した後と本番 003 は置き場所なし（`q2-diff.md:984`・`:988`・`:1766`）。
- 本番 003 の外部キー全部を置き場所つきで読んだ（`prod-reads/fk003.txt`。会社の中 51・共用 24）。共用を指す 24 本と、使い捨て側の置き場所なしの 25 本を、表と指す表の組で1本ずつ比べた（`prod-reads/fk-public-compare.txt`）。違いは 3 本で、どれも分け済み: 使い捨てだけの `bots → users`・`tenant_meta_config → users`（B2 の `bots_owner_staff_id_fkey`・`tenant_meta_config_connected_by_staff_id_fkey`）、本番だけの `calendar_owner_settings → users`（A2）。
- 本番 5 社で共用の表を指す外部キーは 128 本（003 は 24 本。`prod-reads/fk-public.txt`）。発注と商品の仕入先は 5 社とも `public.suppliers` を指す。
- ひな形 `backend/app/services/tenant.py` の `_TENANT_TABLES_SQL` は、仕入先を `{schema}.suppliers` で指す（2 か所）。B1 で会社ごとの仕入先の表を外すと、この 2 か所は `public.suppliers` に直す必要がある。
- **まだ確かめていないこと**: 使い捨て側の「置き場所なし＝共用（public）」は、書き出したときの検索の順（search_path）に頼る。`q1-run.md` にその記録は無い（`search_path` で検索して 0 件）。5-2 の実装カードでは、置き場所を必ず付けて書き出し（指す表の schema 名を別の列で取る）、本番と比べる。§5-6 の CI 検査（K5-2）も同じ取り方にする。

## 4. 分けの外で分かったこと

1. run_py の 12 本は、試験の前準備が入れた会社の行（id 999・schema 無し）で落ちた（`docs/handoff/migration-runner-redesign/recon-5-2a/q1-run.md:358-369`）。台本は会社を id の順に1社ずつ別の取引で流す（例 `scripts/migrate_adr021_sprint2_financials.py:101-127`）ので、003 の分は先に確定している。実装カードの CI 検査では、schema の無い会社の行を前準備で入れないことを書く。
2. run_sql の 3 本は使い捨ての DB に前提が無くて落ちた（`public.auth_events` が無い 2 本・`jarvis_db` が無い 1 本。同 `:370-372`）。会社の形には関わらない。CI 検査での扱いは実装カードで決める。
3. 使っていない機能の 4 表を本番から消すかは、この段では決めない（データの削除になるため、別のテーマとして PO に聞く）。
4. `backend/app/routers/purchase_orders.py:58-64` の説明は「会社ごとの仕入先へ写す」と書くが、本番の発注は `public.suppliers` を指す（`prod-reads/fk-public.txt`）。説明が古い。動き（実際にどちらの表に書くか）はまだ確かめていない。この段では直さない。

## 5. 次

この分けと §3 の比べを使って、5-2 の実装カード（ひな形の直書きを直す・CI 検査を足す・ひな形を直接使う 5 か所を揃える）を書く。実装は PO の明示の実装承認の後。
