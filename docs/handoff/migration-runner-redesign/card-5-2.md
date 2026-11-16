---
mode: handoff
---
# 実装カード：会社のひな形を1つにする（段5 5-2・1A）— ひな形の直書きを分け表どおりに直し、CI に形の差0の検査を足す（Sonnet・クラウド）

状態: **第2版（2026-11-16）。PO の実装承認（2026-11-16「1」）は受領済み。第2版の直しは承認の範囲（1A: 足りない表と列を書き足す）の中。**

第2版の直し（Opus の設計判断・PO の言葉ではない）: 第1版は「手順6の後に形の差0」としていたが、分け表の 147 件だけでは足りなかった。登録の手順が作る 645 件をひな形に足すことが抜けていた（設計の入れ忘れ）。手順6に足す作業を、手順8に B1・B2 の「許す一覧」を足した。1つの PR で全部入れる（検査を必須にしないまま分けると、検査が使われなくなるため）。

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は Draft で作らせる。実装役はマージしない。マージは、PO の明示の実装承認（このカードを流す前に受ける）の後、審査役の APPROVE・CI 緑・ADR-1003 の委任 GO の条件がそろってから Opus が行う。この PR は migrations/・deploy.yml・本番の台本を変えないので ADR-136 の危険 PR には当たらない（設計 §5-3 の 5-2 の GO は「案は PO の確認」） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（ひな形を分け表どおりに直す＋形の差0の CI 検査。本番は触らない。migrations/ は足さない） | ○ |
| 5 | ブランチの起点を明示（`origin/main` から新しく `release/migration-template-5-2`） | ○ |
| 6 | 書式は実例で示す（形の取り方は `card-5-0b.md`「形の取り方」に、指す表の置き場所の列を足した物） | ○ |
| 7 | 合格基準を出力まで縛る | ○（各手順の「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（分け表の数・本番の外部キーの数を渡す） | ○ |
| 12 | 停止は不可逆なもの・設計の前提が崩れたときだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write で書く・止められたら言い換えない | ○ |

## 目的
設計 `docs/handoff/migration-runner-redesign/design.md` §5-6（1A は PO 2026-11-15「1」で決定）を実装する。新しい会社をひな形で作り、登録全件を流しても形が変わらない（K5-2）ようにし、ひな形にだけ余計な物を0にする。今ある5社（本番）は変わらない（K5-3。このカードは本番に何も流さない）。

