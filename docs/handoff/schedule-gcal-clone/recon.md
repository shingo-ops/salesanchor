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
| `docs/adr/ADR-027-ui-internationalization.md`・`ADR-067-design-token-enforcement.md`・`ADR-144-ui-component-governance.md` | 文字は t()・色と大きさはトークン・部品は金型を先に使う |
| `docs/adr/ADR-135-release-stowaway-prevention.md`・`ADR-136-cc-bot-github-identity.md` | 危険な道を含む便は PO の「GO #番号」 |

前の設計: `docs/handoff/schedule-gcal-alignment/design.md`（K1〜K14。便1 #5124・便3 #5135 は本番済。便2 は設計の枝 `origin/release/schedule-gcal-bin2-design` で審査合格のまま main に入っていない）。

## 1. 止まった理由（記録の事実）

- 便2 のカードは 2026-11-04 23:48 にクラウドの再審査 3 回目で APPROVE（`origin/release/schedule-gcal-bin2-design` 9545d849d）。
- 便2 の着手条件は「便1 が本番に出て PO が K1〜K7 を見たあと」（`docs/handoff/schedule-gcal-alignment/design.md:50`）。
- PR #5124 のコメントに「K2 は本番反映後にブラウザで確かめる」とある。PO に K1〜K7 の確認を頼んだ記録・K2 をブラウザで確かめた記録は見つからない（`git grep "K1〜K7"`・`gh pr view 5124 --json comments`）。
- 台帳 `.claude-pipeline/active-work.d/release-schedule-gcal-bin2-design.md` は IN_PROGRESS のまま。
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
| D2 | 目盛り「午後1時」 | 「13:00」 | `SchedulePageImpl.tsx:757` |
| D3 | 1 時間の高さ 約 69px（画面写し上） | 約 34px（画面写し上。css は `--schedule-row-height: 48px` `frontend/src/tokens.css:403`） | 同じ縮尺の画面写しで比べた。css の実寸は Google 側未確認 |
| D4 | 終日の行に「文化の日」（「日本の祝日」カレンダー） | 祝日を出す仕組みが無い。種類の選択肢に「日本の祝日」はある | `git grep -i holiday` はシフトの休みだけ（`schedule-utils.ts:235`） |
| D5 | 枠を押すと押した時刻。押した所に「（タイトルなし）」の仮の箱 | 07:00 固定（B1）。仮の箱なし | 本番で操作 |
| D6 | 小窓: 題名欄が先頭で入力状態。日時は 1 行の文（「11月 4日 (水曜日) 午後4:00 – 午後5:00」）。ゲスト・Meet・場所・説明は押すと開く 1 行。下に「その他のオプション」「保存」 | 種類の選択・終日・Meet・社員にも見せる・日付と時刻の入力欄 4 つ | 本番で操作（Google 側は保存せず閉じた） |
| D7 | 引っぱって作る・つかんで動かす・長さを変える | どれも無い（`onPointerDown`・`onMouseDown`・`draggable` 0 件） | 前の設計の便2（K8〜K11） |
| D8 | 表示の切替は 1 つのボタン「週 ▾」 | 日・週・月・一覧の 4 ボタン | 画面 |
| D9 | 月の升目が画面の下まで | 升目 763px／窓 1448px。下が空く | 本番で寸法を読んだ |
| D10 | ToDo の「4 件の保留中のタスク」が出る | 出ない | 画面 |
| D11 | 開くと今の時刻のあたり（午前11時〜）から見える | 0:00 から（行が 48px なので 1 日がほぼ入る） | 画面 |

動いたもの: 予定を押すと詳しく（Meet で参加を含む）、月の 1 行表示、一覧 30 日、近道の一覧（? で 12 個）、日・次へ・今日、他のカレンダーの切替、設定。

## 4. 金型と今の作り（SSOT）

- 金型 `frontend/src/components/CalendarView.tsx`（168 行）は FullCalendar を包む。`editable={false}`・`selectable={false}`（`:160-161`）、`firstDay={1}` 月曜始まり固定（`:150`）、目盛り `{hour:'2-digit',minute:'2-digit',hour12:false}`（`:35`）、色は種類 7 つの `tone`（`frontend/src/components/calendarView.utils.ts:9-16`）だけ。押す口は `onEventClick`・`onDayClick` だけ（`calendarView.utils.ts` の `CalendarViewProps`）。
- Sales Anchor の予定の画面は金型を使っていない。`frontend/src` の中で `CalendarView` を使う画面は 0 件（`grep -rln CalendarView frontend/src`）。自前の時間割が `SchedulePageImpl.tsx`（1624 行）＋ `schedule.css`（1489 行）にある。
- → ADR-1065 What 1 と食い違う（時間割が 2 か所）。
- 予定の色は担当者の色（`SchedulePageImpl.tsx:198-210` `getOwnerMeta`。色は裏側 `backend/app/routers/calendar.py:183` `COALESCE(cos.color, :default_color)` から＝DB が正本）。金型の `tone` は種類の色で、担当者の色を受ける口が無い。

## 5. 公式資料（Context7 は月の上限で使えなかった：`Monthly quota exceeded`。公式を直接読んだ）

- https://fullcalendar.io/docs/selectable : `selectable`（既定 false）は日・時間枠を押して引っぱり選べる。`interaction` プラグインが要る。選ばれたときは `select`。
- https://fullcalendar.io/docs/editable : `editable`（既定 false）は予定を動かす・長さを変える。予定ごとの `editable` で上書きできる。`interaction` プラグインが要る。
- `frontend/package.json:75` に `@fullcalendar/interaction` 6.1.22 は入っている。

## 6. 未確認

- 会社の Google 接続で「日本の祝日」カレンダー（`ja.japanese#holiday@group.v.calendar.google.com`）を読めるか。手元の Google カレンダー接続は期限切れで試せなかった（`session expired`）。
- Google の 1 時間の高さの css の実寸。
- 狭い窓（高さ 768px など）での小窓の収まり（前の便1 の K1 は自動試験だけ）。
