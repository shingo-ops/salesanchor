# 設計の審査（architect 第2回）: schedule-settings 便3a

- 審査した物: `origin/release/schedule-settings-bin3`（583e8d656）の `docs/handoff/schedule-settings/design-bin3a.md`（以下「設計」）
- 第1回の結果: `origin/release/schedule-settings-bin3a-review1` の `docs/handoff/schedule-settings/review-architect-bin3a-1.md`（R1〜R6・L1〜L9）
- 照らした実物: `origin/main` 314eeef1e（行番号は全部この版）
- 範囲: 読むだけ。製品のコード・DB・本番・secrets には触っていない。試験・検査は 1 本も流していない（下の事実は全部ファイルを読んで確かめた物。「落ちる」は検査の定義を読んで導いた物で、実行はしていない）

## 判定: REVISE

1. 第1回の R1〜R6・L1〜L9 は設計に正しく入っている（下の対応表）。ひな形と移行の `color_key text`＋同じ CHECK の決めも、`tenant-template-shape` では差 0 になる。ただし、この比べは**この変更では中身を比べない**（下の L2）。
2. 直した所が生んだ食い違いが 1 件ある。F10 / §5 の「`_REVIEWED` は新しい試験ファイルごとに 1 項」だけでは足りない。新しい移行の名前は `rls_bootstrap.py` と `test_calendar_sync_tenant_reset_pg.py` の文字にも出るので、この 2 つの既存項に名前を足さないと `test_tenant_loop_migration_guard.py` が落ちる（R1）。第1回 R4 が「`:53`・`:74` は足す」と書いた所を、設計は「`:83` を外す」だけ取り込んで落とした。
3. 受け入れ条件 A1〜A9 は R1 を直せば全部検証できる。A5 の命令は正しく拾うようになったが、設計が書く「今の拾う場所」に実物と合わない行がある（L1）。REJECT の理由は無い。

## 第1回の指摘が設計に入ったかの対応表（1 件ずつ実物で照らした）

