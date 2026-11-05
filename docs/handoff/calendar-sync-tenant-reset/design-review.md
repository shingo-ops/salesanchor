# design-review: 予定を Google に送る処理の会社付け直し漏れ（作成・削除）

- 審査対象: `docs/handoff/calendar-sync-tenant-reset/design.md`・`recon.md`（枝 `release/calendar-sync-tenant-reset`・HEAD 31988c9e6）
- 審査役: architect（製品コードは変えていない。design.md も直していない）
- 審査日: 2026-11-05

## 判定: REVISE

直しの中身（§4 の2行）は正しく、K1〜K3 を満たせる。ただし §5 の試験の土台がこのままでは当てられない（全テナントを回す migration 4本が既存の当て方に登録されていない）こと、テナント番号が既存試験と重なること、§11 の触ってよいファイルに必要な1本が無いことから、実装役が BLOCKED で止まるか、共有 DB で不安定な試験になる。下の「直すべき指摘」R1〜R6 を design.md に入れてから実装へ渡す。

---

## (1) recon C1〜C10 と実物の照合

| # | 結果 | 根拠（実物） |
|---|------|------|
| C1 | 一致 | `backend/app/services/calendar_service.py:271` `await db.commit()` → :272 空行 → :276 `if await can_add_meet(db, tenant_id, user_id):`。間に reset 無し |
| C2 | 一致 | 同 :486 `await db.commit()` → :488 `sync_mode = await _get_sync_mode(db, tenant_id)`。間に reset 無し |
| C3 | **一部不一致** | 挙げた行（calendar_service.py:364-365,403-404,411-412,423-424／google_calendar.py:293-294／routers/calendar.py:301-302,552-553／routers/google_calendar.py:146-147,230-231）はすべて commit 直後に reset あり（grep 生出力で確認）。ただし「ほかの commit はすべて直後に reset」は誤り。calendar_service.py:302（→:303 `except`）と :311（→:312 `meet_url = None`）は reset 無し。両方とも関数の最後の DB 操作で、呼び出し元 `backend/app/routers/calendar.py:365-377` も後で DB を読まずに return するため、今回の不具合には効かない |
| C4 | 一致 | `backend/app/auth/dependencies.py:339-358`（「commit() 後に…別のコネクションが払い出される可能性」） |
| C5 | 一致 | `backend/app/database.py:24-32`（pool_size=20・max_overflow=10） |
| C6 | 一致 | `backend/app/database.py:46-61`（finally で clear_tenant_context）・`dependencies.py:361-380`（`SET app.tenant_id = ''`） |
| C7 | 一致 | `migrations/20261016_010000_add_google_config_rls.sql` 2-9行（ENABLE/FORCE・`NULLIF(current_setting('app.tenant_id', true), '')::INTEGER`）。`git show -s 07f1227f2` → `2026-10-16 feat: Google 接続設定2表を会社別RLSに（ADR-1018 段階②a）` |
| C8 | 一致 | `git show -s 3b35ef7d0` → `2026-05-25 feat: アプリ内カレンダー + Google Calendar 双方向同期`。同 commit の calendar_service.py 追加分に `+    await db.commit()` が7か所 |
| C9 | **行番号不一致** | `scripts/lint_tenant_schema.py:251-262` は router endpoint だけを対象にする判定で一致。ただし `.github/workflows/lint-tenant-schema.yml` は71行しかなく `:440` は存在しない。正しくは :53（変更検知 `^(backend/app/routers/|…)`）と :69（`python3 scripts/lint_tenant_schema.py --mode strict backend/app/routers/`） |
| C10 | 一致（補足あり） | `backend/tests/test_google_config_rls.py:14-64`。`.github/workflows/test.yml:234,236` で RLS_TEST_DATABASE_URL（salesanchor_app）・RLS_ADMIN_DATABASE_URL（jarvis）を渡す。補足: test.yml の起動は PR（main/develop 宛, :4-7）と main/develop への push（:13-16）だけ → R4 |

