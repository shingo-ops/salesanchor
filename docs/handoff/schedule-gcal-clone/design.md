# design: 予定の画面を Google カレンダーと同じ使い心地にする（作り直し）（2026-11-06）

状態: 成功条件 G1〜G14 は **PO 承認済み**（2026-11-06、PO 原文「1.」＝「この14項目で決める」を選択）。設計審査 1 回目・2 回目は REVISE、3 回目は **APPROVE**（§9）。3 回目の推奨 2 件も直した。実装は未着手。
実装の承認: PO はこのセッションの冒頭で「PRマージ、デプロイまで完走させてくれ」、3 択で「3」（違いもまとめて設計し直してから全部いっしょに作る）と指示した。設計審査の APPROVE と便ごとのカードが揃った便から作る。
追加（2026-11-07）: 見た目 5 か所の成功条件 G15〜G19 は **PO 承認済み**（PO 原文「１，」＝「この決め方で設計を進める」を選択）。作り方は §3.8・便6。設計審査は §9 の 4 回目（REVISE）・5 回目（**APPROVE**）。
追加（2026-11-08）: 便8（残りの部品を決められた部品に差し替える・G26〜G30）は PO の選択「1」（2026-11-08）。作り方は §3.13。設計審査は §9 の 11 回目。
追加（2026-11-09）: 便9（月表示・詳しくの小窓と一覧の時刻を Google の形に・G31〜G35）は PO の選択「1、2」（2026-11-08）で設計した。作り方は §3.14。設計審査は §9 の 12 回目（APPROVE）。G31〜G35 は **PO 承認済み**（2026-11-09、PO の選択「1」＝「5か所の直しを承認して、作るところまで進める」）。実装カードは `docs/handoff/schedule-gcal-clone/card-bin9.md`。
追加（2026-11-09）: 便10（日・3日間・週から月へ切り替えると画面全体が消える不具合・G36）は PO の選択「1」（2026-11-09・画面が消える不具合を先に直す）。作り方は §3.15。設計審査は §9 の 13 回目（APPROVE）。実装カードは `docs/handoff/schedule-gcal-clone/card-bin10.md`。金型の設計 `docs/handoff/calendar-view-component/design.md` §4-3 の `views` の行も「月でも渡す」に直した。
追加（2026-11-09）: 便11（日・3日間・週の枠線を Google に揃える・G37〜G41）は PO の選択「1」（2026-11-09・枠線を揃える設計を作り、PO の承認を得てから直す）。作り方は §3.16。設計審査は §9 の 14 回目（APPROVE）。G37〜G41 は **PO 承認済み**（2026-11-09、PO の選択「1」＝「この直し方で作り、本番に出して Google と並べて確かめる」）。実装カードは `docs/handoff/schedule-gcal-clone/card-bin11.md`。
追加（2026-11-09）: 便12（作る小窓を Google の形に・作っている途中の箱を動かせる・G42〜G50）は PO の言葉「つぎは新規の予定を追加するときの表示の仕方と編集途中でもドラッグで動かせる機能を実装してくれ、Googleカレンダーと同じUI/UXで」（2026-11-09）。作り方は §3.17。G42〜G50 と金型 2 つの変更（ADR-144）は **PO 承認済み**（2026-11-10、PO の選択「1」＝「この設計で作り、本番に出してGoogleと並べて確かめる」）。設計審査は §9 の 15 回目（2 回目 APPROVE）。実装カードは `docs/handoff/schedule-gcal-clone/card-bin12.md`。
追加（2026-11-11）: 便13（Google Meet を押す行に・「その他のオプション」で全画面の編集・G51〜G57）は PO の言葉（2026-11-10・§2.6）。作り方は §3.18。設計審査は §9 の 16 回目（3 回目 APPROVE）。G51〜G57 と新しい金型 `FullScreenDialog`（ADR-144）は **PO 承認済み**（2026-11-11、PO の選択「1」＝「この形で作り、本番に出す」）。実装カードは `docs/handoff/schedule-gcal-clone/card-bin13.md`。
追加（2026-11-12）: 便15（予定の繰り返し・G69〜G79）は PO の選択「1」「1、」（2026-11-12・Google の決まった選び方 6 つと 3 択・自由に決める選び方は後で）。作り方は §12。ADR-1075（Proposed）。成功条件 G69〜G79 は PO の選択「1」（2026-11-12）で決まった（§12.14）・設計審査は審査15 で APPROVE・実装カード便15A は審査3 で APPROVE・実装は未着手。
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
| G36 | 日・3日間・週で見ている時に月へ切り替えても、画面が消えない。同じ月を 2 回目に開く時（週→月→週→月・日→月→日→月・3日間→月→3日間→月）も消えず、最後は月の升目が出る。その間に画面の裏の誤り（console の error）が 0 件（今は 2 回目の月で `viewType "calendarDays" is not available` が出て画面全体が消える） | 本番 /schedule で近道のキー w→m→w→m・d→m→d→m・x→m→x→m を各 3 秒あけて押し、console の error の数・`#root` の子の数（1 以上）・最後の表示の種類（`fc-dayGridMonth-view`）を読む（予定は保存しない）。単体の試験で、日・週→月→日・週→月と props を差し替えても月の時に `views.calendarDays` が渡ること | R10-1〜R10-4 |

### 2.4 日・3日間・週の枠線を Google に揃える（G37〜G41・便11・2026-11-09 追加）

PO 2026-11-09 の言葉:「Googleかれんだーはタイムテーブルの予定を入れる宇文だけに枠線が入っていて日付と時間の部分は枠線が入っていないが、SAアプリは枠線が全てに入っている」。PO の選択「1」（枠線を揃える設計を作り、PO の承認を得てから直す）。

| # | 成功条件 | 確かめ方 | 根拠 |
|---|---|---|---|
| G37 | 日・3日間・週の上の行（曜日と日付）に線が 1 本も無い。時間割の外枠（上と左）も無い | 本番 /schedule の週で `.fc-scrollgrid`・`.fc-col-header-cell`・左上の角（`thead .fc-timegrid-axis`）の 4 辺の `border-*-width` が全部 0px。画面写しで日付の行に縦線・横線が無い | R11-1・R11-2 |
| G38 | 左の時刻の列の中に線が無い（時刻の文字を横切る線・列の右の縦線が無い）。毎時の線は、予定を入れる升目の左の端から時刻の列へ 8px だけ出る（Google 実測 9px）。時刻の文字の右の端と、その短い線の左の端の間は 4px 以上あく | 本番の週で `.fc-timegrid-slot-label` の 4 辺が 0px。同じ要素の `::after` が幅 8px・上の線 1px。時刻の文字の要素（`.fc-timegrid-slot-label-cushion`）の右の内側のあき（`padding-right`）が 12px（8px＋4px）で、文字の要素が時刻の列からはみ出ない（右の端が列の右の端以下） | R11-1・R11-3 |
| G39 | 終日の行は、日と日の間の縦線だけ残る。「終日」の文字の升目には線が無い。終日の行と時間割の間は 1px の横線 1 本（今は高さ 3px の灰色の帯） | 本番の週で `.fc-daygrid-body .fc-timegrid-axis` の 4 辺が 0px。`.fc-timegrid-divider` の高さが 1px・下の線 1px・右の線 0px | R11-1・R11-4 |
| G40 | 予定を入れる升目の線（日と日の間の縦線・毎時の横線・升目の左の端の縦線）は今のまま残る。土曜の右の外と、上の行・終日の行の右の端に、線や灰色の帯が出ない。色は今のトークンのまま（ダークでも同じトークン） | 本番の週で `.fc-timegrid-slot-lane` の上の線 1px・`.fc-timegrid-col` の線 1px。`.fc-scrollgrid-section > *` の右と下が 0px。上の行と終日の行の `.fc-scroller` の `scrollbar-color` が透明。画面写しで右の端に灰色の帯が無い | R11-1・R11-5 |
| G41 | 月表示の線は変わらない | 本番の月表示で `.fc-scrollgrid`（上 1px・左 1px）・`.fc-col-header-cell`（4 辺 1px）・`.fc-daygrid-day`（4 辺 1px）・`.fc-scrollgrid-section-body > *`（右 1px・下 1px）・`.fc-scroller` の `scrollbar-color`（auto）が直す前と同じ（直す前の値は R11-6） | R11-6 |

### 2.5 作る小窓を Google の形に・作っている途中の箱を動かせる（G42〜G50・便12・2026-11-09 追加）

PO 2026-11-09 の言葉:「つぎは新規の予定を追加するときの表示の仕方と編集途中でもドラッグで動かせる機能を実装してくれ、Googleカレンダーと同じUI/UXで」。

| # | 成功条件 | 確かめ方 | 根拠 |
|---|---|---|---|
| G42 | 時間割を押して（引っぱって）作る小窓の見た目が Google と同じ並びになる。①幅 600px（窓が狭いときは窓の幅−24px）②角の丸み 28px・枠線なし・地は薄い色（明るい画面 rgb(247,250,252)・ダーク rgb(36,48,70)＝`--bg-subtle`）③題名は下線だけの欄（下線 1px＝`--border`: 明るい rgb(226,232,240)・ダーク rgb(51,65,85)。押すと 2px＝`--accent`: 明るい rgb(30,58,138)・ダーク rgb(91,141,217)）で、文字の大きさ 22px、空のときは「タイトルを追加」 ④行は「絵の列（左から 24px）＋中身（左から 68px）」で、題名も中身の列にそろう ⑤1 行の高さは 40px 以上 ⑥下の右に「その他のオプション」と「保存」が並ぶ（「キャンセル」は無い。閉じるのは右上の ×・Esc・時間割の外を押す） | 本番 /schedule の週で空の升目を押し、小窓の `getBoundingClientRect().width`・`border-radius`・`border-width`・`background-color`、題名の欄の `font-size`・`border-bottom-width`・`border-top-width`（0）・`placeholder`、日時の行の絵と文字の左の位置（小窓の左から 24px・68px・差 ±2px）、各行の高さ、下のボタンの文字と並び順を読む。Google の作る小窓（R12-1）と並べて画面写しを撮る（保存しない） | R12-1・R12-2 |
| G43 | 作る小窓は、時間割の仮の箱の横（右。右に入らないときは左）に 8px あけて出る。縦の位置は「箱の上の端」と「画面の真ん中に置いた位置」の小さい方（画面からはみ出さない）。C キー・左の作成ボタンから作るとき（箱が無い）は今と同じく画面の真ん中。月表示の 1 日押し（箱が無い）は今と同じく押した所の横 | 本番の週で、月曜 10 時・土曜 10 時・水曜 21 時の 3 か所を押し、仮の箱と小窓の四角を読む。箱の右（左）の端と小窓の左（右）の端の差が 8px ±1、上の端が式どおり ±1。C キーで開いて真ん中に出ること、月表示で 1 日を押して押した所の横（12px あけ）に出ることも見る | R12-3 |
| G44 | 作る小窓が開いている間、画面が灰色にならない（幕が無い）。時間割は押せる・引っぱれる。時間割と小窓の外（左の欄・上の帯）を押すと小窓が閉じ、仮の箱も消える。詳しく見る・直す小窓と「他 N 件」の小窓は今のまま（幕あり） | 本番の週で作る小窓を開き、`.schedule-popover-backdrop` が 0 個。詳しく見る小窓では 1 個。左の欄の空いた所を押すと小窓と仮の箱が消える | R12-2・R12-4 |
| G45 | 作る小窓が開いたまま、仮の箱をつかんで別の時刻・別の日へ動かせる。離すと、小窓の日時の 1 行がすぐ新しい日時になり、小窓は動いた箱の横へ付いていく。題名に入れた文字は消えず、箱にも出る | 本番の週で月曜 10 時を押し、題名に「試し」と入れ、箱を同じ月曜の 13 時へ動かし（同じ日の中）、続けて水曜 14 時へ動かす（別の日）。どちらの後も、日時の 1 行が動かした後の日時（例「11月11日(水) 午後2時～午後3時」の形）・小窓の左の端が箱の右の端＋8px（または左）±1・小窓の上の端が式どおり ±1。題名の欄が「試し」・箱の文字が「試し」。保存せず × で閉じる | R12-5 |
| G46 | 作る小窓が開いたまま、仮の箱の下の端を引いて長さを変えられる。離すと日時の 1 行の終わりの時刻が変わる | 本番の週で 10 時の箱の下の端を 11 時半まで引き、日時の 1 行が「午前10時～午前11時30分」の形になる。保存しない | R12-5 |
| G47 | 小窓の日付・時刻の欄を直すと、仮の箱も同じ日時へ動く（箱と小窓の日時は 1 か所から出る） | 本番の週で 10 時の箱を作り、日時の 1 行を押して始まりを 15:00 に直すと、箱が 15 時〜16 時の所へ動く（長さ 1 時間を保つ）。単体の試験で、下書きの日時を変えると仮の箱の start・end が変わる | R12-6 |
| G48 | 箱を動かした後に「保存」を押すと、動かした後の日時で保存される。仮の箱を動かしても、保存を押すまでは裏側へ何も送らない | 単体の試験で、仮の箱を動かした後の保存の送り先・中身（`POST /calendar/events` の start_datetime・end_datetime）と、動かした時点で PATCH・POST が 0 回であることを確かめる（本番では保存しない） | R12-6 |
| G49 | 月表示で 2 日以上を引っぱって作る終日の仮の箱も、つかんで別の日へ動かせ、小窓の日付が変わる。月の 1 日押しは今と同じ（箱を出さず 7 時から 1 時間） | 本番の月で 2 日を引っぱり、箱を 1 週後へ動かして日時の 1 行を読む。単体の試験で終日の箱を動かした後の下書き（startDate・endDate・allDay）を確かめる | R12-5・R12-6 |
| G50 | ダークでも同じ並びで、色はトークンだけ。既にある項目（種類・Google Meet・社員にも見せる・場所・説明）は 1 つも減らない。英語の画面でも文字が t() から出る | 本番でダークに切り替えて小窓の地・題名の下線・押した時の下線の色を読み、G42 ②③ のダークの値（rgb(36,48,70)・rgb(51,65,85)・rgb(91,141,217)）と一致する。作る小窓に 5 つの項目が出る（Meet は Google をつないだ人だけ）。CI の色・数値の見張りと i18n の検査が緑 | R12-2 |

### 2.6 Google Meet を「押す行」に・「その他のオプション」で全画面の編集（G51〜G57・便13・2026-11-11 追加）

PO 2026-11-10 の言葉（要旨）: 予定の箱の UI/UX を Google と同じにしてほしい。違う所は ①Google Meet は切り替えではなく押す行 ②「その他のオプション」は全画面の編集が開き、閉じるとカレンダーに戻る。PO 2026-11-10「1. 見た目だけ Google と同じにして、部屋は保存のときに作る【おすすめ】」（Meet の部屋は今と同じく保存のときに Google が作る・ADR-1060）。

| # | 成功条件 | 確かめ方 | 根拠 |
|---|---|---|---|
| G51 | 作る小窓の Meet は切り替えではなく、絵＋「Google Meet のビデオ会議を追加」の 1 行のボタン。押すと行が「Google Meet のビデオ会議（保存すると参加用のリンクができます）」＋右に × に変わる。× を押すと元の行に戻る。Google をつないでいない人には行が出ない（今と同じ） | 本番の週で空の升目を押し、Meet の行を押す→文が変わり × が出る→× で戻る（保存しない）。名前に「Google Meet」を含む `role="switch"` が小窓に 0 個（試験は `queryByRole("switch", { name: /Google Meet/ })` が null。終日・社員にも見せるの切り替えは残る）。単体の試験で、押した後に保存すると POST の `add_meet` が true、× で戻してから保存すると `add_meet` が無い | R13-1・R13-2 |
| G52 | 自分の Google の予定で Meet が無いものを直す小窓でも、同じ Meet の行が出る（今の切り替えの代わり）。Meet が有る予定は今と同じく「Google Meet で参加」が出る | 単体の試験（今の Meet の試験 8 本を、切り替えからボタンに読み替えて全部通す） | R13-2 |
| G53 | 作る小窓の「その他のオプション」を押すと、窓いっぱいの編集画面が開く。編集画面の一番上は左から ×・題名の欄・「保存」。その下に 日時と終日・種類・Meet の行・社員にも見せる・場所・説明 が全部開いた形で縦に並ぶ（今の作る小窓と同じ順・`frontend/src/pages/schedule/SchedulePageImpl.tsx:445,515,543,556,569,590`）。小窓で入れた題名・日時・種類・Meet の状態がそのまま入っている | 本番の週で月曜 10 時を押し、題名に「試し」と入れ、「その他のオプション」を押す。編集画面の四角が窓と同じ（`getBoundingClientRect` が 0,0,窓の幅,窓の高さ ±1）・題名が「試し」・日時が月曜 10 時〜11 時・6 つの項目が上の順。保存しない | R13-3 |
| G54 | 編集画面の × か Esc で、カレンダーに戻る。戻ると作る小窓が元の位置に開いたままで、入れた題名と仮の箱が残っている。裏側へは何も送らない | 本番で G53 の続きに × を押し、作る小窓の題名が「試し」・仮の箱が月曜 10 時に在る。Esc でも同じ。単体の試験で、開いて × で戻る間の POST・PATCH が 0 回 | R13-3・R13-4 |
| G55 | 編集画面の「保存」は、小窓の「保存」と同じ中身を送る（同じ関数）。うまくいくと編集画面も小窓も閉じて予定が時間割に出る。失敗すると編集画面は開いたままで、失敗の文が編集画面の中に出る | 単体の試験で、編集画面の保存の POST の中身が小窓からの保存と同じ・成功で閉じる・失敗で開いたままエラー文が編集画面の中に在る（本番では保存しない） | R13-4 |
| G56 | 編集画面が開いている間、近道のキー（例: m で月表示）は効かない。Tab で動く先は編集画面の中だけ。閉じると作る小窓の題名の欄に文字を打てる状態（フォーカス）になる。題名の欄で日本語を変換している途中の Esc では閉じない | 単体の試験で、編集画面が開いた状態で body に「m」を送っても表示が変わらない・Tab が編集画面の外へ出ない・× で閉じた後 `document.activeElement` が作る小窓の題名の欄・変換中（`isComposing`）の Esc で dialog が残る。本番で目で見る | R13-4 |
| G57 | 明るい・ダークどちらも色はトークンだけ。英語の画面でも文字が t() から出る。新しい金型（全画面の入れ物）に見本帳の例と単体の試験が在る | 本番でダークに切り替えて編集画面の地が `--bg-surface` のダークの値と一致。CI の「Lint & Dark Mode Check」（色・数値・i18n・見本帳の検査を含む）と「UI governance gate」が緑 | R13-5 |

### 2.7 予定の編集画面を Google の形に（左に寄せる・角の小さい塗りの欄・直すときも全画面）（G58〜G64・便14・2026-11-11 追加）

PO 2026-11-11 の言葉: 「予定の詳細画面だけどGoogleカレンダーをクローンしてほしくて左側に寄せたり入力欄の角の丸みも真似てほしい、今の金型だと実現できないから別途金型を作って」。範囲: 「作るときと直すとき両方」（PO の選択・2026-11-11）。

測る窓はすべて 1279×1448（Google を測った窓と同じ・recon §8.1）。位置の許し幅は ±4px（幅は ±8px）。

| # | 成功条件 | 確かめ方 | 根拠 |
|---|---|---|---|
| G58 | 作る小窓の「その他のオプション」と、詳しくの小窓の「直す」（鉛筆の絵と下の「予定を編集」のボタンの両方）の 2 か所から、同じ編集画面が開く。直すときは今の予定の題名・日時・種類・場所・説明が入っている。編集画面の × か Esc で、作るときは作る小窓に戻り（今と同じ）、直すときはカレンダーに戻る（小窓は閉じる）。どちらも何も送らない | 本番の週で自分の予定を押し、「直す」を押す→編集画面の題名がその予定の題名・× で閉じると小窓が 0 個（保存しない）。単体の試験で、直すから開いて × と Esc で閉じる間の PATCH・POST が 0 回・閉じた後 `.schedule-popover` が 0 個 | R14-1・R14-4 |
| G59 | 直すときの「保存」は今と同じ PATCH を送る（同じ関数）。うまくいくと編集画面が閉じて予定が直る。失敗すると編集画面は開いたままで失敗の文が中に出る。小窓の中で直す形（入力欄に変わる小窓）は無くなる | 単体の試験（今の「直す」の試験 T7・社員にも見せる・Meet の試験を編集画面で通す。PATCH の宛先が数字の番号）。小窓の中に `schedule.editEvent` の見出しの入力欄の形が 0 個 | R14-4 |
| G60 | 中身が左に寄る。× は左上（左端 x32±4・真ん中 x52±4・Google 実測 x32 幅 40）、題名の欄は x80±4 から幅 594±8・24px、保存はその右（左端 x706±8）。日時の段は題名の下（1 段目の上端 y92±8）で x80±4 から、始まりの日・始まりの時刻・「〜」・終わりの時刻・終わりの日の 5 つが同じ 1 段に並ぶ（5 つの上端の差が 4 以内）。白い札は x16±4・幅 636±8・角 28px で、札の頭に「予定の詳細」。札の中の絵の真ん中は x48±4・欄の左端は x80±4・場所の欄の幅 556±8 | 本番の窓 1279×1448 で `getBoundingClientRect` を読み、Google の実測（recon §8.1）と並べた表を残す。目で並べた写しも残す | R14-1・R14-3 |
| G61 | 入力欄・選ぶ欄は Google と同じ形: 高さ 40px・角 4px・枠なし・塗りの地・左右余白 16px・14px 前後の文字（日時 4 つ・種類・場所・説明）。題名の欄は枠なしで下線だけ。欄の上の「開始日時」などの文字は出さず、読み上げの名前（aria-label）で持つ。終日は切り替えではなくチェック欄（金型 Checkbox） | 本番で `getComputedStyle` を読む: 高さ 40・`border-radius` 4px・`border-top-width` 0・`background-color` が新しいトークン `--comp-input-filled-bg` の値・`padding-left` 16px。`role="switch"` で名前が「終日」のものが 0 個・`role="checkbox"` で名前が「終日」のものが 1 個 | R14-2・R14-3 |
| G62 | 並び: 日時の段（始まりの日・始まりの時刻・〜・終わりの時刻・終わりの日。終日なら時刻が消える）→終日→札（予定の詳細）の中に Meet・場所・種類・社員にも見せる・説明。項目は今から 1 つも減らない（Meet はつないだ本人だけ・社員にも見せるは変えてよい人だけ、今と同じ） | 単体の試験で順番を DOM の並びで確かめる。本番で目で見る | R14-1 |
| G63 | 暗い表示でも同じ並びで、色はトークンだけ。スマホの幅（390）でも横にはみ出さない。英語の画面でも文字が t() から出る | 暗い表示の色は G66 で測る。窓 390×844 で `document.documentElement.scrollWidth <= 390`。CI の「Lint & Dark Mode Check」と i18n の検査が緑 | R14-3 |
| G64 | 新しい金型（編集の画面の入れ物 `EditorPage`）に見本帳の例と単体の試験が在り、使わなくなる古い金型 `FullScreenDialog` は消える。塗りの欄・丸い保存は決めた場所の外で使うと CI の試験が止める。本番の画面点検 S13 は変えずに合格のまま | CI の「UI governance gate」「Lint & Dark Mode Check」が緑。`git grep FullScreenDialog -- frontend` が 0 件。新しい守り手の試験が緑。合流の後の本番の画面点検で S13 が合格 | R14-2・R14-5 |
| G65 | 予定の画面すべて（ページ・カレンダーの表・作る小窓・詳しくの小窓・編集画面）の色が、明るい表示で Google の実測（recon §8.6）と同じ。PO 2026-11-11「予定の色だけどGoogleと色を併せて」・範囲「予定の画面すべて」 | 本番の窓 1279×1448・明るい表示で `getComputedStyle` を読み、次の値と一致（rgb の各数の差 2 以内）: `.schedule-page` の地 rgb(248,250,253)・文字 rgb(31,31,31)／ページの題名 `.text-page-title` の文字 rgb(31,31,31)／`.schedule-main__surface` の地 rgb(255,255,255)／`.comp-calendar` の `--fc-border-color` が #dde3ea／日の数字の文字 rgb(31,31,31)／今日の数字の丸 rgb(11,87,208)・文字 rgb(255,255,255)／左の小さい暦の今日 rgb(11,87,208)／今の時刻の丸 rgb(219,55,45)（丸は疑似要素なので `getComputedStyle(el,'::before')` で読む）／作る小窓と詳しくの小窓の地 rgb(240,244,249)／作る小窓の保存 地 rgb(11,87,208)・文字白／編集画面の地 rgb(248,250,253)・札 白・塗りの欄 rgb(233,238,246)・文字 rgb(31,31,31)・保存 地 rgb(11,87,208)・文字白。保存は押さない | R14-6 |
| G66 | 同じ点が暗い表示で Google の暗い実測（recon §8.6 の暗い表示）と同じ | 本番で JS で `html` に `force-dark` を足して（設定は保存しない）G65 と同じ点を読む: ページ rgb(27,27,27)・文字 rgb(227,227,227)／ページの題名の文字 rgb(227,227,227)／表の札 rgb(19,19,20)／線 #333537／日の数字 rgb(227,227,227)／今日の丸 rgb(168,199,250)・文字 rgb(6,46,111)／今の時刻の丸 rgb(245,94,87)／小窓の地 rgb(30,31,32)／保存 地 rgb(168,199,250)・文字 rgb(6,46,111)／編集画面の地 rgb(27,27,27)・札 rgb(19,19,20)・塗りの欄 rgb(40,42,44)・文字 rgb(227,227,227)。表示の選び（日・週・月）の選んだ方の文字は測らない（Google は白、この設計は rgb(194,231,255)。受け入れた違い・ADR-1074） | R14-6 |
| G67 | 予定の画面の外は色が変わらない。予定の箱は持ち主の色のまま・文字は白のまま | 本番で 予定の設定の画面・取引先の一覧の画面の主ボタンの地が rgb(30,58,138)（今と同じ）。予定の箱の地がサーバーの持ち主の色（例 #1a73e8）・文字 rgb(255,255,255)。新しい守り手の試験 `frontend/src/components/gcalColorsUsage.test.ts` が緑 | R14-6・R14-7 |

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

PO 2026-11-08「1、2」の 2（設計に無かった見た目の違いを直す設計）。比べ方は 2026-11-08 の本番と Google の並べ比べ（同じ窓 1433×1448・Claude in Chrome・保存や削除はしていない）と、2026-11-09 の Google の月表示の追加の測定。

