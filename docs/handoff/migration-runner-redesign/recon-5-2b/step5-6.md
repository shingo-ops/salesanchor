---
mode: handoff
---

# 5-2 実装カード（第2版）手順1〜7 の途中結果 — 手順6 の途中で設計の食い違い 2 件が出て止まった

本報告はカード 5-2 の実行結果である（実装役。手順 8〜10 は未実施）。

- 止まった理由（要約）: ひな形を「登録を全件流した後の形」に揃えると、既存の設計・試験 2 件と食い違った。カードの「設計とこのカードが食い違ったら記録して止まる」に従い、決めずに止まる。下の「4. 止まった理由」。
- 作業の枝: `release/migration-template-5-2`（`origin/main` から。手順2 の `git rev-parse HEAD` と `git rev-parse origin/main` は同じ `9f42fe9b16789d5c7b62fe9adce2f82fca51615f`）。
- この枝の中身は **PR にしていない**（Draft PR も作っていない。マージしない）。

## 手順2〜4 の記録

- 作業場所: `bash scripts/new-worktree.sh release/migration-template-5-2`。
- 手順3 の `./scripts/dev/executor-preflight.sh` の出力（全文）:

```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。
       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)
[2/3] gh auth = shingo-cc
  [warn] gh の active account が shingo-cc でない。gh auth switch で切り替え試行...
  [FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。
[3/3] git config user.name = shingo-cc
  [OK]   git user.name を shingo-cc に設定
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)
```

（クラウドの実行環境では前の調べと同じ結果。記録して続けた。）

- 手順4: PostgreSQL は `postgres (PostgreSQL) 16.15`（`/usr/lib/postgresql/16`）。実行者が root のため `initdb` と `pg_ctl` は OS の `postgres` 利用者で流し、`localhost:55432` で受け付けた。Python は `python3.12 -m venv /tmp/recon/venv` → `pip install -r requirements.txt -r requirements-dev.txt` → `pip check` が `No broken requirements found.`。

## 手順5 最初の確かめ（直す前）

使い捨ての DB（`r52_b`）に、直す前のひな形（`create_tenant_schema`）で会社 3 を作り、登録 405 本を全件流した後の外部キーを、指す表の置き場所つき（`pg_constraint.confrelid` → `pg_class` → `pg_namespace`）で取り、本番 003（`recon-5-2a/prod-reads/fk003.txt`）と「表・外部キーの名前・指す表・指す表の置き場所」の組で 1 本ずつ比べた。

| | 本番 003 | 直す前のひな形＋全件 |
|---|---|---|
| 外部キーの本数 | 75 | 76 |
| 会社の中を指す | 51 | 51 |
| 共用（public）を指す | 24 | 25 |

違いの全件（15 行。カードの 12 組と一致。ほかの違いは 0 件）:

| 置き場所 | 本番だけ | ひな形（流した後）だけ | 分け |
|---|---|---|---|
| 共用 | `calendar_owner_settings.fk_calendar_owner_settings_staff_id_user` → `public.users` | | A2 |
| 共用 | | `bots.bots_owner_staff_id_fkey` → `public.users` | B2 |
| 共用 | | `tenant_meta_config.tenant_meta_config_connected_by_staff_id_fkey` → `public.users` | B2 |
| 会社の中 | `orders.fk_orders_invoice` → `invoices` | | C2 |
| 会社の中 | `buddy_feedbacks.buddy_feedbacks_pair_id_fkey` → `buddy_pairs` | | C1 |
| 会社の中 | `user_badges.user_badges_badge_id_fkey` → `badge_definitions` | | C1 |
| 会社の中 | | `deal_close_reasons.deal_close_reasons_lead_id_fkey` → `leads` | B2 |
| 会社の中 | | `quotes.quotes_lead_id_fkey` → `leads` | B2 |
| 会社の中 | | `purchase_order_items.purchase_order_items_order_item_id_fkey` → `order_items` | B2 |
| 会社の中（名前だけ違う） | `companies.companies_lead_id_fkey` → `leads` | `companies.fk_companies_lead` → `leads` | C3 |
| 会社の中（名前だけ違う） | `contacts.contacts_lead_id_fkey` → `leads` | `contacts.fk_contacts_lead` → `leads` | C3 |
| 共用（名前だけ違う） | `products.products_supplier_default_id_fkey` → `public.suppliers` | `products.fk_products_supplier_default` → `{schema}.suppliers` | C3（直す前は会社の中の表を指していた。B1 で `public.suppliers` に直す） |

合否: **合格**（違いはカードが許した名前だけ。止まる条件に当たらない）。

## 手順6 ひな形を直した結果

### 6-1 「登録の手順が作る物」を取り直した結果（カードの 645 件との照合）

使い捨ての DB で同じ比べを取り直した（直す前のひな形、登録 405 本）。全件は `step6-diff.tsv`（696 行。種類・名前・分け・作った/変えた登録の移行のファイル）。