補足（U2 の手がかり・事実のみ）: F4 の「201・24 バイト」は `{"id":2,"meet_url":null}` の長さ（24文字）と一致する。add_meet=true でも router の事前判定 `routers/calendar.py:359`（commit 前なので設定表が読める）は通り、サービス内の判定（commit 後）で落ちるため、返事の形からは U2 を決められない（未確認のまま）。

## (2) design §4 の2行で K1〜K5 を満たせるか

- 満たせる（K1〜K4）。理由:
  - `set_tenant_context`（`dependencies.py:293-299`）は session レベルの `SET search_path`・`SET app.tenant_id` を接続に入れる。commit で接続が替わると新しい接続には入っていない。`reset_tenant_context`（:339-358）は `set_tenant_context` を呼び直すだけなので、:271 の後に足せば :276 `can_add_meet` → `_get_sync_target`（`calendar_service.py:59-69`）の SELECT が RLS を通り、:292 の UPDATE も search_path でテナント表に当たる。:486 の後に足せば :488 `_get_sync_mode`（:47-56）が読める
  - `reset_tenant_context` は `calendar_service.py:29` で import 済み（一致）
  - 既存の SQLite 試験（K4）: 偽物の db（`AsyncMock()`）では `_dialect_supports_search_path`（`dependencies.py:264-274`）が dialect 名を取れず何もしない。実例として `update_event` は :364-365 で既に commit 直後に reset を呼んでいるが、`backend/tests/test_calendar_service.py:385` は `side_effect=[update_result, geid_result, sync_result]`（3件）のまま通っている＝reset が db.execute を消費しない。create/delete の既存試験（同 :246,:270,:296,:319,:345,:426）も同じ形なので壊れない
- K5 は本番での目視・読み取りで、2行の効果をそのまま確かめる形。妥当
- §7 の「ほかの7か所と同じ」は数が合わない（4ファイルで commit 直後 reset は 9 か所、calendar_service.py 内では 4 か所）。判断には影響しない → R5 で文言を直す

## (3) §5 の試験が「直す前は赤・直した後は緑」になるか

### 赤・緑の理屈（成り立つ）
- app engine を `NullPool` にすると、AsyncSession は commit で接続を返し（=閉じ）、次の execute で新しい接続を開く。新しい接続は `app.tenant_id` 未設定 → `current_setting('app.tenant_id', true)` が NULL → 設定表の RLS（C7）で0行 → `_get_sync_target` が `('none', None)`（`calendar_service.py:69`）→ `can_add_meet` False → 偽物0回・sync_status は 'pending' のまま。試験1は「偽物1回」で赤
- 試験2も同じく `_get_sync_mode` が 'none'（:56）→ :489 の条件が偽 → 偽物0回で赤
- 直した後は reset が新しい接続に SET を入れ直すので両方緑。試験3（つないでいない人）は直す前も後も偽物0回で緑
- 同じ NullPool の作りは既存 `test_google_config_rls.py:57` にある
- 偽物の差し替え先: `calendar_service.py:278,:491` は関数の中で `from app.services import google_calendar as cal_svc` してから属性を呼ぶので、`app.services.google_calendar.create_event`／`delete_event` を patch すれば効く

### migration を既存の当て方で当てられるか（**このままでは当てられない** → R1）
- `tests/rls_bootstrap.py:194-199` `_apply_migration_on_conn(conn, f, schema_name=…)` は、`_TENANT_LOOP_MIGRATIONS`（:157-168）か `selectors`（:179-182）に登録された名前でないと `ValueError("Unknown tenant bootstrap migration")`（:185-186）で止まる
- §5 の7本のうち、全テナントを回すのは4本で、どれも未登録:
  - `078_create_calendar_events_tenant.sql`（:28-33 `WHERE nspname ~ '^tenant_\d+$'`）
  - `20260621_020000_add_schedule_calendar_category_and_owner_settings.sql`（:13-18）
  - `20261103_200000_add_google_calendar_import_sync.sql`（:16。前半 :2-9 は public）
  - `20261104_161223_add_calendar_events_meet_url.sql`（:7）