確かめた事実（行番号は origin/main c8fd2ad77）:
- R9-0（予定の中身が違って見えた件・PO「1」）: 並べ比べたアプリの画面は「テスト株式会社」（PO の試験用のログイン）、Google の画面は「HIGH LIFE JPN」のカレンダーで、別の会社どうしだった（本番 DB の読み取り専用の道で `ai_ro` の予定・つながりの設定を読んだ。生の出力は scratchpad `sync/q1.txt`・`q2.txt`）。HIGH LIFE JPN の会社の DB には Google の 4 件が全部ある（後から入った打ち合わせの予定 1 件も入っている＝Google→アプリの取り込みは動いている）。アプリから作った 11/6 の打ち合わせは Google に出ている。Google の番号の無い予定は、11/5 の直しより前に作った 3 件（HIGH LIFE JPN の 11/2・11/3 の打ち合わせ、テスト株式会社のテスト）と、つなぐ前に作ったテスト予定だけ。11/6 に PO が「送り直さない」と決めた分と同じ。設計の変更は要らない。テスト株式会社の Google の画面は、別のログインが要るので目では見ていない。
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
5. 一覧の表示（G35）: `:831` を `{item.allDay ? t("schedule.allDay") : formatEventTimeRange(item.start, item.end, t, false)}`にする。読み込みは `frontend/src/pages/schedule/SchedulePageImpl.tsx:56` の `formatTimeRange,`（`./schedule-utils` から）を消し、`import { formatTimeRange as formatEventTimeRange } from "../../components/calendarView.utils";` を足す（`frontend/src/pages/schedule/schedule-utils.ts:1` と同じ名前の付け方）。`:274` も作り方 4 で消えるので、ページから schedule-utils の `formatTimeRange` を読む所は 0 になる。これで schedule-utils の `formatTimeRange` を使う所が 0 になるので、関数と、その試験があれば試験も消す（実装の前に grep で 0 を確かめる）。

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

### 3.15 便10: 日・3日間・週から月へ切り替えると画面全体が消える不具合（G36・2026-11-09）

PO 2026-11-09「1」（画面が消える不具合を先に直す・設計と審査をしてから直す）。2026-11-09 に本番 /schedule（PO のログインの画面・Claude in Chrome）で、週→月→週→月と切り替えると 2 回目の月で画面全体が白くなるのを観測した。予定の保存・削除はしていない。

確かめた事実（行番号は origin/main a34b0af43。FullCalendar の中身は npm pack した 6.1.22 の実物）:
- R10-1（誤りの全件）: console の error は 10 件で、10 件とも同じ文 `Error: viewType "calendarDays" is not available. Please make sure you've loaded all neccessary plugins`（ERROR 5・EXCEPTION 5）。10 件とも呼び出し元は `componentDidUpdate → resetOptions → … → _computeCurrentViewData`。他の種類の error は 0 件。
- R10-2（起きた順・本番で画面の変化と通信を記録）: 1 回目の月では予定を取りに行き、その間に金型が一度外れて月の形で作り直された（作り直し 2 個目）。週へ戻った時は作り直されず同じ金型のまま。2 回目の月で m を押して約 23ms 後、取り直しの前に上の error が出て、4ms 後に画面の根（`#root`）の中身が 0 個になった。
- R10-3（原因）: 金型 `frontend/src/components/CalendarView.tsx:105-108` で作る `views`（`calendarDays` という表示の種類の定義）を、時間割の設定 `daysProps`（`:193-194`）の中だけで渡している。月の設定 `monthProps`（`:230`）には無く、`:285` で `{...(isMonth ? monthProps : daysProps)}` と入れ替える。React の包み（`@fullcalendar/react` 6.1.22 `dist/index.js:76`）は props が変わるたびに `resetOptions(props 全部)` を呼び、`@fullcalendar/core` 6.1.22 `index.js:1364-1367` は設定を丸ごと置き換える。表示の種類の一覧は `index.js:364-369`（`parseViewConfigs(optionOverrides.views)`）で作り直されるので `calendarDays` が消える。この時まだ表示は `calendarDays` のままで（表示を月へ切り替える `changeView` は `:111-120` の useEffect で、包みの更新より後に走る）、`index.js:1561-1563` が上の error を投げる。
- R10-4（その月の写しが無い時は消えず、写しが在る時に消える理由。本番で観測したのは「1 回目は消えず 2 回目に消える」）: 予定の画面は、予定の写しがまだ無い間は金型を外して読み込み中を出す（`frontend/src/pages/schedule/SchedulePageImpl.tsx:990` の `isPending`・`:1547`）。写しの名前は表示の期間を含み（`:961-964`）、写しは 30 分残る（`frontend/src/lib/query/apiQuery.ts:5,21,28` の `GC_TIME_MS`・`staleTime` 既定 0）。TanStack Query 5.104.4 の `isPending` は「写しがまだ無い」の意味で、写しがあれば裏で取り直しても読み込み中にならない（Context7 /tanstack/query）。写しが無い月は金型が作り直されて助かる。写しが在る月は同じ金型のまま `views` が外れて落ちる。このため 30 分以内に同じ月を一度開いていれば、1 回目の切り替えでも落ちる（筋道からの推論・本番では未確認・審査 13 回目の推奨 1）。直しはどちらの場合も同じ。
- R10-5（画面全体が消える理由）: `frontend/src` に誤りを受け止める部品（`ErrorBoundary`・`componentDidCatch`・`errorElement`）が 0 件（試験を除く・`git grep` で確かめた）。1 か所の誤りでアプリ全体が消える。これは予定の画面に限らない話なので便10 では直さず、PO へ別に伝える（変更は一度に 1 つ）。
- 日・3日間は週と同じ `calendarDays` を使う（`:105-108`・`dayCount` だけ違う）ので同じ道を通る。本番で観測したのは週だけ。
- 金型を作った時点から同じ不具合が在ったかは、まだ確かめていない。

作り方:
1. `frontend/src/components/CalendarView.tsx` の `<FullCalendar>`（`:277-285`）に `views={views}` を足し、`daysProps` の中の `views,`（`:194`）を消す。月でも時間割でも `views` が常に渡る。`views` は `calendarDays` の定義を 1 つ足すだけで、月の升目（`dayGridMonth`）の描き方は変えない。
2. `frontend/src/components/CalendarView.test.tsx` に試験を足す（今の差し替えの FullCalendar の写し `captured.props` を使う）:
   - 週（`mode="days"`・`dayCount=7`）→月→週→月と rerender し、月の時の `views.calendarDays` が `{ type: 'timeGrid', duration: { days: 7 } }` であること。日（1）・3日間（3）でも同じ。
   - 部品の中身の見張り（今の T5 と同じ読み方）: `@fullcalendar/core` の `index.js` に `props.optionOverrides = optionOverrides` と `parseViewConfigs(optionOverrides.views)` の 2 つの文が在ること。部品の版が変わって置き換えの仕方が変わったら、この試験が落ちて読み直しを促す。
3. ADR・トークン・文言・DB は変えない。

選ばなかった案:
- 表示を切り替える時に金型を作り直す（`key={mode}`）: 作り直すたびに描き直しで画面がちらつき、スクロールの位置なども失う。今の「作り直さず合わせる」作り（`:110`）と食い違う。
- 誤りを受け止める部品を足すだけ: 画面全体は消えなくなるが、月へ切り替えられない不具合は残る。別の話として PO に伝える。
- `changeView` を props の差し替えより先に呼ぶ: 包みの更新（子の componentDidUpdate）は親の useEffect より先に走るので、順番を入れ替えるには作りを大きく変える。`views` を常に渡せば順番に関係なく起きない。
- 予定の画面の読み込み中を毎回出して作り直させる: 写しの利点を捨て、原因（金型）を直さない。金型を使う他の画面でも同じ不具合が残る。

心配と対処:
- 月の時も `views` を渡すことで月の見た目が変わる: `views` は `calendarDays` の定義だけで、月の設定（`monthProps`）には触らない。受入れで月の表示を画面写しで便9 の後と比べる。
- 部品の版を上げた時に置き換えの仕方が変わる: 作り方 2 の見張りの試験で気づく。版は ADR-1065 で 6.1.22 に固定。

戻し方: 便10 の PR を revert する（frontend の 2 ファイルだけ・DB や設定は変えない）。

### 3.16 便11: 日・3日間・週の枠線を Google に揃える（G37〜G41・2026-11-09）

PO 2026-11-09「1」（枠線を揃える設計を作り、PO の承認を得てから直す）。2026-11-09 に本番 /schedule の週と Google カレンダーの週（どちらも PO のログインの画面・Claude in Chrome・窓の幅 1378px）を並べて測った。予定の保存・削除はしていない。下の「試した形」は Opus の画面の中だけに一時的な見た目の規則を足して測り、測った後に外した（本番の配布物は変えていない）。

確かめた事実（行番号は origin/main 1ca6dbf38。FullCalendar の中身は npm pack した 6.1.22 の実物）:
- R11-1（Google の週の線・DOM の実測）: 線は 3 種類だけ。①毎時の横線 24 本は、時間割の箱（幅 972px）の中の行ごとの `::after`（幅 972px・下の線 1px solid rgb(221,227,234)）。左の端は x=318 で、日の列の始まり（x=327）より 9px 時刻の列に出る。②日の列 7 本（幅 138px）の右の線 1px rgb(221,227,234)。土曜だけ右の線の色が白（rgb(255,255,255)）で見えない。③升目の左の端は、幅 9px の要素の右の線 1px。曜日と日付の行（`role="columnheader"`）は 4 辺とも線が無い。時刻の文字の要素は線を持たない。終日の行は日の間の縦線だけで、時間割との間は 1 本の線（巻き上げた時に影が付く）。
- R11-2（SA の今・本番の週で読んだ値）: 外枠 `.fc-scrollgrid` は上 1px・左 1px。曜日と日付の升目 `.fc-col-header-cell` と左上の角は 4 辺 1px。色はすべて `--fc-border-color`（`frontend/src/components/CalendarView.css:16` で `--schedule-gridline`・本番の明るい画面で rgb(218,220,224)）。線の元は FullCalendar の `.fc-theme-standard td,.fc-theme-standard th{border:1px solid var(--fc-border-color)}` と `.fc-theme-standard .fc-scrollgrid{border:1px solid …}`（core 6.1.22 `internal-common.js`）。
- R11-3（時刻の列）: `.fc-timegrid-slot-label` は上・右・左が 1px なので、毎時の線が時刻の文字を横切り、列の右にも縦線が出る。時刻の文字の内側のあき（`.fc-timegrid-slot-label-cushion`）は FullCalendar の `padding:0 4px`（timegrid 6.1.22）。時刻の列の幅は FullCalendar が文字の幅を測って決める（試した形で、あきを 8px 足すと列が 55px→63px に広がった）。
- R11-4（終日の行と時間割の間）: `.fc-timegrid-divider` は FullCalendar の `padding:0 0 2px` と下の線 1px で高さ 3px の帯（右の線も 1px）。「終日」の升目（`.fc-daygrid-body .fc-timegrid-axis`）は 4 辺 1px。
- R11-5（右の端）: 区切りの升目 `.fc-scrollgrid-section > *` は右 1px（上の行・終日の行・時間割）と下 1px（終日の行）。上の行と終日の行の巻き上げの箱 `.fc-scroller` は、時間割の巻き上げの帯と列をそろえるため FullCalendar が `overflow-y: scroll` にしており、PO の Mac では幅 15px の空の帯（灰色）が右の端に出て、線に見える。
- R11-6（月表示・直す前の値）: `.fc-scrollgrid` 上 1px・左 1px、`.fc-scrollgrid-section-header > *` 右 1px、`.fc-scrollgrid-section-body > *` 右 1px・下 1px、`.fc-col-header-cell` と `.fc-daygrid-day` は 4 辺 1px、`.fc-scroller` の `scrollbar-color` は auto（2 個）。
- R11-7（試した形・Opus の画面の中だけ）: 作り方の規則を一時的に足すと、上の行と時刻の列の線が消え、毎時の線の 8px の短い線・終日の行の縦線・1px の区切り・日の間の線が残った（G37〜G40 の値をすべて満たした）。画面の写しで Google と同じ並びになったことを目で確かめた。土曜の右の外に線が残ったのは、時間割の巻き上げの帯（本物の巻き上げ）の左の端だけ。
- 使うトークンは在る: `--schedule-gridline`（`frontend/src/tokens.css:400`・ダーク `:669`）、`--schedule-gridline-w: 1px`（`:423`）、`--space-1: 4px`（`:74`）、`--space-2: 8px`（`:75`）。
- 金型の中で日・3日間・週だけに効かせる場所は `.comp-calendar--schedule.comp-calendar--days`（`frontend/src/components/CalendarView.css:180-288`）。月は `.comp-calendar--schedule.comp-calendar--month`（`:290-`）で別。

作り方（`frontend/src/components/CalendarView.css` の `.comp-calendar--schedule.comp-calendar--days` の段の終わり、`:288` の後に足す。値は var() だけ）:
1. トークンを 1 つ足す（`frontend/src/tokens.css` の `--schedule-gridline-w` の次の行）: `--schedule-hour-tick-w: var(--space-2); /* 毎時の線が時刻の列へ出る長さ（Google 実測 9px） */`。
2. 次の規則を足す:
```css
/* ---- 便11（design §3.16）: 線は予定を入れる升目だけ（G37〜G40） ---- */
.comp-calendar--schedule.comp-calendar--days .fc-scrollgrid {
  border-top-width: 0;
  border-left-width: 0;
}

.comp-calendar--schedule.comp-calendar--days .fc-scrollgrid-section > * {
  border-right-width: 0;
  border-bottom-width: 0;
}

.comp-calendar--schedule.comp-calendar--days .fc-col-header-cell,
.comp-calendar--schedule.comp-calendar--days .fc-timegrid-axis,
.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label {
  border-width: 0;
}

.comp-calendar--schedule.comp-calendar--days .fc-scrollgrid-section > .fc-timegrid-divider {
  padding: 0;
  border-bottom-width: var(--schedule-gridline-w);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label {
  position: relative;
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: var(--schedule-hour-tick-w);
  border-top: var(--schedule-gridline-w) solid var(--schedule-gridline);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label-cushion {
  padding-right: calc(var(--schedule-hour-tick-w) + var(--space-1));
}

/* 上の行と終日の行の空の巻き上げの帯を見せない（幅は残して列をそろえる） */
.comp-calendar--schedule.comp-calendar--days .fc-scrollgrid-section:not(.fc-scrollgrid-section-liquid) .fc-scroller {
  scrollbar-color: transparent transparent;
}
```
3. 単体の試験は足さない（jsdom は見た目の規則を計算しないため）。代わりに受入れで本番の値を読む（G37〜G41 の確かめ方）。見本帳（Storybook）の時間割の例はそのまま使える。
4. ADR・文言・DB・金型の口（props）は変えない。ADR-1065 の決まり 7（予定の画面の見た目は金型の css だけ）の範囲の中。

選ばなかった案:
- `--fc-border-color` を透明にして、要る線だけ描き直す: 日の間の線・毎時の線・予定の枠など、残したい線まで全部描き直すことになり、変える行が増える。
- Google の巻き上げた時の影を区切りの線にまねる: 巻き上げた時だけ出る作りで、まだ測っていない。今回は 1px の線 1 本にする。
- 土曜の右の外の線（本物の巻き上げの帯の端）を消す: 巻き上げの帯を細くするなどは、使う人の Mac の設定（巻き上げの帯をいつも出すか）で見え方が変わり、帯をつかめなくなるおそれがある。今回は触らない。
- 線の色を Google の色（rgb(221,227,234)）に変える: PO の指摘は「線がどこにあるか」で、色ではない。変更は一度に 1 つ。
- 時刻の列へ出る短い線を付けない: Google には在り、毎時の線がどの時刻かを目で追いやすい。付けるのは疑似の要素 1 つとトークン 1 つで済む。

心配と対処:
- 時刻の列が 8px 広がり、日の列が少し狭くなる（週・幅 1378px で 1 列およそ 1px）: 受入れで週・3日間・日の画面写しを撮り、予定の文字が切れないかを見る。
- 一番上（0 時）の行にも短い線が出る: 0 時の文字は出さない（G18）が、線は区切りの線と重なる位置で、巻き上げると隠れる。Google も 0 時に線がある（R11-1 ①の 1 本目）。
- `scrollbar-color` を使えない古い道具: 透明にならず今の灰色の帯が残るだけで、列はずれない（幅は変えない）。
- 月の表示が変わる: 規則はすべて `.comp-calendar--days` の下。G41 で直す前の値（R11-6）と比べる。
- ダーク: 色は `--schedule-gridline` だけ（ダークは `frontend/src/tokens.css:669`）。`transparent` は今の css でも使っている（`:182`）。
- 時刻の列の短い線は、1 時間に 1 行という今の設定（`frontend/src/components/CalendarView.tsx:194` の `slotDuration: '01:00:00'`）が前提。30 分ごとの行にすると、時刻の文字が無い行にも短い線が出る。行の刻みを変える時は、この規則を見直す（審査 14 回目の推奨）。

戻し方: 便11 の PR を revert する（frontend の css 2 ファイルだけ・DB や設定は変えない）。

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

### 3.17 便12: 作る小窓を Google の形に・作っている途中の箱を動かせる（G42〜G50・2026-11-09）

2026-11-09 に Google カレンダーの週（PO のログインの画面・Claude in Chrome・窓 1378×1392）で、作る小窓を開いて測った。予定は保存していない（測った後に Google カレンダーの読み取りで 11/11〜11/14 に予定が 0 件と確かめた）。アプリの行番号は origin/main c6ce79fb6。

確かめた事実:
- R12-1（Google の作る小窓・実測）: 幅 598px・角の丸み 28px・地 rgb(240,244,249)・影 3 層・枠線なし。右上に 28×28 の ×、左上に小窓を動かすつまみ（≡）。題名は 22px・枠なしで下線だけ（押すと青い下線）・空のとき「タイトルを追加」・左から 68px。行は絵が左から 24px・文字が 68px。行の高さは 40px（日時とカレンダーの行は 52px・下に 12px の灰色の 2 行目）。日時の文は「11月 11日 (水曜日) 午後1:00 – 午後2:15」。下の右に文字のボタン「その他のオプション」150×40 と、青い「保存」76×40（丸み 20px）。キャンセルは無い。種類のタブ（予定・タスク・予約枠）がある。
- R12-2（アプリの今）: 作る小窓は幅 320px（`--schedule-popover-width: 20rem`。同じ値が `frontend/src/tokens.css:409-410` と `frontend/src/pages/schedule.css:7-8` の 2 か所にある）・丸み 8px・枠 1px・地 `--bg-surface`（`frontend/src/pages/schedule.css:342-356`）。題名は枠つきの欄（`TextFieldControl variant="schedule"`・`frontend/src/pages/schedule/SchedulePageImpl.tsx:367-375`・見た目は `frontend/src/components/FormField.css:381-390`）で、空のとき「タイトル」。日時・場所・説明は金型 Button（ghost・sm・高さ 28px）の 1 行（`:440-450`・`:510-528`）。種類は見出しつきの選ぶ欄（`:452-470`）、Meet と社員にも見せるは見出し＋切り替え（`:476-497`）。下は左から「保存」「キャンセル」（`:538-547`）。小窓の後ろに画面全体の幕（`:289`・`frontend/src/pages/schedule.css:335-340`）があり、時間割を押せない。
- R12-3（置き場所）: Google は箱の横に 8〜9px あけて出す。右に入らないときは左。縦は「箱の上の端」と「画面の真ん中に置いた位置」の小さい方（5 か所で測って全部この式に合った）。アプリは押した点（`pointRect`・`frontend/src/components/CalendarView.tsx:303`）の右に 12px あけ、上の端を押した点にそろえる（`frontend/src/pages/schedule/schedule-utils.ts:221-240`）。
- R12-4（Google の外を押す）: 時間割の外を押すと小窓が閉じる。開いたまま別の空の升目を押したときの動きは測っていない（未確認）。アプリは同じ形にする（下の作り方 3）。
- R12-5（Google の動かす）: 小窓が開いたまま、仮の箱（rgb(3,155,229)・丸み 6px）をつかんで別の日・時刻へ動かせ、下の端を引いて長さを変えられる。離すと小窓の日時がすぐ変わり、小窓が箱の横へ付いていく。入れた題名は消えず、箱に出る。刻みは 15 分（アプリも 15 分・`frontend/src/components/CalendarView.tsx` の `snapDuration`）。
- R12-6（アプリの仮の箱）: 仮の箱は `pendingRange`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:952`）から作り、`editable: false`（`:1260-1272`）。小窓の日時（`draft`）とは別に持つので、小窓で日時を直しても箱は動かない。動かした予定は `patchMoved`（`:1287-1312`）が PATCH で保存する。
- R12-7（FullCalendar 6.1.22・Context7 `/llmstxt/legacy_fullcalendar_io_v6_llms_txt`）: `eventDrop`・`eventResize` の引数に `el`（つかんだ要素）・`event`（動かした後）・`revert` がある。描き直した後の要素は `eventDidMount` で受ける。

作り方:
1. 仮の箱の日時を下書き 1 か所から出す（G47・SSOT）。
   - `pendingRange` をやめ、`pendingVisible`（真偽）だけ持つ。時間割を押して作ったときだけ真（今と同じ条件）。作る小窓以外になったら偽（今の `:1221-1224` と同じ道）。
   - 箱の start・end・allDay は `draft` から出す（終日は `endDate` の次の日 0 時を end にする。日時が読めない・end が start 以前のときは箱を出さない）。この変換は `frontend/src/pages/schedule/schedule-utils.ts` に純粋な関数 `draftToRange(draft)` として置き、`saveEvent`（`:1090-1095`）の日時の作り方と同じ `combineDateTime` を使う。
   - 箱は `editable: true` にする。箱の文字は下書きの題名 `draft.title.trim() || t("schedule.noTitle")`（今の `:1262` の固定の「(タイトルなし)」をやめる・G45「箱にも出る」）。
   - `pendingRange` を使う所は全部置き換える（2026-11-09 に `grep -n setPendingRange` で 5 か所）: 消す 3 か所 `:1223`（作る小窓以外になった）・`:1249`（月の 1 日押しの道）・`:1590`（「他 N 件」）は `pendingVisible` を偽に、作る `:1244`（openCreateRange）は下書きを入れて真に、宣言 `:952` は `pendingVisible` に替える。
   - `calendarEvents`（`:1258`）は `useMemo` で包み、依存は中で使う値すべて（見えている予定・`draft` の日時・題名・終日・`pendingVisible`・祝日 `holidaysQ.data`（`:1284`）・`ownerByUserId`・`currentOwnerUserId`（`:1268`・`:1280`）・`t`）にする。毎回新しい配列を作って金型の `fcEvents` を作り直さないためで、依存を削って祝日や色が古いまま残る形にはしない（`frontend/eslint.config.js:35` の `react-hooks/exhaustive-deps` は警告だけで止めないため、カードに全部書く）。
   - 作る小窓で始まりの日付・時刻だけを直したときは、長さを保って終わりも同じだけずらす（Google と同じ。直す小窓は今のまま）。そうしないと終わり≦始まりになって箱が消え、G47 を満たせない。この計算は純粋な関数 `shiftDraftStart(draft, nextStartDate, nextStartTime)`（`frontend/src/pages/schedule/schedule-utils.ts`）に置き、作る小窓の始まりの日付・時刻の欄（`:396-414`）の `onChange` だけがこれを使う。
2. 箱を動かした・長さを変えたら、下書きを直す（G45・G46・G48・G49）。
   - `onEventMove`・`onEventResize` で id が `"pending"` のときは `patchMoved` を呼ばず、新しい関数 `moveDraft(start, end, allDay)` で `draft` の日付・時刻・終日を直す。裏側へは何も送らない。
   - 終日へ動かしたとき（end が無い）は 1 日、時刻つきへ動かしたとき（end が無い）は 1 時間（FullCalendar の既定と同じ）。
   - 日時→下書きの変換は純粋な関数 `rangeToDraftDates(start, end, allDay)`（`frontend/src/pages/schedule/schedule-utils.ts`）1 つにする。終日は `endDate = addDays(end ?? start＋1 日, −1)`・時刻は 00:00／23:59（今の `openCreateRange` と同じ）。時刻つきは end が無ければ start＋1 時間。`openCreateRange`（`:1227-1245` の `lastDay` の計算）と `moveDraft` の両方がこれを使い、`draftToRange` と往復して同じ値に戻る。
   - 長さを変えたとき（`onEventResize` は終日かどうかを渡さない・`frontend/src/components/CalendarView.tsx:313`）は、id が `"pending"` なら終日かどうかを `draft.allDay` から取る（今の `itemById(id)?.allDay` は仮の箱では偽になり、終日の箱が時刻つきに化けるため）。
3. 作る小窓だけ幕を外す（G44）。
   - `SchedulePopover` の幕（`:289`）を `mode !== "create"` のときだけ出す。「他 N 件」の小窓（`:739`）は変えない。
   - 作る小窓のときは、document の `pointerdown` を capture で見て、`event.composedPath()` に小窓の要素も時間割の箱も入っていないときに閉じる（今の幕を押したときと同じ `onClose`）。capture にするのは、押した先の部品が止めても届くようにするため。日付の見出し（日の数字）を押したときは、今と同じく日表示へ移り（`:1581-1584`）、作る小窓は閉じる（`popover` が null になり、`:1221-1224` で仮の箱も消える）。時間割の中を押したときは FullCalendar に任せる（空の升目は今と同じく新しい箱で作り直す・別の予定は詳しく見る小窓に替わる・仮の箱はつかんで動かせる）。時間割の中かどうかは、予定の画面の時間割の箱（`.schedule-calendar`・`:1563`）に `ref` を付けて `contains` で見る（FullCalendar の名前を画面に出さない）。
   - 押している間の幕の色の token（`--schedule-overlay-scrim`）は残る道（詳しく見る・他 N 件）で使い続ける。
4. 小窓を箱の横に置く（G43）。
   - 金型 `CalendarView` に口を 1 つ足す: `onEventRect?: (id: string, rect: CalendarViewRect | null) => void` と、その対象 `trackEventId?: string`。金型は `eventDidMount` で対象の要素を覚え、`eventWillUnmount` では覚えている要素と同じときだけ忘れる（別の日へ動かすと新しい要素の mount の後に古い要素の unmount が来ることがあるため）。FullCalendar の型は金型の外に出さない（ADR-1065 What 1）。
   - 四角を測る時（FullCalendar 6.1.22 は同じ日の中で動かす・長さを変えるとき要素を作り直さず、外側の `.fc-timegrid-event-harness` の style だけを変える。別の日へ動かすと作り直す。初めの mount の時は `visibility: hidden` のことがある）: ①`eventDidMount` の後の `requestAnimationFrame` ②覚えた要素の一番近い `.fc-timegrid-event-harness, .fc-daygrid-event-harness`（無ければ要素自身）の `style` 属性の変化を `MutationObserver` で見る（月表示と週の終日の段は daygrid の harness で、key が `instanceId:firstCol`（daygrid `internal.js:261,606`）のため、始まりの列が変わらない長さ変えでは作り直されず left・right の style だけが変わる） ③`eventDrop`・`eventResize` の後の `requestAnimationFrame` ④時間割の巻き上げ（`wrapperRef` の中の scroll を capture で受ける）⑤今ある `ResizeObserver`（`:123-131`）の中。どれも `rectOf` で返す。
   - 見えない（`visibility: hidden`・幅 0）ときは `null` を返す。つかんでいる間・引いている間（`eventDragStart`〜`eventDragStop`・`eventResizeStart`〜`eventResizeStop`）は返さず、離した後に 1 回返す（小窓が指の下で揺れない）。
   - 予定の画面は `trackEventId="pending"` を渡し、返ってきた四角を作る小窓の `anchor` にする（押した点の四角は使わない）。
   - 置き場所の式は新しい純粋な関数 `fitCreatePopover(anchor, size, viewport, margin, gap)`（`frontend/src/pages/schedule/schedule-utils.ts`）: 横は箱の右＋gap、入らなければ箱の左−小窓の幅−gap。縦は `min(anchor.top, (viewport.height − size.height) / 2)` を margin〜(画面の高さ−小窓の高さ−margin) に収める。gap は 8（`--space-2` と同じ値・`POPOVER_MARGIN` と同じく定数で持つ）。箱が無いとき（C キー・作成ボタン）は今の `fitPopover` と同じ真ん中。月表示の 1 日押し（箱を出さない）は今のまま押した点の横（`fitPopover`）。四角が `null` の間は、前に受けた四角（無ければ押した点）のまま置く。詳しく見る小窓・他 N 件の小窓は今の `fitPopover` のまま。
5. 作る小窓の見た目を Google に寄せる（G42・G50）。作る小窓だけに `schedule-popover--create` の class を足し、規則はその下だけに書く（詳しく見る・直す小窓は変えない）。
   - 小窓: 幅 `--schedule-create-popover-width: 37.5rem`、丸み `--schedule-create-popover-radius: 1.75rem`、地 `--schedule-create-popover-bg: var(--bg-subtle)`、枠なし、影は今の `--shadow-lg`。新しいトークンは `frontend/src/tokens.css` の `--schedule-popover-max-h` の次に置く（色は既存トークンを指すだけなので、ダークでも `--bg-subtle` のダークの値になる）。あわせて `frontend/src/pages/schedule.css:7-8` の `--schedule-popover-width`・`--schedule-popover-max-h` の写しを消し、`frontend/src/tokens.css:409-410` の 1 か所にする（値は同じなので見た目は変わらない）。
   - 行の形: 中身を 2 列の格子（`grid-template-columns: var(--schedule-create-icon-col) minmax(0, 1fr)`・`--schedule-create-icon-col: 2.75rem`＝絵 20px＋あき 24px）にし、小窓の左右の内側のあきを `--space-6`（24px）にする。絵は 1 列目、中身は 2 列目。各行の高さは `min-height: var(--space-10)`（40px）。題名は 2 列目に置く（Google と同じく 68px）。
   - 日時・場所・説明の 1 行: 今の金型 Button（ghost）を `size="md"` にする（高さ 36px・行の高さは 40px の格子が持つ）。絵は Button の外の 1 列目に出す。
   - 種類・Meet・社員にも見せる: 見出しの文字を外し、絵（下記）＋中身の行にする。種類の選ぶ欄は `aria-label` に「種類」を付ける。Meet と社員にも見せるは、文字＋右の切り替えのまま 1 行。
   - 絵: 金型の絵の表 `SCHEDULE_POPOVER_ICONS`（`frontend/src/constants/icons.tsx`）に heroicons outline の `CalendarIcon`（種類）・`VideoCameraIcon`（Meet）・`UsersIcon`（社員にも見せる）を足す。3 つとも heroicons 2.2.0 に在る（2026-11-09 に `frontend/node_modules/@heroicons/react/24/outline/CalendarIcon.js`・`VideoCameraIcon.js`・`UsersIcon.js` を確かめた。`frontend/package.json:79` は `^2.2.0`）。
   - 題名: 金型 `TextFieldControl` に種類 `"schedule-title"` を 1 つ足す（`frontend/src/components/TextField.tsx:35` の型と `frontend/src/components/FormField.css` の規則）。枠は下だけ 1px `var(--border)`、押すと下 2px `var(--accent)`、地は透明、文字は `--schedule-create-title-size: 1.375rem`（22px・tokens.css に足す）。空のときの文字は新しい文言キー `schedule.addTitle`（ja「タイトルを追加」・en「Add title」）。見本帳の例（`frontend/src/components/TextField.stories.tsx:112-` の variants の例）に 1 つ足す。
   - 下のボタン: 作るときは右寄せで「その他のオプション」（ghost）→「保存」（primary）の順。「キャンセル」は出さない（× は残す・Esc は今のまま）。「その他のオプション」は閉じている行（日時・場所・説明）を全部開き、全部開いたら出さない。新しい文言キー `schedule.moreOptions`（ja「その他のオプション」・en「More options」）。直す・詳しく見る小窓の下は今のまま。
   - 保存のボタンの形（Google は丸み 20px の青）は金型 Button の primary のまま（色はアプリの accent・丸みは `--comp-btn-radius`）。pill の形はログインの画面だけの決まり（`frontend/src/components/Button.tsx:9`）なので使わない。
6. 文言: 新しく足すキーは `schedule.addTitle`・`schedule.moreOptions` の 2 つ（2026-11-09 に `frontend/src/locales/ja.json` の `schedule` に無いことを確かめた）。`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキーを足す（ADR-027）。種類の選ぶ欄の aria-label は今ある `schedule.category`（「カテゴリ」）を使う。
7. ADR-1065 の What 6 に 1 文足す:「予定の四角を知りたいときは、呼ぶ側が対象の id と口（onEventRect）を渡す。金型はその予定の四角だけを返す」。`node scripts/generate-adr-index.js` で索引を作り直す。

