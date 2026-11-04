# architect-review-3: 予定の画面を Google カレンダーに寄せる 便2 再審査（2026-11-04）

- 審査した HEAD: `6f5deecff62ba25cb4920099546bb851d644fe5a`（`origin/release/schedule-gcal-bin2-design`。指定の `6f5deecff` で始まることを `git rev-parse HEAD` で確認）
- **判定: 便2 = APPROVE**（実装カードに書き足すこと N-14〜N-17 あり。design の直しは要らない）
- 見た差分: `git diff 0f297666c 6f5deecff`（design.md だけ、+37/−6。§0 状態・§3・§4・§5-6・§7 の 6〜8・§9・§10・§14）
- 前回の指摘: `origin/release/schedule-gcal-alignment-review2:docs/handoff/schedule-gcal-alignment/architect-review-2.md` の N-5・N-11・N-12
- 実物: `origin/main` `0f297666c`（この枝は main に design.md の 1 ファイルを足しただけで、コードは main と同じ。`git diff --stat 0f297666c HEAD` で確認）
- 審査役: クラウドの Architect（design を書いた AI とは別のセッション）。コードは直していない。リポジトリの試験は流していない（下の §2 の確かめは、関数の写しを Python 3.12.3 で動かしたもの）
- 対象は便2 だけ。便1・便3 は見ていない

---

## 1. N-5・N-11・N-12 は直ったか

| 指摘 | design の直した行 | 実物（origin/main 0f297666c） | 結果 |
|---|---|---|---|
| N-5 終日が Google で 1 日前 | §5-6 125-141・§3 33・§4 47・§7 の 7（186）・§10 219 | 下の §2 で道を全部たどった | **直った** |
| N-11 行の高さ | §5-6 118・§7 の 6（185） | `SchedulePageImpl.tsx:91` `const DEFAULT_ROW_HEIGHT = 48;`・`:651` `const rowHeight = DEFAULT_ROW_HEIGHT;`・`:1184` `next.scrollTop = WORKDAY_START * DEFAULT_ROW_HEIGHT;`・`tokens.css:400` `--schedule-row-height: 48px` | **直った**（引数で受け取り、`getComputedStyle` を使わない。置き場所を増やさない） |
| N-12 category | §5-6 120・§7 の 8（187） | `routers/calendar.py:114-121` `UpdateEventBody` に `category` 無し・`calendar_service.py:271-280` `field_map` にも無し | **直った**（送らない・試験で見ない。補足 N-17） |

### 新しく書かれた行番号の突き合わせ（全部）

| design の行 | 引用 | 実物 | 結果 |
|---|---|---|---|
| 118 | `SchedulePageImpl.tsx:651` `rowHeight` | 651 `const rowHeight = DEFAULT_ROW_HEIGHT;` | 一致 |
| 118・185 | `:91` `DEFAULT_ROW_HEIGHT` | 91 | 一致 |
| 118 | `:1184` 朝の位置 | 1184 `next.scrollTop = WORKDAY_START * DEFAULT_ROW_HEIGHT;` | 一致 |
| 118・185 | `tokens.css:400` | 400 `--schedule-row-height: 48px;` | 一致 |
| 120 | `canEditSelected` `:1336-1338` | 1336 `const canEditSelected = Boolean(`〜1338 `);` | 一致 |
| 121 | 今の保存 `:1247-1257` | 1247 `const saveEvent = async () => {`・1249-1257 `body` | 一致 |
| 121・187 | `routers/calendar.py:114-121` | 114 `class UpdateEventBody`〜121 `calendar_type` | 一致 |
| 121 | `calendar_service.py:314` → `:512` | 314 `google_body = _to_google_event_body(payload)`・512 `"summary": payload.get("title", "")` | 一致 |
| 121 | `:517-522` 終日の崩れ | 終日の分岐は 518-523（前回も指摘した 1 行ずれのまま。直す場所を示す 127・129 行は 518-520 で正しい） | 1 行ずれ（軽微） |
| 127 | 画面 `:1251-1252` | 1251 `combineDateTime(draft.startDate, draft.allDay ? "00:00" : …).toISOString()`・1252 同じく `"23:59"` | 一致 |
| 127・129 | `calendar_service.py:518-520` `str(start_dt)[:10]` | 518 `if payload.get("is_all_day"):`・519-520 `[:10]` | 一致 |
| 128 | `_google_times` `:380-394` | 380 `def`〜394 終日の `return`（関数全体は 402 まで。終日の枝の範囲として正しい） | 一致 |
| 129 | `:486` の上書き条件 | 486 `" WHERE calendar_events.source = 'google'"`（`ON CONFLICT` 自体は 476） | 一致 |
| 130 | 作る `:226`・直す `:314` | 226・314 ともに `_to_google_event_body(payload)`。ほかに呼ぶ所は backend に無い（grep） | 一致 |
| 131 | 今の試験 `test_calendar_service.py:93-105` | 93 `def test_all_day_event`〜105。`"2026-06-01"`／`"2026-06-02"` を送り、そのまま `date` になることを見る | 一致 |
| 132 | `_parse_dt` `:32-37` | 32 `def _parse_dt`〜37 `return datetime.fromisoformat(s.replace(" ", "+"))` | 一致 |
| 134 | `_JST` `:377` | 377 `_JST = ZoneInfo("Asia/Tokyo")` | 一致 |
| 135・141 | `TestToGoogleEventBody` | `test_calendar_service.py:77` | 一致 |
| 122 | 月の 1 日 3 件 `:801` | **`slice(0, 3)` は今 `:843`**（便1 の合流で動いた。改訂 3 の「行のずれ」で直し漏れ） | **ずれ**（N-15） |
| 123 | `index.css:184`・`:384` | 184 `#e8f0fe`・384 `#1e3a5f` | 一致 |

