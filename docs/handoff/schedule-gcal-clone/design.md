# design: 予定の画面を Google カレンダーと同じ使い心地にする（作り直し）（2026-11-06）

状態: 成功条件 G1〜G14 は **PO 承認済み**（2026-11-06、PO 原文「1.」＝「この14項目で決める」を選択）。設計審査 1 回目・2 回目は REVISE、3 回目は **APPROVE**（§9）。3 回目の推奨 2 件も直した。実装は未着手。
実装の承認: PO はこのセッションの冒頭で「PRマージ、デプロイまで完走させてくれ」、3 択で「3」（違いもまとめて設計し直してから全部いっしょに作る）と指示した。設計審査の APPROVE と便ごとのカードが揃った便から作る。
追加（2026-11-07）: 見た目 5 か所の成功条件 G15〜G19 は **PO 承認済み**（PO 原文「１，」＝「この決め方で設計を進める」を選択）。作り方は §3.8・便6。設計審査は §9 の 4 回目（REVISE）・5 回目（**APPROVE**）。
根拠: `docs/handoff/schedule-gcal-clone/recon.md`（以下 recon）。前の設計 `docs/handoff/schedule-gcal-alignment/design.md`（K1〜K14）を引き継ぎ、便2（K8〜K11）はこの設計に入れ直す。

## 1. 目的

- PO の言葉: 「Googleカレンダーのクローンとは決して呼べない」を直す。
- 奥の目的: 社員が Google カレンダーと同じ手の動きで、迷わず予定を入れ・動かし・探せる。
- 利用者に見える変化: 押した時刻で作れる／箱に時刻が見える／引っぱって作る・動かす／祝日が見える／検索できる。

## 2. 成功条件（PO が画面で ○× を付ける）

比べ方はすべて「同じ Chrome の窓で、同じ週を、Sales Anchor と Google カレンダーで並べる」。

| # | 基準 | 検証方法 | recon |
|---|---|---|---|
| G1 | 週の表示で 10 時の枠を押すと、作る小窓が「午前10時〜午前11時」になる。4 時・15 時でも押した時刻になる | 3 か所を押して小窓の時刻を読む | B1 |
| G2 | 枠を押すと、押した所に「（タイトルなし）」の仮の箱が出る。閉じると消える | 画面で見る | D5 |
| G3 | 作る小窓は、①一番上が題名の欄で、開いた瞬間に文字が打てる ②日時が 1 行の文 ③Meet・場所・説明は押すと開く 1 行 ④ボタンがすべて小窓の中に収まる | 窓の高さ 1448 と 768 の 2 通りで開いて見る | B2・D6 |
| G4 | 週・日の箱に題名と「午後12:30〜1:30」の形の時刻が出る。種類の札は箱に出さない | 30 分・1 時間・2 時間の予定を見る | B3・D1 |
| G5 | 左の目盛りが「午前9時」「午後1時」の形 | 画面で見る | D2 |
| G6 | 1 時間の高さが Google カレンダーと同じ（同じ窓の画面写しで差が 5% 以内） | 両方の画面写しで 9 時〜10 時の線の間を測る | D3 |
| G7 | 日本の祝日（例: 11/3 文化の日、11/23 勤労感謝の日）が終日の行に出る | 11 月の週と月で見る | D4 |
| G8 | 空いた枠を上から下へ引っぱると、その長さで小窓が開く。自分の予定はつかんで別の時刻・日へ動かせ、下の端を引いて長さを変えられる。動かした結果は再読み込みしても残る | 3 つの操作をして再読み込み | D7（旧 K8〜K10） |
| G9 | 動かせない予定（他人の予定・シフト・祝日・取り込んだ終日の予定）はつかめない | つかもうとして動かないことを見る | 旧 K10・§3.6 |
| G10 | 月の表示で升目が画面の下まで届く。複数日の予定は日をまたぐ 1 本の帯で出る | 窓の高さ 1448 で見る。3 日間の予定を見る | D9（旧 K11） |
| G11 | 表示の切替は 1 つのボタン（「週 ▾」）で、押すと日・週・月・一覧が選べる | 画面で見る | D8 |
| G12 | 虫めがねを押すと検索の欄が出て、題名の一部で予定が探せ、押すとその日へ飛ぶ | 「商談」で探す | B4 |
| G13 | 週・日を開くと、今の時刻の 1〜2 時間前あたりから見える | 昼に開いて見る | D11 |
| G14 | ToDo（Google のタスク）は**今回は出さない** | — | D10 |

G14 を外す理由: Google の ToDo を読むには、今の接続（予定の読み書きの許可だけ）に別の許可を足して、会社の Google 接続をつなぎ直す必要がある（`backend/app/services/google_calendar.py` の `_SCOPES`）。Google の審査準備も別の作業で進んでいる。入れるなら別の作業として PO に聞く。


### 2.1 見た目 5 か所（G15〜G19・2026-11-07 追加）

測る場所: 本番 /schedule の週の表示・Chrome 窓 1620×1448（Google の実測 recon §7.1 と同じ条件）。色は Google の値を写さず、今のトークンを使う（ADR-067・§6）。

| # | 基準 | 検証方法 | recon |
|---|---|---|---|
| G15 | 日付の帯: 曜日（11〜12px）と日付の数字（24〜28px）が 2 段。今日の数字は直径 44〜48px の丸の中に白字。帯の高さ 76〜92px。今日の列の地は他の列と同じ色 | `.fc-col-header-cell` と中の 2 つの文字の getBoundingClientRect・getComputedStyle。今日の列と別の日の列の地の色は、画面写しの同じ高さ（予定の無い所）の画素の色を比べて一致を見る（別の日の列は FullCalendar が地を塗らない透明なので getComputedStyle では比べられない・4 回目の審査①） | §7.1・§7.2 |
| G16 | 今の時刻の線: 今日の列にだけ出る・太さ 2px・列の左端に直径 10〜14px の丸。時刻の欄の三角は出ない | `.fc-timegrid-now-indicator-line` の数と幅・`border-top-width`・`::before` の大きさと左端・`.fc-timegrid-now-indicator-arrow` が見えない（幅 0 か `display: none`） | §7.1・§7.3 |
| G17 | 予定の箱: 枠が地と同じ色（見えない）・1 時間の予定の幅＝列の幅 −10〜16px・高さ 92〜95px・文字 12px・行高 14〜16px・左の余白 8px（見積もりの点線と重なりの赤枠は今のまま） | 1 時間の予定の `.fc-timegrid-event` の getBoundingClientRect と getComputedStyle | §7.1・§7.2 |
| G18 | 時刻の文字: 10〜12px。文字の上下の真ん中と 1 時間の線の差が ±3px 以内。午前 0 時の文字は出ない（全 24 時間で 23 個） | `.fc-timegrid-slot-label-cushion` の矩形と `.fc-timegrid-slot` の上端を比べる。文字のある数を数える | §7.1・§7.2 |
| G19 | 重なり: 30 分ずれて重なる 2 つの予定で、後の予定が先の予定の上に重なる（後の `z-index` が大きく、後の左端が先の左端と右端の間）。先の予定の幅は後の予定の幅より広い | 自分の試し用の予定 2 つを本番で作って測り、消す（PO に作る日時を伝えてから） | §7.1・§7.3 |

## 3. 作り方（How）

### 3.1 時間割を金型 1 か所にする（SSOT）

- 今は予定の画面だけが自前の時間割を持ち、金型 `CalendarView` はどの画面にも使われていない（recon §4）。ADR-1065 What 1「時間割と月の升目は金型で出す」と食い違う。
- 最上位原則（ADR と実装が食い違ったら ADR に寄せる）に従い、**予定の画面を金型 `CalendarView` に載せ替える**。自前の時間割（`frontend/src/pages/schedule/SchedulePageImpl.tsx` の週・日・月の描画と `schedule.css` の対応部分）は消す。
- 一覧（30 日）・作る小窓・詳しくの小窓・左の小さな月・他のカレンダーの切替は画面側に残す（時間割ではない）。