## 前提
- 先に全部読む: `design.md` §5-6・§5-1・§5-9 と受け入れ基準 K5-2・K5-2b・K5-2c・K5-3、`recon-5-2a/classification.md`（分け表）と `classification.tsv`（147 行）、`recon-5-2a/prod-reads/fk003.txt`・`fk-public-compare.txt`、`card-5-0b.md`「形の取り方」「比べ方」。設計とこのカードが食い違ったら設計を正とし、記録して止まる（`NEEDS_DECISION:`）。
- ひな形の本体は `backend/app/services/tenant.py` の `_TENANT_TABLES_SQL`（:194 から）・`_RLS_ENABLE_SQL`・`_RLS_POLICY_SQL`。直書きの SQL のまま直す（1A。ファイルに書き出す形 1B にはしない）。
- データ（役割・権限・会社の設定の行）はひな形に入れない。今の入れ方（`seed_system_roles` など）は変えない。
- 本番のサーバーと DB には一切つながない。SQL を流すのは、使い捨ての PostgreSQL 16（localhost:55432）に対する pytest の中だけ（`scripts/agent-hooks/cloud/rules.md`）。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 5-2 の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` → `bash scripts/new-worktree.sh release/migration-template-5-2` → `git rev-parse HEAD`・`git rev-parse origin/main` を記録。reset・rebase・force・merge・pull は使わない。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する。
4. PostgreSQL 16 と Python 3.12 の venv を `card-5-0b.md` の手順4・4b と同じ命令で用意する（無ければ `BLOCKED:`）。
5. **最初の確かめ（直す前）**: 今のひな形で使い捨て DB に会社（id 3）を作り、登録全件を流した後の形を、外部キーの指す表の置き場所（schema 名）を別の列にして取る（`pg_constraint.confrelid` → `pg_class` → `pg_namespace`）。会社の中を指す本数と共用（public）を指す本数、共用を指す外部キーの「表 → 指す表」の一覧を出し、`recon-5-2a/prod-reads/fk003.txt`（会社の中 51・共用 24）と1本ずつ比べる。比べるのは本数ではなく「表・外部キーの名前・指す表・指す表の置き場所」の組で1本ずつ（本数だけだと、増えた分と減った分が打ち消し合って違いが見えない。会社の中を指す本数は本番も今のひな形も 51 で同じだが、中身は違う）。合否の線: 違いが次の12組の名前だけであること。共用を指す物（`fk-public-compare.txt`）: 今のひな形だけ `bots_owner_staff_id_fkey`・`tenant_meta_config_connected_by_staff_id_fkey`（B2）、本番だけ `fk_calendar_owner_settings_staff_id_user`（A2）。会社の中を指す物: 本番だけ `fk_orders_invoice`（C2）・`buddy_feedbacks_pair_id_fkey`・`user_badges_badge_id_fkey`（C1）、今のひな形だけ `deal_close_reasons_lead_id_fkey`・`quotes_lead_id_fkey`・`purchase_order_items_order_item_id_fkey`（B2）、名前だけ違う `companies_lead_id_fkey`／`fk_companies_lead` と `contacts_lead_id_fkey`／`fk_contacts_lead`（C3・会社の中。本番の名前／今のひな形の名前）。名前だけ違う共用を指す物: `products_supplier_default_id_fkey`／`fk_products_supplier_default`（C3・`public.suppliers` を指す。`classification.tsv:107-108`）。根拠は審査の生出力 `fk_internal_compare` と `classification.tsv`。ほかの違いがあれば一覧を書いて `NEEDS_DECISION:` で止まる。
6. **ひな形を直す**（分け表 `classification.tsv` の分けごと。行ごとに、tsv の行と直した `backend/app/services/tenant.py` の行番号を対で表にする）:
   - A1 注文の 8 列、A2 `calendar_owner_settings`（表・主キー・索引・`users` への外部キー・`share_mode` の制約。**RLS は本番 003 と同じく切ったままにし、方針は足さない**。本番 003 は `recon-5-0b/prod003/table_flags.tsv:9` で RLS の印が False・False、分け表にも方針の行は無い。RLS を付けるかは別のテーマとして Opus が PO に上げる）、A3 の 8 件を足す・直す。型・既定値・NOT NULL・制約の中身は `recon-5-0b/prod003/` の行と `prod-reads/prod-cols.txt` に合わせる（書き写す元の行を表に書く）。
   - B1 会社ごとの `suppliers`（表・索引・方針・RLS の印・連番）を外し、`{schema}.suppliers` を指す 2 本の外部キー（`backend/app/services/tenant.py:1013`・`:1021` 付近）を `public.suppliers` に直す。
   - B2 の外部キー 5 本を外す。
   - C1・C2・C3・D・E はひな形を変えない。
   - **(第2版で追加) 登録の手順が作る物を全部ひな形に足す**: 第1回の実行（2026-11-16、`NEEDS_DECISION` で停止）で、今のひな形の会社に登録全件を流すと、流した後だけにある物が 632 件（表 26・列 352・索引 103・制約 85・連番 25・方針 20・トリガ 11・関数 10）、流す前だけ 4 件、中身が違う 9 件出た。分け表の 147 件は「本番 003 と、ひな形＋登録全件」の比べなので、この 645 件は分け表に入っていない（`classification.md` §1「対象にしない物」の印1・印3。手順が作るので、ひな形を流した後の形に合わせる物）。これを全部ひな形に足す・直す（`calendar_events` のように表ごと無い物は表ごと足す）。書き写す元は、使い捨て DB で登録全件を流した後のその会社の形（`pg_dump --schema-only` の会社のスキーマ分など）。会社の番号・スキーマ名は `{schema}`・`{tenant_id}` に置き換える。ひな形はファイルに書き出す形にせず、直書きの SQL のまま足す（1A）。足した物は種類ごとの件数と、作った登録の移行のファイル名を表にする。ただし A・B の分けと食い違う物（例: B1・B2 で外すと決めた物）は足さず、手順8の「許す一覧」に回す。
7. **ひな形を直接使う所は変えない（K5-2b の確かめだけ）**: `scripts/setup_review_tenant.py:149`・`:160` と `scripts/setup_tenant.py:171` は、`backend/app/services/tenant.py` の同じ文字列（`_TENANT_TABLES_SQL`・`_RLS_*`・`get_tenant_tables_sql` など）を読み込んで流しているだけで、SQL の写しは持っていない。なので手順6の直しはそのまま届く。この2本を `create_tenant_schema` に差し替えない。理由: `create_tenant_schema` は失敗するとスキーマを丸ごと消す（`backend/app/services/tenant.py` の try/except）。`setup_review_tenant.py` は本番のコンテナで、すでにある審査用の会社に流す手順（`docs/runbooks/review-tenant-operations.md:24-29`）なので、差し替えるとその会社を消すおそれがある。`backend/app/routers/admin.py:74`・`backend/tests/rls_bootstrap.py:411`・`backend/tests/test_channel_type_control.py:73`・`backend/tests/test_system_roles.py:182` も変えない。ひな形の文字列を読んで中身を確かめる試験（`backend/tests/test_roles_system_key_ddl.py:35`・`backend/tests/test_tenant_issuer_tables_pg.py:63`・`backend/tests/test_tenant_payment_versioning_pg.py:73`・`:97`・`backend/tests/test_tenant_duty_rules_pg.py:75`・`:133`・`backend/tests/test_discord_role_link_ddl.py:41`）は、手順6の直しの後も通ることを CI で確かめる。`setup_tenant.py` を使う `.github/workflows/schema-check.yml:224`（テナントスキーマ整合性チェック）と `scripts/check_schema_catchup_sync.py:89` も緑のままであること。合否の線: `git grep -n "CREATE TABLE IF NOT EXISTS {schema" -- scripts/setup_review_tenant.py scripts/setup_tenant.py` が 0 件（ひな形の写しが無い。`{schema}` と `{schema_name}` の両方に当たる。`setup_tenant.py:25`・`:207` の説明の文と、`:281` の移行のファイルの置き換えは写しではないので数えない）で、上の CI が緑（件数と URL を書く）。`backend/tests/test_rls_tenant_meta_config.py:81` は、わざとひな形を使わず最小の表だけを作る試験なので K5-2b の数えに入れず、変えない。設計 §5-6 の第3版の「5か所」にあった setup_test_users という台本は今は無い。

8. **CI の検査を足す**（K5-2・K5-2c）: `.github/workflows/migration-test.yml` に新しい job を足す（既存の job は変えない。集約の `migration-test` の `needs` に足す）。中身:
   - (1) 使い捨て DB に public の前準備をし（`recon-5-2a/q1-run.md` の前準備と同じ）、`create_tenant_schema` で会社を1つ作る。**schema の無い会社の行（例 id 999）を前準備で入れない**（5-2a で run_py 12 本がこれで落ちた。`classification.md` §4 の1）。
   - (2) 形を取る（前）。(3) 登録全件を本体と同じ流し方で流す（run_sql と run_py。`scripts/run_all_migrations.sh` の登録の順）。(4) 形を取る（後）。
   - (5) 前と後の差を出す。比べる物は表・列・型・既定値・NOT NULL・索引・制約（外部キーは指す表の置き場所つき）・トリガ・RLS の印・方針・連番・権限（表ごとの `relacl` と、会社のスキーマの既定の権限 `pg_default_acl`。設計 §5-6 の比べる物に権限が入っているため）。差が0なら合格、1件でもあれば差の全件を出して失敗。
   - **(第2版で追加) 許す一覧**: B1（会社ごとの `suppliers`）・B2（外部キー 5 本）は、ひな形から外しても、登録の移行が今ある全部の会社に作り直すことがある（例 `migrations/020_create_bots_and_senders_view.sql:42`・`migrations/040_create_tenant_meta_config.sql:33`・`migrations/20260721_100000_close_reasons_quotes_add_lead_id.sql:48`・`migrations/20260703_030000_order_items_ben2.sql`）。本番 5 社には無いので、ひな形には入れない。その代わり、流した後にだけ出るこの種の差を、検査の中の「許す一覧」に1件ずつ書く（物の名前・作った移行のファイルと行・分け表の行・理由「本番 5 社に無い。段 5-3 の後は新しい会社に登録を流さないので作られない」）。許す一覧に入れてよいのは、分け表で B1・B2 に分けた物と、その代わりに移行が付ける別名の外部キー（例 `fk_quotes_lead`）だけ。それ以外を許す一覧に入れたくなったら止まる（`NEEDS_DECISION:`）。
   - 前提が無くて落ちる run_sql 3 本（`public.auth_events` が無い 2 本・`jarvis_db` が無い 1 本。`q1-run.md:370-372`）は、検査の中の「外す一覧」に名前と理由つきで書く（会社の形に関わらないため）。それ以外の本が落ちたら検査は失敗。
   - K5-2c（ひな形を変えて `migrations/` を足さない PR を止める段）は**このカードでは足さない**。このカードの PR 自身がひな形を変え、`migrations/` を足さない（手順6の直しは、登録済みの移行が作る形にひな形を合わせるだけなので、新しい移行は要らない）。同じ PR に足すと自分を赤にするため、この PR の合流の後に別のカードで足す。
9. 試験: 新しい検査の台本の試験（差0で緑・ひな形に列を1つ足すと赤）を `backend/tests/` に足す。Mac では流さない。CI で確かめる。
10. commit・push（force 禁止）。Draft の PR を `--base main` で作る。本文は `.github/pull_request_template.md` から書き、「触るファイル:」に全ファイルを列挙する。マージしない。

## 停止
- 止めるのは、手順5で分け表に無い違いが出たとき、設計と食い違うとき、push・PR の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- `migrations/` にファイルを足さない。本番に接続しない。`deploy.yml` を変えない。
- 試験の本文と台本に SQL の危険語を書かない（repo の移行を読んで流すのはよい）。Bash に psql の語を書かない。sleep しない。rm しない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 分かっている別の問題（このカードでは直さない）
- `backend/app/services/po_renderer.py:219` は会社ごとの `{tenant_schema}.suppliers` を読む。本番 5 社にはこの表が無い（`prod-reads/prod-5co.txt`）。B1 で新しい会社からも外れる。発注書の PDF を作る道（`purchase_orders.py:369`・`:402`）が本番で失敗しているかは、まだ確かめていない。Opus が別のテーマとして PO に上げる。

## 報告
- 最後の行は `DONE`・`BLOCKED: <理由>`・`NEEDS_DECISION: <問い>` のどれか。
- commit の番号、PR の番号、手順5・6・7 の表、CI の新しい job の結果の URL を書く。
