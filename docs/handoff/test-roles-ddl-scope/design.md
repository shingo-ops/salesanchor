# design: roles の移行試験を1つのテナントに絞り、同じ種類のぶつかりを見張りで止める

- recon: `docs/handoff/test-roles-ddl-scope/recon.md`
- 関係 ADR: なし（recon §5。試験の土台だけの直し）。新しい ADR は作らない
- PO の言葉: 「1」（試験がぶつからないように直す設計をして、クラウドの担当に直させる）・「不具合とエラー部分を省略せずに確認をして…安全に進めてくれ」

## 1. 目的
docs だけの変更でも CI がたまたま落ちて、マージが止まったり何度もやり直したりするのを無くす。同じ種類のぶつかり（共有 DB で全テナントを回す移行を絞らずに流す）を、次からは機械で止める。

## 2. KGI（○×で判定）
| 基準 | 検証方法 |
|------|----------|
| K1 roles の移行試験が、自分のテナント（tenant_995）以外のテナントに触れない | 新しい試験 `test_roles_migration_is_scoped_to_own_tenant` の結果（下 §4-3）。CI の pytest-run-internal で PASSED。Opus が `gh run view --log` の生出力をファイルに保存し、試験名と PASSED を目で読む |
| K2 冪等の確かめ（2回流しても壊れない）と、列・索引の確かめは前と同じに残る | `test_new_tenant_has_system_key_and_migration_is_idempotent` が CI で PASSED。差分で assert 行（`:76-93` 相当）が変わっていないこと |
| K3 全テナントを回す移行を名前で参照する試験ファイルが増えた・減ったら、分類を書くまで落ちる | 新しい見張り `backend/tests/test_tenant_loop_migration_guard.py` が CI で PASSED。加えて担当がローカルではなくクラウドで「分類表から1行消すと落ちる」ことを1回確かめ、その出力を報告に貼る（コミットはしない） |
| K4 ほかの試験を壊さない | PR の先頭で必須チェックがすべて成功 |
| K5 tenant_991 の「does not exist」で落ちる回数が0 | マージ後 2026-11-19 までの main と PR の pytest-run-internal のログで `schema "tenant_` と `does not exist` を含む行の数。Opus が `gh run list`→ログ保存→ grep で数える（基準値: 11/3〜11/5 で3回） |

## 3. 対象と対象外
- 対象（3ファイル、すべて `backend/tests/`）
  1. `rls_bootstrap.py`: `_TENANT_LOOP_MIGRATIONS` に `"20261005_150000_add_roles_system_key.sql": 1,` を1行足す。上のコメント（`:154`）を「全テナントを回す正本 migration のうち、試験が1つのテナントに絞って流すもの（lead_merge・calendar・roles の試験）」に直す
  2. `test_roles_system_key_ddl.py`: 番号を 995 に、流し方を絞る形に、後片付けを札の中に
  3. 新規 `test_tenant_loop_migration_guard.py`: 見張り（DB を使わない静的な試験）
- 対象外: migrations・製品コード・CI 設定・`test_meta_channels.py`・`test_rls_tenant_meta_config.py`・`test_permission_resolution_pg.py`・TEST_PG_URL だけで動く2本
- 対象外（別の作業として記録・今回は直さない）:
  - 998 の重なり（test_rls_tenant_meta_config が札なしで tenant_998/999 を作って消す。test_permission_resolution_pg も 998）
  - テナント番号が試験ファイルどうしで重ならないことの見張り
  - TEST_PG_URL があるときだけ動く2本（069・063 を絞らずに流す）
  - pre-commit フックが routers だけを見る件

## 4. 変更前後

