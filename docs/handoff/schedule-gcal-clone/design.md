# design: 予定の画面を Google カレンダーと同じ使い心地にする（作り直し）（2026-11-06）

状態: 成功条件 G1〜G14 は **PO 承認済み**（2026-11-06、PO 原文「1.」＝「この14項目で決める」を選択）。設計審査 1 回目・2 回目は REVISE、3 回目は **APPROVE**（§9）。3 回目の推奨 2 件も直した。実装は未着手。
実装の承認: PO はこのセッションの冒頭で「PRマージ、デプロイまで完走させてくれ」、3 択で「3」（違いもまとめて設計し直してから全部いっしょに作る）と指示した。設計審査の APPROVE と便ごとのカードが揃った便から作る。
追加（2026-11-07）: 見た目 5 か所の成功条件 G15〜G19 は **PO 承認済み**（PO 原文「１，」＝「この決め方で設計を進める」を選択）。作り方は §3.8・便6。設計審査は §9 の 4 回目（REVISE）・5 回目（**APPROVE**）。
追加（2026-11-08）: 便8（残りの部品を決められた部品に差し替える・G26〜G30）は PO の選択「1」（2026-11-08）。作り方は §3.13。設計審査は §9 の 11 回目。
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
| G11 | 表示の切替は 1 つのボタン（「週 ▾」）で、押すと日・週・月・一覧が選べる（便7 で 3日間を足す＝G22） | 画面で見る | D8 |
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

### 2.2 上の帯・メニューボタン・3日間・1時間の高さ（G20〜G25・便7・2026-11-08 追加）

PO の言葉（2026-11-08）: 「ヘッダーをGoogleと同じく上部だけに収まる仕様にして、左上にハンバーガーメニューを設置してGoogleカレンダーのように日、3日間、週、月、の切り替えが出来るようにする」。その前の PO の選択「2」: 1 時間の高さを Google と同じく画面の高さに合わせる（約 13 時間見える）・今の時刻の点が半分切れる不具合・一番上の時刻の文字が切れる不具合も直す。
範囲: 幅 1024px 以上（PC）。1023px 以下の並び方・メニューボタンを押した後の細かい動きは Android 側の担当が決める（PO 2026-11-08）。便7 は口（ボタンと切替の状態）を用意するだけで、1023px 以下の css は変えない。

| # | 基準 | 検証方法 | recon |
|---|---|---|---|
| G20 | 上の帯が 1 段。ページ題「スケジュール」の下の説明の文が出ない。帯の高さ（`.page-layout-header` の高さ）が 72px 以下（計算 70px＝上の余白 10＋題の行 40＋下の余白 20・`frontend/src/pages-layout.css:62-75`・`frontend/src/tokens.css:223-224`。説明の文の無い他の画面と同じ高さ。金型の余白は全画面に響くので変えない） | 窓 1440 幅で `.page-subtitle` が 0 個・`.page-layout-header` の getBoundingClientRect().height | R7-1 |
| G21 | 帯の一番左（ページ題より左）にメニューボタン（三本線）がある。押すと左の欄（小さい月の表・カレンダーの一覧）が消えて、時間割が左の欄の幅のぶん広がる。もう一度押すと戻る。開いた時は出ている | 押す前後で `.schedule-sidebar` の有無と `.schedule-calendar` の幅を読む（差が 276px±16px＝左の欄 256px＋間の `--schedule-shell-gap` 20px・`frontend/src/pages/schedule.css:5`） | R7-2 |
| G22 | 表示の切替に「日・3日間・週・月・一覧」がこの順で並ぶ。3日間を選ぶと列が 3 本（選んでいる日から 3 日）。‹ › で 3 日ずつ進む・戻る。キー「x」でも 3日間になる | 切替を開いて並びを読む・`.fc-col-header-cell` の数・› を押して最初の列の日付が 3 日進むのを見る | R7-3 |
| G23 | 1 時間の高さが窓の高さで変わる: 時間割の見える高さ ÷ 13 を 16px 刻みに丸め、48px 以上 96px 以下。窓 1440x723 で 48px・時間割の見える高さ 1073px で 80px・1242px で 96px（Google の実測と同じ） | `.fc-timegrid-slot` の高さと `.fc-scroller-liquid-absolute` の高さを読む。左の欄を出し入れした後も予定の箱の位置が 1 時間の線とずれない（10 時の予定の箱の上端と 10 時の線の差が 2px 以内） | R7-4 |
| G24 | 今の時刻の丸（直径 12px）が欠けずに丸ごと見える | 丸の getBoundingClientRect の幅と、画面写しで丸の左右が切れていないこと | R7-5 |
| G25 | 昼（例: 午後3時台）に開くと、一番上に見える時刻の文字（例:「午後3時」）が上で切れない。上端は「今の 1 時間前の 30 分」（例: 午後3時31分なら午後2時30分。Google の実測 午前3時31分→上端 午前2時30分と同じ） | 開いた直後に、一番上に見える時刻の文字の上端が時間割の見える上端より下にある | R7-6 |

### 2.3 残りの部品を決められた部品に差し替える（G26〜G30・便8・2026-11-08 追加）

PO の選択（2026-11-08）「1」＝「残りの5か所を決められた部品に差し替える【おすすめ】」。奥の目的: 予定の画面（PC）の部品を全部、決められた部品（金型）とトークンで作り、直書きを残さない（ADR-144・ADR-067）。
範囲: 決められた部品がそのまま使える所だけ（§3.13 の A 組）。決められた部品が形に合わない所（§3.13 の B 組）は今回は変えず、PO に聞く。
測る場所: 本番 /schedule・幅 1024px 以上。予定は保存しない（見るだけ）。

| # | 基準 | 検証方法 | recon |
|---|---|---|---|
| G26 | 予定の詳しくの小窓の右上のボタン 3 つ（直す・消す・閉じる）と、「他 N 件」で開くその日の一覧の小窓の閉じるボタンが、決められたボタンの部品（`comp-btn comp-btn--ghost comp-btn--icon-only`・大きさ 36px）。画面の中に `.modal-icon-btn` が 0 個。押した時の動き（直す画面が開く・消す確認が出る・閉じる）は今と同じ | 本番で自分の予定を押して小窓を開き、3 つのボタンの class と getBoundingClientRect の幅・高さを読む。単体の試験で押した時の動き | R8-1 |
| G27 | つながった知らせの帯（緑・赤）の × が、決められたボタンの部品（`comp-btn comp-btn--ghost comp-btn--sm comp-btn--icon-only`）で、中身は閉じるの絵（文字の「×」ではない）。押すと帯が消える | 本番で `/schedule?connected=true` を開き（読むだけ・保存しない）、帯の中のボタンの class と中身の `svg` を読む。押して帯が消えるのを見る | R8-2 |
| G28 | 詳しくの小窓の種類の札が、決められた札の部品（`comp-badge comp-badge--soft comp-badge--md`）。7 種類の色は次の表どおりで、要素に `style` が無い: 会議=info・個人=purple・仕入れ=success・発送=danger・請求=warning・リリース=neutral・祝日=purple | 本番で会議の予定を押して札の class と `style` の有無を読む。7 種類全部は単体の試験 | R8-3 |
| G29 | 予定の画面の部品のファイル 4 つ（`frontend/src/pages/schedule/SchedulePageImpl.tsx`・`frontend/src/features/schedule/calendars.config.ts`・`frontend/src/pages/schedule/schedule-owner.ts`・`frontend/src/components/CalendarView.stories.tsx`）に、色の直書き（`#` と 3〜8 桁の英数字）が 0 件（今は 22 件） | `grep -cE "#[0-9a-fA-F]{3,8}\b"` を 4 つのファイルで数える | R8-3・R8-4 |
| G30 | 使われなくなった見た目の規則を消した: `frontend/src/components.css` の `.modal-icon-btn` の 3 つと `frontend/src/pages/schedule.css` の `.schedule-category-chip` が 0 件。`.schedule-banner__close` は置き場所の 2 行（左の間・縦の真ん中）だけ | `grep -c` で数える | R8-5 |
| G31 | 月表示の日付の数字が、升目の上の真ん中に出る（文字 12px・太さ 500）。各月の 1 日だけ「M月1日」（M は月の数字）の形。今日の数字は直径 24px の青い丸に白い字で、今日の升目の地は塗らない（今は升目全体が薄い青・数字は右上「2日」） | 本番の月表示で、今日と 1 日と普通の日の数字の要素の getBoundingClientRect・文字の大きさ・太さ・地の色、今日の升目 `.fc-day-today` の地の色（透明）を読む。単体の試験で「M月1日」（M は月の数字）と今日の丸の class | R9-1・R9-3 |
| G32 | 月表示の曜日の行の文字が、時間割の曜日と同じ（文字 11.2px・太さ 500・時刻の文字と同じ灰色）。今は 13.6px・太さ 700・黒 | 本番の月表示で `.fc-col-header-cell` の中の文字の大きさ・太さ・色を読む | R9-1 |
| G33 | 月表示の、時刻のある 1 日だけの予定が 1 行「色の点（8px）＋始まりの時刻（例「午後8時」）＋題名」で、枠の線と地の色が無い。行の高さは 20〜24px（Google 実測 22px）。終日の予定は今の帯のまま。日をまたぐ時刻のある予定は帯の枠と地のまま、点は出さず中の文字は「始まりの時刻＋題名」の 1 行 | 本番の月表示で時刻のある予定 1 つの高さ・`border-width`・地の色・点の要素の大きさと、中の文字を読む。帯の予定（`.fc-daygrid-block-event`）の中の点の要素の `display` が `none`。単体の試験で 1 行の形と、終日の予定が帯のままなこと | R9-2・R9-4 |
| G34 | 予定の詳しくの小窓の日時が 1 行「11月6日(金) 午後12時30分～午後1時30分」の形（作る小窓・検索の結果と同じ文の作り方）。別の行の日付は無くなる。終日は「11月6日(金) 終日」 | 本番で時刻のある予定と終日の予定を押し、小窓の日時の行の文字を読む。`.schedule-popover__date` が 0 個。単体の試験 | R9-5 |
| G35 | 一覧の表示の行の時刻が 12 時間の形（例「午前7時～午前8時」）。今は「07:00 - 08:00」 | 本番の一覧の表示で、行の時刻の文字を読む。単体の試験 | R9-5 |

