---
mode: handoff
---

# 5-2 実装カード（第3版）手順8〜10 の結果

本報告はカード 5-2 の実行結果である（実装役。第3版の決め1〜6に従った）。

## 起点と手順2・3

- 枝: `release/migration-template-5-2`。`origin` のその枝の先頭 `e69a123f12d518134f13c11ab50a8301e6e167c4`（Opus が main を取り込み済み）から始めた。`git rev-parse HEAD` と `git rev-parse origin/release/migration-template-5-2` は同じ。main は自分では取り込んでいない。
- 前回の commit `b13b826c8` は無いので、決め1をやり直した。
- 手順3 `./scripts/dev/executor-preflight.sh`: `PREFLIGHT FAIL`（[1/3] GitHub API に到達不可・[2/3] `gh auth switch` 失敗。[3/3][4/4] は OK）。Opus の決定どおり記録して続けた。gh と PR 作成はしていない。

## 決め1（やり直し）

| 項目 | 直した物 |
|---|---|
| ひな形から `channel_masters` を外す | `backend/app/services/tenant.py` の表（旧 :1616-1628）・RLS の印（旧 :2368）・方針 `channel_masters_tenant_isolation`（旧 :2641-2644）を外した。ひな形の中の `channel_masters` は 0 件 |
| 検査の許す一覧を表単位に | `scripts/check_tenant_template_shape.py` の `ALLOWED_DIFFS`（物ごと）を `ALLOWED_TABLES`（表の名前 1 つ → 理由）に替えた。入っているのは `channel_masters` の 1 表だけ。理由の欄は決め1の文（K6・登録の移行名・PR-C（ADR-1069）の合流後に外す）。表に属する物（表・列・索引・制約・トリガ・方針・連番・権限）だけを許す |
| 使われなかった行の知らせ | 差が出なかった行は失敗にせず、`知らせ: 許す一覧の行 <表名> は使われなかった…` を出す |
| 許す一覧の広がりの歯止め | 試験 `test_allowed_tables_is_only_channel_masters` が、一覧が `channel_masters` の 1 表だけであることを確かめる（増やすときは PO に聞く） |

## 手順8 CI の検査

`.github/workflows/migration-test.yml`（既存の job の中身は変えていない）:

- 新しい job `tenant-template-shape`（名前「会社のひな形の形の差0（実DB）」）。PostgreSQL 16 を立て、`scripts/check_tenant_template_shape.py` を流す。流れ: (1) public の前準備＋`create_tenant_schema` で会社 1 つ（schema の無い会社の行は入れない）→ (2) 形を取る（前）→ (3) 登録を `scripts/run_all_migrations.sh` の順に全件流す（run_sql と run_py）→ (4) 形を取る（後）→ (5) 差。比べる物: 表・列・型・既定値・NOT NULL・索引・制約（外部キーは指す表の置き場所つき）・トリガ・RLS の印・方針・連番・関数・ビュー・権限（表と連番の `relacl`・スキーマの既定の権限）。差が 1 件でもあれば全件を出して失敗。
- 「外す一覧」（前提が無くて落ちる 3 本。名前と理由つき）: `migrations/072_add_retention_indexes.sql`・`migrations/20261101_130000_add_new_device_approval.sql`（`public.auth_events` が無い）、`migrations/20260605_030000_create_salesanchor_app_role.sql`（本番の DB 名 `jarvis_db` が無い）。それ以外が落ちたら失敗。登録の数は固定の数を書かず `scripts/run_all_migrations.sh` から数える（今回は 405 本＝run_sql 379・run_py 26）。
- 方針の書き方の違い: 本番の `public.current_tenant_id()` とひな形の `current_setting('app.tenant_id', true)::integer` を同じ物として比べる置き換えを 1 つだけ（台本の中に理由を書いた）。
- 検査の前に `salesanchor_app`（LOGIN）の利用者を用意する（`ensure_app_role`）。無いと、会社の表への権限が前に付かず「権限」が全表で違って見える（クリーンな PostgreSQL で確かめて判明）。
- 集約 job `migration-test` の `needs` に `tenant-template-shape` を足し、結果を見る（動く条件が成り立つのに success でなければ失敗・条件が無いのに動いたら失敗）。
- `detect-changes` に出力 `tenant_template` を足した（`migrations/**`・`backend/app/services/tenant.py`・検査の台本・試験・登録の台本・workflow の変更で true）。ひな形だけを変える PR でも検査が動くため。既存の `migrations` の出力と各 job の条件は変えていない。
- K5-2c（ひな形を変えて `migrations/` を足さない PR を止める段）は足していない（カードの指示どおり、この PR の合流の後に別のカード）。

