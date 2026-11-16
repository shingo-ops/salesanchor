# 実装カード 便2: 会社と連絡先の status 列を表 public.customer_statuses に外部キーで結ぶ

- 設計: [design.md](design.md) §5・§5-2・§8 K2/K3/K10/K13（設計 PR #5419 で審査 APPROVE）。調査: [recon.md](recon.md)。
- 前提（済み・事実）: 便1 PR #5422 で表を本番に作った（2026-11-12 07:24 の移行で実行）。4行は 2026-11-12 に PO が `run-insert.sh` で本番に入れ、読み取り鍵で4行を確かめた（active/inactive/archived/pending_dedup_review）。本番の会社・連絡先は5つの会社の領域で合計105行、すべて `active`。旧 CHECK は10本（tenant_001/003/004/005/006 × companies/contacts）、外部キーは0本。
- PO の実装承認: 2026-11-12 のセッション冒頭の依頼「PRマージ、デプロイまで完走させてくれ」。本番への反映は「GO #PR番号」が要る（migrations を含むため・ADR-135/136。GO は ADR-1003 の委任で Opus が出す）。
- ブランチ: `release/status-ssot-bin2`（Opus がこのカードを積んで push 済み）。この枝を取り込んで、その上に積む。PR は作らない（Opus が作る）。
- 試験は Mac で流さない。CI で確かめる。行番号は origin/main 9747e2cf1。
- この便では画面・API は変えない（便3）。`scripts/migration-guard/protected-tables.txt` も変えない（便3）。

## やること（この順）

1. 作業場所: `git fetch origin && git switch release/status-ssot-bin2`（クラウドの写しで）。`./scripts/dev/executor-preflight.sh` を流し、生出力を報告に貼る。クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして先へ進む。[3/3] と [4/4] が OK でなければ `BLOCKED:`。台帳の札はクラウドでは作らない・commit しない（Opus が手元で作る）。
2. 新しい migration `migrations/20261112_140000_customer_status_fk.sql` を作る。中身は下の「migration の中身」を1文字も変えずに使う（`20261112_130000` は別テーマが使用済みなので 140000）。
3. `scripts/run_all_migrations.sh` の最後の `run_sql`（今は `run_sql migrations/20261112_130000_add_viewer_contracting_status.sql`）の後ろに、注釈1行 `# 会社と連絡先の状態 便2: status 列を public.customer_statuses に外部キーで結び、旧 CHECK を外す（済みの領域は飛ばす・冪等）` と `run_sql migrations/20261112_140000_customer_status_fk.sql` を足す。
4. `backend/app/services/tenant.py`（新しい会社を作るときの表の形）:
   - `:223-224`（companies）と `:254-255`（contacts）の
     ```
     status VARCHAR(20) NOT NULL DEFAULT 'active'
         CHECK (status IN ('active','inactive','archived','pending_dedup_review')),
     ```
     をどちらも次に変える（名前は付けない。自動で付く `companies_status_fkey`／`contacts_status_fkey` が migration の名前と同じになる）:
     ```
     status VARCHAR(20) NOT NULL DEFAULT 'active'
         REFERENCES public.customer_statuses(code),
     ```
   - `:251-253` の注釈（`PR #163 … 4 値を許容する。`）を次の2行に変える:
     ```
     -- 状態の記号は public.customer_statuses の4行が正本（ADR-1076・便2）。
     -- companies.status と同じく外部キーで結ぶ（値の一覧をここに書かない）。
     ```
   - 他の行は変えない。
5. `backend/tests/seed_data.py` に関数を1つ足す（`country_seed_sql` の近く）:
   ```python
   def customer_statuses_seed_sql() -> str:
       """public.customer_statuses の4行。値は docs/handoff/status-ssot-contact-company/insert-customer-statuses.sql が正本（ここに値を書かない・ADR-1076）。"""
       return (Path(__file__).resolve().parents[2] / "docs" / "handoff" / "status-ssot-contact-company" / "insert-customer-statuses.sql").read_text("utf-8")
   ```
   `Path` は既に import 済みか確かめ、無ければ足す。
6. `backend/tests/rls_bootstrap.py`:
   - `:36` の `_PG_AFTER_TENANTS_MIGRATIONS` に `"20261112_120000_create_public_customer_statuses.sql"` を足す（タプルの2つ目）。**design.md §5-2 は `_PG_BOOTSTRAP_MIGRATIONS` と書いているが、そこは BEGIN/COMMIT を除かずに取引の中で流すため、便1 の migration（BEGIN/COMMIT あり）は入れられない。BEGIN/COMMIT を除いて流す `_PG_AFTER_TENANTS_MIGRATIONS` に入れる（Opus 判断・設計との差）。**
   - `bootstrap_tenant_schema` の中、`for filename in _PG_AFTER_TENANTS_MIGRATIONS:` のループ（今は `:360-362`）の直後・`INSERT INTO public.tenants` の前に、次を足す:
     ```python
                 # 状態の4行（便2 で tenant.py の status が外部キーで指す・ADR-1076）。書けるのは運営だけ
                 await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
                 await conn.exec_driver_sql(customer_statuses_seed_sql())
                 await conn.execute(text("SELECT set_config('app.is_operator', '', true)"))
     ```
     `customer_statuses_seed_sql` を `tests.seed_data` からの import に足す（既存の import 行にそろえる）。