## 3. 作り方（How）

### 3.1 時間割を金型 1 か所にする（SSOT）

- 今は予定の画面だけが自前の時間割を持ち、金型 `CalendarView` はどの画面にも使われていない（recon §4）。ADR-1065 What 1「時間割と月の升目は金型で出す」と食い違う。
- 最上位原則（ADR と実装が食い違ったら ADR に寄せる）に従い、**予定の画面を金型 `CalendarView` に載せ替える**。自前の時間割（`frontend/src/pages/schedule/SchedulePageImpl.tsx` の週・日・月の描画と `frontend/src/pages/schedule.css` の対応部分）は消す。
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

方針: 金型 `CalendarView` に口を 1 つ足し（`appearance`）、予定の画面だけがそれを使う。既定は今の見た目のまま（見本帳・他の画面が増えても変わらない）。見た目はすべて `CalendarView.css` の `.comp-calendar--schedule.comp-calendar--days` の下にトークンだけで書く（月の表示の今日の升目・曜日の行に効かせないため。包みの class `comp-calendar--${mode}` は `frontend/src/components/CalendarView.tsx:156`）。下の表の選び方はすべてこの 2 つの class の下。画面側（`frontend/src/pages/schedule/SchedulePageImpl.tsx`・`frontend/src/pages/schedule.css`）に見た目を書かない。

口: `appearance?: 'plain' | 'schedule'`（既定 `'plain'`）。`'schedule'` のとき包みの class に `comp-calendar--schedule` を足し、`mode === 'days'` のときだけ次の 3 つを FullCalendar に渡す。月の表示は変えない。

| 渡すもの | 中身 | 成功条件 |
|---|---|---|
| `slotEventOverlap: true` | 今の `false`（`frontend/src/components/CalendarView.tsx:171`）を `'schedule'` のときだけ true。重なりの形は recon §7.3 の `computeSegHStyle` | G19 |
| `dayHeaderContent` | 曜日と日付の数字の 2 つの `span`。曜日は新しい関数 `formatWeekdayShort(date, language)`（`frontend/src/components/calendarView.utils.ts` に足す・`Intl.DateTimeFormat(language, { weekday: 'short' })`）。数字は `date.getDate()`。今日（引数の `isToday`）は数字に `comp-calendar__daynum--today` | G15 |
| `slotLabelContent` | 今の時刻の文字の作り方（`timeStyle` が `'meridiem'` なら `formatMeridiem`・`:176`、`'h24'` なら今の 24 時間の形）を、時が 0 で分が 0 のときだけ空の文字にする関数で包む（新しい関数 `formatSlotLabel(date, text, t, timeStyle)`・`frontend/src/components/calendarView.utils.ts`。`h24` は FullCalendar の引数 `text` をそのまま返す・作り方は card-bin6.md §2-2） | G18 |

css（`CalendarView.css` の末尾に足す。値は var() と calc() と % だけ）:

| 何 | 書き方 | 成功条件 |
|---|---|---|
| 今日の列の地 | `.comp-calendar--schedule.comp-calendar--days { --fc-today-bg-color: transparent; }`（別の日の列は FullCalendar が地を塗らない透明。同じ透明にして一致させる・5 回目の審査 R4。`transparent` は色の直書きの見張り `check-css-hardcoded-colors.js:23,26` の対象外で、`frontend/src/components/Button.css` などに前例あり） | G15 |
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
- 金型は `tone: "holiday"`（`frontend/src/components/calendarView.utils.ts:16`）と色（`frontend/src/components/CalendarView.css:139-142`）を既に持ち、`editable: false` で予定ごとにつかめなくできる（`frontend/src/components/calendarView.utils.ts:44-45`）。
- 期間は `toRangeStart`・`toRangeEnd`（`frontend/src/pages/schedule/schedule-utils.ts:145-157`）。終わりは含まない日（週は翌週の頭・月は翌月 1 日）。
- 部品の言語: Japan は en_US・ja・th を持ち、既定は ja（holidays の公式説明 https://holidays.readthedocs.io/en/latest/ を 2026-11-07 に直接読んだ。Context7 は月の上限で使えなかった）。
- 内閣府の表の 2026・2027 年は 35 件（Mac で取得した syukujitsu.csv を Shift_JIS から読み直して数えた）。

作り方:
1. 裏側に 新しいファイル backend/app/services/holiday_service.py の `list_japan_holidays(start, end, lang)` を作る（正本はこの関数 1 か所。DB に持たない）。
2. `GET /calendar/holidays?start=YYYY-MM-DD&end=YYYY-MM-DD&lang=ja|en` を `backend/app/routers/calendar.py` に足す。返すのは `{"holidays":[{"date","name"}]}`。ログインは要る（`get_current_tenant`）が、会社によらず同じ答え。`end <= start` と 400 日を超える期間は 422。
3. openapi.json を生成し直す（CI「API contract is up to date」）。
4. 画面は 4 本目の `useApiQuery` で読み、`toHolidayEvents` で `allDay: true`・`tone: "holiday"`・`editable: false` の箱にして `calendarEvents` の最後に足す。名前は画面の言語（`i18n.language` が en で始まれば en、それ以外は ja）で裏側が返すので、文言キーは足さない。
5. 祝日の読み込みは、読み込み中の印・取れなかった文に入れない（祝日が取れなくても予定は見える）。
6. 押しても何も開かない・つかめない（G9）は、今の `itemById` の形と `editable: false` で満たす（画面の分岐を足さない）。

選ばなかった案:
- 祝日を `/calendar/events` の答えに混ぜる → 予定（会社の DB）と祝日（部品）の正本が 1 本の答えに混ざり、予定の直し・消しの道が祝日を予定と取り違える恐れがある。道を分ける。
- 画面に祝日の表を持つ（npm の部品や手書きの表）→ 裏側と画面で 2 か所になる（SSOT 違反）。裏側の 1 か所にする。

