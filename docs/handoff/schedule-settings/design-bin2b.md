# 設計: 便2b 予定の共有に「チームを選ぶ」を足す

- 版: 第1版（2026-11-25・Opus）
- 状態: 設計案作成済み・審査前
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
| F7 | `GET /teams` は `teams.view` が要る。マネージャーの役には `teams.view` が無い | `backend/app/routers/teams.py:55-58`・`backend/app/services/tenant.py:68-90` |
| F8 | 本番のチーム: 会社1・会社4・会社6 に 1 つずつ（すべて使っている）、メンバーは 5 社とも 0 人 | 2026-11-25 18:44 JST 読むだけの鍵で `ai_ro.tenant_00N__teams`／`__team_members` を数えた |
| F9 | 本番の予定: 会社1 meeting/personal 1・meeting/shared 2、会社4 meeting/personal 27・meeting/shared 8。`team` の予定は 0 | 2026-11-25 18:35 JST 読むだけの鍵（PR #5759 のコメント） |
| F10 | 種類の共有の初期値は `self`／`all`。CHECK `calendar_categories_default_share_check`・受け口 `_VALID_CATEGORY_SHARES`・画面の型 `CalendarCategoryShare` | `migrations/20261126_100000_create_calendar_categories.sql:41`・`backend/app/routers/calendar.py:167`・`frontend/src/features/schedule/useCalendarCategories.ts:9` |
| F11 | 画面の共有は `draft.visibleToStaff`（真偽）1 つ。送るときに `shared`／`personal` に変える | `frontend/src/pages/schedule/SchedulePageImpl.tsx:100`・`:1025`・`:1085`、`frontend/src/pages/schedule/ScheduleDraftFields.tsx:300`・`:426-430` |
| F12 | 画面の取り込みは `calendar_type` が `personal` 以外を全部 `shared` に丸める | `frontend/src/pages/schedule/schedule-utils.ts:372` |
| F13 | 変更の知らせ（`calendar.events`）は会社単位の合図だけで、予定の中身を送らない | `backend/app/services/google_webhook.py:376-380` |
| F14 | 金型に複数選択 `MultiSelect`・選択 `SelectControl` がある | `frontend/src/components/MultiSelect.tsx:36-77`・`frontend/src/components/Select` |

## 2 受入条件

| 基準 | 内容 | 検証方法 |
|---|---|---|
| B1 | 共有「チーム」の予定は、持ち主と、その予定のどれかのチーム（使っているチーム）に入っている人だけの一覧・探すに出る | 本物の PostgreSQL の試験: 持ち主・メンバー・メンバーでない人・メンバーでない管理者・使っていないチームのメンバー の 5 人で一覧と探すを呼び、出る／出ないが表のとおり |
| B2 | メンバーでない人（管理者も）がその予定を直す・消すと 404 `not_found:calendar_event` | 本物の PostgreSQL の試験 |
| B3 | 繰り返しのチーム予定は、回・例外の行・「これ以降」で分けた新しい元の行も、同じチームの人に見える | 本物の PostgreSQL の試験（3 通り） |
| B4 | 作る・直すで `calendar_type: "team"` には `team_ids`（1 つ以上・使っているチームの id）が要る。欠け・空・無い id・使っていない id は 422 `invalid_team_ids`。`team` 以外で `team_ids` を送ると 422 `invalid_team_ids` | 裏側の試験 |
| B5 | チームから別の共有に変えると、その予定のチームの対応は消える。チームを変えると入れ替わる。変えられるのは持ち主だけ（今の見せ方と同じ 403） | 裏側の試験 |
| B6 | 種類の共有の初期値に「チーム」と初期のチーム（1 つ以上）を決められる。予定を作るときにその種類を選ぶと、共有「チーム」と初期のチームが入る | 裏側の試験＋画面の試験 |
| B7 | 今ある予定の見え方は変わらない（要件 G6） | 本番で反映の前後に `category/calendar_type` ごとの件数を数えて F9 と同じ＋`team` 0 件。移行の試験で、移行の前後の `shared`／`personal` の行が同じ |
| B8 | 共有の値の正本は 1 か所ずつ: DB の CHECK（`shared`/`personal`/`team`）と、裏側の定数 1 つ、画面の型 1 つ | `git grep -n "('shared', 'personal')" -- backend/app ':!backend/app/services/tenant.py'` が 0 件 |
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
- 2 つの新しい表の行の持ち主の守り（RLS など）は、同じ部屋の `team_members` と同じ扱いにする（`backend/app/services/tenant.py:2340-2363` の連携表の並びに足す）。実装役は `backend/tests/rls_bootstrap.py` と `team_members` の扱いを読んで同じにする。