### 3.2 金型に足す口（ADR-1065 の改訂が要る）

| 足す口 | 中身 | 受ける成功条件 |
|---|---|---|
| `onSelectRange(start, end, allDay, anchor)` | `selectable` を口があるときだけ有効。押す・引っぱるで範囲を返す。刻みは 15 分（`snapDuration: "00:15"`。今の `slotDuration` 1 時間 `frontend/src/components/CalendarView.tsx:117` のままだと 1 時間刻みになる・timegrid internal.js:1017）。中身の決まりは下の「選んだ範囲の決まり」 | G1・G2・G8 |
| `onEventMove` / `onEventResize` | `editable` を口があるときだけ有効。予定ごとの `editable` で動かせない予定を止める（FullCalendar の予定ごとの上書き。recon §5） | G8・G9 |
| 予定ごとの色 `color` | 担当者の色（DB が正本・画面は受けた値を使うだけ）。無いときは今の `tone` | G4 |
| 目盛りの形 | 「午前9時」の形（言語は画面の言語に合わせる。日本語・英語の 2 つを `t()` 側で持つ） | G5 |
| 1 時間の高さ | 新しいトークンは作らない。金型は既に `--schedule-row-height` を使う（`frontend/src/components/CalendarView.css:48`）。この値を G6 の測定で決め直す（1 か所）。ADR-1065 What 5 が「48px」と値を書いているので、改訂で値を書かない形にする（下の改訂の範囲） | G6 |
| 押した場所の四角 | 今の `onEventClick(id)`・`onDayClick(date)` は場所を返さない（`frontend/src/components/CalendarView.tsx` の `eventClick`・`navLinkDayClick`）。今の詳しくの小窓と「他 N 件」の小窓は押した所の四角を基準に出る（`frontend/src/pages/schedule/SchedulePageImpl.tsx:803,905`）。`onEventClick(id, rect)` に変え、rect は FullCalendar の `EventClickArg.el.getBoundingClientRect()`（6.1.22 の型 `EventClickArg { el; event; jsEvent; view }`）。呼ぶ側の今の使い方（id だけ）は引数が増えるだけで壊れない | G8・C6 |
| 「他 N 件」を押したとき | 今の金型は表示を切り替えるだけ（`moreLinkClick` が `arg.view.type` を返す）。口 `onMoreClick(date, rect)` を足し、渡されたときは FullCalendar の小窓を出さず呼ぶ側に任せる（`MoreLinkHandler` は `void` を返してよい・6.1.22 の型）。rect は `MoreLinkArg.jsEvent.target` の要素の四角。口があるときも**戻り値は `arg.view.type`（今の表示）を返す**（`void` や `"popover"` を返すと FullCalendar が自分の小窓を開く・core internal-common.js:7462・審査 2 回目 Q1）。口が無いときは今のまま | C6 |
| 引っぱる部品 | `interactionPlugin`（`@fullcalendar/interaction` 6.1.22・`frontend/package.json:75` に既にある）を金型の `PLUGINS` に足す。選択・動かす・長さを変えるはこれが無いと動かない（recon §5） | G1・G2・G8 |
| 見える時間の幅 | 金型は予定から見える時間を絞る（`frontend/src/components/CalendarView.tsx:42-43,60` `startHour=8`・`endHour=20`・`computeHourRange`）。Google は 0 時〜24 時を出して今の時刻へ送る。口で「0〜24 時を出す」を選べるようにする | G13 |
| 開いたときの位置 `scrollTime` | 今の時刻の 1 時間前 | G13 |
| 箱の中身 | 題名＋時刻の 2 行。札は出さない | G4 |
| 月の高さ | 今の金型は `height="auto"`（中身の高さ）。口 `fillHeight`（真偽）を足し、真のときは FullCalendar の `height="100%"` にして、包む枠の高さ（呼ぶ側が画面の残りの高さを渡す）いっぱいに広げる。偽・無しは今のまま | G10 |
| 週の始まり `firstDay` | 今の画面は日曜始まり（`frontend/src/pages/schedule/schedule-utils.ts:130,136` `addDays(..., -getDay())`）。Google の観測も 11/1（日）〜7（土）。金型の固定値 1（月曜）を口で渡せるようにし、予定の画面は 0（日曜）を渡す | — |

選んだ範囲の決まり（`onSelectRange`・審査 2 回目 Q3）:
- 押しただけ（選んだ長さが 15 分以下）のときは、押した刻みの頭（15 分単位）から 1 時間に広げて返す。引っぱったときは選んだ範囲そのまま。Google と同じく 10:00 の枠の上の方を押すと 10:00〜11:00。
- `anchor`（小窓の基準の四角）: `DateSelectArg.jsEvent` があるときは押した位置の 1 点（`clientX`・`clientY`、幅と高さ 0）。`jsEvent` が null のとき（6.1.22 の型 `jsEvent: MouseEvent | null`）は `null` を返し、画面は今の `openCreate(date, null)` と同じく基準なしの置き場所で開く（近道 c `:1424` と同じ道）。
- 月の升目（`allDay` が真で返る）: 画面は今の月の升目の作り方（`onSelectDay` `frontend/src/pages/schedule/SchedulePageImpl.tsx:874`→ その日の 7 時から 1 時間・§6 ③）をそのまま使う。終日の行で選んだとき（週・日の表示）は終日の予定として小窓を開く。
- 月の升目や終日の行で複数の日を引っぱったときは、選んだ日の範囲の終日の予定として小窓を開く（Google と同じ。審査 3 回目 Q2）。1 日だけ押したときは上の「7 時から 1 時間」。

ADR-1065 の改訂（便1 の PR に入れる）。直すのは 3 か所:
1. What 5「1時間の高さは `--schedule-row-height`（48px）」→「1時間の高さはトークン `--schedule-row-height` の値で決める（値は tokens.css 1 か所）」。
2. What 6「ドラッグ・選択は使わない」→「選択・動かす・長さを変える・他 N 件の小窓は、呼ぶ側が口を渡したときだけ使う」。
3. ステータス欄の採用条件「agent-console の予定画面で使われたら」→「Sales Anchor の予定の画面か agent-console の予定画面のどちらかで使われ、K1〜K9 が ○ になったら」。

### 3.3 動かした結果を保存する道

前の便2 カード（`origin/release/schedule-gcal-bin2-design` 9545d849d の `docs/handoff/schedule-gcal-alignment/design.md` §5-6・§11-2。審査 APPROVE）から、次の 5 つをそのまま引き継ぐ（1 回目の審査 Q1 で、前の版の書き方が間違っていた）:

1. 送る道と中身（旧 K9・N-12）: 離したら `PATCH /calendar/events/{id}` に、今の保存（`frontend/src/pages/schedule/SchedulePageImpl.tsx` の保存の処理）と同じ形で、題名・開始・終了・終日・説明・場所をまとめて送る。題名などは動かす予定の今の値。`category` と `calendar_type` は送らない（直す口の受け取り `UpdateEventBody` `backend/app/routers/calendar.py:118-126`（origin/main 9571ce84e） に `category` が無い）。開始と終了だけを送ると、裏側が Google へ送る中身を送られた欄だけで作り、Google 側の題名が空で上書きされる（旧カード §5-6）。
2. 失敗したとき: 元の位置に戻し、今の失敗の帯（`setError` の形）を出す。FullCalendar の `eventDrop`・`eventResize` の `revert()` を使う。
3. 終日を動かしたときの終わり（N-14）: 終わりは「新しい最後の日の 23:59（日本時間）」で作る（`combineDateTime(新しい最後の日, "23:59")`）。FullCalendar の終日の終わりは「次の日の 0:00」で返るので、1 日引いてから作る。次の日の 0:00 では送らない（Google で 1 日長くなる）。
4. 終日が Google で 1 日前にずれる不具合の直し（N-5・PO 2026-11-04「1」で便2 に入れると決めた件）: 裏側 `backend/app/services/calendar_service.py` の `_to_google_event_body` の終日の枝だけを、旧カード §5-6 の手順 1〜4 のとおりに変える（日付だけの値はそのまま／時刻つきは日本時間の日付にする／終わりは +1 日）。2026-11-06 の時点で main に入っていない（`backend/app/services/calendar_service.py:648-650` に `str(start_dt)[:10]` が残る・1 回目の審査 C5）。試験は旧カード §11-2 の 6・7（`TestToGoogleEventBody` に 6 件、`TestCreateEvent`・`TestUpdateEvent` に各 1 件）。
5. 端末は日本時間の前提（N-18）: 画面は端末の時刻で 00:00／23:59 を作る。日本以外の端末のずれは今からあり、便2 で増やさない。

- Google へ送るのは今の決まりのまま（ADR-1057: つないだ本人の予定だけ）。
- 動かせる予定の決まりは §3.6。

### 3.6 動かせる予定の決まり（G9・1 回目の審査 Q4）

予定の値だけで決める。画面に 1 つの関数 `canMoveItem(item)` を置き、金型には予定ごとの `editable` として渡す。

| 予定 | 見分け方（予定の値） | 動かせるか |
|---|---|---|
| 自分の予定・管理者が見る他人の予定 | `canEditItem(item)`（今の `canEditSelected` `frontend/src/pages/schedule/SchedulePageImpl.tsx:1385-1387` の中身＝持ち主が自分か、管理者か。中身は変えずに 1 件を受け取る関数へ切り出す・旧カード §11-2 の 2） | 下の 3 つに当たらなければ動かせる |
| シフト | `item.source === "shift"`（`frontend/src/pages/schedule/schedule-utils.ts:241`） | 動かせない |
| 取り込んだ終日の予定 | `item.source === "google" && item.allDay`（取り込みは `frontend/src/pages/schedule/schedule-utils.ts:218` で `source: "google"`） | 動かせない |
| 祝日 | 便4 で足す。予定の並びとは別の並びとして金型に渡し、`tone: "holiday"`（`frontend/src/components/calendarView.utils.ts:16` に既にある）・`editable: false` で出す | 動かせない（押しても何も開かない） |
| 他人の予定（管理者でない） | `canEditItem(item)` が偽 | 動かせない |

`canMoveItem(item) = canEditItem(item) && item.source !== "shift" && !(item.source === "google" && item.allDay)`。祝日は予定の並びに入らないので式に入らない。

### 3.7 「（タイトルなし）」の仮の箱（G2・1 回目の審査 Q6）

- 押す・引っぱるで範囲が選ばれたら、画面側が仮の予定 1 件（題名は `t("schedule.untitled")`・色は自分の担当者の色・`editable: false`）を金型へ渡す予定の並びの先頭に足す。作る小窓を閉じる・保存する・別の所を押すと消す。
- FullCalendar の選んだ範囲の色付け（`selectMirror`）は使わない。理由: 色付けには題名が出ないため。仮の予定は画面の状態だけにあり、DB にも Google にも送らない。
- 文言 `schedule.untitled` は便2 で ja/en に足す（今のキーに同じ意味のものがあればそれを使う。便2 のカードで実物を確かめる）。

### 3.8 見た目 5 か所（G15〜G19・便6）

方針: 金型 `CalendarView` に口を 1 つ足し（`appearance`）、予定の画面だけがそれを使う。既定は今の見た目のまま（見本帳・他の画面が増えても変わらない）。見た目はすべて `CalendarView.css` の `.comp-calendar--schedule.comp-calendar--days` の下にトークンだけで書く（月の表示の今日の升目・曜日の行に効かせないため。包みの class `comp-calendar--${mode}` は `frontend/src/components/CalendarView.tsx:156`）。下の表の選び方はすべてこの 2 つの class の下。画面側（`frontend/src/pages/schedule/SchedulePageImpl.tsx`・`schedule.css`）に見た目を書かない。

口: `appearance?: 'plain' | 'schedule'`（既定 `'plain'`）。`'schedule'` のとき包みの class に `comp-calendar--schedule` を足し、`mode === 'days'` のときだけ次の 3 つを FullCalendar に渡す。月の表示は変えない。

| 渡すもの | 中身 | 成功条件 |
|---|---|---|
| `slotEventOverlap: true` | 今の `false`（`frontend/src/components/CalendarView.tsx:171`）を `'schedule'` のときだけ true。重なりの形は recon §7.3 の `computeSegHStyle` | G19 |
| `dayHeaderContent` | 曜日と日付の数字の 2 つの `span`。曜日は新しい関数 `formatWeekdayShort(date, language)`（`calendarView.utils.ts` に足す・`Intl.DateTimeFormat(language, { weekday: 'short' })`）。数字は `date.getDate()`。今日（引数の `isToday`）は数字に `comp-calendar__daynum--today` | G15 |
| `slotLabelContent` | 今の時刻の文字の作り方（`timeStyle` が `'meridiem'` なら `formatMeridiem`・`:176`、`'h24'` なら今の 24 時間の形）を、時が 0 で分が 0 のときだけ空の文字にする関数で包む（新しい関数 `formatSlotLabel(date, text, t, timeStyle)`・`calendarView.utils.ts`。`h24` は FullCalendar の引数 `text` をそのまま返す・作り方は card-bin6.md §2-2） | G18 |

css（`CalendarView.css` の末尾に足す。値は var() と calc() と % だけ）:

| 何 | 書き方 | 成功条件 |
|---|---|---|
| 今日の列の地 | `.comp-calendar--schedule.comp-calendar--days { --fc-today-bg-color: transparent; }`（別の日の列は FullCalendar が地を塗らない透明。同じ透明にして一致させる・5 回目の審査 R4。`transparent` は色の直書きの見張り `check-css-hardcoded-colors.js:23,26` の対象外で、`Button.css` などに前例あり） | G15 |
| 日付の帯 | `.comp-calendar__day-head` を縦に並べ中央寄せ・上下の余白 `var(--space-2)`・間 `var(--space-1)`。`.fc-col-header-cell` の太字を `var(--font-weight-normal)` に | G15 |
| 曜日の文字 | `font-size: var(--font-2xs)`・`font-weight: var(--font-weight-medium)`・`color: var(--schedule-hour-label)`。今日は `color: var(--schedule-today)` | G15 |
| 日付の数字 | `font-size: var(--schedule-day-num-size)`・`width`/`height: var(--schedule-mini-size)`・`border-radius: var(--radius-full)`・中央寄せ。今日は `background: var(--schedule-today)`・`color: var(--on-solid)` | G15 |
| 今の線 | `.fc-timegrid-now-indicator-line { border-top-width: var(--schedule-now-line-w); }`。`::before` で丸（`width`/`height: var(--schedule-now-dot-size)`・`border-radius: var(--radius-full)`・`background: var(--schedule-now-line)`・左 0・上下の中心を線に合わせる calc）。`.fc-timegrid-now-indicator-arrow { display: none; }` | G16 |
| 予定の箱 | `.fc-timegrid-col-events { margin-right: var(--space-3); }`。`.comp-calendar__event:not(.comp-calendar__event--line-dashed) { --fc-event-border-color: var(--fc-event-bg-color); }`（見積もりの点線は除く。重なりの赤枠は `:165-168` が `border-color` を直接書くので残る）。`.fc-timegrid-event { font-size: var(--font-xs); line-height: var(--line-height-tight); }`・`.fc-timegrid-event .fc-event-main { padding: var(--space-1) var(--space-2) 0; }` | G17 |
| 時刻の文字 | `.fc-timegrid-slot-label { vertical-align: top; font-size: var(--font-2xs); line-height: var(--line-height-tight); }`・`.fc-timegrid-slot-label-cushion { font-weight: var(--font-weight-medium); transform: translateY(-50%); }`。文字の大きさと行高は外側の枠に付ける（中の文字だけに付けると外側の行高 13.6px×1.6 が残り、真ん中が線から下へずれる・4 回目の審査②） | G18 |

