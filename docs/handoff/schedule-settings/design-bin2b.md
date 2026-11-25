# 設計: 便2b 予定の共有に「チームを選ぶ」を足す

- 版: 第3版（2026-11-25・Opus。第1回審査の R1〜R7・S1〜S12、第2回審査の R1・R2・S1〜S6 を入れた）
- 状態: 設計案作成済み・設計審査済み（第3回 APPROVE。推奨 S1〜S3 も入れた）
- 元: `docs/handoff/schedule-settings/requirements.md`（G4・G5・G6。PO「1」で承認済み）・`docs/handoff/schedule-settings/design.md` §6・`docs/handoff/schedule-settings/design-bin2a.md` §0（便2 を 2 つに分けた理由）
- 関連 ADR: ADR-027（i18n）・ADR-067／ADR-144（金型・デザイントークン）・ADR-072（commit 後の付け直し）・ADR-135／ADR-136（DB 変更の GO）・ADR-1037（ロック待ち 1 秒・長いロックを取らない）・ADR-1059（Google から取り込んだ予定は本人だけ）・ADR-1075（繰り返しの 3 択）・ADR-1081（予定の色）

## 0 この便でやること・やらないこと

| やる | やらない |
|---|---|
| 予定の共有に「チーム」を足す（1 つの予定に 1 つ以上のチーム） | 秘書のチャットからの予定作成でチームを選ぶ（今の「自分だけ／全員」のまま） |
| だれに見えるかの条件に「その予定のチームに入っている人」を足す | 予定を直せる人の決まりを変える（作った人か管理者のまま） |
| 種類の共有の初期値に「チーム」と初期のチームを足す | Google に送る・Google から取り込む決まり（ADR-1059・今の送り方のまま） |
| 予定の画面・設定ページの共有の選び方を「自分だけ／全員／チーム」にする | 人ごとの初期値・死んだ列（便3） |