### 3-2 移行（新規 `migrations/20261127_100000_add_calendar_team_share.sql`）

- 便2a の移行（`migrations/20261126_100000_create_calendar_categories.sql`）と同じ型: 全部屋を 1 つの `DO`・何度流しても同じ・`calendar_events` が無い部屋は飛ばす。
- CHECK の入れ替えは「新しい CHECK を `NOT VALID` で足す → `VALIDATE` → 古い CHECK を消す」の順。既に新しい CHECK があれば何もしない（ADR-1037。長いロックを取らない）。
- 最後の確かめ: 各部屋で `calendar_type` を使う CHECK がちょうど 1 つで `team` を含む・`default_share` も同じ・2 つの表がある。満たさなければ `RAISE EXCEPTION` で全体を戻す。
- 便2a の合流（56419ebfa）が一緒に直した周りのファイルを同じように直す: `scripts/run_all_migrations.sh`・`scripts/migration-guard/reference-allowlist.tsv`・`docs/handoff/cloud-case-ai/stage1-column-class.tsv`・`migrations/20261024_100300_create_ai_cloud_views.sql`・`backend/tests/ops/test_ai_cloud_views.py`（件数）・`backend/tests/rls_bootstrap.py`・`backend/tests/test_tenant_loop_migration_guard.py`。新しい 2 表の列の分類は、`team_members` の列と同じ分類にする。

### 3-3 見え方の正本（`backend/app/services/calendar_service.py`）

見え方の条件を 1 つの関数に出し、一覧・探す・直す・消すの全部がこれを使う。

```python
SHARE_VALUES = ("shared", "personal", "team")  # 共有の値の正本（裏側）

def visibility_sql(alias: str = "ce") -> str:
    """この人に見える予定の条件。:me が無い呼び方はしない。
    繰り返しの回・例外の行は元の行のチームで判定する（COALESCE(recurring_event_id, id)）。"""
    return (
        f"({alias}.calendar_type = 'shared'"
        f" OR {alias}.user_id = :me"
        f" OR ({alias}.calendar_type = 'team' AND EXISTS ("
        f"   SELECT 1 FROM calendar_event_teams cet"
        f"   JOIN teams t ON t.id = cet.team_id AND t.is_active"
        f"   JOIN team_members tm ON tm.team_id = cet.team_id AND tm.user_id = :me"
        f"   WHERE cet.event_id = COALESCE({alias}.recurring_event_id, {alias}.id))))"
    )

async def can_see_event(db, owner_row: dict, user_id: int) -> bool:
    """1 件の予定が見えるか。条件は visibility_sql と同じ文を DB で確かめる。"""
    # SELECT 1 FROM calendar_events ce WHERE ce.id = :id AND {visibility_sql()}
```

- `list_events`（`:240-246`）: `user_id is None` のときの `ce.calendar_type = 'shared'` はそのまま。`user_id` があるときは `visibility_sql()` に置き換える。
- `list_events` の返す項目に `team_ids`（チーム予定だけ・元の行の対応・id の昇順。ほかは `[]`）を足す。SELECT に `COALESCE((SELECT array_agg(cet.team_id ORDER BY cet.team_id) FROM calendar_event_teams cet WHERE cet.event_id = COALESCE(ce.recurring_event_id, ce.id)), '{}')` を足す。
- 種類の `calendar_type = 'personal'` 絞り（`:228-231`）はそのまま。
- チームの対応の書き手は 1 つ: `async def set_event_teams(db, event_id: int, team_ids: list[int]) -> None`（その event_id の行を消して入れ直す。空なら消すだけ）。
  - 作る（`create_event`）: `calendar_type == "team"` なら INSERT のあと同じ取引で呼ぶ。
  - 直す（単発・「すべて」・単発→繰り返し）: 送られた `calendar_type` か `team_ids` があれば、元の行の id で呼ぶ（`team` 以外になったら空で呼ぶ）。
  - 「これ以降」: 新しい元の行（`new_id`）に、送られた `team_ids`、無ければ元の元の行の対応を写す。新しい行が `team` でなければ呼ばない。
  - 「この予定だけ」: `team_ids` を送ると `calendar_type` と同じく 422 `recurrence_this_not_allowed`（`check_recurrence_request` の `:859` の判定に足す）。
- チームの確かめは 1 つ: `async def validate_team_ids(db, calendar_type, team_ids)` → 違えば HTTP 422 `invalid_team_ids`。受け口で `try` の前に呼ぶ（便2a の種類の確かめと同じ置き方。422 を 500 にしない）。

### 3-4 受け口（`backend/app/routers/calendar.py`）