範囲の外（記録だけ）: 月の升目の前後の月の日（例: 11 月の表示の 10/26〜10/31）には祝日も予定も出ない（今の期間の作りのまま）。一覧の表示は金型を使わないので祝日は出ない（G7 は週と月）。月の升目の「他 N 件」を押して出る一覧の小窓は予定だけから作る（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1276-1277` の visibleEvents）ので、祝日は件数に数えられても小窓の一覧には出ない。直すなら別の便にする（8 回目の審査の推奨）。

試験と確かめ: カード §6・§7。本番では 11 月の週（11/2〜11/8）と月で「文化の日」「勤労感謝の日」が終日の行に出ること（G7）、押して何も開かず、引っぱっても動かないこと（G9）を Chrome で見る。

### 3.11 便5: 題名で予定を探す（G12・2026-11-07）

PO 承認: 成功条件 G12（§2）。便5 の着手は PO が 2026-11-07「1」（便3〜便5 を順に進める）で承認。

今の形（2026-11-07 に origin/main 04edc8e4a で確かめた）:
- 虫めがねのボタンは押しても何も起きない。`frontend/src/pages/schedule/SchedulePageImpl.tsx` の見出しの `aria-label={t("common.search")}` の金型 Button に `onClick` が無い（recon B4）。
- 予定の一覧の道 `GET /calendar/events`（`backend/app/routers/calendar.py` の `list_events`）は期間（start・end 必須）と種類でしか絞れない。題名の絞り込みは無い。
- 見せてよい予定の決まり（共有の予定＋自分の予定だけ。他人の「自分だけ」は返さない）は `backend/app/services/calendar_service.py` の `list_events` の中の 1 か所だけにある。

作り方:
1. 裏側（道を 1 本足す・見せてよい予定の決まりは 1 か所のまま）
   - `calendar_service.list_events` に、省略できる引数 `title_query: Optional[str] = None` と `limit: Optional[int] = None` を足し、`start`・`end` を省略できるようにする（`Optional[str] = None`）。start・end が None のときは期間の条件を付けない。今の呼び出し（期間を渡す）の SQL は 1 字も変えない。
   - `title_query` があるときだけ `ce.title ILIKE :title_q ESCAPE '\'` を足す。`:title_q` は `%` + 文字の `\`・`%`・`_` を `\` で逃がした値 + `%`。並びは `ORDER BY ce.start_datetime DESC`（新しい予定が上）、`limit` があるときだけ `LIMIT :limit`。
   - 新しい道 `GET /calendar/events/search?q=...` を `list_events` の道のすぐ後に置く。`q` は前後の空白を除いて 1〜100 文字（外れたら 422）。返す形は `{"events": [...]}` で `/calendar/events` と同じ。件数は最大 50。ログイン必須（`get_current_tenant`・`get_current_user`）。
   - `/calendar/events/{event_id}` は PATCH と DELETE だけで GET は無い（`backend/app/routers/calendar.py` の `@router.patch` `@router.delete`）。GET の `/calendar/events/search` とはぶつからない。
2. 画面（金型だけで作る・色や大きさの直値なし）
   - 虫めがねを押すと、見出しの虫めがねの場所に金型 `TextFieldControl`（`variant="search"`・`type="search"`）が出て、すぐ文字が打てる。中の文字の例は「題名で予定を探す」（新しい言葉は ja.json・en.json に同じキーで足す）。
   - 打った文字で道を呼ぶのは、Enter を押したときだけ（1 文字ごとに呼ばない）。
   - 結果は金型 `Popover`（制御式 `open`・`onOpenChange`。子＝トリガーは検索の欄）の中に金型 `ListRow` を並べる。1 行の題名は予定の題名、下の行は「11月10日(火) 午前10時～午前11時」の形（便3 の `formatDraftDateLine` を使う。終日の予定は「11月10日(火) 終日」）。見つからないときは金型 `EmptyState` で「見つかりませんでした」。
   - 結果の行を押すと、表示の基準日（`setAnchorDate`）をその予定の始まりの日にし、検索の欄と結果を閉じる。表示の種類（日・週・月・一覧）は変えない。
   - Esc で検索の欄と結果を閉じ、虫めがねに戻る。検索の欄の中では文字の近道は効かない（今の近道の処理は入力欄を除外済み）。
3. 触らないもの: 金型 `frontend/src/components/`、migrations、deploy、本番 scripts、DB の形、`/calendar/events` の今の動き。

受入れ（G12）:

| 基準 | 検証方法 |
|---|---|
| 虫めがねを押すと検索の欄が出て、そのまま文字が打てる | 試験（押して入力欄に focus）と本番で目視 |
| 「商談」で Enter を押すと、題名に「商談」を含む予定が新しい順に出る（最大 50 件） | 裏側の試験（SQL の条件と並び・件数）、画面の試験（作り物の答えが行に出る）、本番で目視 |
| 他人の「自分だけ」の予定は検索に出ない | 裏側の試験（見せてよい予定の条件が同じ SQL に入る） |
| `%` や `_` を打っても全部が当たらない | 裏側の試験（逃がした値になる） |
| 結果の行を押すと、その予定の日が画面に出る | 画面の試験（押した後に見出しの日付が変わる）、本番で目視 |
| 当たりが無いと「見つかりませんでした」が出る | 画面の試験 |
| Esc で閉じる | 画面の試験 |

選ばなかった案:
- 画面に読み込んだ予定（今の週だけ）の中を探す: 先の週や前の月の予定が探せない。G12 の「探して押すとその日へ飛ぶ」が成り立たない。
- `/calendar/events` に `q` を足す: 期間が必須の道なので、期間を外す変更が今の呼び出し全部に響く。道を分ければ今の道は 1 字も変わらない。
- 新しい service 関数を作り SQL を写す: 見せてよい予定の決まりが 2 か所になる（SSOT 違反）。

心配と対処:
- 予定が多い会社で遅くなる: 最大 50 件・Enter のときだけ呼ぶ。題名の索引は今回は足さない（DB を触らない）。遅さが出たら別の作業で索引を足す。
- 金型 Popover はトリガー（検索の欄）を押すと開閉が切り替わる（`frontend/src/components/Popover.tsx` の `handleTriggerClick`）。欄を押して直すたびに結果が閉じないよう、検索の欄の `onClick` で `stopPropagation` する（金型は変えない）。

### 3.12 便7: 上の帯を 1 段・左上のメニューボタン・3日間・1時間の高さ・不具合 2 つ（G20〜G25・2026-11-08）

確かめた事実（行番号は origin/main 5a531586a）:
- R7-1: 帯が 2 段なのは、予定の画面が説明の文の口を渡しているため（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1364` `subtitleKey="schedule.subtitle"`）。金型は口があると題の行の下に `p.page-subtitle` を出す（`frontend/src/components/PageLayout.tsx:51-53`）。
- R7-2: 金型 PageLayout は題 `h2` を先に出し、その後に `headerLeft`（`frontend/src/components/PageLayout.tsx:45-46`）。題より左に何かを置く口は無い。三本線の絵は `NAV_ICONS.menu`（`frontend/src/constants/icons.tsx:246`）に在る。左の欄は `.schedule-shell__content` の 2 列の左（`frontend/src/pages/schedule.css:57-65`・幅は `--schedule-leftpanel-width` 256px）。
- R7-3: 表示の種類は `"day" | "week" | "month" | "list"`（`frontend/src/pages/schedule/schedule-utils.ts:3`）。期間は `toRangeStart/End`（同 :195-207）、送り幅は `navigatePeriod`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1164`）、列の日は `viewDays`（同 :1169-1175）、題は `formatRangeTitle`（同 :142-148）、切替は `ContextMenu`（同 :1486）、キーは `handleShortcut`（同 :1340-1343）と近道の一覧（同 :845-856）、金型へは `dayCount={view === "day" ? 1 : 7}`（同 :1542）。金型は `dayCount` 日の `timeGrid` を作る（`frontend/src/components/CalendarView.tsx:104-107`）。
- R7-4: 1 時間の高さは常に `--schedule-row-height` 96px（`frontend/src/components/CalendarView.css:48`・`frontend/src/tokens.css` の予定の段）。Google は窓で変わる（scratchpad 実測: 時間割の見える高さ 517→48px・1073→80px・1242→96px。3 点とも「÷13 を 16px 刻みに一番近い値・下限 48px」で一致）。FullCalendar は窓の大きさの変化だけを聞く（`windowResize`）ので、左の欄の出し入れでは測り直さない。
- R7-5: 丸は線の左端から 6px 左へはみ出す（`CalendarView.css:223-241`）が、親 `.fc-timegrid-now-indicator-container` が `overflow: hidden`（FullCalendar 6.1.22 の既定の css）で切れる（2026-11-08 実測 x=404 で切れる）。
- R7-6: 開いた時の上端は「今 −1 時間 の 00 分」（`frontend/src/components/calendarView.utils.ts:238`）。時刻の文字は線の上下の真ん中に置くため半分上へずらす（`CalendarView.css:260-270`）。上端が線ちょうどなので、その線の文字の上半分が見える範囲の外に出る。