7. 新しい試験 `backend/tests/test_customer_statuses_pg.py`（PostgreSQL・RLS）。形は `backend/tests/test_tenant_login_requests.py:72-82` と `backend/tests/test_channel_masters_shared_pg.py` にそろえる（使い捨て DB・`bootstrap_tenant_schema(admin_engine, <会社番号>)`・環境変数が無ければ skip）。会社番号は他の試験と重ならない番号（例 978）を `git grep -n '_TENANT_.* = 97\|_TA = \|_TB = ' backend/tests` で確かめて選ぶ。試験は次の3つ:
   - K10: アプリ接続役（NOBYPASSRLS）で `app.tenant_id` を付け、`tenant_NNN.companies` に `status='active'` の行を入れて成功する。続けて同じ会社に `contacts` を `status='pending_dedup_review'` で入れて成功する（必須列は tenant.py の表の形を見て最小限を埋める）。
   - K3: 同じ役で `status='no_such_status'` の会社を入れると外部キー違反（`ForeignKeyViolationError` か `IntegrityError`、SQLSTATE 23503）で断られる。contacts も同じ。
   - 結び目の確かめ: 管理役で `pg_constraint` を読み、その会社の領域に `companies_status_fkey` と `contacts_status_fkey` があり（contype='f'・convalidated=true）、`companies_status_check` と `contacts_status_check` が無い。
8. `.github/workflows/migration-test.yml`: 「変更 SQL の前提の移行を先に実行（Google カレンダーの通知の登録の表）」の step の後ろ・「変更 SQL を 1回目実行」の前に、次の step を足す（前の step と同じ形）:
   ```yaml
         - name: 変更 SQL の前提の移行を先に実行（会社と連絡先の状態の表）
           if: steps.detect.outputs.has_sql_changes == 'true' && contains(steps.detect.outputs.changed_sql, 'migrations/20261112_140000_customer_status_fk.sql')
           run: |
             # 20261112_140000 は public.customer_statuses（20261112_120000）を外部キーで指すので、その表を本番と同じ順で先に作る
             for sqlfile in migrations/20261112_120000_create_public_customer_statuses.sql; do
               echo "▶ $sqlfile を前提として実行中..."
               psql -h localhost -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -f "$sqlfile"
               echo "✅ $sqlfile 成功"
             done
   ```
   この job の土台の `tenant_001.companies` には status 列が無いので、migration は飛ばすだけで4行は要らない。
9. `.github/workflows/schema-check.yml`: 「Create minimal public schema」の step（今は `:110-158`）の後ろ・「Seed permissions master」の前に、次の step を足す（tenant.py の外部キーの参照先。前例は同じファイルの public.products の追加 `:142-146`）:
   ```yaml
         # public.customer_statuses（tenant_NNN.companies / contacts の status の外部キーの参照先・ADR-1076 便2）
         # 表は本物の migration で作り、4行は正本の SQL ファイルから入れる（値をここに書かない）
         - name: Create customer statuses master
           env:
             PGPASSWORD: testpass
           run: |
             psql -h localhost -U jarvis -d jarvis_schema_check_db -v ON_ERROR_STOP=1 \
               -f migrations/20261112_120000_create_public_customer_statuses.sql
             { echo "BEGIN;"; echo "SET LOCAL app.is_operator = 'true';"; cat docs/handoff/status-ssot-contact-company/insert-customer-statuses.sql; echo "COMMIT;"; } \
               | psql -h localhost -U jarvis -d jarvis_schema_check_db -v ON_ERROR_STOP=1
   ```
   インデントは前後の step にそろえる（実物を見て合わせる）。
10. 提出前: `bash scripts/dev/check-before-submit.sh` を流し、生の結果をファイルに残してパスを報告する。
11. commit（1つでよい。題は `feat(db): 会社と連絡先の status を状態の表に外部キーで結ぶ（便2）`。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git push origin release/status-ssot-bin2`。

## migration の中身

```sql
-- 会社と連絡先の状態 便2: status 列を public.customer_statuses に外部キーで結び、旧 CHECK を外す
--
-- 設計: docs/handoff/status-ssot-contact-company/design.md §5（ADR-1076）
-- 全会社の領域（tenant_NNN）の companies・contacts で: 外部キーを NOT VALID で足す → VALIDATE → 旧 CHECK を外す。
-- 止め役は VALIDATE そのもの: 会社・連絡先の status に表に無い値があれば外部キー違反で失敗し、移行全体が止まる（4行の投入前に流すと止まる）。
-- 表や status 列が無い領域は飛ばす。外部キーが有効で旧 CHECK が無い領域は飛ばす（流し直しで ALTER を出さない・鍵を取りに行かない）。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）
--
-- ロールバック（領域ごと・PO GO）: docs/handoff/status-ssot-contact-company/card-bin2.md「戻し方」

