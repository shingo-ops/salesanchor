# recon: 予定の画面を Google カレンダーと同じ使い心地にする（作り直し）（2026-11-06）

基準: `origin/main` feae3a87a（worktree `release/schedule-gcal-clone-design`）。行番号はこの時点。
本番の観測: 2026-11-06 21 時台、app.salesanchor.jp/schedule と calendar.google.com を同じ Chrome の窓（1621x1448）で同じ週（11/1〜7）に開いて並べた。

PO の依頼（原文）:
- 「見本と全然違うくてGoogleカレンダーのクローンとは決して呼べないUIナノは理解できる？」
- 「停止したということは意図していないので推測は禁止して事実事実確認を怠らずに確実性を重視して…不具合とエラー部分を省略せずに確認をして…安全に進めてくれ」
- 3 択に「3」＝違いもまとめて設計し直してから全部いっしょに作る。

## 0. ADR の検索結果

`git grep -n -i -E "calendar|schedule|予定" docs/adr/FEATURE-INDEX.md` と ADR 一覧から:

| ADR | 関係 |
|---|---|
| `docs/adr/ADR-1065-calendar-view-component-fullcalendar-v6.md` | **時間割と月の升目は金型 `CalendarView`（FullCalendar 6.1.22）で出す**（What 1）。ドラッグ・選択は使わない（What 6）。ステータス Proposed |
| `docs/adr/ADR-1057-google-calendar-owner-only-sync.md` | 接続は会社で 1 つ。Google へ送るのはつないだ本人の予定だけ |
| `docs/adr/ADR-1059-google-calendar-import-owner-private.md` | 持ち主の Google の予定を取り込む |
| `docs/adr/ADR-1060-calendar-google-meet.md` | Meet を付ける（便3・本番済） |
| `docs/adr/ADR-027-ui-internationalization.md`・`docs/adr/ADR-067-design-token-enforcement.md`・`docs/adr/ADR-144-ui-component-governance.md` | 文字は t()・色と大きさはトークン・部品は金型を先に使う |
| `docs/adr/ADR-135-release-stowaway-prevention.md`・`docs/adr/ADR-136-cc-bot-github-identity.md` | 危険な道を含む便は PO の「GO #番号」 |

前の設計: `docs/handoff/schedule-gcal-alignment/design.md`（K1〜K14。便1 #5124・便3 #5135 は本番済。便2 は設計の枝 `origin/release/schedule-gcal-bin2-design` で審査合格のまま main に入っていない）。

## 1. 止まった理由（記録の事実）

- 便2 のカードは 2026-11-04 23:48 にクラウドの再審査 3 回目で APPROVE（`origin/release/schedule-gcal-bin2-design` 9545d849d）。
- 便2 の着手条件は「便1 が本番に出て PO が K1〜K7 を見たあと」（`docs/handoff/schedule-gcal-alignment/design.md:50`）。
- PR #5124 のコメントに「K2 は本番反映後にブラウザで確かめる」とある。PO に K1〜K7 の確認を頼んだ記録・K2 をブラウザで確かめた記録は見つからない（`git grep "K1〜K7"`・`gh pr view 5124 --json comments`）。
- 台帳 release-schedule-gcal-bin2-design.md（枝 origin/release/schedule-gcal-bin2-design にだけある） は IN_PROGRESS のまま。
- 結論（事実の並び）: 着手条件の確認依頼を Opus が出さず、便2 は誰も動かさないまま止まった。

## 2. 本番の不具合（同じ操作で毎回起きる・原因はコードで確認）