作り方:
1. 帯を 1 段（G20）: `frontend/src/pages/schedule/SchedulePageImpl.tsx:1364` の `subtitleKey="schedule.subtitle"` を消す。説明の文の無い PageLayout は検査 `frontend/scripts/check-page-layout.js:94` で落ちるので、同じファイルの `SUBTITLE_ALLOWLIST`（`:28-33`）に `'schedule/SchedulePageImpl'`（理由: PO 2026-11-08 の「上の帯を 1 段」）を足す。文言キー `schedule.subtitle` は ja/en に残す（他で使っていないが、消すと他の道具の確かめに響くかを今回は調べない。残しても画面は変わらない）。
2. メニューボタン（G21）: 金型 PageLayout に口 `headerStart?: ReactNode` を 1 つ足し、`h2` の前に出す。見た目の props は足さない（`docs/specs/design-system/component-ssot/page-title/design.md` D1 の「見た目は金型が独占」を守る。中身の口であり `headerLeft` と同じ種類）。予定の画面は `headerStart` に金型 `Button`（`variant="ghost" size="md" iconOnly`・`aria-label={t("schedule.togglePanel")}`・`aria-expanded`・中身 `NAV_ICONS.menu`）を置く。状態はページの `useState(true)`（保存しない・開いた時は出ている）。閉じている時は `.schedule-shell__content` に `schedule-shell__content--panel-hidden` を足し、`ScheduleSidebar` を出さない（描かない）。css は `.schedule-shell__content--panel-hidden { grid-template-columns: minmax(0, 1fr); }` を 1 つだけ（幅を問わず 1 列）。
3. 3日間（G22）: 種類に `"threeDay"` を足す。`toRangeStart` は選んでいる日の 0 時、`toRangeEnd` はその +3 日。`viewDays` はその日から 3 日。`navigatePeriod` の送り幅 3。`formatRangeTitle` は「最初の日 - 3 日目」。切替の並びは `["day", "threeDay", "week", "month", "list"]`。キー「x」（Google の「自分で決めた日数」と同じキー）。近道の一覧に `{ keys: ["X"], labelKey: "threeDay" }` を「D」の次に。金型へは `dayCount={view === "day" ? 1 : view === "threeDay" ? 3 : 7}`。文言 `schedule.threeDayView`「3日間」/「3 days」・`schedule.shortcuts.threeDay`「3日間の表示」/「3-day view」・`schedule.togglePanel`「メニュー」/「Main menu」を ja/en に同じキーで足す。
4. 1 時間の高さ（G23）: css だけで決める（JS で高さを測って書かない＝値の出どころを 1 つにする）。
   - トークン（`frontend/src/tokens.css` の予定の段）に `--schedule-row-min: 48px`・`--schedule-row-step: 16px`・`--schedule-visible-hours: 13` を足す（上限は今の `--schedule-row-height` 96px を使う）。
   - `CalendarView.css` の末尾に、`.comp-calendar--schedule.comp-calendar--fill.comp-calendar--days` の中だけ: 時間割の本体の送り枠 `.fc-scroller-liquid-absolute` に `container-type: size`、`.fc-timegrid-slot` に `height: clamp(var(--schedule-row-min), round(nearest, calc(100cqh / var(--schedule-visible-hours)), var(--schedule-row-step)), var(--schedule-row-height))`。`fillHeight` でない使い方（他の画面）は今の 96px のまま。
   - 金型 CalendarView に `ResizeObserver` を 1 つ足し、包みの大きさが変わったら `api.updateSize()` を呼ぶ（左の欄の出し入れで予定の箱の位置を測り直す）。`ResizeObserver` が無い所（試験の jsdom）では何もしない。
5. 今の時刻の丸（G24）: `CalendarView.css` 末尾に `.comp-calendar--schedule.comp-calendar--days .fc-timegrid-now-indicator-container { overflow: visible; }`。
6. 一番上の時刻の文字（G25）: `scrollTimeForNow` を「0 時台は 00:00:00、それ以外は (時−1):30:00」に変える。試験 T9（`frontend/src/components/CalendarView.test.tsx:290-297`）の期待値を 12:34→`11:30:00`・0:10→`00:00:00` に直し、1:05→`00:30:00` を足す。
   - 限界: 夜遅く（午後11時台など）は下の端に当たって上端が決めた位置まで送れない。その時は上端が線ちょうどになることがある（Google も同じく下の端で止まる）。

選ばなかった案:
- 1 時間の高さを JS で測ってトークンに書く: 値の出どころが css と JS の 2 か所になる。css の容器の大きさ（container query）で 1 か所に決まる。
- 画面の高さ（`100vh`）で割る: 帯や終日の行の高さが入ってしまい、時間割の見える高さと合わない。Google の 3 点は時間割の見える高さで一致した。
- メニューボタンを `headerLeft` に入れる（金型を変えない）: 題「スケジュール」の右に出てしまい「左上」にならない。
- 左の欄の開け閉めを保存する: PO の言葉に無い。Android 側の決めごとに任せる。

心配と対処:
- `round()` と容器の単位 `cqh` は古いブラウザで効かない: 効かない時は宣言ごと無効になり今の 96px のまま（今より悪くならない）。Chrome 125 以上で効く。
- 送り枠に `container-type: size` を付けると、中身の大きさで送り枠の大きさが決まらなくなる: 送り枠は FullCalendar が上下左右 0 の絶対配置で大きさを決めている（`height` 100% の時）ので影響しない。クラウドの審査で 6.1.22 の実物の css と生成の道を照らす。
- 1023px 以下: 送り枠の規則は `fillHeight` の時だけ。今の 1023px 以下は時間割の高さが 0 になる不具合（scratchpad 実測 D）があり、それは Android 側の担当が直す。便7 は 1023px 以下の並び方を変えない。

### 3.13 便8: 残りの部品を決められた部品に差し替える（G26〜G30・2026-11-08）

確かめた事実（行番号は origin/main 36ea9b7b2）:
- R8-1: 小窓のボタン 4 つは生の `<button className="modal-icon-btn">`。詳しくの小窓: 直す `frontend/src/pages/schedule/SchedulePageImpl.tsx:308-317`・消す `:318-327`（`modal-icon-btn--danger`）・閉じる `:328-330`。その日の一覧の小窓: 閉じる `:744-746`。絵は `SCHEDULE_POPOVER_ICONS`（`:250-252`・`:735`）で `size={18}`。見た目は `frontend/src/components.css:362-385`（36px＝`--space-9`・丸・地は透明・乗せると `--bg-hover`・消すは乗せると `--danger-bg`）。`.modal-icon-btn` を使うのはこの 4 つだけ（2026-11-08 に `frontend/src` 全体を grep。他は `frontend/src/tokens.css:81` の説明の文だけ）。決められたボタンの部品 `frontend/src/components/Button.tsx` は `variant="ghost"`（地は透明・文字は `--text-primary`・乗せると `--bg-subtle`・`frontend/src/components/Button.css:83-103`）と `iconOnly`（36px＝`--size-icon-btn`・`frontend/src/components/Button.css:149-155`・`frontend/src/tokens.css:167`）を持ち、`aria-label` と `title` はそのまま渡る（`aria-label` は `frontend/src/components/Button.tsx:54`・`:67`、`title` を含む残りは `...rest` で `:55`・`:68`）。同じ画面の上の帯は既に `<Button variant="ghost" size="sm" iconOnly ...>` を使っている（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1388`）。
- R8-2: 知らせの帯の × は生の `<button className="schedule-banner__close">×</button>`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1532-1538`）で、中身は文字の「×」。見た目は `frontend/src/pages/schedule.css:1026-1032`。帯は `?connected=true`／`false` で開いた時に出る（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1012-1020`）。帯は横並び（flex）ではない（`frontend/src/pages/schedule.css:1034-1041`・`frontend/src/components.css:698-706`）。
- R8-3: 種類の札は生の `<span className="schedule-category-chip" style={{ background: cssVar(meta.tintVar), color: cssVar(meta.textVar) }}>`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:298-304`）。色は `frontend/src/features/schedule/calendars.config.ts:23-73` に 7 種類 × 3 つ＝21 個の直書き（`colorVar`・`tintVar`・`textVar`）。`colorVar` はどこからも読まれていない。`tintVar`・`textVar` を読むのは `:301` だけ。`cssVar`（`frontend/src/features/schedule/calendars.config.ts:82-84`）は値をそのまま返すだけで、使うのは `:301` だけ。ダークの時も明るい色のまま出る（直書きのため）。決められた札の部品 `frontend/src/components/Badge.tsx` は 6 色（neutral・info・success・warning・danger・purple）を持ち、色はトークン（soft の 6 色は `frontend/src/components/Badge.css:71-76`・ライトとダークの両方がある）。札の試験 `frontend/src/features/schedule/calendars.config.test.ts` は文言キーだけを見る。
- R8-4: 持ち主の色が無い時の色 `DEFAULT_OWNER_COLOR = "#1a73e8"`（`frontend/src/pages/schedule/schedule-owner.ts:34`）。使う所は `normalizeOwner`（同 `:43`）・`getOwnerMeta`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:218`）・見本帳（`frontend/src/components/CalendarView.stories.tsx:5`・`:118-119`）。持ち主の色の正本はサーバー: 色が無い時は `backend/app/routers/calendar.py:50` の `_DEFAULT_OWNER_COLOR = "#1a73e8"` で必ず埋めて返す（`:243`・`:250`・`:269`・`:368`・`:377`・`:392`）。同じ色のトークン `--calendar-google-blue`（ライト `#1a73e8`・ダーク `#8ab4f8`・`frontend/src/index.css:184`・`:385`）が在る。金型 CalendarView は色を css の変数に入れるだけ（`frontend/src/components/CalendarView.tsx:261-262`）なので `var(...)` の文字でも効く。設定の画面の色の欄 `<input type="color" value={owner.color}>`（`frontend/src/pages/schedule/ScheduleSettingsPage.tsx:145-148`・`:198-201`）は `#` の 6 桁でないと黒になるので、`normalizeOwner` の色に `var(...)` を入れてはいけない。
- R8-5: 消す規則を使う所は他に無い（`.modal-icon-btn` は R8-1・`.schedule-category-chip` と `.schedule-banner__close` は `frontend/src/pages/schedule/SchedulePageImpl.tsx` だけ。2026-11-08 に `frontend/src` 全体を grep）。

