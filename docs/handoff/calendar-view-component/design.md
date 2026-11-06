# 予定の時間割・月の升目の金型（CalendarView）— design

状態: 設計案（Opus 作成 2026-11-06）・Opus 自己審査 APPROVE（§10。同じ AI による審査で、独立した第二者の審査ではない）・PO 決定済み（2026-11-06「1」）・実装未着手。
調査: [recon.md](recon.md)（docs/handoff/calendar-view-component/recon.md）。ADR: [ADR-1065](../../adr/ADR-1065-calendar-view-component-fullcalendar-v6.md)。

## 1 目的（PO の言葉と、読み取った目的）
- PO（2026-11-06「1」）: 「FullCalendar を包んだ部品を部品集に登録して、予定画面に使う」。
- PO（2026-10-30）: 「フロントエンドのパーツもデザイントークンとデザインシステムを遵守して、金型登録のないハードコードを禁止する」。
- 目的: agent-console の予定画面（PO 承認済みの成功条件（１）（５）（８）（９））を、金型とトークンだけで作れるようにする。時間割と月の升目を、ページごとの作り込みでなく部品集の1か所で持つ。

## 2 成功条件（○×で判定）
| 番号 | 基準 | 検証方法 |
|---|---|---|
| K1 | 部品集に `CalendarView` が増え、Storybook に「Components/CalendarView」の見本が7つ出る（2列・7列・月・重なり・見積もりの点線・時間外の予定・暗い画面） | CI の Storybook build check が緑。stories のファイルに7つの export |
| K2 | 2列（今日・明日）と7列の時間割、月曜始まりの月の升目が出る | 試験 T3（FullCalendar に渡す値）が緑 |
| K3 | 1時間の高さが 48px（トークン `--schedule-row-height` の値） | 評価役が Storybook の「2列」で `.fc-timegrid-slot` の1行の高さを測り 48px（±0.5px） |
| K4 | 重なる予定が横に並び、赤枠になる | T3 で `slotEventOverlap: false`。T2 で conflict の class。評価役が「重なり」の見本の画像で横並び・赤枠を確かめる |
| K5 | 見積もりは点線、実際は実線の枠 | T2 で line の class。評価役が「見積もりの点線」の見本の画像で確かめる |
| K6 | 既定は 8:00〜20:00。範囲の外の予定があれば、その時刻まで目盛りが広がる | T1（時刻の範囲の計算）が緑 |
| K7 | 色・線・影・寸法の直書きが 0。FullCalendar の `--fc-*` 変数は全部トークンで上書きされる | 既存の CSS 検査（check:css-colors・check:css-values）が緑。T4（変数の上書きの漏れ 0）が緑 |
| K8 | 文言は全部 t()。ja.json と en.json のキーが同じ | 既存の i18n の検査が緑。T3 で「ほか N 件」が t() を通る |
| K9 | 既存の画面の見た目と動きは変わらない | 変更ファイルが §3 の対象だけ（PR の変更ファイル一覧）。既存の試験が全部緑 |

## 3 対象と対象外
- 対象（salesanchor）:
  - frontend/src/components/CalendarView.tsx・CalendarView.css・CalendarView.stories.tsx・CalendarView.test.tsx（新規）
  - frontend/src/components/calendarView.utils.ts（新規。純粋な関数だけ）
  - frontend/src/tokens.css（「Schedule page」の段に3行足す。§4-4）
  - frontend/src/locales/ja.json・en.json（`calendarView.*` のキー）
  - frontend/package.json・package-lock.json（@fullcalendar の5つを 6.1.22 に固定。§4-1）
  - docs/adr/ADR-1065（新規）・docs/adr/README.md（索引の再生成）・この設計の書類3つ・作業中の印
- 対象外:
  - 予定ページ（pages/schedule/）は変えない。今の自作の時間割はそのまま。この金型に寄せるかは別の設計で PO に聞く。
  - agent-console の変更（@fullcalendar の依存を足すこと・画面を作ること）は agent-console の便1で行う（§8）。
  - ドラッグで動かす・枠を伸ばす・空き枠を選ぶ（editable・selectable）は作らない。
  - 地名つきの時刻（timeZone の plugin）は入れない（recon §9）。

## 4 作り方