- `CreateEventBody`・`UpdateEventBody` に `team_ids: Optional[list[int]] = None`。
- 作る `:542`・直す `:633` の `("shared", "personal")` を `cal_svc.SHARE_VALUES` に置き換える。直すで `team_ids` だけ送ったときも、持ち主でなければ 403（見せ方を変えるのと同じ文）。
- 直す・消すの「他人の自分だけ予定は 404」（`:626-627`・`:731-732`）を `if not await cal_svc.can_see_event(db, owner_row, user.id): 404` に置き換える（自分だけ・チームの両方をこの 1 つで判定する）。その後の 403 の判定は変えない。
- 新しい道 `GET /calendar/teams`（ログインした人）: 使っているチームの `id, name` を名前順。`teams` 表を読むだけ（写しを作らない）。`teams.view` の無い人もチームを選べるようにするため（F7）。
- 種類: `default_share` に `team` を足す（`_VALID_CATEGORY_SHARES`）。`POST`/`PATCH /calendar/categories` に `default_team_ids: Optional[list[int]]`。`default_share = 'team'` なら 1 つ以上の使っているチームが要る（違えば 422 `invalid_team_ids`）。`team` 以外にしたら対応を消す。`GET /calendar/categories` の各行に `default_team_ids`（昇順。無ければ `[]`）。書き手は `backend/app/services/calendar_categories.py` に 1 つ。
- 新しい理由の語 `invalid_team_ids` は、便2a の直し2 と同じく、理由の語の表と件数の試験（`backend/tests/test_api_error_reason_sync.py`）と画面の訳（`frontend/src/lib/apiErrorReason.ts`）に足す。`GET /calendar/teams` は変更の知らせの表（`backend/app/realtime/topics.py`）の決まりに従う（読むだけの道が要らなければ足さない。実装役が試験の失敗で確かめる）。

## 4 画面の変更

### 4-1 共有の値（`frontend/src/pages/schedule/schedule-utils.ts`・`SchedulePageImpl.tsx`）

- 型 `CalendarShare = "self" | "all" | "team"` を `frontend/src/features/schedule/useCalendarCategories.ts` に 1 つ置き、`CalendarCategoryShare` はこれにする。裏側の値との変換（`self`↔`personal`・`all`↔`shared`・`team`↔`team`）も同じファイルに 1 組だけ置く。
- `ApiCalendarEvent` に `team_ids: number[]`。`ScheduleItem.calendarType` を `"shared" | "personal" | "team"`、`teamIds: number[]` を足す。`normalizeEvent`（`:372`）は 3 つの値をそのまま写す。
- `ScheduleDraft.visibleToStaff` を `share: CalendarShare` と `teamIds: number[]` に置き換える（`:100`・`:159`・`:959`・`:1025`・`:1085` とその使い手すべて）。送るとき `team` なら `team_ids` も送る。繰り返しで見せ方が変わったかの判定（`:1085`）は `share` と `teamIds` の両方を比べる。
- 新しい読み手 `useCalendarTeams()`（`GET /calendar/teams`・`useApiQuery`）を `frontend/src/features/schedule/` に置く。

### 4-2 予定の共有の選び方（`frontend/src/pages/schedule/ScheduleDraftFields.tsx:415-440`）

- `Toggle` を金型 `SelectControl`（自分だけ／全員／チーム）に替える。`チーム` のとき、下に金型 `MultiSelect`（`useCalendarTeams` の一覧）を出す。チームが 0 件なら `MultiSelect` の `emptyLabel` に「使っているチームがありません」。
- `team` でチームが 0 個のとき保存を押せない（保存ボタンを止め、欄の下に文を出す）。裏側の 422 は最後の守り。
- 種類を選んだとき（`:291-305`）: `default_share` が `team` なら `share: "team"`・`teamIds: default_team_ids`。今の決まり（作るときだけ入れる・直すときは変えない）はそのまま。
- 予定の詳しい表示（`SchedulePageImpl.tsx:395-405` の並び）に「共有」の行を足す（自分だけ／全員／チーム: 名前・名前）。名前は `useCalendarTeams` から引き、使っていないチームは出さない。

### 4-3 設定ページ（`frontend/src/pages/schedule/ScheduleSettingsPage.tsx:346-355`）

- 共有の初期値の `SelectControl` に「チーム」を足す。`チーム` のとき `MultiSelect` で初期のチームを選ぶ。0 個なら保存しない（文を出す）。送るとき `default_team_ids`。

### 4-4 新しい文字（ja/en 同じキー・`schedule` の中）

`shareLabel`（共有）・`shareSelf`（自分だけ）・`shareAll`（全員）・`shareTeam`（チーム）・`shareTeams`（共有するチーム）・`shareTeamsRequired`（チームを1つ以上選んでください）・`noActiveTeams`（使っているチームがありません）。今の `shareWithStaff`・`categoryShareSelf`・`categoryShareAll` で使わなくなるものは消す（両方の言語から）。

