# card: 便4 日本の祝日を予定の画面の終日の行に出す（G7・G9）（2026-11-07）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §3.4（出どころ＝案 C）・§3.6（祝日は動かせない）・§3.10（便4 の作り方）
- 成功条件: G7「日本の祝日（例: 11/3 文化の日、11/23 勤労感謝の日）が終日の行に出る」（11 月の週と月で見る）／G9 のうち「祝日はつかめない・押しても何も開かない」
- 区分: B-1（裏側の読み取り専用の道 1 本＋画面）。DB・migrations・workflow・本番 scripts は触らない。依存を 1 つ足す（`holidays==0.108`）。

## 0. 始める前（必須）

1. 起点: **便3（PR #5261）が main に入った後の origin/main** から `release/schedule-gcal-holiday-bin4-impl` を作る。便3 も `SchedulePageImpl.tsx`・`SchedulePageImpl.test.tsx` を変えるので、便3 より前の main から作らない。
   - `git log origin/main --oneline -20 | grep 5261` で入ったことを確かめる。無ければ止めて報告（BLOCKED）。
2. 行番号は 2026-11-07 の origin/main 18565cd1b のもの。便3 で `SchedulePageImpl.tsx` の行はずれるので、**書いてある文字の並び（下の「目印」）で場所を探す**。目印が見つからなければ止めて報告。
3. `./scripts/dev/executor-preflight.sh || exit 1`

## 1. 触るファイルと触らない範囲

| ファイル | 変え方 |
|---|---|
| `backend/requirements.txt` | `holidays==0.108` を 1 行足す（並びは近い行の流儀に合わせる） |
| `backend/app/services/holiday_service.py` | 新規。§2 |
| `backend/app/routers/calendar.py` | `GET /calendar/holidays` を足す。§3 |
| `backend/tests/test_holiday_service.py` | 新規。§6 |
| `backend/tests/test_calendar_holidays_api.py` | 新規。§6 |
| `frontend/api-contract/openapi.json` | 生成し直す（手で書かない）。§4 |
| `frontend/src/pages/schedule/schedule-utils.ts` | `ApiHoliday` 型と `toHolidayEvents` を足す。§5 |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 祝日を読む・`calendarEvents` に足す。§5 |
| `frontend/src/pages/schedule/schedule-utils.test.ts` | `toHolidayEvents` の試験。§6 |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | 祝日の試験 H1・H2 と、api の作り物に祝日の道を足す。§6 |

触らない: `frontend/src/components/`（金型。`tone: "holiday"` の色は `calendarView.utils.ts:16`・`CalendarView.css:139-142` に既にある）、ja.json・en.json（新しい文言は無い。祝日の名前は裏側が言語ごとに返す）、DB・migrations、`google_calendar.py`、予定の一覧（`/calendar/events`）の中身、一覧表示（list）の画面。

## 2. `backend/app/services/holiday_service.py`（新規・この形のまま）

```python
"""日本の祝日（ADR なし・design schedule-gcal-clone §3.4 案 C）。

正本は PyPI の holidays 部品 1 か所。DB には持たない。
翌年分は部品の版上げで入る（内閣府の翌年分の掲載は毎年 2 月）。
"""
from __future__ import annotations

from datetime import date

import holidays

# 画面の言語 → 部品の言語（JP が持つのは en_US・ja・th）
_LANGUAGES = {"ja": "ja", "en": "en_US"}


def list_japan_holidays(start: date, end: date, lang: str = "ja") -> list[dict[str, str]]:
    """start 以上 end 未満の日本の祝日を、日付の早い順に返す。"""
    language = _LANGUAGES.get(lang, "ja")
    years = range(start.year, end.year + 1)
    jp = holidays.country_holidays("JP", years=years, language=language)
    return [
        {"date": day.isoformat(), "name": jp[day]}
        for day in sorted(jp)
        if start <= day < end
    ]
```

## 3. `backend/app/routers/calendar.py`

- 目印: `@router.get("/calendar/events", tags=["calendar"])`（18565cd1b で :138）の関数 `list_events` の終わり（`return {"events": events}`）の後、`# 担当者一覧 / 設定` の区切りの前に足す。
- import: `from datetime import date` を `import logging`（:17）の後に、`from app.services import holiday_service` を `from app.services import calendar_service as cal_svc`（:36）の後に足す。
- 冒頭の説明（:6-12 のエンドポイント一覧）に `GET    /calendar/holidays       — 日本の祝日（期間・言語）` を 1 行足す。