### 4-1 版
- @fullcalendar/core・daygrid・interaction・react・timegrid を `6.1.22` に固定する（`^` を外す）。package-lock.json も 6.1.22 に揃える。
- 理由（ADR-1065 の Why）: 10/30 に動かした比較で要る形が全部出たのは v6。v6 は legacy の札だが 2026-10-16 にも直しが出ている（recon §4）。6.1.22 には React で表示の範囲を state にすると止まらなくなる不具合の直し（#7069）が入っている。v7 は見た目の仕組みが変わり（recon §4）、比較をやり直す必要がある。
- FullCalendar の型や名前は CalendarView.tsx と calendarView.utils.ts の外に出さない。呼ぶ側は FullCalendar を知らない。v7 に上げるときに変わるのはこの2つと CSS だけにする。

### 4-2 部品の形（呼ぶ側に見せるもの）
```ts
export type CalendarViewMode = 'days' | 'month';
export type CalendarEventTone =
  'personal' | 'meeting' | 'purchase' | 'shipping' | 'billing' | 'release' | 'holiday'; // tokens.css の --cal-* と同じ7つ
export type CalendarEventLine = 'solid' | 'dashed';

export interface CalendarViewEvent {
  id: string;
  title: string;
  start: Date | string;   // ISO 8601
  end?: Date | string;
  allDay?: boolean;
  tone?: CalendarEventTone;   // 既定 'personal'
  line?: CalendarEventLine;   // 既定 'solid'（見積もりは 'dashed'）
  conflict?: boolean;         // 重なりの赤枠
}

export interface CalendarViewProps {
  mode: CalendarViewMode;
  date: Date | string;        // days: 最初の列の日／month: その月の中の日
  dayCount?: 1 | 2 | 3 | 4 | 5 | 6 | 7;   // days の列の数。既定 7
  events: CalendarViewEvent[];
  startHour?: number;         // 既定 8
  endHour?: number;           // 既定 20
  monthMaxEvents?: number;    // 既定 2。超えた分は「ほか N 件」
  renderEventContent?: (event: CalendarViewEvent, timeText: string) => ReactNode;
  onEventClick?: (id: string) => void;
  onDayClick?: (date: Date) => void;   // 月の升目の日付・「ほか N 件」を押したとき
  ariaLabel: string;
  className?: string;
}
```
- 金型の外への export はこの型と `CalendarView` だけ。