| # | 観測 | 原因 |
|---|---|---|
| B1 | 週の 10:00 の枠を押すと小窓の時刻が 07:00〜08:00。4:00 の枠でも 07:00〜08:00（入力欄の値を読んで確認） | 枠は時刻入りの日付を渡す（`frontend/src/pages/schedule/SchedulePageImpl.tsx:781-783` `base.setHours(hour, 0, 0, 0)`）。受け手 `openCreate`（`:1237` `hour: number = WORKDAY_START`、`:1240` で日付と hour から作り直す）は呼び出し `:1574` が hour を渡さないので 7（`:106` `WORKDAY_START = 7`）になる。`git log -S` で 0b3a249a7（便1・2026-11-04）から |
| B2 | 作る小窓の「詳しく入れる」が小窓の左に 26px はみ出して切れる | 小窓 幅 320px（左端 590）、ボタン左端 564。下の帯 3 ボタンの幅 128+71+113px |
| B3 | 週・日の予定の箱に時刻が出ない | 箱 高さ 48px・`overflow: hidden`・縦並び。題名 4-19px／種類の札 21-45px／時刻 47-60px で箱の外（札 `:809`・時刻 `:815`） |
| B4 | 虫めがね（検索）を押しても何も起きない | `onClick` なし（前の recon §4。前の設計で対象外） |

読み込み: 通信 24 件すべて 200。画面のエラー 0 件（読み込み時・操作後）。

## 3. Google カレンダーとの違い（同じ窓・同じ週）

| # | Google カレンダー | Sales Anchor | 根拠 |
|---|---|---|---|
| D1 | 箱に題名と「午後12:30〜1:30」。札なし | 題名と「商談・打合せ」の札。時刻は隠れる | B3 |
| D2 | 目盛り「午後1時」 | 「13:00」 | `frontend/src/pages/schedule/SchedulePageImpl.tsx:757` |
| D3 | 1 時間の高さ 約 69px（画面写し上） | 約 34px（画面写し上。css は `--schedule-row-height: 48px` `frontend/src/tokens.css:403`） | 同じ縮尺の画面写しで比べた。css の実寸は Google 側未確認 |
| D4 | 終日の行に「文化の日」（「日本の祝日」カレンダー） | 祝日を出す仕組みが無い。種類の選択肢に「日本の祝日」はある | `git grep -i holiday` はシフトの休みだけ（`frontend/src/pages/schedule/schedule-utils.ts:235`） |
| D5 | 枠を押すと押した時刻。押した所に「（タイトルなし）」の仮の箱 | 07:00 固定（B1）。仮の箱なし | 本番で操作 |
| D6 | 小窓: 題名欄が先頭で入力状態。日時は 1 行の文（「11月 4日 (水曜日) 午後4:00 – 午後5:00」）。ゲスト・Meet・場所・説明は押すと開く 1 行。下に「その他のオプション」「保存」 | 種類の選択・終日・Meet・社員にも見せる・日付と時刻の入力欄 4 つ | 本番で操作（Google 側は保存せず閉じた） |
| D7 | 引っぱって作る・つかんで動かす・長さを変える | どれも無い（`onPointerDown`・`onMouseDown`・`draggable` 0 件） | 前の設計の便2（K8〜K11） |
| D8 | 表示の切替は 1 つのボタン「週 ▾」 | 日・週・月・一覧の 4 ボタン | 画面 |
| D9 | 月の升目が画面の下まで | 升目 763px／窓 1448px。下が空く | 本番で寸法を読んだ |
| D10 | ToDo の「4 件の保留中のタスク」が出る | 出ない | 画面 |
| D11 | 開くと今の時刻のあたり（午前11時〜）から見える | 0:00 から（行が 48px なので 1 日がほぼ入る） | 画面 |

動いたもの: 予定を押すと詳しく（Meet で参加を含む）、月の 1 行表示、一覧 30 日、近道の一覧（? で 12 個）、日・次へ・今日、他のカレンダーの切替、設定。

## 4. 金型と今の作り（SSOT）

