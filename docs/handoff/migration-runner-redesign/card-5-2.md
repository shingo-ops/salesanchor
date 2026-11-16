---
mode: handoff
---
# 実装カード：会社のひな形を1つにする（段5 5-2・1A）— ひな形の直書きを分け表どおりに直し、CI に形の差0の検査を足す（Sonnet・クラウド）

状態: **草案。PO の明示の実装承認の前は流さない。**

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は Draft で作らせる。マージはさせない（Opus が審査役の判定の後に行う） | ○ |
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
5. **最初の確かめ（直す前）**: 今のひな形で使い捨て DB に会社（id 3）を作り、登録全件を流した後の形を、外部キーの指す表の置き場所（schema 名）を別の列にして取る（`pg_constraint.confrelid` → `pg_class` → `pg_namespace`）。会社の中を指す本数と共用（public）を指す本数、共用を指す外部キーの「表 → 指す表」の一覧を出し、`recon-5-2a/prod-reads/fk003.txt`（会社の中 51・共用 24）と1本ずつ比べる。合否の線: 違いが `fk-public-compare.txt` の3本（B2 の2本・A2 の1本）と、分け表の C2 の `fk_orders_invoice` 以外に無いこと。ほかの違いがあれば一覧を書いて `NEEDS_DECISION:` で止まる。
6. **ひな形を直す**（分け表 `classification.tsv` の分けごと。行ごとに、tsv の行と直した `tenant.py` の行番号を対で表にする）:
   - A1 注文の 8 列、A2 `calendar_owner_settings`（表・主キー・索引・`users` への外部キー・`share_mode` の制約・RLS の印と方針）、A3 の 8 件を足す・直す。型・既定値・NOT NULL・制約の中身は `recon-5-0b/prod003/` の行と `prod-reads/prod-cols.txt` に合わせる（書き写す元の行を表に書く）。
   - B1 会社ごとの `suppliers`（表・索引・方針・RLS の印・連番）を外し、`{schema}.suppliers` を指す 2 本の外部キー（`tenant.py:1013`・`:1021` 付近）を `public.suppliers` に直す。
   - B2 の外部キー 5 本を外す。
   - C1・C2・C3・D・E はひな形を変えない。
7. **ひな形を直接使う所を揃える**（K5-2b）: `scripts/setup_review_tenant.py:149`・`:160` と `scripts/setup_tenant.py:171` は、ひな形の文字列を自分で組み立てて流している。どちらも `create_tenant_schema`（`tenant.py:1951`）を呼ぶ形に変え、自分で組み立てる行を0にする。`backend/app/routers/admin.py:74`・`backend/tests/rls_bootstrap.py:411`・`backend/tests/test_channel_type_control.py:73`・`backend/tests/test_system_roles.py:182` は既に `create_tenant_schema` を呼ぶので変えない（2026-11-16 origin/main a7537ec54 で数え直し。設計 §5-6 末尾と同じ）。ひな形の文字列を読んで中身を確かめる試験（`test_roles_system_key_ddl.py:35`・`test_tenant_issuer_tables_pg.py:63`・`test_tenant_payment_versioning_pg.py:73`・`:97`・`test_tenant_duty_rules_pg.py:75`・`:133`・`test_discord_role_link_ddl.py:41`）は、読むだけなのでそのまま通ることを確かめる。設計 §5-6 の第3版の「5か所」にあった `scripts/setup_test_users.py` は今は無い。合否の線: `git grep -n "_TENANT_TABLES_SQL.format\|get_tenant_tables_sql(" -- scripts backend/app` が `tenant.py` の中だけになる（件数と行を書く）。
8. **CI の検査を足す**（K5-2・K5-2c）: `.github/workflows/migration-test.yml` に新しい job を足す（既存の job は変えない。集約の `migration-test` の `needs` に足す）。中身:
   - (1) 使い捨て DB に public の前準備をし（`recon-5-2a/q1-run.md` の前準備と同じ）、`create_tenant_schema` で会社を1つ作る。**schema の無い会社の行（例 id 999）を前準備で入れない**（5-2a で run_py 12 本がこれで落ちた。`classification.md` §4 の1）。
   - (2) 形を取る（前）。(3) 登録全件を本体と同じ流し方で流す（run_sql と run_py。`scripts/run_all_migrations.sh` の登録の順）。(4) 形を取る（後）。
   - (5) 前と後の差を出す。比べる物は表・列・型・既定値・NOT NULL・索引・制約（外部キーは指す表の置き場所つき）・トリガ・RLS の印・方針・連番。差が0なら合格、1件でもあれば差の全件を出して失敗。
   - 前提が無くて落ちる run_sql 3 本（`public.auth_events` が無い 2 本・`jarvis_db` が無い 1 本。`q1-run.md:370-372`）は、検査の中の「外す一覧」に名前と理由つきで書く（会社の形に関わらないため）。それ以外の本が落ちたら検査は失敗。
   - K5-2c: ひな形（`tenant.py` の `_TENANT_TABLES_SQL`・`_RLS_*`）を変えた PR で、同じ PR に `migrations/` の新しいファイルが無ければ失敗させる段を足す。
9. 試験: 新しい検査の台本の試験（差0で緑・ひな形に列を1つ足すと赤・ひな形だけ変えて migrations/ 無しで赤）を `backend/tests/` に足す。Mac では流さない。CI で確かめる。
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