試験:
- `frontend/src/pages/schedule/schedule-utils.test.ts`: `draftToRange`（時刻つき・終日 1 日・終日 2 日・読めない・end≦start）・`rangeToDraftDates`（終日 1 日・終日 2 日・時刻つき・end なし）・`draftToRange` と `rangeToDraftDates` の往復が同じ値（終日 1 日・終日 2 日・時刻つき）・`shiftDraftStart`（時刻つきで 10:00〜11:00 の始まりを 15:00 にすると 15:00〜16:00・日付を 1 日進めると終わりも 1 日進む・終日）・`fitCreatePopover`（右・左・縦の min・下にはみ出す・箱なしで真ん中）。
- `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`: 作る小窓に幕が無い・詳しく見るには幕がある／仮の箱が `editable: true`／題名に「試し」と入れると仮の箱の title が「試し」・空なら「(タイトルなし)」／作る小窓で始まりの時刻を直すと箱の start と end が同じ長さのまま動く／終日の仮の箱で `onEventResize("pending", …)` を呼ぶと下書きの allDay が真のまま／金型の `onEventMove("pending", …)` を呼ぶと日時の 1 行が変わり、PATCH・POST が 0 回、続けて保存すると POST の start_datetime・end_datetime が動かした後の値／`onEventResize("pending", …)` で終わりが変わる／終日の箱を動かすと startDate・endDate が変わる／日時の欄を直すと箱の start が変わる／時間割と小窓の外の pointerdown で閉じ、時間割の中の pointerdown では閉じない／下のボタンが「その他のオプション」「保存」の順で「キャンセル」が無い／「その他のオプション」で 3 つの行が開く。
- `frontend/src/components/CalendarView.test.tsx`: `trackEventId` を渡すと、その予定の描画の後に `onEventRect` が四角つきで呼ばれ、ほかの予定では呼ばれない／同じ日の中で start だけ変えた events を渡し直すと（要素は作り直されない）、`onEventRect` がもう一度呼ばれる／`eventWillUnmount` が古い要素で後から来ても、新しい要素を忘れない。
- 見た目の値（幅・丸み・22px・68px・40px・8px）は jsdom が計算しないので、受入れで本番の値を読む（G42〜G44）。

選ばなかった案:
- 仮の箱を FullCalendar の `selectMirror`（選んだ範囲の影）にする: 影は動かせない（つかめない）ので G45 を満たさない。
- `pendingRange` を残して、動かすたびに `pendingRange` と `draft` の両方を直す: 日時が 2 か所になり、片方だけ直す漏れが出る（G47 と SSOT に反する）。
- 幕を残し、幕の上に穴を開ける: 時間割の他の所（別の升目・他の予定）が押せないままで、Google と違う。
- 押した点を基準に置き続ける: 箱を動かした後に小窓が付いていかない（G45）。
- 小窓を動かすつまみ（≡）・種類のタブ（予定・タスク・予約枠）を作る: アプリにタスク・予約枠の種類は無く、つまみは今回の願い（作る時の表示と、箱を動かす）の外。次の便の候補に残す。
- 保存のボタンを pill にする: 金型 Button の pill はログインの画面だけの決まり。変えると全画面の決まりが変わる。
- 下線の題名を schedule.css で `variant="schedule"` に上書きする: 金型の外で見た目を変えることになる（ADR-144）。金型に種類を足す。

心配と対処:
- 幕を外すと、小窓の外の押した所がそのまま下の物に届く（例: 左の欄の別のカレンダーの切替を押すと、閉じると同時に切り替わる）: Google も同じ（外を押すとその操作も効く）。小窓の外の押しで閉じた後、入れかけの題名は消える（今の幕と同じ）。
- 仮の箱を時間割の外へ落とす: FullCalendar が元へ戻す（`eventDrop` は呼ばれない）。
- 作る小窓が開いている間に別の空の升目を押す: 今と同じく新しい箱で作り直す（題名は消える）。Google の動きは未確認（R12-4）。受入れで目で見て、Google と違えば次の便で直す。
- 幅 600px の小窓が狭い窓ではみ出す: 幅は `min(var(--schedule-create-popover-width), calc(100vw - var(--space-6)))`（今と同じ式）。高さは今の上限のまま。窓の幅 900 でも測る。
- 箱の四角を返す口が多く呼ばれる: 呼ぶのは対象の予定 1 つだけで、四角が前と同じなら置き場所は変えない（`usePopoverPlacement` の今の比べ方）。
- 金型 `TextFieldControl` の種類を足す（ADR-144・`docs/CC_UI_GOVERNANCE.md:14`「PO 許可を得てから components/ に金型を登録」）: PO の承認を得てから作る。今ある種類は変えない。
- 月表示: 箱を出すのは 2 日以上の終日だけ（今と同じ）。1 日押しは箱なしで、押した所の横（今のまま・G43 で確かめる）。
- 要素を作り直さない動かし方で四角が古いまま: 上の作り方 4 の ②（harness の style を見る）と ③（離した後）で測り直す。単体の試験と G45 の「同じ日の中で動かす」で確かめる。

戻し方: 便12 の PR を revert する（frontend だけ・DB・移行・設定は変えない）。

### 3.18 便13: Google Meet を押す行に・「その他のオプション」で全画面の編集（G51〜G57・2026-11-11）

アプリの行番号は origin/main 4ceb0f381（2026-11-11 に読んだ。768b3db1c まで予定の画面・金型・文言の差は無し）。

確かめた事実:
- R13-1（Google）: PO の言葉で、Google の Meet は「押す行」で、「その他のオプション」は全画面の編集が開き閉じるとカレンダーに戻る（PO 2026-11-10）。Google は Meet の行を押した時点で部屋を作るが、アプリは保存のときに作る（ADR-1060・PO 2026-11-10「1」）。このため押した後の行は参加の案内ではなく「保存すると参加用のリンクができます」と書く（まだ無いリンクを出さない）。Google の全画面の編集の細かい寸法は測っていない（未確認）。受入れで Google と並べて写しを撮り、並び（×・題名・保存が一番上、その下に項目）を比べる。
- R13-2（アプリの Meet）: 切り替え（金型 Toggle・`role="switch"`）で、`meetAvailable && !item?.meetUrl` のときに作る・直す小窓の両方に出る（`frontend/src/pages/schedule/SchedulePageImpl.tsx:541-552`）。値は下書きの `addMeet`（`:95`）1 つで、保存のとき `meetAvailable && draft.addMeet && !popover?.item?.meetUrl` なら `add_meet` を送る（`:1201`）。裏側（`backend/app/routers/calendar.py`・`backend/app/services/calendar_service.py`）は変えない。外す操作は作らない（ADR-1060 What 8）——今回の × は保存前の下書きの印を戻すだけで、Google の予定から Meet を外す操作ではない。
- R13-3（アプリの「その他のオプション」）: 作る小窓の下に在り、押すと閉じている行（日時・場所・説明）を全部開き、全部開くと消える（`:612-630`）。試験は `frontend/src/pages/schedule/SchedulePageImpl.test.tsx:726-738`。
- R13-4（重なりの心配）: ①作る小窓は document の `pointerdown` を capture で見て、小窓と時間割の外を押すと閉じる（`:309-324`）。全画面を小窓の上に重ねると、全画面の中を押しただけで小窓（と下書き）が閉じる。②近道のキーは window に 1 つ（`:1432-` の判定・`:1477` で付ける）。小窓が開いている間は `windowOpen = popover !== null`（`:1440`）で文字キーは今も効かない（`:1450`）。③失敗の文（`shownError`・`:1089`）と帯（`banner`・`:1649`）は時間割の側（`schedule-main`）に出るので、全画面の下に隠れる。
- R13-5（金型）: 窓いっぱいの入れ物の金型は無い（`frontend/src/components/` に Modal・Sheet・Drawer は在るが、Modal は寸法 sm〜xl・Drawer は右から出る板・Sheet は下から出る板）。新しい金型は PO の許可が要る（ADR-144・`docs/CC_UI_GOVERNANCE.md:14`。前例は Sheet・2026-10-13 PO 許可）。色・重なりのトークンは在る（`--z-modal: 400`・`frontend/src/tokens.css:135`／`--modal-wide-w: 880px`・`:489`／`--bg-surface`）。`frontend/scripts/check-css-fixed-position` は `src/pages` の css だけを見るので、金型の css で `position: fixed` を使える。

作り方:
1. Meet の行（G51・G52）。
   - `:541-552` の切り替えを、新しい部品 `MeetRow`（`frontend/src/pages/schedule/ScheduleDraftFields.tsx`）に替える。印が偽のとき: 金型 Button（ghost・md）に「Google Meet のビデオ会議を追加」（`schedule.addMeet` の文を替える）。押すと `onDraftChange({ ...draft, addMeet: true })`。印が真のとき: 文「Google Meet のビデオ会議（保存すると参加用のリンクができます）」（新しいキー `schedule.meetPending`）＋金型 Button（ghost・sm・iconOnly・× の絵・aria-label は新しいキー `schedule.removeMeet`「Google Meet を外す」）。× は `addMeet: false` に戻すだけ。
   - 出す条件・送る中身・`joinMeetLink`（`:327-339`）は変えない。
2. 入れる項目を 1 か所にする（SSOT）。
   - 作る小窓の項目（日時と終日・種類・Meet・社員にも見せる・場所・説明。今の小窓と同じ順）の描き方を `frontend/src/pages/schedule/ScheduleDraftFields.tsx` に移し、小窓と全画面の両方がそれを使う。値は今の `draft`（`:1033`）1 つで、全画面用に写しを作らない。始まりを直すときは今と同じ `shiftDraftStart` を使う。
   - 小窓は今の「閉じた行を押すと開く」まま。全画面は全部開いた形で出す（部品に `expanded` を渡す）。
3. 全画面の入れ物の金型 `FullScreenDialog`（G53・G56・G57。PO の許可の後に作る）。
   - 「frontend/src/components/FullScreenDialog.tsx」・`frontend/src/components/FullScreenDialog.css`・「frontend/src/components/FullScreenDialog.stories.tsx」・「frontend/src/components/FullScreenDialog.test.tsx」。document.body へ portal、`role="dialog"`・`aria-modal="true"`・`aria-label`（呼ぶ側が渡す文字）、`useFocusTrap`（`frontend/src/hooks/useFocusTrap`）、開いた時は `initialFocusRef`（無ければ最初の押せる物）へ、閉じた時は開く前の要素がまだ画面に在ればそこへ戻す（予定の画面では押した元は小窓と一緒に消えるので、戻る先は描き直した小窓の題名の欄。小窓の `placed` で題名へ移る今の動き・`:307`）。Esc は document の keydown で受けて `stopPropagation` し `onClose`（金型 Modal と同じ形・window の近道へ届かない）。ただし変換中（`event.isComposing || event.keyCode === 229`）の Esc は何もしない（近道の判定 `:1436` と同じ形。金型 Modal の Esc `:72-77` は見ていないので写さない）。
   - 口: `open`・`onClose`・`ariaLabel`・`closeLabel`・`title`（一番上の真ん中に置く中身）・`actions`（右の中身）・`children`。× は金型 Button（ghost・iconOnly）。
   - 見た目: `position: fixed; inset: 0; z-index: var(--z-modal); background: var(--bg-surface)`。一番上の帯と中身。中身の幅は `min(var(--modal-wide-w), 100%)` で真ん中。新しいトークンは足さない（数値は既存の space・トークンだけ）。
4. 予定の画面につなぐ（G53〜G56）。
   - ページの状態 `fullEditOpen`（真偽）を足す。作る小窓の「その他のオプション」は `setError(null)` と `setFullEditOpen(true)` にする（行を開く今の動きはやめる）。
   - 全画面が開いている間は作る小窓を描かない（`{popover && !fullEditOpen && <SchedulePopover …/>}`・`:1752`）。`popover` は残すので、仮の箱（`:1318-1320` は `popover?.mode` を見る）と下書きは残る。閉じると小窓が同じ `popover.anchor` で描き直される。
   - 新しい部品 `ScheduleFullEditor`（`frontend/src/pages/schedule/ScheduleFullEditor.tsx`）: 金型 `FullScreenDialog` の中に、題名（金型 `TextFieldControl variant="schedule-title"`）・「保存」（金型 Button primary・題名が空なら押せない）・`ScheduleDraftFields`（`expanded`）・失敗の文（`error` を中に出す）。
   - × と Esc は `setFullEditOpen(false)` と `setError(null)`（保存に失敗した文は編集画面の中で見せ終えたので、時間割の側 `shownError`・`:1089` に残さない）。下書き・popover は触らない・何も送らない。
   - 編集画面の Meet の行の出す条件は、作る小窓に渡している `meetAvailable`（`:1766-1773` の式）と同じ値を渡す（式を 2 か所に書かない。1 つの変数にして両方へ渡す）。
   - 保存は今の `saveEvent`（`:1186-1225`）をそのまま呼ぶ。`saveEvent` の成功の道の最後に `setFullEditOpen(false)` を足す。失敗の道は `setError` のままなので全画面は開いたままで、全画面の中に `error` を出す。
   - 近道の判定（`:1432-`）の最初に `if (fullEditOpen) return;` を足す。今も `windowOpen`（`:1440`）で止まるが、小窓を描かない形に変わっても止まることを明示しておく（Esc は金型が先に止める）。
   - `popover` が null になる道（保存・時間割の外を押す）では `fullEditOpen` も偽にする（`useEffect` で `popover?.mode !== "create"` のとき偽・`:1318` と同じ形）。
5. 文言（ADR-027）: `schedule.addMeet` の文を替える（ja「Google Meet のビデオ会議を追加」・en「Add Google Meet video conferencing」）。新しいキー `schedule.meetPending`・`schedule.removeMeet`・`schedule.fullEditLabel`（ja「予定の編集」・en「Edit event」）を `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` の両方に足す。× の読み上げは今ある `common.close`。
6. 触らない範囲: 裏側・DB・移行・deploy・scripts・Google の権限。詳しく見る・直す小窓の並び（Meet の行の置き換えだけ）。既に有る予定を全画面で直すこと・招待する人・通知・繰り返し・色（次の便の候補）。

試験:
- 「frontend/src/components/FullScreenDialog.test.tsx」: open で dialog が出る・aria-modal・× と Esc で `onClose`・Esc が window へ届かない・変換中の Esc では `onClose` が呼ばれない・Tab が中を回る・閉じると元の要素へ戻る。
- `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`: 今の Meet の試験 8 本（`:437-`）を `role="button"` に読み替え／× で戻すと `add_meet` を送らない／`queryByRole("switch", { name: /Google Meet/ })` が null（作る小窓・直す小窓・全画面の 3 か所）／「その他のオプション」で dialog が開き、題名・日時が小窓の値のまま（`:726-738` を書き替え）／× と Esc で dialog が消え小窓が開いたまま題名が残り POST・PATCH が 0 回／dialog の保存で POST の中身が小窓からの保存と同じ・成功で dialog と小窓が消える・失敗で dialog が開いたままエラー文が dialog の中／dialog が開いた状態で「m」を送っても表示が変わらない／× で閉じた後のフォーカスが作る小窓の題名の欄／保存に失敗して × で閉じると時間割の側に失敗の文が出ない。
- 見本帳: 「frontend/src/components/FullScreenDialog.stories.tsx」（`check:stories`）。

選ばなかった案:
- 金型 Modal に寸法「full」を足す: Modal の上の帯は題の文字 1 つの形で、×・題名の欄・保存の帯にならない。広く使われている金型の形を変えることになる。
- 金型 Drawer に寸法を足す: 右から出る板で、背景の幕を押すと閉じる作り。窓いっぱいの形と動きが違う。
- 別の道（URL）`/schedule/new` に画面を作る: 下書きを道をまたいで持ち運ぶことになり、下書きが 2 か所になる（SSOT に反する）。戻ったときの仮の箱・小窓の位置も作り直しになる。
- 全画面を小窓の上に重ねる: 小窓の外の押しで閉じる仕組み（R13-4 ①）で、全画面を押しただけで下書きが消える。
- Meet の行を押した時点で部屋を作る（Google と同じ）: PO が「部屋は保存のときに作る」を選んだ（2026-11-10「1」）。

心配と対処:
- 小窓を描き直すと、小窓の中の開いた行（日時・場所・説明）は閉じた形に戻る: 値は下書きに残るので消えない。全画面で直した値は、閉じた行の 1 行の文に出る。
- 全画面の題名の欄に初めから文字を入れると、近道のキーの判定より前に金型の Esc が働く: 金型が `stopPropagation` するので window の近道は動かない（試験で確かめる）。
- 狭い窓（スマホの幅）: 全画面なのではみ出さない。中身は縦に並ぶだけ。
- 編集画面で日付を今見ている週の外へ変えて閉じる: 仮の箱は見えず、小窓は前の位置に出る（`handlePendingRect` は四角が null のとき置き場所を変えない・`:1356`）。今の作る小窓の中で日付を週の外へ変えたときと同じ動きなので、今回は変えない。保存すれば予定はその日に入る。
- Meet の × を Google の予定から Meet を外す操作と取り違える: 印が真になるのは保存前の下書きだけで、保存済みの予定では行が出ない（`!item?.meetUrl`）。

戻し方: 便13 の PR を revert する（frontend だけ・DB・移行・設定は変えない）。

### 3.19 便14: 予定の編集画面を Google の形に（左に寄せる・角の小さい塗りの欄・直すときも全画面）（G58〜G64・2026-11-11）

アプリの行番号は origin/main a7fbffdfe（2026-11-11 に読んだ）。

確かめた事実:
- R14-1（Google の形）: recon §8.1。中身は左に寄り（題名 x80・札 x16 幅 636）、白い札の中に絵の列（真ん中 x48）と欄（x80〜）。欄は塗りの地・角 4px・枠なし・高さ 40。保存は丸い。
- R14-2（今の金型で作れない理由）: 金型 FullScreenDialog は中身を真ん中寄せの 1 列にする（`frontend/src/components/FullScreenDialog.css:46-49`）だけで、左に寄せる・札で包む・絵の列を作る口が無い（「frontend/src/components/FullScreenDialog.tsx:93-102」）。入力欄は決まりで完全に丸く（`docs/specs/design-system/design.md:811`）、角 4px の塗りの欄の種類（variant）が無い。保存の丸い形はログイン画面だけ（`frontend/src/components/buttonShapeUsage.test.ts:13-19`）。
- R14-3（今の画面）: recon §8.2。真ん中寄せ・丸い白地の欄・文字つき・終日は切り替え。
- R14-4（直す流れ）: 直すは小窓の中で入力欄に変わる（`frontend/src/pages/schedule/SchedulePageImpl.tsx:975-982`・`:380-420`・`:432-440`）。全画面は作るときだけ（`:1587`）。保存は 1 つの関数 `saveEvent`（`:988-1031`）で、直すときは PATCH。
- R14-5（使う所）: FullScreenDialog を使うのは `frontend/src/pages/schedule/ScheduleFullEditor.tsx` だけ。本番の点検 S13 は dialog の名前「予定の編集」（`schedule.fullEditLabel`）で探す。

