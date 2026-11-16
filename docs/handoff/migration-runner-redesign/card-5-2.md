---
mode: handoff
---
# 実装カード：会社のひな形を1つにする（段5 5-2・1A）— ひな形の直書きを分け表どおりに直し、CI に形の差0の検査を足す（Sonnet・クラウド）

状態: **第3版（2026-11-16）。PO の実装承認（2026-11-16「1」）は受領済み。第2版の直しは承認の範囲（1A: 足りない表と列を書き足す）の中。**

第2版の直し（Opus の設計判断・PO の言葉ではない）: 第1版は「手順6の後に形の差0」としていたが、分け表の 147 件だけでは足りなかった。登録の手順が作る 645 件をひな形に足すことが抜けていた（設計の入れ忘れ）。手順6に足す作業（流した後だけ・前だけ・中身違いの3つ）を足し、手順8は「形の差の許す一覧は0件で始め、要れば止まる」とした。1つの PR で全部入れる（検査を必須にしないまま分けると、検査が使われなくなるため）。

第3版の直し（Opus の設計判断・PO の言葉ではない）: 第2回の実行（2026-11-16、commit `3d1b00a00214d082623fe2cd56880ec9f60c6c7e`、報告 `docs/handoff/migration-runner-redesign/recon-5-2b/step5-6.md`）が `NEEDS_DECISION` で止まった2件を決めた。下の「第3版の決め」に従い、同じブランチ `release/migration-template-5-2` の続きから手順8〜10を行う。

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
   - **(第2版で追加) 登録の手順が作る物を全部ひな形に足す**: 第1回の実行（2026-11-16、`NEEDS_DECISION` で停止）で、今のひな形の会社に登録全件を流すと、流した後だけにある物が 632 件（表 26・列 352・索引 103・制約 85・連番 25・方針 20・トリガ 11・関数 10）、流す前だけ 4 件、中身が違う 9 件出た。分け表の 147 件は「本番 003 と、ひな形＋登録全件」の比べなので、この 645 件は分け表に入っていない（`classification.md` §1「対象にしない物」の印1・印3）。第1回の生の一覧は commit されずに消えたので、まず手順5の使い捨て DB で同じ比べを取り直し、645 件の一覧（種類・名前・作った/変えた登録の移行のファイル）を報告に表で出す（件数が違えば記録して続ける）。そのうえで次の3つに分けて直す。
     - (a) 流した後だけの物: ひな形に足す（`calendar_events` のように表ごと無い物は表ごと足す。別名の外部キーもここ）。
     - (b) 流す前だけの物（移行が消す・付け替える物）: ひな形から外す。
     - (c) 中身が違う物: 流した後の中身にひな形を直す。
     - どれも、直す前に分け表 A・B と食い違わないか照らす（例: (a) に B1・B2 の名前そのものや C の物が出たら足さずに止まる `NEEDS_DECISION:`）。
     - 書き写す元は、使い捨て DB で登録全件を流した後のその会社の形（`pg_dump --schema-only` の会社のスキーマ分など）。会社の番号・スキーマ名は `{schema}`・`{tenant_id}` に置き換える。ひな形はファイルに書き出す形にせず、直書きの SQL のまま足す（1A）。直した物は (a)(b)(c) ごとの件数と、元の登録の移行のファイル名を表にする。
