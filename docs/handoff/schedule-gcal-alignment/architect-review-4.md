# 設計の再審査 4 回目（便3 Google Meet だけ）

- HEAD: `3c86807a48c1deb7fbc8ca61106139a0b686a470`（`origin/release/schedule-gcal-bin2-design`。指示どおり 3c86807a4 で始まる）
- 突き合わせた実物: `origin/main` `1f017118d45519053c66ea3579650e7c0a9df6c8`
- 対象: design.md §5-7・§7 の 3（前提確認の結果を含む）・§9・§16。改訂は `git diff 9545d849d 3c86807a4`（design.md だけ・+27/-4）
- 前回の指摘: `origin/release/schedule-gcal-alignment-review2:docs/handoff/schedule-gcal-alignment/architect-review-2.md` の N-1（107 行目）・N-2（108）・N-3（109）・N-13（111）
- 審査役: クラウドの Architect（コードは直していない・本番に接続していない・外部の道具は使っていない）

## 判定: 便3 = **REVISE（軽い）**

前回の 4 件（N-1・N-2・N-3・N-13）はすべて直った。§7-3 の前提 4 件も結果が書かれた（本番の読み取りはこの審査では確かめ直していない＝未確認のまま受け取る）。
ただし、改訂で新しく書いた道に穴が 2 つある（R4-1・R4-2）。どちらも §5-7 に数行書き足せば済み、設計の向きは変わらない。R4-1・R4-2 を直せば、もう一度のクラウド審査なしで §11-3 のカードを書いてよい（同一 AI の自己確認で足りる程度）。

## 1. 前回の指摘が直ったか（実物で確かめた）

| 指摘 | 設計の書いた場所 | 実物（origin/main 1f017118d） | 結果 |
|---|---|---|---|
| N-1 422 が 500 になる | §5-7「作る」150 行目・「直す」151 行目 | 作る口 `backend/app/routers/calendar.py:340` `create_event`、`:352` `try:`、`:359` `except Exception as e:`、`:361-364` 500。直す口 `:374` `update_event`、`:421` `try:`、`:429` `except Exception as e:`、`:431-434` 500。口の try の前に 422 を出す前例は既にある（`:347-351`・`:407-412`） | **直った**。判定を `try` の前に置く形（案 a）。サービスを呼ばないので表にも Google にも入らない、が口の段で保証される |
| N-1 の付け足し: 判定の式を 1 か所に | §5-7 148 行目 `can_add_meet` | 送る条件は `backend/app/services/calendar_service.py:220` `_get_sync_target`・`:222` `if sync_mode in ("bidirectional", "write_only") and connected_by == user_id:`。`_get_sync_target` は `:57-67`（行が無ければ `('none', None)`） | **直った**。`:222` もこの関数に置き換えると書いてある。ただし接続状態の口の書き方が 2 通りある（R4-3） |
| N-2 失敗を画面が知る道が無い | §5-7「返事」152 行目・画面「保存のあと」161 行目・文字 162 行目 | 返事は `calendar_service.py:251`・`:290`・`:335` の 3 か所とも `return {"id": event_id}`。口は `routers/calendar.py:365`・`:435` で `return result`。画面 `frontend/src/pages/schedule/SchedulePageImpl.tsx:1247` `saveEvent`、`:1263` `api.patch`、`:1265` `api.post`（今は返事を捨てている）。`frontend/src/lib/api.ts:246` `post: <T>`・`:253` `patch: <T>` は型を受け取れる。知らせの帯 `:1103` `useState<{ type: "success" \| "error"; …}>`、`:1473-1478` で `error-banner`。前例 `:1161` `setBanner({ type: "error", message: t("schedule.connectError") })` | **直った**。返事の 3 か所、口の 2 か所、画面の受け取り口、帯の置き場所がすべて実物と一致。新しい部品を作らない |
| N-3 判定に要る値を UPDATE の前に読む | §5-7「直す」151 行目 | 口の SELECT `routers/calendar.py:391` `SELECT created_by_user_id, calendar_type, user_id FROM calendar_events WHERE id = :id`、`:398` で `record[0..2]` を取り出す。サービスの `google_event_id` の読み取りは UPDATE（`:294-298`）の後の `:302-307` | **直った**。口の `:391` に `google_event_id, meet_url` を足す。ただし今の口の試験の作りと合わない（R4-2） |
| N-13 持ち主も見る | §5-7「直す」(3) | `event_owner` は `routers/calendar.py:399`。持ち主を見ずに送るのは `calendar_service.py:309-310` | **直った** |
| 口の試験の置き場所 | §5-7「試験」164 行目 | `backend/tests/test_calendar_owner_api.py:10-18` の import（`UpdateEventBody`・`update_event` はあるが `create_event`・`CreateEventBody` は無い）、`:191` `patch("app.routers.calendar.cal_svc.update_event", new=AsyncMock())`、`:240` `test_invalid_calendar_type_is_422` | **直った**（置き場所・前例は正しい）。import に `create_event`・`CreateEventBody` を足す、は書いておくとよい（R4-5） |