## 1 現在地（実物・origin/main 5a72c083f）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | だれに見えるかの条件は 1 か所。ログインした人がいれば `(ce.calendar_type = 'shared' OR ce.user_id = :me)`、いなければ `ce.calendar_type = 'shared'` | `backend/app/services/calendar_service.py:240-246` |
| F2 | この条件を使うのは一覧 `GET /calendar/events` と探す `GET /calendar/events/search` の 2 つ。どちらも `cal_svc.list_events` を呼ぶ | `backend/app/routers/calendar.py:282`・`:310` |
| F3 | 直す・消すは、他人の「自分だけ」予定を 404 にする判定をそれぞれの受け口に持つ（管理者でも 404）。そのあと「作った人か管理者」でなければ 403 | `backend/app/routers/calendar.py:626-630`・`:731-737` |
| F4 | `calendar_type` の値は `shared`／`personal` の 2 つ。DB の CHECK `calendar_events_calendar_type_check` と、作る `:542`・直す `:633` の受け口の判定の 3 か所 | `backend/app/services/tenant.py:1608`・`backend/app/routers/calendar.py:542`・`:633` |
| F5 | 繰り返しの例外の行は元の行の `calendar_type` を写す。「この予定だけ」で見せ方を変えると 422 `recurrence_this_not_allowed`。「これ以降」は元の行を切り、新しい元の行を INSERT する（新しい id） | `backend/app/services/calendar_service.py:859-860`・`:970-990`・`:1100-1135` |
| F6 | チームの表は `teams`（`is_active` あり）と `team_members`（`team_id`→`teams` ON DELETE CASCADE・`UNIQUE(team_id, user_id)`） | `backend/app/services/tenant.py:530-548` |
| F7 | `GET /teams` は `teams.view` が要る。ひな形の初期の役では、マネージャー（`:81`）などには有り、営業（`:100-123`）・仕入（`:149-165`）・発送（`:168-184`）には無い（会社ごとに役の権限は変えられるので、これは初期値の話） | `backend/app/routers/teams.py:55-58`・`backend/app/services/tenant.py:81`・`:100-184` |
| F8 | 本番のチーム: 会社1・会社4・会社6 に 1 つずつ（すべて使っている）、メンバーは 5 社とも 0 人 | 2026-11-25 18:44 JST 読むだけの鍵で `ai_ro.tenant_00N__teams`／`__team_members` を数えた |
| F9 | 本番の予定: 会社1 meeting/personal 1・meeting/shared 2、会社4 meeting/personal 27・meeting/shared 8。`team` の予定は 0 | 2026-11-25 18:35 JST 読むだけの鍵（PR #5759 のコメント） |
| F10 | 種類の共有の初期値は `self`／`all`。CHECK `calendar_categories_default_share_check`・受け口 `_VALID_CATEGORY_SHARES`・画面の型 `CalendarCategoryShare` | `migrations/20261126_100000_create_calendar_categories.sql:41`・`backend/app/routers/calendar.py:167`・`frontend/src/features/schedule/useCalendarCategories.ts:9` |
| F11 | 画面の共有は `draft.visibleToStaff`（真偽）1 つ。送るときに `shared`／`personal` に変える | `frontend/src/pages/schedule/SchedulePageImpl.tsx:100`・`:1025`・`:1085`、`frontend/src/pages/schedule/ScheduleDraftFields.tsx:300`・`:426-430` |
| F12 | 画面の取り込みは `calendar_type` が `personal` 以外を全部 `shared` に丸める | `frontend/src/pages/schedule/schedule-utils.ts:372` |
| F13 | 変更の知らせ（`calendar.events`）は会社単位の合図だけで、予定の中身を送らない | `backend/app/services/google_webhook.py:376-380` |
| F14 | 金型に複数選択 `MultiSelect`（必須: `label`・`options`・`selected`・`onChange`・`clearLabel`・`allLabel`・`countLabel`。任意: `emptyLabel`・`layout`＝`popover`/`inline`/`row`）・選択 `SelectControl` がある | `frontend/src/components/MultiSelect.tsx:36-62`・`frontend/src/components/Select` |
| F15 | 本番の CHECK の名前は 5 社とも `calendar_events_calendar_type_check`（`CHECK (calendar_type IN ('shared','personal'))`）と `calendar_categories_default_share_check`（`IN ('self','all')`）。ひな形 `backend/app/services/tenant.py:1608` も同じ名前。古い移行 `migrations/078_create_calendar_events_tenant.sql:47-48` は名前を付けない CHECK で作っていた | 2026-11-25 19:00 JST 読むだけの鍵で `pg_constraint` を読んだ（10 行・AUDIT `rows=10 result=ok`） |
| F16 | 書き込みの道で「ほかに変える欄が無いと何もせず返る」所がある: 単発の直す `update_event` は `set_clauses` が空なら早く返る（`:533-536`）。繰り返しの「すべて」D1 は `fields` が空なら行を直さない（`:1165-1167`）。作る `create_event` は `:434` で commit する。「これ以降」は `_insert_row` → `_commit`（`:1134-1135`） | `backend/app/services/calendar_service.py` 該当行 |
| F17 | 「この予定だけ」で見せ方を変える判定は、送られた `calendar_type` が今の値と違うときだけ 422（同じ値なら通す） | `backend/app/services/calendar_service.py:858-859` |
| F18 | 行の持ち主の守り（RLS）: `calendar_events`・`calendar_categories` には無い。`teams`・`team_members` には有る（`ENABLE` `backend/app/services/tenant.py:2352-2353`・方針 `:2446`・`:2467`。会社の番号 `app.tenant_id` で絞る） | `backend/app/services/tenant.py` 該当行 |
| F19 | AI に見せる列の分類表: `calendar_categories.key` は `mask`（`migrations/20261024_100300_create_ai_cloud_views.sql:371`・`docs/handoff/cloud-case-ai/stage1-column-class.tsv:564`）。分類の行数の試験は今 1169（`backend/tests/ops/test_ai_cloud_views.py:486`） | 該当行 |
| F20 | 理由の語の表 `frontend/src/lib/apiErrorReason.ts` と、その並びを数える試験 `backend/tests/test_api_error_reason_sync.py:41-69`。`backend/app/services/calendar_categories.py` の理由の語（`category_conflict`・`invalid_category` など）は今この表に無い | 該当行 |
| F21 | 本番の予定の持ち主の列: `user_id` が NULL なのは会社4 の `shared` 6 件だけ（`created_by_user_id` はあり）。`personal` で `user_id` が NULL は 0 件。ほかは `user_id` と `created_by_user_id` が同じ。作る道は `user_id` に作った人を必ず入れる（`backend/app/services/calendar_service.py:422` の `"uid": user_id`）ので、`user_id` が NULL の行は Google 取り込み由来に限られる（第2回 S5） | 2026-11-25 19:04 JST 読むだけの鍵（AUDIT `rows=5 result=ok`） |

## 2 受入条件