## 手順9 試験

`backend/tests/test_check_tenant_template_shape.py`（新規。試験の本文に SQL の危険語は無い）:

| 試験 | 中身 | DB |
|---|---|---|
| `test_diff_zero_when_same` / `test_diff_reports_three_kinds` | 差 0・3 種類の差 | 不要 |
| `test_allowed_table_covers_only_that_table_and_marks_used` / `test_allowed_row_unused_when_no_diff` | 許す一覧が `channel_masters` の物だけに効く・使われたかの記録 | 不要 |
| `test_allowed_tables_is_only_channel_masters` | 許す一覧は 1 表だけ | 不要 |
| `test_registry_counts_lines_like_runner` / `test_excluded_registry_files_exist_and_are_registered` | 登録の数え方・外す一覧の実在 | 不要 |
| `test_template_does_not_contain_channel_masters` | ひな形の文字列に `channel_masters` が無い | 不要 |
| `test_shape_diff_zero_when_template_matches_registry` | ひな形が登録と同じ列を持てば差 0（緑） | 要 |
| `test_shape_diff_red_when_registry_adds_column_template_lacks` | 登録が足す列をひな形が持たないと差 1 件（赤） | 要 |

手元（使い捨て PostgreSQL 16.15・localhost:55432・Python 3.12 の venv）の結果: `10 passed`。CI では `--no-cov` で流す（全体の網羅率の下限に引っかからないため）。決め1に関わる `tests/test_channel_type_control.py`（`test_create_tenant_schema_does_not_copy_channel_masters` を含む）・`test_roles_system_key_ddl.py`・`test_discord_role_link_ddl.py`・`test_tenant_duty_rules_pg.py` は手元で `15 passed, 3 skipped`（skipped は別の DB 設定を要する物）。

## 検査の手元の流し（使い捨て PostgreSQL 16.15。pytest と python の中からだけ DB に触った）

- クリーンな PostgreSQL（`jarvis` だけ。CI の service と同じ形）で `scripts/check_tenant_template_shape.py` を流した終わり:

```
登録 405 本（run_sql 379・run_py 26）
外す一覧で許した失敗: migrations/072_add_retention_indexes.sql（…）
外す一覧で許した失敗: migrations/20260605_030000_create_salesanchor_app_role.sql（…）
外す一覧で許した失敗: migrations/20261101_130000_add_new_device_approval.sql（…）
OK: 形の差 0
```

- 許す一覧の `channel_masters` の行は使われた（登録の `migrations/20260611_100000_create_channel_masters.sql` が作る表の差を許した）ので、「使われなかった」の知らせは出ていない。
- 手順7（確かめだけ）: `git grep -n "CREATE TABLE IF NOT EXISTS {schema" -- scripts/setup_review_tenant.py scripts/setup_tenant.py` は 0 件（終わりの番号 1）。2 本は差し替えていない。CI（`schema-check.yml`・`check_schema_catchup_sync.py`）の緑は push 後の CI で確かめる（URL は無い。PR を作っていないため。下の「未実施」）。

## 第3版の決め2〜6 の扱い

- 決め2（`calendar_events.meet_url` の分類の行）: 別の枝 `origin/release/ai-class-meet-url` に Opus 側の commit（`f0df9074a`・`7ddf092bd`）がすでにある。この実行では触っていない。`release/migration-template-5-2` の t10 は、その PR の合流まで落ちたままでよい（カードのとおり）。
- 決め3: `schema-check.yml` の `public.suppliers`、`test_lead_merge_pg.py` の会社の追加は残した。
- 決め4: 方針の置き換えは 1 つだけ（上）。
- 決め5: 登録は 405 本、外す 3 本は上のとおり。数えは `run_all_migrations.sh` から。
- 決め6: 並べて流すと止まる 2 試験（`test_tenant_issuer_tables_pg.py`・`test_assistant_karte_pg.py`）は手元では流していない・直していない。CI で落ちたら 1 回だけ流し直す。