## 2. 新しい行番号の突き合わせ（全部）

| 設計の参照 | 実物 | 一致 |
|---|---|---|
| `routers/calendar.py:104-112` `CreateEventBody`・`:114-121` `UpdateEventBody` | 104-111・114-121 | ○ |
| `routers/calendar.py:340`・`:352`・`:359`・`:365` | 同じ | ○ |
| `routers/calendar.py:374`・`:391`・`:399`・`:421`・`:429`・`:435` | 同じ | ○ |
| `calendar_service.py:57` `_get_sync_target`・`:180` `create_event`・`:193` INSERT・`:220-222` | 同じ | ○ |
| `calendar_service.py:251`・`:259`・`:289-290`・`:290`・`:302-307`・`:309-310`・`:335` | 同じ | ○ |
| `calendar_service.py:134` 一覧の SELECT・`:410` `upsert_from_google`・`:476-486` ON CONFLICT・`:486` `WHERE calendar_events.source = 'google'` | 同じ | ○ |
| `google_calendar.py:348`・`:377`・`:392`・`:407` | 同じ | ○ |
| `routers/google_calendar.py:242` `connection_status`・`:243-244` | 同じ（SELECT は `:247-253` で `calendar_id, connected_at` だけ） | ○ |
| `SchedulePageImpl.tsx:1247-1273` `saveEvent`・`:1103`・`:1473-1478` | 同じ | ○ |
| `api.ts:246`・`:253` | 同じ | ○ |
| `schedule-utils.ts:13` `ApiCalendarEvent`・`:46` `ScheduleItem` | 同じ | ○ |
| `schedule-utils.ts:159` `normalizeEvent` | **`:201`**（`:159` は別の関数の中の行） | × ずれ（R4-4） |
| `scripts/run_all_migrations.sh:377`（078）・`:1217`（前例） | 同じ。ただし今の末尾は `:1219`（`20261105_100000_tenant_discord_config_purpose.sql`） | ○（「末尾に足す」で正しい） |
| `migrations/20261103_200000_add_google_calendar_import_sync.sql:11-34` | 11 `DO $gcal_import_uniq$`・34 で閉じる | ○ |
| §7-3 の 2: `tenant.py` に calendar 0 件・`create_tenant_schema` `:1658`・`078` `:44` | 0 件・`:1658`・`:44` `CREATE TABLE IF NOT EXISTS %I.calendar_events` | ○ |
| §7-3 の 3: `test_calendar_service.py:77`・`:231`・`:283`・`:309` | 同じ | ○ |
| §7-3 の 1・4（本番の同期方式 bidirectional・会社 4 の 1 行）・§7-7 の数 | この審査では本番に接続していない | 未確認（設計の記録をそのまま受け取る） |

## 3. 新しい穴