| 基準 | 内容 | 検証方法 |
|---|---|---|
| B1 | 共有「チーム」の予定は、持ち主と、その予定のどれかのチーム（使っているチーム）に入っている人だけの一覧・探すに出る | 本物の PostgreSQL の試験: 持ち主・メンバー・メンバーでない人・メンバーでない管理者・使っていないチームのメンバー の 5 人で一覧と探すを呼び、出る／出ないが表のとおり |
| B2 | メンバーでない人（管理者も）がその予定を直す・消すと 404 `not_found:calendar_event` | 本物の PostgreSQL の試験 |
| B3 | 繰り返しのチーム予定は、回・例外の行・「これ以降」で分けた新しい元の行も、同じチームの人に見える | 本物の PostgreSQL の試験（3 通り） |
| B4 | 作る・直すで共有が `team` になるときの `team_ids` の決まりは §3-3 の「直すときの決まりの表」のとおり。作るときと、今が `team` 以外の予定を `team` にするときの欠け（送らない）・空は 422 `invalid_team_ids`。今が `team` の予定で `team_ids` を送らないのは通し、対応は今のまま。`team` で空を明示（`[]`）・無い id・使っていない id・int4 の範囲外は 422 `invalid_team_ids`。`team` 以外で空でない `team_ids` を送ると 422 `invalid_team_ids`。同じ id の重なりは 1 つにまとめる | 裏側の試験（§5 の B4 の並び: 表の 6 行・作るときの欠け・作るときの空・int4 の範囲外・重なりのまとめ） |
| B5 | チームから別の共有に変えると、その予定のチームの対応は消える。チームを変えると入れ替わる。`team_ids` だけを送った直す（ほかの欄なし）でも入れ替わる。変えられるのは持ち主だけ（今の見せ方と同じ 403） | 裏側の試験（単発・繰り返しの「すべて」・`team_ids` だけ の 3 通り） |
| B11 | 繰り返しのチーム予定の「この予定だけ」を持ち主が直す（題名だけ変える）: ①`calendar_type: "team"` を送り `team_ids` を送らない（画面と同じ）→ 200 ②今と同じ `team_ids` を送る → 200。③今と違う `team_ids` か違う `calendar_type` を送る → 422 `recurrence_this_not_allowed` | 裏側の試験（3 通り） |
| B12 | 種類の `default_team_ids`: `PATCH` で送らなければ今の対応のまま。`default_share='team'` で `[]` は 422。種類を読むとき、使っていないチームは `default_team_ids` に入らない | 裏側の試験（3 通り） |
| B6 | 種類の共有の初期値に「チーム」と初期のチーム（1 つ以上）を決められる。予定を作るときにその種類を選ぶと、共有「チーム」と初期のチームが入る | 裏側の試験＋画面の試験 |
| B7 | 今ある予定の見え方は変わらない（要件 G6） | 本番で反映の前後に `category/calendar_type` ごとの件数を数えて F9 と同じ＋`team` 0 件。移行の試験で、移行の前後の `shared`／`personal` の行が同じ、かつ持ち主・ほかの人・管理者の 3 人それぞれに見える件数が移行の前後で同じ |
| B8 | 共有の値の正本は層ごとに 1 か所: DB の CHECK 2 つ（予定・種類）・裏側の定数 2 つ（予定の `SHARE_VALUES`・種類の `CATEGORY_SHARE_VALUES`）・画面の型 1 つ（`CalendarShare`） | ①`git grep -n '"shared", "personal")' -- backend/app` が 0 件（閉じ括弧まで含める。定義 `("shared", "personal", "team")` には当たらない）（今 2 件 `backend/app/routers/calendar.py:542`・`:633`）②`git grep -n "^SHARE_VALUES\b\|^CATEGORY_SHARE_VALUES\b" -- backend/app` がちょうど 2 件 ③`git grep -n "_VALID_CATEGORY_SHARES" -- backend/app` が 0 件 ④`git grep -n '"self" | "all"' -- frontend/src` が型の定義の 1 件だけ（`CalendarShare` の定義のこと。`ScheduleItem.calendarType` の `"shared" | "personal" | "team"` は裏側の値の型で、この数の対象外） |
| B9 | 新しい文字は `t()`・ja/en 同じキー。部品は金型だけ・色の直書きなし | i18n 点検・UI governance gate・Lint & Dark Mode Check |
| B10 | ひな形で作った会社と、移行を流した会社の形が同じ | CI のひな形と形の差の検査 |

## 3 裏側の変更

### 3-1 表（`backend/app/services/tenant.py` のひな形と移行の両方に同じ形）

```sql
-- 予定とチームの対応（1 つの予定に複数チーム）。繰り返しは元の行の id だけに付ける
CREATE TABLE IF NOT EXISTS {schema}.calendar_event_teams (
    event_id integer NOT NULL REFERENCES {schema}.calendar_events(id) ON DELETE CASCADE,
    team_id  integer NOT NULL REFERENCES {schema}.teams(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, team_id)
);
CREATE INDEX IF NOT EXISTS idx_calendar_event_teams_team ON {schema}.calendar_event_teams (team_id);

-- 種類の初期のチーム
CREATE TABLE IF NOT EXISTS {schema}.calendar_category_teams (
    category_key character varying(50) NOT NULL REFERENCES {schema}.calendar_categories(key) ON UPDATE RESTRICT ON DELETE CASCADE,
    team_id integer NOT NULL REFERENCES {schema}.teams(id) ON DELETE CASCADE,
    PRIMARY KEY (category_key, team_id)
);
```

- `calendar_events_calendar_type_check` を `CHECK (calendar_type IN ('shared', 'personal', 'team'))` に入れ替える。
- `calendar_categories_default_share_check` を `CHECK (default_share IN ('self', 'all', 'team'))` に入れ替える。
- CHECK の名前はひな形でも明示する: `CONSTRAINT calendar_events_calendar_type_check CHECK (...)`・`CONSTRAINT calendar_categories_default_share_check CHECK (...)`（F15。移行の後と同じ名前）。
- 2 つの新しい表には RLS を付けない。理由: 対応表の親の `calendar_events`・`calendar_categories` に RLS が無く（F18）、会社ごとの部屋（schema）で分かれている。行を絞る役は `visibility_sql` が持つ。`team_members` の RLS（会社の番号で絞る）を真似ると、親に無い守りを子にだけ足すことになり形がずれる。
- `visibility_sql` は RLS のある `teams`・`team_members` を読む。会社の番号は今の受け口が `reset_tenant_context` で入れているので、そのまま読める。本物の PostgreSQL の試験（`backend/tests/rls_bootstrap.py` で役を作る形）で、ふだんの接続の役で B1 が通ることを確かめる。

### 3-2 移行（新規 `migrations/20261127_100000_add_calendar_team_share.sql`）