新しいトークン（`frontend/src/tokens.css` の `--schedule-*` の並び・`:422-424` の後）: `--schedule-now-line-w: 2px;`（今の時刻の線の太さ）・`--schedule-now-dot-size: 12px;`（今の時刻の丸）。色ではないので暗い表示の追加は要らない（`:640` 以降の暗い表示は色だけを持つ）。

予定の画面: `frontend/src/pages/schedule/SchedulePageImpl.tsx:1392` の `<CalendarView>` に `appearance="schedule"` を 1 行足すだけ。

組み合わせの決まり（5 回目の審査 R3）: G18 の「線の高さに合わせる」は `hourRange="full"`（予定の画面の今の値・`frontend/src/pages/schedule/SchedulePageImpl.tsx` の `<CalendarView>` の `hourRange="full"`）で守る。`hourRange="events"` と組むと一番上の時刻の文字が半分切れる。これは今使う画面が無いので直さず、見本帳の例は `hourRange="full"` で作る。`timeStyle` は `'meridiem'`・`'h24'` のどちらでも 0 時だけ空にする。

ADR-1065 の改訂（便6 の PR に入れる。ADR-1065 に口の一覧は無いので、What に 1 行足す・4 回目の審査③）:
- What 7 を足す:「見た目の型 `appearance` を口で選べる。`'plain'`（標準）は今の形。`'schedule'`（Sales Anchor の予定の画面）は時間割のときだけ、日付の帯を 2 段・今の線を丸つき・予定の枠を地と同じ色・時刻の文字を線の高さに合わせ、重なりは後の予定を先の予定の上に重ねて置く（PO 2026-11-07 G15〜G19 承認）」。
- Why に 1 行足す:「重なり横並びは `'plain'` の形として残す。予定の画面は PO が Google と同じ重ね方を選んだ（G19）」。Why の 2026-10-30 の比較（重なり横並びが要る形）と食い違わないようにする。
- 「設計・根拠」の欄に本 design §3.8 を足す。新しい依存・色の直書きは無い（What 2・4 の範囲内）。
- ADR を変えたら `node scripts/generate-adr-index.js` で `docs/adr/README.md` を作り直して同じ PR に入れる（CI「ADR index is up to date」）。

PR 本文: tokens.css にトークンを 2 つ足すので、`frontend/scripts/check-new-tokens.js` が求める「デザイントークン変更時」のチェック項目を PR 本文に入れる（4 回目の審査・観点 5）。

試験（`frontend/src/components/CalendarView.test.tsx`）:
- `:125` の `slotEventOverlap` を「既定は false・`appearance="schedule"` かつ days では true・month では渡さない」に分ける。
- `formatWeekdayShort`（ja で 2026-11-08 が「日」・en で「Sun」）と `formatSlotLabel`（0 時は空・9 時は「午前9時」）。
- `appearance="schedule"` で `dayHeaderContent` が今日だけ `--today` を付ける。
- `appearance="schedule"` で包みに `comp-calendar--schedule` が付き、既定では付かない（5 回目の審査 R1）。
- `appearance="schedule"` の金型に渡した `slotLabelContent` が 0 時で空・9 時で「午前9時」を返す（金型の props を通して見る・5 回目の審査 R2）。
- 試験の日付は `new Date(2026, 10, 8)` のように手元の時刻で作る（文字の日付から作ると地名の時差でずれる・5 回目の審査 R5）。
- T4（`--fc-*` を全部置き換える）は変えない。
- 見本帳（`frontend/src/components/CalendarView.stories.tsx`）に `appearance="schedule"` の週の例を 1 つ足す（重なる 2 つの予定を含む）。

### 3.9 便3: 作る小窓を Google の形に・表示切替を 1 つのボタンに（G3・G11・2026-11-07）