### 4-3 FullCalendar に渡す値（CalendarView.tsx）
| 値 | days | month | 理由 |
|---|---|---|---|
| plugins | timeGridPlugin・dayGridPlugin | 同じ | |
| views | `{ calendarDays: { type: 'timeGrid', duration: { days: dayCount } } }` | — | 2列・7列を同じ形で出す |
| initialView | `'calendarDays'` | `'dayGridMonth'` | |
| initialDate | `date` | `date` | |
| headerToolbar | `false` | `false` | 送るボタンは呼ぶ側が金型 Button で置く |
| firstDay | 1 | 1 | 月曜始まり |
| fixedWeekCount | — | `false` | 5〜6行 |
| slotDuration・slotLabelInterval | `'01:00:00'` | — | 1行＝1時間 |
| slotLabelFormat | `{ hour: '2-digit', minute: '2-digit', hour12: false }` | — | 「08:00」 |
| slotMinTime・slotMaxTime | §4-5 の計算 | — | |
| slotEventOverlap | `false` | — | 重なりは横に並べる |
| allDaySlot | `true` | — | 終日の帯 |
| nowIndicator | `true` | `true` | いまの線 |
| dayMaxEvents | — | `monthMaxEvents` | |
| moreLinkContent | — | `t('calendarView.more', { count: arg.num })` | 文言は t() |
| moreLinkClick | — | 関数。呼ぶ側の `onDayClick(arg.date)` を呼び、`arg.view.type` を返す（§4-3-1） | 小窓の影（直書きの rgba）を出さない |
| showNonCurrentDates | — | `false` | 前後の月の日に予定と「ほか N 件」を出さない（§4-3-1） |
| navLinks・navLinkDayClick | — | `true`・`onDayClick(date)` | 日付を押すと呼ぶ側へ |
| eventClick | `onEventClick(id)` | 同じ | |
| eventClassNames | §4-6 | 同じ | |
| eventContent | `renderEventContent` があればそれ、無ければ「時刻 題名」 | 同じ | |
| editable・selectable | `false` | `false` | 対象外 |
| height | `'auto'` | `'auto'` | 高さは中身で決まる（1時間＝トークン） |
| locale | `i18n.language` が `ja` で始まれば `@fullcalendar/core/locales/ja`、それ以外は既定（英語） | 同じ | |
- `date`・`mode`・`dayCount` が変わったら、`ref.getApi()` の `changeView`・`gotoDate` で合わせる（作り直さない）。
#### 4-3-1 「ほか N 件」を押したとき（2026-11-06 Opus が確かめた）
- 公式頁（https://legacy.fullcalendar.io/v6/moreLinkClick）の文: 「A callback function can return a string value, like "day", that will be processed as the new value of the setting.」「view name: A literal string name of any of the available views.」。小窓を開かない方法は頁に書かれていない。
- 6.1.22 の実物（@fullcalendar/core internal-common.js:7452-7467）: 関数の戻り値が空か `'popover'` なら小窓を開く。文字列なら `calendarApi.zoomTo(date, 戻り値)` を呼ぶ。zoomTo（同 :4984-5003）は、その名前の表示があれば同じ日付でその表示に切り替える。
- なので、関数は `onDayClick(arg.date)` を呼んだあと、いまの表示の名前 `arg.view.type`（`'dayGridMonth'`）を返す。同じ月の日付で同じ月の表示に切り替わるだけなので、見た目は変わらない。
- 前後の月の日で押されると、その月へ動いてしまう。`showNonCurrentDates: false`（公式の設定）で前後の月の日に予定を出さず、そこに「ほか N 件」が出ないようにする。
- 日付を押したとき（navLinkDayClick）は、関数を渡せば FullCalendar は表示を変えない（同 :5518-5529）。
- T5（§7）で、6.1.22 の internal-common.js にこの2か所の処理がそのまま有ることを文字で確かめる。版を上げて形が変われば落ちる。
- 包む要素: `<div className="comp-calendar comp-calendar--{mode} {className}" role="region" aria-label={ariaLabel}>`。

### 4-4 トークン（tokens.css の「Schedule page」の段に足す）
```css
  --schedule-gridline-w:      1px;      /* 時間割の罫線の太さ（1時間の高さから引く） */
  --schedule-event-border-w:  2px;      /* 予定の枠の太さ（見積もり・重なり） */
  --schedule-event-estimate-style: dashed; /* 見積もりの枠の線の種類（実際は solid） */
```
- 色は足さない。重なりの赤は `--danger`、いまの線は `--schedule-now-line`、罫線は `--schedule-gridline` を使う。
- 暗い画面: 足すのは寸法と線の種類だけなので明暗で値は変わらない（check-dark-parity は index.css だけを見る。recon §5）。

### 4-5 時刻の範囲（calendarView.utils.ts の `computeHourRange`）
- 入力: `events`・`startHour`・`endHour`。出力: `{ slotMinTime: 'HH:00:00', slotMaxTime: 'HH:00:00' }`。
- `allDay` の予定は数えない。`end` が無い時刻つきの予定は開始＋1時間として数える。
- 最小 = min(startHour, 各予定の開始の「時」を切り捨て)。最大 = max(endHour, 各予定の終了の時刻を「時」に切り上げ)。日をまたぐ予定は、その日の 24:00 まで（`'24:00:00'`）で止める。
- 時刻は動かしている機械の時刻（`Date` の getHours）で読む（recon §9）。

### 4-6 予定の class（calendarView.utils.ts の `eventClassNames`）
- `['comp-calendar__event', 'comp-calendar__event--tone-{tone}', 'comp-calendar__event--line-{line}', conflict ? 'comp-calendar__event--conflict' : null]` から null を除いたもの。既定は tone `personal`・line `solid`。
- CSS: 色は `--cal-{tone}`（枠）・`--cal-{tone}-tint`（地）・`--cal-{tone}-text`（字）。`--line-dashed` は `border-style: var(--schedule-event-estimate-style)`・`border-width: var(--schedule-event-border-w)`、地は `--bg-surface`。`--conflict` は `border-color: var(--danger)`・`border-width: var(--schedule-event-border-w)`。