7. **ひな形を直接使う所は変えない（K5-2b の確かめだけ）**: `scripts/setup_review_tenant.py:149`・`:160` と `scripts/setup_tenant.py:171` は、`backend/app/services/tenant.py` の同じ文字列（`_TENANT_TABLES_SQL`・`_RLS_*`・`get_tenant_tables_sql` など）を読み込んで流しているだけで、SQL の写しは持っていない。なので手順6の直しはそのまま届く。この2本を `create_tenant_schema` に差し替えない。理由: `create_tenant_schema` は失敗するとスキーマを丸ごと消す（`backend/app/services/tenant.py` の try/except）。`setup_review_tenant.py` は本番のコンテナで、すでにある審査用の会社に流す手順（`docs/runbooks/review-tenant-operations.md:24-29`）なので、差し替えるとその会社を消すおそれがある。`backend/app/routers/admin.py:74`・`backend/tests/rls_bootstrap.py:411`・`backend/tests/test_channel_type_control.py:73`・`backend/tests/test_system_roles.py:182` も変えない。ひな形の文字列を読んで中身を確かめる試験（`backend/tests/test_roles_system_key_ddl.py:35`・`backend/tests/test_tenant_issuer_tables_pg.py:63`・`backend/tests/test_tenant_payment_versioning_pg.py:73`・`:97`・`backend/tests/test_tenant_duty_rules_pg.py:75`・`:133`・`backend/tests/test_discord_role_link_ddl.py:41`）は、手順6の直しの後も通ることを CI で確かめる。`setup_tenant.py` を使う `.github/workflows/schema-check.yml:224`（テナントスキーマ整合性チェック）と `scripts/check_schema_catchup_sync.py:89` も緑のままであること。合否の線: `git grep -n "CREATE TABLE IF NOT EXISTS {schema" -- scripts/setup_review_tenant.py scripts/setup_tenant.py` が 0 件（ひな形の写しが無い。`{schema}` と `{schema_name}` の両方に当たる。`setup_tenant.py:25`・`:207` の説明の文と、`:281` の移行のファイルの置き換えは写しではないので数えない）で、上の CI が緑（件数と URL を書く）。`backend/tests/test_rls_tenant_meta_config.py:81` は、わざとひな形を使わず最小の表だけを作る試験なので K5-2b の数えに入れず、変えない。設計 §5-6 の第3版の「5か所」にあった setup_test_users という台本は今は無い。

8. **CI の検査を足す**（K5-2・K5-2c）: `.github/workflows/migration-test.yml` に新しい job を足す（既存の job は変えない。集約の `migration-test` の `needs` に足す）。中身:
   - (1) 使い捨て DB に public の前準備をし（`recon-5-2a/q1-run.md` の前準備と同じ）、`create_tenant_schema` で会社を1つ作る。**schema の無い会社の行（例 id 999）を前準備で入れない**（5-2a で run_py 12 本がこれで落ちた。`classification.md` §4 の1）。
   - (2) 形を取る（前）。(3) 登録全件を本体と同じ流し方で流す（run_sql と run_py。`scripts/run_all_migrations.sh` の登録の順）。(4) 形を取る（後）。
   - (5) 前と後の差を出す。比べる物は表・列・型・既定値・NOT NULL・索引・制約（外部キーは指す表の置き場所つき）・トリガ・RLS の印・方針・連番・権限（表ごとの `relacl` と、会社のスキーマの既定の権限 `pg_default_acl`。設計 §5-6 の比べる物に権限が入っているため）。差が0なら合格、1件でもあれば差の全件を出して失敗。
   - **(第2版で追加) 形の差の許す一覧は0件の見込み**: 審査で確かめた事実（2026-11-16）: B1 の会社ごとの `suppliers` を作る登録の移行は無い（`migrations/038_add_products_phase1c_columns.sql:76-90` は表が有る時だけ外部キーを付け、表は作らない）。B2 の5本の名前（`*_fkey`）そのものを作る登録の移行も無い。登録の移行が付けるのは別名の外部キー（`fk_quotes_lead`・`fk_deal_close_reasons_lead`・`fk_poi_order_item`・`fk_bots_owner_staff_id_user`・`fk_tenant_meta_config_connected_by_staff_id_user`。後の2本は `migrations/20261013_110000_repoint_person_columns_to_users.sql:51-61`）で、5本とも本番 003 にある（`recon-5-2a/prod-reads/fk003.txt:4`・`:24`・`:54`・`:62`・`:76`）。これらは手順6でひな形に足す物で、形の差の許す一覧には入れない。検査の中に「形の差の許す一覧」の置き場所は作ってよいが、中身は0件で始める。1件でも入れたくなったら止まる（`NEEDS_DECISION:`。物の名前・作った移行のファイルと行・本番 003 に有るか無いかを書く）。
   - 前提が無くて落ちる run_sql 3 本（`public.auth_events` が無い 2 本・`jarvis_db` が無い 1 本。`q1-run.md:370-372`）は、検査の中の「外す一覧」に名前と理由つきで書く（会社の形に関わらないため）。それ以外の本が落ちたら検査は失敗。
   - K5-2c（ひな形を変えて `migrations/` を足さない PR を止める段）は**このカードでは足さない**。このカードの PR 自身がひな形を変え、`migrations/` を足さない（手順6の直しは、登録済みの移行が作る形にひな形を合わせるだけなので、新しい移行は要らない）。同じ PR に足すと自分を赤にするため、この PR の合流の後に別のカードで足す。
