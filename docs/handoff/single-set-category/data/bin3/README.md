# 区分「シングルセット系」便3 手順 2：13 商品の付け替え 記録 SQL（本番未適用）

PO が 2026-11-12「1」で決めた 13 商品（465992・466031・466062・466088・466165〜466173）の区分を、セット系（PC_SET）からシングルセット系（PC_SINGLE_SET）へ付け替える（設計 `docs/handoff/single-set-category/design.md` §5「### 便3」手順 1・2。ADR-1007 により migration には書かない）。前例: ADR-1035 便2（`docs/handoff/condition-unit-booklet/data/bin2/02_apply.sql`）の商品の付け替え。

前提（2026-11-12 reader で確かめた）:
- 便1（PR #5417）のコードは本番に出ている（2026-11-12 05:36Z 配備）。
- 便2 の区分 PC_SINGLE_SET（id 15・シングルセット系・有効・tenant_id NULL）は本番に入っている（2026-11-12 19:58 JST。`../bin2/`）。
- 13 商品はすべてセット系（product_category_id 4）・有効・tenant_id NULL。`01_precheck.sql` の読み取り部分（記録の検査を足す前の 4 本）を reader の表に置き換えて 1 文ずつ流し、PRECHECK_OK 4 行がそろうことを確かめた（2026-11-12 12:43Z）。区分ごとの商品数: 区分なし 1009・ブックレット系 5・箱系 350・バルク系 24・プロモパック系 11・セット系 20・シングル系 55。
- 表 products には更新時刻を入れる仕掛け（trigger_set_updated_at_public_products）と、区分への外部キー（fk_products_product_category_id。migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:305）がある。付け替えで 13 商品の updated_at が変わる。
- 解析は 1 回ごとに区分を DB から読み直す（`backend/app/services/line_analysis_v102_svc.py:1609` の run_v102_analysis が投稿ごとに `load_v102_masters`（同 `:219`）を呼び、同 `:237` → `gemini_raw_copy_v102_product_first.load_product_first_masters` → `tcg_analyzer_svc.load_product_kubun_type_map`。手元に溜めておく仕組みは無い）。

| 順 | 作業 | 期待 |
|---|---|---|
| 1 | `01_precheck.sql` | PRECHECK_OK が 5 行（targets_in_pc_set 13・single_set_category_active 1・single_set_products 0・pc_set_products 20・audit_absent 0）。ROW 行 13 行・COUNT 行は情報 |
| 2 | `02_apply.sql` を `-v end=ROLLBACK` で DRY-RUN | AUDIT_INSERTED 1・UPDATED products 13・CHECK_OK 4 行（targets_single_set 13・single_set_products 13・pc_set_products 7・audit 1）。BEFORE 行・AFTER 行 13 行ずつ。最後に ROLLBACK |
| 3 | `02_apply.sql` を `-v end=COMMIT` | 手順 2 と同じ件数、COMMIT |
| 4 | `03_verify.sql` | VERIFY_OK が 4 行（audit 1 を含む）。AUDIT 行に書く前の区分が 13 商品ぶん入っている。COUNT 行を 01 と突き合わせ、セット系 20→7・シングルセット系 0→13 のほかは変わっていないことを確かめる |

記録（設計 §5 便3 手順 2「前後の区分と audit を残す」）:
- 前後の区分は `public.audit_log` に 1 行残す（table_name products・changed_by `claude-opus (single-set-bin3-20261112; PO 2026-11-12)`・old_values に 13 商品の書く前の区分・new_values に印 `single-set-bin3-20261112` と付け替え先）。画面で商品を直したときも同じ表に 1 行入る（`backend/app/services/tcg_product_detail_svc.py:310-314`）。record-SQL から audit_log に書く前例: `docs/handoff/revival-guard/data/02_apply.sql`。
- 本番の audit_log の列（2026-11-12 reader）: id（連番の既定値）・table_name・record_id（uuid）・action・changed_by（100 字まで）・changed_at（既定 now()）・old_values・new_values。行単位の制限（RLS）は無い。印 `single-set-bin3-20261112` の行は 0 件。
- products は行単位の制限が強制（FORCE）されているが、台本が使う DB の利用者 jarvis は superuser（2026-11-12 reader の pg_roles）。superuser は行単位の制限を常に通り越す（PostgreSQL 公式 https://www.postgresql.org/docs/current/ddl-rowsecurity.html 「Superusers and roles with the BYPASSRLS attribute always bypass the row security system」）。前例の付け替え（condition-unit-booklet 便2）も同じ利用者で通っている。
- psql の生出力（BEFORE/AFTER 行を含む）は、PO が流す台本が `~/CC報告ファイル-keep/single-set-bin3-<日付>/` に `precheck|dryrun|commit|verify-<時刻>.out` として残す。

戻し: `04_rollback.sql`（設計 §9）。`-v end=ROLLBACK` で DRY-RUN してから `-v end=COMMIT`。付け替えの記録が 1 行あることを確かめ、戻したことも audit_log に 1 行（印 `single-set-bin3-20261112-rollback`）残し、13 商品をセット系へ戻す。13 行でなければ止まる。13 商品のどれかが付け替えの後に画面で別の区分に変わっていると全体が止まるので、そのときは BEFORE 行で外れた商品を見て PO に聞く。解析の行は戻らないので、戻した後は設計 §9 のとおり対象の job を再解析する。

- 実行: PO が `!` で台本を流す（作者は本番に書き込まない）。ロック待ちは 1 秒で切る（ADR-1037）。
- 付け替えの後に届く投稿は、この 13 商品をシングルセット系として読む（状態はシングル系と同じ群・単位は Set）。今ある解析の行は書き換わらない。
- この後は設計 §5 便3 の手順 3〜6（対象 job を選ぶ → 古い投稿から → 試走（書き込みなし）→ PO の了解 → 再解析）。試走の台本は便3 の実装カードで作る（まだ無い）。KGI 1・2（K5）と K6 はその後に数える。