- 金型 `frontend/src/components/CalendarView.tsx`（168 行）は FullCalendar を包む。`editable={false}`・`selectable={false}`（`:160-161`）、`firstDay={1}` 月曜始まり固定（`:150`）、目盛り `{hour:'2-digit',minute:'2-digit',hour12:false}`（`:35`）、色は種類 7 つの `tone`（`frontend/src/components/calendarView.utils.ts:9-16`）だけ。押す口は `onEventClick`・`onDayClick` だけ（`frontend/src/components/calendarView.utils.ts` の `CalendarViewProps`）。
- Sales Anchor の予定の画面は金型を使っていない。`frontend/src` の中で `CalendarView` を使う画面は 0 件（`grep -rln CalendarView frontend/src`）。自前の時間割が `frontend/src/pages/schedule/SchedulePageImpl.tsx`（1624 行）＋ `schedule.css`（1489 行）にある。
- → ADR-1065 What 1 と食い違う（時間割が 2 か所）。
- 予定の色は担当者の色（`frontend/src/pages/schedule/SchedulePageImpl.tsx:198-210` `getOwnerMeta`。色は裏側 `backend/app/routers/calendar.py:183` `COALESCE(cos.color, :default_color)` から＝DB が正本）。金型の `tone` は種類の色で、担当者の色を受ける口が無い。

## 5. 公式資料（Context7 は月の上限で使えなかった：`Monthly quota exceeded`。公式を直接読んだ）

- https://fullcalendar.io/docs/selectable : `selectable`（既定 false）は日・時間枠を押して引っぱり選べる。`interaction` プラグインが要る。選ばれたときは `select`。
- https://fullcalendar.io/docs/editable : `editable`（既定 false）は予定を動かす・長さを変える。予定ごとの `editable` で上書きできる。`interaction` プラグインが要る。
- `frontend/package.json:75` に `@fullcalendar/interaction` 6.1.22 は入っている。

## 6. 未確認

- 会社の Google 接続で「日本の祝日」カレンダー（`ja.japanese#holiday@group.v.calendar.google.com`）を読めるか。手元の Google カレンダー接続は期限切れで試せなかった（`session expired`）。
- Google の 1 時間の高さの css の実寸。
- 狭い窓（高さ 768px など）での小窓の収まり（前の便1 の K1 は自動試験だけ）。

## 7. 見た目 5 か所（G15〜G19）の現在地（2026-11-07・origin/main 9cf750f29）

### 7.1 Google カレンダーの実測（2026-11-07 14 時台 JST・Chrome 窓 1620×1448・getBoundingClientRect / getComputedStyle）

| 項目 | Google | Sales Anchor（本番 /schedule・同じ窓） |
|---|---|---|
| 日付の帯 | 高さ 84・2 段（曜日 11px 太さ 500／日付 26px 太さ 400）・今日は 46×46 の丸に白字・今日の列の地は白 | 高さ 27・1 行「11/1(日)」13.6px 太字・丸なし・今日の列に薄い色 |
| 今の時刻の線 | 今日の列だけ・2px・列の左端に 12×12 の丸 | 1px・時刻の欄に 6×10 の三角 |
| 予定の箱（1 時間） | 列 172 の右に 13 空け幅 159・高さ 94・枠なし・左 8 上 4 の余白・12px・行高 15 | 161×95・枠 1px・行高 19.2 |
| 時刻の文字 | 11px 太さ 500・線の高さに真ん中・午前 0 時の文字なし（23 個） | 13.6px 太さ 400・1 時間の枠の真ん中・0 時の文字あり（24 個） |
| 重なり（30 分ずれた 2 つ） | 先の予定 159→135 に縮む・後の予定は列の左から 79px・幅 80 で上に重なる（z 6 が 5 の上）・白い縁 | 横に半分ずつ並ぶ設定（`slotEventOverlap: false`） |

予定の名前・中身は記録しない。Google 側の試し用の予定 2 つは測った後に削除し、再読み込みで 0 件を確かめた（PO 承認「1」）。

### 7.2 コード（origin/main 9cf750f29）