作り方（A 組・決められた部品がそのまま使える所）:
1. 小窓のボタン 4 つ（G26）: `<Button variant="ghost" size="md" iconOnly aria-label=... title=... onClick=...>` にする。中身の絵と `size={18}` は今のまま。大きさは今と同じ 36px（`size="md"`）。消すボタンも `ghost`。
2. 帯の ×（G27）: `<Button variant="ghost" size="sm" iconOnly aria-label={t("common.close")} layoutClassName="schedule-banner__close" onClick=...>` にし、中身を `SCHEDULE_POPOVER_ICONS.close`（`size={16}`）にする。`frontend/src/pages/schedule.css` の `.schedule-banner__close` は置き場所の 2 行 `margin-left: var(--space-3); vertical-align: middle;` だけにする（`layoutClassName` は外側の置き場所専用の口・`frontend/src/components/Button.tsx:37-38`）。
3. 種類の札（G28）: `CalendarMeta` に `badgeVariant: BadgeVariant` を足し、`colorVar`・`tintVar`・`textVar` と `cssVar` を消す。札は `<Badge variant={meta.badgeVariant} size="md">{t(meta.labelKey)}</Badge>`。色の対応は会議=info・個人=purple・仕入れ=success・発送=danger・請求=warning・リリース=neutral・祝日=purple（今の色に一番近い色の組。祝日と個人は同じ紫になる）。
4. 持ち主の色が無い時（G29）: `DEFAULT_OWNER_COLOR` を `"var(--calendar-google-blue)"` にする（画面に描く時だけの色）。`normalizeOwner` の `|| DEFAULT_OWNER_COLOR` は消し `owner.color` だけにする（正本はサーバーで、必ず埋めて返す・R8-4）。
5. 消す規則（G30）: `frontend/src/components.css:362-385` の `.modal-icon-btn` の 3 つ（直前の説明の 1 行も）と `frontend/src/pages/schedule.css:381-389` の `.schedule-category-chip`。`frontend/src/tokens.css:81` の説明の文の「（.modal-icon-btn 等）」は消す。

B 組（決められた部品が形に合わない所・今回は変えない・PO に聞く）:
- 左の小さい月の日の升目（`frontend/src/pages/schedule/SchedulePageImpl.tsx:637` の生の `<button>`）: 決められたボタンの部品に「日付の丸」の形が無い。
- その日の一覧の行（`:753`）と一覧の表示の行（`:821`）: 決められた 1 行の部品 `ListRow` は丸い画像つきの 2 段の行で、今の 1 段の行と見た目が変わる。
- 小窓の外枠（`:290`・`:740` の手作りの `schedule-popover`）: 決められた小窓の部品 `Popover` は押したボタンの横に出す形で、押した予定の箱の横に出す口が無い。
- 設定の画面の左の項目（`frontend/src/pages/schedule/ScheduleSettingsPage.tsx:115`・`:123` の生の `<button>`）: 決められた項目の部品 `NavItemList` は画面の移動（リンク）用。
- 設定の画面の色の欄（`frontend/src/pages/schedule/ScheduleSettingsPage.tsx:144`・`:197` の `<input type="color">`）: 色を選ぶ部品が無い。
- どれも、部品を新しく作るか部品を変える必要があり、PO の承認が要る（ADR-144）。

選ばなかった案:
- 消すボタンを `variant="danger"`: 文字が常に赤になる（`frontend/src/components/Button.css:112-115`）。今は灰色で、乗せた時だけ赤い。灰色のまま乗せた時だけ赤くする形は部品に無く、足すには部品を変える（PO の承認が要る）。乗せた時の赤は無くなる。
- 種類ごとに色のトークンを 21 個作る: 同じ役目の色が札の部品に既にある（ADR-067 の重複を作らない）。
- `normalizeOwner` に `var(...)` を入れる: 設定の画面の色の欄が黒になる（R8-4）。

心配と対処:
- 札の色が少し変わる（例: 会議は `#e8f0fe` の地→`--info-bg` `#bee3f8`）: 決められた色に揃えるのが目的。ダークでも暗い地の色になる（今は明るい地のまま）。
- 帯の × が 28px の丸になり、帯が少し高くなる: 押しやすくなる。帯の文字の並びは変えない。
- サーバーが色を空で返すと、設定の画面の色の欄が黒になる: サーバーは必ず埋める（R8-4 の 6 か所）。今の画面の表示でも `getOwnerMeta` が持ち主の無い時に色を補う形は残る。
- 試験の作り物の持ち主は `color: null`（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx:54-55`）なので、直した後は `normalizeOwner` が null をそのまま返す。画面の色は `getOwnerMeta`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:218`）の `??` で補われるので、既存の試験は変わらない。

### 3.14 便9: 月表示・詳しくの小窓と一覧の時刻を Google の形に（G31〜G35・2026-11-09）

PO 2026-11-09「1、2」の 2（設計に無かった見た目の違いを直す設計）。比べ方は 2026-11-08 の本番と Google の並べ比べ（同じ窓 1433×1448・Claude in Chrome・保存や削除はしていない）と、2026-11-09 の Google の月表示の追加の測定。

確かめた事実（行番号は origin/main c8fd2ad77）:
- R9-0（予定の中身が違って見えた件・PO「1」）: 並べ比べたアプリの画面は「テスト株式会社」（shingo@salesanchor.jp）、Google の画面は「HIGH LIFE JPN」のカレンダーで、別の会社どうしだった（本番 DB の読み取り専用の道で `ai_ro` の予定・つながりの設定を読んだ。生の出力は scratchpad `sync/q1.txt`・`q2.txt`）。HIGH LIFE JPN の会社の DB には Google の 4 件が全部ある（ビオネスト様 MTG は最初の取り込みの後に入った＝Google→アプリの取り込みは動いている）。アプリから作った 11/6 の打ち合わせは Google に出ている。Google の番号の無い予定は、11/5 の直しより前に作った 3 件（HIGH LIFE JPN の 11/2・11/3 の打ち合わせ、テスト株式会社のテスト）と、つなぐ前に作ったテスト予定だけ。11/6 に PO が「送り直さない」と決めた分と同じ。設計の変更は要らない。テスト株式会社の Google の画面は、別のログインが要るので目では見ていない。
- R9-1: 月表示の中身は `monthProps`（`frontend/src/components/CalendarView.tsx:219-243`）だけで、日付の数字・曜日の行の中身を渡していない。FullCalendar の既定で数字は右上（`.fc-daygrid-day-top` が `flex-direction: row-reverse`）・ja の言葉で「2日」。予定の画面の見た目（`.comp-calendar--schedule.comp-calendar--days`・`frontend/src/components/CalendarView.css:181-222`）は時間割だけで、月には効かない。今日の升目の地は `--fc-today-bg-color: var(--schedule-slot-hover)`（`frontend/src/components/CalendarView.css:37`）で塗られ、透明にしているのは時間割だけ（`:181-183`）。
- R9-2: FullCalendar は月表示で、時刻のある 1 日だけの予定を「点の形」（`fc-daygrid-dot-event`）で出し、点（`fc-daygrid-event-dot`）は既定の中身の中で描く（`@fullcalendar/daygrid` の `internal.js:157-164`。手元に在るのは 6.1.20 の写しで読んだ。6.1.22 で同じかはクラウドの審査で npm pack と照らす）。金型は中身を `renderContent` で差し替える（`frontend/src/components/CalendarView.tsx:137-167`）ので点が消え、予定の画面は `eventLayout="stacked"`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1574`）で題名と時刻の 2 行になる。さらに全部の予定に枠の線が付く（`frontend/src/components/CalendarView.css:98-102`）。これが「黒い枠の箱・2 行・高さ 44px」の原因。
- R9-3: Google の月表示の実測（2026-11-08・11-09）: 日付は升目の上の真ん中・12px・太さ 500。1 日だけ「11月 1日」。今日は直径 24px の丸（地 rgb(11,87,208)・白い字・12px・500）。曜日は 11px・500・rgb(68,71,70)。時刻のある予定は 1 行「点 8px＋午後8時＋題名」・12px・太さ 400・高さ 22px・左の間 8px・角の丸み 6px。
- R9-4: 金型の月表示を予定の画面の見た目で使うのは予定の画面だけ（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1566-1578`。2026-11-09 に `frontend/src` を grep。他は試験と見本帳）。
- R9-5: 詳しくの小窓の時刻は 24 時間の形 `formatTimeRange`（`frontend/src/pages/schedule/schedule-utils.ts:164-168`）で、日付は別の行（`frontend/src/pages/schedule/SchedulePageImpl.tsx:273-274`・`:339-340`）。一覧の表示の行も同じ 24 時間の形（`:831`）。時間割の箱は「午前7時～8時」の 12 時間の形なので、アプリの中でも形が食い違う。作る小窓と検索の結果の 1 行は `formatDraftDateLine`／`formatSearchResultLine`（`frontend/src/pages/schedule/schedule-utils.ts:102-142`）で、Google と同じ「日付＋12 時間の時刻」の形が既に在る。`formatTimeRange`（schedule-utils）を使うのはこの 2 か所だけ（2026-11-09 に grep）。