### 4-1. `backend/tests/test_roles_system_key_ddl.py`
```python
# 変更前 :17
from tests.rls_bootstrap import bootstrap_tenant_schema, tenant_schema_lock
# 変更後
from tests.rls_bootstrap import _apply_migration_on_conn, bootstrap_tenant_schema, tenant_schema_lock

# 変更前 :23
_TENANT_ID = 997
# 変更後（997 は test_meta_channels.py:725 と重なる。995 は試験・移行のどこにも無い番号。recon §4）
_TENANT_ID = 995

# 変更前 :69-75 と :94-97
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
            assert schema_name == _SCHEMA
            migration_sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
            async with admin_engine.begin() as conn:
                await conn.exec_driver_sql(migration_sql)  # 1 回目
                await conn.exec_driver_sql(migration_sql)  # 2 回目（冪等）
            （確かめの部分）
    finally:
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
        await admin_engine.dispose()
# 変更後
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            try:
                schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
                assert schema_name == _SCHEMA
                # 全テナントを回す正本を、この試験のテナントだけに絞って流す（他ワーカーのテナントに触れない）
                async with admin_engine.begin() as conn:
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 1 回目
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 2 回目（冪等）
                （確かめの部分は1文字も変えない。字下げだけ1段深くなる）
            finally:
                async with admin_engine.begin() as conn:
                    await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    finally:
        await admin_engine.dispose()
```
- 文字だけの試験（DDL の印・run_all_migrations.sh への登録・INSERT/UPDATE/DELETE が無い）は変えない。
- `migration_sql` の読み込み行は不要になるので消す（`_REPO_ROOT` を他で使っていれば import は残す）。

### 4-2. `backend/tests/rls_bootstrap.py`
- §3 の1のとおり。`_scope_tenant_migration` 本体は変えない（回数1は recon §2 で確認済み。ずれたら既存の検査が止める）。

### 4-3. `test_roles_system_key_ddl.py` に足す試験（K1・DB を使わない）
```python
def test_roles_migration_is_scoped_to_own_tenant():
    from tests.rls_bootstrap import _scope_tenant_migration
    sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    scoped = _scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql
```

### 4-4. 新規 `backend/tests/test_tenant_loop_migration_guard.py`（K3）
- やること:
  1. `migrations/*.sql` のうち、正規表現 `(?:nspname|schema_name|schemaname|table_schema)\s*(?:~\*?|I?LIKE|~~)\s*'\^?tenant_`（大文字小文字を区別しない）に当たるものを「全テナントを回す移行」とする
  2. `backend/tests/**/*.py`（このファイル自身を除く）から、`[0-9]{3}[0-9_]*_[a-z0-9_]+\.sql` に当たる名前のうち 1 に入るものを集め、`{試験ファイルの backend/tests からの相対パス: {移行名, ...}}` を作る
  3. 下の分類表 `_REVIEWED` と**完全に一致**することを確かめる。足りない・余る組があれば、どのファイルのどの移行かを出して落ちる（「分類を書いてから足す」）
  4. 分類ごとの確かめ:
     - `scoped`: その移行が `rls_bootstrap._TENANT_LOOP_MIGRATIONS` か `rls_bootstrap._TENANT_BOOTSTRAP_MIGRATIONS` に入っていること
     - `own_database`: その試験ファイルの文字に `CREATE DATABASE` か `test_tcg_work_matching_integration import` があること
     - `text_only` / `pg_url_only`: 理由の文字が空でないこと（`pg_url_only` はファイルに `TEST_PG_URL` があることも確かめる）
- 分類表（`/tmp/CC報告ファイル/test-race/100-crosscheck-head.txt` から。今は 63 組。段A で rls_bootstrap.py に roles を足すので **64 組**。担当は実物で数え直し、64 でなければ止めて報告）:

| ファイル | 分類 | 移行 |
|---|---|---|
| rls_bootstrap.py | scoped | 17本（078・090・091・095・099・20260602_120000・20260604_090000・20260604_180000・20260604_220000・20260611_100000・20260614_100000・20260621_020000・20260715_100000・20260902_100000・20261005_150000（段Aで追加）・20261103_200000・20261104_161223） |
| test_calendar_sync_tenant_reset_pg.py | scoped | 078・20260621_020000・20261103_200000・20261104_161223 |
| test_lead_merge_pg.py | scoped | 090・091・095・099・20260602_120000・20260604_090000・20260604_180000・20260604_220000・20260715_100000・20260902_100000 |
| test_lead_merge_pg.py | text_only（消した表の照合 `:76-79`） | 20260601_140000_drop_customers_tables・20260729_043520_drop_deals |
| test_roles_system_key_ddl.py | scoped | 20261005_150000_add_roles_system_key |
| condition_value_columns.py | text_only（コメント `:6`） | 20260925_010000 |
| conftest.py | text_only（コメント `:214`・`:590`） | 20260917_020000・20261015_090000 |
| test_inbox_new_assignment_badge.py | text_only（SQLite で落ちることを確かめる） | 20261015_090000 |
| test_value_migrations_neutralized.py | text_only（流すのは全テナントを回らない4本だけ） | 20260611_100000・20260613_020000 |
| test_value_migrations_neutralized_3c.py | text_only | 063・069 |
| test_inventory_sprint8_migrations.py | pg_url_only | 069 |
| test_inventory_visibility_permissions.py | pg_url_only | 063 |
| test_leads_assignment_opened_at_pg.py | own_database | 20260729_043520・20261015_090000 |
| test_suppliers_rls.py | own_database | 20260918_030000 |
| test_tcg_condition_review.py | own_database | 20260910_160000・20260917_020000・20260920_010000 |
| test_tcg_extraction_record_pg.py | own_database | 20260914_010000 |
| test_tcg_import_progress_pg.py | own_database | 20260910_010000・20260917_020000 |
| test_tcg_product_list_pg.py | own_database | 20260920_010000 |
| test_tcg_sold_out_results.py | own_database | 20260910_010000・20260917_020000 |
| test_tcg_work_comparison_pg.py | own_database | 20260910_010000 |
| test_tcg_work_matching_integration.py | own_database | 20260910_010000・20260910_160000・20260912_020000・20260914_010000・20260917_010000・20260917_020000・20260920_010000 |

（表ではファイル名の先頭だけ書いた。コードには完全なファイル名を書く。完全な名前は crosscheck の生出力にある）
- 見張りの先頭に、新しく足すときの決まりを日本語2行で書く:「共有 DB で全テナントを回す移行を流すなら `_apply_migration_on_conn(..., schema_name=...)` で絞り、`_TENANT_LOOP_MIGRATIONS` に登録する。絞れないなら使い捨て DB にする」

## 5. 代替案と選んだ理由
| 案 | 結果 | 選んだか |
|---|---|---|
| A 1つのテナントに絞って流す（既にある正本の関数を使う） | 他ワーカーのテナントに触れない。lead_merge・calendar と同じ形 | **選ぶ** |
| B 全テナント共通の札（1つの大きな札）を roles と DROP する全試験で持つ | 札を持たない試験（meta_channels など）が多く、全部に足す必要がある。並列が遅くなる | 選ばない |
| C roles の試験を使い捨て DB にする | 確実だが bootstrap 全体を作り直すので重い。A で足りる | 選ばない |
| D 失敗したら自動でやり直す（rerun） | 落ちる原因が残る。同じ種類のミスを隠す | 選ばない |

## 6. リスクと対処
- `_apply_migration_on_conn` は asyncpg の生接続で流す（`rls_bootstrap.py:205-208`）。`admin_engine.begin()` の中の同じ接続なので、2回流しても1つの transaction のまま（lead_merge と同じ使い方）。
- 回数1がずれる（移行が書き換わる）と `_scope_tenant_migration` が止める → 試験が赤で知らせる（黙って全テナントを回ることは無い）。
- 見張りが既存の試験ファイルの言い回しで誤って当たる → 分類表に `text_only` と理由を書いて通す。表は人（Opus）が審査する。

