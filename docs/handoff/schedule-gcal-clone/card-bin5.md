# card: 便5 題名で予定を探す（G12）（2026-11-07）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §3.5・§3.11（便5 の作り方）
- 成功条件: G12「虫めがねを押すと検索の欄が出て、題名の一部で予定が探せ、押すとその日へ飛ぶ」（「商談」で探す）
- 区分: B-1（裏側の読み取り専用の道 1 本＋画面）。DB の形・migrations・workflow・本番 scripts は触らない。依存は足さない。

## 0. 始める前（必須）

1. 起点: **便4（PR #5263）が main に入った後の origin/main** から `release/schedule-gcal-search-bin5-impl` を作る。`git log origin/main --oneline -20 | grep 5263` で入ったことを確かめる。無ければ止めて報告（BLOCKED）。
2. 行番号は 2026-11-07 の origin/main 67d7bbf87 のもの。ずれていたら **下の「目印」の文字の並びで場所を探す**。目印が見つからなければ止めて報告。
3. `./scripts/dev/executor-preflight.sh || exit 1`

## 1. 触るファイルと触らない範囲

| ファイル | 変え方 |
|---|---|
| `backend/app/services/calendar_service.py` | `list_events` に省略できる引数を足す。§2 |
| `backend/app/routers/calendar.py` | `GET /calendar/events/search` を足す。§3 |
| `backend/tests/test_calendar_service.py` | 試験 S1〜S4 を足す。§6 |
| `backend/tests/test_calendar_events_search_api.py` | 新規。試験 A1〜A3。§6 |
| `frontend/api-contract/openapi.json` | 生成し直す（手で書かない）。§4 |
| `frontend/src/pages/schedule/schedule-utils.ts` | `formatSearchResultLine` を足す。§5 |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 虫めがね・検索の欄・結果。§5 |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | `schedule` の中に 3 キーを足す（両方同じキー）。§5 |
| `frontend/src/pages/schedule/schedule-utils.test.ts` | 試験 U1・U2。§6 |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | 作り物に検索の道を足す・試験 F1〜F5。§6 |

触らない: `frontend/src/components/`（金型）、`frontend/src/pages/schedule.css`（新しい見た目の規則は足さない。足さないと形が崩れる場合は止めて報告）、DB・migrations、`/calendar/events`（期間の一覧）の動き、祝日の道。

## 2. `backend/app/services/calendar_service.py` の `list_events`

目印: `async def list_events(` と、その中の `filters = [` `"start_datetime < :end",` `"end_datetime > :start",`、`f" ORDER BY ce.start_datetime"`。

変更前:

```python
async def list_events(
    db: AsyncSession,
    tenant_id: int,
    start: str,
    end: str,
    calendar_type: Optional[str] = None,
    user_id: Optional[int] = None,
) -> list[dict]:
    ...
    filters = [
        "start_datetime < :end",
        "end_datetime > :start",
    ]
    params: dict = {"start": _parse_dt(start), "end": _parse_dt(end)}
```

変更後:

```python
async def list_events(
    db: AsyncSession,
    tenant_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    calendar_type: Optional[str] = None,
    user_id: Optional[int] = None,
    title_query: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    ...（説明の文に 1 行足す: title_query は題名の部分一致（%・_・\ は文字として扱う）。指定時は新しい順・limit 件まで）
    filters: list[str] = []
    params: dict = {}
    if end is not None:
        filters.append("start_datetime < :end")
        params["end"] = _parse_dt(end)
    if start is not None:
        filters.append("end_datetime > :start")
        params["start"] = _parse_dt(start)
```

- 期間を渡す今の呼び出しで、SQL の文字の並びが変わらないよう、**`start_datetime < :end` を先・`end_datetime > :start` を後**の順で足す（**必ず上の順（`if end` が先・`if start` が後）で書く**。今の順「`start_datetime < :end` → `end_datetime > :start`」（`backend/app/services/calendar_service.py:164-167`）と同じにするため。入れ替えない）。
- `calendar_type` の枝はそのまま（`filters.append(...)` のまま）。
- `where = " AND ".join(f"ce.{f}" for f in filters)` は、filters が空のとき空文字になる。その直後の見せ方の絞り（`if user_id is None: where += " AND ce.calendar_type = 'shared'"` ／ `else: where += " AND (ce.calendar_type = 'shared' OR ce.user_id = :me)"`）が `" AND ..."` で始まるため、**空のときは `"TRUE"` から始める**:

```python
    where = " AND ".join(f"ce.{f}" for f in filters) or "TRUE"
```