| 指摘 | 設計の場所 | 実物との照合 | 結果 |
|---|---|---|---|
| R1 openapi.json | §3-2・§10 | `/home/user/salesanchor/.github/workflows/api-contract-check.yml:38-58` は書き出して `git diff --exit-code -- frontend/api-contract/`。`frontend/api-contract/openapi.json:25683`（`OwnerRosterItem`）・`:25788`（`OwnerSettingsBody`）に `is_visible`（:25693・:25801）・`share_mode`（:25712・:25812）が実在。設計の命令は同 workflow :39-43 と同じ | 入った |
| R2 allowlist の sha256 | §3-4・F11 | `scripts/migration-guard/reference-allowlist.tsv:7` の sha256 `ef4dddd9…4dde` は `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` と一致（現物で確かめた）。規則は同 :5 | 入った |
| R3 件数 1169 | §3-4・F11 | `backend/tests/ops/test_ai_cloud_views.py:486` は `== n0 == 1170`。`migrations/20261024_100300_create_ai_cloud_views.sql:3` は「1169 行」。2 行外して 1 行足すので 1169、コメントも 1169 で一致。件数を固定する場所は `backend/tests/`・`scripts/`・`.github/` でこの 1 か所だけ（`git grep` で確かめた） | 入った |
| R4 `_REVIEWED` と登録の行 | F10・§5 | `scripts/run_all_migrations.sh:1494-1495` が便2b、`:1498` が `mr_report_summary`。「:1495 の次」は正しい。`:83` を外した点は正しい。**ただし `rls_bootstrap.py`・`test_calendar_sync_tenant_reset_pg.py` の既存項が抜けている** | **一部のみ（R1）** |
| R5 A5 の命令 | §2・§4-1 | `-E` で `is_visible|share_mode|_DEFAULT_OWNER_COLOR` に直っている。実物で流すと 38 行拾う（`backend/app/routers/calendar.py`・`tenant.py`・`schedule-owner.ts`・4 つの試験の fixture）。0 件にならず拾う | 入った（拾う場所の一覧に誤り: L1） |
| R6 古い形の作り方 | §5 | 下の「`ALTER TABLE` の方法」で確かめた。門・分類と矛盾しない | 入った |
| L1 行番号・422 の形 | §3-2 | `backend/app/services/event_colors.py:18`（`EVENT_COLOR_KEYS`）・`backend/app/routers/calendar.py:43`（取り込み済み）・`:119`（`value == "" or value in EVENT_COLOR_KEYS`）が実在。空文字を許さない点も書いてある | 入った |
| L2 ひな形と移行の書き方 | §3-1 | 下の「ひな形と移行の `color_key`」で確かめた | 入った（比べ方の限界: L2） |
| L3 24 色の写し | §3-1・§5 | `backend/app/services/event_colors.py:8-17`・前例 `backend/tests/test_event_colors_tokens.py` が実在 | 入った |
| L4 `SimpleNamespace` | §5 | `backend/tests/test_calendar_owner_api.py:95`・`:113`・`:121` が `SimpleNamespace` の本体で呼ぶ。設計は本物の `OwnerSettingsBody` に直すと書いている。pydantic 2.10.6 は `backend/requirements.txt:8` | 入った |
| L5 無効チームの写し | §8 | 設計の行が `backend/app/services/calendar_service.py:1273-1275` の写しの記録になっている | 入った |
| L8 既存の試験の直し | §5 | `SchedulePageImpl.test.tsx:1939`・`ScheduleSettingsPage.test.tsx:348` を直す、と書いてある。en の末尾空白は `frontend/scripts/check-i18n-missing-keys.js` が値を整えるかを実装役が確かめる（`frontend/scripts` の i18n 関係で `trim()` を使う物は `git grep` で見つからなかった。ただし検査は流していないので未確認） | 入った |
| L9 A8 | §2 A8 | 趣旨が「件数を変えない確認」に直っている | 入った |
| L6・L7 | 記録のみ | 変更不要 | — |

## R（直さないと壊れる物）

### R1 `_REVIEWED` に足す項を、新しい試験ファイルだけでなく既存の 2 項にも書く（設計 F10 の最終行・§5 を直す）

- 事実: `/home/user/salesanchor/backend/tests/test_tenant_loop_migration_guard.py:342`（`_actual`）は `backend/tests/` の全ての `*.py` を読み、全テナントを回す移行（`nspname ~ '^tenant_` を含む SQL。同 :19-22 の `_LOOP_RE`）の名前が文字に出る組を全部拾う。`:364`（`test_every_tenant_loop_migration_reference_is_classified`）は、拾った組が `_REVIEWED` に無ければ落ち、`_REVIEWED` にあって拾えなければ落ちる。
- 事実: 設計 F10 の最終行は「`_REVIEWED`: 新しい試験ファイルごとに 1 項」。設計はそのほかに `backend/tests/rls_bootstrap.py:190` の `_TENANT_LOOP_MIGRATIONS` と `backend/tests/test_calendar_sync_tenant_reset_pg.py:56` の流す順の末尾へ、新しい移行名を足すと書く。この 2 つのファイルの文字に新しい移行名が出るので、`(rls_bootstrap.py, 新)`・`(test_calendar_sync_tenant_reset_pg.py, 新)` の 2 組が拾われる。
- 事実: `_REVIEWED["rls_bootstrap.py"]`（同 :28 から）と `_REVIEWED["test_calendar_sync_tenant_reset_pg.py"]`（同 :62 から）の集合に、直近の便2b の `20261127_100000_add_calendar_team_share.sql` が入っている（:53・:74）。便2b も同じ形で足した前例。
- 影響: 足さないと上の試験が「分類表に無い」で落ちる。第1回 R4 は「`:53`・`:74` は足す」と書いたが、設計は「`:83` を外す」だけ取り込み、足す側を落とした。
- 直し: F10 の `_REVIEWED` の行を次に差し替える。
  - 「`rls_bootstrap.py` の集合と `test_calendar_sync_tenant_reset_pg.py` の集合に、新しい移行名を 1 つずつ足す」
  - 「新しい試験ファイルごとに 1 項。移行を流す試験（§5 の移行の試験）は `scoped`、移行ファイルを文字として読むだけの試験（24 組と CHECK を照らす試験）は `text_only` で理由つき（`test_classification_details_hold`（:380）は `text_only` に理由が無いと落ちる。同 :392）。同じファイルに置くなら 1 項にまとめる」
  - 「A6 の試験ファイルは移行名を文字に出さないなら項は要らない」