## 7. 実装の順番（1つの PR・コミットは2つ）
1. 段A: 4-2・4-1・4-3（roles を絞る）
2. 段B: 4-4（見張り）
- 試験は Mac で回さない。CI（GitHub）とクラウドで回す。

## 8. 維持する仕組み
- 見張り `test_tenant_loop_migration_guard.py` は CI の pytest（必須チェック）で毎回走る。新しい試験が全テナントを回す移行を参照すると、分類を書くまでマージできない。
- 正本は `rls_bootstrap.py` の `_TENANT_LOOP_MIGRATIONS` 1か所。見張りはそこを読み、別の一覧を持たない（分類表は「どの試験がどう扱うか」だけ）。
- K5 の数え直しは 2026-11-19 に Opus が行う（記憶 rule_c_reset_after_commit に書く）。

## 9. 外部事例
- Context7 は「Monthly quota exceeded」で使えなかった（2026-11-05）。起動指示の代わりの手段として公式資料を直接読んだ: https://pytest-xdist.readthedocs.io/en/stable/distribution.html（2026-11-05 取得）
  - `--dist loadfile`: "Tests are grouped by their containing file. ... This guarantees that all tests in a file run in the same worker."
  - `-n auto`: "pytest-xdist will use as many processes as your computer has physical CPU cores."
  - 意味: 同じファイルの中の試験は同じワーカーに並ぶが、**別のファイルどうしは別のプロセスで同時に走る**。共有 DB の中のテナントの分け方は試験の側で守る必要がある（xdist はそこを守らない、という記述も、守るという記述も公式ページには無い＝守られない前提で設計する）。
- 数値の外部事例は使わない。今回の根拠は CI ログの実測（recon §1）で足りる。

## 10. 設計審査（同じ AI による自己審査・独立した第二者の審査ではない）
判定: **APPROVE（設計合格）**。PO 承認・マージの承認は兼ねない。

| 観点 | 確かめたこと | 結果 |
|---|---|---|
| 原因と直しの対応 | 失敗した文は roles 移行の `ALTER TABLE tenant_991.roles`（recon §1）。絞った後は `AND nspname = 'tenant_995'` が付き tenant_991 を選ばない（4-3 で機械的に確かめる） | ○ |
| 既存の正本を使うか | 新しい絞り方を作らず `_scope_tenant_migration`・`_apply_migration_on_conn`（`rls_bootstrap.py:175-208`）を使う。一覧は `_TENANT_LOOP_MIGRATIONS` 1か所 | ○ |
| 回数1の正しさ | 実物の `_TENANT_LOOP_SELECTOR_RE` で roles 移行に1回（`81-regex-check.txt`） | ○ |
| 番号 995 が空いているか | 試験・移行の全文でテナント 995 は0件（recon §4） | ○ |
| 札の中で DROP | `tenant_schema_lock` は別の接続で advisory lock を持つ（`rls_bootstrap.py:308-322`）。DROP は別の接続で流すので自分を待たない。今の `admin_engine.connect()` と `begin()` の2本使いと同じ | ○ |
| 冪等の確かめが残るか | 2回流す形はそのまま。確かめの assert は変えない（K2） | ○ |
| 見張りの組の数 | 修正後の実物で 64 組（今の 63 組＋ rls_bootstrap.py に roles を足す1組）。担当は数え直し、64 でなければ止める | ○（自分で数え直して 61→64 に直した） |
| 見張りの過検出 | 文字だけ・コメントは `text_only` と理由で通す。新しい組は必ず落ちる＝審査を通る | ○ |
| 受入条件の検証可能性 | K1〜K4 は CI の PASSED を生ログで読む。K5 は 11/19 にログを grep で数える | ○ |
| 未解決 | 998 の重なり・番号の見張り・TEST_PG_URL だけの2本・pre-commit の範囲（§3 対象外に記録） | 事業判断は不要。次の便で扱う |