- 便2a の移行（`migrations/20261126_100000_create_calendar_categories.sql`）と同じ型: 全部屋を 1 つの `DO`・何度流しても同じ・`calendar_events` が無い部屋は飛ばす。
- `teams` が無い部屋は飛ばす（`to_regclass(format('%I.teams', nspname)) IS NULL` なら CONTINUE）。
- CHECK の入れ替え（予定・種類で同じ手順。名前がぶつからないよう仮の名前を通す）:
  1. 既に「`team` を含む CHECK が名前 `calendar_events_calendar_type_check` で 1 つ」なら何もしない（何度流しても同じ）。
  2. 仮の名前 `calendar_events_calendar_type_check_v2` で `CHECK (calendar_type IN ('shared','personal','team')) NOT VALID` を足す（前の回で残っていれば足さない）→ `VALIDATE CONSTRAINT`。
  3. 古い CHECK を消す: `pg_constraint` で `conrelid = 表 AND contype = 'c' AND pg_get_constraintdef(oid) ~ '\mcalendar_type\M' AND conname <> 仮の名前` の行を全部 `DROP CONSTRAINT`（名前が違う古い部屋＝F15 の名前なし CHECK にも効く）。
  4. `ALTER TABLE ... RENAME CONSTRAINT calendar_events_calendar_type_check_v2 TO calendar_events_calendar_type_check`（ひな形 `backend/app/services/tenant.py:1608` と同じ名前にそろえる）。
  - 種類は `calendar_categories_default_share_check`・`_v2`・`\mdefault_share\M` で同じ手順。
  - 全部屋 1 つの `DO`・1 つの取引。ロックは短い（ADR-1037。本番の行は 5 社で予定 38 行）。
- 最後の確かめ: 各部屋で `calendar_type` を使う CHECK がちょうど 1 つ・名前が `calendar_events_calendar_type_check`・定義に `team` を含む。`default_share` も同じ。2 つの表がある。満たさなければ `RAISE EXCEPTION` で全体を戻す。
- 便2a の合流（56419ebfa）が一緒に直した周りのファイルを同じように直す: `scripts/run_all_migrations.sh`・`scripts/migration-guard/reference-allowlist.tsv`・`backend/tests/rls_bootstrap.py`・`backend/tests/test_tenant_loop_migration_guard.py`。
- AI に見せる列の分類（F19）: `calendar_event_teams` は数の列（`event_id`・`team_id`）だけで分類の行は足さない（数の列の扱いは今の決まりどおり。CI の T10 型の試験で確かめる）。`calendar_category_teams.category_key` は `calendar_categories.key` と同じ `mask`（理由も同じ文）。`team_id` は数の列。足す場所: `migrations/20261024_100300_create_ai_cloud_views.sql`（`:371` の並び）・`docs/handoff/cloud-case-ai/stage1-column-class.tsv`・`backend/tests/ops/test_ai_cloud_views.py:486` の件数を実物の今の値＋1（この版の時点で 1169 → 1170。合流の前に main の値を読み直す）。

### 3-3 見え方の正本（`backend/app/services/calendar_service.py`）

見え方の条件を 1 つの関数に出し、一覧・探す・直す・消すの全部がこれを使う。

```python
SHARE_VALUES = ("shared", "personal", "team")  # 共有の値の正本（裏側）

def visibility_sql(alias: str = "ce") -> str:
    """この人に見える予定の条件。:me が無い呼び方はしない。
    繰り返しの回・例外の行は元の行のチームで判定する（COALESCE(recurring_event_id, id)）。"""
    return (
        f"({alias}.calendar_type = 'shared'"
        f" OR COALESCE({alias}.user_id, {alias}.created_by_user_id) = :me"
        f" OR ({alias}.calendar_type = 'team' AND EXISTS ("
        f"   SELECT 1 FROM calendar_event_teams cet"
        f"   JOIN teams t ON t.id = cet.team_id AND t.is_active"
        f"   JOIN team_members tm ON tm.team_id = cet.team_id AND tm.user_id = :me"
        f"   WHERE cet.event_id = COALESCE({alias}.recurring_event_id, {alias}.id))))"
    )

async def can_see_event(db, event_id: int, user_id: int) -> bool:
    """1 件の予定が見えるか。条件は visibility_sql と同じ文を DB で確かめる。"""
    # SELECT 1 FROM calendar_events ce WHERE ce.id = :id AND {visibility_sql()}
```

- 持ち主は `COALESCE(user_id, created_by_user_id)`。今の直す・消すの 404 の判定がこの決め方（`backend/app/routers/calendar.py:624` `event_owner = event_user_id if event_user_id is not None else created_by`）なので、一覧・探すもこれにそろえる（S1）。繰り返しの回・例外の行は元の行（`owner_row`）で判定する今の形を `can_see_event` でも守る（元の行の id を渡す）。一覧の見え方が変わるのは「`personal` で `user_id` が NULL」の行だけで、本番は 0 件（F21）。