作り方:
1. 新しい金型 `EditorPage`（PO の許可の後に作る・ADR-144・ADR-1074）。
   - 置き場所: `frontend/src/components/EditorPage.tsx`・`frontend/src/components/EditorPage.css`・`frontend/src/components/EditorPage.stories.tsx`・`frontend/src/components/EditorPage.test.tsx`。
   - 振る舞いは FullScreenDialog と同じ（portal・`role="dialog"`・`aria-modal`・`aria-label`・`useFocusTrap`・開くと `initialFocusRef` へ・閉じると元の要素がまだ在ればそこへ・Esc は document で受けて `stopPropagation`・変換中の Esc は何もしない）。中身は FullScreenDialog.tsx の振る舞いの部分をそのまま移す（書き直さない）。
   - 口: `open`・`onClose`・`ariaLabel`・`closeLabel`・`title`（題名の欄）・`saveLabel`・`onSave`・`saveDisabled`・`initialFocusRef`・`lead`（札の上に置く中身。日時の段）・`cardTitle`（札の頭の文字）・`children`（札の中の行）。行の部品 `EditorPageRow`（口 `icon`・`children`）も同じファイルから出す（絵の列は金型が持つ）。
   - 保存のボタンは金型が描く: 金型 Button `variant="primary"`・`shape="pill"`。× は金型 Button（ghost・iconOnly）。
   - 見た目（`EditorPage.css`・var() だけ）: 地 `--bg-primary`。左の余白 `--space-4`、絵の列の幅 `--comp-editor-rail-w`（新しいトークン 4rem）。上の段は [× の列][題名（最大幅 `--comp-editor-title-w`・新しいトークン 37.125rem）][間 `--space-8`][保存]。`lead` は題名と同じ左端。札は地 `--bg-surface`・角 `--comp-editor-card-radius`（新しいトークン 1.75rem）・幅 `min(var(--comp-editor-main-w), 100%)`（新しいトークン 39.75rem）。札の頭は高さ `--space-12` で `cardTitle` を出し、下に 2px の `--accent` の線（Google の選ばれたタブの線に合わせる。押せる物ではない）。行は [絵の列][中身]・行の間 `--space-2`。狭い窓（`@media (max-width: 767px)`・ほかの金型と同じ区切り。例 `frontend/src/components/Card.css:34`）では札の幅を 100% にし、上の段の題名が縮む。
   - 古い金型 FullScreenDialog の 4 ファイルは消す（使う所が無くなるため。同じ働きの金型を 2 つ置かない・`docs/specs/design-system/design.md:32`）。
2. 塗りの欄の種類（variant）を足す（金型の口を 1 つずつ・ADR-1074）。
   - TextFieldControl に `editor-filled` と `editor-title`、SelectControl と TextareaControl に `editor-filled`。
   - `editor-filled`（`frontend/src/components/FormField.css`）: `min-height: var(--space-10)`・`border: none`・`border-radius: var(--radius-sm)`・`background-color: var(--comp-input-filled-bg)`・`padding: 0 var(--space-4)`・`font-size: var(--font-sm)`。押した時は下に 2px の `--accent` の線（`box-shadow: inset 0 -2px 0 var(--accent)`）。Textarea は上下にも `--space-2`。
   - `editor-title`: schedule-title と同じ形で文字だけ `--font-2xl`。
   - 新しいトークン `--comp-input-filled-bg` の値は §3.20 作り方 2（`var(--gcal-surface-filled)`・明るい #e9eef6／暗い #282a2c）。【2026-11-11 色の追加で置き換え。元の案: 明るい表示 `var(--link-active-bg)`、暗い表示 `var(--bg-subtle)`（#243046・暗い札 #1e293b の上で見える）】。`frontend/src/index.css` の明るい・暗いの両方に置く（`check:dark-parity`）。
3. 項目の部品（`frontend/src/pages/schedule/ScheduleDraftFields.tsx`）を 1 項目ずつの部品に分ける。
   - `DraftDateFields`・`DraftCategoryField`・`DraftMeetField`・`DraftShareField`・`DraftLocationField`・`DraftDescriptionField` を同じファイルに置き、それぞれ口 `appearance: "popover" | "page"` を持つ。値を変える式（`shiftDraftStart`・種類で社員にも見せるを変える式）は各部品の中の 1 か所のまま。
   - `ScheduleDraftFields`（作る小窓が使う）は今と同じ順で `appearance="popover"` の部品を並べるだけにする（作る小窓の見た目と動きは変えない）。
   - `appearance="page"` のとき: 欄は `editor-filled`・欄の上の文字を出さず `aria-label` で持つ・終日は金型 Checkbox（label は `schedule.allDay`）・日時は 1 段（始まりの日・始まりの時刻・〜・終わりの時刻・終わりの日）。
   - 「Google Meet で参加」のリンク（今は小窓 `frontend/src/pages/schedule/SchedulePageImpl.tsx:290-301` で作る）は `DraftMeetField` の中に移す（小窓と編集画面の 2 か所で作らない）。`MEET_URL_PREFIX`（`:96`）も一緒に移す。
4. `frontend/src/pages/schedule/ScheduleFullEditor.tsx` を金型 `EditorPage` に載せ替える: `lead` に失敗の文（`role="alert"`）・`DraftDateFields`・終日、札の中に `EditorPageRow` で Meet・場所・種類・社員にも見せる・説明（G62 の順）。札の頭は `schedule.eventDetail`（「予定の詳細」・既存のキー）。dialog の名前は今の `schedule.fullEditLabel` のまま（S13 が探す名前）。口 `mode` と `item` を足す。
5. 直すときも編集画面（`frontend/src/pages/schedule/SchedulePageImpl.tsx`）。
   - `openEdit`（`:975-982`）の最後で `setError(null)` と `setFullEditOpen(true)`。
   - 編集画面を開く条件（`:1588`）を `fullEditOpen && (popover?.mode === "create" || popover?.mode === "edit")` に。閉じる useEffect（`:1132-1134`）は `popover === null || popover.mode === "detail"` のときに閉じる。
   - 閉じる（`:1591`）: 作るときは今と同じ（小窓に戻る）。直すときは `setPopover(null)` も（カレンダーに戻る）。
   - 小窓の中の直す形（`:394-406` の文字つきの題名・`:432-440` の下の段）を消す。小窓は「作る」と「詳しく」の 2 つだけになる（`:311` の見出しは「予定の詳細」だけに）。
6. 守り手（CI の試験）を足す。
   - `frontend/src/components/buttonShapeUsage.test.ts` の使ってよい場所に `frontend/src/components/EditorPage.tsx` と `frontend/src/components/EditorPage.stories.tsx`・`frontend/src/components/EditorPage.test.tsx` を足す（画面のファイルには足さない）。
   - 新しい `frontend/src/components/editorVariantUsage.test.ts`: `"editor-filled"`・`"editor-title"` の文字が、金型 3 つ（TextField・Select・Textarea）とその見本帳・試験、`components/EditorPage.*`、`frontend/src/pages/schedule/ScheduleDraftFields.tsx`・`frontend/src/pages/schedule/ScheduleFullEditor.tsx`、`pages/design-preview/` の外の tsx に 0 件。
   - 決まりの文書 `docs/specs/design-system/design.md:260,276,537,1115,811` に例外の 1 文（ADR-1074 を指す）。
7. 文言: 新しいキーは 1 つだけ `schedule.rangeSeparator`（ja「〜」・en「–」。日時の段の始まりと終わりの間の文字。`aria-hidden`。2026-11-11 に ja.json を探して同じ働きのキーが無いことを確かめた）。ほかは既存のキー（`schedule.eventDetail`・`schedule.fullEditLabel`・`schedule.allDay` など）を使う。日時 4 つの欄の読み上げの名前は、今の欄の上の文字と同じキーを `aria-label` に渡す。
8. 触らない範囲: 裏側・DB・移行・deploy・scripts・Google の権限・本番の点検 S13。詳しくの小窓の中身（直す形を消すだけ）・作る小窓の見た目。招待する人・通知・繰り返し・タイムゾーン・「時間を探す」のタブ・説明の飾りの帯（Google に在るがアプリに機能が無い）。

試験:
- `frontend/src/components/EditorPage.test.tsx`: 「frontend/src/components/FullScreenDialog.test.tsx」 の 7 本（F1〜F7: dialog と aria-modal と名前・× で `onClose`・Esc で `onClose` と window へ届かない・変換中の Esc・初めのフォーカス・Tab が中を回る・閉じると元の要素へ）をそのまま移す。足す: 保存のボタンが `onSave` を呼ぶ・`saveDisabled` で押せない・`lead`・`cardTitle`・`EditorPageRow` の絵と中身が出る。
- `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`: 今の直すの試験（`:171`・`:183`・`:507-547`・`:571-590`・`:1009`）を編集画面の中で通す。足す: 直すから開いて題名が予定の題名／× と Esc で閉じると小窓が 0 個で PATCH・POST が 0 回／直すの保存で PATCH・成功で閉じる・失敗で開いたまま文が中／G62 の順／終日がチェック欄。
- `frontend/src/components/editorVariantUsage.test.ts`（新規）・`frontend/src/components/buttonShapeUsage.test.ts`（場所を足す）。

選ばなかった案:
- FullScreenDialog に口（layout）を足す: PO が「別途金型を作って」と言った。今の真ん中寄せの形を使う画面はほかに無く、2 つの形を 1 つの金型に持たせる理由が無い。
- 今の丸い欄（schedule）の角だけ変える: 作る小窓も一緒に変わる（作る小窓の欄は Google でも丸くない別の形で、PO は編集画面の話をしている）。
- （2026-11-11 色の追加で取り下げ）欄の地を既存の `--link-active-bg` で代える案: PO が Google と同じ色を求めたので、§3.20 の `--gcal-surface-filled` を使う。
- 保存を今の角 6px のまま: PO は「真似て」と言った。丸い形は金型 Button に既に在り、使う場所を金型 1 つ足すだけで済む。
- 右の列（ゲスト）・繰り返し・通知も作る: 裏側に機能が無い。今回は見た目と並びだけ。

心配と対処:
- 小窓の中の直す形を消すと、今の試験が落ちる: 落ちる試験は上に挙げた行だけ。編集画面で同じ確かめをし、確かめの数を減らさない。
- 狭い窓で日時の段がはみ出す: 段を折り返す（flex-wrap）。G63 で 390 の幅を測る。
- 塗りの欄が他の画面に広がる: 守り手の試験（作り方 6）で止める。
- 本番の点検 S13 が落ちる: dialog の名前・題名の欄・Esc の動きは変えない。合流の後の点検で確かめる（G64）。
- 消す金型を誰かが使い始めている: 合流の前に `git grep FullScreenDialog` を取り直す。

戻し方: 便14 の PR を revert する（frontend と書類だけ・DB・移行・設定は変えない）。

### 3.20 便14: 予定の画面の色を Google に合わせる（G65〜G67・2026-11-11 追加）

PO 2026-11-11 の言葉: 「予定の色だけどGoogleと色を併せて、Googleのは移植は心理的な意識をした青を使った配色になっていたはず」。範囲: 「予定の画面すべて」（編集画面・カレンダーの表・予定の箱・作る小窓・詳しくの小窓。ほかの画面は今のまま）。

アプリの行番号は origin/main a7fbffdfe（2026-11-11 に読んだ）。

確かめた事実:
- R14-6（Google の色）: recon §8.6 に明るい・暗いの両方を測った。青を選んだ心理の理由は Google の公式の説明が見つからず **未確認**。根拠は「PO が Google と同じ色を求めた」だけにする。
- R14-7（予定の箱）: 箱の地は持ち主（社員）の色で、正本はサーバー（`backend/app/routers/calendar.py:50` `_DEFAULT_OWNER_COLOR = "#1a73e8"`）。文字は白（`--on-solid` #fff・`frontend/src/tokens.css:558`）。`--on-solid` を暗い文字に変えると #1a73e8 の上で読みにくくなる（明るさの比 約 2.7）。→ 箱の色と文字は変えない。
- R14-8（範囲の作り）: 予定の画面の根は `frontend/src/pages/schedule/SchedulePageImpl.tsx:1304` の `<div className="schedule-page">`。作る小窓（`:306`）・日の一覧の小窓（`:633`）はこの中に描かれる。表示の選び（`:1348` 金型 Popover）・近道の表（`:754` 金型 Modal）・右クリックの表（ContextMenu）・編集画面（`:1587`）は body の直下に出る（portal）。
- R14-9（CSS の決まり）: `:root` で `var()` を使って決めたトークンは `:root` で値が決まり、子の要素で元のトークンを変えても変わらない。予定の画面で使う、変える元のトークンから作られたトークンを機械で全部探した（2026-11-11 に Python の短い式で、`frontend/src/index.css`・`frontend/src/tokens.css` の `:root` の定義をたどり、`frontend/src/pages/schedule.css` と予定が読み込む金型の CSS（CalendarView・FormField・Button・Checkbox・CheckboxControl・Badge・EmptyState・ListRow・PageLayout・Toggle）の `var()` と突き合わせた）: `--schedule-today`（`frontend/src/tokens.css:399`）・`--schedule-gridline`（`:400`・暗い表示は `:675` の #2d3b52）・`--schedule-create-popover-bg`（`:413`）・`--comp-btn-primary-text`・`--comp-btn-primary-hover-bg`・`--comp-btn-tab-selected-text`・`--comp-btn-focus-color`（`frontend/src/index.css:12-15`・暗い `:221-224`）・`--icon-empty`（`frontend/src/components/EmptyState.css:32`）・`--indicator`（`frontend/src/components/ListRow.css:64`）・`--comp-badge-count-ring-color`（`frontend/src/components/Badge.css:64`）・`--role-page-title-color`（`frontend/src/tokens.css:45`・使う所は `frontend/src/pages-layout.css:158` の `.text-page-title`＝`frontend/src/components/PageLayout.tsx:49` の題名。1 回目の洗い出しで `pages-layout.css` を見落とし、5 回目の審査 3 で見つかった。ほかの文字の役のトークン `--role-section-title-color`・`--role-card-title-color`・`--role-body-color`・`--role-caption-color` は、使う class が予定の画面に 0 件と確かめた）。これらは範囲の札の中でも決め直す。`frontend/src/pages/schedule.css:3-17` の `.schedule-page` の中の決め直し（`--schedule-rail-bg` など）は同じ要素で決まるので、範囲の札の値を拾う。今の時刻の線 `--schedule-now-line` は色の直書き（`frontend/src/tokens.css:401` #ea4335）。

作り方:
1. Google の色のトークン 13 個を `frontend/src/index.css` に足す。明るい表示は `:root` の `--calendar-*` の後（`:191` の後）、暗い表示は `:root.force-dark` の `--calendar-*` の後（`:392` の後）。両方に置く（`check:dark-parity`）。名前は `--gcal-` で始める（色のトークンの見本帳の検査 `check-color-token-sync` は bg/text/accent/border/success/warning/danger/info で始まる名前だけを見るので、見本帳には足さない）。値は色の直書きで、予定専用の既存の `--calendar-*`（`frontend/src/index.css:184-191`・暗い `:385-392`）と同じ形（決まりの文書の層0〜1 の理想 `docs/specs/design-system/design.md:30-31` とは違うが、今の予定の色のトークンと揃える）。

| トークン | 明るい | 暗い | Google のどこ（recon §8.6） |
|---|---|---|---|
| `--gcal-surface` | #f8fafd | #1b1b1b | ページの地・編集画面の地 |
| `--gcal-surface-lowest` | #ffffff | #131314 | 表の札・編集画面の札 |
| `--gcal-surface-container` | #f0f4f9 | #1e1f20 | 作る小窓・詳しくの小窓の地 |
| `--gcal-surface-filled` | #e9eef6 | #282a2c | 塗りの欄 |
| `--gcal-on-surface` | #1f1f1f | #e3e3e3 | 文字 |
| `--gcal-on-surface-variant` | #444746 | #c4c7c5 | 絵・補足・曜日・時刻 |
| `--gcal-outline-variant` | #c4c7c5 | #444746 | タブの下の線 |
| `--gcal-gridline` | #dde3ea | #333537 | 日の列の線 |
| `--gcal-primary` | #0b57d0 | #a8c7fa | 保存・今日の丸・リンク・押した欄の線 |
| `--gcal-on-primary` | #ffffff | #062e6f | 保存と今日の丸の文字 |
| `--gcal-secondary-container` | #c2e7ff | #004a77 | 選ばれた表示切替・種類の地 |
| `--gcal-on-secondary-container` | #004a77 | #c2e7ff | 選ばれた種類の文字 |
| `--gcal-now` | #db372d | #f55e57 | 今の時刻の線と丸 |

2. 塗りの欄のトークン `--comp-input-filled-bg`（§3.19 作り方 2）は、明るい・暗いとも `var(--gcal-surface-filled)` にする（§3.19 の `--link-active-bg`／`--bg-subtle` の案を置き換える）。使うのは編集画面の中だけなので、ほかの画面は変わらない。
3. `frontend/src/tokens.css` の `:root` に 2 つ足す（今の値と同じなので、範囲の外は変わらない）: `--schedule-today-text: var(--on-solid);`（今日の丸の文字）・`--schedule-popover-bg: var(--bg-surface);`（詳しくの小窓の地）。
4. 範囲の札 `.gcal-colors` を `frontend/src/tokens.css` の最後（`:687` の後）に 1 つ置く。中身（すべて var()）:
   - 地: `--bg-primary: var(--gcal-surface)`・`--bg-surface: var(--gcal-surface-lowest)`・`--bg-subtle: var(--gcal-surface-container)`。
   - 文字と線: `--text-primary: var(--gcal-on-surface)`・`--text-secondary: var(--gcal-on-surface-variant)`・`--text-muted: var(--gcal-on-surface-variant)`・`--border: var(--gcal-outline-variant)`・`--role-page-title-color: var(--gcal-on-surface)`。合わせて 25 行。
   - 青: `--accent: var(--gcal-primary)`・`--accent-hover: var(--gcal-primary)`・`--on-accent: var(--gcal-on-primary)`・`--link-active-bg: var(--gcal-secondary-container)`。
   - ボタンほか（R14-9 で見つけた作られたトークン）: `--comp-btn-primary-text: var(--gcal-on-primary)`・`--comp-btn-primary-hover-bg: var(--gcal-primary)`・`--comp-btn-tab-selected-text: var(--gcal-on-secondary-container)`・`--comp-btn-focus-color: var(--gcal-on-surface)`・`--icon-empty: var(--gcal-on-surface-variant)`・`--indicator: var(--gcal-primary)`・`--comp-badge-count-ring-color: var(--gcal-surface-lowest)`。
   - 予定: `--schedule-today: var(--gcal-primary)`・`--schedule-today-text: var(--gcal-on-primary)`・`--schedule-gridline: var(--gcal-gridline)`・`--schedule-now-line: var(--gcal-now)`・`--schedule-create-popover-bg: var(--gcal-surface-container)`・`--schedule-popover-bg: var(--gcal-surface-container)`。
   - 変えない: `--bg-hover`・影・押した時の輪（`--focus-ring-shadow`）・失敗や成功の色・`--schedule-slot-hover`・`--calendar-google-blue*`・`--on-solid`・予定の箱の色と文字（Google の値を測っていない、または R14-7）。
5. 札を付ける場所は 2 つだけ: `frontend/src/pages/schedule/SchedulePageImpl.tsx:1304` を `className="schedule-page gcal-colors"` に。金型 `EditorPage` の根（portal の中の dialog）にいつも `gcal-colors` を付ける（編集画面は予定でしか使わない・ADR-1074）。
6. CSS の行を直す:
   - `frontend/src/pages/schedule.css:25` の `.schedule-page` に `background: var(--bg-primary);` と `color: var(--text-primary);` を足す（今は `.app-content` が透明で地が無い・`frontend/src/styles/topbar.css:97`。文字の色も決めないと、自分で色を決めていない文字が body の古い色 rgb(26,32,44) を受け継ぐ・6 回目の審査 2）。
   - `frontend/src/pages/schedule.css:351`（`.schedule-popover` の地）を `var(--schedule-popover-bg)` に。
   - 今日の丸の文字 5 か所を `var(--on-solid)` から `var(--schedule-today-text)` に: `frontend/src/pages/schedule.css:166`（左の小さい暦）・`:594`（一覧）・`:1110`（日の見出し）・`frontend/src/components/CalendarView.css:220`（日・週の数字）・`:364`（月の数字）。
7. 「Google Meet で参加」のリンク（`DraftMeetField` の中・§3.19 作り方 3）は金型 ButtonLink の `variant="primary"`（Google は青い地・白い字。今は secondary・`frontend/src/pages/schedule/SchedulePageImpl.tsx:290-301`）。
8. 守り手（CI の試験）`frontend/src/components/gcalColorsUsage.test.ts`（新規）: `gcal-colors` の文字は `frontend/src/pages/schedule/SchedulePageImpl.tsx`・`frontend/src/components/EditorPage.tsx`・`frontend/src/components/EditorPage.stories.tsx`・`frontend/src/components/EditorPage.test.tsx`・`frontend/src/components/gcalColorsUsage.test.ts`・`frontend/src/pages/schedule/SchedulePageImpl.test.tsx`・`tokens.css` の外の `frontend/src` に 0 件（`index.css` の説明の文にも札の名前を書かない）。`--gcal-` は `index.css`・`tokens.css`・`frontend/src/components/gcalColorsUsage.test.ts` の外に 0 件（カード §8 と同じ）。どちらも「探して 1 件以上見つかった」ことも確かめる（探し方が壊れて 0 件になるのを防ぐ）。数えるのはこの試験のファイル自身を除いた物: (1) は `tokens.css` と `frontend/src/pages/schedule/SchedulePageImpl.tsx`、(2) は `index.css` と `tokens.css` が見つかった物に在ること（6 回目の審査 1）。
9. 決まりの文書 `docs/specs/design-system/design.md:30-31`（色の層の説明）の後に 1 文: 「予定の画面だけは範囲の札 `.gcal-colors` で Google の色に置き換える（ADR-1074）。ほかの画面で使わない（`frontend/src/components/gcalColorsUsage.test.ts`）」。

触らない: ほかの画面・予定の設定の画面（`.schedule-settings` には札を付けない）・body の直下に出る金型（表示の選び Popover・近道の表 Modal・右クリックの表 ContextMenu。ほかの画面と共通の金型で、範囲の外に描かれる）・予定の箱の色・裏側・DB。

選ばなかった案:
- アプリ全体の `--accent` を Google の青にする: PO の範囲は「予定の画面すべて」で、ほかの画面は今のまま。
- 予定の CSS の `var(--text-primary)` などを 1 行ずつ `var(--gcal-*)` に書き換える: 予定の CSS と金型の CSS の色の行は 149 行（2026-11-11 に数えた）。金型（Button・TextField など）の CSS も予定のためだけに書き換えることになり、ほかの画面との共有が崩れる。範囲の札で元のトークンを置き換えるほうが、触る行が少なく、戻すのも札を外すだけ。
- 予定の箱も Google のように暗い表示で色を変える: 色の正本はサーバーで、Google の変え方の決まりを測っていない（R14-7）。
- body の直下に出る金型にも札を付ける: ほかの画面と共通の金型で、予定から開いたときだけ色を変える口が要る。今回は見送る（未対応として報告する）。

心配と対処:
- 札の中で作られたトークンを決め直し忘れ、古い色が残る: R14-9 の機械の洗い出しで全部挙げた。G65・G66 で本番の値を読んで確かめる。
- 札がほかの画面に広がる: 守り手の試験（作り方 8）で止める。G67 で外の画面の主ボタンの色が rgb(30,58,138) のままか読む。
- 暗い表示の保存の文字（#062e6f）が読めない: 地 #a8c7fa との明るさの比は 7 以上（Google と同じ組み合わせ）。
- 押した時の輪（`--focus-ring-shadow`）は古い青のまま: Google の値を測っていない。未対応として報告する。

戻し方: 便14 の PR を revert する。色だけ戻すときは 2 か所の `gcal-colors` を外す。

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
| 便9 | 月表示の日付・今日の丸・曜日の行・予定の 1 行の形、詳しくの小窓と一覧の時刻の形（§3.14 の A 組）。金型 CalendarView の月の中身 2 つ・css・トークン 1 つ・予定の画面の 2 か所・ADR-1065 の決まり 7 に月の 1 文（§3.14「ADR の改訂」・PO 承認 2026-11-09「1」） | G31〜G35 | なし（frontend だけ。移行・deploy・scripts・DB は無い） |
| 便10 | 日・3日間・週から月へ切り替えると画面全体が消える不具合の直し（§3.15）。金型 CalendarView の 1 か所（`views` を常に渡す）と試験 | G36 | なし（frontend だけ。移行・deploy・scripts・DB は無い） |
| 便11 | 日・3日間・週の枠線を Google に揃える（§3.16）。金型 CalendarView の css に規則 8 つ・トークン 1 つ | G37〜G41 | なし（frontend の css だけ。移行・deploy・scripts・DB は無い） |
| 便12 | 作る小窓を Google の形に・作っている途中の箱を動かせる（§3.17）。金型 CalendarView に口 1 つ（ADR-1065 What 6 に 1 文）・金型 TextFieldControl に種類 1 つ・絵 3 つ・トークン 5 つ・文言 2 つ・予定の画面 | G42〜G50 | なし（frontend だけ。移行・deploy・scripts・DB は無い）。PO 承認（G42〜G50・金型 2 つ・ADR-1065 What 6）の後に着手 |
| 便13 | Google Meet を押す行に・「その他のオプション」で全画面の編集（§3.18）。新しい金型 FullScreenDialog 1 つ・項目の部品を 1 か所に・文言 3 つ足し 1 つ替え・予定の画面 | G51〜G57 | なし（frontend だけ。移行・deploy・scripts・DB・Google の権限は無い）。PO 承認済み（2026-11-11「1」・G51〜G57・新しい金型）。カード `docs/handoff/schedule-gcal-clone/card-bin13.md` |
| 便14 | 予定の編集画面を Google の形に・直すときも全画面（§3.19）。新しい金型 EditorPage（古い金型 FullScreenDialog は消す）・塗りの欄の種類 4 つ・トークン 5 つ・文言 1 つ・項目の部品を 1 項目ずつに・予定の画面・守り手の試験 1 つ足し 1 つ直し・決まりの文書に例外 5 文・ADR-1074 | G58〜G64 | なし（frontend と書類だけ。移行・deploy・scripts・DB・Google の権限は無い）。PO 承認済み（2026-11-11「1」・G58〜G67・新しい金型・古い金型を消す・塗りの欄・丸い保存・直すときも全画面・予定の画面の色を Google に）。カード `docs/handoff/schedule-gcal-clone/card-bin14.md` |
| 便15A・便15B | 予定の繰り返し（§12）。便15A は裏側（欄 4 つの移行・受け口・広げ方・3 択・Google 同期）、便15B は画面 | G69〜G79 | 便15A は**あり**（`migrations/`・ADR-136 の GO）。便15B はなし（frontend だけ） |

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
- 便12 の事例: Google カレンダーの作る小窓と、開いたまま仮の箱を動かす動き（2026-11-09 に PO のログインの画面で測った・§3.17 R12-1・R12-3・R12-5。保存はしていない）。Google の絵・名前・色は使わず、並びと手の動きだけ合わせる。
- 便13 の事例: Google カレンダーの Meet の行と「その他のオプション」の全画面の編集（PO の言葉 2026-11-10）。寸法は未測定で、受入れで並べて比べる。Google の絵・名前・色は使わない。
- 便14 の事例: Google カレンダーの予定の編集画面（2026-11-11 に PO のログインの画面で窓 1279×1448 で測った・recon §8.1。保存はしていない）。位置・大きさ・角・地の色の実測を成功条件 G60・G61 に使う。Google の絵・名前は使わない。色は PO の言葉（2026-11-11「Googleと色を併せて」）で、予定の画面だけ Google の実測の色（recon §8.6）にする（§3.20）。青の心理の効果は Google の公式の説明が無く未確認で、根拠に使わない。Google の数字は「同じ形・同じ色になったか」の比べる相手で、使われ方の効果の証拠ではない。
- 他社の導入事例の数字は使わない。理由: 今回の成功条件はすべて「Google と同じ画面・同じ操作になったか」で、本物を横に置いて直接比べられるため。