本番の今（2026-11-07 にアプリで測った・窓 900×1279）:
- 作る小窓は幅 320。高さは閉じた形で 496、「詳しく入れる」を押すと 544。
- 開いた瞬間の文字の行き先は BODY（題名の欄に入らない）→ G3 ① ×。
- 日時は日付と時刻の欄が 4 つ並ぶ → G3 ② ×。
- 場所・説明は「詳しく入れる」の奥。Meet は切り替えの 1 行 → G3 ③ は一部だけ。
- ボタンは小窓の中に収まっている → G3 ④ ○（recon B2 の 26px はみ出しは便2 で直った）。
- 表示の切替は 4 つのボタンが並ぶ（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1332-1345`）→ G11 ×。

作る小窓（`SchedulePopover`・`frontend/src/pages/schedule/SchedulePageImpl.tsx:213-515`）の変え方。変えるのは作るとき（mode が create）の見た目で、詳しく見る・直すときの中身は今と同じ項目を出す:
1. 上の帯: 作るときは「予定を追加」の札と種類の札を出さない（閉じる × は残す）。直す・詳しく見るときは今のまま。
2. 題名: 一番上に置く。作るときは見出しの文字を出さず、読み上げ用に `aria-label`（「タイトル」）を付ける。作るときは開いた瞬間に欄へ文字が入る → G3 ①。小窓は最初の描画で隠して（`visibility: hidden`）測ってから見せるので、`autoFocus` は効かない（審査 1 回目 H1・Chromium で再現）。位置決めの関数が「見えた」を返し、見えた後に `ref` で focus する。
3. 日時の 1 行: 時計の絵＋「11月10日(火) 午前10時～午前11時」の 1 行のボタン。押すと今の「終日」の切り替えと日付・時刻の欄 4 つが出る → G3 ②。作るとき以外は最初から開いた形（今と同じ欄）。
   - 文は新しい関数 `formatDraftDateLine`（`frontend/src/pages/schedule/schedule-utils.ts`）で作る。曜日つきの日付は `Intl.DateTimeFormat(language, { month: "long", day: "numeric", weekday: "short" })`（ja で「11月10日(火)」・Mac の node で確認）。時刻は金型の `formatTimeRange`（`frontend/src/components/calendarView.utils.ts:224`）を午前・午後を省かない形で使う。「～」は既存の `calendarView.timeRange`。
   - 新しい文言キーは `schedule.dateTimeLine`「{{date}} {{time}}」の 1 つだけ。
   - 終日 1 日は「11月10日(火) 終日」、終日で複数日は「11月10日(火)～11月12日(木)」、日をまたぐ時刻つきは「11月10日(火) 午後11時～11月11日(水) 午前1時」。日付が読めないときは空、終わりだけ読めないときは始まりだけ。
4. 種類・Meet・共有: 今の欄・切り替えのまま、日時の下に置く。Meet は「Google Meet を付ける」の 1 行の切り替えで、押すと付く（Google も 1 行のボタン）。G3 ③ の「押すと開く 1 行」に当たる（中身の入力が無いので開く物が無い）。
5. 場所・説明: 作るときは地図の絵＋「場所を追加」、線の絵＋「説明を追加」の 1 行のボタン。押すとその欄が出て、文字がそこに入る → G3 ③。値があるときと、作るとき以外は最初から欄を出す。欄に文字が入るのは 1 行を押して開いたときだけ（最初から開いている欄は題名から focus を奪わない）。
6. 「詳しく入れる」のボタン・状態 `expanded`・文言キー `schedule.moreOptions`（ja・en）・css `.schedule-popover__more` を消す。
7. 絵は金型の絵の表 `SCHEDULE_POPOVER_ICONS`（`frontend/src/constants/icons.tsx:360`）に heroicons の `ClockIcon`・`MapPinIcon`・`Bars3BottomLeftIcon`（outline・2.2.0 にあると確認済み）を足して使う。
8. 1 行のボタンは金型 `Button`（ghost・sm・fullWidth）。左寄せの `.schedule-popover .schedule-popover__line { justify-content: flex-start; }` と、文字の包み `.schedule-popover__line-text`（`min-width: 0; overflow: hidden; text-overflow: ellipsis;`）の 2 規則を足す（色・寸法の直書きなし）。金型 Button は折り返さない（`white-space: nowrap`）ので、長い文は末尾が「…」になる。

高さ: 閉じた形は題名・日時 1 行・種類・切り替え 0〜2 行・場所 1 行・説明 1 行で、今の 496 より低くなる。全部開いた形の高さは今の 544 に近い。小窓の高さの上限（`frontend/src/pages/schedule.css:372-387` の `max-height: min(var(--schedule-popover-max-h), calc(100vh - var(--space-6)))`）と中身だけを巻く形（`:417-429`）は変えないので、高さ 768 でもボタンは中に収まる → G3 ④。本番で 1448 と 768 の 2 通りで測る（高さを変えられないときは、上限の計算の値を書き、768 では測れなかったと報告する）。

表示の切替（G11）:
- 4 つのボタン（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1332-1345`）を、今の表示の名前（「週」）＋下向きの絵（`NAV_ICONS.chevronDown`）の金型 `Button` 1 つにする。`aria-haspopup="menu"`・`aria-expanded` を付ける。
- 押すと金型 `ContextMenu`（`frontend/src/components/ContextMenu.tsx`・受信箱で使っている）を、ボタンの左下を基準に開く。中身は日・週・月・一覧の 4 つ。選ぶと切り替わって閉じる。Esc・外を押すと閉じる（金型の動き）。
- 開いている間は文字の近道（d・w・m など）を効かせない（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1236` の「小窓が開いている」に足す）。
- 表示切替には新しい css の class を作らない。古い `.schedule-view-switch*`（`frontend/src/pages/schedule.css:57-90`）は消す。
- 金型 ContextMenu は document の mousedown で「外を押した」と見て閉じる（`frontend/src/components/ContextMenu.tsx:141`）。開いているときに切替ボタンを押すと閉じてすぐ開き直す（審査 1 回目 M1）。開いているときだけボタンの mousedown を止め、閉じるのはボタンの click が行う（金型は変えない）。

選ばなかった案:
- 「詳しく入れる」を残して中を並べ替えるだけ → G3 ③（場所・説明が 1 行ずつ開く）を満たさない。
- 表示切替に金型 `NavDropdown` → 行き先が画面の住所（route）に結び付いた部品で、表示の切り替えには使えない。
- 日時の 1 行を自前の文字の組み立てで作る → 金型の時刻の書き方（便2・便6 と同じ「午前10時」）と分かれる。金型の関数を使う。

試験（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx`・`frontend/src/pages/schedule/schedule-utils.test.ts`）:
- 近道の試験の `pressed`（`:246-247`）は「表示切替のボタンの名前がその表示か」に変える。
- T1・T3・T4（`:539-585`）は先に日時の 1 行を押してから欄を読む。T1 は 1 行に「午前10時～午前11時」「午前4時～午前5時」「午後3時～午後4時」が出ることも見る。
- 足す（C1〜C4・既存の T1〜T9 と名前を分ける）: 作る小窓で題名の欄に文字が入っている（`document.activeElement`）、場所・説明は 1 行だけで欄が無い／押すと欄が出る、表示切替のボタンを押すと 4 つが出て「月」を選ぶと月になる、切替を開いている間は「d」が効かず、閉じた後は効く。
- 近道の「効かない」試験は、表示切替のボタンが無いときに落ちる形にし、週のままであることも見る。
- 試験の環境（jsdom）は `visibility: hidden` を見ないので、H1 は試験では見つけられない。本番の Chrome で G3 ① として確かめる。
- 試験の 2 ファイルは答えの日本語を直接書くので、1 行目で `local/no-japanese-literal` を外す（先例 `frontend/src/components/CalendarView.test.tsx:1`・審査 1 回目 M2）。
- `formatDraftDateLine` の 7 通り（カード §8）。

台帳・ADR: ADR の改訂は無い（金型 Button・ContextMenu・TextFieldControl を今の口のまま使う。金型に口を足さない）。文言は ADR-027 に従い t() だけ。

### 3.10 便4: 日本の祝日を終日の行に出す（G7・G9・2026-11-07）

出どころは §3.4 の案 C（部品 `holidays==0.108` を裏側に 1 つ足す）。カードは `docs/handoff/schedule-gcal-clone/card-bin4.md`。

本番の今: 祝日は出ない（11 月の週・月に 11/3・11/23 の箱が無い）→ G7 ×。

確かめた事実（2026-11-07・origin/main 18565cd1b）:
- 裏側の予定の道は `backend/app/routers/calendar.py:138-157`（`GET /calendar/events`・`get_current_tenant`）。祝日の道は無い。
- 依存は `backend/requirements.txt` で、本番の箱は `backend/Dockerfile:18-21` で `pip install -r requirements.txt` する（版上げは配備で入る）。
- 画面の予定は `frontend/src/pages/schedule/SchedulePageImpl.tsx:903-910`（`useApiQuery` 3 本）で読み、`:1176-1198` の `calendarEvents` で金型に渡す。押したときは `:1405-1408` が `itemById` で探し、無ければ何もしない。動かすときは `patchMoved`（`:1202-`）が `itemById` 無しで元に戻す。
- 金型は `tone: "holiday"`（`frontend/src/components/calendarView.utils.ts:16`）と色（`frontend/src/components/CalendarView.css:139-142`）を既に持ち、`editable: false` で予定ごとにつかめなくできる（`calendarView.utils.ts:44-45`）。
- 期間は `toRangeStart`・`toRangeEnd`（`frontend/src/pages/schedule/schedule-utils.ts:145-157`）。終わりは含まない日（週は翌週の頭・月は翌月 1 日）。
- 部品の言語: Japan は en_US・ja・th を持ち、既定は ja（holidays の公式説明 https://holidays.readthedocs.io/en/latest/ を 2026-11-07 に直接読んだ。Context7 は月の上限で使えなかった）。
- 内閣府の表の 2026・2027 年は 35 件（Mac で取得した syukujitsu.csv を Shift_JIS から読み直して数えた）。

作り方:
1. 裏側に `backend/app/services/holiday_service.py` の `list_japan_holidays(start, end, lang)` を作る（正本はこの関数 1 か所。DB に持たない）。
2. `GET /calendar/holidays?start=YYYY-MM-DD&end=YYYY-MM-DD&lang=ja|en` を `calendar.py` に足す。返すのは `{"holidays":[{"date","name"}]}`。ログインは要る（`get_current_tenant`）が、会社によらず同じ答え。`end <= start` と 400 日を超える期間は 422。
3. openapi.json を生成し直す（CI「API contract is up to date」）。
4. 画面は 4 本目の `useApiQuery` で読み、`toHolidayEvents` で `allDay: true`・`tone: "holiday"`・`editable: false` の箱にして `calendarEvents` の最後に足す。名前は画面の言語（`i18n.language` が en で始まれば en、それ以外は ja）で裏側が返すので、文言キーは足さない。
5. 祝日の読み込みは、読み込み中の印・取れなかった文に入れない（祝日が取れなくても予定は見える）。
6. 押しても何も開かない・つかめない（G9）は、今の `itemById` の形と `editable: false` で満たす（画面の分岐を足さない）。