## 変えた物（触るファイル）

- `backend/app/services/tenant.py`（`channel_masters` を外した）
- `scripts/check_tenant_template_shape.py`（許す一覧を表単位に・知らせ・`ensure_app_role`）
- `.github/workflows/migration-test.yml`（job `tenant-template-shape`・`detect-changes` の出力・集約の `needs`）
- `backend/tests/test_check_tenant_template_shape.py`（新規）
- `docs/handoff/migration-runner-redesign/recon-5-2b/step8-10.md`（この報告）

## 未実施・注意

- Draft の PR は作っていない（指示: gh・PR 作成はしない。preflight の gh 認証も FAIL）。手元で `shingo-cc` 名義で作る。本文は `.github/pull_request_template.md` から。
- CI の新しい job の結果の URL は無い（push だけ。PR が無いので workflow は未実行）。
- `migrations/`・`deploy.yml`・本番 `scripts/` は変えていない。本番には接続していない。

## 審査の差し戻し1件の直し（関数の比べ方・第3版の決め4）

- `scripts/check_tenant_template_shape.py` の関数の比べ方から、空白をまとめる置き換え（`regexp_replace`）を外した。比べるのは関数の本文そのもの（`md5(p.prosrc)`）。
- 代わりに `backend/app/services/tenant.py` の `trg_set_updated_at()` の本文を、登録の順で最後に流れる `CREATE OR REPLACE`（`migrations/20260902_100000_create_lead_attachments.sql`・登録の 742 行目）の本文と一字一句同じにした（`BEGIN` から `$fn$` の前の行までの字下げを含む）。
- 手元（使い捨て PostgreSQL 16・localhost:55432・Python 3.12 の venv）: `check_tenant_template_shape.py` は `OK: 形の差 0`（登録 405 本・外す 3 本は前と同じ）。`tests/test_check_tenant_template_shape.py` は `10 passed`（`--no-cov`）。
- preflight は FAIL のまま続けた（GitHub API に到達不可・gh の認証切り替え失敗。この実行では gh を使わない）。

## CI の Backend Tests 赤（test_real_repo）の直し

- 流したもの: `python3 -I scripts/ci/check_ci_aggregators.py`（直す前・終わりの番号 1）。生の出力:

```
OK e2e.yml:lint 組 192 外れ 0
OK e2e.yml:visual-language 組 48 外れ 0
OK karte-gate.yml:karte-gate 組 96 外れ 0
NG migration-test.yml:migration-test 組 0 外れ 0
  問題: run が参照する needs.detect-changes.outputs.<鍵> が 1 種類でない: ['migrations', 'tenant_template']
OK schema-check.yml:schema-check 組 48 外れ 0
OK test.yml:pytest 組 192 外れ 0
合計 まとめ役 6 組 576 外れ 0 問題 1
```

- 原因: この枝で足した `migration-test.yml` の集約 `migration-test` の run が、`detect-changes` の出力を `migrations` と `tenant_template` の 2 種類見ていた。点検の決まりは「鍵は 1 種類」。枝の中の原因。
- 直し: `tenant_template` の出力と絞り込みを外し、ひな形の 3 ファイル（`backend/app/services/tenant.py`・`scripts/check_tenant_template_shape.py`・`backend/tests/test_check_tenant_template_shape.py`）を `migrations` の絞り込みに足した。`tenant-template-shape` の `if` は `migrations == 'true'`。集約の run は `migrations` の値で、`$t` が true なら success・false なら skipped を求める（他の 3 ジョブと同じ形）。
- 直した後: 点検は `OK migration-test.yml:migration-test 組 12288 外れ 0`・合計 `問題 0`・終わりの番号 0。`scripts/tests/test_check_ci_aggregators.py` は `5 passed`（Python 3.12 の使い捨て venv）。
- preflight は FAIL（GitHub API 不達・gh 切り替え失敗）のまま続けた。