- `schema_name` を付けずに `_apply_migration` で流すと、CI の共有 DB（`backend/pyproject.toml:65` `-n auto --dist=loadfile`）のすべての tenant_* スキーマを回る。ほかの worker が `bootstrap_tenant_schema`（`rls_bootstrap.py:377` でスキーマを作り直す）を走らせている最中と重なり得て、不安定になる。既存の正しい形は `test_lead_merge_pg.py:52-65,303-309`（登録した migration を `public_bootstrap_lock` の中で `schema_name=` 付きで流す）
- 登録に要る数（`_TENANT_LOOP_SELECTOR_RE` を rls_bootstrap.py から取り出して数えた生出力）:
  ```
  078_create_calendar_events_tenant.sql 2
  20260621_020000_add_schedule_calendar_category_and_owner_settings.sql 1
  20261103_200000_add_google_calendar_import_sync.sql 1
  20261104_161223_add_calendar_events_meet_url.sql 1
  ```
  078 が 2 なのは、末尾の戻し方のコメント（:131）にも同じ条件があるため
- 前提の表: 078 は `role_permissions` があるスキーマだけ作る（:35-40）、20260621_020000 は `staff` を参照（:55）。どちらも `create_tenant_schema` が作る（`backend/app/services/tenant.py:513,:600`）ので、`bootstrap_tenant_schema` の後なら満たす
- 権限: `create_tenant_schema` が `ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA …` で salesanchor_app に表・連番の権限を付ける（`tenant.py:1716-1735`）。admin（jarvis, test.yml:236）で後から作る calendar_events にも効く
- public 側（076・077・20261016・20261103 前半）は `public_bootstrap_lock` の中で `_apply_migration`（既存 `test_google_config_rls.py:60-62` と同じ）でよい

### そのほかの足りない点
- テナント 982 は `backend/tests/test_suppliers_rls.py:39` `_TENANT_A = 982` と重なる（xdist で別 worker が同じスキーマを作り直す）→ R2
- 設定表 `connected_by_user_id`（076 :21）と calendar_events の `user_id`・`created_by_user_id`（078 :46,:63）は `public.users(id)` を参照する。`_ensure_public_users`（`rls_bootstrap.py:250-260`）が入れるのは id=999 だけ → 試験の user 2人を admin で入れる手順が §5 に無い → R3
- `add_meet` を付けると `_resolve_meet_url` が `gcal.get_event` と `asyncio.sleep` を呼び得る（`calendar_service.py:106-112`）→ R6

## (4) create_event・delete_event のほかの reset 漏れ・偽物にすべき Google 呼び出し

- reset 漏れ: §4 の2か所のほかに、両関数内で「commit の後に同じ関数・呼び出し元でまた DB を読む」箇所は無い
  - create_event :302・:311 の commit は関数の最後（:314 return）。呼び出し元 `routers/calendar.py:365-377` も後で DB を読まない
  - create_event の except（:305）の UPDATE は、§4 の reset の後の接続か、`google_calendar.py:293-294`（トークン更新の commit 直後に reset 済み）の後の接続で走るので context はある
  - delete_event は :488 以後、Google 側の `google_calendar.delete_event` だけ（その中の commit も :293-294 で reset 済み）
- Google 呼び出し:
  - create_event: `cal_svc.create_event`（:283・:288）。add_meet のときは `_resolve_meet_url` → `gcal.get_event`（:112）も呼び得る（`hangoutLink` 無し・`statusCode == "pending"` のとき）
  - delete_event: `cal_svc.delete_event`（:493）だけ
  - 偽物は `google_calendar.create_event`／`delete_event`（add_meet なら `get_event` も）を丸ごと差し替えるので、その中の `_get_service`（`google_calendar.py:303`）・トークン復号・通信は動かない
- 範囲外として記録（直さない）: `routers/google_calendar.py:323,:383` は Google 直接の作成・削除で、今回の経路ではない

## (5) 触る範囲と触らない範囲