## 5 試験

- 裏側（本物の PostgreSQL。`docs/handoff/schedule-settings/design-bin2a.md` §5 と同じ置き場 `backend/tests/test_calendar_categories.py` の隣に `backend/tests/test_calendar_team_share.py`）:
  - B1 の 5 人 × 一覧・探す（出る／出ない）
  - B2 直す・消すの 404（メンバーでない人・メンバーでない管理者）と、メンバーの管理者は直せる
  - B3 繰り返し: 回が見える・「この予定だけ」の例外の行が見える・「これ以降」の新しい元の行が見える（メンバーでない人には 3 つとも出ない）
  - B4 の 422（6 通り）・B5（チームを外す・入れ替える・持ち主でない人の 403）
  - B6 種類の初期のチーム（足す・直す・`team` 以外にすると消える・0 個で 422）
  - 移行（2 回流して同じ・CHECK が 1 つ・`team` が入る・`custom_9` に相当する値は入らない・前後で `shared`/`personal` の行が同じ）
  - チームを消すと対応が消え、メンバーだった人に見えなくなる（持ち主には見える）
- 画面: 共有の選び方（3 つ・チームで複数選ぶ・0 個で保存できない）／種類の初期値でチームが入る／詳しい表示の「共有」の行／設定ページの初期のチーム。既存の試験で `visibleToStaff` を使うものは新しい形に直す。

## 6 触らない

- 作った人か管理者でなければ 403 の判定（`backend/app/routers/calendar.py:629-630`・`:735-737`）。
- Google に送る・取り込む決まり（`_send_ok`・`can_add_meet`・`upsert_from_google`）。チーム予定も今の共有予定と同じく送る。
- 秘書の予定作成（`frontend/src/features/secretary/*`・`backend/app/routers/assistant.py`）。
- `calendar_owner_settings`・人ごとの色（便3）。

## 7 代替案

| 案 | 採らない理由 |
|---|---|
| 予定に `team_id` の列を 1 つ足す | 1 つのチームしか選べない。対応表なら 1 つの使い方はその一部（design.md §6） |
| 見え方を画面で絞る | 裏側が全部返すと、チーム外の人にも中身が届く（G5 が満たせない） |
| 管理者にはチーム予定を全部見せる | 今の「自分だけ」と同じく管理者も見えない方がそろう。G5「チーム外の人で開いて見えない」をそのまま満たす |
| チームの一覧を `GET /teams` から読む | マネージャーの役に `teams.view` が無く選べない（F7） |
| 繰り返しの回ごとに対応を付ける | 行が増え、元の行と回でずれる。元の行 1 つに付け、回は元の行で判定する |

## 8 危うさと手当て

| 危うさ | 手当て |
|---|---|
| 見え方の条件の書き漏れで、他人の予定が見える | 条件を `visibility_sql` 1 つにし、一覧・探す・直す・消すの全部が使う。B1〜B3 の 5 人の試験 |
| チームを消す・使わなくすると、メンバーだった人に見えなくなる | 持ち主には必ず見える（`ce.user_id = :me`）。本番はメンバー 0 人（F8）で今の見え方に影響なし |
| CHECK の入れ替えでロック待ち | `NOT VALID`→`VALIDATE`→古いものを消す。全部屋 1 つの DO（便2a と同じ。本番で 1 本 0.1 秒台・`>>> [final] read probe` で確かめる） |
| 「これ以降」でチームの対応が写らず、後半が持ち主だけになる | B3 の試験 |

## 9 外部・過去事例

- Google カレンダーは、予定に「ゲスト」としてグループのアドレスを入れると、そのグループの人に予定が見える（support.google.com/calendar「予定にゲストを追加する」。日付は未確認）。「予定に複数のまとまりを付ける」形の参考。数値の根拠には使わない。

## 10 維持の仕組み

- 見え方の正本は `visibility_sql` 1 つ。共有の値は DB の CHECK・`SHARE_VALUES`・画面の `CalendarShare` の 3 層だけ（B8 の `git grep` を審査役の確かめに入れる）。
- 守り手: CI（pytest・vitest・i18n 点検・UI governance gate・移行の試験・ひな形の形の差）。設計の持ち主は Opus（設計担当）。

## 11 本番での目視（PO）

1. 設定でチームに自分ともう 1 人を入れる。
2. 予定を作り、共有を「チーム」にしてそのチームを選ぶ。
3. チームに入っていない人で開くと、その予定が出ない。チームの人で開くと出る。

## 12 審査

| 回 | 日 | 判定 | 記録 | 入れた直し |
|---|---|---|---|---|