DO $fk$
DECLARE
    _schema TEXT;
    _tbl    TEXT;
    _fk     TEXT;
    _chk    TEXT;
    _valid  BOOLEAN;
BEGIN
    FOR _schema IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' ORDER BY nspname
    LOOP
        FOREACH _tbl IN ARRAY ARRAY['companies', 'contacts']
        LOOP
            _fk  := _tbl || '_status_fkey';
            _chk := _tbl || '_status_check';

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = _schema AND table_name = _tbl AND column_name = 'status'
            ) THEN
                RAISE NOTICE 'customer_status_fk: %.% に status 列が無いので飛ばす', _schema, _tbl;
                CONTINUE;
            END IF;

            _valid := NULL;
            SELECT con.convalidated INTO _valid
            FROM pg_constraint con
            WHERE con.conrelid = format('%I.%I', _schema, _tbl)::regclass
              AND con.conname = _fk;

            IF _valid IS TRUE AND NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = format('%I.%I', _schema, _tbl)::regclass AND conname = _chk
            ) THEN
                CONTINUE;
            END IF;

            IF _valid IS NULL THEN
                EXECUTE format(
                    'ALTER TABLE %I.%I ADD CONSTRAINT %I FOREIGN KEY (status) REFERENCES public.customer_statuses (code) NOT VALID',
                    _schema, _tbl, _fk);
            END IF;
            IF _valid IS NOT TRUE THEN
                EXECUTE format('ALTER TABLE %I.%I VALIDATE CONSTRAINT %I', _schema, _tbl, _fk);
            END IF;
            EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I', _schema, _tbl, _chk);
            RAISE NOTICE 'customer_status_fk: %.% を外部キーに付け替えた', _schema, _tbl;
        END LOOP;
    END LOOP;
END $fk$;
```

## 戻し方（PR 本文にも写す。本番で使うときは PO GO）

領域ごと・表ごとに（例 tenant_004.companies）:

```sql
ALTER TABLE tenant_004.companies DROP CONSTRAINT IF EXISTS companies_status_fkey;
ALTER TABLE tenant_004.companies ADD CONSTRAINT companies_status_check
    CHECK (status IN ('active','inactive','archived','pending_dedup_review'));
```

contacts は `contacts_status_fkey` / `contacts_status_check` で同じ。アプリのコードは tenant.py を git revert で戻す。表 public.customer_statuses と4行は残す。

## 触らない

- `frontend/` 全部・`backend/app/` の tenant.py 以外・`backend/tests/conftest.py`（SQLite の表は変えない・design §5-2）。
- 既存の migration（便1 の `20261112_120000` を含む）・`deploy.yml`・`.github/workflows/workflow-lint.yml`。
- `scripts/migration-guard/protected-tables.txt`（便3）・`docs/`（このカードを含め全部。Opus が直す）。
- migration に INSERT・UPDATE・DELETE・件数の SELECT・RAISE EXCEPTION を書かない（design §5・審査3回目 M1）。

## 想定される分かれ道

- 行番号がずれている（本線が進んだ）→ 文字で場所を探す。中身がカードと違えば止めて `NEEDS_DECISION:` で報告する。
- `run_all_migrations.sh` の最後の `run_sql` が `20261112_130000` でない → 今の最後の後ろに足し、そのファイル名を報告に書く。`20261112_140000` が既にあれば止めて `NEEDS_DECISION:`。
- `check-before-submit.sh` の migration の検査（値の書き込み・参照先の一覧・確認8 等）が止める → 直さずに止めて、生の結果を付けて `BLOCKED:`。
- `exec_driver_sql` が先頭の注釈つきの SQL で失敗する見込みがあっても、Mac で試さない。CI の結果を Opus が見る。
- `bootstrap_tenant_schema` の接続が書き込みの RLS で断られる形が読み取れたら（set_config で足りない）→ 止めて `NEEDS_DECISION:`。
- 見張りに止められた → 言い換えずに `BLOCKED:` で止める。
- 変更ファイルは 8 つ（新しい migration・run_all_migrations.sh・tenant.py・seed_data.py・rls_bootstrap.py・test_customer_statuses_pg.py・migration-test.yml・schema-check.yml）。違えば報告に理由を書く。

## 終わりの報告

- 最後の行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 問い`。HEAD の sha・変更ファイル一覧（`git diff --name-only origin/main...HEAD`）・各検査の終了コードを付ける。