- `list_events`（`:240-246`）: `user_id is None` のときの `ce.calendar_type = 'shared'` はそのまま。`user_id` があるときは `visibility_sql()` に置き換える。
- `list_events` の返す項目に `team_ids`（チーム予定だけ・元の行の対応・id の昇順。ほかは `[]`）を足す。SELECT に `COALESCE((SELECT array_agg(cet.team_id ORDER BY cet.team_id) FROM calendar_event_teams cet WHERE cet.event_id = COALESCE(ce.recurring_event_id, ce.id)), '{}')` を足す。
- 種類の `calendar_type = 'personal'` 絞り（`:228-231`）はそのまま。
- チームの対応の書き手は 1 つ: `async def set_event_teams(db, event_id: int, team_ids: list[int]) -> None`（その event_id の行を消して入れ直す。空なら消すだけ。commit しない＝呼び手の取引に乗る）。
- 呼ぶ決まり（F16 の「何もせず返る」所の前に置く。commit の前に呼ぶ）:
  - 作る（`create_event`）: `calendar_type == "team"` なら INSERT の後・`:434` の commit の前に呼ぶ。
  - 直す（単発 `update_event`）: 送られた中に `calendar_type` か `team_ids` があれば、`:533` の「`set_clauses` が空なら返る」より前に呼ぶ。呼んだら空で返さず commit する。決める共有＝送った `calendar_type`、無ければ今の値。`team_ids` の扱いは下の「直すときの決まりの表」のとおり。`team` 以外なら空で呼ぶ。
  - 繰り返しの「すべて」（D1・D2・D3）: 同じ決まりで元の行の id に呼ぶ。D1 は `:1165` の `if fields:` の外・`:1169` の `_commit` の前。
  - 単発→繰り返し（`_update_single_to_recurring`）: 同じ決まりで、その行（元の行になる）の id に呼ぶ。`:1234` の `_commit` の前。
  - 「これ以降」: 新しい元の行（`new_id`）に、送られた `team_ids`、無ければ元の元の行の対応を写す。`_insert_row`（`:1134`）の後・`_commit`（`:1135`）の前。新しい行が `team` でなければ呼ばない。
  - 「この予定だけ」: 対応は書かない。`team_ids` が送られ、元の行の対応（並べ替えて重なりを除いた集合）と違えば 422 `recurrence_this_not_allowed`（`check_recurrence_request` `:858-859` の `calendar_type` の判定と同じ「違うときだけ」）。同じなら通す。`team_ids` を送らなければ確かめない（第1回 R1・第2回 R1）。
  - Google から回の変更が来たとき（`_apply_app_instance_from_google` `:1753-1755`）: 例外の行に対応は書かない。見え方は元の行の対応で決まる（B3 の「例外の行」の試験で確かめる。第2回 S6）。
- 直すときの決まりの表（第2回 R1。単発・「すべて」・「これ以降」・単発→繰り返しに共通。「この予定だけ」は上の決まり）:

  | 今の共有 | 送った `calendar_type` | 送った `team_ids` | 結果 | 対応 |
  |---|---|---|---|---|
  | `team` | `team` か送らない | 送らない | 通す | 今のまま（`validate_team_ids` は `None` を返し、`set_event_teams` を呼ばない） |
  | `team` | `team` か送らない | 1 つ以上・正しい | 通す | 送った組に入れ替える |
  | どれでも | 決める共有が `team` | `[]`（明示の空） | 422 `invalid_team_ids` | 変えない |
  | `team` 以外 | `team` | 送らない | 422 `invalid_team_ids` | 変えない |
  | どれでも | `team` 以外（送った、または今の値） | 送らない、または `[]` | 通す | 空で呼ぶ（`team` から外すときは対応が消える） |
  | どれでも | `team` 以外 | 空でない | 422 `invalid_team_ids` | 変えない |

  作るときは「今の共有」が無いので、`team` で `team_ids` を送らない・空は 422。
- チームの確かめは 1 つ: `async def validate_team_ids(db, calendar_type: Optional[str], team_ids: Optional[list[int]], current_type: Optional[str] = None) -> Optional[list[int]]`。決める共有は `calendar_type`、無ければ `current_type`（直すときの今の値）。重なりを除いて昇順にした list を返す。今が `team`・決める共有も `team`・`team_ids` が `None` のときは `None` を返す（呼び手は対応を書かない）。int4 の範囲外・無い id・使っていない id（`is_active` が NULL も使っていない扱い）・`team` で空・`team` 以外で空でない → HTTP 422 `invalid_team_ids`。受け口で `try` の前に呼ぶ（便2a の種類の確かめと同じ置き方。422 を 500 にしない）。直すときは `owner_row` の `calendar_type` を `current_type` に渡す。
- 確かめと書き込みの間にチームが消えた・使わなくなったとき: 消えたら外部キーで INSERT が失敗し 409 にする（便2a の `category_conflict` と同じ `IntegrityError` の扱い）。使わなくなっただけなら対応は残り、`visibility_sql` が使っていないチームを見ないので、持ち主だけに見える。
- 説明文の直し: `list_events` の説明（`:207-209`）に「チーム」と持ち主の決め方を足す。`list_events` の中の変数 `visibility_sql`（例外の行の問い合わせ `:344-347` でも使う）は新しい関数の結果で作る（名前がぶつかるので変数名は `vis_where` に変える）。

### 3-4 受け口（`backend/app/routers/calendar.py`）

- `CreateEventBody`・`UpdateEventBody` に `team_ids: Optional[list[int]] = None`。
- 作る `:542`・直す `:633` の `("shared", "personal")` を `cal_svc.SHARE_VALUES` に置き換える。直すで `team_ids` だけ送ったときも、持ち主でなければ 403（見せ方を変えるのと同じ文）。
- 直す・消すの「他人の自分だけ予定は 404」（`:626-627`・`:731-732`）を `if not await cal_svc.can_see_event(db, owner_row["id"], user.id): 404` に置き換える（自分だけ・チームの両方をこの 1 つで判定する）。その後の 403 の判定は変えない。
- 新しい道 `GET /calendar/teams`（ログインした人）: 使っているチームの `id, name` を名前順。`teams` 表を読むだけ（写しを作らない）。`teams.view` の無い人（初期の役で営業・仕入・発送）もチームを選べるようにするため（F7）。
  - 出すのはチームの名前と番号だけ（メンバーは出さない）。同じ会社の人どうしで、予定の共有先を選ぶのに要る最小。チームの名前は今も会社の人に見える画面（予定の詳しい表示の共有の行）に出るので、新しく漏れる中身は無い（S6）。