```python
class HolidayItem(BaseModel):
    date: str
    name: str


class HolidayListResponse(BaseModel):
    holidays: list[HolidayItem]


# 長すぎる期間は断る（月の表示は最大 31 日。年をまたぐ見方も 400 日に収まる）
_HOLIDAY_MAX_DAYS = 400


@router.get("/calendar/holidays", tags=["calendar"], response_model=HolidayListResponse)
async def list_holidays(
    start: date = Query(..., description="この日から（含む） 例: 2026-11-01"),
    end: date = Query(..., description="この日まで（含まない） 例: 2026-12-01"),
    lang: str = Query("ja", pattern="^(ja|en)$", description="祝日の名前の言語"),
    tenant_id: int = Depends(get_current_tenant),
):
    """日本の祝日を期間で返す。会社によらず同じ（ログインは要る）。"""
    if end <= start or (end - start).days > _HOLIDAY_MAX_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid holiday range",
        )
    return {"holidays": holiday_service.list_japan_holidays(start, end, lang)}
```

- `tenant_id` は使わないが、ログインしていない人に返さないために残す（他の道と同じ `get_current_tenant`）。
- `HolidayItem` の `date` という名前の欄と `from datetime import date` がぶつかる場合（pydantic が型を読み違えて import や openapi 生成が失敗する場合）は、欄の型の注記を `str` のままにし、import を `import datetime as dt` に変えて `start: dt.date`・`end: dt.date`・`(end - start).days` とする。どちらにしたかを報告に書く。

## 4. openapi.json

`cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を実行して生成し、差分が `/api/v1/calendar/holidays` と `HolidayItem`・`HolidayListResponse` だけであることを `git diff --stat` と `git diff frontend/api-contract/openapi.json | grep '^[+-]' | head -80` で確かめる。ほかの差分が出たら止めて報告。生成した型（frontend の schema 生成）を使うなら `npm run` の既存の手順に従う（手で型を書く場合は §5 の `ApiHoliday`）。

## 5. 画面

### 5-1 `frontend/src/pages/schedule/schedule-utils.ts`

`normalizeShift` の後（目印: `export function normalizeShift(`）に足す。`CalendarViewEvent` の import が無ければ `../../components/calendarView.utils` から型だけ import する。

```ts
export interface ApiHoliday {
  date: string; // YYYY-MM-DD
  name: string;
}

/** 祝日を金型の予定の形にする。終日・動かせない・tone holiday（design §3.6・§3.10） */
export function toHolidayEvents(holidays: ApiHoliday[] | undefined): CalendarViewEvent[] {
  if (!Array.isArray(holidays)) return [];
  return holidays.flatMap((holiday) => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(holiday.date);
    if (!match) return [];
    const start = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    return [{
      id: `holiday-${holiday.date}`,
      title: holiday.name,
      start: holiday.date,
      end: formatDateInput(addDays(start, 1)),
      allDay: true,
      tone: "holiday" as const,
      editable: false,
    }];
  });
}
```

### 5-2 `frontend/src/pages/schedule/SchedulePageImpl.tsx`

1. 目印 `export default function SchedulePage` の中（または `const eventsQ = useApiQuery` を持つ関数）の `const { t } = useTranslation();` を `const { t, i18n } = useTranslation();` にする（その関数の 1 か所だけ）。
2. 目印 `const shiftsQ = useApiQuery<ApiShift[]>(` の塊の後に足す:

```ts
  // 便4（G7）: 日本の祝日。会社によらず同じ。取れなくても予定の画面は止めない（読み込み中・失敗の文には入れない）
  const holidayLang = i18n.language?.startsWith("en") ? "en" : "ja";
  const holidaysQ = useApiQuery<{ holidays: ApiHoliday[] }>(
    `/calendar/holidays?start=${formatDayKey(rangeStart)}&end=${formatDayKey(rangeEnd)}&lang=${holidayLang}`,
    { enabled: live },
  );
```

3. 目印 `const calendarEvents: CalendarViewEvent[] = [` の配列の **最後**（`...visibleEvents.map(...)` の後）に `...toHolidayEvents(holidaysQ.data?.holidays),` を足す。
4. `loading`・`staleFailed` の並び（`[ownersQ, eventsQ, shiftsQ]`）には **足さない**。
5. import に `toHolidayEvents`・`ApiHoliday` を足す（schedule-utils から）。
6. 押したとき: `onEventClick` は `itemById(id)` が null なら何もしない（今の形）。祝日は `visibleEvents` に入らないので何も開かない。ここは変えない。
7. 動かす: `editable: false` で金型がつかませない。`patchMoved` も `itemById` が null で `revert()` する（今の形）。変えない。

- 範囲: 月の表示は月の 1 日〜翌月 1 日（`toRangeEnd`）。升目の前後の月の日には祝日が出ない。予定（`/calendar/events`）も同じ範囲なので揃っている。今回は変えない（design §3.10 に記録）。
- 一覧（list）の表示は金型 CalendarView を使わないので祝日は出ない（G7 は週と月）。

## 6. 試験

### 裏側
`backend/tests/test_holiday_service.py`:
- S1 内閣府の表（2026-11-06 に Mac で取得した syukujitsu.csv）の 2026・2027 年の 35 日と、`list_japan_holidays(date(2026,1,1), date(2028,1,1))` の日付が **全件一致**（順番も同じ・名前は比べない）。正解の 35 日（そのまま書く）:
  2026-01-01, 2026-01-12, 2026-02-11, 2026-02-23, 2026-03-20, 2026-04-29, 2026-05-03, 2026-05-04, 2026-05-05, 2026-05-06, 2026-07-20, 2026-08-11, 2026-09-21, 2026-09-22, 2026-09-23, 2026-10-12, 2026-11-03, 2026-11-23,
  2027-01-01, 2027-01-11, 2027-02-11, 2027-02-23, 2027-03-21, 2027-03-22, 2027-04-29, 2027-05-03, 2027-05-04, 2027-05-05, 2027-07-19, 2027-08-11, 2027-09-20, 2027-09-23, 2027-10-11, 2027-11-03, 2027-11-23
  - 試験の上に「2028 年分は 2027 年 2 月の内閣府の掲載後に部品の版を上げて足す」と 1 行書く。
- S2 `date(2026,11,1)`〜`date(2026,12,1)` は 2 件（11-03・11-23）。名前は ja で「文化の日」「勤労感謝の日」。
- S3 lang="en" で 2026-11-03 の名前が「Culture Day」。（違う英語名が返ったら、その実際の値を報告に書き、試験はその値で書く。値を推測で書かない）
- S4 end は含まない: `date(2026,11,3)`〜`date(2026,11,3)+1日` は 1 件、`date(2026,11,4)`〜`date(2026,11,23)` は 0 件。

`backend/tests/test_calendar_holidays_api.py`（`test_calendar_owner_api.py` と同じく関数を直接呼ぶ形でよい。`tenant_id=1` を渡す）:
- A1 11 月で 2 件を返す。
- A2 `end <= start` は 422。
- A3 401 日は 422、400 日は 200。

### 画面
`schedule-utils.test.ts`:
- U1 `toHolidayEvents([{date:"2026-11-03",name:"文化の日"}])` が `{id:"holiday-2026-11-03", title:"文化の日", start:"2026-11-03", end:"2026-11-04", allDay:true, tone:"holiday", editable:false}`。
- U2 月末: `2026-12-31` の end が `2027-01-01`。
- U3 形の違う日付は除く・`undefined` と `[]`（api の作り物の既定の答え）で空の配列。

`SchedulePageImpl.test.tsx`:
- api の作り物（`vi.mock("../../lib/api"` の `get`）に `if (path.startsWith("/calendar/holidays")) return { holidays: answers.holidays };` を `/calendar/events` の行の前に足し、`answers` に `holidays: [] as Array<Record<string, unknown>>` を足す（各試験の前に `[]` に戻す所があればそこにも足す）。
- H1 `answers.holidays = [{date:"2026-11-03",name:"文化の日"}]` で、金型に渡した `events` に `tone:"holiday"`・`allDay:true`・`editable:false` の「文化の日」がある（`calendarProps.current.events`）。
- H2 その「文化の日」のボタンを押しても予定の小窓（dialog）が開かない。
- H3 祝日の道の url に `lang=ja` と、今の範囲の `start`・`end`（YYYY-MM-DD）が入る（`mockGet` の呼び出しを見る）。

## 7. 確かめ（報告に生の結果を全部書く）

1. `cd backend && pip install -r requirements.txt -r requirements-dev.txt`（holidays 0.108 が入ること: `pip show holidays | head -2`）
2. `cd backend && python -m pytest tests/test_holiday_service.py tests/test_calendar_holidays_api.py tests/test_calendar_owner_api.py -q`
3. `cd backend && ruff check app/services/holiday_service.py app/routers/calendar.py tests/test_holiday_service.py tests/test_calendar_holidays_api.py`
4. openapi 生成（§4）と `git diff --stat`
5. `cd frontend && npx vitest run src/pages/schedule`（ブラウザ型の 1 ファイルがクラウドの chromium 無しで落ちるのは便3 と同じ。その場合はそう書く）
6. `cd frontend && npm run check:all` と `npx tsc --noEmit -p tsconfig.app.json`（無ければ既存の tsc の手順）・`npm run lint`・`npm run build`
7. push は 1 回。`git push -u origin release/schedule-gcal-holiday-bin4-impl`。PR は作らない（Opus が作る）。

## 8. 想定の分岐（迷ったら止めて報告）

- `holidays` が import できない・0.108 が入らない → 止める（版を変えない）。
- S1 で 35 日と 1 日でも違う → 止めて、違う日を全部書く（試験を部品に合わせて直さない）。
- openapi の差分に今回以外が出る → 止める。
- 便3 が main に無い → 止める。
- 目印が見つからない・1 つに決まらない → 止める。

報告の最後の行は `DONE` か `BLOCKED: <理由>`。