| 種類 | 流した後だけ（a） | 流す前だけ（b） | 中身が違う（c） |
|---|---|---|---|
| 表 | 25 | 0 | 0 |
| 列 | 352 | 1 | 5 |
| 索引 | 103 | 0 | 0 |
| 制約 | 85 | 3 | 3 |
| 連番 | 25 | 0 | 0 |
| 方針 | 20 | 0 | 0 |
| トリガ | 11 | 0 | 0 |
| 関数 | 10 | 0 | 1 |
| 権限（表・連番の `relacl`） | 51 | 0 | 0 |
| ビュー | 1 | 0 | 0 |
| 合計 | 683 | 4 | 9 |

- カードの数との違い（記録して続けた）: カードは「流した後だけ 632（表 26・列 352・索引 103・制約 85・連番 25・方針 20・トリガ 11・関数 10）・流す前だけ 4・中身違い 9」。今回は表が 25（カードは 26）。権限 51 とビュー 1 は、第2版の「権限」を比べる物に入れたため、この数え方で初めて出た。登録の本数は 405（カードの前提は 404。`origin/main` に 1 本増えた）。流す前だけ 4・中身違い 9 は一致。
- 流した結果: 405 本中、落ちたのは 3 本だけ。`migrations/072_add_retention_indexes.sql`・`migrations/20261101_130000_add_new_device_approval.sql`（`public.auth_events` が無い）と `migrations/20260605_030000_create_salesanchor_app_role.sql`（本番の DB 名 `jarvis_db` が無い）。run_py の 26 本は、schema の無い会社の行（id 999）を入れない前準備にしたので全部通った（前は 12 本落ちた）。

(b) 流す前だけ（ひな形から外した）: 列 `leads.converted_deal_id`、制約 `invoice_items_product_id_fkey`・`purchase_order_items_product_id_fkey`・`quote_items_product_id_fkey`（登録の移行が付け替える）。

(c) 中身が違う（流した後の中身に直した）: `deal_close_reasons.lead_id`・`invoices.company_id`・`orders.company_id`・`quotes.company_id`・`quotes.lead_id` を NOT NULL に、`goals_kpi_type_check` に `won_count`・`gross_profit` を足す、`products.fk_products_supplier_default` と `purchase_orders.purchase_orders_supplier_id_fkey` を `public.suppliers` へ（B1 と同じ）。`trg_set_updated_at()` は本文の空白だけの違いなので、検査は空白をまとめて比べる（ひな形は変えない）。

(a) の直し方（`backend/app/services/tenant.py` の `_TENANT_TABLES_SQL` の末尾に「段5 5-2」の節）: 新しい表 25 を依存の順に `CREATE TABLE IF NOT EXISTS`（主キー・制約・索引つき）、既存の表に足す列 29 を `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`、既存の表に足す索引 10、別名の外部キー 7 を名前の有無を確かめる DO ブロック、更新時刻の関数 10 とトリガ 11、ビュー `v_company_stats` 1。RLS の印と方針は `_RLS_ENABLE_SQL`・`_RLS_POLICY_SQL` の末尾に足した。

### 6-2 分け表 147 行との対応（A・B）

行ごとの対応表は `step6-map-147.tsv`（分け表の全 147 行と、直した `backend/app/services/tenant.py` の行番号）。件数:

| 分け | 件数 | 直した | 確かめ |
|---|---|---|---|
| A1 | 8 | 注文の 8 列（`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`） | 本番 003 との比べで消えた |
| A2 | 11 | `calendar_owner_settings`（表・主キー・索引・人への外部キー・`share_mode` の制約）。RLS は付けず方針も足さない（本番 003 の `table_flags.tsv` どおり） | 消えた |
| A3 | 8 | `calendar_events.category` と制約、`close_reasons_type_check`、`leads_initiative_check`、`idx_bots_status`、`close_reasons.is_active`（boolean・既定 true）・`created_at`（NOT NULL）、`deal_close_reasons.is_primary`（boolean・既定 false） | 消えた |
| B1 | 17 | 会社ごとの `suppliers`（表・索引・方針・RLS の印・連番）を外し、`products`・`purchase_orders` の外部キーを `public.suppliers` に | 消えた |
| B2 | 5 | 外部キー 5 本を外した。`bots`・`deal_close_reasons`・`quotes`・`tenant_meta_config`・`purchase_order_items` は別名の外部キー（登録の移行が付ける名前）を名前の有無を確かめる DO ブロックで付ける | 消えた |
| C1・C2・C3・D1・D2・E | 98 | ひな形を変えない | 残る（分け表どおり） |

確かめ方: 直したひな形で作った会社に登録全件を流した後の形を、本番 003 の形と `recon-5-2a` の台本で比べ、分け表の 147 件のうち A・B の 49 件が消え、C・D・E の 98 件が残ることを見た。分け表に無い違いが 6 件ある（新しい表 6 つの会社分離の方針）。本番は `public.current_tenant_id()`、ひな形は `current_setting('app.tenant_id', true)::integer` で書く（会社を作る時点で public に包み関数が無い環境があるため。分け表 D1 と同じ「同じ値を返す書き方の違い」）。CI の検査はこの 2 つを同じ物として比べる。