- 製品コードの範囲（calendar_service.py の2行だけ）・本番データを触らない・migration を足さない、は明確
- 不足: R1 のため `backend/tests/rls_bootstrap.py`（`_TENANT_LOOP_MIGRATIONS` に4行足すだけ）が §11 の触ってよいファイルに無い。このままだと §11 想定分岐 (a) で必ず BLOCKED になる
- 不足: §6 段A「PR（Draft）」の作り手が書かれていない。クラウドの実装役は製品・試験コードを含む PR を作らない決まり（PR は手元で shingo-cc 名義、AGENTS.md「ブランチと作業場所」）。CI は PR か main/develop への push でしか走らない（test.yml:3-16）ので、段A の赤を CI で取るには誰かが PR を作る必要がある → R4

---

## 直すべき指摘（design.md のどこをどう直すか）

| # | 重さ | 節 | 直し方 |
|---|------|----|--------|
| R1 | 必須 | §5「適用する migration」・§11 | 全テナントを回す4本（078・20260621_020000・20261103_200000・20261104_161223）を `backend/tests/rls_bootstrap.py` の `_TENANT_LOOP_MIGRATIONS` に数 2・1・1・1 で登録し、`test_lead_merge_pg.py:303-309` と同じく `public_bootstrap_lock` の中で `_apply_migration_on_conn(conn, f, schema_name=<試験のスキーマ>)` で流す、と書く。public の4本（076・077・20261016・20261103 前半は 20261103 を schema_name 付きで流せば一緒に入る）は `_apply_migration`。順番は 076→077→20261016→（bootstrap_tenant_schema の後）078→20260621_020000→20261103→20261104。§11 の触ってよいファイルに `backend/tests/rls_bootstrap.py`（登録4行だけ）を足す。「当て方が分からなければ止まる」は残してよい |
| R2 | 必須 | §5「テナント」 | 982 は `test_suppliers_rls.py:39` と重なる。既存試験で使っていない番号（grep で未使用を確認した例: 978・979・988・989・990）に変える |
| R3 | 必須 | §5 | admin で `public.users` に試験の user 2人（つないだ本人・ほかの人）を入れ、後始末で消す手順を足す（076 :21・078 :46,:63 の外部キーのため） |
| R4 | 必須 | §6 段A・§11 | 段A の赤の記録の取り方を決める。案: (i) 実装役はクラウドの使い捨て PostgreSQL（localhost）に test.yml:192-215 と同じ salesanchor_app を作り、RLS_ADMIN_DATABASE_URL／RLS_TEST_DATABASE_URL を渡して新しい試験だけ pytest し、段A 赤・段B 緑の生出力を impl-report に残す (ii) CI での K1〜K4 は、PO が手元で shingo-cc 名義の Draft PR を作った後に記録する。どちらで K1 を判定するかを §2 の検証方法にも書く |
| R5 | 軽 | §8・§7 | §8 の根拠 `dependencies.py:24-25` は誤り。正しくは `dependencies.py:264-274`（dialect 判定）・`:293-294`（no-op）。加えて「偽物の db（AsyncMock）でも何もしない。実例: update_event は :364-365 で reset 済みで、`test_calendar_service.py:385` は side_effect 3件のまま通る」を足す。§7 A の「ほかの7か所」は「同じ4ファイルの9か所（calendar_service.py 内は4か所）」に直す |
| R6 | 軽 | §5 試験1 | payload に `add_meet` を入れないと明記する（入れると `get_event`・`asyncio.sleep` が走り得る）。Meet まで確かめたいなら、試験1b として add_meet=True・偽物 create_event が `hangoutLink` 付きを返す形を足し、`meet_url` が保存されることを見る（get_event は呼ばれない） |

recon.md への補足（直しは design 側の判断に影響しない）: C3 の「すべて」は :302・:311 を除く。C9 の `lint-tenant-schema.yml:440` は :53・:69。

## 確かめたコマンド（抜粋）
- `git rev-parse HEAD` → `31988c9e60f0f6dbfde4b353fdf826fb568f7f80`
- `grep -n -A1 "await db.commit()"`（4ファイル）→ 上の C3 の行
- `wc -l .github/workflows/lint-tenant-schema.yml` → `71`
- `git show -s --format='%h %ad %s' --date=short 3b35ef7d0` / `07f1227f2` → 上の C7・C8
- 未使用テナント番号: `backend/tests` を 960〜999 で grep → `960 … 979 988 989 990 992 994 995`