9. 試験: 新しい検査の台本の試験（差0で緑・ひな形に列を1つ足すと赤）を `backend/tests/` に足す。Mac では流さない。CI で確かめる。
10. commit・push（force 禁止）。Draft の PR を `--base main` で作る。本文は `.github/pull_request_template.md` から書き、「触るファイル:」に全ファイルを列挙する。マージしない。

## 第3版の決め（第2回の止まり2件と、カードに無かった変更）
根拠は Opus が 2026-11-16 に読んだ物: `docs/handoff/channel-master-shared/design.md` の K6、Draft の PR #5248（ADR-1069・PR-C。会社ごとの `channel_masters` を消す移行 `migrations/20261107_180000_drop_tenant_channel_masters.sql` を足す。PO 本人の GO 待ち）、`migrations/20261024_100000_create_ai_cloud_meta.sql:111-130`（分類の無い文字の列は形だけにする）、本番の分類表の読み取り（reader の道、AUDIT sha=2d4769bc424b。`calendar_events` の分類 11 行に `meet_url` が無い）、前例 PR #5507（分類の行を足す変更を ADR-1003 の委任 GO で合流）。

1. **`channel_masters` は K6 を守る（ひな形に入れない）**。K6 は PO が承認した設計で、ひな形と移行が食い違うときは設計を正とする（このカードの「前提」）。会社ごとの表は PR-C で消える予定で、ひな形に足すと逆向きになる。
   - ひな形（`backend/app/services/tenant.py`）に `channel_masters` の物（表・列・索引・制約・方針・RLS の印・連番・権限）を足していたら外す。`backend/tests/test_channel_type_control.py::test_create_tenant_schema_does_not_copy_channel_masters` が通ること。
   - 形の差の検査の「許す一覧」に、表 `channel_masters` に属する物だけを入れる（第2版の「0件で始める」をこの1表に限って改める）。これは設計 `design.md` §5-6 の追記2と K5-2 の表の注記に書いた例外なので、「設計と食い違ったら止まる」には当たらない。書き方は表の名前1つで、物ごとの名前の羅列にしない。理由の欄に「K6（`docs/handoff/channel-master-shared/design.md`）。登録の `migrations/20260611_100000_create_channel_masters.sql` が全会社に作るが、PR-C（ADR-1069）で消す予定。PR-C の合流後にこの行を外す」と書く。
   - 許す一覧の行が使われなかった（差が出なかった）ときは、検査は失敗にせず、行の名前を出して知らせる（PR-C の後に外し忘れを見つけるため）。
   - `channel_masters` 以外の物を許す一覧に入れたくなったら止まる（`NEEDS_DECISION:`）。