作り方（A 組・決められた部品と既存の関数で足りる所）:
1. 月表示の日付（G31）: 金型 CalendarView の `monthProps` に、`appearance="schedule"` の時だけ `dayCellContent` を渡す。引数は `(arg: { date: Date; isToday: boolean })` の 2 つだけ使う（FullCalendar の型名は金型の外に出さない・ADR-1065 の決まり 3）。中身は `<span className={今日 ? 'comp-calendar__monthnum comp-calendar__monthnum--today' : 'comp-calendar__monthnum'}>{1 日なら new Intl.DateTimeFormat(言語, { month: 'short', day: 'numeric' }).format(日) それ以外は 日.getDate()}</span>`（ja は「M月1日」（M は月の数字）・en は「Nov 1」。新しい文言キーは要らない）。css は `CalendarView.css` に `.comp-calendar--schedule.comp-calendar--month` の段を足す:
   - `--fc-today-bg-color: transparent;`
   - `.fc-daygrid-day-top { justify-content: center; }`
   - `.comp-calendar__monthnum`: 横並びの真ん中・`min-width` と `height` は新しいトークン `--schedule-month-daynum-size`（24px・`frontend/src/tokens.css` の予定の段に `--schedule-month-dot-size` の次）・`padding: 0 var(--space-1)`・`border-radius: var(--radius-full)`・`font-size: var(--font-xs)`・`font-weight: var(--font-weight-medium)`・`color: var(--text-primary)`
   - `.comp-calendar__monthnum--today`: `background: var(--schedule-today)`・`color: var(--on-solid)`（時間割の今日の丸 `:218-221` と同じ 2 つ）
2. 曜日の行（G32）: 同じ段に `.fc-col-header-cell` の `font-size: var(--font-2xs)`・`font-weight: var(--font-weight-medium)`・`color: var(--schedule-hour-label)`（時間割の曜日 `:197-201` と同じ 3 つ）。
3. 予定の 1 行（G33）: 金型の `renderContent` で、`mode === 'month'` かつ予定の画面の見た目かつ終日でない予定は、`eventLayout` に関係なく `<span className="fc-daygrid-event-dot" />`（色は予定の種類の `--fc-event-border-color`）＋`<span className="comp-calendar__time">{formatMeridiem(始まり, t)}</span>`＋`<span className="comp-calendar__title">{題名}</span>` の 1 行にする。点の形にするか帯の形にするかは金型で判定しない。FullCalendar が決める（6.1.22 の `internal.js:133-139` `hasListItemDisplay`: 終日でない・週の行の中で 1 列だけ・始まりと終わりがその列に在る。終わりは含まない数え方なので 23時〜翌0時の予定も点の形）。css は同じ段に次の 3 つ:
   - `.fc-daygrid-dot-event.comp-calendar__event { border-width: 0; background: transparent; color: var(--text-primary); }`
   - `.fc-daygrid-block-event .fc-daygrid-event-dot { display: none; }`（帯の形になった日をまたぐ予定から点を隠す）
   - `.comp-calendar__title` の `overflow: hidden; text-overflow: ellipsis`
   終日の予定は今の中身（`renderContent` の今の分かれ道）のまま。日をまたぐ時刻のある予定は帯の枠と地のまま、中の文字だけ 1 行になる。
4. 詳しくの小窓（G34）: `frontend/src/pages/schedule/SchedulePageImpl.tsx:273-274` を `const timeLabel = item ? formatSearchResultLine(item, t, i18n.language) : "";` の 1 つにし、`:340` の `schedule-popover__date` の行と `dateLabel` を消す。`frontend/src/pages/schedule.css:409` の `.schedule-popover__date,` を消す。
5. 一覧の表示（G35）: `:831` を `{item.allDay ? t("schedule.allDay") : formatEventTimeRange(item.start, item.end, t, false)}`にする。読み込みは `frontend/src/pages/schedule/SchedulePageImpl.tsx:56` の `formatTimeRange,`（`./schedule-utils` から）を消し、`import { formatTimeRange as formatEventTimeRange } from "../../components/calendarView.utils";` を足す（`schedule-utils.ts:1` と同じ名前の付け方）。`:274` も作り方 4 で消えるので、ページから schedule-utils の `formatTimeRange` を読む所は 0 になる。これで schedule-utils の `formatTimeRange` を使う所が 0 になるので、関数と、その試験があれば試験も消す（実装の前に grep で 0 を確かめる）。

B 組（金型を変える必要がある・または何を正とするか PO が決める所。今回は変えない）:
- 作る小窓: Google は幅約 600px・角の丸み 28px・題名の欄は下線だけで 22px・行の高さ 40px・下のボタンは「その他のオプション」と青い「保存」（保存が右）。アプリは幅 320px・角の丸み 8px・題名は丸い枠の 13.6px・行の高さ 28px・「保存」「キャンセル」（保存が左）。題名の「下線だけ」の形は欄の部品 `TextFieldControl` に無く、足すには部品を変える（ADR-144・PO の承認が要る）。幅・丸み・行の高さは `--schedule-popover-width`（`frontend/src/pages/schedule.css:7` と `frontend/src/tokens.css:409` の 2 か所に同じ名前で在る＝直す時に 1 か所にする）と欄の大きさの金型（`--field-h-sm` 28px・`--field-h-md` 36px）に関わる。
- 上の帯: Google は高さ 64px・「今日」「週▾」は 78×40px。アプリは高さ 70px・「今日」50×28px（ボタンの部品の `size="sm"`）・表示切替 80×36px。40px のボタンは部品の大きさに無い（`sm` 28・`md` 36・`lg` は `--comp-btn-height-lg`）。合わせるには部品の大きさを足すか変える（PO の承認が要る）。
- 終日の行の左の文字: Google は「GMT+9」、アプリは「終日」。「終日」の方が意味が分かるので変えない案を勧める。PO が Google どおりを望めば文言 1 つの直し。
- 作る時刻の刻み（Google 30 分・アプリ 15 分 `snapDuration: '00:15:00'`）: 並べ比べで押した位置が同じでなかったので、Google が 30 分刻みかはまだ確かめていない。確かめてから決める。
- 範囲の外のまま: 月表示の前後の月の日（§3.10 で範囲の外と記録済み）、曜日を 1 段目の升目の中に入れる形（FullCalendar は曜日を別の行で出す作りで、変えるには表の作りを変える）。

選ばなかった案:
- 月表示の予定を FullCalendar の既定の中身に戻す（`renderContent` を月で渡さない）: 時刻が「8p」の形になり、時間割と同じ「午後8時」の形にならない。点だけは既定の規則を使い、文字は金型で作る。
- 点にするかを金型の中で「終日でなく始まりと終わりが同じ日」と判定する: FullCalendar の規則（終わりは含まない数え方）と食い違い、23時〜翌0時の予定や終わりの無い予定が点の形の枠に 2 行で出る（クラウドの審査 12 回目 1 回目の指摘）。規則を写すと版ごとにずれるので、判定は FullCalendar に任せ css で点を隠す。
- 今日の丸の大きさに既存の `--size-icon-btn-sm`（28px）を使う: 役目が違い、Google の 24px とも合わない。予定の段に 1 つ足す（ADR-067 の「役目ごとに 1 つ」）。
- 詳しくの小窓の時刻だけ 12 時間の形にして日付の行を残す: Google は 1 行で、作る小窓・検索の結果とも形が揃わない。