## push 後の記録
`git log --oneline -2`（1回目の push 後）:
```
f3b981967 docs: calendar-sync-tenant-reset の設計審査（REVISE）
31988c9e6 docs: calendar sync tenant-context reset fix design (create/delete)
```

---

## 2回目

- 審査対象: 直した `design.md`・`recon.md`（枝 `release/calendar-sync-tenant-reset`・HEAD 109304a38）
- 審査役: architect（製品コード・design.md は変えていない）
- 審査日: 2026-11-05

### 判定: REVISE

R1〜R6 はすべて design.md に入り、入れた中身も実物と合う。ただし新しく見つけた N1（試験の準備で `20261016_010000_add_google_config_rls.sql` が前提にする表を作る migration が抜けている）は、CI の共有 DB で試験の準備が落ちる・落ちないが実行順で変わる必須の穴。N1 の1行（と N2・N3 の文言）を直せば、ほかに直す所は無い。N1〜N3 だけの直しなら、3回目の審査はその3点の照合だけでよい。

### R1〜R6 の結果

| # | 結果 | design.md の場所 | 実物との照合 |
|---|------|------|------|
| R1 | 反映・合う（引用の行だけ誤り → N2） | §3 対象・§5「土台の登録」「準備の順番」・§8・§11 | 登録の数: `_TENANT_LOOP_SELECTOR_RE`（`backend/tests/rls_bootstrap.py:156`）で数え直した生出力は `078…2`・`20260621_020000…1`・`20261103_200000…1`・`20261104_161223…1` で §5 と一致。数が合わないと :176-177 で ValueError、登録していれば :178 で `AND nspname = 'tenant_978'` を足す。schema_name: `"tenant_978"` は :174 の `tenant_[0-9]+` に合う。lock: `public_bootstrap_lock`（:44-63）は別接続で advisory lock を取り、中で `admin_engine.begin()` の接続に `_apply_migration_on_conn` で流す形は `test_lead_merge_pg.py:303-309` と同じ。076・077・20261016 は schema_name なしで、`_TENANT_BOOTSTRAP_MIGRATIONS`（:35-38）に入っていないので :198-199 で止まらない。前提: 078 :35-40・20260621_020000 :11-18 は `role_permissions` があるスキーマだけ、20260621_020000 は `staff` を参照し、どちらも `bootstrap_tenant_schema`（:340-379）で作られた後に流す順になっている。§11 に `rls_bootstrap.py`（4行だけ）が入った |
| R2 | 反映・合う | §5「テナント」 | `grep -rnE "\b978\b\|97801\|97802\|tenant_978" backend/tests` → 0件。978・97801・97802 はどれも未使用 |
| R3 | 反映・合う（注意1点 → N3） | §5 準備3・後始末 | `_ensure_public_users` の INSERT 列は `rls_bootstrap.py:252-258`（id, tenant_id, firebase_uid, username, email, full_name, role, is_active, is_super_admin, locale, theme）。外部キーは 076 :21（`connected_by_user_id REFERENCES users(id)`）・078 :46,:63（`public.users(id)`）で、どれも ON DELETE SET NULL なので後始末で消してよい |
| R4 | 反映・合う | §2 K1・§6 段A・§11 | 段A は CI（Opus が手元で shingo-cc 名義の Draft PR を作る）で K1 を判定、と §2 の検証方法にも書かれた。クラウドの実装役は PR を作らない、も §11 にある。案(i)（クラウドの使い捨て DB で先に赤を取る）は採らなかったが、R4 は「どちらで判定するかを書く」ことを求めたもので、満たす |
| R5 | 反映・合う | §8・§7 A | `dependencies.py:264` `def _dialect_supports_search_path`〜:274 `return name.startswith("postgresql")`、:293-294 `if not _dialect_supports_search_path(db): return`。`test_calendar_service.py:385` は `side_effect=[update_result, geid_result, sync_result]`。calendar_service.py の commit は :271,302,311,364,403,411,423,486 で、直後に reset があるのは :365,:404,:412,:424 の4か所＝§7 の「うち calendar_service.py 内4か所」と合う |
| R6 | 反映・合う | §5 試験1・試験1b | 試験1は add_meet を入れない（`calendar_service.py:281` の分岐に入らず :288 の create_event だけ）。試験1b: `_resolve_meet_url`（:92）は :97 `url = google_event.get("hangoutLink")` → :98-99 で返るので、:110 `asyncio.sleep`・:112 `gcal.get_event` には届かない。UPDATE（:292-300）は `meet_url` 列を使い、その列は 20261104 で入る（準備の順番に入っている） |

