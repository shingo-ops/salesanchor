# 実装カード 便4: 古い移行 037 が contacts の status CHECK を足し直すのを止める

- 設計: [design.md](design.md) §15（K16・K17・K13 後半・K2）。前提の事実は §15-2。
- PO の実装承認: 2026-11-12 のセッション冒頭の依頼「PRマージ、デプロイまで完走させてくれ」と、同日の「11」（古い移行の直しを設計から始める）。本番への反映は「GO #PR番号」が要る（migrations を含む・ADR-135/136。GO は ADR-1003 の委任で Opus が出す）。
- ブランチ: `release/status-ssot-m037-skip`（Opus がこのカードを積んで push 済み）。この枝の上に積んで push する。PR は作らない（Opus が作る）。
- 試験は Mac で流さない。PostgreSQL の試験はクラウドで skip になるので CI で確かめる。行番号は origin/main a3e93f053。
- 変えるのは下の2ファイルだけ。便2 の migration・tenant.py・run_all_migrations.sh・workflow は変えない。

## やること（この順）

1. 作業場所: `git fetch origin && git switch release/status-ssot-m037-skip`。`./scripts/dev/executor-preflight.sh` を流し、生出力を報告に貼る。クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして先へ進む。[3/3] と [4/4] が OK でなければ `BLOCKED:`。台帳の札は作らない（Opus が作る）。
2. `migrations/037_add_pending_dedup_review_to_contacts_check.sql`:
   - (a) 先頭の注釈の `-- 作成日: 2026-04-27 (PR #163 Critical fix)` の行の直後に、次の3行を足す:
     ```
     -- 追記 2026-11-12（ADR-1076 便4・docs/handoff/status-ssot-contact-company/design.md §15）:
     --   contacts.status が外部キー contacts_status_fkey で結ばれた領域は何もしない。
     --   値の決まりは外部キーの先の表が持つ。CHECK を足すと便2 の移行が毎回外し直すため。
     ```
   - (b) DECLARE の `skipped_no_table INTEGER := 0;       -- contacts テーブルが無いスキーマ` の直後に1行足す:
     ```
         skipped_fk INTEGER := 0;             -- contacts.status が外部キーで結ばれている（便4・no-op）
     ```
   - (c) ループの中、contacts の表が無いときの `END IF;`（今の `:71`）の直後に、空行1つと次を足す:
     ```
             -- 便4（design.md §15）: 外部キー contacts_status_fkey があれば CHECK は要らないので何もしない
             IF EXISTS (
                 SELECT 1 FROM pg_constraint con
                 JOIN pg_class cls ON cls.oid = con.conrelid
                 JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
                 WHERE nsp.nspname = schema_rec.nspname
                   AND cls.relname = 'contacts'
                   AND con.contype = 'f'
                   AND con.conname = 'contacts_status_fkey'
             ) THEN
                 skipped_fk := skipped_fk + 1;
                 CONTINUE;
             END IF;
     ```
     この行に外部キーの先の表の名前を書かない（protected-tables.txt にある名前は、足した行に出ると確認8 が止める・design.md §15-3）。
   - (d) 最後の RAISE NOTICE（今の `:147-149`）を次に変える:
     ```
         RAISE NOTICE
             'migration 037: 完了。新規追加 % テナント、既存対応済 % テナント、外部キー済 % テナント、contacts 未存在 % テナント',
             applied_count, skipped_already_ok, skipped_fk, skipped_no_table;
     ```
   - 他の行（DROP・ADD・下のロールバックの注釈）は変えない。
3. `backend/tests/test_customer_statuses_pg.py` の末尾に、次の2つの関数と試験1つを足す（既存の試験・`_fresh()` は変えない）:
   ```python
   async def _status_fkey_oids(admin_engine) -> dict[str, int]:
       from sqlalchemy import text

       async with admin_engine.connect() as conn:
           rows = (
               await conn.execute(
                   text(
                       "SELECT con.conname, con.oid FROM pg_constraint con "
                       "JOIN pg_namespace nsp ON nsp.oid = con.connamespace "
                       "WHERE nsp.nspname = :s AND con.contype = 'f' "
                       "AND con.conname IN ('companies_status_fkey', 'contacts_status_fkey')"
                   ),
                   {"s": _SCHEMA},
               )
           ).all()
       return {r[0]: int(r[1]) for r in rows}


   async def _status_check_count(admin_engine) -> int:
       from sqlalchemy import text

       async with admin_engine.connect() as conn:
           return (
               await conn.execute(
                   text(
                       "SELECT count(*) FROM pg_constraint con "
                       "JOIN pg_class cls ON cls.oid = con.conrelid "
                       "JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace "
                       "WHERE nsp.nspname = :s AND cls.relname IN ('companies', 'contacts') "
                       "AND con.contype = 'c' "
                       "AND pg_get_constraintdef(con.oid) ILIKE '%status%' "
                       "AND pg_get_constraintdef(con.oid) NOT ILIKE '%trust_level%'"
                   ),
                   {"s": _SCHEMA},
               )
           ).scalar_one()


   async def test_k16_rerunning_037_and_fk_migration_changes_nothing():
       """デプロイのたびに全 migration を流し直しても、037 は CHECK を足さず、便2 は外部キーを付け直さない（design.md §15-4）。"""
       from tests.rls_bootstrap import _apply_migration

       async with _fresh() as (admin_engine, _app_engine, _lead_id):
           before = await _status_fkey_oids(admin_engine)
           assert set(before) == {"companies_status_fkey", "contacts_status_fkey"}
           assert await _status_check_count(admin_engine) == 0
           for _ in range(2):
               await _apply_migration(admin_engine, "037_add_pending_dedup_review_to_contacts_check.sql")
               assert await _status_check_count(admin_engine) == 0
               await _apply_migration(admin_engine, "20261112_140000_customer_status_fk.sql")
               assert await _status_fkey_oids(admin_engine) == before
               assert await _status_check_count(admin_engine) == 0
   ```
4. 確かめ（クラウドで・生出力を報告に貼る）:
   - `git diff --stat origin/main...HEAD` が、このカード・design.md と上の2ファイルだけ。
   - `python3 scripts/check-migration-value-writes.py repo` の終了コードと末尾。
   - `python3 -m py_compile backend/tests/test_customer_statuses_pg.py` が0。
   - PostgreSQL が使えるなら（`RLS_ADMIN_DATABASE_URL` と `RLS_TEST_DATABASE_URL` がある）`cd backend && python -m pytest tests/test_customer_statuses_pg.py -q` を流す。さらに 2(c) の IF ブロックを一時的に消して同じ試験が落ちることを確かめ、元に戻す（消したまま commit しない）。PostgreSQL が無ければ「skip・CI で確かめる」と書く。
5. commit（文は `fix(migrations): 037 は contacts に外部キーがあれば CHECK を足さない（ADR-1076 便4）`）して push。最後の行は `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。

## 想定される分岐

- 2(c) の `END IF;` が `:71` に無い（行がずれている）: 「contacts テーブルが存在すること」の IF の `END IF;` の直後に足す。見つからなければ `BLOCKED:`。
- `_fresh()` の領域で、試験の最初の2つの assert が落ちる（tenant.py の表の形に status の CHECK が残っている等）: 直さずに `BLOCKED:` と、落ちた値を書く。
- check-migration-value-writes.py が 037 の足した行で止まる: 止めた行と理由を生のまま貼って `BLOCKED:`。言い換えて回避しない。