## 8. 維持の仕組み

- 時間割は金型 1 か所。新しい画面が時間割を自前で書いたら、UI の見張り（ADR-144）で止める対象に加えるかを便2 で決める。
- 金型の口ごとに見本帳の例と単体の試験を置く。
- 便6 の見た目は `CalendarView.css` の `.comp-calendar--schedule.comp-calendar--days` の 1 か所だけ。数値の見張り（`frontend/scripts/check-css-hardcoded-values.js`）と色の見張り（`frontend/scripts/check-css-hardcoded-colors.js`）が CI で直書きを止める。
- 便8 の札の色は札の部品の 6 色だけ。`frontend/src/features/schedule/calendars.config.test.ts` が 7 種類の対応と、設定に `#` の色が無いことを CI で毎回確かめる。
- 便9 の月表示の見た目は `CalendarView.css` の `.comp-calendar--schedule.comp-calendar--month` の 1 か所だけ。数値と色の見張り（同上）が CI で直書きを止める。`frontend/src/components/CalendarView.test.tsx` が 1 日の「M月1日」（M は月の数字）・今日の丸・点の 1 行を毎回確かめる。
- 便10 の不具合は `frontend/src/components/CalendarView.test.tsx` が、表示を切り替えても月の時に `views.calendarDays` が渡ることと、FullCalendar の設定の置き換え方（丸ごと置き換え）を CI で毎回確かめる。
- 便11 の線は `frontend/src/components/CalendarView.css` の `.comp-calendar--schedule.comp-calendar--days` の 1 か所だけ。数値と色の見張り（同上）が CI で直書きを止める。jsdom は見た目の規則を計算しないので単体の試験は置かず、FullCalendar の版を上げる時は G37〜G41 の確かめ方で本番の値を読み直す（版は ADR-1065 で 6.1.22 に固定）。
- 便12 の仮の箱の日時は下書き 1 か所から出す（`draftToRange`）。`frontend/src/pages/schedule/schedule-utils.test.ts` と `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` が、箱を動かすと日時が変わり保存まで何も送らないこと・作る小窓に幕が無いことを CI で毎回確かめる。作る小窓の見た目は `.schedule-popover--create` の下と `frontend/src/tokens.css` だけで、数値と色の見張り（同上）が直書きを止める。
- 便13 の全画面の入れ物は金型 「frontend/src/components/FullScreenDialog.tsx」 1 か所（見本帳の例が無いと CI の `check:stories` が止める）。入れる項目の描き方は `frontend/src/pages/schedule/ScheduleDraftFields.tsx` 1 か所で、小窓と全画面が同じ部品を使う。`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` が、Meet が切り替えでなくボタンであること・全画面を閉じても下書きが残り何も送らないこと・全画面の保存が小窓と同じ中身を送ることを CI で毎回確かめる。これらの試験と色・数値・i18n・見本帳の検査は main に入る前の必須の確かめ「Lint & Dark Mode Check (ADR-067)」の中で走り、赤のままでは合流できない。新しい金型は「UI governance gate」も通る。
- 便14 の編集画面の入れ物は金型 `frontend/src/components/EditorPage.tsx` 1 か所（古い金型 FullScreenDialog は消し、同じ働きの金型を 2 つ置かない）。塗りの欄の種類 `editor-filled`・`editor-title` は金型 TextField・Select・Textarea の中だけで定め、新しい `frontend/src/components/editorVariantUsage.test.ts` が決めた場所の外での使用を CI で止める。丸い保存は `frontend/src/components/buttonShapeUsage.test.ts` の使ってよい場所に金型 EditorPage だけを足す。`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` が、直すから編集画面が開き閉じても何も送らないこと・直すの保存が PATCH を送ること・並びの順を CI で毎回確かめる。本番の画面点検 S13（ADR-1051）が毎日 07:00 と配備の後に編集画面を開いて閉じる。
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
- 推奨 2 件と直したこと: 作り方 1 に `dayCellContent` の引数 `(arg: { date: Date; isToday: boolean })` を書いた。作り方 5 に `frontend/src/pages/schedule/SchedulePageImpl.tsx:56` の読み込みの付け替えを書いた。
- schedule-utils の `formatTimeRange` を使うのは 2 か所だけで、専用の試験は無い（審査の grep）。

### 12 回目（便9・G31〜G35）: 2 回目 APPROVE（2026-11-08 15:28〜15:29 UTC・クラウドの Opus・origin/release/schedule-gcal-visual-diff-design 3169bb07d・セッション cse_01HHUUpSQJA9hhx3dQN7t8uG）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ npm pack した 6.1.22 で、点の形は `hasListItemDisplay`（`internal.js:133-139`）、帯の予定は `fc-daygrid-block-event`（`:146`）、点の形の予定は `fc-daygrid-dot-event`（`:157`）。css で帯の予定の点だけが消え、点の形の予定には点が出る。点の色を地の色に替える規則は時間割だけ（`frontend/src/components/CalendarView.css:247-249`）。終日の予定は今の中身のまま（`frontend/src/components/CalendarView.tsx:149-165`）。予定の画面は `renderEventContent` を渡していない（grep 0 件）。ADR の改訂と推奨 2 件も直っている。
- (2) ○ G33 の受入れ・選ばなかった案・ADR の改訂・戻し方・便9 の行が互いに合う。
- (3) ○ 直しは design.md だけ。1 回目に ○ だった所は変わっていない。
- 指摘なし。

### 13 回目（便10・G36）: APPROVE（2026-11-09 02:00〜02:03 UTC・クラウドの Opus・origin/release/schedule-view-switch-crash 1c2b17b51・照合は origin/main a34b0af43・セッション cse_01HHUUpPVCG139vep4NhSB8m）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ npm pack した 6.1.22 で、`@fullcalendar/react` `dist/index.js:76` は `resetOptions` を changedOptionNames なしで呼ぶ。core `index.js:1366-1367` は設定を丸ごと置き換え、`:366` が `parseViewConfigs(optionOverrides.views)`、`:1561-1563` が throw。a34b0af43 の `frontend/src/components/CalendarView.tsx:194` で `views` は `daysProps` の中だけ。/tmp で core を直接動かすと、今の形は dayCount 1・3・7 のどれも同じ誤りになった。
- (2) ○ 直した形では週→月→週→月が 3 通りとも通り、最後は `dayGridMonth`。月の時に dayCount を 3 に変えてから `calendarDays` へ切り替えても期間は 3 日。`monthProps` には触れない。
- (3) ○ 今の差し替え（`captured.props`）と T5 の読み方で書ける。core の 2 つの文は中身に在る。
- (4) ○ `frontend/src/pages/schedule/SchedulePageImpl.tsx:961-964,990,1547`・`frontend/src/lib/query/apiQuery.ts:5,21,28` と合う。
- (5) ○ 推奨 2 件と直したこと: ①R10-4 の「1 回目」を「その月の写しが無い時」に書き換え、30 分以内に同じ月を開いていれば 1 回目でも落ちる（推論・本番未確認）と書いた。②包み（react）側の丸ごと置き換えも見張る: カード §3-2 に `readPackageFiles('react/dist', ...)` で `dist/index.js` の `this.calendar.resetOptions(Object.assign(Object.assign({}, this.props)` を見る 1 行を足した（関数は変えない・`node_modules/@fullcalendar/<pkg>/` を読むため）。

### 14 回目（便11・G37〜G41）: APPROVE（2026-11-09 05:43〜 UTC・クラウドの Opus・origin/release/schedule-gcal-borders-design aa2dce8c5・照合は origin/main 1ca6dbf38・セッション cse_01HHUUpR2iMPQkS9eqyvoEGt）

- 結果は返事の本文で全部読んだ（途中で切れていない）。
- (1) ○ `frontend/src/components/CalendarView.css:16,180-288,182`・`frontend/src/tokens.css:74,75,400,423,669` が実物と合う。npm pack した 6.1.22 で、td/th と scrollgrid の線（core `internal-common.js`）・divider の `padding:0 0 2px`・cushion の `padding:0 4px`（timegrid）・`overflow-y`（`internal-common.js:7055` の `forceYScrollbars ? 'scroll'`）を確かめた。
- (2) ○ /tmp の写しに規則を足し、FullCalendar の global 版の週を Playwright で読んだ。上の行・左上の角・時刻の列・「終日」の升目は 4 辺 0px。`::after` は幅 8px・上の線 1px。cushion の右のあきは 12px で、文字の右の端 52.5 は列の右の端 53 以下。divider は高さ 1px・下の線 1px だけ。slot-lane の上 1px・timegrid-col・終日の日の升目の線は残った。divider の規則の詳細度 (0,4,0) は `.fc-scrollgrid-section > *` の (0,3,0) に勝つ。
- (3) ○ 同じ写しで月表示の値（scrollgrid・曜日の行・日の升目・区切り・scrollbar-color）が足す前と後で全部同じ。
- (4) ○ `check-css-hardcoded-values.js` は PASSED。新トークンは var() で、置き場所は `--schedule-gridline-w` の次の行。
- (5) ○ 抜けなし。推奨 1 件: 短い線は 1 時間 1 行（`frontend/src/components/CalendarView.tsx:194`）が前提 → §3.16 の心配と対処に 1 行足した。

### 15 回目（便12・G42〜G50）: 1 回目 REVISE（2026-11-09・クラウドの Opus・origin/release/schedule-gcal-create-drag 4a98e7ff7・照合は origin/main・セッション cse_01HHUUpQ8FDPRcA2kozeeKvS）

- 結果は返事の本文で全部読んだ（実行記録では途中で切れたので、セッションの画面で全文を読んだ）。行番号のずれ無し。heroicons の 3 つの絵・ADR の照合は ○。
- 直す 1: 仮の箱の文字が固定の「(タイトルなし)」のまま（`:1262`）で G45「箱にも出る」を満たさない → §3.17 作り方 1 に `draft.title.trim() || t("schedule.noTitle")` と試験を足した。
- 直す 2: 始まりだけ直すと終わり≦始まりになり箱が消え、G47 を確かめられない → 作る小窓では長さを保って終わりもずらす（`shiftDraftStart`）。G47 の確かめ方と試験を直した。
- 直す 3: 日時→下書きの変換が 2 か所になる・長さを変えたとき終日の箱が時刻つきに化ける（`frontend/src/components/CalendarView.tsx:313` は終日を渡さない）→ `rangeToDraftDates` 1 つにし、仮の箱は `draft.allDay` を使う。往復の試験を足した。
- 直す 4: FullCalendar 6.1.22 は同じ日の中の動かし・長さ変えで要素を作り直さず harness の style だけ変える（timegrid `internal.js:765`）ので、`eventDidMount` だけでは四角が古い → harness の style を `MutationObserver` で見る・離した後に測る・見えないときは null・unmount は同じ要素のときだけ忘れる。G45 に同じ日の中の動かしを足した。
- 推奨 5〜9（`calendarEvents` を useMemo・つかんでいる間は返さない／外の押しは capture と composedPath・日付の見出しを押すと閉じる・消す所の一覧／月の 1 日押しは今のまま押した所の横で G43 に足す／G42②・G50 に合格の値／§4 の便12 の行に PO 承認の後に着手）は全部入れた。消す所は審査の挙げた行ではなく、`grep -n setPendingRange` の実物（`:952,1223,1244,1249,1590`）で書いた。

2 回目: APPROVE（2026-11-09 14:04〜14:06 UTC・クラウドの Opus・origin/release/schedule-gcal-create-drag 10e31b8e5・照合は origin/main d9d0e1d8・セッション cse_01HHUUpRJwvgNN1Y7yZUf1LZ）
- 結果は返事の本文で読んだ。1 回目の 9 件は全部 ○（行つき）。pendingRange の 5 か所・幕・saveEvent・日付と時刻の欄・patchMoved は origin/main d9d0e1d8 の実物と一致。c6ce79fb6 から frontend の差は無し。
- npm pack した 6.1.22 で eventDragStart（interaction `index.js:1286`）・eventDragStop（`:1371`）・eventResizeStart（`:1595`）・eventResizeStop（`:1663`）・eventDidMount／eventWillUnmount（core）が在る。種類の欄は普通の `<select>`（`frontend/src/components/Select.tsx:93`・portal なし）なので外の押しの判定で誤って閉じない。
- 推奨 1: useMemo の依存に祝日・持ち主の色・t が抜けていた → 作り方 1 を「中で使う値すべて」に直した。
- 推奨 2: 月表示・週の終日の段は daygrid の harness で、始まりの列が同じ長さ変えは style だけ変わる → 作り方 4 ② の見張る相手に `.fc-daygrid-event-harness` を足した。

### 16 回目（便13・G51〜G57）: 1 回目 REVISE（2026-11-10 17:36〜17:38 UTC・クラウドの Opus・origin/release/schedule-gcal-full-edit-design f96c28db4・照合は origin/main 768b3db1・セッション cse_01HHUUpRAuVAawvQRSz2qLo1）

- 結果は実行記録の本文で読んだ。§3.18 の引用行（541-552・309-324・612-630・1186-1225・1318・1432-/1477・1089・1649・1752・:95・:1201・:327-339）は実物どおり。小窓を描かない間も popover・draft・仮の箱・anchor は残る。全画面の中の部品で外の押しの誤判定は無い。saveEvent の成功・失敗の道に穴は無い。選ばなかった案の理由は実物どおり。
- 直す 1: 項目の並びが G53・作り方 2・実物で 3 通り → 実物の並び（日時:445→種類:515→Meet:543→社員:556→場所:569→説明:590）に揃えた。
- 直す 2: 終日・社員にも見せるの `<Toggle>`（:449・:559）が残るので「switch が 0 個」は必ず× → 「名前が Google Meet の switch が 0 個」に直した。
- 直す 3: 押した元の「その他のオプション」は小窓と一緒に消える → G56 を「閉じると作る小窓の題名へ」に直し、試験に足した。
- 推奨 4〜7（近道は今も `windowOpen` で止まる旨／金型の Esc は変換中は何もしない・試験／週の外へ日付を変えたときの動きを心配と対処に／× で `error` を消す・`meetAvailable` を 1 つの変数で両方へ）は全部入れた。

2 回目: REVISE（2026-11-10 17:44〜17:45 UTC・クラウドの Opus・0dd26de2a・照合は origin/main 263889d6・セッション cse_01HHUUpSEkRwbzNiSnb7zgrK）
- 結果は実行記録の本文で読んだ。1 回目の 7 件は全部 ○（行つき）。768b3db1 から 263889d6 までに予定の画面・Modal・useFocusTrap の差は無し。
- 直す 1: G51 の「名前が Google Meet の switch」は Testing Library の完全一致で今も直した後も 0 個になり、切り替えが残っても ○ になる（今の名前は `schedule.addMeet`「Google Meet を付ける」・`frontend/src/pages/schedule/SchedulePageImpl.tsx:548`）→ G51 と試験を `queryByRole("switch", { name: /Google Meet/ })` が null に揃えた。

3 回目: APPROVE（2026-11-10 17:49〜17:50 UTC・クラウドの Opus・8a33cc85a・照合は origin/main 5dc69e7・セッション cse_01HHUUpRAdMdDJ9ZagZTVXTK）
- 結果は実行記録の本文で読んだ。必須 0 件・推奨 0 件。
- 2 回目の直す 1 は ○: G51（`:123`）と §3.18 の試験（`:738`）が同じ書き方。今の切り替えの名前は ja「Google Meet を付ける」・en "Add Google Meet"（どちらも `frontend/src/locales/ja.json:3351`・`frontend/src/locales/en.json:3351`）で、今は ×・直した後は ○ になり判定できる。終日（`:449`）・社員にも見せる（`:559`）の切り替えは当たらない。
- 263889d6 から 5dc69e7 までに予定の画面と言葉の表の差は無し。
- 未確認: 試験そのものは流していない（読むだけの役）。実装の CI で確かめる。

### 17 回目（便14・G58〜G64）: 1 回目 REVISE（2026-11-11 03:56〜04:02 UTC・クラウドの Opus・origin/release/schedule-gcal-editor-page 3ff046d37・セッション cse_01HHUUpTA8twprbc7uYpw2mz）
- 審査役はカードの CSS とトークンを写しに当てて Chromium で測り、stylelint と色・暗い表示の点検を流した。
- 直したこと:
  - (1) 重: 日時の 4 つの欄が共通の `width: 100%`（`frontend/src/components/FormField.css:50`）で 4 段に積まれ G60 を満たさない → カード §3 に日付と時刻の `editor-filled` だけ `width: auto` の規則を足した。G60 に「5 つが同じ 1 段（上端の差 4 以内）」を足した。
  - (2) 重: `frontend/src/components/editorVariantUsage.test.ts` が金型 `frontend/src/components/EditorPage.tsx` の説明の文に当たって落ちる・§3.19 と §8 の食い違い → カード §8 の使ってよい場所に `frontend/src/components/EditorPage.tsx` を足した。
  - (3) 中: × の真ん中が x48 で G60 の x52±4 のぎりぎり → × を列の中で左に寄せ、列の左に `--space-4` の余白（左端 x32 は Google と同じ・真ん中 x50）。G60 に左端 x32±4 を足した。
  - (4) 中: 日時の段の上端が y76 で G60 の y92±8 の外 → 札の上の余白を `--space-8` に（20＋40＋32＝92）。
  - (5) 中: 丸いボタンはログインだけと書いた場所は `docs/specs/design-system/design.md:260`・`:276`・`:537`・`:1115`（`:262` はトグルの行）。`frontend/src/components/Button.tsx:29` の説明も古くなる → 例外の 1 文の置き場所と Button の説明 2 行を直した。
  - (6) 軽: 行番号のずれ（FullScreenDialog の useEffect は `:49-79` の 3 つ・Button の口は `:30`・`tokens.css` は `:415`・`--radius-sm` は `:96`・予定の画面の題名の枝は `:394-406`・`schedule.css` は説明を含め `:528-537`）を直した。
  - (7) 軽: 新しい試験の名前 H1〜H5 が祝日の試験（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx:1037`・`:1048`・`:1057`）とぶつかる → EP1〜EP5 に。
  - (8) 軽: Checkbox の `onChange` は出来事を受け取り、Toggle は真偽を受け取る（`frontend/src/components/Checkbox.tsx:25-26`・`frontend/src/pages/schedule/ScheduleDraftFields.tsx:121-126`）→ カード §4 に `event.target.checked` から読む式を書いた。
- 審査役の最後の文は 8 件目の途中で切れていた。残りは 2 回目の審査で全部書いてもらう。

### 17 回目 2 回目（2026-11-11・便14 の設計・クラウドの Opus architect・commit 0ea920725）: REVISE

- 1 回目の 8 件のうち 7 件は直っていた。審査役が窓 1279 の Chromium でカードの CSS を写しに当てて測った: × 左端 x32・真ん中 x50、題名 x80 幅 594、保存 x706、日時の段の上端 y92、札 x16 幅 636、札の中の欄 x80（幅 556）、窓 390 ではみ出しなし。stylelint と CSS の検査 8 本は通った。
- 指摘と直し:
  - (1) 重: 日時の 5 つ目（終わりの日）が x80 y140 の 2 段目に落ちる。lead の幅の上限（652）から左の余白 64 を引くと 588 で、5 つに要る 622 に足りない → lead の幅の上限を消した（カード §2-2）。
  - (2) 中: 「〜」は上端 y99 で欄と 7 ずれ、G60 の「上端の差 4 以内」が × になる → 「〜」に `schedule-editor-dates__sep`（`inline-flex`・高さ `--space-10`）を付けた（カード §4・§5）。
  - (3) 中: 「DraftMeetField が null でないときだけ包む」は親が描く前に知れない → page のときは DraftMeetField 自身が `EditorPageRow` で包む形に替えた（カード §4・§5）。
  - (4) 軽: `.schedule-full-editor .schedule-popover__line` を消すと Meet のボタンの文字が真ん中に寄る → `.schedule-editor-meet .schedule-popover__line { justify-content: flex-start; }` を残す（カード §5）。
  - (5) 軽: 種類の選ぶ欄で文字と矢印が 4px 重なる → `.comp-select__control.comp-select--editor-filled { padding-right: var(--space-8); }` と判定（32px）をカード §3 に書いた。
  - (6) 軽: 行番号のずれ（題名の規則 `:393-409`・`width: 100%` は `FormField.css:51`・鉛筆 `:321-332`・`:1054`/`:1163`/`:1175` は直す対象外）を直した。

### 17 回目 3 回目（2026-11-11 04:22〜04:27 UTC・便14 の設計・クラウドの Opus architect・commit ed0bbbbe7・セッション cse_01HHUUpSXv3oAtkVqVS9RXjY）: REVISE

- 2 回目の 6 件のうち 5 件は直っていた。審査役が写しで測った: 窓 1279 で × 左端 x32・真ん中 x50、題名 x80 幅 594、保存 x706、日時の 5 つは全部 y92・高さ 40 の 1 段（x80〜x702）、札 x16 幅 636、札の中の欄 x80 幅 556、種類の欄の右余白 32px、Meet の文字は左寄せ、欄は高さ 40・角 4px・枠 0。窓 390 ではみ出しなし。流れ（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1568`・`:1007-1009`）と S13 は成り立つ。
- 指摘と直し:
  - (1) 重: 種類の欄の右余白の規則を `:focus` の規則より後ろに置くと stylelint `no-descending-specificity` が 1 件落ちる（実測 `FormField.css 461:1`）→ カード §3 の塊の 2 つ目（共通の見た目の規則のすぐ後・`:focus` より前）に移した。審査役がこの置き方で stylelint 0 件・右余白 32px のままを実測。
  - (2) 軽: Button の行番号 → 説明「ログイン画面だけで使う」は `frontend/src/components/Button.tsx:28`・口 `shape` は `:29` に直した（カード §1・§2-1）。
  - (3) 軽: 小窓の本体は `frontend/src/pages/schedule/SchedulePageImpl.tsx:380-420` に直した（カード §7）。

### 17 回目 4 回目（2026-11-11 04:34〜04:39 UTC・便14 の設計・クラウドの Opus architect・commit 3aef82a37・セッション cse_01HHUUpPga7mkexiNwyoAsSx）: APPROVE

- 3 回目の 3 件は 3 件とも直っていた。審査役が写しにカード §2-2・§3・§5・§6 をカードどおりの順で入れ、`npx stylelint "src/**/*.css"` が rc=0（0 件）。窓 1279 で × 左端 x32・真ん中 x50、題名 x80 幅 594、保存 x706（角 9999px）、日時の 5 つは全部 y92・高さ 40、札 x16 幅 636、札の中の欄 x80 幅 556、欄は高さ 40・角 4px・枠 0・地 rgb(235,239,248)、種類の欄の右余白 32px、Meet の文字は左寄せ。窓 390 で scrollWidth 390。
- 流れ（直すから開く・× と Esc でカレンダーに戻る・保存成功で閉じる・失敗で開いたまま）と S13 は成り立つ。写しで dark-parity（132）・css-values・css-var-fallbacks・css-colors・color-token-sync・stories・page-size・page-layout・page-folder・i18n が緑。EditorPage.tsx の型の誤り 0 件（クラウドに生成物の無い api/generated/schema 由来を除く）。check-new-tokens は CI と PR 本文で確かめる。
- 軽い指摘 3 件と直し（この commit）:
  - (1) `frontend/src/pages/schedule/ScheduleFullEditor.tsx:3` の説明の文に `FullScreenDialog` が残るのにカードに直す指示が無い → カード §2-4 に 1 行足した。
  - (2) §4 の便14 の行の「例外 3 文」は実際は 5 か所 → 「例外 5 文」に直した。
  - (3) R14-4 の行番号 `:380-418`・`:1588` が古い → `:380-420`・`:1587` に直した。
- 判定: APPROVE。残りは PO の承認（新しい金型・古い金型を消す・角の小さい塗りの欄・丸い保存・直すときも全画面）。

### 17 回目 5 回目（2026-11-11 05:50〜05:55 UTC・便14 の色の設計 G65〜G67・クラウドの Opus architect・commit c9ed86422・セッション cse_01HHUUpRuPc2v1UTKfPcYkYD）: REVISE

- 写しで Chromium に入れて測り、明るい・暗いのページの地・札・線・日の数字・今日の丸・小さい暦・今の時刻の丸・小窓・ボタンが G65・G66 の値と一致。色の見張り 5 つ（css-hardcoded-colors・dark-parity 145・css-var-fallbacks・css-hardcoded-values・color-token-sync 37）が緑。文字と地の明るさの比はすべて 4.5 以上。
- 指摘と直し（この commit）:
  - (1) 重: カードどおり作ると守り手が自分で落ちる（`index.css` の説明の文に `.gcal-colors`・EP6 の試験 `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` が許す場所の外）→ index.css の説明の文 3 か所から札の名前を外し、許す場所に `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` を足した（カード §6-2・§8・§11）。
  - (2) 中: 設計 §3.20 作り方 8 とカード §8 の許す場所が食い違う → 作り方 8 をカード §8 と同じ一覧に直した。
  - (3) 中: ページの題名の色 `--role-page-title-color` を決め直していない（R14-9 の洗い出しで `pages-layout.css` を見落とし）→ 札に 1 行足して 25 行に。G65・G66 に題名の文字を足した。ほかの文字の役のトークン 4 つは使う class が予定の画面に 0 件と確かめた。
  - (4) 軽: カード §1 の「色の 6 行」→ 5 行に直した。
  - (5) 軽: 今の時刻の丸は `::before` で読むと G65 に書いた。暗い表示の表示の選びの選んだ方の文字（Google 白・設計 rgb(194,231,255)）は受け入れた違いとして G66 と ADR-1074 に書いた。指摘 (5) の残りと後ろの返事は記録の上で約 1300 字切れて読めていない（まだ確かめていません）。6 回目で見直してもらう。