---

## 2. 終日の直しを端から端までたどる

### 2-1. 画面の送る形
- 予定の画面は作るも直すも同じ `saveEvent`（`SchedulePageImpl.tsx:1247`）。`:1263` `api.patch`・`:1265` `api.post`。終日は `combineDateTime(日付, "00:00"/"23:59").toISOString()`（`:1251-1252`）。`combineDateTime` は端末の時刻で日時を作る（`schedule-utils.ts:75-77`・`:95-96`）。日本の端末では 7/1 → `2026-06-30T15:00:00.000Z`／`2026-07-01T14:59:00.000Z`。
- **もう 1 つ同じ口を呼ぶ所がある**: 秘書の下書き `frontend/src/features/secretary/SecretaryDraftEvent.tsx:50-58` も `POST /calendar/events` に同じ形（`"00:00"`／`"23:59"` の `toISOString()`）で送る。design には書かれていないが、形が同じなので直しで一緒に正しくなる（N-16）。

### 2-2. 口から裏側へ
- 口は文字のまま渡す: `CreateEventBody`・`UpdateEventBody` の `start_datetime`・`end_datetime` は `str`（`routers/calendar.py:106-107`・`:116-117`）、`model_dump(exclude_none=True)`（`:357`・`:382`）。`_to_google_event_body` に届くのは画面の文字そのもの。design の「値が日付だけ（`T` を含まない）か」で分ける前提は成り立つ。
- 作る道 `calendar_service.py:226`、直す道 `:314`。どちらも `try` の中（`:223-249`・`:313` から）なので、仮に読み取りで例外が出ても `sync_status='failed'` になるだけで 500 にはならない。

### 2-3. 直した後の Google の終わりの日・取り込みとの往復
design 132-134 の手順を写した関数を Python 3.12.3（本番の `backend/Dockerfile` は `python:3.12-slim`）で動かした。`_parse_dt`・`_JST`・`_google_times` は `calendar_service.py:32-37`・`:377-402` をそのまま写した。

| 入力（開始／終わり） | 出る Google の date | design の期待 |
|---|---|---|
| `2026-06-30T15:00:00.000Z`／`2026-07-01T14:59:00.000Z` | `2026-07-01`／`2026-07-02` | 試験 1 と一致 |
| `2026-06-30T15:00:00.000Z`／`2026-07-03T14:59:00.000Z` | `2026-07-01`／`2026-07-04` | 試験 2 と一致 |
| `2026-07-01T00:00:00+09:00`／`2026-07-01T23:59:00+09:00` | `2026-07-01`／`2026-07-02` | 試験 3 と一致 |
| `2026-07-01T00:00:00`／`2026-07-01T23:59:00` | `2026-07-01`／`2026-07-02` | 試験 4 と一致 |
| `2026-07-01`／`2026-07-02`（今の試験の形） | `2026-07-01`／`2026-07-02` | 試験 6 と一致 |
| 往復: 1 行目の結果を `_google_times` に通す | 日本時間 7/1 00:00〜7/1 23:59・終日 | 試験 5 と一致 |

- **Python 3.12 で `.000Z` を読めるか**: 読める。`datetime.fromisoformat` は 3.11 から `Z` と小数の秒を受ける。3.12.3 と 3.11.18 の両方で `2026-06-30T15:00:00.000Z` → `+00:00` 付きの日時になることを確かめた。`_parse_dt` の空白→`+` の置き換えも、`T` 区切りの文字には影響しない。
- **日付だけの今の試験**: 手順 1（`T` が無ければそのまま）で今の期待（`2026-06-01`／`2026-06-02`）が変わらない。
- **アプリの表は正しいまま**: 作る道は `_parse_dt` で読んで表に入れる（`:210-211`）ので表は日本時間 7/1 00:00〜23:59。取り込みは `:486` で `source='google'` の行しか上書きしない。アプリの予定が Google から戻ってきて崩れることは無い（さらに `_is_app_origin` で取り込み自体を飛ばす）。

### 2-4. 作る・直すの両方の道
- 作る: `:226` → 直した関数 → `cal_svc.create_event`。直す: `:314` → 同じ関数 → `cal_svc.update_event`。1 か所で両方直る、は正しい。
- 直す道は送られた欄だけで Google の中身を作る（前回の B-1）。便2 の動かす操作は題名・開始・終了・終日・説明・場所を全部送る（design 121）ので、`is_all_day` も必ず入り、終日の枝を通る。