- 種類: `_VALID_CATEGORY_SHARES`（`:167`）を消し、`backend/app/services/calendar_categories.py` に `CATEGORY_SHARE_VALUES = ("self", "all", "team")` を 1 つ置いて受け口はそれを使う（B8）。`POST`/`PATCH /calendar/categories` に `default_team_ids: Optional[list[int]]`。
  - 決める共有＝送った `default_share`、無ければ今の値。`team` なら `default_team_ids` は 1 つ以上の使っているチーム（`validate_team_ids` と同じ確かめ。違えば 422 `invalid_team_ids`）。`PATCH` で `default_team_ids` を送らなければ今の対応のまま。`team` 以外にしたら対応を消す。`team` 以外で空でない `default_team_ids` は 422。
  - `PATCH` の受け方は今の `_FIELD_COLUMNS`（`backend/app/services/calendar_categories.py:109` 付近）の形に従い、`default_team_ids` は列ではないので `_FIELD_COLUMNS` に入れず別に扱う。`default_team_ids` だけの `PATCH` も `no_fields_to_update` にしない。
  - `GET /calendar/categories` の各行に `default_team_ids`（使っているチームだけ・昇順。無ければ `[]`）（S4）。対応の書き手は `backend/app/services/calendar_categories.py` に 1 つ（`set_category_teams`）。
- 新しい理由の語 `invalid_team_ids` は、画面の訳の表（`frontend/src/lib/apiErrorReason.ts`）と並びの試験（`backend/tests/test_api_error_reason_sync.py:41-69` の列に足す）に入れ、ja/en の `apiError` に文を足す（F20。種類の理由の語は今この表に無いので、この便では `invalid_team_ids` だけ足し、ほかは足さない）。`GET /calendar/teams` は変更の知らせの表（`backend/app/realtime/topics.py`）の決まりに従う（読むだけの道が要らなければ足さない。実装役が試験の失敗で確かめる）。

## 4 画面の変更

### 4-1 共有の値（`frontend/src/pages/schedule/schedule-utils.ts`・`frontend/src/pages/schedule/SchedulePageImpl.tsx`）

- 型 `CalendarShare = "self" | "all" | "team"` を `frontend/src/features/schedule/useCalendarCategories.ts` に 1 つ置き、`CalendarCategoryShare` はこれにする。裏側の値との変換（`self`↔`personal`・`all`↔`shared`・`team`↔`team`）も同じファイルに 1 組だけ置く。
- `ApiCalendarEvent` に `team_ids: number[]`。`ScheduleItem.calendarType` を `"shared" | "personal" | "team"`、`teamIds: number[]` を足す。`normalizeEvent`（`:372`）は 3 つの値をそのまま写す。
- `ScheduleDraft.visibleToStaff` を `share: CalendarShare` と `teamIds: number[]` に置き換える（`:100`・`:159`・`:959`・`:1025`・`:1085` とその使い手すべて）。送るとき `team` なら `team_ids` も送る。繰り返しで見せ方が変わったかの判定（`:1085`）は `share` と `teamIds` の両方を比べる。
- 新しい読み手 `useCalendarTeams()`（`GET /calendar/teams`・`useApiQuery`）を `frontend/src/features/schedule/` に置く。

### 4-2 予定の共有の選び方（`frontend/src/pages/schedule/ScheduleDraftFields.tsx:415-440`）

- `Toggle` を金型 `SelectControl`（自分だけ／全員／チーム）に替える。`チーム` のとき、下に金型 `MultiSelect`（`useCalendarTeams` の一覧）を出す。チームが 0 件なら `MultiSelect` の `emptyLabel` に「使っているチームがありません」。
- 金型の使い方: `SelectControl` は同じ画面のほかの欄と同じ `variant="editor-filled"`（`frontend/src/pages/schedule/ScheduleDraftFields.tsx:151`）。`MultiSelect` は必須の `label`=`t("schedule.shareTeams")`・`clearLabel`=`t("schedule.shareTeamsClear")`・`allLabel`=`t("schedule.shareTeamsNone")`・`countLabel`=`(n) => t("schedule.shareTeamsCount", { count: n })`・`emptyLabel`=`t("schedule.noActiveTeams")` を渡す。予定の画面は引き出し（Drawer）の中なので `layout="inline"`、設定ページは `layout="popover"`（F14）。
- `team` でチームが 0 個のとき保存を押せない（保存ボタンを止め、欄の下に文を出す）。裏側の 422 は最後の守り。
- 繰り返しの予定を「この予定だけ」で直すとき、画面は `team_ids` を送らない。`calendar_type` は今と同じ値のまま送ってよい（今の画面は `canChangeVisibility` なら毎回送る: `frontend/src/pages/schedule/SchedulePageImpl.tsx:1024-1025`）。裏側は `team_ids` が送られても元の行と同じなら通す（二重の守り）。
- `MultiSelect` の `selected`・`options[].value` は文字（`string[]`）。チームの id（数）は渡すときに `String(id)`、受け取るときに `Number(v)` で変える。変換は `useCalendarTeams` のそばに 1 組だけ置く（第2回 S2）。
- 種類を選んだとき（`:291-305`）: `default_share` が `team` なら `share: "team"`・`teamIds: default_team_ids`。今の決まり（作るときだけ入れる・直すときは変えない）はそのまま。
- 予定の詳しい表示（`frontend/src/pages/schedule/SchedulePageImpl.tsx:395-405` の並び）に「共有」の行を足す（自分だけ／全員／チーム: 名前・名前）。名前は `useCalendarTeams` から引き、使っていないチームは出さない。`:402` の `schedule.calendarTypeValues.shared` はそのまま使ってよい（種類の名前が無いときの表示）。`calendarTypeValues` に `team`（チーム）を ja/en で足す（`frontend/src/locales/ja.json:3538`）。