### 4-7 CSS（CalendarView.css）
- `.comp-calendar` の中で、FullCalendar 6.1.22 の core・daygrid・timegrid が使う `--fc-*` 変数を全部トークンに置き換える。対応の例: `--fc-border-color: var(--schedule-gridline)`、`--fc-page-bg-color: var(--bg-surface)`、`--fc-neutral-bg-color: var(--schedule-hour-bg)`、`--fc-neutral-text-color: var(--text-muted)`、`--fc-today-bg-color: var(--schedule-slot-hover)`、`--fc-now-indicator-color: var(--schedule-now-line)`、`--fc-event-bg-color: var(--cal-personal-tint)`、`--fc-event-border-color: var(--cal-personal)`、`--fc-event-text-color: var(--cal-personal-text)`、`--fc-more-link-text-color: var(--accent)`、`--fc-highlight-color: var(--schedule-slot-hover)`。残りの変数（6.1.20 で core 27・daygrid 6・timegrid 11 の名前。recon の手順で 6.1.22 を数え直す）も同じ形で全部置く。寸法の変数（`--fc-small-font-size` など）は既存の寸法・文字のトークンに置く。
- 変数を通らない直書きの色（6.1.20 で core に box-shadow 5・rgba 3、daygrid に rgba 2）は、出どころの class を特定し、(a) 使わない機能（ボタン・小窓・ドラッグ・選択）の物は使わないことを表にして PR 本文に書く、(b) 使う物は `.comp-calendar` の中のセレクタで `var(--shadow-*)` などのトークンに上書きする。
- 1時間の高さ: `.comp-calendar .fc-timegrid-slot { height: calc(var(--schedule-row-height) - var(--schedule-gridline-w)); }`。K3 で 48px を測る。
- 時刻の列の幅は `--schedule-time-gutter-width`、月の升目の高さは `--schedule-month-cell-min-h`、予定の角丸は `--schedule-event-radius`、日の列の最小の幅は `--schedule-day-min-w`。
- `#`・`rgb(`・`rgba(` の直書きは 0。px の直書きは 0（`calc()` の中の var だけ）。

### 4-8 文言（ja.json・en.json に同じキー）
- `calendarView.more`: ja「ほか {{count}} 件」、en「{{count}} more」。
- `calendarView.allDay`: ja「終日」、en「All day」（`allDayContent` に渡す）。

### 4-9 見本（CalendarView.stories.tsx、7つ）
TwoDays（今日・明日、予定3件）／Week（7列）／Month（1日に4件ある日を含む）／Conflict（重なる2件、conflict）／Estimate（見積もりの点線と実際の実線を同じ時間に）／OutsideHours（7:00 開始と 21:30 終了の予定）／Dark（`document.documentElement.classList.add('force-dark')` を見本の中だけで付けて外す。index.css:218 の `:root.force-dark`）。日付は見本の中で `new Date()` から作る（固定の日付を書かない）。

## 5 代替案と選んだ理由
| 案 | 見送った理由 |
|---|---|
| FullCalendar v7 | 見た目の仕組みが変わり、10/30 の比較が使えない（recon §4）。v6 の手入れが続いている間は v6 で包み、上げるときは金型の中だけを変える |
| Schedule-X | 10/30 の比較でいまの線の色が変数で変えられず、日本語に別の部品が要った（agent-console design.md §15-1） |
| 予定ページの自作の時間割を外に出す | 予定ごとの見た目を変えられない・24時間固定・Sales Anchor だけの物に頼る（同 §15-1） |
| 一から作る | PO が既製の部品を選んだ（2026-11-06「1」） |

## 6 リスクと対処
| リスク | 対処 |
|---|---|
| v6 の手入れが止まる | ADR-1065 に「v7 に上げる条件」を書く。型と名前を金型の外に出さない（§4-1） |
| 版を上げたとき、新しい `--fc-*` 変数がトークンを通らない | T4 が node_modules の実物から変数を数え、CSS に無い物があれば落ちる |
| CSP で inline style を止めると FullCalendar の見た目が崩れる | 今は両方とも 'unsafe-inline'（recon §8）。止める変更をするときはこの金型を確かめる、と ADR-1065 に書く |
| agent-console と salesanchor で版がずれる | agent-console の便1で同じ 6.1.22 に固定する。agent-console の設計書 §15-1 に書く |
| jsdom で FullCalendar を描けない | 試験は FullCalendar を差し替えて渡す値を見る（T3）。見た目は評価役が Storybook で見る |