## L（軽い指摘）

- **L1 A5 の「今の拾う場所」の一覧が実物と合わない**（設計 §2 の A5 の下の段落）。
  - 設計は `schedule-owner.ts` を「1、10-11、30、34、45-46」と書く。実物で `git grep -n -E 'is_visible|share_mode|_DEFAULT_OWNER_COLOR' -- backend/app frontend/src` を流すと拾うのは `schedule-owner.ts` の **10・11・34・45・46** だけ。`:1`（`CalendarShareMode`）と `:30`（`shareMode`）は大文字小文字・書き方が違い、拾わない。
  - `tenant.py` は `:1652`・`:1653`・`:1656` を拾う（`:1654`・`:1655` は拾わない）。範囲の書き方なら誤りではない。
  - `calendar.py` の `_VALID_OWNER_SHARE_MODES`（大文字）は拾わない。A5 はその削除を証明しない（設計 §3-2 に削除の記載があるので、実物の差分で確かめる）。
  - 直し: 一覧を「10-11、34、45-46」に直す。実装の合格は「A5 が 0 件」と一致するので、一覧の誤りだけを直せばよい。
  - 付記: 画面側の試験に「`is_visible` が応答に無いこと」を書く場合は、`frontend/src` にその文字が残って A5 が 0 件にならない。名前を書かずに、期待するキーの完全一致で確かめる。後ろの `backend/tests` は A5 の範囲外なので、書いてよい。
- **L2 `tenant-template-shape` はこの変更の差を見つけない（通るが、同じ書き方の証明にならない）**。
  - 事実: `scripts/check_tenant_template_shape.py:449-451`（`main`）は、ひな形で作った会社の形（前）と、登録を全件流した後の形（後）を比べる。列は `format_type | notnull | default`（:80 から）、制約は `contype | pg_get_constraintdef`（:99 から）。
  - 設計の移行は、手順 1（`ADD COLUMN IF NOT EXISTS`）・手順 2（名前が在れば飛ばす）・手順 3（`color` が無ければ飛ばす）・手順 4（`DROP COLUMN IF EXISTS`）で、新しいひな形（`color_key text`・`calendar_owner_settings_color_key_check`・3 列なし）の上では**全部何もしない**。前と後は同じ形になり、差 0 で通る。型が `text`・CHECK が `IN (24 鍵)` で `calendar_events`（`tenant.py:1599`・`:1607`）・`calendar_categories`（`:1555`・`:1564`）と同じ書き方であることは、この検査では証明されない。
  - 一方、本番の既存会社はひな形ではなく移行の出来上がりで形が決まる。移行が `NOT VALID` のままだったり、鍵の並びが違ったりすると、本番とひな形が静かにずれる。
  - 直し（設計 §5 の移行の試験に 1 行）: 移行を流した後の会社の `format_type(color_key)` と `pg_get_constraintdef`（`calendar_owner_settings_color_key_check`）を、ひな形の文字（`tenant.py` の新しい `CREATE TABLE` の中の CHECK を読み込むか、`calendar_events_color_key_check` の定義と同じであること）と照らす。24 組の試験（L3）が「CHECK の鍵の並びを `tenant.py:1607` と照らす」と書いているなら、「新しい `calendar_owner_settings` の CHECK の鍵の並び」とも照らす、と書く（`:1607` は `calendar_events` の CHECK で、ひな形の `calendar_owner_settings` 自身の CHECK ではない）。