### 4-3 設定ページ（`frontend/src/pages/schedule/ScheduleSettingsPage.tsx:346-355`）

- 共有の初期値の `SelectControl` に「チーム」を足す。`チーム` のとき `MultiSelect` で初期のチームを選ぶ。0 個なら保存しない（文を出す）。送るとき `default_team_ids`。フォームの状態（今は `defaultShare` だけ・`:346-355`）に `defaultTeamIds: number[]` を足し、`=== "self" ? "self" : "all"` の 2 値の決め打ちを `CalendarShare` の 3 値にする（第2回 S3）。

### 4-4 新しい文字（ja/en 同じキー・`schedule` の中）

`shareLabel`（共有）・`shareSelf`（自分だけ）・`shareAll`（全員）・`shareTeam`（チーム）・`shareTeams`（共有するチーム）・`shareTeamsClear`（選択を外す）・`shareTeamsNone`（未選択）・`shareTeamsCount`（{{count}}チーム）・`shareTeamsRequired`（チームを1つ以上選んでください）・`noActiveTeams`（使っているチームがありません）・`calendarTypeValues.team`（チーム）。`apiError.invalidTeamIds`（選んだチームが使えません。選び直してください）。今の `shareWithStaff`・`categoryShareSelf`・`categoryShareAll` で使わなくなるものは消す（両方の言語から）。

## 5 試験

- 裏側（本物の PostgreSQL。`docs/handoff/schedule-settings/design-bin2a.md` §5 と同じ置き場 `backend/tests/test_calendar_categories.py` の隣に `backend/tests/test_calendar_team_share.py`）:
  - B1 の 5 人 × 一覧・探す（出る／出ない）
  - B2 直す・消すの 404（メンバーでない人・メンバーでない管理者）と、メンバーの管理者は直せる
  - B3 繰り返し: 回が見える・「この予定だけ」の例外の行が見える・「これ以降」の新しい元の行が見える（メンバーでない人には 3 つとも出ない）
  - B4（「直すときの決まりの表」の 6 行を 1 つずつ・作るときの欠けと空・int4 の範囲外・重なりのまとめ。今が `team` で `team_ids` を送らない直すが 200 で対応が変わらない、を含む）・B5（チームを外す・入れ替える・`team_ids` だけ送る・繰り返しの「すべて」で題名を変えずにチームだけ変える・持ち主でない人の 403）
  - B11（「この予定だけ」: `team_ids` を送らず 200・今と同じ `team_ids` で 200・違う `team_ids` で 422・違う `calendar_type` で 422）・B12（3 通り）
  - 持ち主の決め方: `user_id` が NULL で `created_by_user_id` が自分の `team` 予定は、チームに入っていなくても自分には見える
  - B6 種類の初期のチーム（足す・直す・`team` 以外にすると消える・0 個で 422）
  - 移行（2 回流して同じ・CHECK が 1 つで名前が `calendar_events_calendar_type_check`・`team` が入る・ほかの値は入らない・前後で `shared`/`personal` の行が同じ・前後で 3 人それぞれに見える件数が同じ（S8）・名前なしの古い CHECK の部屋でも入れ替わる・`teams` が無い部屋は飛ばす）
  - チームを消すと対応が消え、メンバーだった人に見えなくなる（持ち主には見える）