- 題名の条件（見せ方の絞りの後に足す）:

```python
    if title_query is not None:
        escaped = title_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where += " AND ce.title ILIKE :title_q ESCAPE '\\'"
        params["title_q"] = f"%{escaped}%"
```

- 並びと件数（`f" ORDER BY ce.start_datetime"` の 1 行を置き換える）:

```python
            f" ORDER BY ce.start_datetime{' DESC' if title_query is not None else ''}"
            f"{' LIMIT :limit' if limit is not None else ''}"
```

  `limit` があるときは `params["limit"] = limit`。

- 返す dict の形は変えない。

## 3. `backend/app/routers/calendar.py`

目印: `@router.get("/calendar/events", tags=["calendar"])` の `list_events` 関数の `return {"events": events}` の直後（`class HolidayItem` の前）に足す。

```python
_SEARCH_MAX_RESULTS = 50


@router.get("/calendar/events/search", tags=["calendar"])
async def search_events(
    q: str = Query(..., description="題名の一部（前後の空白は除く・1〜100 文字）"),
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """題名の一部で予定を探す。見せてよい予定の決まりは list_events と同じ。新しい順・最大 50 件。"""
    query = q.strip()
    if not 1 <= len(query) <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid search query",
        )
    events = await cal_svc.list_events(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        title_query=query,
        limit=_SEARCH_MAX_RESULTS,
    )
    return {"events": events}
```

- ファイル冒頭の道の一覧の説明に `GET    /calendar/events/search  — 題名で予定を探す` を 1 行足す（`GET    /calendar/holidays` の行の前）。
- `/calendar/events/{event_id}` は PATCH・DELETE だけなので、GET の `/calendar/events/search` とはぶつからない（念のため A1 で 200 を確かめる）。

## 4. `frontend/api-contract/openapi.json`

便4 と同じ手順で生成し直す（手で書かない）。差分が `/api/v1/calendar/events/search` の 1 本だけであることを確かめる（他の道が変わったら止めて報告）。tsc の前に `npm run generate:api-types` が要る（生成物は git の対象外。commit しない）。

## 5. 画面

### 5-1. `frontend/src/locales/ja.json`・`en.json` の `schedule` に 3 キー（両方同じ場所に足す）

| キー | ja | en |
|---|---|---|
| `searchPlaceholder` | 題名で予定を探す | Search events by title |
| `searchResults` | 検索の結果 | Search results |
| `searchNoResults` | 見つかりませんでした | No matching events |

### 5-2. `frontend/src/pages/schedule/schedule-utils.ts`

`formatDraftDateLine` の直後に足す:

```ts
/** 検索の結果の 2 行目（便5 G12）。終日は「11月10日(火) 終日」、時間ありは formatDraftDateLine と同じ形 */
export function formatSearchResultLine(item: ScheduleItem, t: Translate, language: string): string {
  return formatDraftDateLine(
    {
      startDate: formatDateInput(item.start),
      startTime: formatTimeInput(item.start),
      endDate: item.allDay ? formatDateInput(item.start) : formatDateInput(item.end),
      endTime: formatTimeInput(item.end),
      allDay: item.allDay,
    },
    t,
    language,
  );
}
```

（`Translate`・`formatDateInput`・`formatTimeInput` は同じファイルにある。無ければ止めて報告）

### 5-3. `frontend/src/pages/schedule/SchedulePageImpl.tsx`

1. import: 金型 `Popover`（`../../components/Popover`）・`ListRow`（`../../components/ListRow`）・`EmptyState`（`../../components/EmptyState`）を足す。schedule-utils からの import に `formatSearchResultLine` を足す。
2. 状態（目印: `const [viewMenu, setViewMenu] = useState<` の直後）:

```ts
  // 便5（G12）: 検索の欄・打った文字・Enter で決めた文字・結果の小窓
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [searchQuery, setSearchQuery] = useState<string | null>(null);
  const [searchResultsOpen, setSearchResultsOpen] = useState(false);
```

3. 読み込み（目印: 祝日の `const holidaysQ = useApiQuery<` の文の直後）:

```ts
  const searchQ = useApiQuery<{ events: ApiCalendarEvent[] }>(
    `/calendar/events/search?q=${encodeURIComponent(searchQuery ?? "")}`,
    { enabled: live && searchQuery !== null },
  );
  const searchResults = useMemo(
    () => (Array.isArray(searchQ.data?.events) ? searchQ.data.events.map(normalizeEvent) : []),
    [searchQ.data],
  );
```