- **L3 移行の「会社を選ぶ文」の書き方と数を決めておく**（設計 §3-1・F10）。`backend/tests/rls_bootstrap.py:171-172`・`:200-207` は、移行の中の会社を選ぶ条件を `nspname ~ '^tenant_\d+$'`（または `LIKE 'tenant_%'`）の形に限り、その出現数が `_TENANT_LOOP_MIGRATIONS` の値と違うと `ValueError("Canonical tenant selector changed")` で止める。設計は「mapping count 1」と書くので、会社を選ぶのは 1 か所（手順 5 の最後の確かめを別の `FOR` でやらず、同じループの中か、同じ選び方でない書き方）にする。便2b の前例 `migrations/20261127_100000_add_calendar_team_share.sql:18` は `FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP` の 1 か所。設計に「選ぶのは `WHERE nspname ~ '^tenant_\d+$'` の 1 か所」と 1 行足す。
- **L4 `ALTER TABLE` の方法（R6）が門と分類と矛盾しないことの確認（記録）**。
  - `scripts/check_test_schema_dup.py:28`（`_CREATE = CREATE\s+TABLE\b`）は `CREATE TABLE` の文字だけを拾う。`ALTER TABLE … ADD COLUMN`・`DROP COLUMN` は拾わない。したがって試験が `ALTER TABLE` で古い形に戻すのは門に当たらない。試験の文字列に `CREATE TABLE` を書かないこと（古い形の表を作り直す書き方にしない）は設計 §5 のとおり。
  - `backend/tests/rls_bootstrap.py:368-418`（`bootstrap_tenant_schema`）は `DROP SCHEMA … CASCADE` のあと `create_tenant_schema`（ひな形）で作るので、試験が `ALTER` で変えても次の試験には持ち越されない（試験ごとに別の会社番号を使う前例: `backend/tests/test_calendar_team_share.py:37` の `_TENANT = 981`。会社番号の割り当てが他の試験とぶつからないことは実装役が確かめる）。
  - `DROP COLUMN color_key` は、その列を含む CHECK も一緒に消す（PostgreSQL の決まり。設計の記述と合う）。古い 3 列は `NOT NULL DEFAULT` つきで足すので、行を入れた後に移行を流す入口の形になる。`public.users` へ外部キー（`tenant.py:1657`）があるので、試験は先に `public.users` に行を入れる（前例 `backend/tests/rls_bootstrap.py:236` の `_ensure_public_users`）。
  - 分類は `scoped`（R1）。`test_classification_details_hold`（`test_tenant_loop_migration_guard.py:380-386`）は、新しい移行が `rls_bootstrap` の登録に在ることを確かめる。登録は設計 F10 のとおり。
- **L5 `_scope_tenant_migration` が足す条件の位置**: 会社を選ぶ文の直後に `AND nspname = 'tenant_NNN'` が入る（`rls_bootstrap.py:207`）。移行の `FOR … IN SELECT … WHERE nspname ~ '…' LOOP` は 1 行に書き、`WHERE` の直後に別の条件や `ORDER BY` を挟まない（前例と同じ形）。L3 と同じ箇所に 1 行足せば足りる。
- **L6 A4 の本番での確認は未確認**: 設計 A4 の「本番を読み取り専用の鍵で確かめる」は、この審査では本番の窓口を使っていないので、列・CHECK の本番の形は未確認（設計 F2 の 0 行も設計の記載のまま）。デプロイ後の確認で足りる。

## A5 の命令が今の実物で拾う場所（実物で流した一覧）