- 画面: 共有の選び方（3 つ・チームで複数選ぶ・0 個で保存できない）／種類の初期値でチームが入る／詳しい表示の「共有」の行／設定ページの初期のチーム／繰り返しの「この予定だけ」で `team_ids` を送らない。既存の試験で `visibleToStaff`・`shareWithStaff` の `switch` を使うもの（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx:171`・`:1047`・`:1403`・`:1433`）は新しい選び方（`combobox`）に直す。

## 6 触らない

- 作った人か管理者でなければ 403 の判定（`backend/app/routers/calendar.py:629-630`・`:735-737`）。
- Google に送る・取り込む決まり（`_send_ok`・`can_add_meet`・`upsert_from_google`）。チーム予定も今の共有予定と同じく送る。
- 秘書の予定作成（`frontend/src/features/secretary/*`・`backend/app/routers/assistant.py`）。
- Google の画面に出す一覧 `/google-calendar/events`（`backend/app/routers/google_calendar.py:300-400`）。この道はアプリの予定の表を見せ方で絞らない今の形のまま。G5「チーム外の人に見えない」は、アプリの予定の画面と `/calendar/*` の道で満たす（S7）。
- `calendar_owner_settings`・人ごとの色（便3）。

## 7 代替案

| 案 | 採らない理由 |
|---|---|
| 予定に `team_id` の列を 1 つ足す | 1 つのチームしか選べない。対応表なら 1 つの使い方はその一部（design.md §6） |
| 見え方を画面で絞る | 裏側が全部返すと、チーム外の人にも中身が届く（G5 が満たせない） |
| 管理者にはチーム予定を全部見せる | 今の「自分だけ」と同じく管理者も見えない方がそろう。G5「チーム外の人で開いて見えない」をそのまま満たす |
| チームの一覧を `GET /teams` から読む | 初期の役で営業・仕入・発送に `teams.view` が無く、その人たちが選べない（F7） |
| 繰り返しの回ごとに対応を付ける | 行が増え、元の行と回でずれる。元の行 1 つに付け、回は元の行で判定する |

## 8 危うさと手当て

| 危うさ | 手当て |
|---|---|
| 見え方の条件の書き漏れで、他人の予定が見える | 条件を `visibility_sql` 1 つにし、一覧・探す・直す・消すの全部が使う。B1〜B3 の 5 人の試験 |
| チームを消す・使わなくすると、メンバーだった人に見えなくなる | 持ち主には必ず見える（`ce.user_id = :me`）。本番はメンバー 0 人（F8）で今の見え方に影響なし |
| CHECK の入れ替えでロック待ち | `NOT VALID`→`VALIDATE`→古いものを消す。全部屋 1 つの DO（便2a と同じ。本番で 1 本 0.1 秒台・`>>> [final] read probe` で確かめる） |
| 「これ以降」でチームの対応が写らず、後半が持ち主だけになる | B3 の試験 |
| ほかの欄を変えない直すで対応が書かれない（F16） | 呼ぶ決まりを「早く返る所の前・commit の前」に固定。B5 の `team_ids` だけ の試験 |
| CHECK の名前がぶつかる・古い部屋で名前が違う（F15） | 仮の名前 `_v2` → 古いものを定義で探して消す → 名前を戻す。移行の試験に名前なし CHECK の部屋を入れる |
| 確かめと書き込みの間にチームが消える | 外部キーで失敗 → 409。使わなくなっただけなら持ち主だけに見える |
| `teams`・`team_members` の RLS で見え方の問い合わせが空になる | 会社の番号は今の受け口が入れている。本物の PostgreSQL の試験をふだんの接続の役で回す |

## 9 外部・過去事例

- Google カレンダーは、予定に「ゲスト」としてグループのアドレスを入れると、そのグループの人に予定が見える（support.google.com/calendar「予定にゲストを追加する」。日付は未確認）。「予定に複数のまとまりを付ける」形の参考。数値の根拠には使わない。

## 10 維持の仕組み

- 見え方の正本は `visibility_sql` 1 つ（持ち主＝`COALESCE(user_id, created_by_user_id)`）。共有の値は DB の CHECK 2 つ・裏側の定数 2 つ（`SHARE_VALUES`・`CATEGORY_SHARE_VALUES`）・画面の型 `CalendarShare` 1 つだけ（B8 の 4 つの `git grep` を審査役の確かめに入れる）。
- 守り手: CI（pytest・vitest・i18n 点検・UI governance gate・移行の試験・ひな形の形の差）。設計の持ち主は Opus（設計担当）。

## 11 本番での目視（PO）

1. 設定でチームに自分ともう 1 人を入れる。
2. 予定を作り、共有を「チーム」にしてそのチームを選ぶ。
3. チームに入っていない人で開くと、その予定が出ない。チームの人で開くと出る。

## 12 審査

| 回 | 日 | 判定 | 記録 | 入れた直し |
|---|---|---|---|---|
| 1 | 2026-11-25 | REVISE | `docs/handoff/schedule-settings/review-architect-bin2b-1.md` | R1 §3-3「この予定だけ」・§4-2・B11／R2 §3-3 呼ぶ決まり・F16・B5／R3 §3-2 仮の名前・F15／R4 §3-1 RLS 無し・F18／R5 §3-2 分類・F19／R6 F7・§7／R7 B8／S1 F21・持ち主の決め方／S2 B4／S3・S4 §3-4・B12／S5 §4-2・§4-4・§5／S6 §3-4／S7 §6／S8 B7・§5／S9 F20／S10 §3-2・§3-3／S11 F15・F21 時刻／S12 §3-3 |
| 2 | 2026-11-25 | REVISE | `docs/handoff/schedule-settings/review-architect-bin2b-2.md` | R1 §3-3「直すときの決まりの表」・`validate_team_ids` の `None`・B4・B11（3 通り）・§4-2「この予定だけ」／R2 B8 ①を閉じ括弧まで／S1 `:1234`／S2 §4-2 文字↔数／S3 §4-3 `defaultTeamIds`／S4 B8 ④の注／S5 F21／S6 §3-3 Google の回 |
| 3 | 2026-11-25 | APPROVE | `docs/handoff/schedule-settings/review-architect-bin2b-3.md` | 推奨 S1 §5 B11 の 4 通り／S2 B4 の検証方法の並び／S3 表の行 5 に `[]` |