- 金型を使う画面は予定の画面 1 か所だけ: `frontend/src/pages/schedule/SchedulePageImpl.tsx:1392-1421`（`timeStyle="meridiem"`・`eventLayout="stacked"`・`hourRange="full"`）。ほかは試験の差し替えだけ（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx:15`・`frontend/src/pages/schedule/SchedulePageCache.test.tsx:24`）。
- 重なり: `frontend/src/components/CalendarView.tsx:171` `slotEventOverlap: false`。試験 `frontend/src/components/CalendarView.test.tsx:125` が `false` を固定。
- 日付の帯: `dayHeaderContent` を渡していない（`frontend/src/components/CalendarView.tsx:204-245`）。日本語の既定の形「11/1(日)」が出る。
- 時刻の文字: `frontend/src/components/CalendarView.tsx:175-177` で `formatMeridiem`。午前 0 時も文字を出す。
- 見た目は `frontend/src/components/CalendarView.css` だけ（178 行・var() のみ）。今日の列 `:37` `--fc-today-bg-color: var(--schedule-slot-hover)`・今の線 `:38`・予定の枠 `:98-102`（`border-width: var(--schedule-gridline-w)`）・担当者の色 `:146-150`（地と枠が同じ色）・見積もり `:158-162`（地は面の色・点線）・重なりの赤枠 `:165-168`。
- 既にあるトークン（`frontend/src/tokens.css`）: `:398` `--schedule-day-num-size: 1.625rem`（26px・曜日の帯の日付）・`:396` `--schedule-mini-size: 46px`・`:399` `--schedule-today: var(--accent-bright)`・`:401` `--schedule-now-line`・`:417` `--schedule-hour-label`・`:13` `--font-2xs`（11.2px）・`:14` `--font-xs`（12px）・`:29-30` `--font-weight-normal`/`medium`・`:35` `--line-height-tight: 1.25`・`:75-76` `--space-2`/`--space-3`・`:102` `--radius-full`・`:544` `--on-solid`。今の線の太さと丸の大きさのトークンは無い。

### 7.3 FullCalendar 6.1.22 の中身（unpkg の @fullcalendar/timegrid@6.1.22/internal.js を取り寄せて読んだ。Context7 は `Monthly quota exceeded` で使えなかった）

- `computeSegHStyle`（internal.js:802-829）: `slotEventOverlap` が true のとき、予定の幅を 2 倍まで広げる（`farCoord = Math.min(1, nearCoord + (farCoord - nearCoord) * 2)`）。`zIndex = stackDepth + 1`。右に 20px 空ける枝（`:826` `!segHCoords.stackForward` のとき `marginRight = 10 * 2`）は通らない。`webToRects`（`:616-632`）が後ろに何も無い予定にも `rect.stackForward = processNodes(...) + 1`（`:622`）で 1 以上を入れるため（4 回目の審査で判明・Opus が scratchpad の 6.1.22 の写しで同じ行を確認）。→ 2 つが重なると、先の予定は列の幅のまま縮まず、後の予定が列の半分から右端までを上に重ねて覆う。
- `isInset = rect.stackForward > 0`（`:762`）は上の理由で全部の予定が真になり、全部に `fc-timegrid-event-harness-inset` が付く。標準の css が `box-shadow: 0 0 0 1px var(--fc-page-bg-color)`（面の色の縁）を付ける。
- 標準の css（`:1149`）: `.fc-timegrid-col-events { margin: 0 2.5% 0 2px }`・`.fc-timegrid-event .fc-event-main { padding: 1px 1px 0 }`・`.fc-timegrid-now-indicator-line { border-width: 1px 0 0; left:0; right:0 }`・`.fc-timegrid-now-indicator-arrow`（時刻の欄の三角）・`.fc-timegrid-now-indicator-container { overflow: hidden }`・`.fc-timegrid-slot-label { vertical-align: middle }`・`.fc-timegrid-slot-label-cushion { padding: 0 4px }`。
- 公式資料 v6（legacy.fullcalendar.io/v6）: `slotEventOverlap` は既定 true・「At most half of each event will be obscured」。`dayHeaderContent` の引数に `date`・`text`・`isToday`。`nowIndicatorClassNames`・`nowIndicatorContent` の引数に `isAxis`・`date`。`slotLabelContent` の引数に `date`・`text`。

### 7.4 未確認

- Google の後の予定の白い縁を何で描いているか（読み取れず）。こちらは 7.3 の面の色の縁で出る。
- Google の 1 時間の高さが窓 900×1327 で 80 になる理由（幅か高さか）。今回の G15〜G19 は窓 1620×1448 だけで測る。

## 8. 便14: 予定の編集画面を Google の形に（G58〜G64・2026-11-11）

PO の言葉（2026-11-11）: 「予定の詳細画面だけどGoogleカレンダーをクローンしてほしくて左側に寄せたり入力欄の角の丸みも真似てほしい、今の金型だと実現できないから別途金型を作って」。範囲の問いへの答え: 「作るときと直すとき両方」。

### 8.1 Google の編集画面の実測（2026-11-11・PO の Google（HIGH LIFE JPN）・Chrome 窓 1279×1448・明るい表示・getBoundingClientRect / getComputedStyle・保存していない）

- 地: rgb(248,250,253)。× x32 y26 40×40 角 20。題名の欄 x80 y29 幅 594 高さ 30・24px・太さ 400・枠なしで下線 1px rgb(68,71,70)（押すと 3px rgb(11,87,208)）。保存 x706 y20 76×40 角 20（丸い）・地 rgb(11,87,208)・左右余白 24。
- 日時の 1 段目 y92 高さ 40: 始まりの日 x80 幅 137・始まりの時刻 x225 幅 89・「〜」・終わりの時刻・終わりの日・「タイムゾーン」の文字リンク x587。2 段目 y140: 終日のチェック欄 x72（40×40）＋文字・「繰り返さない」の選ぶ欄 x170 幅 148 高さ 40。
- 塗りの欄: 角 4px・地 rgb(233,238,246)・枠なし・左右余白 16・14px。
- 白い札: x16 y206 幅 636 高さ 634・角 28・上下余白 4。札の頭に「予定の詳細」「時間を探す」の 2 つのタブ（x72 y210・各 102×48）。
- 札の中: 絵の列の真ん中 x48・中身は x80〜636。行の間隔 48。上から Meet の行（文字のボタン x80 y272 高さ 40）・場所（塗りの欄 x80 y320 幅 556 高さ 40）・通知（y368）・カレンダーの選ぶ欄（y472 幅 169）と色・予定あり（y520）・説明（塗りの欄 x80 y576 幅 556 高さ 248・飾りの帯つき）。
- 右の列: ゲスト（x680〜1024）。
- 原本: scratchpad b15 `google-measure.txt`・`google-eventedit.jpg`（社外に出さない）。

### 8.2 アプリの今の全画面の編集（2026-11-11・本番 app.salesanchor.jp・PO のログイン・同じ窓 1279×1448・保存していない）

- 地は白（`--bg-surface`）。上の帯の高さ 56。中身は x200 幅 880 で真ん中寄せ（`frontend/src/components/FullScreenDialog.css:46-49` `width: min(var(--modal-wide-w), 100%); margin: 0 auto`）。
- × x16 y10 36×36 角 6。題名 x64 y8 幅 1116 高さ 40・22px。保存 x1192 71×36 角 6・地 rgb(30,58,138)。
- 日時の欄 高さ 28・角 9999（完全に丸い）・白地に 1px の枠 rgb(226,232,240)・13.6px・幅 414。上に「開始日時」「時刻」「終了日時」の文字。終日は切り替え（Toggle）。種類の選ぶ欄 高さ 30・丸い。Meet のボタン 幅 836 高さ 36。社員にも見せるは切り替え。場所 高さ 28・丸い。説明 高さ 80・角 12。
- 直す（既にある予定）は全画面にならない。詳しくの小窓の「直す」で小窓の中が入力欄に変わる（`frontend/src/pages/schedule/SchedulePageImpl.tsx:975-982` `openEdit`・小窓の中身 `:380-418`・下の段 `:432-440`）。

### 8.3 コード（origin/main a7fbffdfe）

- 全画面の入れ物は金型 「frontend/src/components/FullScreenDialog.tsx」（106 行）。使うのは `frontend/src/pages/schedule/ScheduleFullEditor.tsx:38` の 1 か所だけ（`git grep FullScreenDialog -- ':!docs'` で見本帳と試験のほかに無い）。上の帯の真ん中に title・右に actions、中身は真ん中寄せの 1 列で、左に寄せる・札で包む・絵の列を作る口が無い（`:93-102`）。
- 開く条件 `open={fullEditOpen && popover?.mode === "create"}`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1588`）。作る小窓でなくなると閉じる（`:1132-1134`）。保存は `saveEvent`（`:988-1031`）で、`popover.mode === "edit"` なら PATCH `/calendar/events/{id}`・そうでなければ POST。成功で `setFullEditOpen(false)`（`:1022`）。
- 項目の部品 `frontend/src/pages/schedule/ScheduleDraftFields.tsx`（272 行）: 日時（`:114-182`・終日は Toggle `:118`・文字つきの日付と時刻 `:131-173`）・種類（`:184-208`）・Meet（`:210-213`・`MeetRow` `:44-72`）・社員にも見せる（`:215-226`）・場所（`:228-247`）・説明（`:249-269`）。
- 入力欄の見た目は `frontend/src/components/FormField.css`（schedule `:382-390`・schedule-title `:393-409`・textarea schedule `:326-332`）。種類の一覧: TextFieldVariant 8 つ（`frontend/src/components/TextField.tsx:35`）・SelectVariant 6 つ（`frontend/src/components/Select.tsx:18`）・TextareaVariant 6 つ（`frontend/src/components/Textarea.tsx:32`）。
- 決まり: 1 行の入力欄・選ぶ欄は完全に丸い（`--comp-input-radius` = `--radius-full`・`docs/specs/design-system/design.md:811`・`frontend/src/tokens.css:543`）。ボタンの `shape="pill"` はログイン画面だけ（`docs/specs/design-system/design.md:260,276,537,1115`・守り手 `frontend/src/components/buttonShapeUsage.test.ts:13-19`）。部品 1 つに定義 1 つ・違いは variant/size の口で（`docs/specs/design-system/design.md:32`）。
- 使えるトークン: `--radius-sm` 4px・`--space-10` 40px・`--space-12` 48px・`--font-2xl` 24px（`--radius-sm` は `frontend/src/tokens.css:96`・`--font-2xl` は `:21`・余白は `:74-83`）・`--bg-primary`（明 #f5f7fa / 暗 `--palette-ink-deep`・`frontend/src/index.css:17,225`）・`--bg-surface`・`--link-active-bg`（明 #ebeff8 / 暗 #1e3a8a・`:37,242`）・`--bg-subtle`（明 #f7fafc / 暗 #243046・`:19,227`）。角 28px の汎用トークンは無い（`--schedule-create-popover-radius` は作る小窓専用）。
- 金型 Checkbox（`frontend/src/components/Checkbox.tsx`・label は呼ぶ側で t() 済みの文字）が在る。
- 本番の点検 S13（`tests/prod-check/prod-ui.spec.ts`）は、名前「予定の編集」の dialog・題名の引き継ぎ・m キー・Tab・Esc を見る（ADR-1051 2026-11-11 改訂）。