### 新しい指摘

| # | 重さ | 節 | 中身（根拠） | 直し方 |
|---|------|----|------|--------|
| N1 | 必須 | §5 準備2 | `migrations/20261016_010000_add_google_config_rls.sql:11-12` は `ALTER TABLE public.tenant_google_drive_config ENABLE/FORCE ROW LEVEL SECURITY`（IF EXISTS なし）。この表を作るのは `20260606_010000_add_google_drive_config.sql:16` で、§5 の順番に無い。CI は全 migration を先に当てない（`test.yml:192-216` は salesanchor_app を作るだけ）。試験の中でこの表を作るのは `test_google_config_rls.py:45-49` だけで、`pyproject.toml:65` `--dist=loadfile` ではその試験が先に同じ DB で走るかは決まらない。先に走らなければ準備が「relation does not exist」で落ちる | 準備2の順番を 076 → 077 → **`20260606_010000_add_google_drive_config.sql`（schema_name なし）** → 20261016 → 078 → … にする（既存 `test_google_config_rls.py:45-49` と同じ並び） |
| N2 | 軽 | §5「土台」 | 引用 `test_lead_merge_pg.py:58-73,88-93` は誤り。:66-73 は `_PUBLIC_TABLES`・見張りの見出し、:88-93 は `_ALTER_ADD_RE`。全テナント migration をスキーマに限って流す形は :52-65（`_TABLE_MIGRATIONS`）と :303-309（`_apply_table_migrations`） | 行番号を :52-65,303-309 に直す |
| N3 | 軽 | §5 準備3 | `public.users.firebase_uid` は UNIQUE（`rls_bootstrap.py:238`）。`_ensure_public_users` の値 `'test-user'`（:256）をそのまま写すと id=999 の行と重なり、`ON CONFLICT (id)` では受けられず一意違反で落ちる | 「列は同じ、値は firebase_uid・username・email を人ごとに別の値（例 `cal-reset-97801`）にする」と書く |

確かめて問題が無かったこと（記録）:
- 赤・緑の理屈: `set_tenant_context`（`dependencies.py:277-299`）は session レベルの SET を3つ流すだけで、NullPool の app engine では commit 後の新しい接続に入っていない。直す前は `_get_sync_target`（`calendar_service.py:59-69`）・`_get_sync_mode`（:47-56）が RLS で0行 → 試験1・1b・2 は偽物0回で赤、試験3 は前後とも緑、で1回目の (3) と変わらない
- 偽物の差し替え先: `google_calendar.py:377 get_event`・`:390 create_event`・`:430 delete_event`。calendar_service.py は :278・:491 で関数の中で import してから属性を呼ぶので patch が効く。試験2の期待 `(db, 978, 'g-2')` は :493 `cal_svc.delete_event(db, tenant_id, google_event_id)` と合う
- 共有 DB で全テナントを回る migration を流す既存試験は無い: `grep -rn "078_create_calendar\|20261104_161223\|20261103_200000\|20260621_020000" backend/tests` は migration の当てでは0件（別名の backfill スクリプトだけ）

### 確かめたコマンド（抜粋）
- `git rev-parse HEAD` → `109304a38d9ac88d6100da27c787472910f20029`
- rls_bootstrap.py から `_TENANT_LOOP_SELECTOR_RE` を取り出して4本を数えた生出力: `078_create_calendar_events_tenant.sql 2`／`20260621_020000_add_schedule_calendar_category_and_owner_settings.sql 1`／`20261103_200000_add_google_calendar_import_sync.sql 1`／`20261104_161223_add_calendar_events_meet_url.sql 1`
- `grep -n "await db.commit()" backend/app/services/calendar_service.py` → `271 302 311 364 403 411 423 486`
- `grep -rln tenant_google_drive_config migrations` → 20260606_010000（作る）・20261016_010000（ALTER）ほか2本

