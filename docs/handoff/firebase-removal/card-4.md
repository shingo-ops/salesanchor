# card: 便4 会社ごとの名簿（staff）から使わない Firebase の列を消す

状態: カード発行（Opus、2026-11-09）。PO の委任（2026-11-07「PRマージ、デプロイまで完走させてくれ」）と指示（2,3 の後に 1＝ログインの残り）による。設計: [design.md](./design.md) §5-4（末尾の「カード作成時の直し」を含む）。根拠: [recon.md](./recon.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番には触らない。PR は作らない（Opus が作る）。
基準: origin/main `bb87bf0b1ed7329ed85f9e38e2a2f97311a68847`。下の行番号はすべてこの時点のもの。行がずれていたら、行番号ではなく「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。
画面（`frontend/`）には触らない。backend のアプリのコード（`backend/app/` のうち `services/tenant.py` 以外）には触らない。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルを §1 で全部挙げた。新しいファイルは migration 1 つ。PR は Opus が作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に変更前と変更後の文を書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED firebase-removal-bin4 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/firebase-removal-bin4` を origin から取り直し、`docs/handoff/firebase-removal/card-4.md` が在ること。
- P2 `git diff --quiet bb87bf0b1ed7329ed85f9e38e2a2f97311a68847 HEAD -- backend migrations scripts` が終了 0（基準から変わっていない）。
- P3 `git grep -n "firebase_uid" -- backend migrations scripts/qa ':!scripts/data_migration' | wc -l` が `31`。
- P4 `ls migrations | sort | tail -1` が `20261108_100000_rebuild_company_stats_on_meta_messages.sql`、かつ `tail -1 scripts/run_all_migrations.sh` が `run_sql migrations/20261108_100000_rebuild_company_stats_on_meta_messages.sql`。
- P5 `sed -n '484p' backend/tests/ops/test_ai_cloud_views.py` が `    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1084`。
- P6 `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の 1 列目が `bb7a4e7b2f3375a4e0706ac670ace68cd61490eeef138c73dfdde2165d8a1b16`。

## 1. 触るファイル
- 新しく作る: `migrations/20261109_200000_drop_staff_firebase_uid.sql`
- `scripts/run_all_migrations.sh`（末尾に 2 行足す）
- `backend/app/services/tenant.py`
- `backend/tests/conftest.py`
- `backend/tests/rls_bootstrap.py`
- `backend/tests/test_calendar_sync_tenant_reset_pg.py`
- `backend/tests/test_export_inventory_for_sheet.py`
- `backend/tests/test_staff_create_users.py`
- `backend/tests/ops/test_ai_cloud_views.py`
- `migrations/20261024_100300_create_ai_cloud_views.sql`
- `scripts/migration-guard/reference-allowlist.tsv`
- `scripts/qa/seed-tenant.sql`

触らない: `migrations/019_create_staff_tables.sql`（過去の記録）、`scripts/data_migration/*`、`scripts/qa/reset-tenant.sh`、`.github/workflows/qa-smoke.yml`（どちらも ADR-1051 D5 で消す）。

## 2. 変更の中身

### 2-1. 新しいファイル `migrations/20261109_200000_drop_staff_firebase_uid.sql`（全文）

```sql
-- firebase-removal 便4: 全テナントの staff から使わない列 firebase_uid を外す（構造のみ・冪等・ADR-1007）
--
-- 設計: docs/handoff/firebase-removal/design.md §5-4
-- 目的: ログインは自社の仕組み（ADR-1013）に替わり、アプリはこの列を読まない。人の正本は public.users.id。
-- 列が無いテナントは飛ばす。もう一度流しても結果は同じ。
-- ビューに使われていれば CASCADE しないので失敗して止まる（黙って消さない）。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（値は戻らない。列だけ戻す）:
--   各 tenant_NNN で ALTER TABLE tenant_NNN.staff ADD COLUMN IF NOT EXISTS firebase_uid VARCHAR(128) UNIQUE;
DO $drop_staff_fuid$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT c.table_schema AS schema_name
        FROM information_schema.columns c
        WHERE c.table_schema ~ '^tenant_[0-9]+$'
          AND c.table_name = 'staff'
          AND c.column_name = 'firebase_uid'
    LOOP
        EXECUTE format('ALTER TABLE %I.staff DROP COLUMN IF EXISTS firebase_uid', r.schema_name);
    END LOOP;
END
$drop_staff_fuid$;
```

### 2-2. `scripts/run_all_migrations.sh`（最後の行の後ろに足す）
```
# firebase-removal 便4: 全テナントの staff から使わない列 firebase_uid を外す（構造のみ・冪等）
run_sql migrations/20261109_200000_drop_staff_firebase_uid.sql
```

### 2-3. `backend/app/services/tenant.py:617` の 1 行を消す
変更前: `    firebase_uid VARCHAR(128) UNIQUE,`（:616 `        CHECK (status IN ('active','inactive','pending')),` の次の行）

### 2-4. `backend/tests/conftest.py:534` の 1 行を消す
変更前: `                firebase_uid VARCHAR(128) UNIQUE,`（:533 `                status VARCHAR(20) NOT NULL DEFAULT 'active',` の次の行）

### 2-5. `backend/tests/rls_bootstrap.py`
- :246 の 1 行を消す。変更前: `                firebase_uid VARCHAR(128) UNIQUE,`（:245 `tenant_id INTEGER NOT NULL DEFAULT 999,` の次）
- :261 と :264 を直す。
  - 変更前 :261: `                id, tenant_id, firebase_uid, username, email, full_name,`
  - 変更後 :261: `                id, tenant_id, username, email, full_name,`
  - 変更前 :264: `            VALUES (999, 999, 'test-user', 'testuser', 'test@example.com', 'Test User',`
  - 変更後 :264: `            VALUES (999, 999, 'testuser', 'test@example.com', 'Test User',`

### 2-6. `backend/tests/test_calendar_sync_tenant_reset_pg.py`
- 変更前 :100: `                    " id, tenant_id, firebase_uid, username, email, full_name,"`
- 変更後 :100: `                    " id, tenant_id, username, email, full_name,"`
- 変更前 :102: `                    " VALUES (:id, :t, :fuid, :uname, :email, 'Cal Reset', 'admin',"`
- 変更後 :102: `                    " VALUES (:id, :t, :uname, :email, 'Cal Reset', 'admin',"`
- :109 の 1 行を消す。変更前: `                    "fuid": f"cal-reset-{uid}",`

### 2-7. `backend/tests/test_export_inventory_for_sheet.py`
- 変更前 :75: `                    "INSERT INTO public.users (firebase_uid, email, name, is_active, is_super_admin) "`
- 変更後 :75: `                    "INSERT INTO public.users (email, name, is_active, is_super_admin) "`
- 変更前 :76: `                    "VALUES (:uid, :email, :n, TRUE, TRUE) RETURNING id"`
- 変更後 :76: `                    "VALUES (:email, :n, TRUE, TRUE) RETURNING id"`
- :79 の 1 行を消す。変更前: `                    "uid": f"export_test_op_{tag}",`

### 2-8. `backend/tests/test_staff_create_users.py`
関数の名前と、API に `firebase_uid` を送る所（:161・:232）、応答に無いことの確かめ（:166・:235）は残す。DB の列を読む所だけを「列が無いこと」の確かめに替える。
- 変更前 :167-170:
```
    row = (await db_session.execute(text(
        "SELECT primary_email, firebase_uid FROM staff WHERE id = :id"), {"id": body["id"]})).mappings().first()
    assert row["primary_email"] is None
    assert row["firebase_uid"] is None
```
- 変更後:
```
    row = (await db_session.execute(text(
        "SELECT primary_email FROM staff WHERE id = :id"), {"id": body["id"]})).mappings().first()
    assert row["primary_email"] is None
    staff_cols = [r[1] for r in (await db_session.execute(text("PRAGMA table_info(staff)"))).all()]
    assert "firebase_uid" not in staff_cols  # 列そのものが無い（便4）
```
- 変更前 :236-238:
```
    stored = (await db_session.execute(text(
        "SELECT firebase_uid FROM staff WHERE id = :id"), {"id": staff_id})).scalar()
    assert stored is None
```
- 変更後:
```
    staff_cols = [r[1] for r in (await db_session.execute(text("PRAGMA table_info(staff)"))).all()]
    assert "firebase_uid" not in staff_cols  # 列そのものが無い（便4）
```
（この試験は SQLite の足場で流れる。`backend/tests/conftest.py:18`）

### 2-9. `migrations/20261024_100300_create_ai_cloud_views.sql`
- :544 の配列から `'firebase_uid',` を外す。
  - 変更前: `  ('tenant_*','staff',ARRAY['discord_user_id','firebase_uid','given_name_en',`（行の頭の部分。行の残りはそのまま）
  - 変更後: `  ('tenant_*','staff',ARRAY['discord_user_id','given_name_en',`
- :3 の `1084 行` を `1083 行` にする。

### 2-10. `backend/tests/ops/test_ai_cloud_views.py`
- :484 の `== 1084` を `== 1083` にする。
- :556 の 1 行を消す。変更前: `            ("public", "users", "firebase_uid"),`

### 2-11. `scripts/migration-guard/reference-allowlist.tsv:7`
- 2 列目のハッシュを、2-9 の後の `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の 1 列目に替える。
- 4 列目（decision_ref）の最後に ` / firebase-removal card-4（分類1列削除）` を足す。
- 列の区切りはタブのまま。ほかの列は変えない。

### 2-12. `scripts/qa/seed-tenant.sql`
- :21-23 の 3 行（`--   :qa_admin_firebase_uid` で始まる行・`--   :qa_staff_firebase_uid`・`--   :qa_viewer_firebase_uid`）を消す。
- :109・:114・:119 の 3 行の最後の `, firebase_uid)` を `)` に替える。
- :110・:115・:120 の 3 行の最後の `, :'qa_admin_firebase_uid'`・`, :'qa_staff_firebase_uid'`・`, :'qa_viewer_firebase_uid'` を消す（`'active'` で終わる形にする）。

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/firebase-removal-bin4 && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P6 を流し、結果をそのまま報告に貼る
    cd ~/sa && ls docs/handoff/firebase-removal/card-4.md | tail -1
    cd ~/sa && git diff --quiet bb87bf0b1ed7329ed85f9e38e2a2f97311a68847 HEAD -- backend migrations scripts; echo "P2 exit=$?"
    cd ~/sa && git grep -n "firebase_uid" -- backend migrations scripts/qa ':!scripts/data_migration' | wc -l | tail -1
    cd ~/sa && ls migrations | sort | tail -1 && tail -1 scripts/run_all_migrations.sh
    cd ~/sa && sed -n '484p' backend/tests/ops/test_ai_cloud_views.py | tail -1
    cd ~/sa && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql | tail -1

手順3 §2 の変更をする（2-1 から 2-12 の順。1 つのファイルの中は下の行から直すと行番号がずれない。2-11 は 2-9 の後）

手順4 残りの文字の確かめ
    cd ~/sa && git grep -n "firebase_uid" -- backend migrations scripts/qa ':!scripts/data_migration' | tail -20
期待: 次の 4 つのファイルの行だけ、計 17 行。
- `migrations/019_create_staff_tables.sql` の 2 行（:51・:70）
- `backend/tests/test_staff_create_users.py` の 8 行（関数名 2 行・API に送る 2 行・応答の確かめ 2 行・新しく足した確かめ 2 行）
- `scripts/qa/reset-tenant.sh` の 3 行（:120-122）
- `migrations/20261109_200000_drop_staff_firebase_uid.sql` の 4 行（1 行目の注記・ロールバックの注記・`column_name = 'firebase_uid'`・`EXECUTE format(...)`）
この形と違う行が出たら §4。

手順5 形の確かめ
    cd ~/sa && bash -n scripts/run_all_migrations.sh && echo "bash OK" | tail -1
    cd ~/sa && python3 -m py_compile backend/tests/conftest.py backend/tests/rls_bootstrap.py backend/tests/test_calendar_sync_tenant_reset_pg.py backend/tests/test_export_inventory_for_sheet.py backend/tests/test_staff_create_users.py backend/tests/ops/test_ai_cloud_views.py backend/app/services/tenant.py && echo "py OK" | tail -1
    cd ~/sa && awk -F'\t' 'NR==7{print NF}' scripts/migration-guard/reference-allowlist.tsv | tail -1
期待: `bash OK`・`py OK`・`4`。

手順6 ハッシュの確かめ
    cd ~/sa && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql | cut -d' ' -f1 | tail -1 && awk -F'\t' 'NR==7{print $2}' scripts/migration-guard/reference-allowlist.tsv | tail -1
期待: 2 行が同じ。

手順7 記録の検査（あれば流す。無ければ「無し」と報告して進む）
    cd ~/sa && (python3 scripts/check-migration-value-writes.py repo 2>&1 || echo "value-writes exit=$?") | tail -5
    cd ~/sa && (bash scripts/check-migration-registration-exists.sh 2>&1 || node scripts/check-migration-registration-exists.js 2>&1 || echo "registration check を流せない") | tail -5

手順8 試験を流す（SQLite で流れる名簿の試験だけ。PostgreSQL の試験は CI で流れる）
    cd ~/sa/backend && pip install -q -r requirements.txt 2>&1 | tail -2; python3 -m pytest -q tests/test_staff_create_users.py 2>&1 | tail -6
期待: 全部合格。

手順9 変わったファイルを確かめる
    cd ~/sa && git status --short | tail -20 && git diff --stat | tail -3
期待: §1 の 12 ファイルだけ（新しいファイルは `??` で 1 つ）。

手順10 記録して送る
    cd ~/sa && git add migrations/20261109_200000_drop_staff_firebase_uid.sql scripts/run_all_migrations.sh backend/app/services/tenant.py backend/tests/conftest.py backend/tests/rls_bootstrap.py backend/tests/test_calendar_sync_tenant_reset_pg.py backend/tests/test_export_inventory_for_sheet.py backend/tests/test_staff_create_users.py backend/tests/ops/test_ai_cloud_views.py migrations/20261024_100300_create_ai_cloud_views.sql scripts/migration-guard/reference-allowlist.tsv scripts/qa/seed-tenant.sql && git commit -q -m "feat(db): drop unused staff.firebase_uid from all tenants (firebase-removal bin4)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/firebase-removal-bin4 2>&1 | tail -3

## 4. 想定される分かれ道

BLOCKED: に入ったら、その場で作業を停止し、それまでの出力と §5 の形の報告を返して終わる（直さずに先へ進まない・別のやり方を試さない）。

- P1〜P6 のどれかが外れた → 実装せず `BLOCKED: P番号 と見えたもの`。
- 変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名と行 変更前の文が一致しない`。
- 手順4 で期待と違う行が出た → 行をそのまま報告し、§2 の書き漏れか、§1 の触らない所かを書いて `BLOCKED: 残り`。
- 手順5・6 が期待と違う → 出力を報告し、§2 のとおりに直せるなら直してもう一度流す。直らなければ `BLOCKED: 形`。
- 手順7 の検査が見つからない → 「無し」と報告して進む。検査が赤 → 出力の最後の 15 行を報告して `BLOCKED: 検査名`。
- 手順8 で pip が失敗して試験を流せない → 「流せない」と最後の 5 行を報告して進む（CI で流れる）。試験が赤 → 赤の試験名と最後の 15 行を報告して `BLOCKED: 試験名`。
- push が拒まれた → 出力の最後の 3 行を報告して `BLOCKED: push`（force はしない）。

## 5. 報告の形

- 1 行目: 受領確認（`RECEIVED firebase-removal-bin4 HEAD=…`）。
- 手順2・4〜10 の出力（tail の範囲）をそのまま貼る。
- §4 の分かれ道に入ったら、どれに入ったかと見えたもの。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