心配と対処:
- 月の升目の予定が 1 行（約 22px）になり、升目の高さ `--schedule-month-cell-min-h`（7.5rem）は変えないので空きが増える: 「ほか N 件」に回る数（`monthMaxEvents={3}`）は今のまま。増やすかは PO の言葉に無いので触らない。
- 点の形の予定は地の色が無くなり、押せる所が見えにくい: 行全体が押せる（`a` の要素）。乗せた時は既に `--bg-hover`（`frontend/src/components/CalendarView.css:78-82`）。
- `fc-daygrid-event-dot` は FullCalendar の class 名を借りる: 版を上げて名前が変わると点が出なくなる。版は ADR-1065 で 6.1.22 に固定。単体の試験で点の要素が在ることを確かめる。
- ダーク: 使う色は全部トークン（`--schedule-today`・`--on-solid`・`--text-primary`・`--schedule-hour-label`）。

ADR の改訂: ADR-1065 の決まり 7 は「`'schedule'` は時間割のときだけ」と書いてある。便9 は月表示にも広げるので、PO が G31〜G35 を承認したら、便9 の実装の PR で決まり 7 に次の 1 文を足す（承認の前に ADR は変えない）:「月の升目のときは、日付を升目の上の真ん中に・今日を丸で・曜日を時間割と同じ文字で・時刻のある 1 日の予定を点＋時刻＋題名の 1 行で出す（PO 承認 G31〜G35）。」あわせて `node scripts/generate-adr-index.js` で索引を作り直す。

戻し方: 便9 の PR を revert する（frontend と ADR-1065 の 1 文だけ・DB や設定は変えない）。

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

- 2026-11-07 に読んで決めた: 今の一覧の道には題名の絞り込みが無く期間が必須なので、読み取りの道 `GET /calendar/events/search` を 1 本足す。見せてよい予定の決まりは `calendar_service.list_events` の 1 か所のまま使う。作り方は §3.11。

## 4. 便の分け方（作る順）

| 便 | 中身 | 成功条件 | 危険な道 |
|---|---|---|---|
| 便0 | 押した時刻が 7 時になる不具合だけを今の画面で直す（1 行） | G1 | なし |
| 便1 | 金型に口を足す・ADR-1065 改訂・見本帳（Storybook）に例 | （画面は変わらない） | なし |
| 便2 | 予定の画面を金型に載せ替え・目盛り・高さ・箱・今の時刻へ・月の高さと帯・引っぱる／動かす・終日のずれの直し（§3.3 の 4） | G2・G4〜G6・G8〜G10・G13 | なし（保存の道は既存。裏側は `backend/app/services/calendar_service.py` の `_to_google_event_body` の終日の枝と `backend/tests/test_calendar_service.py` だけ。移行・deploy・scripts は無い） |
| 便3 | Google 型の作る小窓・表示切替を 1 つに | G3・G11 | なし |
| 便4 | 祝日（案 C） | G7 | なし（移行なし。依存の追加 1 つ） |
| 便5 | 検索（§3.11） | G12 | なし（移行・deploy・scripts・DB の形は無い。裏側は読み取りの道 1 本と `calendar_service.list_events` の省略できる引数だけ） |
| 便6 | 見た目 5 か所（§3.8）。金型に口 1 つ・css・トークン 2 つ・予定の画面に 1 行 | G15〜G19 | なし（frontend だけ。移行・deploy・scripts・DB は無い） |
| 便7 | 上の帯を 1 段・左上のメニューボタン・3日間・1時間の高さ・今の時刻の丸・一番上の文字（§3.12）。金型 PageLayout に口 1 つ・金型 CalendarView に測り直し 1 つ・css・トークン 3 つ | G20〜G25 | なし（frontend だけ。移行・deploy・scripts・DB は無い） |
| 便8 | 残りの部品を決められた部品に差し替える（§3.13 の A 組）。ボタン 5 つ・札 1 つ・持ち主の色・使わなくなった規則を消す。部品の追加・変更なし | G26〜G30 | なし（frontend だけ。移行・deploy・scripts・DB は無い） |
| 便9 | 月表示の日付・今日の丸・曜日の行・予定の 1 行の形、詳しくの小窓と一覧の時刻の形（§3.14 の A 組）。金型 CalendarView の月の中身 2 つ・css・トークン 1 つ・予定の画面の 2 か所・ADR-1065 の決まり 7 に月の 1 文（§3.14「ADR の改訂」・PO 承認の後） | G31〜G35 | なし（frontend だけ。移行・deploy・scripts・DB は無い） |

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
- 便8 の札の色は札の部品の 6 色だけ。`frontend/src/features/schedule/calendars.config.test.ts` が 7 種類の対応と、設定に `#` の色が無いことを CI で毎回確かめる。
- 便9 の月表示の見た目は `CalendarView.css` の `.comp-calendar--schedule.comp-calendar--month` の 1 か所だけ。数値と色の見張り（同上）が CI で直書きを止める。`frontend/src/components/CalendarView.test.tsx` が 1 日の「M月1日」（M は月の数字）・今日の丸・点の 1 行を毎回確かめる。
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

### 9 回目（便5・G12）: 1 回目 REVISE（2026-11-07・クラウドの Opus・origin/release/schedule-gcal-search-bin5 d64dc4e6f）