- **R4-1（穴）`add_meet` だけの直しで Google の予定の題と時刻を消す**: 設計は「`add_meet` だけ送られた場合はこの早戻り（`:289-290`）の前に Meet を処理する」と書くが、何を Google に送るかを書いていない。今の直す道は `_to_google_event_body(payload)`（`calendar_service.py:314`）で中身を作り、この関数は `payload.get("title", "")` で `summary` を空にし（`:512`）、`start_datetime` が無いと `{"dateTime": "", …}` を作る（`:515-523`）。`{"add_meet": true}` だけの payload でこれを `patch` に渡すと、Google の予定の題が空になるか、時刻が不正で断られる。**直す案**: 5-7「直す」に「`add_meet` だけのとき（`set_clauses` が空のとき）は `_to_google_event_body` を使わず、`{"conferenceData": {"createRequest": …}}` だけを `patch` で送る」と書き、試験に 1 件（題・時刻を送らないこと）を足す。画面はふつう全部の欄を送るので当たらないが、設計で開けた道なので閉じ方も書く。
- **R4-2（穴）口の SELECT に列を足すと今の口の試験 4 件が壊れる**: `test_calendar_owner_api.py:178-182` の `_event_db` は `first=(created_by, calendar_type, owner)` の 3 つだけを返す。口が `:391` で 5 列を読み `record[3]`・`record[4]` を取り出すと、`:187`・`:212`・`:226`・`:240` の 4 件が `IndexError`（口の try の外なので 500 にもならず落ちる）。**直す案**: 5-7「試験」に「`_event_db` に `google_event_id=None, meet_url=None` の既定つき引数を足して 5 つ返す形にする（今の 4 件の呼び方は変えない）」と書く。
- **R4-3（不整合・軽い）`meet_available` の出し方が 2 通り**: 148 行目は「接続状態の口の `meet_available` もこの関数（`can_add_meet`）で出す」、156 行目は「`connection_status` の SELECT に `sync_mode`・`connected_by_user_id` を足して…真 = 接続あり かつ … かつ …」と自前で式を書く。後者で作ると式が 2 か所になり、148 行目の「式を 2 か所に置かない」に反する。**直す案**: 156 行目を「`user` を受け取り、`meet_available = await cal_svc.can_add_meet(db, tenant_id, user.id)` を返す（SELECT は今のまま）」に寄せる。行が無いときは `_get_sync_target` が `('none', None)` を返すので「接続あり」も同じ式で満たされる。
- **R4-4（ずれ）`normalizeEvent` の行**: 157 行目の `schedule-utils.ts:159` は `:201`。
- **R4-5（書き足し・軽い）画面から何を送るか**: 「保存のあと」は返事の扱いを書いたが、`saveEvent` の `body`（`:1249-1260`）に `add_meet` をいつ入れるかが無い。「`meet_available` が真で Toggle が入っているときだけ `body.add_meet = true`」「直す小窓で `meetUrl` がすでにあるときは Toggle を出さず参加の釦だけ出す（口で外すので害は無いが、押しても何も起きない Toggle を出さない）」「帯を出す条件は『`add_meet: true` を送った かつ 返事の `meet_url` が null』」の 3 行を足す。あわせて口の試験の import（`:10-18`）に `create_event`・`CreateEventBody` を足す、と書く。

注意（直さなくてよい）:
- 作る口は `body.model_dump(exclude_none=True)` を渡すので `add_meet: False` も payload に入るが、INSERT は欄を名指しで読み（`calendar_service.py:203-214`）、`_to_google_event_body` も名指しなので害は無い。直す口も `field_map`（`:271-280`）に無い鍵は無視される。
- アプリから作った予定に Google 側で Meet を足しても、取り込みは `source='google'` の行だけ更新する（`:486`）ので `meet_url` には入らない。ADR に「アプリから作った予定の Meet はアプリから付ける」と 1 行書いておくと後で迷わない。
- Workspace の管理者が Meet を止めているとき、`conferenceDataVersion=1` 付きの作成が予定ごと断られるのか、予定は作られ `createRequest.status` が `failure` になるのかは、この審査では確かめていない（未確認）。前者なら予定が Google に入らず `sync_status='failed'` になる（`:241-249`）。§7-3 のリスク 3 の「予定は保存し」はアプリ側の行としては守られるが、Google 側に入らない場合があることを §7-3 に書き足すとよい。

## 4. 根拠と直す案のまとめ

- 根拠: N-1・N-2・N-3・N-13 は実物の行と一致して直った。新しい行番号は `schedule-utils.ts:159` 以外すべて一致。R4-1（`calendar_service.py:314`・`:512-523` で `add_meet` だけの直しが題と時刻を空で送る）と R4-2（`test_calendar_owner_api.py:181` が 3 つしか返さず、5 列を読む口で 4 件が落ちる）は、書いたとおりに作ると壊れる。
- 直す案: 5-7 に R4-1（`add_meet` だけのときは `conferenceData` だけを送る）・R4-2（`_event_db` を 5 つ返す形に）・R4-3（`meet_available` は `can_add_meet` を呼ぶだけ）・R4-4（`:201`）・R4-5（送る条件・Toggle の出し方・import）を書き足す。直したら §11-3 の便3 のカードを書いてよい。便3 は表の列を足すので、実装のあとも PO の「GO #番号」が要る（§9 のとおり）。