### 17 回目 6 回目（2026-11-11 06:05〜06:11 UTC・便14 の色の設計 G65〜G67・クラウドの Opus architect・commit 0a2712c7d・セッション cse_01HHUUpSJg55RzQbJ3JWBFgF）: REVISE

- 5 回目の指摘 5 件はすべて直っていた（index.css の札の名前 0 件・札 25 行・許す場所の一致・カード §1・`::before` と受け入れた違い）。写しで Chromium 窓 1279 に入れ、G65・G66 の全部の点（題名の文字を含む）が一致。色の見張り（css-colors・dark-parity 145・var-fallbacks・css-values・color-token-sync 37）と stylelint が緑。未使用トークンは作る前と同じ 17 件。予定の試験と守り手 169 件が通った（見本帳の試験 1 ファイルは写しの環境で動かず未確認）。明るさの比は最も低い組で 4.92。:root の決め直しの漏れ無し。
- 指摘と直し（この commit）:
  - (1) 中: 守り手の「1 件以上見つかる」確認が試験のファイル自身の文字で必ず通る（写しで探し方を壊しても通った）→ 数えるのを試験のファイル以外にし、(1) は `tokens.css`・`frontend/src/pages/schedule/SchedulePageImpl.tsx`、(2) は `index.css`・`tokens.css` が見つかることを確かめる形に（カード §8・作り方 8）。
  - (2) 軽: `.schedule-page` が文字の色を決めていないので、色を決めていない文字が body の古い色を受け継ぐ（写しの素の文字で明るい rgb(26,32,44)・暗い rgb(241,245,249) を実測）→ `.schedule-page` に `color: var(--text-primary);` を足す（カード §1 は 6 行・§6-3・作り方 6）。G65・G66 にページの文字の色を足した。


### 17 回目 7 回目（2026-11-11 06:16〜06:25 UTC・便14 の色の設計 G65〜G67・クラウドの Opus architect・commit 710fb0a3d・セッション cse_01HHUUpRRkCd4mfDR7jpk4uQ）: APPROVE

- 6 回目の指摘 2 件は直っていた。カード §8 の守り手を写しに作り、今の形で 2 件とも通り、探し方を壊すと落ち、予定の設定の画面で使うと落ちた。カード §1 の 6 行・§6-3・作り方 6・G65・G66 も揃っていた。
- 足した `color` で変わったのは、文字の色を自分で決めていない入れ物 24 個だけ（明るい rgb(26,32,44)→rgb(31,31,31)・暗い rgb(241,245,249)→rgb(227,227,227)）。色を自分で決めている文字は 102 個のうち 0 個が変わった。
- G65・G66 の全部の点が明るい・暗いとも一致（写しの Chromium 窓 1279）。色の見張り（css-colors・dark-parity 145・var-fallbacks・css-values・color-token-sync 37）と stylelint が緑。未使用トークンは 1 個増えるが、カード §3 の FormField.css で使うので作った後は消える。components と予定の試験 70 ファイル・1085 件が通った。
- 予定の設定の画面と取引先の一覧は、明るい・暗いとも作る前と後で全部の要素の色が同じ（偽の API の答えなので要素は 8 個と 36 個）。
- 明るさの比: 新しく決めた色の文字で最も低いのは 6.39。予定の箱の白い文字は 4.51 で作る前と同じ。詳しくの小窓の札は明るい表示で 4.01 だが、作る前も 4.01 でこの設計で生じた物ではない。
- 未確認: 編集画面はカードの CSS を写した仮の DOM で測った（全部一致）。本物の EditorPage は実装の後に G58〜G67 で測る。
- 指摘 0 件。

### PO の承認（2026-11-11・便14 の実装）

- PO に聞いた中身: 予定の編集画面を作るときも直すときも画面いっぱいに開く・中身は左寄せ・角の小さい灰色の塗りの欄・丸い保存・詳しくの小窓の中で直す形を無くす・予定の画面だけ地と文字と線と青を Google の色に（明るい・暗い）・ほかの画面は変えない・丸い欄と丸い保存は外で使えないよう機械で止める。Google と違うまま残る所（保存が 4px 低い・暗い表示で予定の箱の色は今のまま・表示の切り替えと右クリックの表は今の色・招待する人と通知と繰り返しは作らない・青の心理の効果は公式の説明が無く根拠にしない）。作った後に本番で 10 項目（G58〜G67）を測り、毎朝の点検 S13 を見る。
- PO の答え（原文）: 「1」（選択肢「1. この設計で作り始める【おすすめ】」）
- これで新しい金型 EditorPage・古い金型 FullScreenDialog を消す・塗りの欄の種類・丸い保存・範囲の札 `.gcal-colors` と `--gcal-*` トークンを承認とする（ADR-144）。


## 10. 追補: 色の数の見張りの例外（2026-11-11・便14 の PR の CI で見つかった）

### 10-1. 何が起きたか（事実）

- 便14 の PR の CI `guard-hex-increase`（`.github/workflows/design-token-guard.yml:20` が `scripts/check-design-token-ratchet.sh` を流す）が失敗した。出力は `frontend/src/index.css 171->197`。ほかの変更ファイルは増加 0。今の merge-base（f3ff550）と比べると `172->198`（クラウドの審査役が 2026-11-11 に流した結果）。どちらも増えた数は 26。
- 増えた 26 個の hex は全部 `--gcal-*` の 13 個の名前の行（明るい `:root` と暗い `:root.force-dark` に 13 行ずつ）。1 行に 1 宣言・`--gcal-<名前>: #hex;` の形。それ以外の行の hex 増加は 0（`git diff origin/main...HEAD -- frontend/src/index.css` の追加行を数えた）。
- 21 種の新しい値のうち、origin/main の index.css に同じ値があるのは 1 種だけ。今の色の素材で代えられない。
- この見張りが入った 2026-09-05 以降、index.css の hex の数は増えたことが無い（origin/main の index.css の各版を数えた: 190→188→179→179→172→172→172→171）。
- 設計の時にこの見張りを確かめ忘れた（設計漏れ）。§9 の PO の承認にはこの件が入っていない。
- 見張りの例外は `scripts/check-design-token-ratchet.sh:12` に「変更はPO承認必須」と書かれている。

### 10-2. 考えた案

| 案 | 中身 | 採るか | 理由 |
|---|---|---|---|
| A | 見張りに、index.css の `--gcal-*` 13 個の名前の 1 行 1 宣言だけを数えない例外を足す | 採る（PO の選択「1」） | 色の正本は index.css（`docs/specs/design-system/design.md:794`）のまま。明るい・暗いの対の検査 `frontend/scripts/check-dark-parity.js:19`（index.css だけを読む）も効いたまま。名前を 13 個に固定し、1 つの名前につき 2 行（明るい色と暗い色の 1 組）までしか除かないので、除ける hex は最大 26 個。14 個目の名前・同じ名前の 3 行目・他の色の増加は今どおり止まる |
| B | index.css 全体を見張りから外す | 採らない | 今後ほかの色が増えても止まらない |
| C | `--gcal-*` を tokens.css へ移す（前例: `docs/handoff/inventory-table-nine-columns/design.md:166` の追補2。予定の分類の色 `--cal-*` も tokens.css にある） | 採らない | 見張りは変えずに済むが、`check-dark-parity.js` は index.css しか読まないため明るい・暗いの対が機械で守られなくなる。色の正本は index.css という決まり（design-system design.md:794）からも外れる |
| D | 色を `rgb()` で書いて数えられないようにする | 採らない | 見張りの抜け道で、決まりの趣旨に反する |
| E | Google の色をやめる | 採らない | PO の願い「予定の色だけどGoogleと色を併せて」がかなわない |

### 10-3. 作り方（案 A）

- `scripts/check-design-token-ratchet.sh`: 例外の対象を「ファイル `frontend/src/index.css` の中で、名前が次の 13 個のどれかで、1 行に宣言が 1 つだけ（`--gcal-<名前>: #hex;` の後ろは空白だけ）の行」に限る。さらに 1 つの名前につき、ファイルの先頭から数えて 2 行目までだけを除く（明るい `:root` と暗い `:root.force-dark` の 1 組）。3 行目からは数える。ほかのファイル・ほかの行・1 行に 2 つ以上の宣言がある行は今どおり数える。
  - 2 行までに限る理由: 審査 1 回目（§10-7）で、限らないと同じ名前をほかの場所に書き直して hex をいくらでも増やせると分かったため。
  - 13 個: surface・surface-lowest・surface-container・surface-filled・on-surface・on-surface-variant・outline-variant・gridline・primary・on-primary・secondary-container・on-secondary-container・now
- `scripts/tests/test-design-token-ratchet.sh`（新規）: 使い捨ての git の倉庫を作り、見張りを流して結果を確かめる。場合は §10-4 の表。
- `.github/workflows/design-token-guard.yml`: 起動の条件に `scripts/check-design-token-ratchet.sh` と `scripts/tests/test-design-token-ratchet.sh` を足す（見張り自身だけを変えた PR でも動くように）。見張りの前に試験を流す 1 段を足す。job 名 `guard-hex-increase` は変えない。

### 10-4. 成功の条件（G68）

| 基準 | 検証方法 |
|---|---|
| 便14 の PR の `guard-hex-increase` が PASS | PR の CI の結果 |
| 13 個の名前の 1 行 1 宣言を index.css に足しても PASS | 試験の場合 1 |
| 14 個目の名前 `--gcal-extra: #123456;` を足すと FAIL | 試験の場合 2 |
| `--gcal-surface: #ffffff; --x: #000000;` の 1 行を足すと FAIL | 試験の場合 3 |
| index.css にほかの名前の hex を足すと FAIL | 試験の場合 4 |
| index.css 以外の CSS に `--gcal-surface: #ffffff;` を足すと FAIL | 試験の場合 5 |
| hex を足さない変更は PASS | 試験の場合 6 |
| 26 行に加えて同じ名前の 3 行目（`.x { --gcal-primary: #ff0000; }`）を足すと FAIL | 試験の場合 7 |
| 同じ名前を 3 行足すと FAIL | 試験の場合 8 |
| 便14 の枝の index.css で除かれるのはちょうど 26 行、残る hex は 172 個（main と同じ） | 変えた見張りの関数を枝の index.css に当てて数える |
| 試験が CI で流れる | design-token-guard の job の記録に試験の段がある |

### 10-5. 影響と戻し方

- 影響: この見張りを使うのは `.github/workflows/design-token-guard.yml:20` の 1 か所だけ（`git grep -n check-design-token-ratchet -- .github` の結果）。`scripts/` を触るため、この PR は GO 記録が要る種類になる（`scripts/check-process-artifacts.js:1025`）。
- 戻し方: この追補のコミットを戻す。戻すと便14 の色の追加は見張りで止まる。

### 10-6. PO の承認（2026-11-11）

- PO に聞いた中身: 見張りに例外を 1 つ足す（Google の色の名前が付いた色だけ、色の置き場で増えてもよい）。画面の色の直書きは今どおり止まる。直しはクラウドの担当が作り、審査を通して合流する。
- PO の答え（原文）: 「1、推測は禁止して事実確認を怠らずに確実性を重視して最も効果があり、現状把握の粒度が細く、精度が高いエビデンスを確立して安全に進めてくれ。…確立したなら進める。」
- 案 C の前例（tokens.css）は PO に聞いた後で見つけた。§10-2 の理由で案 A のままとする。

### 10-7. 審査（クラウドの architect・Opus）

- 1 回目（2026-11-11・a5970ce3b）: REVISE。正規表現は index.css の 26 行ちょうどに当たり、変えた見張りは main との合流後の形でも PASS、試験 6 件も期待どおり。ただし例外が「名前と 1 行の形」だけで決まり、同じ名前をほかの場所に書き直すと hex をいくらでも増やせる（審査役が場合 7・8 を作って PASS してしまうことを確かめた）。
  - 直したこと: 1 つの名前につき先頭から 2 行までだけ除く形に変えた（§10-2 案 A の理由・§10-3・§10-4 の場合 7・8、カード §2・§3）。PO の承認（§10-6）より狭める直しなので、承認の範囲の中。試験は終了コードを `|| rc=$?` で受けると明記した。
  - Opus が手元で確かめたこと: 直した見張りを便14 の枝に流すと `PASS: 対象25ファイル・増加なし`・終了コード 0。直した関数を枝の index.css に当てると除かれたのは 26 行、残る hex は 172 個。8 件の試験は手元の見張りの都合で流せないため、2 回目の審査で流してもらう。
- 2 回目（2026-11-11 12:05〜12:08 UTC・d2df0a970・セッション cse_01W47tdgVTJ5y8REATtyZ4MT）: APPROVE。
  - カード §2 を入れた見張りは merge-base（f3ff550）比で `PASS: 対象25ファイル・増加なし`・rc=0。今の見張りは `172->198` で FAIL。除かれたのは 26 行、残る hex は 172 個。
  - カード §3 の試験 8 件: 変えた見張りで 8 件とも ok。今の見張りでは場合 1 だけが NG。mawk・gawk の両方で同じ結果。
  - 漏れの探り（名前の後ろの空白・タブ・空白なし・CRLF・大文字・前に別宣言・後ろのコメントの hex・似た名前）: どれも 3 行目は FAIL になり、hex を増やせる形は無かった。
  - 軽い指摘 3 点（結果は変わらない）: カード §0 の `git pull` はクラウドでは使わない／場合 5 を足す位置／試験は一時の倉庫に cd してから流す。カードに一言ずつ足した。

## 11. 便14 の本番の測定（2026-11-11 12:55〜13:10 UTC・Opus・本番 app.salesanchor.jp・読むだけ）

- 前提: 便14 は 2026-11-11 12:47 UTC に main へ合流し、本番への反映（Deploy to VPS run 43023547977・本線 5a137d208）は成功。保存と会議に入るボタンは押していない。暗い表示は `html` に `force-dark` を足して読み、読んだ後に外した（設定は保存していない）。
- 窓: 窓の大きさの変更が効かず、表示の幅は 1845×1448 で測った。中身は左寄せなので G60 の位置は幅に左右されない。

| 条件 | 結果 | 本番で読んだ値 |
|---|---|---|
| G58 | ○ | 作る小窓の「その他のオプション」で編集画面（名前「予定の編集」）。Esc で作る小窓に戻る。詳しくの小窓の「予定を編集」で題名・日時（2026-11-09 21:00〜22:00）・種類が入る。× で閉じると編集画面 0・小窓 0・予定は 1 件のまま |
| G59 | ○（見える部分） | 詳しくの小窓の中の入力欄 0 個。PATCH は保存を押さないため単体試験（CI 緑）で確かめた |
| G60 | ○ | × 左端 32・真ん中 50／題名 x80・幅 594・24px／保存 左端 706／日時 5 つと「〜」の上端すべて 92／札 x16・幅 636・角 28px・頭「予定の詳細」／絵の真ん中 48（5 行）／欄の左端 80・場所の幅 556 |
| G61 | ○ | 日時 4 つ・場所・種類・説明: 高さ 40（説明 140）・角 4px・上枠 0・地 rgb(233,238,246)（`--comp-input-filled-bg` #e9eef6）・左余白 16px。題名は下線 2px だけ。終日は checkbox・switch の「終日」0 個 |
| G62 | ○ | 日時の段→終日→札（Meet・場所・種類・社員にも見せる・説明） |
| G63 | 一部未確認 | 暗い表示は G66 で ○。幅 390 は窓の大きさが変えられず、枠に入れる方法も別の出どころとして止められ、本番では測れていない（CI の画面の試験は緑） |
| G64 | ○ | `git grep FullScreenDialog origin/main -- frontend` 0 件。合流後の本番の画面点検（prod-ui-check run 43024147141）12 件合格・S13 合格 |
| G65 | ○ | 明るい表示の全点が一致（ページ 248,250,253・文字 31,31,31・題名 31,31,31・表の札 255・線 #dde3ea・日の数字 31,31,31・今日の丸 11,87,208／白・小さい暦 11,87,208・今の時刻 219,55,45・小窓 240,244,249・小窓の保存 11,87,208／白・編集画面 248,250,253／札 白／塗りの欄 233,238,246／保存 11,87,208） |
| G66 | ○ | 暗い表示の全点が一致（ページ 27,27,27／227・題名 227・表の札 19,19,20・線 #333537・日の数字 227・今日の丸 168,199,250／6,46,111・小さい暦 168,199,250・今の時刻 245,94,87・小窓 30,31,32・保存 168,199,250／6,46,111・編集画面 27,27,27／札 19,19,20／塗りの欄 40,42,44） |
| G67 | ○ | 予定の箱 rgb(26,115,232)・文字白。予定の設定の画面と顧客管理の画面の主ボタンは rgb(30,58,138)、`.gcal-colors` は 0 個 |
| G68 | ○ | 便14 の PR の guard-hex-increase は試験 8 件 ok と PASS（§10-7） |

- 残り: G63 の幅 390 の本番の測定。毎朝の画面点検 S13 は 2026-11-12 07:30（日本時間）にも見る。

## 12. 便15: 予定の繰り返し（2026-11-12・Opus・設計案）

状態: 設計案。設計審査は審査7 で APPROVE（§12.13・2026-11-11 22:00 UTC）。そのあと PO の問い「繰り返しを消すときの動きも把握したか」（2026-11-12）で、消すときの Google 側の抜けが 2 つ見つかった。Google で消し方を測り（recon §9.5 U6）、§12.2 G74・§12.5・§12.7 を直した。審査8〜審査14 の REVISE（§12.13）を直し、審査15 で **APPROVE**（2026-11-12 00:02 UTC・対象 ac42be185）。審査15 の推奨 1 件も直した。成功条件 G69〜G79 は **PO 承認済み**（2026-11-12 選択「1」・§12.14）。実装は未着手（次は実装カード）。PO の範囲の承認は済み（2026-11-12 選択「1、」）。根拠は recon §9。ADR-1075（Proposed）。

### 12.1 目的

- PO の言葉: 繰り返しを付ける（選択「1」）。範囲は Google の決まった選び方 6 つと、直す・消すときの 3 択（この予定／これ以降／すべて）。自由に決める選び方（Google の 7 番目）は後で。
- 奥の目的: 毎週の会議や月に 1 回の締めを 1 回の入力で済ませ、Google カレンダーと同じ手の動きで直せるようにする。
- 利用者に見える変化: 編集画面の終日の右に「繰り返さない」の選ぶ欄が出る。選ぶと日・週・月の表示に回が並ぶ。回を直す・消すと「この予定／これ以降のすべての予定／すべての予定」を聞かれる。

### 12.2 成功条件（PO が画面で ○× を付ける・2026-11-12 PO 承認済み）

| # | 成功条件 | 確かめ方 | 根拠 |
|---|---|---|---|
| G69 | 編集画面の終日のチェックの**同じ段の右**に繰り返しの選ぶ欄があり、塗りの欄（`editor-filled`）の形。初めは「繰り返さない」 | 本番で Google の編集画面と並べ、位置（同じ段・右）と地の色を読む | recon §9.1 |
| G70 | 選び方は上から「繰り返さない／毎日／毎週 ○曜日／毎月 第 N ○曜日／毎月 最終○曜日／毎年 ○月○日／毎週平日（月～金）」で、○ は開始日から作られる。「第 N」は開始日が第 1〜4 週のときだけ、「最終」は開始日がその月の最後の同じ曜日のときだけ出る（2026-11-12（木）は第 2 だけ・11-26（木）は第 4 と最終の両方・11-30（月）は最終だけ） | その 3 日で開いて並びを読む。Google と同じ日で並べる | recon §9.1・§9.5 |
| G71 | 選び方のどれかで保存すると、日・週・月の表示で決まりどおりの日に回が並ぶ（毎日 7 日・毎週 1 週 1 回・毎月 第 2 木曜・毎月 最終月曜・毎年・平日 5 日）。保存したのは表の 1 行だけ | 選び方を 1 つずつ作り 2 か月分を見る。本番の表は reader 鍵で数える（予定 1 件＝1 行） | §12.4 |
| G72 | 回を押したときの詳しくの小窓に、日時の行の下に繰り返しの行が出る。文字は選び方の文字と同じ（2026-11-12（木）始まりの毎週なら「毎週 木曜日」） | 毎週の予定の回を押し、日時の行の下の文字を読む | recon §9.5 |
| G73 | 回を保存・削除すると小窓が出る。題は「定期的な予定の編集」（保存）・「定期的な予定の削除」（削除）、選び方は「この予定／これ以降のすべての予定／すべての予定」、ボタンは「キャンセル」「OK」、初めの選択は「この予定」。**1 回目**の回では「これ以降のすべての予定」を出さず 2 択。キャンセルすると何も送られない | 1 回目と 2 回目で開いて読み、キャンセルしたときの送信 0 件を通信の記録で読む | recon §9.5・§12.6 |
| G74 | 3 択の結果。直すとき: 「この予定」はその回だけ変わる／「これ以降」はその回と後の回だけ変わる／「すべて」は全部変わる。消すとき: 「この予定」はその回だけ消え、ほかの回の詳しくの小窓の繰り返しの行は変わらない／「これ以降」はその回と後の回が消え、前の回は残る／「すべて」は全部消える（先に 1 回だけ消した回・直した回も含む）。Google とつないだ本人の予定では、Google の月表示でも同じ回が消えている | 終わりの無い毎週の予定を作り、3 回目でそれぞれ試し、1〜5 回目を読む（試すごとに作り直す）。消すときはアプリと Google の両方の月表示で 1〜5 回目を読む。消すときの「これ以降」と「すべて」は、作り直した予定で先に 4 回目の時刻を「この予定」で 1 時間後ろに直し、5 回目を「この予定」で消してから、3 回目（「すべて」は 2 回目）で消す（審査8 指摘3） | §12.5・§12.7・recon §9.5 U6 |
| G75 | 回を引っぱって動かすと「定期的な予定の編集」の 2 択が出る。2 回目以降は「この予定／これ以降のすべての予定」、1 回目は「この予定／すべての予定」。キャンセルすると元の位置に戻り何も送られない | 1 回目と 2 回目を動かして読み、キャンセルで戻ることと送信 0 件を見る | recon §9.5 |
| G76 | Google とつないだ本人の繰り返しの予定は、Google にも同じ繰り返しで出る。アプリには二重に出ない（取り込みの後も 1 回は 1 つ） | 作って Google で回を見る。15 分の取り込みを待ってアプリの回の数を数える | recon §9.3 の危ないところ |
| G77 | 今ある予定は変わらない（数・時刻・表示）。繰り返しでない予定の保存・削除では 3 択は出ない | 便A の本番反映の前後で予定の行数と画面を比べる。単発の予定で保存・削除して見る | §12.8 |
| G79 | 選び方を後から変えられる（審査3 指摘1）: 単発の予定を「毎週」に直すと回が並ぶ。3 回目の回を「すべての予定」で「繰り返さない」に直すと、3 回目の日時の 1 件だけ残る（審査4 指摘3）。Google から取り込んだ予定では繰り返しの選ぶ欄が出ない（審査4 指摘1）。回で選び方を変えて保存すると、小窓は「これ以降のすべての予定／すべての予定」の 2 択（「この予定」は出ない・1 回目は「すべての予定」だけで小窓は出さない） | 単発→毎週、毎週の 3 回目→繰り返さない（すべて）、2 回目で毎週→毎日（これ以降）を試し、2 か月分の回を読む。小窓の選び方を読む。Google で作った予定を開き、選ぶ欄が無いことを読む | §12.5 選び方を変える |
| G78 | 守り手: 選び方（7 つの値）の決まりの広げ方・3 択の 3 つの結果・取り込みの二重の防ぎを試験が見張る。CI 緑 | CI の結果 | §12.10 |

### 12.3 選ばなかった案

| 案 | 選ばなかった理由 |
|---|---|
| 回を 1 行ずつ作り置く（例: 1 年分） | 同じ予定のデータが何百行にも分かれ、直すたびに全部を直す必要がある。データを分散させない決まり（PO の指示・SSOT）に反する。終わりの無い繰り返しを表せない |
| 繰り返しの決まりを別の表に置く | 予定の 1 行と決まりが 1 対 1 で、表を分ける得が無い。Google の形（予定が `recurrence` を持つ）とも違う |
| 決まりの文字（RRULE）を画面から直接受け取る | 決まった選び方以外の決まりが入り込む。受け口は「どの選び方か」だけを受け、決まりの文字はサーバーが開始日から作る（§12.5） |
| 「これ以降」「すべて」を 1 回ずつ直して実現する | Google の公式が止めている形（recon §9.2）。例外が増えて重くなる |

### 12.4 データの持ち方（1 か所だけ）

各会社の部屋の `calendar_events` に 4 つの欄を足す（`migrations/078_create_calendar_events_tenant.sql:44-65` の表）。

| 欄 | 型 | 意味 |
|---|---|---|
| `recurrence_rule` | TEXT NULL | 繰り返しの元の行だけが持つ。RFC 5545 の RRULE（頭の `RRULE:` を除く）。例 `FREQ=WEEKLY;BYDAY=TH`。「これ以降」で切ったときだけ `;UNTIL=...` が付く |
| `recurring_event_id` | INTEGER NULL・同じ表の id を指す・元が消えたら一緒に消える（ON DELETE CASCADE） | 例外の行（1 回だけ直した・消した回）だけが持つ。元の行の id |
| `original_start_datetime` | TIMESTAMPTZ NULL | 例外の行だけ。決まりでのその回の元の始まり（動かしても変わらない・Google の `originalStartTime` と同じ考え） |
| `is_cancelled` | BOOLEAN NOT NULL DEFAULT false | 例外の行だけ true になりうる。「この予定」を消した回の印 |

- 決まり（CHECK）:
  - 元と例外を兼ねない: `NOT (recurrence_rule IS NOT NULL AND recurring_event_id IS NOT NULL)`
  - 例外の 2 つは一緒に入る: `(recurring_event_id IS NULL) = (original_start_datetime IS NULL)`
  - 消した印は例外だけ: `NOT is_cancelled OR recurring_event_id IS NOT NULL`
  - 決まりの形: `recurrence_rule ~ '^FREQ=(DAILY|WEEKLY|MONTHLY|YEARLY)(;[A-Z]+=[A-Z0-9,+-]+)*$'`