- 必須 1 件: カード §2 の例は `if start` が先で、写すと期間を渡す今の呼び出しの SQL の順が変わる（今は `backend/app/services/calendar_service.py:164-167` で `start_datetime < :end` が先）→ `if end` を先に書き、「書き直してよい」を「必ずこの順・入れ替えない」に改めた。
- 推奨 1 件: 検索の欄の Enter が変換の確定でも走る → `event.nativeEvent.isComposing || event.keyCode === 229` で先に返す（今の近道 `frontend/src/pages/schedule/SchedulePageImpl.tsx:1284-1285` と同じ形）をカード §5-3 に足した。
- 推奨 1 件: 試験 F3 の「見出しの日付が変わる」が比べる値を決めていない・`rangeText` は K7 の describe（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx:249`）の中だけ → 期待値を `getWeekDays`・`formatDayLabel`（`frontend/src/pages/schedule/schedule-utils.ts:137`・`:161` で export 済み）で作り、`rangeText` を F の describe にも置くと決めた。画面の部品のファイルに export は足さない。
- ○: 期間が無いときの `WHERE TRUE`・`ESCAPE` の意味と S3 の値・道のぶつかり無し（`/calendar/events/{event_id}` は PATCH と DELETE だけ）・金型 Popover・ListRow・EmptyState・TextFieldControl の口・`isLoading`・訳と日付の関数・カードの目印はすべて実物と一致。

### 9 回目（便5・G12）: 2 回目 APPROVE（2026-11-07 14:03〜14:04 UTC・クラウドの Opus・origin/release/schedule-gcal-search-bin5 631d14b3a・照合は origin/main 67d7bbf87・セッション cse_01HHUUpR6HRDSTAKnSXpcQSn）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ カード §2 の例で作られる WHERE は `ce.start_datetime < :end AND ce.end_datetime > :start` の順で、`backend/app/services/calendar_service.py:164-167` と同じ。
- (2) ○ 変換中の扱いは `frontend/src/pages/schedule/SchedulePageImpl.tsx:1284-1285` と同じ形。`TextFieldControl` は `onKeyDown` を input に渡す（`frontend/src/components/TextField.tsx:37`・`:44`・`:55`）。型は審査役が「未確認」としたため Opus が手元の `@types/react` で確かめた（`KeyboardEvent` は DOM の `KeyboardEvent` を `nativeEvent` に持ち、`keyCode: number` がある）。最後の型の確かめは実装の `tsc` で行う。
- (3) ○ F3 の期待値の式は `formatRangeTitle` の週の文（`frontend/src/pages/schedule/SchedulePageImpl.tsx:138-144`・`:1162`）と一致。
- (4) ○ 新しい食い違いなし。

### 10 回目（便7・G20〜G25）: 1 回目 REVISE（2026-11-08 00:07〜00:12 UTC・クラウドの Opus・origin/release/schedule-gcal-topbar 96bb760aa・セッション cse_01HHUUpR1m4FSUyRkL6r75vw）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ 本体の送り枠だけが liquid（timegrid 6.1.22 `internal.js:193`・終日の段 `:179` には無い）で class は `fc-scroller-liquid-absolute`（core `internal-common.js:6735`・上下左右 0 の絶対配置）。now-indicator-container の既定は `overflow:hidden`（詳しさ 0,2,0）でカードの規則（0,3,0）が勝つ。`updateSize`→`_resize`→`handleSizing`（`:6994`）→ slot の測り直し（timegrid `:435-450`）。
- (2) △ 式・容器の解決は ○。css の 2 検査は node で PASSED。stylelint と tsc は審査役の場所に node_modules が無く未確認（実装の CI で確かめる）。
- (3) ○ `ScheduleView` を使うのは schedule-utils と SchedulePageImpl だけ。`NAV_ICONS.menu`（`frontend/src/constants/icons.tsx:246`）・`ghost`/`md`（`frontend/src/components/buttonAppearance.ts:1-2`）は実在。
- 必須 3 件と直したこと:
  - 説明の文を消すと `frontend/scripts/check-page-layout.js:94` が rc=1 → `SUBTITLE_ALLOWLIST` に `'schedule/SchedulePageImpl'` を足すと決め、カード §1・§6-2 に足した。
  - G21 の幅の差は左の欄 256 と間 20 で 276px → 基準を 276±16 に直した。
  - G20 の帯は計算 70px で 64px を外れる → 金型の余白は全画面に響くので変えず、基準を 72px 以下に直した（説明の文の無い他の画面と同じ高さ）。
- 推奨 3 件と直したこと: 消す行は `:1364`（`:1363` は navKey）に直した。G25 の例を「午後3時」に直した。カード §5 に check-new-tokens の PR 本文の項目を足した。

### 10 回目（便7・G20〜G25）: 2 回目 REVISE（2026-11-08 00:33〜00:34 UTC・クラウドの Opus・origin/release/schedule-gcal-topbar 997451513・セッション cse_01HHUUpT6RA4AvoHyvdMfeTF）

- 結果は返事の本文で全部読んだ（途中で切れていない）。前の回（cse_01HHUUpSTC362LBLQTWR2RCK）は写しを消す操作が見張りに止められ、判定なしで終わった。消さない試し方に変えてやり直した。
- (1) ○ 写しで除外を足して説明の文を消すと rc=0、除外を外すと SchedulePageImpl.tsx の 1 件だけで rc=1。includes で当たるのは SchedulePageImpl.tsx と .test.tsx だけで、.test.tsx に PageLayout は 0 件。G21 は 256（tokens.css:405）＋20＝276。G20 は 10＋40＋20＝70 で 72 以下。
- (2) △ :1364 と午後3時は ○。PR 本文の項目は ×（下の必須 1）。
- (4) ○ 直しは文書 2 つだけ。stylelint と tsc は未確認（実装の CI で確かめる）。
- 必須 1 件と直したこと: カードの PR 本文の 1 行には「デザイントークン変更時」も「check:dark-parity」も無く、`frontend/scripts/check-new-tokens.js:96-97` で rc=1 になる → `.github/PULL_REQUEST_TEMPLATE.md:51-55` の見出しと 4 項目をそのまま残し、4 項目すべてを `- [x]` にすると書き直した。色トークンは足さないと添え、dark-parity は流して確かめてから付ける。

### 10 回目（便7・G20〜G25）: 3 回目 APPROVE（2026-11-08 00:44〜00:45 UTC・クラウドの Opus・origin/release/schedule-gcal-topbar a14caf3c5・セッション cse_01HHUUpRCCs6z3bTsWtKa7gY）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ カードどおりの PR 本文の例（見出し＋4 項目すべて `- [x]`・色の行末に「（色トークンの追加なし）」）で、`frontend/scripts/check-new-tokens.js` の見出しの判定と未チェックの判定を node で再現し、両方 rc=0。直す前のテンプレートのままでは rc=1。添え書きは「色トークンの」で「色トークンは」を含まず、別の行に当たらない。
- (2) ○ tokens.css:403（`--schedule-row-height: 96px`）・:405（256px）・:426（`--schedule-now-dot-size`）はカードと一致。下限・刻み・時間数の既存トークンは 0 件。
- (3) ○ 1・2 回目に ○ だった所は変わっていない。
- 推奨 1 件と直したこと: 見出しの判定の行は `:95-98`（判定式 :95-96・止める if :98）→ カードを `:95-98` に直した。
- 残る未確認: stylelint と tsc（実装の CI で確かめる）。

### 11 回目（便8・G26〜G30）: 1 回目 REVISE（2026-11-08 10:13〜10:15 UTC・クラウドの Opus・origin/release/schedule-mold-bin8 b225e7513・セッション cse_01HHUUpRoDXmriDdcK7fvqzm）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ カードの行番号と「前」のコードは 36ea9b7b2 の実物と一字一句同じ。:938 は `SchedulePage`（:922〜）の中の `banner` の useState。
- (2) ○ Button は variant・size・iconOnly・layoutClassName を持ち、title は `...rest` で渡る。`size="md"` は大きさの class を付けない（`frontend/src/components/buttonAppearance.ts:39`）。Badge は `BadgeVariant` を export（`frontend/src/components/Badge.tsx:16`）。`SCHEDULE_POPOVER_ICONS` は先頭で import 済み（:27）。消す名前を使う所はカードの所だけ。
- (3) ○ G29 は 0＋21＋1＋0＝22 件。カードどおりで 0 件。stories は 0 件のまま。
- (4) ○ apiEvent（test:142）・view（:104）・MemoryRouter（:3）・answers（:31）で (a)〜(e) が書ける。帯は loading の判定より前に描かれる（Impl:1529）。
- (5) × 必須 2 件と直したこと: R8-1 と作り方 2 の `frontend/src/components/Button.tsx:236`・`:262-263`・`:232-233` は実物（74 行）に無い → `aria-label` は `:54`・`:67`、`title` を含む残りは `...rest` で `:55`・`:68`、`layoutClassName` は `:37-38` に直した。R8-3 の `frontend/src/components/Badge.css:324-329` は実物（85 行）に無い → soft の 6 色は `:71-76` に直した。
- 推奨 1 件と直したこと: 試験の作り物の持ち主は `color: null`（test:54-55）で、直した後の `normalizeOwner` は null を返す → 「心配と対処」に、画面の色は `getOwnerMeta:218` の `??` で補われ既存の試験は変わらないと足した。
- 未確認とされた 1 件の確かめ: features 層から components を import してよいか → `frontend/eslint.config.js:120-131` の `no-restricted-imports` は lucide-react だけを止める。前例は `frontend/src/features/tcg-distribution/DistributionPreview.tsx` など 5 件以上（2026-11-08 grep）。

### 11 回目（便8・G26〜G30）: 2 回目 APPROVE（2026-11-08 10:19〜10:20 UTC・クラウドの Opus・origin/release/schedule-mold-bin8 01297f23b・セッション cse_01HHUUpSDWn2RtGhc6fkiQ6x）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ 36ea9b7b2 の実物で `aria-label` は `frontend/src/components/Button.tsx:54`・`:67`、`...rest` は `:55`・`:68`、`layoutClassName` は `:37-38`。soft の 6 色は `frontend/src/components/Badge.css:71-76`。
- (2) ○ 試験の持ち主は test:54-55 で 2 人とも `color: null`。Impl:218 は `owner?.color ?? DEFAULT_OWNER_COLOR`。frontend/src の試験に色の値を見る所は 0 件。`eslint.config.js:120-131` は lucide-react だけを止め、層の止め（no-restricted-paths・boundaries）は 0 件。features から components を import する file は 39 件（DistributionPreview.tsx:13-14 を含む）。
- (3) ○ 直しは design.md だけ（15 行足し・3 行消し）。カードの「前」のコード・G29 の 22 件・試験の書き方は触っていない。
- 指摘なし。

### 12 回目（便9・G31〜G35）: 1 回目 REVISE（2026-11-08 15:22〜15:23 UTC・クラウドの Opus・origin/release/schedule-gcal-visual-diff-design 2290995ae・セッション cse_01HHUUpTkvBHehF64msxPetj）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ R9-1〜R9-5 の行は c8fd2ad77 の実物と合う。npm pack した `@fullcalendar/daygrid@6.1.22` の `internal.js:157-164` にも、点を既定の中身の中で描く作りが在る（6.1.20 の写しと同じ）。
- (2) × 必須 1 件と直したこと: 点の形の条件は 6.1.22 の `internal.js:133-139`（終わりは含まない数え方）で、作り方 3 の「同じ日」と食い違う → 金型では判定せず、終日でない月の予定に点を描き、帯の予定は css `.fc-daygrid-block-event .fc-daygrid-event-dot { display: none; }` で隠す形に直した。G33 の受入れと「選ばなかった案」も直した。
- (3) ○ G31〜G35 は数値・文字・要素の個数で ○× を決められる。
- (4) × 必須 1 件と直したこと: ADR-1065 の決まり 7 は「`'schedule'` は時間割のときだけ」 → §3.14 に「ADR の改訂」（PO 承認の後に便9 の PR で 1 文足す・索引を作り直す）を足し、便9 の行と戻し方にも書いた。
- 推奨 2 件と直したこと: 作り方 1 に `dayCellContent` の引数 `(arg: { date: Date; isToday: boolean })` を書いた。作り方 5 に `SchedulePageImpl.tsx:56` の読み込みの付け替えを書いた。
- schedule-utils の `formatTimeRange` を使うのは 2 か所だけで、専用の試験は無い（審査の grep）。