## 7 試験（CalendarView.test.tsx。Mac では流さず CI で流す）
- T1 `computeHourRange`: 予定なし→08〜20／7:30 開始→07〜20／21:15 終了→08〜22／終日だけ→08〜20／end 無しの 19:30 開始→08〜21／23:30〜翌 1:00→08〜24。
- T2 `eventClassNames`: 既定（personal・solid・conflict なし）／tone meeting・line dashed・conflict true の class の並び。
- T3 `@fullcalendar/react` を vi.mock で差し替え、渡された props を見る: days・dayCount 2 で views の duration が 2 日・slotEventOverlap false・nowIndicator true・headerToolbar false・editable false／month で dayMaxEvents 2・fixedWeekCount false・firstDay 1／moreLinkContent が t('calendarView.more') の結果を返す／moreLinkClick と navLinkDayClick が onDayClick を呼ぶ／eventClick が onEventClick(id) を呼ぶ。
- T5 node_modules/@fullcalendar/core/internal-common.js に `if (!moreLinkClick || moreLinkClick === 'popover')` と `context.calendarApi.zoomTo(date, moreLinkClick)` の2つの文字があることを確かめる（§4-3-1）。T3 で month のとき moreLinkClick が `onDayClick` を呼び `view.type` を返すこと、showNonCurrentDates が false であることも見る。
- T4 node_modules の @fullcalendar/core・daygrid・timegrid の index.js と internal の .js から `--fc-[a-z-]+` を全部拾い、CalendarView.css の `.comp-calendar` の中に同じ名前の定義があるかを見る。無い名前があれば名前を出して落ちる。

## 8 その後（この PR の外）
- agent-console 便1: package.json に @fullcalendar の5つを 6.1.22 で足す。`@sa/components/CalendarView` を予定画面で使う（agent-console design.md §4-1）。日＝dayCount 2・週＝7・月＝month。送るボタンは金型 Button。
- 予定ページ（Sales Anchor）をこの金型に寄せるかは、PO に聞いてから別の設計で。

## 9 戻し方
- この PR を revert する。金型を使っている画面はまだ無いので、画面の見た目は変わらない。package.json の版は ^6.1.20 に戻る（ソースから使う所が無いので動きは変わらない）。

## 10 審査（Opus 自己審査・2026-11-06）
- 既存の決まりとの合い方: ADR-144（金型の登録は PO の許可＋3点セット）→ PO「1」・§3 の4ファイル。ADR-067（直書き禁止）→ §4-7・K7・T4。ADR-073（stories）→ K1。ADR-027（t()）→ §4-8・K8。○
- 根拠: 版・CSP・変数・トークンはすべて recon の実物（行番号・コマンド・公式頁）で確かめた。○
- 確かめられる受入: K1〜K9 はすべて CI か評価役の測定で○×が決まる。○
- 範囲: 触るファイルを §3 で列挙。予定ページ・agent-console は対象外。○
- 残る未確認: 無し。`moreLinkClick` の返し方は §4-3-1 で公式頁と 6.1.22 の実物で確かめた（クラウドからは公式頁に届かず、1回目の実装が止まったため Opus が手元で確かめた）。6.1.22 の変数はクラウドで数えて 6.1.20 と同じ（core 27・daygrid 6・timegrid 11、重なりを除き28）。
- 判定: APPROVE。

## 11 維持の仕組み
- T4 が版を上げるたびに変数の漏れを見る。既存の CSS 検査・stories の検査・i18n の検査が直書きと文言を見る。
- 持ち主: 金型の正本は salesanchor frontend/src/components/CalendarView.*。版を上げる判断は ADR-1065 の条件で行う。
- 守り手: frontend/src/components/CalendarView.test.tsx

## 12 外部・過去事例の参照と我々への応用
- 該当なし：外部事例は使っていない。理由: 決めることは「どの既製品をどの版で包むか」で、根拠は 10/30 に実際に動かした比較と、公式頁・npm の記録（recon §4）で足りる。他社の導入の数を、この金型の成功の証明には使わない。