2. **`calendar_events.meet_url` の分類の行は、別の小さい PR で先に足す**（この PR の試験は変えない）。本番の分類表にも行が無い（本番の AI 用の写しでは、文字の列の既定どおり形だけで出ている）。行を `mask` で足しても AI 用の写しの出し方は変わらない。
   - `origin/main` から新しいブランチ `release/ai-class-meet-url` を作り（`bash scripts/new-worktree.sh release/ai-class-meet-url`）、`migrations/20261024_100300_create_ai_cloud_views.sql` の `calendar_events` の `mask`・理由空の行（:373）に `meet_url` を足す。分類表の元 `docs/handoff/cloud-case-ai/stage1-column-class.tsv` にも同じ行を足す。行の総数を書いた所（`backend/tests/ops/test_ai_cloud_views.py:486` の `1162` と、同じ数を書いた他の所。`git grep -n 1162 -- migrations backend docs/handoff/cloud-case-ai` で全部出す）を 1 増やす。ほかは変えない。
   - Draft の PR を `--base main` で作る（本文はひな形から。「触るファイル:」に全部）。このブランチの作業は手順8より先に終える。`release/migration-template-5-2` に混ぜない。
   - `release/migration-template-5-2` の t10 は、上の PR の合流まで落ちたままでよい（報告に書く）。実装役は main を取り込まない（手順2の禁止のまま）。上の PR の合流の後、Opus が `gh pr update-branch` で取り込む。
   - 行の総数 1162 を書き換えるのは `backend/tests/ops/test_ai_cloud_views.py:486` と `migrations/20261024_100300_create_ai_cloud_views.sql:3` の2か所。`docs/handoff/cloud-case-ai/stage1-h-decision.md:62` は実行の番号の一部なので変えない。`stage1-column-class.tsv` の行は、ほかの `calendar_events` の行と同じ列の形（型の列は `text`）で足す。
   - 合流の順の注意: Draft の PR #5248（PR-C）も同じ行の総数を書き換える。後から合流する側が数を合わせ直す（Opus が合流のときに確かめる）。
   - この別の PR は `migrations/` を変えるので危険 PR（ADR-136）に当たる。GO は ADR-1003 の委任の道で Opus が出す（前例 #5507）。
3. **第2回のカードに無かった変更は残してよい**: (a) `.github/workflows/schema-check.yml` に `public.suppliers`（`id` だけ）を足した物。B1 でひな形が `public.suppliers` を指すため要る。`IF NOT EXISTS` で作り、行の上に理由（B1・このカード）を1行書く。(b) `backend/tests/test_lead_merge_pg.py` の見積の種に会社を足した物（`quotes.company_id` が本番と同じく NOT NULL になったため）。
4. **方針（policy）の書き方の違い**: 新しい表 6 つの方針を `current_setting('app.tenant_id', true)::INTEGER` で書いたのはよい。検査で `public.current_tenant_id()` と同じ物として比べる置き換えは、この1つの書き換えだけにし、台本の中に理由（会社を作る時点で public の包み関数が無い環境がある）を書く。ほかの書き方の違いを同じにする置き換えは足さない。
5. **登録の数**: 登録は 405 本（第1版の 404 は古い）。新しい会社に流すと前提が無くて落ちる 3 本（`migrations/072_add_retention_indexes.sql`・`migrations/20261101_130000_add_new_device_approval.sql`・`migrations/20260605_030000_create_salesanchor_app_role.sql`）は手順8の「外す一覧」に入れる（第2版のとおり）。数え方は固定の数を書かず、`scripts/run_all_migrations.sh` の登録から数える。
6. **並べて流すと止まる試験**: `test_tenant_issuer_tables_pg.py`・`test_assistant_karte_pg.py` が並べて流すときだけ止まる件は直さない。CI で落ちたら1回だけ流し直し、2回目も落ちたら止まって報告する。

## 停止
- 止めるのは、手順5の外部キーの比べ（許す12組）で分け表に無い違いが出たとき（手順6の 645 件の比べはここに入らない。手順6の中の止まる条件に従う）、設計と食い違うとき、push・PR の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- `migrations/` にファイルを足さない（第3版の決め2の別ブランチで既存の分類の移行1本の行を直すのは除く）。本番に接続しない。`deploy.yml` を変えない。
- 試験の本文と台本に SQL の危険語を書かない（repo の移行を読んで流すのはよい）。Bash に psql の語を書かない。sleep しない。rm しない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 分かっている別の問題（このカードでは直さない）
- `backend/app/services/po_renderer.py:219` は会社ごとの `{tenant_schema}.suppliers` を読む。本番 5 社にはこの表が無い（`prod-reads/prod-5co.txt`）。B1 で新しい会社からも外れる。発注書の PDF を作る道（`purchase_orders.py:369`・`:402`）が本番で失敗しているかは、まだ確かめていない。Opus が別のテーマとして PO に上げる。

## 報告
- 最後の行は `DONE`・`BLOCKED: <理由>`・`NEEDS_DECISION: <問い>` のどれか。
- commit の番号、PR の番号、手順5・6・7 の表、CI の新しい job の結果の URL を書く。