## 3回目

- 審査対象: 直した `design.md`（枝 `release/calendar-sync-tenant-reset`・HEAD efbd28adc。照合した差分は `git diff 109304a38..efbd28adc -- design.md`）
- 審査役: architect（製品コード・design.md は変えていない）
- 審査日: 2026-11-05
- 範囲: 2回目の取り決めどおり N1〜N3 の3点の照合だけ

### 判定: APPROVE

N1〜N3 はすべて design.md に入り、書かれた行番号・中身は実物と合う。design.md の差分は冒頭の審査の記録1行と §5 の3か所（土台・準備2・準備3）だけで、ほかの節は変わっていない。

### N1〜N3 の照合

| # | 結果 | design.md の場所 | 実物との照合 |
|---|------|------|------|
| N1 | 反映・合う | §5 準備2（:62） | 順番が 076 → 077 → `20260606_010000_add_google_drive_config.sql`（schema_name なし）→ 20261016 → 078 → … になった。`20261016_010000_add_google_config_rls.sql:11-12` は IF EXISTS なしの `ALTER TABLE public.tenant_google_drive_config`、作るのは `20260606_010000_add_google_drive_config.sql:16` `CREATE TABLE IF NOT EXISTS tenant_google_drive_config` で、20261016 より前に流れる。引用 `test_google_config_rls.py:45-49` は `_MIGRATIONS = (` 〜 `)` で 076 → 20260606 → 20261016 の並び＝一致。20260606 は全テナントを回す書き方が無い（`pg_namespace\|nspname\|tenant_%` 0件）・`rls_bootstrap.py` に名前が無い＝`_TENANT_BOOTSTRAP_MIGRATIONS` に入らず、schema_name なしで止まらない。間に挟まる 077 は drive の語0件で、並びの違いは影響しない |
| N2 | 反映・合う | §5「土台」（:53） | 引用が `test_lead_merge_pg.py:52-65,303-309` に直った。:52 `_TABLE_MIGRATIONS = (`〜:65 `)`、:303 `async def _apply_table_migrations`〜:309 `_apply_migration_on_conn(conn, filename, schema_name=_SCHEMA if scoped else None)` で、全テナント migration をスキーマに限って流す形そのもの |
| N3 | 反映・合う | §5 準備3（:63） | firebase_uid・username・email を人ごとに別の値（例 `cal-reset-97801`）にし、`'test-user'` を写さない、と書かれた。`rls_bootstrap.py:238` `firebase_uid VARCHAR(128) UNIQUE`、:256 の id=999 の値が `'test-user'` で一致。UNIQUE は firebase_uid だけ（username・email に UNIQUE なし :239-240）なので、別の値にすれば `ON CONFLICT (id) DO NOTHING` だけで足りる |

### 確かめたコマンド（抜粋）
- `git rev-parse HEAD` → `efbd28adc760ce5fce086c7e76aaa1e872f5b3cf`
- `git diff --stat 109304a38..efbd28adc` → design-review.md +42・design.md 8行（4行入れ替え）
- `grep -n tenant_google_drive_config` 20261016・20260606 → 20261016 :11,:12,:14,:15／20260606 :10（注記）,:16（CREATE）
- `sed -n '40,52p' backend/tests/test_google_config_rls.py`・`sed -n '50,66p;300,312p' backend/tests/test_lead_merge_pg.py`・`sed -n '230,260p' backend/tests/rls_bootstrap.py` で上の行を目で確かめた
- `grep -cE "pg_namespace|nspname|tenant_%" migrations/20260606_010000_add_google_drive_config.sql` → 0、`grep -n 20260606 backend/tests/rls_bootstrap.py` → 0件、`grep -c drive migrations/077_…` → 0