`git grep -n -E 'is_visible|share_mode|_DEFAULT_OWNER_COLOR' -- backend/app frontend/src`（38 行）:

- `backend/app/routers/calendar.py`: 53・83・84・94・95・404・405・410・429・430・431・462・463・464・465・468・470・502・529・530・537・552・553・554
- `backend/app/services/tenant.py`: 1652・1653・1656
- `frontend/src/pages/schedule/schedule-owner.ts`: 10・11・34・45・46
- 試験の fixture: `frontend/src/lib/query/batch3bPages.test.tsx:52`・`frontend/src/pages/schedule/SchedulePageCache.test.tsx:53`・`SchedulePageImpl.test.tsx:73-74`・`ScheduleSettingsPage.test.tsx:54-55`

設計が直す場所と一致する。A5 は書いたとおりに流れて、直した後に 0 件になる設計になっている。

## 受け入れ条件 A1〜A9 を検証できるか

| 条件 | 判定 | 根拠 |
|---|---|---|
| A1 | 検証できる | `type="color"` は `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:426` の 1 か所だけ（`git grep` で確かめた） |
| A2 | 検証できる | 画面の試験・受け口の試験とも作れる（L4 の形） |
| A3 | 検証できる | 受け口の中の 422（`calendar.py:119` と同じ形の確かめ） |
| A4 | 検証できる（R1 を直せば `_REVIEWED` で止まらず流れる） | 古い形の入口は `ALTER TABLE`（L4）。本番の確認はデプロイ後（L6） |
| A5 | 検証できる | 上の一覧。直った後は 0 件。一覧の誤りは L1 |
| A6 | 検証できる | `calendar_service.py:226-232`・`:381-383` は実物と合う。`teams.is_active` は `calendar_service.py:210-211` と同じ形 |
| A7 | 検証できる | `git grep -F` の 2 本は実物の文字（`SchedulePageImpl.tsx:346`・`ScheduleSettingsPage.tsx:476`）と合う。直した後に 0 件 |
| A8 | 検証できる | 趣旨が「件数を変えない」に直っている |
| A9 | 検証できる | 手順 1〜4 は 2 回目に何も起きない形。試験は 2 回流す |

## 設計どおりで実物と合う点（再確認した物）

- `tenant.py:1649-1660` の `calendar_owner_settings` の形・`tenant.py:1555`・`:1599`・`:1607` の `color_key text` と CHECK の書き方（`IS NULL OR` なし）・`event_colors.py:8-18` の 24 色・`schedule-owner.ts:34-35` は設計の記述と合う。
- `migrations/20261024_100300_create_ai_cloud_views.sql:381-382` の `color`（mask）・`share_mode`（allow）の 2 行は実在する。`backend/tests/ops/test_ai_cloud_views.py:1061` 付近の前例（`test_t10_calendar_categories_are_classified_on_bootstrapped_db`）が実在する。
- 移行の登録: `scripts/run_all_migrations.sh:1494-1495` が便2b、直後（:1497）が `mr_report_summary` の行で、新しい行は「:1495 の次」で正しい。
- `calendar_owner_settings` を参照する物は `backend/app/routers/calendar.py`・`backend/app/services/tenant.py`・`backend/tests/test_calendar_owner_api.py`・`scripts/run_all_migrations.sh:1313`（コメント）・`backend/app/realtime/topics.py:204`（PATCH の経路だけ）・移行 SQL だけ（`git grep` で確かめた）。設計が触らない物で列に依存する物は見つからなかった。

## 付記（事実と未確認）

- 試験・検査（pytest・npm・CI の検査・`check_tenant_template_shape.py`）は 1 本も流していない。R1 は `test_tenant_loop_migration_guard.py` の定義（読んだ）から導いた物で、実行はしていない。L2 は `check_tenant_template_shape.py` の比べ方（読んだ）から導いた物。
- 本番の列の形・行数は、読む窓口を使っていないので未確認。