### 6-3 形の差 0（K5-2）

直したひな形で会社 3 を作り、登録 405 本を全件流した後の形との差は **0 件**（表・列・型・既定値・NOT NULL・索引・制約・外部キーの指す表の置き場所・トリガ・RLS の印・方針・連番・関数・ビュー・権限）。検査の台本は `scripts/check_tenant_template_shape.py`。

## 手順7 ひな形を直接使う所（確かめだけ）

- `git grep -n "CREATE TABLE IF NOT EXISTS {schema" -- scripts/setup_review_tenant.py scripts/setup_tenant.py` は 0 件（終わりの番号 1）。2 本は `backend/app/services/tenant.py` の同じ文字列を読み込むだけで、手順6 の直しはそのまま届く。差し替えていない。
- `setup_tenant.py` を使う `.github/workflows/schema-check.yml`（テナントスキーマ整合性チェック）: 直したひな形が `public.suppliers` を指すため、この流れの最小の public に表が無いと会社が作れなくなる。`public.products` の前例（ADR-090）に倣い、`public.suppliers`（`id` だけ）を 1 つ足した（**カードに無い変更**。要らなければ外してよい。足さないと次に `migrations/` を触る PR で schema-check が落ちる）。足した状態で、同じ手順（最小の public → 会社 4 つ → `sync_tenant_schema.py --dry-run`）を使い捨ての DB で再現し、会社 4 つが作れて差分なしだった。
- ひな形の文字列を読む試験 27 ファイルを使い捨ての DB で流した（CI の `test.yml` と同じ役割・権限）。直したひな形で落ちた物と対処:
  - `tests/test_lead_merge_pg.py`: `quotes.company_id` が NOT NULL になったため、見積を 1 行入れる箇所に会社を 1 つ足した（**カードに無い変更**。同じ形の NOT NULL は本番 5 社の形）。
  - `tests/test_channel_type_control.py::test_create_tenant_schema_does_not_copy_channel_masters` と `tests/ops/test_ai_cloud_views.py::test_t10_classification_covers_real_shaped_tables` の 2 件が落ちる。**直していない**。下の「4. 止まった理由」。元の `origin/main` ではどちらも通る。
  - ほか 2 件（`test_tenant_issuer_tables_pg.py`・`test_assistant_karte_pg.py`）は並列実行のデッドロックで落ち、1 本ずつ流すと通る（直したひな形とは無関係）。

## 4. 止まった理由（設計の食い違い 2 件）

1. **`channel_masters`（設計 K6 と食い違う）**: `docs/handoff/channel-master-shared/design.md` の K6 は「会社の作成後、`tenant_NNN.channel_masters` が作られず、一覧に共用 6 つが出る」。試験 `tests/test_channel_type_control.py::test_create_tenant_schema_does_not_copy_channel_masters` がそれを守る。一方、登録の `migrations/20260611_100000_create_channel_masters.sql`（登録に有る）は全会社に `channel_masters` を作るので、「全件を流した後」のひな形に `channel_masters`（表 1・列 7・索引・制約・方針・RLS の印・連番）を入れると K6 と試験に反する。入れないと、形の差が 0 にならず、検査の「許す一覧は 0 件で始める」にも反する（許す一覧に入れたくなったので止まる）。物の名前・作った移行・本番 003 に有るか: `channel_masters`・`migrations/20260611_100000_create_channel_masters.sql`・本番 003 に有る（分け表の対象外の「有る」に入っている）。
2. **`calendar_events` 等の新しい表の列に分類が無い**: `tests/ops/test_ai_cloud_views.py::test_t10_classification_covers_real_shaped_tables` は、ひな形で作った会社の全列に AI 用ビューの分類があることを確かめる。ひな形に `calendar_events` を足すと `calendar_events.meet_url` に分類が無いと落ちる（分類は `migrations/20261024_100300_create_ai_cloud_views.sql`）。直すには `migrations/` の分類か試験を変える必要があり、このカードは `migrations/` を足さない。

問い（NEEDS_DECISION）: 上の 2 件をどう扱うか。
- (1) `channel_masters` は K6 を守って「許す一覧」に名前と理由つきで入れる（検査が `channel_masters` の差を許す。カードの「許す一覧は 0 件」を 1 件にする）か、K6 を改めてひな形に入れるか、登録の移行側（`migrations/20260611_100000_create_channel_masters.sql` が新しい会社にも表を作る動き）を別のテーマで直すか。
- (2) `test_t10` の分類漏れ（`calendar_events.meet_url` など）は、別のカードで分類を足してから入れるか、この PR で試験を調整するか。

## 未実施（止まったため）

手順 8（`.github/workflows/migration-test.yml` の新しい job）・手順 9（検査の台本の試験）・手順 10（Draft PR）。`scripts/check_tenant_template_shape.py`（前準備・形を取る・差を出す・登録を全件流す。許す一覧と外す一覧の置き場所つき）は下書きとして置いた。CI には入れていない。