4. 閉じる・飛ぶ（目印: `const SearchIcon = NAV_ICONS.search;` の直後）:

```ts
  const closeSearch = () => {
    setSearchOpen(false);
    setSearchText("");
    setSearchQuery(null);
    setSearchResultsOpen(false);
  };
  const jumpToResult = (item: ScheduleItem) => {
    setAnchorDate(new Date(item.start.getFullYear(), item.start.getMonth(), item.start.getDate()));
    closeSearch();
  };
```

5. 見出しの虫めがね（目印: `aria-label={t("common.search")}` を持つ `<Button` ブロック。今は `onClick` が無い）を、次に置き換える:

```tsx
            {searchOpen ? (
              <Popover
                open={searchResultsOpen}
                onOpenChange={setSearchResultsOpen}
                placement="bottom"
                content={
                  <div role="listbox" aria-label={t("schedule.searchResults")}>
                    {searchQ.isLoading ? null : searchResults.length === 0 ? (
                      <EmptyState size="compact" title={t("schedule.searchNoResults")} />
                    ) : (
                      searchResults.map((item) => (
                        <ListRow
                          key={item.id}
                          title={item.title}
                          subtitle={formatSearchResultLine(item, t, i18n.language)}
                          onClick={() => jumpToResult(item)}
                        />
                      ))
                    )}
                  </div>
                }
              >
                <TextFieldControl
                  variant="search"
                  type="search"
                  autoFocus
                  aria-label={t("common.search")}
                  placeholder={t("schedule.searchPlaceholder")}
                  value={searchText}
                  onChange={(event) => setSearchText(event.target.value)}
                  // 金型 Popover はトリガーを押すと開閉が切り替わる（Popover.tsx handleTriggerClick）。欄を押して直すたびに結果が閉じないよう止める
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => {
                    // 変換中の Enter は確定なので探さない（Safari は確定の Enter で isComposing が偽になるため 229 も見る。今の近道 SchedulePageImpl.tsx:1284-1285 と同じ形）
                    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
                    if (event.key === "Enter") {
                      const next = searchText.trim();
                      if (next.length === 0) return;
                      setSearchQuery(next);
                      setSearchResultsOpen(true);
                    } else if (event.key === "Escape") {
                      event.stopPropagation();
                      closeSearch();
                    }
                  }}
                />
              </Popover>
            ) : (
              <Button
                variant="ghost"
                size="md"
                iconOnly
                aria-label={t("common.search")}
                onClick={() => setSearchOpen(true)}
              >
                <SearchIcon size={18} aria-hidden="true" />
              </Button>
            )}
```

- `searchQ.isLoading` が `useApiQuery` の返り値に無い場合は、同じ意味の名前（例: `isFetching`・`isPending`）を `frontend/src/lib/query/apiQuery.ts` で確かめて使う。どれも無ければ止めて報告。
- `ListRow` の `onClick` で行が押せる形にならない（button や role が付かない）場合は止めて報告（金型は変えない）。
- `TextFieldControl` が `onClick`・`onKeyDown`・`autoFocus` を input に渡さない場合は止めて報告。
- 色・大きさ・余白の直値は書かない。schedule.css も変えない。

## 6. 試験

### 裏側

`backend/tests/test_calendar_service.py`（今の `list_events` の試験と同じ作り: `_make_db()` で作り物の DB を作り、`db.execute` に渡った SQL の文字と params を見る）:

- S1: `list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30")` の SQL に `ILIKE`・`LIMIT`・`DESC` が無く、`ce.start_datetime < :end AND ce.end_datetime > :start` がこの順で入る（今の呼び出しが変わらない）。
- S2: `list_events(db, tenant_id=1, user_id=7, title_query="商談", limit=50)` の SQL に `ce.title ILIKE :title_q ESCAPE`・`ORDER BY ce.start_datetime DESC`・`LIMIT :limit`・`(ce.calendar_type = 'shared' OR ce.user_id = :me)` が入り、`:start`・`:end` が入らない。params は `title_q == "%商談%"`・`limit == 50`・`me == 7`。
- S3: `title_query="50%_off\\"` で `params["title_q"] == "%50\\%\\_off\\\\%"`。
- S4: `title_query="x"`・`user_id=None` で SQL が `WHERE TRUE AND ce.calendar_type = 'shared'` を含む（期間なしでも WHERE が壊れない）。

`backend/tests/test_calendar_events_search_api.py`（新規。便4 の `test_calendar_holidays_api.py` と同じく関数を直接呼ぶ。`cal_svc.list_events` は `unittest.mock.patch` で作り物にする）:

- A1: `search_events(q="  商談 ", tenant_id=1, user=<id=7 の作り物>, db=<作り物>)` が `{"events": [...]}` を返し、作り物の `list_events` が `title_query="商談"`・`limit=50`・`user_id=7` で呼ばれ、`start`・`end` を渡さない。
- A2: `q="   "`（空白だけ）で 422。
- A3: `q` が 101 文字で 422。100 文字は通る。

### 画面

`frontend/src/pages/schedule/schedule-utils.test.ts`:

- U1: 時間ありの予定（2026-11-10 10:00〜11:00）で `formatSearchResultLine` が `formatDraftDateLine` に同じ値を渡したときと同じ文を返す。
- U2: 終日の予定（start 2026-11-10・end 2026-11-11）で、文に日付が 1 つだけ入り（`11/11` や「11日」が入らない）、`schedule.allDay` の訳が入る。

`frontend/src/pages/schedule/SchedulePageImpl.test.tsx`:

- 作り物の api（目印: `if (path.startsWith("/calendar/events")) return { events: answers.events };`）の**前**に `if (path.startsWith("/calendar/events/search")) return { events: answers.searchEvents };` を足す。`answers` に `searchEvents: [] as ...`（`events` と同じ型）と、初期化に `answers.searchEvents = [];` を足す。
- F1: 虫めがね（`common.search` の名前のボタン）を押すと検索の欄（role searchbox か textbox で同じ名前）が出て、focus がそこにある。
- F2: `answers.searchEvents` に「商談A」（2026-12-15 10:00〜11:00）を入れ、欄に「商談」と打って Enter → 作り物の api が `/calendar/events/search?q=%E5%95%86%E8%AB%87` で呼ばれ、結果に「商談A」が出る。
- F3: F2 の結果の行を押すと、`rangeText()` が次の `expected` と一致する。`` const days = getWeekDays(new Date(2026, 11, 15)); const expected = `${formatDayLabel(days[0])} - ${formatDayLabel(days[6])}`; ``（`formatDayLabel`・`getWeekDays` は `frontend/src/pages/schedule/schedule-utils.ts:137`・`:161` で export 済み。週の見出しは `frontend/src/pages/schedule/SchedulePageImpl.tsx:138-144` の `formatRangeTitle` がこの形で作り `:1162` の `viewLabel` に入る。`frontend/src/pages/schedule/SchedulePageImpl.tsx` に export は足さない）。検索の欄が閉じて虫めがねのボタンに戻る。
- 見出しの文を読む小さな関数 `rangeText()`（`.schedule-shell__range` の textContent を返す）を F の describe の中で定義する（今の `rangeText` は `frontend/src/pages/schedule/SchedulePageImpl.test.tsx:249` の K7 の describe の中だけにあり、F からは使えない）。
- F4: `answers.searchEvents = []` で Enter → 「schedule.searchNoResults」の文（訳のキーで見る今の試験の流儀に合わせる）が出る。
- F5: 欄で Esc → 欄が閉じて虫めがねのボタンに戻る。続けて `t` を押すと今日へ戻る近道が今までどおり効く（Esc が近道を壊していない）。

## 7. 確かめ（push 前に全部）

1. `cd backend && pytest tests/test_calendar_service.py tests/test_calendar_events_search_api.py tests/test_calendar_holidays_api.py -q` が全部合格。
2. `ruff check` で今回触った py ファイルにエラーなし。
3. `cd frontend && npm run generate:api-types && npx tsc --noEmit` が終了コード 0。
4. `npx vitest run src/pages/schedule` が失敗 0（ブラウザ型の 1 ファイルが chromium 無しで起動できないのは可。CI で確かめる）。
5. `npm run check:all`・`npm run lint`（エラー 0）・`npm run build` が合格。
6. ja.json と en.json のキー数が同じ。
7. openapi.json の差分が検索の道 1 本だけ。
8. push 前の入口の検査（`scripts/dev/check-before-submit.sh`）で落ちた検査 0 件。

## 8. 想定の分かれ道（迷ったら止める）

- 目印が見つからない／行が大きくずれている → 止めて報告。
- `useApiQuery` が `enabled: false` でも呼ぶ（作り物の api が `q=` 空で呼ばれる）→ 止めて報告。
- 金型を変えないと形が成り立たない（ListRow が押せない・Popover の位置が欄に付かない等）→ 止めて報告。金型は変えない。
- 試験の名前や期待値がこのカードと合わない所が出た → 直さず止めて報告。
- 完了報告に「カードと違う所」を必ず書く（無ければ「なし」）。