### 8.4 ADR

- ADR-144（金型。新しい金型は PO の許可・`docs/CC_UI_GOVERNANCE.md:14`）・ADR-067（色と寸法はトークン）・ADR-027（i18n）・ADR-073（見本帳）・ADR-1060（Meet は保存のときに作る）・ADR-1065（時間割の金型）・ADR-1051（本番の画面点検）。入力欄の角を丸から変える例外を決めた ADR は無い（`git grep -il "comp-input-radius\|角.*丸" docs/adr` で 0 件・2026-11-11）→ ADR-1074 を起こす。

### 8.6 Google の予定の画面の色（2026-11-11 追加測定・PO の Google（HIGH LIFE JPN）・Chrome 窓 1914×1448・明るい表示・getComputedStyle・保存していない）

PO の言葉（2026-11-11）: 「予定の色だけどGoogleと色を併せて、Googleのは移植は心理的な意識をした青を使った配色になっていたはず」。範囲の問いへの答え: 「予定の画面すべて」（編集画面・カレンダーの表・予定の箱・作る小窓・詳しくの小窓。ほかの画面は今のまま）。

- 青を選んだ理由（心理の狙い）: Google の公式の説明は見つからなかった（WebSearch 2026-11-11。出てきたのは一般の色彩心理の記事と、Material 3 Expressive の研究が「元気・親しみ」などの評価を測ったという記事だけ）。→ **未確認**。設計の根拠には使わず、「PO が Google と同じ色を求めた」を根拠にする。
- 週の表（/r/week）: ページの地 rgb(248,250,253)。表の白い札 rgb(255,255,255)・角 28。日の列の線 1px rgb(221,227,234)。今日の丸 rgb(11,87,208)・文字白。左の小さい暦の今日 rgb(11,87,208) 24×24。今の時刻の線と丸 rgb(219,55,45)（線 2px・丸 12px）。見出しの文字 rgb(31,31,31) 22px/400。曜日・時刻・絵 rgb(68,71,70)。外枠のある操作（「今日」等）の枠 1px rgb(116,119,117)。「作成」ボタン 白地・角 16・影 rgba(0,0,0,.3) 0 1px 2px, rgba(0,0,0,.15) 0 1px 3px 1px。選ばれた表示切替の地 rgb(194,231,255)。
- 予定の箱: 地はカレンダーの色（このカレンダーは rgb(3,155,229)）・角 6・枠なし・文字 rgb(255,255,255) 12px/400。
- 作る小窓: 地 rgb(240,244,249)・598×513・影 rgba(0,0,0,.14) 0 3px 4px, rgba(0,0,0,.12) 0 3px 3px -2px, rgba(0,0,0,.2) 0 1px 8px。選ばれた種類（「予定」）の地 rgb(194,231,255)・文字 rgb(0,74,119)・角 8。文字 rgb(31,31,31)・補足と絵 rgb(68,71,70)。保存 地 rgb(11,87,208)・文字白・76×40・角 20。
- 詳しくの小窓（既にある予定）: 地 rgb(240,244,249)・496 幅。題名 rgb(31,31,31) 22px。補足と絵 rgb(68,71,70)。「Google Meet に参加」地 rgb(11,87,208)・文字白・角 20。文字のリンク rgb(11,87,208)。
- 編集画面（/r/eventedit）: 地 rgb(248,250,253)・札 白・角 28。文字 rgb(31,31,31)・絵と補足 rgb(68,71,70)・欄の中の案内文 rgb(68,71,70)。塗りの欄 rgb(233,238,246)。題名の下線 1px rgb(68,71,70)・押すと 3px rgb(11,87,208)。選ばれたタブの文字と下の帯 rgb(11,87,208)・帯 3px。選ばれていないタブ rgb(68,71,70)。タブの下の線 1px rgb(196,199,197)。チェック欄（入）地と枠 rgb(11,87,208)・（切）枠 2px rgb(68,71,70)。保存 rgb(11,87,208)・文字 rgb(255,255,255)。
- アプリの今（コード・origin/main a7fbffdfe）: 予定の画面は全体のトークンを使う（`frontend/src/pages/schedule.css` で `--text-primary` 15 回・`--text-secondary` 14・`--text-muted` 13・`--border` 10・`--accent` 5 ほか）。`--text-primary` #1a202c・`--text-secondary` #4a5568・`--text-muted` #718096・`--border` #e2e8f0・`--accent` #1e3a8a（`frontend/src/index.css:24-34`）。暗い値 `:231-239`。予定専用の古い Google 色のトークンが既に在る: `--calendar-google-blue` #1a73e8 / 暗 #8ab4f8・`--calendar-google-blue-light` #e8f0fe / #1e3a5f・`--calendar-today-bg` #1a73e8 / #8ab4f8・`--calendar-grid-border` #dadce0 / #3c4043（`frontend/src/index.css:184-187,385-388`）。今の時刻の線 `--schedule-now-line` #ea4335（`frontend/src/tokens.css:401`）。
- 予定の箱の色は持ち主（社員）の色で、正本はサーバー（`frontend/src/pages/schedule/schedule-owner.ts:35` のコメント・`backend/app/routers/calendar.py` `_DEFAULT_OWNER_COLOR`）。Google も箱の色はカレンダーごとの色。→ 箱の地の色は変えない（DB の正本のまま）。
- 暗い表示（PO の選択「1」2026-11-11 で Google の「デザイン」をライトモード→ダークモードに切り替えて測り、ライトモードに戻した。戻ったことは設定の選択「light=true」と画面で確かめた。保存していない）:
  - 週の表: ページの地 rgb(27,27,27)・表の札 rgb(19,19,20)。日の列の線 1px rgb(51,53,55)。今日の丸 rgb(168,199,250)・文字 rgb(6,46,111)。今の時刻の丸 rgb(245,94,87)。文字 rgb(227,227,227)・絵と補足 rgb(196,199,197)。外枠のある操作の枠 1px rgb(142,145,143)。「作成」ボタンの地 rgb(55,57,59)。選ばれた表示切替の地 rgb(0,74,119)・文字 rgb(255,255,255)。予定の箱はカレンダーの色を暗い表示向けに変えた色（rgb(3,155,229)→rgb(75,153,210)）・文字 rgb(19,19,20)。
  - 作る小窓: 地 rgb(30,31,32)。選ばれた種類の地 rgb(0,74,119)・文字 rgb(194,231,255)。文字 rgb(227,227,227)・絵と補足 rgb(196,199,197)。保存 地 rgb(168,199,250)・文字 rgb(6,46,111)。
  - 詳しくの小窓: 地 rgb(30,31,32)。「Google Meet に参加」地 rgb(168,199,250)・文字 rgb(6,46,111)。文字のリンク rgb(168,199,250)。
  - 編集画面: 地 rgb(27,27,27)・札 rgb(19,19,20)。塗りの欄 rgb(40,42,44)。文字 rgb(227,227,227)・絵と案内文 rgb(196,199,197)。題名の下線 1px rgb(196,199,197)・押すと 3px rgb(168,199,250)。選ばれたタブ rgb(168,199,250)・選ばれていないタブ rgb(196,199,197)・タブの下の線 1px rgb(68,71,70)。チェック欄（入）rgb(168,199,250)・（切）枠 2px rgb(196,199,197)。保存 地 rgb(168,199,250)・文字 rgb(6,46,111)。
- 箱の色の暗い表示: Google はカレンダーの色を暗い表示で別の色に変える。アプリの箱の色はサーバーの持ち主の色をそのまま描く。→ 箱の色は今回変えない（正本はサーバー）。

### 8.5 未確認

- Google の暗い表示の編集画面 → §8.6 で測った（2026-11-11）。
- Google の日付の欄は押すと Google の暦が開く。アプリはブラウザの日付・時刻の欄（native）のまま。