- 重なり禁止: `(recurring_event_id, original_start_datetime)` に部分の UNIQUE（`WHERE recurring_event_id IS NOT NULL`）。同じ回の例外は 1 行だけ。
- 例外の行は、題名・日時など他の欄を普通の予定と同じに持つ（直した後の値）。消した回は元の値の写しで `is_cancelled = true`。
- 例外の行の `calendar_type`・`user_id` は**いつも元の行の値の写し**（審査1 ①）。今の一覧は `(ce.calendar_type = 'shared' OR ce.user_id = :me)` で見える行を絞る（`backend/app/services/calendar_service.py:184-189`）ため、例外の行だけ見える人が違うと、元の回は消えて例外が見えない人が出る。→ this で持ち主・共有の別を変える送信は 422。all は例外の行の 2 つも一緒に直す。following は新しい元の行に直した値を入れる（それより前の例外は元の値のまま）。
- 終日の例外の行の `original_start_datetime` は、その日の日本時間 0:00（審査1 終日）。
- 選び方は表に持たない。決まりの文字から 1 対 1 で読み戻す（`FREQ=DAILY`→毎日、`WEEKLY;BYDAY=<1つ>`→毎週、`WEEKLY;BYDAY=MO,TU,WE,TH,FR`→平日、`MONTHLY;BYDAY=<n><曜>`（n は 1〜4）→毎月 第 n、`MONTHLY;BYDAY=-1<曜>`→毎月 最終、`YEARLY`→毎年）。読み戻せない決まりは自由に決める選び方として表示だけする（今回は作らないが、Google から来る可能性に備える）。

### 12.5 受け口（API）

- 作る `POST /calendar/events`（`backend/app/routers/calendar.py:405`）: `CreateEventBody`（`:111`）に `recurrence: Literal["none","daily","weekly","monthly_nth","monthly_last","yearly","weekdays"] = "none"` を足す。サーバーが開始日（日本時間）から決まりの文字を作り、元の行に入れる。
  - weekly: `FREQ=WEEKLY;BYDAY=<開始日の曜>`／monthly_nth: `FREQ=MONTHLY;BYDAY=<n><曜>`（n は `(日-1)//7+1`）／monthly_last: `FREQ=MONTHLY;BYDAY=-1<曜>`／yearly: `FREQ=YEARLY`／weekdays: `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR`／daily: `FREQ=DAILY`。
  - 開始日で選べないもの（n が 5 の monthly_nth・その月の最後の同じ曜日でない日の monthly_last）は 422。画面も Google と同じく出さない（recon §9.5 U2）。
  - 直すときも同じ（審査1 ⑦）: 開始日を変えて今の選び方がその日で選べなくなったら 422。画面は開始日が変わるたびに選び方を作り直し、今の選び方が無くなったら送らずに i18n のキーの誤りの文を出す。これは設計の決定で、Google がこの場合にどう動くかは確かめていない。
- 一覧 `GET /calendar/events?start&end`（`:143`）→ `list_events`（`backend/app/services/calendar_service.py:150`）:
  - 単発の行と例外の行（消した印でないもの）は今と同じ条件で取る。条件に `recurrence_rule IS NULL` を足して元の行を外す。
  - 元の行は別に `recurrence_rule IS NOT NULL AND start_datetime < :end` で取り（審査2 指摘1: このときも単発と同じ type の絞り `backend/app/services/calendar_service.py:176-181` と見せ方の絞り `:184-189`（他人の「自分だけ」は返さない）を必ず付ける。例外の行を期間に関係なく引くときも同じ絞りを付ける）、期間の中の回に広げる（python-dateutil の `rrulestr` と `between(期間の始まり − 長さ, 期間の終わり, inc=True)`）。回の終わり＝回の始まり＋元の長さ。
  - 時刻つきは日本時間の始まりを dtstart にし、UNTIL は UTC の形。終日は日付だけで広げ、UNTIL は日付の形（RFC 5545 で dtstart と同じ型が要る）。
  - 例外の行がある回（同じ `original_start_datetime`）は広げた回から外す（審査1 ⑤）: 見つかった元の行の id で例外の行を**期間に関係なく**別に引き（`recurring_event_id = ANY(:ids)`）、その `original_start_datetime` の回を外す。回を別の日へ動かした例外でも元の回が残らない。消した印でない例外の行そのものは、上の普通の期間の条件で出る。消した印の例外は返さない。
  - 広げた回は、今と同じ厳しい比べ方で最後に絞る（審査1 ⑥）: 回の始まり < 期間の終わり かつ 回の終わり > 期間の始まり（`backend/app/services/calendar_service.py:168-172` と同じ）。`between` の inc=True で境目の回が入りすぎるのをここで落とす。
  - 終日は日付で広げる（dtstart は日付・回の始まりはその日の日本時間 0:00）。
  - 1 つの元から返す回は 1000 まで（毎日でも約 2 年 9 か月分）。超えたら打ち切って記録に残す。
  - 回は元の行の欄を写し、`id`＝元の id・`recurring_event_id`＝元の id・`occurrence_start`＝その回の元の始まり・`recurrence`＝選び方・`recurrence_rule` を足して返す。例外の行は自分の id と `recurring_event_id`・`occurrence_start`（＝`original_start_datetime`）と、元の `recurrence`。
- 探す `title_query`（`list_events` の同じ関数・`backend/app/routers/calendar.py:166`）: 広げない。探すときは `recurrence_rule IS NULL` の条件を**足さない**（審査2 指摘7）。返すのは、単発の行・元の行（1 件）・消した印でない例外の行。消した印の例外（`is_cancelled = true`）は返さない。Google の探す結果の出方は確かめていない（未確認・G の条件には入れない）。
- 直す `PATCH /calendar/events/{id}`（`:446`）・消す `DELETE`（`:538`）: `scope: Literal["this","following","all"]` と `occurrence_start`（ISO）を足す（DELETE は query）。
  - 選び方を変える（審査3 指摘1）: `UpdateEventBody`（`backend/app/routers/calendar.py:122`）にも `recurrence: Optional[Literal[...7 つ...]] = None` を足す（None は「変えない」）。値が今の選び方と同じなら変えないのと同じに扱う。
    - 単発の行に `recurrence`（none 以外）: scope 無しで受ける。その行に決まりを入れて元の行にする（開始日から作る・選べない値は 422）。その行に `meet_url` があれば 422（Meet と繰り返しを組み合わせない・下の Meet の項）。
    - Google から取り込んだ行（`source = 'google'`）に `recurrence`（none 以外）が来たら 422（審査4 指摘1・判定は `try` の前）。取り込みは 1 回ずつで元の予定の id が来ない（`backend/app/services/google_webhook.py:300` `singleEvents`）ため、元の行にすると全部取り直しの掃除（`:340-346`）で消える。Google で作った予定の繰り返しは Google で付ける。画面はこの予定に選ぶ欄を出さない（`frontend/src/pages/schedule/schedule-utils.ts:353` の `source` で分ける）。
    - 元の行・例外の行で選び方を変える: scope が this なら 422（例外の行は自分の決まりを持たない）。following はその回で元を切り、新しい元の行をその回から新しい選び方で作る（none なら新しい行は単発）。all は元の行の決まりを作り直し（none なら決まりを NULL にして単発に戻す）、例外の行は全部消す。all で none にしたとき残る 1 件の日時は、押した回の日時（同じ保存で直した日時があればその値）にする。1 回目以外の回で押しても元の 1 回目の日時には戻さない（審査4 指摘3・画面で見ている回がそのまま残る。Google が同じ場面でどうするかは確かめていない設計の決定）。1 回目の following は all と同じ。
    - 画面は回で選び方を変えたとき、3 択から「この予定」を外す（§12.6）。Google が同じ場面でどう聞くかは確かめていない（設計の決定）。
  - 422 を出す判定（この §12.5 と §12.4 に書いた 422 の全部）は、受け口の `try` の**前**で行う（審査2 指摘2）。直す受け口は `try` の中の例外を全部 500 に変える（`backend/app/routers/calendar.py:523` の `except Exception`。作る受け口は `:431`）。今の Meet の判定（`:417-418` の注意書き・`:497-508`）と同じ置き方にする。判定はサービスに `check_recurrence_request(...)`（誤りの文か None を返す・表は読むだけ）を作り、受け口が `try` の前に呼んで None でなければ 422。消す受け口も、`cal_svc.delete_event` を呼ぶ前に同じ判定を呼ぶ。
  - 元の行に scope が無ければ 422（3 択を飛ばした古い画面からの送信を止める）。単発の行に scope があれば 422。
  - `occurrence_start` が決まりの回に当たらなければ 422（その時刻 ±1 秒で `between` して 0 件）。
  - 例外の行の id に送ったとき: this はその行を直す（消すは `is_cancelled = true`）、following と all は元の行の id に読み替える。
  - this: 例外の行を作る（あれば直す）。消すは `is_cancelled = true` の例外の行。
  - following: 元の決まりに UNTIL（その回の前の日の終わり。時刻つきは前の日の 23:59:59 日本時間を UTC の Z 形で、終日はその前の日の日付）を付けて切り、新しい元の行（その回の日時・直した値・同じ選び方から開始日で作り直した決まり）を作る。その回以降の例外の行は消す。1 回目で following を選んだら all と同じ。消すときは元の決まりを切り、`original_start_datetime` がその回以降の例外の行も消す（審査1 ⑨。1 回目なら全部消す）。
  - all: 元の行を直す。始まり・終わり・選び方が変わったら例外の行を消し、決まりを開始日から作り直す。変わらなければ題名・場所・説明・`calendar_type`・`user_id` などの変わった欄だけを例外の行にも写す。消すは元の行を消す（例外は一緒に消える）。
  - all で始まりを変えたとき（審査1 ④）: 送られる始まりは「押した回」の新しい始まり。元の行の新しい始まり＝元の行の始まり＋（新しい始まり − `occurrence_start`）。終わりも同じだけずらす。1 回目以外の回で直しても、1 回目から全部が同じだけ動く。none 以外のときは、Google へ送る本文の始まり・終わりも、画面から来た値でなく、この「元の行の新しい始まり・終わり」から作る（審査2 指摘3。今の `update_event` は `_to_google_event_body(payload)` をそのまま送る・`backend/app/services/calendar_service.py:395`）。all で none にするときはこのずらしを使わない。残る 1 件の日時は上の「all で none にしたとき残る 1 件の日時」（押した回の日時・同じ保存で直した日時があればその値）だけで決め、Google へ送る本文もその日時から作る（審査5 指摘1・審査6 指摘1 で文の順を直した）。
  - UNTIL の扱い（審査1 UNTIL・⑧）: 既に UNTIL がある決まりを following で切るときは、古い UNTIL と新しい UNTIL の早い方にする。all で決まりを作り直すときは今の UNTIL を引き継ぐ。following の新しい元の行は元の UNTIL を引き継ぐ。新しい始まりが UNTIL より後なら 422。
  - 持ち主の確かめ（`:465`・`:546`）は元の行の id で今と同じに行う。
  - Meet と繰り返し（審査2 指摘8）: 今回は組み合わせない。繰り返しを付けて作るときの `add_meet`・元の行／例外の行への `add_meet` は 422（判定は上と同じく `try` の前）。例外の行の `meet_url` は元の行の写し（今は元の行に Meet が付かないので NULL）。画面は繰り返しが「繰り返さない」以外のとき Meet の行を出さない。繰り返しの予定の Meet を Google がどう扱うかは確かめていない。

#### 決まりの文字から選び方への読み戻し（審査2 指摘5）

- 読み戻すときは `UNTIL=...` を除いてから §12.4 の対応で選ぶ。「これ以降」で切った元の行も、切る前と同じ選び方の文字を出す（例「毎週 木曜日」）。終わりの日は文字に出さない。Google は「毎週 木曜日, 5 回」「毎週 木曜日, 2026年 12月 2日まで」のように出す（recon §9.5 U6）。今回の選ぶ欄は決まった 7 つの値だけで、回数や終わりの日を選ぶ所が無い。選ぶ欄に無い文字を出すと選べるように見えるため、今回は出さない（審査8 指摘2）。

### 12.6 画面

- 選ぶ欄: `frontend/src/pages/schedule/ScheduleDraftFields.tsx:159` の終日の Checkbox と同じ段の右に、金型 `SelectControl` の `editor-filled`（`:254` と同じ使い方）。文字は i18n のキー（ja・en 同じキー）と、曜日・月日を `Intl.DateTimeFormat` で開始日から作る。直書きの日本語は入れない（ADR-027）。新しい部品・色の直値は作らない（ADR-144・ADR-067）。
- 選ぶ欄を出さない場合（審査5 指摘2・§12.5 と同じ決まり）: Google から取り込んだ予定（`normalizeEvent` の `source` が `"google"`・`frontend/src/pages/schedule/schedule-utils.ts:353`）の編集画面には選ぶ欄を出さない。サーバーも 422 で止める（§12.5）。G79 で確かめる。
- Meet の行との関係（§12.5 の Meet と繰り返し）: 選ぶ欄が「繰り返さない」以外のときは Meet の行を出さない。行を隠すだけでは足りない。送るかどうかは下書きの `addMeet` で決まる（`frontend/src/pages/schedule/SchedulePageImpl.tsx:976`・行を押すと true になる `frontend/src/pages/schedule/ScheduleDraftFields.tsx:300`）。だから繰り返しを「繰り返さない」以外に変えたら、同じ変更で下書きの `addMeet` を false に戻す（審査6 指摘2。戻さないと `add_meet` が送られ 422 になる）。Meet が付いている予定（`meet_url` あり）では選ぶ欄を出さない（サーバーは 422・§12.5）。
- 詳しくの小窓: 日時の行の下に繰り返しの行（選び方の文字）。
- 3 択の小窓: 金型 `Modal`（`frontend/src/components/Modal.tsx`）と `RadioControl`。題は保存・動かすとき「定期的な予定の編集」、消すとき「定期的な予定の削除」。選び方「この予定／これ以降のすべての予定／すべての予定」、ボタン「キャンセル」「OK」、初めは「この予定」（recon §9.5 U1）。1 回目の回では「これ以降のすべての予定」を出さない（1 回目の following は all と同じのため・§12.5）。キャンセルすると何も送らない。
- 選び方を回で変えて保存するとき（審査3 指摘1）: 3 択から「この予定」を外し「これ以降のすべての予定／すべての予定」（初めの選択は「これ以降のすべての予定」）。1 回目の回なら「すべての予定」だけなので小窓を出さずに all で送る。単発の予定で選び方を変えたときは小窓を出さない。
- `occurrence_start` の送り方（審査3 指摘2）: 回の始まりは UTC の `Z` の形（`Date.prototype.toISOString()`）で送る。消すときは URL の後ろに付くので `URLSearchParams` で組む（`+09:00` の `+` が空白に化けて 422 になるのを防ぐ）。サーバーは受けた時刻を日本時間に直してから回と比べる。
- 回の id: `event-<元のid>-<回の始まりのミリ秒>`。`eventNumericId`（`frontend/src/pages/schedule/schedule-utils.ts:408`）は両方の形から元の id を返すように広げ、回の始まりを返す関数を足す。`normalizeEvent`（`:339`）で `occurrence_start` があればこの形の id にする。
- 保存 `frontend/src/pages/schedule/SchedulePageImpl.tsx:989,991`・消す `:1006`・動かす `:1192`（PATCH `:1203`）: 回なら小窓を挟み、選んだ scope と回の始まりを付けて送る。動かすときは 2 択（2 回目以降「この予定／これ以降のすべての予定」・1 回目「この予定／すべての予定」）で、キャンセルなら元の位置に戻す（recon §9.5 U3）。

### 12.7 Google との同期（ADR-1057・ADR-1059 の範囲の中）

- 送る（つないだ本人の自分だけの予定・双方向か書くだけのときだけ。今と同じ）:
  - `_to_google_event_body`（`backend/app/services/calendar_service.py:652`）に、元の行なら `"recurrence": ["RRULE:" + 決まり]` を足す。時刻つきは今と同じ `timeZone: "Asia/Tokyo"` 付き（繰り返しでは必須・recon §9.2）。終日は今と同じ日付だけで `timeZone` を付けない（公式の終日の繰り返しの例が日付だけ・「終日では時間帯は意味を持たない」・recon §9.5 U5）。
  - this: `backend/app/services/google_calendar.py` に `get_instance(元の google_event_id, 回の元の始まり, 終日か)`（`events.instances` を回の前後の窓（`timeMin`・`timeMax`）で引き、`originalStartTime` が一致する回を選ぶ。`originalStart` の引数は終日の値の形が公式に書かれていないため使わない。実装カード便15A の審査で直した・2026-11-12）を足す。返った回の id を例外の行の `google_event_id` に入れ、その id に patch（消すは `status: "cancelled"`）。同時に例外の行の `sync_origin_id` を `app:<会社>:<例外の行の id>` にする（審査1 ⑩。作る道の `backend/app/services/calendar_service.py:305-309` と同じ書き方）。
  - following: 元の予定を patch して `recurrence` を UNTIL 付きにし、新しい元の行を insert（今の作る道と同じ）。
  - 消すとき（recon §9.5 U6 で Google の結果を測った。PO の問い 2026-11-12 で抜けを直した）:
    - this: 上の this と同じ道で、その回に `status: "cancelled"` を送る。元の予定の `recurrence` は送らない（Google でも決まりは「5 回」のまま変わらなかった）。
    - following: 元の予定に、`recurrence` を UNTIL 付きにした patch だけを送る。新しい予定は作らない。UNTIL の値は §12.5 following と同じ（前の日の終わり）。Google で「これ以降」を消したときの表示「2026年 12月 2日まで」と同じ日になる。あわせて、その回以降の例外の行のうち、`is_cancelled = false` で `google_event_id` を持つ行それぞれに `status: "cancelled"` の patch を送る（審査8 指摘1）。時刻などを直した回が UNTIL で切った後も Google に残るかは確かめていないため、残っても消えるように送る。行を消す前に id を読んでおき、表を消して commit した後に送る。すでに Google 側で消えていて失敗しても警告の記録だけにする（今の `:509-510` と同じ）。1 回目の following は all と同じ。
    - all: 元の行の `google_event_id` に今の `delete_event`（`backend/app/services/google_calendar.py:430`）を送る。Google では元の予定を消すと、直していない回は全部消えた（U6）。時刻などを直した回が一緒に消えるかは確かめていない（審査8 指摘1）。そのため、following と同じく、`is_cancelled = false` で `google_event_id` を持つ例外の行それぞれにも `status: "cancelled"` の patch を送る。行を消す前に id を読んでおき、表を消して commit した後に送る。失敗は警告の記録だけ。アプリの表の例外の行は ON DELETE CASCADE で消える。今の消す道（`backend/app/services/calendar_service.py:483-510`）は消す行の `google_event_id` を送るので、元の行の id に読み替えてから呼ぶ（§12.5 の「例外の行の id に送ったとき」）。
    - 送る順番（審査9 指摘3）: 先に例外の回への cancelled を 1 件ずつ送り、そのあと元の予定への送り（following は UNTIL の patch・all は delete）を送る。元を先に消すと回への送りが毎回失敗するため。送りは 1 件ごとに別々の `try` で包み、1 件の失敗で残りを止めない（今の消す道は送り 1 件に `try` 1 つ・`backend/app/services/calendar_service.py:505-510`）。
    - どれも、送る先の判定は今と同じ（`google_event_id` があり、双方向か書くだけのとき・`backend/app/services/calendar_service.py:503-504`）。Google への送りに失敗しても、アプリの表は消したまま（今の `:509-510` と同じ。警告の記録だけ）。
  - all: 題名・場所・説明など、始まり・終わり・選び方以外だけが変わったときは元の予定を patch（`recurrence` は送らない）。始まり・終わり・選び方のどれかが変わったときは、下の「消して作り直す道」を使う（審査4 指摘2。アプリは例外の行を全部消すので、Google 側の直した回・消した回も一緒に消える形にそろえる）。
- 例外の行を消す道はどれも同じ送りにする（審査9 指摘2）: アプリが例外の行を消すのは、消すときの following・all のほかに、直すときの following（その回以降の例外の行）と、下の「消して作り直す道」（all で始まり・終わり・選び方を変えたときと、all で none にしたとき）がある。どの道でも、消える例外の行のうち `is_cancelled = false` で `google_event_id` を持つ行に `status: "cancelled"` の patch を送る。Google の直した回が元の予定の切りや削除で一緒に消えるかは確かめていないため。順番と `try` は上の「送る順番」と同じ（例外の回を先・元の予定への送りを後）。直すときの following は、例外の回への送りのあとに元の UNTIL の patch と新しい予定の insert を送る。
  - 送り先の id は、消すときと同じく、例外の行を表から消す前に読んでおき、commit の後に送る（審査10 指摘2）。今の直す道は commit の後に `google_event_id` を読む（`backend/app/services/calendar_service.py:381-387`）ので、その形のままだと例外の行が消えた後で送り先が 0 件になる。
  - 失敗したときの扱いは**直す道だけ**に効く（審査11 指摘1）。消す道（this・following・all）は、どの送りが失敗しても今の消す道（`backend/app/services/calendar_service.py:483-510`）と同じく警告の記録だけで、`sync_status` は変えない。
  - 直す道で元の予定への送りが失敗したときは、そのあとの新しい予定の送り（following の insert・消して作り直す道の create）を送らない（審査10 指摘3）。送ると Google に古い繰り返しと新しい予定が両方残り、回が重なるため。警告を記録し、`sync_status` を `'failed'` にする（今の直す道の失敗と同じ値・`backend/app/services/calendar_service.py:420-423`）。`'failed'` にする行は次のとおり（審査11 指摘2・3）:
    - 直すときの following で元への UNTIL の patch が失敗: 元の行と新しい元の行の**両方**を `'failed'`。新しい元の行の `google_event_id` は NULL のまま。
    - 直すときの following で UNTIL の patch は通り insert だけ失敗: 新しい元の行だけ `'failed'`（`google_event_id` は NULL）。元の行は、UNTIL の patch が通った時点で `sync_status = 'synced'`・`last_synced_at = NOW()` に書く（審査12 指摘1。今の直す道は直す前に `'pending'` を書き（`backend/app/services/calendar_service.py:372`）、送りが通ったら `'synced'` に書く（`:409-415`）。同じ形にそろえる）。
    - 直すときの this で `get_instance` か例外の回への patch が失敗: 例外の行を `'failed'`。新しく作った例外の行の `google_event_id` は NULL のまま（審査12 指摘2）。
    - 直すときの all で、決まり以外だけを直す元の予定への patch が失敗: 元の行を `'failed'`。`google_event_id` はそのまま（今の直す道の失敗 `:420-423` と同じ・審査12 指摘2）。
    - どの道も、Google への送りを試して通った行は `'synced'`・`last_synced_at = NOW()` に書く。Google に送らない場合（`google_event_id` が無い・同期の向きが双方向でも書くだけでもない。今の直す道の `backend/app/services/calendar_service.py:391` の条件）は、今と同じく `'pending'` のまま残す（審査13 指摘1）。
    - 新しく作る行（直すときの following の新しい元の行・this の例外の行）は、insert の文で `sync_status = 'pending'` を明示して書く（審査14 指摘2）。列の既定値は `'synced'`（`migrations/078_create_calendar_events_tenant.sql:59`）なので、書かないと送っていない行が `'synced'` になる。今の作る道も `'pending'` を明示している（`backend/app/services/calendar_service.py:266`）。
    - 新しく作る行を送るかどうかは、**元の行**の `google_event_id` があり、同期の向きが双方向か書くだけのときに送る（審査14 指摘3。新しい行は insert の直後は必ず id を持たないため、上の「`google_event_id` が無い」を新しい行に当てない）。元の行が id を持たない・同期の向きが合わないときは、新しい行も送らず `'pending'` のまま残す。
    - 消すときの this で新しく作る消した印の例外の行（`is_cancelled = true`）も、insert の文で `sync_status = 'pending'` を明示して書く（審査15 の推奨）。消す道は送りの後も `sync_status` を変えないので、この行は `'pending'` のまま残る。一覧はこの行を返さない（§12.4）ので画面には出ない。
    - 消して作り直す道で delete が失敗: その行を `'failed'`。`google_event_id`・`sync_origin_id` は古い値のまま残す（Google にも古い予定が残っているため）。
    - 消して作り直す道で delete は通り create だけ失敗: その行を `'failed'` にし、`google_event_id` と `sync_origin_id` を NULL にする。今の作る道の失敗（`backend/app/services/calendar_service.py:316-324`）と同じ「Google の id を持たない行」の形にそろえ、Google で消えた古い id に patch を送らないため。
    - `'failed'` の行を後から送り直す仕組みは今の main に無い（`sync_status` を読むのは一覧の `backend/app/services/calendar_service.py:200` だけ）。便15 でも作らない。今の単発の予定の失敗と同じ扱い。
  - 例外の回への cancelled の失敗は、直す道でも消す道でも、警告だけで後の送りを止めない。
- 消して作り直す道（審査3 指摘1・審査4 指摘2）: 単発⇄繰り返しの切り替え（単発に決まりを入れる・all で none にする）は、Google の今の予定を消して（`backend/app/services/google_calendar.py:430` `delete_event`）、新しい予定として作り直す（`:390` `create_event`）。新しい id を `google_event_id` に、`sync_origin_id` も作る道と同じ形で入れ直す。すでにある予定に `recurrence` を patch で足す・外す動きは確かめていないため使わない。古い id の取り消しの知らせが取り込みで来ても、表にその id の行が無いので消す文は 0 行に当たるだけ（`backend/app/services/calendar_service.py:573-581`）。all で始まり・終わり・選び方を変えたとき（繰り返しのまま）も同じく消して作り直す（審査4 指摘2）。following は公式の勧める形（recon §9.2・元に UNTIL を patch して新しい予定を作る）のまま。
- 取り込み（`upsert_from_google`・`backend/app/services/calendar_service.py:551`）:
  - 来た予定の `recurringEventId` が、アプリ起源の元の行の `google_event_id` と同じなら飛ばす（二重を防ぐ。recon §9.3 の危ないところ）。
  - 例外の行に入れた回の id は今の完全一致（`_is_app_origin`・`:129`）で飛ばされる（`_is_app_origin` は google_event_id の一致**かつ** sync_origin_id が `app:<会社>:` で始まるときだけ当たる。だから §12.7 の this で両方を入れる。審査2 指摘6）。
  - Google で作った繰り返しは今と同じ（1 回ずつ 1 行・source='google'）。3 択は出さない（`recurrence_rule` を持たないため）。
  - 全部取り直しの掃除（`backend/app/services/google_webhook.py:340-346`）は source='google' の行だけを消すので、アプリの元の行と例外の行には触れない。