N-5 の直しは、送る形 → 裏側 → Google の終わりの日 → 取り込みの往復まで、筋が通っている。

---

## 3. 新しい穴・書き足し

いずれも design を直すほどではなく、便2 の実装カードに書けば足りる。

- **N-14（書き足し・大事）月の帯・終日の行で動かすときの終わりの形**: 直した関数は「終わり = 最後の日の 23:59（その日を含む）」を前提に、日付に 1 日足す。動かす操作で終わりを「次の日の 0:00（含まない）」で作ると、Google で 1 日長くなる。確かめた例: `2026-06-30T15:00:00.000Z`／`2026-07-01T15:00:00.000Z`（7/1 の終日を次の日の 0:00 で終わらせた形）→ `2026-07-01`／`2026-07-03`（2 日の予定）。**直す案**: カードに「終日の予定を動かすときは、元の開始と終わりの両方を同じ日数だけずらす（終わりは最後の日の 23:59 のまま）。`combineDateTime(新しい最後の日, "23:59")` で作り直してもよい」と書き、画面の試験（K9）で「終日を 1 日右へ動かしたとき、送る `end_datetime` が新しい最後の日の 23:59（日本時間）」を 1 件足す。
- **N-15（行番号）** design 122 の「1 日 3 件（`:801`）」は今 `SchedulePageImpl.tsx:843`（`dayEvents.slice(0, 3)`）。カードでは `:843` を使う。
- **N-16（書き足し）** 同じ口を呼ぶ所に秘書の下書き（`SecretaryDraftEvent.tsx:50-58`）がある。形が同じなので直しの効き目は同じ。カードの「影響を受ける所」に書き、§7 の 7 の「すでにずれた終日の予定」の数え方にも秘書から作ったものが入ることを書く（数える条件は `is_all_day AND google_event_id IS NOT NULL AND source='app'` で区別は要らない）。
- **N-17（補足）** §7 の 8 の「種類が保存されない」は、直す口だけでなく作る口も同じ。`CreateEventBody`（`routers/calendar.py:104-111`）にも `category` が無いので、作るときも `calendar_service.py:206` の既定 `"meeting"` が入る。台帳に残すときにこの 1 行を足す。
- **N-18（注意）端末の時間帯**: 画面は端末の時刻で 00:00／23:59 を作るので、日本以外の時間帯の端末では、直した後もずれる（例: UTC の端末で 7/1 → `2026-07-01T00:00Z`／`2026-07-01T23:59Z` → 日本時間で 7/1／7/2 → Google `2026-07-01`／`2026-07-03`）。今の表の値も同じく端末に依存しており、便2 で増える穴ではない。使う人が日本だけなら害は無い。カードに「前提: 端末は日本時間」と書けば足りる。
- **N-19（任意）両方の道を試験で見る**: design の試験 1〜6 は関数だけ。`TestCreateEvent`（`test_calendar_service.py:231`）・`TestUpdateEvent`（`:362`）に「終日で作る・直すと、Google に渡す中身の `date` が日本時間の日付と次の日」を 1 件ずつ足すと、将来どちらかの道が関数を通らなくなったときに気づける。
- 手順 1 の「そのまま渡す」は、今の `[:10]` を残す形でもよい（日付だけの文字では同じ結果）。どちらでも試験 6 は通る。

---

## 4. 判定

**便2 = APPROVE**

根拠:
1. N-5: 画面（`SchedulePageImpl.tsx:1251-1252`）→ 口（`routers/calendar.py:106-107`・`:116-117` で文字のまま）→ 裏側（`calendar_service.py:226`・`:314` → `:518-520`）→ Google の date → 取り込み `_google_times`（`:380-394`）の往復まで、直した手順で正しくなることを Python 3.12.3 で確かめた。日付だけの今の試験（`:93-105`）も変わらない。直す場所は関数 1 つで、`migrations/`・`deploy.yml`・本番 `scripts/` に触れない（§4 の危険な道「無し」は正しい）。
2. N-11・N-12: 実物の行と一致し、筋も正しい。
3. 新しい行番号 20 件のうち、一致 18・軽微なずれ 2（121 の `:517-522`・122 の `:801`）。どちらも直す場所の判断には影響しない。

実装カードに書き足すこと: N-14（終日を動かすときの終わりの形と試験 1 件）・N-15（`:843`）・N-16（秘書の下書き）・N-17・N-18。N-19 は任意。

REVISE・REJECT にする理由は見つからなかった。

---

## 5. この審査でやっていないこと

- コードは直していない。リポジトリの試験（pytest・vitest）は流していない。§2-3 は関数の写しを動かした確かめで、実装の試験ではない。
- 本番の Google の画面で 1 日ずれを見てはいない（未確認）。すでにずれた予定の件数も数えていない（design §7 の 7 のとおり本番反映のあと）。
- 便1・便3 は対象外のため見ていない。canvas の見本は見ていない（この環境から読めない）。