選ばなかった案:
- 祝日を `/calendar/events` の答えに混ぜる → 予定（会社の DB）と祝日（部品）の正本が 1 本の答えに混ざり、予定の直し・消しの道が祝日を予定と取り違える恐れがある。道を分ける。
- 画面に祝日の表を持つ（npm の部品や手書きの表）→ 裏側と画面で 2 か所になる（SSOT 違反）。裏側の 1 か所にする。

範囲の外（記録だけ）: 月の升目の前後の月の日（例: 11 月の表示の 10/26〜10/31）には祝日も予定も出ない（今の期間の作りのまま）。一覧の表示は金型を使わないので祝日は出ない（G7 は週と月）。月の升目の「他 N 件」を押して出る一覧の小窓は予定だけから作る（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1276-1277` の visibleEvents）ので、祝日は件数に数えられても小窓の一覧には出ない。直すなら別の便にする（8 回目の審査の推奨）。

試験と確かめ: カード §6・§7。本番では 11 月の週（11/2〜11/8）と月で「文化の日」「勤労感謝の日」が終日の行に出ること（G7）、押して何も開かず、引っぱっても動かないこと（G9）を Chrome で見る。

### 3.4 祝日の出どころ（2026-11-06 に確かめて決めた）

確かめた事実:
- 裏側の依存に祝日の部品は無い（クラウド調べ: `backend/requirements.txt`・`requirements-dev.txt`・`pyproject.toml` を grep、該当なし）。
- `backend/app/services/google_calendar.py` は会社の 1 つのカレンダーだけを読む（`get_calendar_id` :334-345 → `get_events` :348,356,362）。祝日カレンダーを読む関数は無い。
- 内閣府の祝日の表 https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv（Shift_JIS・列は「国民の祝日・休日月日,国民の祝日・休日名称」・1955〜2027 年）。2028 年分は 2027 年 2 月に載る（https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html）。2027 年は 17 件。2026-11-06 に Mac で取得。
- PyPI `holidays` 0.108（2026-11-02 公開・MIT・Python 3.11 以上）は 2027 年の日本の祝日を 17 件返す（クラウドで Python 3.12 に入れて実行）。振替の名前は「振替休日」。

| 案 | 中身 | 判定 |
|---|---|---|
| A | 会社の Google 接続で「日本の祝日」カレンダーを読む | 採らない。読む関数が無く、接続していない会社では出ない |
| B | 内閣府の表を DB の表に入れ、年 1 回入れ直す | 採らない。表の追加（移行）と年 1 回の手作業が増える |
| **C** | 裏側に `holidays==0.108` を足し、「期間の祝日を返す道」を 1 本作る。画面は終日の行に出す（動かせない・G9） | **採る**。DB も手作業も増えない。正本は部品 1 か所 |

- 正しさの確かめ: 便4 の試験に、内閣府の表の 2026・2027 年の 35 件（2026 年 18 件＋2027 年 17 件）の日付を正解として書き、部品の答えの日付と全件一致を見る（名前は比べない）。
- 更新: 部品の版上げで翌年分が入る。2027 年 2 月の内閣府の掲載後に版を上げ、同じ試験に 2028 年分を足す（便4 の PR に書き残す）。
- 内閣府の表は振替休日も国民の休日もまとめて「休日」と書く（2026/5/6・9/22）。画面には部品の名前をそのまま出す（3/22 は「振替休日」とクラウドで確認）。

### 3.5 検索

- 今ある予定の一覧の道で題名を探す（新しい道を作るかは、便5 の前に今の道に絞り込みがあるかを読んで決める）。

## 4. 便の分け方（作る順）

| 便 | 中身 | 成功条件 | 危険な道 |
|---|---|---|---|
| 便0 | 押した時刻が 7 時になる不具合だけを今の画面で直す（1 行） | G1 | なし |
| 便1 | 金型に口を足す・ADR-1065 改訂・見本帳（Storybook）に例 | （画面は変わらない） | なし |
| 便2 | 予定の画面を金型に載せ替え・目盛り・高さ・箱・今の時刻へ・月の高さと帯・引っぱる／動かす・終日のずれの直し（§3.3 の 4） | G2・G4〜G6・G8〜G10・G13 | なし（保存の道は既存。裏側は `backend/app/services/calendar_service.py` の `_to_google_event_body` の終日の枝と `backend/tests/test_calendar_service.py` だけ。移行・deploy・scripts は無い） |
| 便3 | Google 型の作る小窓・表示切替を 1 つに | G3・G11 | なし |
| 便4 | 祝日（案 C） | G7 | なし（移行なし。依存の追加 1 つ） |
| 便5 | 検索 | G12 | 未定（便5 の前に確認） |
| 便6 | 見た目 5 か所（§3.8）。金型に口 1 つ・css・トークン 2 つ・予定の画面に 1 行 | G15〜G19 | なし（frontend だけ。移行・deploy・scripts・DB は無い） |

便0 を先に出す理由: 今の本番で毎回起きる間違いで、1 行で直り、載せ替えを待つ理由がない。

## 5. 選ばなかった案

- 自前の時間割を直し続ける: 時間割が 2 か所のまま（ADR-1065 違反）。引っぱる・動かすを一から作ることになり、前の便2 カードも自前で 200 行を超えていた。
- 別の部品（FullCalendar 以外）: ADR-1065 で 6.1.22 に固定済み。

前に FullCalendar を外した件（1 回目の審査 Q7）:
- 2026-05-25 に予定の画面を FullCalendar で作った（9aed7103c）。2026-06-21 に自前の時間割へ置き換えた（1e4c4e7fb「fix schedule parity」。画面の先頭の説明 `frontend/src/pages/schedule/SchedulePageImpl.tsx:4` は「design_handoff_schedule_gcal を元に、FullCalendar 依存を外した内製グリッドへ置換」）。外した理由は、commit 文にも説明にも書かれていない（2026-11-06 に `git log -S` で確かめた）。
- その後 2026-11-06 に PO が ADR-1065 で「時間割は FullCalendar 6.1.22 を包んだ金型で出す」と決めた（ADR-1065 備考 PO「1」）。Why に 2026-10-30 の実物比較（要る形が全部そろったのは FullCalendar）がある。新しい決定が古い置き換えより後なので、金型へ戻す。
- 外した理由が見た目の差だった場合に備え、見た目は金型の css でトークンに置き換える（ADR-1065 What 4・§6）。

## 6. 心配と対処

| 心配 | 対処 |
|---|---|
| 載せ替えで今動いているものが壊れる | 次の 9 つを便2 の受入れに全部入れ、本番で 1 つずつ確かめる: ①予定を押すと詳しくの小窓（押した箱の横に出る） ②「他 N 件」を押すとその日の一覧の小窓（`frontend/src/pages/schedule/SchedulePageImpl.tsx:905,921`） ③月の升目を押して作る（`:874`） ④近道 12 個（`?` の一覧・`c` で今日の 9 時の小窓 `:1424` を含む） ⑤一覧（30 日） ⑥他のカレンダーの切替 ⑦左の小さな月 ⑧前へ・次へ・今日 ⑨シフトの予定の見た目（`schedule-event--shift` `:793`） |
| FullCalendar の見た目がトークン外の色を持つ | 金型の css だけでトークンに置き換える（ADR-067）。画面側に色を書かない |
| Google の見た目をまねすぎる | 仕組みと手の動きだけ合わせる。Google の絵・ロゴ・名前は使わない |
| 狭い窓で小窓がはみ出る | G3 を高さ 768 でも測る |
| 便6 の重なりで、先の予定は後の予定に隠れた所が押せない | 先の予定は列の幅のまま、右半分を後の予定が覆う。見えて押せるのは先の予定の左半分（recon §7.3・右 20px は空かない）。Google も先の予定の左側だけが見える形（Google 実測: 後の予定は列の左から 79px の所から）。G19 の測定で、先の予定の見えている所を押して詳しくの小窓が開くことも確かめる |
| 便6 の枠を消すと見積もりの点線が見えなくなる | 点線の予定は `:not(.comp-calendar__event--line-dashed)` で外す。受入れで点線の予定を目で見る |
| 便6 の時刻の文字を上へ半分ずらすと、一番上の文字が切れる | 一番上（0 時）は文字を出さない（G18）。`hourRange='events'` で 8 時から始まる使い方は `appearance='plain'` のままなので影響しない |
| 便6 で月の表示が変わる | 3 つの設定は `mode === 'days'` のときだけ渡す。css はすべて `.comp-calendar--days` の下に書く。受入れで月の表示の見た目が変わらないことを画面写しで比べる |

## 7. 外部・過去事例の参照と我々への応用

- 使う事例: Google カレンダー本体（2026-11-06 に同じ窓で並べて観測・recon §3）。比べたのは画面の形と手の動きだけで、速さや使われ方の数字は持っていない。
- 他社の導入事例の数字は使わない。理由: 今回の成功条件はすべて「Google と同じ画面・同じ操作になったか」で、本物を横に置いて直接比べられるため。

## 8. 維持の仕組み

- 時間割は金型 1 か所。新しい画面が時間割を自前で書いたら、UI の見張り（ADR-144）で止める対象に加えるかを便2 で決める。
- 金型の口ごとに見本帳の例と単体の試験を置く。
- 便6 の見た目は `CalendarView.css` の `.comp-calendar--schedule.comp-calendar--days` の 1 か所だけ。数値の見張り（`frontend/scripts/check-css-hardcoded-values.js`）と色の見張り（`frontend/scripts/check-css-hardcoded-colors.js`）が CI で直書きを止める。
- 守り手: frontend/src/pages/schedule/SchedulePageImpl.test.tsx（押した時刻で小窓が開くことを CI の試験で毎回確かめる。金型に載せ替えた後は frontend/src/components/CalendarView.test.tsx が加わる）

## 9. 審査

### 1 回目（2026-11-06 14:23 UTC・クラウド Opus・対象 79a23bd6b）: REVISE

- C1 ○（引用の行は origin/main 9571ce84e で合う）。C2〜C6 ×。
- 必須 Q1〜Q4・推奨 Q5〜Q7。直した場所:
  - Q1 旧便2 の N-5・N-14・K9 の書き方の間違い → §3.3 を書き直し、便2 の触るファイルに裏側を足した（§4）。
  - Q2 金型の口の不足（押した場所の四角・interaction・月の高さ・他 N 件）→ §3.2 に 4 行。
  - Q3 ADR-1065 の改訂の範囲 → §3.2 の末尾に 3 か所。
  - Q4 動かせない予定の見分け方 → §3.6。
  - Q5 守る機能 → §6 に 9 つ。Q6 仮の箱 → §3.7。Q7 前に外した理由 → §5。
- 1 回目は祝日の節（§3.4）と便0 のカードを見ていない（後から足したため）。2 回目で見てもらう。
- 未確認のまま残るもの: G6 の Google 側の 1 時間の css の実寸（便2 で同じ窓の画面写しで測る＝G6 の検証方法そのもの）。祝日の案 A は採らないので確かめない。
- Context7 は月の上限で使えなかった。FullCalendar の仕様は公式資料を直接読んだ（recon §5）。

### 2 回目（2026-11-06 14:38 UTC・クラウド Opus・対象 0b49f99ea）: REVISE・便0不可

- R1 ○（Q1〜Q7 は直っている）。R2 ×・R3 ○・R4 ×・R5 ×。
- R2 で FullCalendar 6.1.22 の型（`EventClickArg.el`・`MoreLinkHandler`・`height`・`firstDay`・`scrollTime`・予定ごとの `editable`/`color`・`revert`）は成り立つと npm pack の中身で確かめた。
- R3 `holidays==0.108` を Python 3.12 で数えて 2026 年 18 件・2027 年 17 件（合計 35 件）。内閣府の表はクラウドから接続を断られた（403）ので、内閣府との日付の突き合わせは便4 の試験で行う（§3.4 のとおり）。
- 直した場所:
  - Q1（必須）「他 N 件」で void を返すと FullCalendar の小窓が開く → §3.2 の行を「戻り値は `arg.view.type`」に直した。
  - Q2（必須）便0 で見出し（:709）も 0 時になる → `docs/handoff/schedule-gcal-clone/card-bin0.md` を 3 か所の変更（口の型 :682 に `hour?`・枠 :783 で `hour` を渡す・呼び出し :1574）に直し、見出しが 7 時のままの試験を 1 件足した。
  - Q3（推奨）刻み・押しただけの長さ・anchor・月の升目 → §3.2 に「選んだ範囲の決まり」。
  - Q4（推奨）`UpdateEventBody` の行 → `backend/app/routers/calendar.py:118-126`。

### 3 回目（2026-11-06 14:44 UTC・クラウド Opus・対象 39966f85c）: APPROVE・便0可

- S1〜S5 すべて ○（引用の行は origin/main 5574bf327 で照合。`moreLinkClick` が文字列を返すと `zoomTo` に進み小窓は開かない＝internal-common.js:7462。便0 の変更前の 3 か所は一字一句一致）。必須の指摘なし。
- 推奨 2 件を直した: Q1 便0 の試験で枠を列の中から取る（`docs/handoff/schedule-gcal-clone/card-bin0.md`）。Q2 月の升目・終日の行で複数日を引っぱったら複数日の終日の予定（§3.2）。

### 4 回目（便6・G15〜G19）: REVISE（2026-11-07・クラウドの Opus・origin/release/schedule-gcal-look-v2 aef7c764f）

- 観点: (1) 行番号 ○ (2) FullCalendar の主張 ×（右 20px は付かない） (3) 数値 ×（G15 の測り方・G18 の文字の行高） (4) 月・点線・赤枠・担当者の色 ○ (5) 見張り ○（check-new-tokens の PR 本文だけ要る） (6) i18n・UI ×（ADR-1065 に口の一覧が無い） (7) 試験の直し方。
- 直したこと: recon §7.3 の重なりの形を実物に直した（Opus も 6.1.22 の写し `:616-632`・`:826` で確認）。§2.1 G15 の測り方を画素の色の比較に。§3.8 の時刻の文字の大きさを外側の枠へ。§3.8 に ADR-1065 の改訂（What 7・Why 1 行）と PR 本文の項目を足した。§6 の重なりの行を直した。
- 審査の返事は記録の上で 1500 字の途中から切れて読めず、観点 (6) の後半と (7) の判定は Opus が読めていない（まだ確かめていません）。5 回目で (6)(7) も見直してもらう。

### 5 回目（便6・G15〜G19）: APPROVE（2026-11-07 07:36〜07:40 UTC・クラウドの Opus・origin/release/schedule-gcal-look-v2 6f56e9552・照合は origin/main 9cf750f29 と FullCalendar 6.1.22 の npm pack）

- 観点: (1) 4 回目の指摘 5 件の直し ○ (2) G18 の文字の真ん中 ○ (3) i18n・UI ○ (4) 試験の直し方 ○ (5) 新しい食い違い ○（必須なし）。
- (1) 右 20px は空かない（internal.js:622 で全部の予定が `stackForward ≥ 1`・`:826` の枝を通らない）。G15 は画素の色で比べる形、文字の大きさと行高は外側の枠、ADR-1065 は What 7、PR 本文に check-new-tokens の項目。
- (2) 行の高さ 11.2px × 1.25 = 14px。文字の箱の上端は線 + 0.5px（枠 1px の半分）。`translateY(-50%)` で 7px 上がり、箱の真ん中は線 + 0.5px。字の形のずれを入れても約 2.2px で ±3px 以内。
- (3) ADR-027 は日付の書き方も対象。言語で Intl を切り替える前例 `frontend/src/pages/schedule/schedule-utils.ts:103` があり、Intl を止める見張りは無い。
- (4) `:125` を分ける案で足りる。T4 は `.comp-calendar {` の塊を切り出すので変えずに通る。
- 推奨を直した: R1 包みの class の試験・R2 0 時の文字の試験・R3 `hourRange`/`timeStyle` との組み合わせ（§3.8）・R4 今日の列の地を `transparent`・R5 試験の日付の作り方。R6（日付の帯の class 名と行高）は便6 のカードで class 名を `comp-calendar__day-head`・`comp-calendar__dayname`・`comp-calendar__daynum` に固定する。R7（冒頭の「4 回目」の表記）は冒頭を直した。
- 審査の結果のファイルは、クラウドの見張り（作業場所の外での commit 禁止）に止められて push されなかった。中身は実行の記録（RemoteTrigger の run log・セッション cse_01HHUUpQXH3goWYWdFkgnNpJ）の最後の返事で全部読めた（切れていない）。審査役は指示どおり言い換えずに止まった。

### 6 回目（便3・G3・G11）: REVISE（2026-11-07 11:12〜11:20 UTC・クラウドの Opus・origin/release/schedule-gcal-create-bin3 50e56c0b4・照合は origin/main 37fa04f7b）

- 審査の結果のファイルは、5 回目と同じくクラウドの見張り（作業場所の外での commit 禁止）に止められて push されなかった。中身は実行の記録（セッション cse_01HHUUpTnMjo55nyv2JCfsv5）の最後の返事で読んだ。書いた結果のファイルの本文は記録の上で途中から切れていて、軽い指摘 L1〜L6 の一部は返事の要約だけで読んだ（まだ確かめていない部分がある）。
- ○: `formatDraftDateLine` の 7 通りの答えは node で全部一致（TZ=UTC でも同じ）。行番号はおおむね一致。ADR-144・ADR-067・ADR-027 の本文には触れない。
- H1（重い）: 小窓は最初の描画で `visibility: hidden`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:176-178`）なので、題名の `autoFocus` は本物の Chrome で効かない（React 18.3.1 と Chromium で再現。jsdom の試験は見逃す）→ 位置決めの関数が `placed` を返し、見えた後に `ref` で focus する形に直した（§3.9 の 2・カード §6-0・§6-2）。
- M1（中）: 金型 ContextMenu の mousedown で閉じるため、切替ボタンの再押しで開き直す（Chromium で再現）→ 開いているときだけボタンの mousedown を止める（§3.9 表示の切替・カード §7-3）。
- M2（中）: 試験の日本語が commit 前の検査で止まる → 両試験ファイルの 1 行目で規則を外す（カード §8）。
- L（軽い）: 金型 Button は折り返さない → 「…」にする規則を足した。新しい試験名 T6〜T9 が既存と重なる → C1〜C4。`check-page-header-actions.js` はどこからも回っていない → カードの想定分岐から消した。近道の「効かない」試験が弱い → ボタンが無いと落ちる形と、週のままの確認を足した。設計とカードの食い違い（設計の「値があるときは欄を出す」がカードに無い・試験の節番号）→ 揃えた。行番号の小さなずれ（keydown の取り付けは `:1272`）→ カードは `:1229-1275` の範囲指定のままで、該当の書き換えは文の照合で行う。
- 次の審査（7 回目）は、結果をファイルに commit させず、返事の本文に全部書かせる。


### 7 回目（便3・G3・G11）: APPROVE（2026-11-07・2 回目は 11:40〜11:42 UTC・クラウドの Opus 2 回・origin/release/schedule-gcal-create-bin3 b9cafcb1b・照合は origin/main 37fa04f7b）

- 結果はファイルに commit させず、返事の本文で読んだ。1 回目の返事は記録の上で途中から切れた（(4) 以降は読めていない）ため、(4)(5) だけを短い返事で 2 回目に回した（セッション cse_01HHUUpSviko7E4E978kBaVX・cse_01HHUUpSGw9UVCwgS7oK5r83）。
- (1) ○ H1: React 18.3.1 と Chromium で、直す前は開いた直後の文字の行き先が BODY、直した後は題名の欄（`frontend/src/components/TextField.tsx:43-55` は ref を渡す）。M1: 直す前は 2 回目の押しで一覧が開いたまま、直した後は閉じる（`frontend/src/components/ContextMenu.tsx:136-142`・`frontend/src/components/Button.tsx:41,68`）。M2: `frontend/eslint.config.js:31` は warn・前例 `frontend/src/components/CalendarView.test.tsx:1`。L ○。
- (2) ○ 「…」: 幅 320 で文字の実寸 471 に対し見える幅 275、はみ出さない。
- (3) ○ 場所・説明の欄: 下書きの値は文字列で既定は空（`frontend/src/pages/schedule/SchedulePageImpl.tsx:77-78`・`:984-985`・`:1155-1156`）。
- (4) ○ 試験の直しで既存の試験は落ちない（コードを読んで確かめた・vitest は回していない）。C4 の順: 金型の Esc は document で受けて伝わりを止め（`frontend/src/components/ContextMenu.tsx:122-131`）、近道は window で受ける（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1272-1276`）。開いている間の d は `:1236`・`:1246` で止まり、閉じた後は `:1258` で日に変わる。
- (5) ○ 新しい食い違いなし。推奨 1 件: カード §8 の想定分岐の範囲「:297-397」→ 実物の describe は `:244-399` → 直した。
- 試験を実際に回すのは実装の CI で確かめる。

### 8 回目（便4・G7・G9）: APPROVE（2026-11-07 12:40〜12:43 UTC・クラウドの Opus・origin/release/schedule-gcal-holiday-bin4 edb43370e・セッション cse_01HHUUpR2rYa2ud1RduecWHt）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ Python 3.12.3＋holidays 0.108 でカード §2 の関数を実行。2026-01-01〜2028-01-01 は 35 日で、カード §6 S1（内閣府の表）と順番まで全件一致。lang=en の 2026-11-03 は「Culture Day」。2027-03-22 は「振替休日」。
- (2) ○ HEAD の写しにカード §2・§3 を入れて確かめた。欄名 date と import の date はぶつからない。範囲が空・401 日は 422、400 日は通る。既存の test_calendar_owner_api と合わせて 25 passed・ruff 合格。openapi 生成の差は `/api/v1/calendar/holidays`・`HolidayItem`・`HolidayListResponse` の 3 つだけ。
- (3) ○ 型（`frontend/src/components/calendarView.utils.ts:33-45`）・押しても開かない（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1174`・`:1405-1407`）・動かせない（`:1202-1207` で revert）・読み込み中に入れない（`:917`・`:919`）・試験の作り物は決まりの無い道に `[]`（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx:62`）。
- (4) ○ 行番号は HEAD と一致。便3 は origin/main に入っている。推奨 1 件（月の「他 N 件」の一覧に祝日が出ない）→ §3.10 の範囲の外に記録した。