- Google 側で回を直したとき（アプリ起源の繰り返し）: 上の飛ばす決まりで取り込まない。アプリの表示とずれる。Google からの直しを反映するのは今回の範囲の外（今のアプリ起源の単発の予定も Google での直しを取り込まない・`_is_app_origin` で飛ばす）。

### 12.8 移行と便の分け方

- 移行 migrations/20261112_<時刻>_add_calendar_events_recurrence.sql（新しく作るファイル）: meet_url の移行（`migrations/20261104_161223_add_calendar_events_meet_url.sql`）と同じ「会社ごとに回す・冪等」の形で、欄 4 つ・CHECK 4 つ・部分 UNIQUE 1 つ。欄はどれも NULL 可か一定の初期値なので、表を書き直さず速い（ロック待ち 1 秒の決まり ADR-1037 の中）。
  - 何度流しても同じになる書き方（審査1 冪等）: 欄は `ADD COLUMN IF NOT EXISTS`（`recurring_event_id` の参照の決まりは欄の行の中に書く）。CHECK は名前を付け、`pg_constraint` にその表（`format('%I.calendar_events', 会社)::regclass`）でその名前が無いときだけ `NOT VALID` で足してから `VALIDATE`。部分 UNIQUE は `CREATE UNIQUE INDEX IF NOT EXISTS`。
  - 本番で流す一覧（審査2 指摘4）: `scripts/run_all_migrations.sh` の末尾に説明の 1 行と `run_sql migrations/<新しい移行のファイル名>` を足す（meet_url は `:1226-1227`）。
  - 試験の足場（審査1 ②）: 新しい移行の名前を次の 3 か所に足す（meet_url の移行が載っている所と同じ）。
    - `backend/tests/rls_bootstrap.py` `_TENANT_LOOP_MIGRATIONS`（:159-176 付近）に名前と「会社を選ぶ条件」の回数。
    - `backend/tests/test_calendar_sync_tenant_reset_pg.py` `_MIGRATIONS`（:44-53）に `(名前, True)`。
    - `backend/tests/test_tenant_loop_migration_guard.py` `_REVIEWED` の 2 つの組（"rls_bootstrap.py" と "test_calendar_sync_tenant_reset_pg.py"）。
  - 分類表 `migrations/20261024_100300_create_ai_cloud_views.sql:351-354` に `recurrence_rule` の行（mask・理由「値の決まりが値の一覧でなく文字の形だけのため伏せる」）を足す（審査1 ③）。他の 3 つは数・真偽・日時で行が要らない（`backend/tests/ops/test_ai_cloud_views.py:50-53`）。今の `meet_url` も分類表に無い（recon §9.4 U4）。この便では直さず、別の件として台帳に残す。
  - 道具: `backend/requirements.txt` に `python-dateutil==2.9.0.post0` を明示（既に間接に入っている版・recon §9.3）。
- 便A（裏側だけ・画面は変わらない）: 移行・受け口・広げ方・3 択の処理・Google 同期・試験。移行を含むので危ない PR（ADR-136）。GO は委任の手順で記録する。便A の後は、繰り返しの元の行が 0 件なので一覧の結果は今と同じ（G77）。
- 便B（画面）: 選ぶ欄・詳しくの行・3 択の小窓・id の形・文言・試験。便A の本番反映の後。

| 便 | 中身 | 成功条件 | 危険な道 |
|---|---|---|---|
| 便15A | 繰り返しの裏側（§12.4・§12.5・§12.7・§12.8）。欄 4 つの移行・受け口・広げ方・3 択・Google 同期・試験 | G71（裏側）・G74・G76〜G79（裏側） | **あり**（`migrations/`）。ADR-136 の GO（委任）・直前のバックアップの確認 |
| 便15B | 繰り返しの画面（§12.6）。選ぶ欄・詳しくの行・3 択の小窓・文言・試験 | G69〜G75・G79 | なし（frontend だけ） |

### 12.9 心配と対処・戻し方

| 心配 | 対処 | 戻し方 |
|---|---|---|
| 二重に取り込む | §12.7 の飛ばす決まりと試験（G78） | 便A の差し戻し。重なった Google 起源の行は `source='google' AND google_event_id` で特定できる |
| 毎日の繰り返しで一覧が重い | 期間の中だけ広げる・1 元 1000 回まで | 打ち切りの数を下げる |
| 移行がロックで止まる | 欄足しだけ・ロック待ち 1 秒 | 移行は冪等。失敗しても欄が無いままで今の動き |
| 便A の後に古い画面から元の行に scope 無しで送られる | 422 で止める（元の行は便B まで作られない） | — |
| アプリを戻した（欄は残る） | 古いコードは欄を読まない。元の行は 1 回目だけ・例外の行は単発に見える（壊れはしない） | 欄を消す SQL（`ALTER TABLE ... DROP COLUMN`）は PO 確認の上で別に流す |
| Google で回を直してもアプリに来ない | 今回の範囲の外と明記（§12.7）。PO に完了報告で伝える | — |

### 12.10 守り手（維持の仕組み）

- backend 試験（`backend/tests/test_calendar_service.py` に足す）: 6 つの決まりの作り方と 2 か月分の広げ方・例外で外す・消した印・1000 回の打ち切り・3 択の 3 結果×直す／消す・422 の 3 通り・Google から取り込んだ行への選び方は 422・all で none のとき押した回の日時が残る・選び方の変更（単発→繰り返し・all で none・this で 422・following で新しい選び方）と Google の消して作り直す道・Google の本文の `recurrence`・取り込みの飛ばし。消すときの Google への送り（§12.7 の消すとき）を 3 択ごとに: this はその回に `status: "cancelled"` の patch 1 件だけ／following は消す範囲の例外の行のうち `is_cancelled = false` で `google_event_id` を持つ行の数だけの cancelled の patch と、元の予定への `recurrence` の patch 1 件で、insert 0 件、UNTIL は前の日の 23:59:59 日本時間（終日は前の日の日付）／all は同じ条件の例外の行の数だけの cancelled の patch と、元の `google_event_id` への delete 1 件（審査10 指摘1）。どちらも例外の回への送りが元の予定への送りより先であること。直すときの following と、消して作り直す道でも、消える例外の行の数だけ cancelled が先に送られること（審査9 指摘1・2・3）。例外の行の id に all・following で送ったときも元の id に送ること。例外の回への送りの 1 件が失敗しても、表は消えたままで警告が 1 件残り、残りの送りは続くこと。直すときの following と消して作り直す道で、例外の行の id が消す前に読まれ、送り先が 0 件にならないこと。直す道で元の予定への送り（UNTIL の patch・delete）を失敗させたとき、insert・create が 0 件で、§12.7 の表のとおりの行が `'failed'` になること（審査10 指摘2・3）。直すときの following で insert だけ失敗させたとき、新しい元の行だけ `'failed'` で `google_event_id` が NULL。消して作り直す道で create だけ失敗させたとき、行が `'failed'` で `google_event_id` と `sync_origin_id` が NULL。消す道で送りを失敗させたとき、`sync_status` が変わらず警告が残ること（審査11 指摘1〜3）。直すときの following で insert だけ失敗させたとき、元の行が `'synced'` であること。直すときの this・all の patch を失敗させたとき、その行が `'failed'` であること（審査12 指摘1・2）。同期の向きが none のときと、元の行が `google_event_id` を持たないときに this・following・all で直すと、Google への送りが 0 件で、直した行と新しく作った行（following の新しい元の行・this の例外の行）が `'pending'` であること。元の行が `google_event_id` を持ち双方向のとき、following の新しい元の行と this の例外の行が送られ、通ったら `'synced'` になること（審査14 指摘1〜3）。
- frontend 試験: 6 つの文字（開始日 2 通り）・id の形と `eventNumericId`・3 択の取り消しで送らない・選び方を変えたとき「この予定」を出さない・`occurrence_start` を Z 形で送る・Google から取り込んだ予定と Meet が付いた予定で選ぶ欄を出さない・繰り返しを選んだら Meet の行を出さない（審査5 指摘2）・Meet の行を押してから「毎週」を選んで保存すると `add_meet` を送らない（審査6 指摘2）。
- 移行の見張り: `backend/tests/test_tenant_loop_migration_guard.py`（会社ごとに回す移行が試験の足場に載っているか）。
- 分類表の T10 は calendar_events を見ない（会社の部屋を作る `bootstrap_tenant_schema` がこの表を作らないため・審査1 ③）。分類の行の抜けを見張る試験は今は無い。守り手に数えない。

### 12.11 外部の事例

- Google Calendar API の公式（Context7・2026-11-12・recon §9.2）: 繰り返しは元の予定の `recurrence` 1 か所に持ち、回は `recurringEventId`・`originalStartTime` で表す。「これ以降」は UNTIL で切って新しい繰り返しを作る。この設計の持ち方はこの形にそろえた。数で測った事例（重さ・誤りの率）は見つけていない。成功の証明には使わず、形の根拠にだけ使う。

### 12.12 未確認（設計の合格の前に決める）

- U1・U2・U3・U5 は 2026-11-12 に測って決めた（recon §9.5）。G70・G72・G73・G75・§12.5・§12.6・§12.7 に入れた。
- U6（消したときの 3 択の結果）も 2026-11-12 に測って決めた（recon §9.5 U6）。G74・§12.5 following・§12.7 の消すときに入れた。Google が中で持つ UNTIL の文字そのものは読めていない。表示の「12月 2日まで」に合わせ、前の日の終わりにした。
- 残る未確認: Google の探す結果での繰り返しの出方（G の条件に入れない・§12.5）。保存の小窓の 1 回目の 2 択は、削除と動かすの 1 回目で測った形にそろえた（保存の 1 回目は開いていない）。

### 12.13 審査

#### 審査1（2026-11-11 20:46〜20:54 UTC・クラウドの Opus・対象 0d7056a4f）

- 判定: REVISE（直す所あり）。実行記録 cse_01W47tdiy8F1wU8h4rCL5f9v と続き cse_01W47tdg8tXvf9HS6xXLK6gs。記録の文が途中で切れて読めない所があったため、続きの審査で残りの点を聞いた（続きの各点の本文は読めず、判定の行だけ読めた）。
- 指摘と直し:

| # | 指摘 | 直した所 |
|---|---|---|
| ① | 例外の行の持ち主・共有の別が元と違うと、見える人がずれる | §12.4（いつも元の写し・this で変えたら 422・all と following の扱い） |
| ② | 試験の足場の 3 か所に新しい移行が無いと CI の見張りが止める | §12.8 |
| ③ | T10 は calendar_events を見ない | §12.8・§12.10 |
| 冪等 | CHECK・索引を 2 回流すと失敗する | §12.8 |
| ④ | all で 1 回目以外の始まりを変えたときの元の始まりが決まっていない | §12.5 |
| ⑤ | 別の日へ動かした例外が期間の外だと元の回が残る | §12.5 |
| ⑥ | `between` の inc=True で境目の回が今の一覧と違って入る | §12.5 |
| ⑦ | 開始日を変えて選び方が成り立たないとき | §12.5（422・画面は送らない） |
| 終日 | 終日の広げ方と例外の元の始まり | §12.4・§12.5 |
| UNTIL・⑧ | UNTIL の重ね・引き継ぎ | §12.5 |
| ⑨ | following の削除で後の例外が残る | §12.5 |
| ⑩ | 例外の行の sync_origin_id | §12.7 |
| ⑪ | G74 の確かめ方が 4 回だと 5 回目以降を見られない | §12.2 G74 |

#### 審査2（2026-11-11 21:16〜21:19 UTC・クラウドの Opus・対象 5b150f516）

- 判定: REVISE。実行記録 cse_01W47tdieQ7X31CJYrHZpGtx。指摘は 1 件ずつ echo で出させ、全文を読めた。1 回目の指摘は全部直っているとの判定。成功条件 G69〜G78 はどれも ○× で判定できる（G72 は期待する文字を書くよう指摘）。
- 指摘の根拠は Opus が origin/main で確かめた（`backend/app/routers/calendar.py:417-418,431,497-508,523`・`backend/app/services/calendar_service.py:129-142,176-189,395`・`scripts/run_all_migrations.sh:1226-1227`）。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 高 | 元の行を取る条件に見せ方の絞りが無く、他人の「自分だけ」の繰り返しが出る | §12.5 一覧 |
| 2 | 中 | 新しい 422 をサービスで出すと受け口の `except Exception` で 500 になる | §12.5 直す・消す（`try` の前で判定） |
| 3 | 中 | all で始まりをずらすとき Google へ送る始まりが画面の値のまま | §12.5 all |
| 4 | 中 | 本番で流す一覧 `scripts/run_all_migrations.sh` への 1 行が抜け | §12.8 |
| 5 | 低 | UNTIL 付きの決まりの読み戻し | §12.5 読み戻し |
| 6 | 低 | `_is_app_origin` は「かつ」なのに「どちらでも」と書いた | §12.7 |
| 7 | 低 | 探すときの分け方 | §12.5 探す |
| 8 | 低 | Meet と繰り返しの組み合わせ | §12.5（今回は組み合わせない・422・画面で出さない） |
| G72 | — | 期待する文字を書く | §12.2 G72 |

#### 審査3（2026-11-11 21:29〜21:31 UTC・クラウドの Opus・対象 12f9a9d60）

- 判定: REVISE。実行記録 cse_01W47tdivuYnS6chLre2YLov。指摘は echo で出させ、全文を読めた。2 回目の指摘 1〜8 と G72 は直っており、引いた行は origin/main と合うとの判定（観点(a) 指摘なし）。観点(b)(c) は下の 3 件のほか無し。
- 指摘 1 の Google の消す・作るの関数と、取り消しの知らせの扱いは Opus が origin/main で確かめた（`backend/app/services/google_calendar.py:390,430`・`backend/app/services/calendar_service.py:573-581`）。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 高 | 直す受け口で選び方を変える道（単発→繰り返し・繰り返し→繰り返さない・回で選び方を変える）が決まっていない。成功条件にも無い | §12.5 選び方を変える・§12.6・§12.7・G79 を足した |
| 2 | 低 | 消すとき URL に付ける `occurrence_start` の `+` が空白に化ける | §12.6（UTC の Z 形・URLSearchParams） |
| 3 | 低 | recon §9.3 に「T10 が数える」が残り §12.10 と食い違う | recon §9.3 |

#### 審査4（2026-11-11 21:38〜21:40 UTC・クラウドの Opus・対象 2a037b1c2）

- 判定: REVISE。実行記録 cse_01W47tdfh4GrAiDiZFrLu5o5。指摘は echo で出させ、全文を読めた。3 回目の指摘 1〜3 は直っており、新しく引いた行は origin/main と合うとの判定（観点(a) 指摘なし）。
- 指摘 1 の画面の分け方の根拠は Opus が origin/main で確かめた（`frontend/src/pages/schedule/schedule-utils.ts:26,57,353` に `source`）。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 高 | Google から取り込んだ予定を繰り返しに変えると、全部取り直しの掃除で消える。Google にしか無い中身も消える | §12.5（422）・画面で選ぶ欄を出さない・G79・§12.10 |
| 2 | 中 | all で選び方を替えるとき patch を使い、Google 側の例外の回の扱いが確かめていない | §12.7（始まり・終わり・選び方が変わる all は消して作り直す） |
| 3 | 中 | 途中の回で all・繰り返さないにしたとき残る 1 件の日時が決まっていない | §12.5（押した回の日時）・G79 |

#### 審査5（2026-11-11 21:45〜21:47 UTC・クラウドの Opus・対象 3c45c85e6）

- 判定: REVISE。実行記録 cse_01W47tdibdRf8vgEn4WfCsew。観点(a): 4 回目の指摘 1〜3 は直っており、引いた file:行（google_webhook.py:300・:340-346／schedule-utils.ts:353／calendar.py:122,431,446,497-508,523,538／calendar_service.py:129,305-309,551,573-581,652／google_calendar.py:390・:430）は origin/main と合うとの判定。
- 記録の制約: 指摘の echo は実行記録の表示で途中から切れた。下の 2 件は、読めた冒頭（指摘1 の「design.md:1424 と :1433 が食い違う」）と VERDICT の理由の文（「all で none にしたときの日時の決め方」「選ぶ欄を出さない決まりが §12.6 に無い」）から取った。切れた部分の細かい言い分は読めていない。審査6 で直しが足りるかを確かめる。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 中 | all で繰り返さないにしたとき、残る日時（押した回の日時）と、all で始まりを変えたときのずらし（元の始まり＋差）のどちらを使うかが食い違う | §12.5 のずらしの項に「none のときはずらしを使わず、残る日時の決まりだけで決める・Google へ送る本文も同じ」を足した |
| 2 | 中 | 取り込んだ予定で選ぶ欄を出さない決まりが §12.6 に無く、画面の実装役が見落とす | §12.6 に出さない場合（取り込んだ予定・Meet 付き）と Meet の行との関係を足した・§12.10 の画面の試験 |

#### 審査6（2026-11-11 21:52〜21:54 UTC・クラウドの Opus・対象 d2c6cc7e6）

- 判定: REVISE。実行記録 cse_01W47tdfdFL4K94G1ecHvRnR。指摘は 1 件ずつ別の echo で出させ、全文を読めた（審査5 の切れた記録の 2 件は、この回で直っていると判定された）。観点(b) 新しい食い違いなし。観点(c) 下の 2 件のほかに迷う所なし。
- 指摘 2 の根拠は Opus が origin/main で確かめた（`frontend/src/pages/schedule/SchedulePageImpl.tsx:976` の `draft.addMeet`・`frontend/src/pages/schedule/ScheduleDraftFields.tsx:300` の `MeetRow` の onChange）。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 軽 | all の始まりの項で「Google へ送る本文はずらした後の値から作る」の文が none の文の後ろにあり、none でもずらすと読める | §12.5 の文の順を入れ替え、頭に「none 以外のときは」を付けた |
| 2 | 中 | 繰り返しを選んだら Meet の行を隠すだけで、押し済みの `addMeet` が残り `add_meet` が送られて 422 になる | §12.6（繰り返しに変えたら `addMeet` を false に戻す）・§12.10 の画面の試験 |

#### 審査7（2026-11-11 21:59〜22:00 UTC・クラウドの Opus・対象 293a081d7）

- 判定: **APPROVE**。実行記録 cse_01W47tdfZfmqTZPq847uepVp。指摘は 1 件ずつ別の echo で出させ、全文を読めた。
- 観点(a): 6 回目の指摘 1・2 は直っている（根拠の行 `frontend/src/pages/schedule/SchedulePageImpl.tsx:976`・`frontend/src/pages/schedule/ScheduleDraftFields.tsx:300` は origin/main と一致）。観点(b): 新しい食い違いなし（下書きは開くとき `addMeet` が false で始まる `frontend/src/pages/schedule/SchedulePageImpl.tsx:927`・`:1120`）。観点(c): 実装役が迷う所なし。
- 体裁の指摘 1 件（§12.5 の句点の後の余分な空白）は直した。
- これは同じ AI（Opus）による審査で、独立した第二者の審査ではない。設計の合格は、PO の成功条件の決定・実装の開始の承認を兼ねない。

#### 審査7 の後の直し（2026-11-12・PO の問いから）

- PO の問い「繰り返しを消すときの動きも把握したか？」で Opus が読み直し、抜けを 2 つ見つけた。(1) 「これ以降」で消すとき Google へ何を送るかが書かれていなかった（直すときの following だけだった）。(2) 「すべて」で消すとき Google 側が全部消えるかを、今の消す道に任せていて、書いていなかった。あわせて、G74 は消したときの結果がはっきりしていなかった。
- PO の選択「1」で Google の消し方を測り（recon §9.5 U6）、§12.2 G74・§12.5 following の UNTIL・§12.7 の消すとき・§12.12 を直した。

#### 審査8（2026-11-11 23:10 UTC・対象 bedee4477）: REVISE

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 中 | 消すときの following・all で例外の行に送らないとしたが、直した回が Google で消えるかは U6 で試していない | §12.7 消すとき（例外の行にも cancelled を送る・失敗は警告だけ）・§12.10 |
| 2 | 低 | 読み戻しの「Google の出し方を確かめていない」が U6 で古くなった | §12.5 読み戻し（理由を選ぶ欄に無い文字のためと書き直し） |
| 3 | 中 | G74 の「先に消した回・直した回も含む」を今の判定方法で○×にできない | §12.2 G74 の判定方法 |

- 審査役は 3 択とも今のコードの道具（`backend/app/services/google_calendar.py:413,430`・`backend/app/services/calendar_service.py:503-504,509-510`）で作れること、UNTIL の前の日の終わりが U6 の表示と合うことを確かめた。

#### 審査9（2026-11-11 23:16 UTC・対象 c81489a2e）: REVISE

審査8 の指摘 1〜3 は直っていると確かめた。そのうえで次の 3 件。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 中 | §12.10 の前半の件数（following は patch 1 件だけ・all は delete 1 件だけ）が §12.7 の直しと食い違う | §12.10 |
| 2 | 中 | 直すときの following と消して作り直す道も例外の行を消すのに、Google の直した回へは送らず、消すときと扱いが割れた | §12.7（例外の行を消す道はどれも同じ送り） |
| 3 | 低 | 例外の回と元の予定への送りの順番が無い。送りごとの `try` も無い | §12.7（例外の回を先・1 件ずつ別の `try`） |

#### 審査10（2026-11-11 23:22 UTC・対象 855c059e9）: REVISE

審査9 の指摘 1〜3 は直っていると確かめた。そのうえで次の 3 件。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 低 | §12.10 の件数の文から「`is_cancelled = false` で `google_event_id` あり」の条件が落ちた | §12.10 |
| 2 | 中 | 直す道に「消す前に id を読み、commit の後に送る」が無い。今の直す道の形では送り先が 0 件になる | §12.7・§12.10 |
| 3 | 中 | 元の予定への送りが失敗しても新しい予定を送ると、Google で回が重なる | §12.7（失敗したら新しい予定を送らず `sync_status = 'failed'`）・§12.10 |

#### 審査11（2026-11-11 23:29 UTC・対象 71168e171）: REVISE

審査10 の指摘 1〜3 は直っていると確かめた。そのうえで次の 3 件。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 低 | 「失敗したら `'failed'`」が消す道にも効くと読め、消すときの「警告だけ」と食い違う | §12.7（直す道だけに効く・消す道は警告だけ）・§12.10 |
| 2 | 中 | 消して作り直す道で delete は通り create だけ失敗すると、行が Google で消えた古い id を持ち続ける | §12.7（`google_event_id`・`sync_origin_id` を NULL）・§12.10 |
| 3 | 低 | 直すときの following で `'failed'` にする行が決まっていない・送り直す仕組みが無い | §12.7（行ごとに決めた・送り直しは作らない）・§12.10 |

#### 審査12（2026-11-11 23:35 UTC・対象 50ce0c15e）: REVISE

審査11 の指摘 1〜3 は直っていると確かめた。そのうえで重さ低の 2 件。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 低 | 「元の行は `'synced'` のまま」とあるが、今の直す道は直す前に `'pending'` を書く（`backend/app/services/calendar_service.py:372`） | §12.7（UNTIL の patch が通ったら `'synced'` に書く）・§12.10 |
| 2 | 低 | 直す道の this と all（決まり以外だけ）の送りが失敗したときの行の扱いが表に無い | §12.7（どちらも `'failed'`）・§12.10 |

#### 審査13（2026-11-11 23:42 UTC・対象 31152d584）: REVISE

審査12 の指摘 1〜2 は直っていると確かめた。そのうえで重さ低の 1 件。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 低 | 「`'pending'` のまま残す行は作らない」が、Google に送らない場合の今の動き（`backend/app/services/calendar_service.py:372`・`:391`）と食い違う | §12.7（送りを試して通った行だけ `'synced'`・送らない場合は今と同じく `'pending'`） |

#### 審査14（2026-11-11 23:51 UTC・対象 3899d4cde）: REVISE

審査13 の指摘 1 は直っていると確かめた（`backend/app/services/calendar_service.py:372`・`:391`・`:409-415` と一致）。そのうえで重さ低の 3 件。列の既定値が `'synced'` であることは Opus が origin/main の `migrations/078_create_calendar_events_tenant.sql:59` で確かめた。

| # | 重さ | 指摘 | 直した所 |
|---|---|---|---|
| 1 | 低 | 送らない場合に `'pending'` のまま残ることを確かめる試験が §12.10 に無い | §12.10 |
| 2 | 低 | 新しく作る行（following の新しい元の行・this の例外の行）の insert のときの `sync_status` が書かれていない。列の既定値は `'synced'` | §12.7（`'pending'` を明示） |
| 3 | 低 | 送らない条件「`google_event_id` が無い」を新しく作る行に当てると一度も送らない読みになる | §12.7（新しい行は元の行の id と同期の向きで決める） |

#### 審査15（2026-11-12 00:02 UTC・対象 ac42be185）: APPROVE

審査14 の指摘 1〜3 は origin/main の `migrations/078_create_calendar_events_tenant.sql:59`・`backend/app/services/calendar_service.py:266`・`:391` と合う形で直っていると確かめた。§12 の他の所との食い違いは無い。作り始めを止めない重さ低の推奨が 1 件。

| # | 重さ | 推奨 | 直した所 |
|---|---|---|---|
| 1 | 低 | 消すときの this で新しく作る消した印の例外の行の `sync_status` が決まっていない（書かないと既定値の `'synced'`） | §12.7（insert で `'pending'` を明示・消す道は変えない・一覧に出ない）。再審査はしない（審査7 までの推奨の直しと同じ扱い） |

### 12.14 PO の承認（2026-11-12・便15 の成功条件と実装）

- PO に聞いた中身: 成功条件 G69〜G79 の 11 件（編集画面の終日の右の選ぶ欄・7 つの値・日週月の並び・詳しくの行・保存と削除の 3 択の小窓・3 択の結果と Google 側でも消えること・動かすときの 2 択・Google に同じ繰り返しで出て二重にならない・今ある予定は変わらない・選び方を後から変えられる・試験の見張り）。Opus が決めた点として「毎月 最終○曜日」を 7 つ目に足すこと・繰り返しの予定に Meet を付けないこと・Google で作った予定には選ぶ欄を出さないこと。選択肢「1. この11件で決める【おすすめ】（…選ぶと、裏側の仕組みから作り始めます）」。
- PO の答え（原文）: 「1」
- これで G69〜G79 と上の 3 点を承認とし、便15A（裏側・移行あり）から作り始める。便15A の GO は ADR-136 の委任の手順で記録する。
