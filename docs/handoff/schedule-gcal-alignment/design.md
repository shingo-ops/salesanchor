# design: 予定の画面を Google カレンダーに寄せる 段1（2026-11-04）

recon: `docs/handoff/schedule-gcal-alignment/recon.md`（以下 R§0〜R§7）
見本: canvas「予定の画面 完成予定」（週・月・一覧・操作と近道の 4 枚。PO「1」で承認）
状態: 設計案作成済み（同一 AI の自己審査 §9 済み）。成功条件（§2）は PO 承認済み（2026-11-04「1」）。クラウドの設計審査 1 回目は 3 便とも REVISE（審査の記録 architect-review.md・枝 `release/schedule-gcal-alignment-review`）→ 改訂 1 で指摘を反映（§12）。再審査（審査の記録 architect-review-2.md・枝 `release/schedule-gcal-alignment-review2`）は 便1 = APPROVE／便2 = REVISE（軽い）／便3 = REVISE。改訂 2 で便1 の追記を反映し、便1 の実装カード（§11-1）を出した。便2・便3 は改訂待ち。改訂 3（§14）で便2 の REVISE（N-5・N-11・N-12）を反映した。N-5 は PO が「便2 の中で裏側も含めて直す」を選んだ（2026-11-04「1」）。クラウドの再審査 3 回目（審査の記録 architect-review-3.md・枝 `release/schedule-gcal-bin2-review3`・HEAD 6f5deecff）で便2 = APPROVE。書き足し N-14〜N-19 を便2 の実装カード（§11-2）に入れた（§15）。便2 の実装は、PO が本番で K1〜K7 を見たあと（§4）。便3 は改訂待ち。

## 1. 目的（PO の言葉で）

予定の画面の見た目と操作を Google カレンダーに近づける。作る小窓が画面から切れないようにする。アプリから Google Meet を付けられるようにする。
段1は PO 1 人で動作確認する範囲（Meet は Google をつないだ PO 本人の予定だけ）。段2（全員が自分の Google をつなぐ）は段1の確認後に別の設計で行う。

## 2. 成功条件（PO が画面で ○× を付けられる形）

| # | 便 | 基準 | 検証方法 |
|---|---|---|---|
| K1 | 1 | 作る・詳しく・直すの小窓の保存（または閉じる）ボタンと題名が、どの予定・どの空き枠を押しても画面の中に全部見える。「詳しく入れる」で小窓が伸びても同じ | 自動試験: (a) `fitPopover` の純粋な関数で、画面の高さ 600・768・900px、横 1024・1280・1920px の 9 通り × 小窓の高さ 3 種（240px・400px・上限＝min(544px, 画面の高さ−24px)）＝27 件で、画面の一番下と一番右の枠を押したときの四角が画面の内側に収まる。(b) 部品の試験 2 件: 測った値（`getBoundingClientRect` を差し替え）で位置が当たること／中身が伸びたら測り直すこと。PO は自分の画面で一番下の枠（23 時台）を押し、「詳しく入れる」も押して保存ボタンが見えれば ○ |
| K2 | 1 | 小窓が画面より高いとき、見出しの行（閉じる・直す・消すのボタンの行）と保存の行は動かず、間の欄だけが動く | 自動試験: 高さ 600px で「詳しく入れる」を開き、中を一番下まで動かしても保存ボタンの位置が変わらない。PO は画面を小さくして確かめる |
| K3 | 1 | 空き枠を押すと、題名・時刻・終日・種類・社員にも見せるだけの短い小窓が出る。「詳しく入れる」で今の全部の欄（場所・説明など）が出る | PO が週の表示で空き枠を押して見る |
| K4 | 1 | 月の表示で、1 つの予定が 1 行（担当者の色の丸・時刻・題名）で出る。2 行に折れない | PO が今月の表示で見る。題名が長いと末尾が「…」になれば ○ |
| K5 | 1 | 月の表示の「他 ◯ 件」を押すと、その日の予定が全部並んだ小窓が出て、そこから予定を押すと詳しくが出る | PO が予定の多い日で押して見る |
| K6 | 1 | 表示の切り替えに「一覧」が増え、選んだ日から 30 日分の予定が日付ごとに並ぶ（予定の無い日は出ない） | PO が「一覧」を押して見る |
| K7 | 1 | キーボードの近道が効く: T 今日／J・→ 次／K・← 前／D 日／W 週／M 月／A 一覧／C 作る／Esc 閉じる／? 近道の一覧。文字を入れている最中は効かない（Esc だけは入力欄の中でも小窓を閉じる。変換中は閉じない） | 自動試験 20 件すべて合格: 効く 12 件（T・J・→・K・←・D・W・M・A・C・Esc・? がそれぞれ効く）＋入力・修飾・開いている間の 8 件（入力欄の中で文字キー／入力欄の中で Esc は閉じる／変換中の Esc は閉じない／Ctrl 付き／⌘ 付き／Alt 付き／小窓が開いている間の文字キー／近道の一覧が開いている間の文字キー）。PO は T・W・M・? を押して見る |
| K8 | 2 | 週・日の表で、空いた時間を上から下へ引っぱると、その長さの枠と短い小窓が出る（15 分きざみ） | PO が引っぱって作って見る |
| K9 | 2 | 自分が直せる予定をつかんで別の時間・別の日へ動かせる。下の端を引っぱると終わる時刻が変わる。離すと保存され、Google に送ってある予定は Google でも変わる | PO が動かした後、Google カレンダーでも同じ時刻で、題名・終日・説明・場所が変わっていなければ ○。自動試験: 動かしたときに送る中身に題名・終日・説明・場所が入っている |
| K10 | 2 | 直せない予定（他人の予定・シフト）はつかめない | 自動試験: 直せない予定で押して引いても時刻が変わらない |
| K11 | 2 | 月の表示で、複数日・終日の予定が日をまたぐ 1 本の帯で出る | PO が複数日の予定のある月で見る |
| K12 | 3 | PO が作る・直す小窓で「Google Meet を付ける」を入れて保存すると、詳しくに「Google Meet で参加」が出て、押すと Meet が開く。Google カレンダー側の同じ予定にも Meet が付いている | PO が 1 件作って両方で見る |
| K13 | 3 | PO 以外の人には「Google Meet を付ける」が出ない。裏側を直接呼んでも Meet は付かない（断られる）。作るときも直すときも同じ | 自動試験 4 件: つないだ本人以外が Meet 付きで作る→422・表に行が増えない・Google に送られない／本人以外が Meet 付きで直す→422・表が変わらない・Google に送られない |
| K14 | 3 | Google 側で Meet を付けた予定（Google で作って取り込んだ予定）にも「Google Meet で参加」が出る。前提: 同期方式が bidirectional（取り込みが動く方式。ADR-1059）。アプリで作った予定に Google 側で後から付けた Meet は対象外 | PO が Google で Meet 付きの予定を作り、15 分以内にアプリで見る（取り込みは 15 分おき `backend/app/tasks/google_calendar_sync.py:4`） |

## 3. 対象と対象外

- 対象: 上の K1〜K14。便1 は画面だけ。便2 は画面＋裏側の関数 1 つ（終日の予定を Google へ送る形の直し・表と移行は触らない・PO 2026-11-04「1」）。便3 は画面＋裏側＋表に列を 1 つ足す。
- 対象外:
  - 段2（全員が自分の Google をつなぐ・Google の公開審査）。別の設計で行う
  - 予定を探す（「/」の近道を含む）。今の虫めがねボタンは押しても何も起きない（R§4）。探す機能は別テーマとして PO に出す
  - Meet を外す操作（付けた Meet を消す）。付けるだけにする
  - 種類の色の直書きのトークン化（R§6・既知の残件）
  - 狭い画面（1023px 以下）の並びの作り直し。今の並びを保ち、引っぱり操作はマウスだけ（指での引っぱりは対象外）
  - Google のロゴや画像を使うこと。形と操作だけを寄せる

## 4. 便の分け方と順番

| 便 | 中身 | 危険な道（`migrations/` 等） | 合流 |
|---|---|---|---|
| 便1 | 小窓の置き場所・短い作る小窓・月の 1 行・他◯件・一覧・近道 | 無し | CI 緑＋審査で委任 GO |
| 便2 | 引っぱって作る・動かす・長さを変える・月の帯・終日が Google で 1 日前にずれる不具合の直し（裏側の関数 1 つ） | 無し（`migrations/`・`.github/workflows/deploy.yml`・本番 `scripts/` に触れない） | 同上 |
| 便3 | Meet（裏側・列 1 つ・ADR） | 有り | PO の「GO #番号」が要る（ADR-135・136） |

便1 が本番に出て PO が K1〜K7 を見たあと、便2 に進む。便3 は便2 と並べてよいが、カードを出す前に §7-3 の前提確認を済ませる。

## 5. 変更前後

### 5-1. 便1 小窓の置き場所（K1・K2）

変更前（`frontend/src/pages/schedule/SchedulePageImpl.tsx:122-144`）: 高さ 420px の決め打ちで位置を出す。

変更後:
- `frontend/src/pages/schedule/schedule-utils.ts` に純粋な関数 `fitPopover(anchor, size, viewport, margin)` を足す。`size` は出したあとに測った幅と高さ。
  1. 横: 押した枠の右に置けなければ左に置く。どちらも入らなければ画面の中に押し戻す（日の表示の横に広い空き枠では枠に重なる位置に出る。今の `buildPopoverPosition` と同じで、許容する）。
  2. 縦: 押した枠の上端にそろえ、下が出るなら上へずらす: `top = clamp(anchor.top, margin, viewportH − h − margin)`。
  3. 高さの上限は今の CSS（`frontend/src/pages/schedule.css:683` `max-height: min(var(--schedule-popover-max-h), calc(100vh - var(--space-6)))`。`--space-6` = 24px = 上下の余白 12px×2）に任せ、`fitPopover` は高さを返さない。CSS が h ≤ 画面の高さ−24px を保つので、2 の式は常に画面の内側に収まる。inline の `maxHeight` は使わない（ESLint `frontend/eslint.config.js:111` が数値の `maxHeight` を禁止・ADR-067）。
  - `margin` は 12（`frontend/src/tokens.css:76` `--space-3: 12px` と同じ値。数字の理由をコメントに書く。前例 `frontend/src/components/Popover.tsx:53` `const margin = 8;`）。
- 小窓の部品で `useLayoutEffect` を使い、出したあとの `getBoundingClientRect()` で測って `fitPopover` を呼ぶ。測る前は `visibility: hidden` にして、ずれた位置が一瞬見えないようにする（前例 `frontend/src/components/Popover.tsx:110` の `visible`）。
- 測り直すきっかけは 2 つ: 画面の大きさが変わったとき（`resize`）と、小窓の中身の高さが変わったとき（小窓自身を `ResizeObserver` で見る。「詳しく入れる」で伸びたときなど）。jsdom には `ResizeObserver` が無いので、無ければ付けない（`typeof ResizeObserver !== "undefined"` で確かめる）。部品の試験では差し替えて呼ぶ。
- `frontend/src/pages/schedule.css:679-693` `.schedule-popover`: 外側の `overflow: auto` をやめて `overflow: hidden`。見出し（`.schedule-popover__header`）と下の帯（`.schedule-popover__footer`）は縮まない（`flex: none`）。間の `.schedule-popover__body` だけ `flex: 1 1 auto; min-height: 0; overflow: auto`。
- 金型 `frontend/src/components/Popover.tsx` は使わない。理由: 押す相手を子に持つ作りで、押した場所の四角だけを渡せない（R§1）。金型を直すと他の画面に響く。置き場所の計算の考え方は金型と同じ（測ってから画面の中へ押し戻す）にそろえる。
- 試験: `frontend/src/pages/schedule/schedule-utils.test.ts` に `fitPopover` の 27 件（K1 (a) の 9 通り×高さ 3 種）と、右にも左にも入らない場合の 1 件と、枠が無いとき真ん中に出る 1 件（5-5 の `c`）。`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` に K1 (b) の部品の試験 2 件。

### 5-2. 便1 短い作る小窓（K3）

- 作る小窓（`mode === "create"`）で、最初は 題名・開始と終了（日付と時刻）・種類・社員にも見せる・終日 だけを出す。
- 下の帯の左に「詳しく入れる」（`Button variant="ghost"`）。押すと今の全部の欄（`frontend/src/pages/schedule/SchedulePageImpl.tsx:285-410`）を出す。伸びたら 5-1 の `ResizeObserver` で置き直す。入れた中身は消えない（同じ `draft`）。
- 直す小窓（`mode === "edit"`）は今どおり全部の欄。
- 新しい文字: `schedule.moreOptions`（ja「詳しく入れる」・en「More options」）。

### 5-3. 便1 月の 1 行と他◯件（K4・K5）

- `frontend/src/pages/schedule/SchedulePageImpl.tsx:805-823` の札を、背景なしの 1 行に変える: 担当者の色の丸（今の `ownerMeta.color`。色の意味は今と同じ「担当者」）・開始時刻（終日は時刻なし）・題名。`white-space: nowrap; overflow: hidden; text-overflow: ellipsis` を札全体にかける。月の札から種類の札（`:815-821`）は外し、種類は詳しくで見る。
- 終日の予定は今の札（背景が担当者の色）のまま 1 行にする（便2 で帯にする）。
- `:826-828` の `<span>` を `<button type="button">` にし、押すとその日の一覧の小窓を出す。押したときは `event.stopPropagation()` する（日の枠 `:797` の `onClick` が作る小窓を開くため。予定の札 `:810` と同じ止め方）。小窓は 5-1 の置き場所の計算を使う。中の予定を押すと今の詳しくを出す。
- 文字: `frontend/src/locales/ja.json:3195` `"moreCount": "+{{count}}件"` → `"他 {{count}} 件"`。en は `"{{count}} more"`。
- 新しいトークン（`frontend/src/tokens.css` の予定の段 `:392-416` に足す）: `--schedule-month-dot-size: 8px;`

### 5-4. 便1 一覧の表示（K6）

- `frontend/src/pages/schedule/schedule-utils.ts:1` `ScheduleView` に `"list"` を足す。`toRangeStart` は選んだ日の 0 時、`toRangeEnd` は 30 日後。前後の移動（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1090-1096`）は 30 日ずつ。
- 表示の切り替え（`:1179-1190`）に「一覧」を足す。ラベルは `` t(`schedule.${nextView}View`) ``（`:1188`）で引くので、文字のキーは `schedule.listView`（ja「一覧」・en「Schedule」。今の `schedule.dayView`・`weekView`・`monthView` は `frontend/src/locales/ja.json:3215-3217`）。
- 一覧の部品は新しく `ScheduleListView`（`frontend/src/pages/schedule/SchedulePageImpl.tsx` の中）。日付ごとに 1 段、左に日付の丸（今日は `--schedule-today`）、右に予定の行（色の丸・時刻・題名・種類）。行は `<button>` で、押すと詳しく。予定の無い日は出さない。全部無いときは今の空の表示を使う。
- 見出しの日付は `Intl.DateTimeFormat`（今の `formatDayLabel` と同じ道具）で出す。
- 「月か日か、それ以外は週」と分けている箇所に一覧を入れる（触る場所の全部）:
  - `frontend/src/pages/schedule/SchedulePageImpl.tsx:115-120` `formatRangeTitle`: 一覧は「開始日 - 30 日後の前日」。
  - `:935` 左の小さい月の基準: 一覧は `startOfMonth(anchorDate)`（週と同じ）でよい。
  - `:973` 今の時刻へ動かす処理: 一覧でも動かさない（`view === "month" || view === "list"` で戻る）。
  - `:1098-1102` `viewDays`: 一覧は使わない（一覧は `ScheduleListView` が範囲の予定から日を作る）。
  - `frontend/src/pages/schedule/schedule-utils.ts:147-157` `toRangeStart`・`toRangeEnd`。
- 試験: `toRangeStart`・`toRangeEnd` の一覧 3 件（30 日分・月をまたぐ・年をまたぐ）。

### 5-5. 便1 キーボードの近道（K7）

- `frontend/src/pages/schedule/SchedulePageImpl.tsx` の本体に `useEffect` で `window` の `keydown` を 1 つだけ付ける（外すときに必ず外す）。
- 判定の順番（上から見て最初に当たったもので決める）:
  1. `event.isComposing || event.keyCode === 229` → 何もしない（変換の取消を優先。Safari は変換を決めた Enter で `isComposing` が偽になるため 229 も見る）。
  2. 近道の一覧（Modal）が開いている → 何もしない（Esc は金型 `frontend/src/components/Modal.tsx:73-80` が閉じる。ページ側は何もしない）。
  3. `Escape` → 予定の小窓（作る・詳しく・直す、と 5-3 の「他 ◯ 件」の日の一覧の小窓）が開いていれば閉じる。入力欄の中でも効く。
  4. 予定の小窓（5-3 の日の一覧の小窓を含む）が開いている → ここで終わり（文字キーは効かない）。
  5. `Ctrl`・`⌘`（`metaKey`）・`Alt` が押されている → 何もしない。`Shift` は除外しない（`?` は Shift で出すため）。
  6. `event.target` が `input`・`textarea`・`select`・`[contenteditable]` → 何もしない。切替スイッチ `Toggle` は `<input type="checkbox">`（`frontend/src/components/Toggle.tsx:27-31`）なのでここで止まる（安全側）。`<button>` にフォーカスがあるときは効く（Google カレンダーと同じ）。
  7. `event.key` が 1 文字のときだけ小文字にそろえて（CapsLock 対策）キーの表で引く。`ArrowRight` などの名前のキーはそのまま比べる。押しっぱなし（`event.repeat`）でも効く（`j` を押し続けると進み続ける。Google と同じ）。
- キー: `t` 今日／`j`・`ArrowRight` 次／`k`・`ArrowLeft` 前／`d` 日／`w` 週／`m` 月／`a` 一覧／`c` 作る（今日の 9 時の短い小窓。押した枠が無いので、週・日の表示でも月・一覧の表示でも画面の真ん中に出す。今の `buildPopoverPosition` の枠なしの道 `frontend/src/pages/schedule/SchedulePageImpl.tsx:126-131` と同じ考え方で、`fitPopover` に枠が無いときは真ん中を返す 1 件を足す）／`Escape` 小窓を閉じる／`?` 近道の一覧。12 キー。
- 近道の一覧は金型 `frontend/src/components/Modal.tsx` で出す。キーの見た目は新しいクラス `.schedule-kbd`（トークンだけで書く）。
- 文字: `schedule.shortcuts.title` と各キーの説明 10 個（ja・en 同じキー。J と → ・K と ← は 1 行にまとめる）。
- 試験: K7 の 20 件を `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` に置く。

### 5-6. 便2 引っぱる・動かす・長さを変える・月の帯（K8〜K11）

- 外部の部品は入れない（今は無い・R§4。前に FullCalendar を外した経緯 `frontend/src/pages/schedule/SchedulePageImpl.tsx:4`）。Pointer Events（`onPointerDown`・`setPointerCapture`）で書く。
- 時刻への換算は純粋な関数にして `frontend/src/pages/schedule/schedule-utils.ts` に置く: 位置(px) → 分 = `px / 行の高さ × 60` を 15 分に丸める。行の高さは関数の引数で受け取り、画面からは今ある `rowHeight`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:651`。中身は `DEFAULT_ROW_HEIGHT` `:91`）を渡す。今の朝の位置の計算（`:1184`）と同じ値を使い、3 つ目の置き場所を作らない（N-11）。`getComputedStyle` は使わない（試験の環境では空の文字を返す）。`DEFAULT_ROW_HEIGHT` とトークン `--schedule-row-height`（`frontend/src/tokens.css:400`・48px）が 2 か所にある状態は今からあるもので、便2 では増やさない（§7 の 6）。位置(px) は「押した日の列の `getBoundingClientRect().top` からの差」で測る（列の四角は表が縦に動いた分を含むので、動いた量を別に足さない）。
- 引っぱって作る: 空き枠で押して 4px 以上動いたら引っぱりとみなし、薄い枠を出す。離すと 5-2 の短い小窓。4px 未満なら今の「押して 1 時間」。
- 動かす・長さを変える: 今の `canEditSelected`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1336-1338`。選んだ 1 件用）の中身を、予定を 1 件受け取る関数 `canEditItem(item)` に切り出して両方で使う（判定の中身は変えない）。かつ `source !== "shift"` の予定だけ。
- 離したときの送り方（Google の予定を壊さないため）: `PATCH /calendar/events/{id}` に、今の保存（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1247-1257`）と同じ形で、題名・開始・終了・終日・説明・場所を送る（題名などは動かす予定の今の値）。種類（`category`）は送らない: 直す口の受け取り `UpdateEventBody`（`backend/app/routers/calendar.py:114-121`）に `category` が無く、送っても捨てられる（N-12）。開始と終了だけを送ると、裏側が Google へ送る中身を送られた欄だけで作る（`backend/app/services/calendar_service.py:314` → `:512` `"summary": payload.get("title", "")`）ため、Google 側の題名が空で上書きされ、終日も崩れる（`:517-522`）。動かす操作のための裏側の変更は無い（裏側で触るのは次の終日の直しだけ）。`calendar_type` は送らない（見せ方は変えない）。失敗したら元の位置に戻し、今の失敗の帯を出す。
- 月の帯: 終日・複数日の予定を週の行ごとに `grid-column: 開始 / 終了+1` の帯で出す。月で日をまたいで動かすのも同じ PATCH。帯は帯の段に出し、1 日 3 件（`:801`）と「他 ◯ 件」の数には入れない（3 件と数えるのは時刻つきの予定だけ）。
- 新しいトークン: `--schedule-drag-ghost-bg`（`var(--calendar-google-blue-light)` を指す。参照先はライト `frontend/src/index.css:184`・ダーク `:384` の両方にある）。ADR-067「新規トークン追加手順」に従い、ADR の表も直す。
- 試験: 換算の関数（境目・15 分丸め・日をまたぐ）と、直せない予定が動かないこと（K10）と、動かしたときの送る中身に題名・終日・説明・場所が入っていること（K9）。
- 終日が Google で 1 日前にずれる不具合の直し（N-5・PO 2026-11-04「1」で便2 に入れる）:
  - 今の形（事実・origin/main 0f297666c）: 画面は終日を `combineDateTime(日付, "00:00").toISOString()` と `combineDateTime(日付, "23:59").toISOString()` で送る（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1251-1252`）。日本時間 7/1 00:00 は `2026-06-30T15:00:00.000Z` になる。裏側は Google へ送るとき、この文字の先頭 10 文字を日付にする（`backend/app/services/calendar_service.py:518-520` `str(start_dt)[:10]`）。開始は 6/30、終わりは 7/1 になる。Google の終日の終わりの日は「次の日」の意味なので、Google では 6/30 の 1 日だけの予定になる。
  - 取り込みの側（`_google_times` `backend/app/services/calendar_service.py:380-394`）は日本時間に直し、終わりの日から 1 日引いている。逆向きの送る側だけが崩れている。
  - アプリの表の値は正しい: 取り込みの上書きは `WHERE calendar_events.source = 'google'`（`:486` の ON CONFLICT の条件）で、アプリで作った予定は上書きしない。ずれるのは Google 側だけ。
  - 直し方: `_to_google_event_body` の終日の枝（`:518-520`）だけを変える。作る（`:226`）と直す（`:314`）の両方がこの関数を通るので、1 か所で両方直る。画面の送り方は変えない（画面と裏側の約束を変えない）。
    1. 値が日付だけ（`T` を含まない）のときは今のまま、そのまま Google へ渡す（今の試験 `backend/tests/test_calendar_service.py:93-105` がこの形）。
    2. 時刻つきのときは `_parse_dt`（`:32-37`）で読む。時差が無ければ日本時間とみなす（`replace(tzinfo=_JST)`）。`astimezone(_JST).date()` で日本時間の日付にする。
    3. 開始 = 開始の日付。終わり = 終わりの日付 + 1 日（`_google_times` の逆）。終わりが開始以前になるときは開始 + 1 日。
    4. 新しい定数・新しい表・新しい列は作らない。日本時間は今ある `_JST`（`:377`）を使う。
  - 試験（`backend/tests/test_calendar_service.py` の `TestToGoogleEventBody` に足す）:
    1. 画面が 7/1 の終日で送る形（`2026-06-30T15:00:00.000Z`／`2026-07-01T14:59:00.000Z`）→ 開始 `2026-07-01`・終わり `2026-07-02`
    2. 7/1〜7/3 の複数日（`2026-06-30T15:00:00.000Z`／`2026-07-03T14:59:00.000Z`）→ `2026-07-01`／`2026-07-04`
    3. `+09:00` の形（`2026-07-01T00:00:00+09:00`／`2026-07-01T23:59:00+09:00`）→ `2026-07-01`／`2026-07-02`
    4. 時差の無い形（`2026-07-01T00:00:00`／`2026-07-01T23:59:00`）→ `2026-07-01`／`2026-07-02`
    5. 行って戻る: 1 の結果を `_google_times` に通すと、日本時間 7/1 00:00〜7/1 23:59・終日になる
    6. 今の日付だけの試験（`:93-105`）がそのまま通る
  - すでに Google へ送ってずれている終日の予定は、この直しでは戻らない（アプリで直して保存すると正しく送り直される）。件数はまだ確かめていない（§7 の 7）。

### 5-7. 便3 Google Meet（K12〜K14）

- 表: 会社ごとの `calendar_events` に `meet_url TEXT NULL` を 1 つ足す（`migrations/` に新しいファイル。`migrations/20261103_200000_add_google_calendar_import_sync.sql:11-34` と同じ「会社ごとに回す・何度流しても同じ」書き方）。`scripts/run_all_migrations.sh` の末尾に 1 行登録する（前例 `:1217`。表を作るのは `:377` の `078`）。Meet の URL の置き場所はこの列 1 か所だけ。
- 裏側:
  - `backend/app/routers/calendar.py:104-112` `CreateEventBody` に `add_meet: bool = False`、`:114-121` `UpdateEventBody` に `add_meet: Optional[bool] = None` を足す。
  - Meet を付けてよいかの判定は 1 か所: `backend/app/services/calendar_service.py` に `async def can_add_meet(db, tenant_id, user_id) -> bool` を足す。中身は `_get_sync_target`（`:57`）を呼び、`sync_mode in ("bidirectional", "write_only") and connected_by == user_id` を返す（`:220-222` の送る条件と同じ式。`:222` も この関数を使う形に置き換え、式を 2 か所に置かない）。接続状態の口の `meet_available` もこの関数で出す。
  - 作る（口 `backend/app/routers/calendar.py:340` `create_event`）【改訂 4・N-1】: 判定は**口の中、サービスを呼ぶ `try`（`:352`）の前**で行う。`body.add_meet` が真で `await cal_svc.can_add_meet(db, tenant_id, user.id)` が偽なら、422「Google Meet は Google カレンダーをつないだ本人の予定にだけ付けられます」を返す。サービスは呼ばないので表にも Google にも何も入らない（今の口は `:359` の `except Exception` が `HTTPException` も拾って 500 に変えるため、サービスの中で 422 を出してはいけない）。サービスの `create_event`（`backend/app/services/calendar_service.py:180`）は、`add_meet` が真なら Google に送る中身へ `conferenceData.createRequest = {requestId: <毎回新しい uuid4>, conferenceSolutionKey: {type: "hangoutsMeet"}}` を足すだけ。`add_meet` は表の列ではないので INSERT（`:193`）の値には入れない。
  - 直す（口 `backend/app/routers/calendar.py:374` `update_event`）【改訂 4・N-1・N-3・N-13】: 口が今読んでいる行（`:391` `SELECT created_by_user_id, calendar_type, user_id FROM calendar_events WHERE id = :id`）に `google_event_id, meet_url` を足して読む（UPDATE の前に読む・N-3）。`payload.get("add_meet")` が真なら、サービスを呼ぶ `try`（`:421`）の前に次の 3 つを確かめ、1 つでも欠ければ 422 で何も変えない: (1) `can_add_meet(db, tenant_id, user.id)` が真 (2) `google_event_id` がある (3) `event_owner`（`:399`）== `user.id`（N-13。ADR の「本人の予定だけ」とそろえる。今の直す道は持ち主を見ずに送る `backend/app/services/calendar_service.py:309-310`・ADR-1057:30 の受け入れ点だが、Meet だけは本人に絞る）。`meet_url` がすでに入っていれば `add_meet` を外してからサービスへ渡す（頼み直さない）。サービスの `update_event`（`:259`）は、`add_meet` が真なら `patch` に `createRequest`（新しい `requestId`）を付ける。今は送る欄が 1 つも無いと `:289-290`（`if not set_clauses: return {"id": event_id}`）で何もせず戻るので、`add_meet` だけ送られた場合はこの早戻りの前に Meet を処理する。【改訂 5・R4-1】このとき（`set_clauses` が空のとき）は `_to_google_event_body`（`:509`）を使わない。この関数は `summary` を `payload.get("title", "")`（`:512`）で作り、時刻が無いと空の `dateTime` を作る（`:515-523`）ので、Google の予定の題を消すか断られる。代わりに `{"conferenceData": {"createRequest": …}}` だけを `patch` で送る。画面は直す小窓から送るとき今の保存（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1247-1273` `saveEvent`）と同じ全部の欄を送るので、通常はこの場合に当たらない。
  - 返事【改訂 4・N-2】: 作る（`backend/app/services/calendar_service.py:251`）・直す（`:290`・`:335`）の返事を `{"id": event_id, "meet_url": <表の meet_url。無ければ null>}` にする。口はそのまま返す（`backend/app/routers/calendar.py:365`・`:435` 付近の `return result`）。
  - `backend/app/services/google_calendar.py:377` `create_event`・`:392` `update_event` に `conference: bool = False` を足し、真のときだけ `conferenceDataVersion=1` を付けて呼ぶ。1 件を読む関数 `get_event(db, tenant_id, event_id)` を新しく足す（今は `get_events` `:348`・`create_event` `:377`・`update_event` `:392`・`delete_event` `:407` だけで、1 件を読む関数が無い）。
  - 返事の `hangoutLink` を `meet_url` に入れる。`conferenceData.createRequest.status.statusCode` が `pending` で `hangoutLink` が無いときは、`await asyncio.sleep(1)` をはさんで 2 回まで `get_event` で読み直す（同期の `time.sleep` は使わない）。それでも無ければ `meet_url` は空のままにし、警告を記録に残す（予定そのものは保存済み）。PO がもう一度「Google Meet を付ける」を押すと直す道を通り、新しい `requestId` で頼み直す。
  - 取り込み（`backend/app/services/calendar_service.py:410` `upsert_from_google`）: `google_event.get("hangoutLink")` を `meet_url` に入れる。INSERT の列と値に `meet_url` を足し、`:476-486` の `ON CONFLICT ... DO UPDATE SET` に `meet_url = EXCLUDED.meet_url` を足す（`source='google'` の行だけ・今の条件 `:486` のまま）。
  - 予定の一覧（`backend/app/services/calendar_service.py:134` の SELECT）: `ce.meet_url` を SELECT の**最後**（`created_by_name` の後）に足し、返す辞書に `"meet_url"` を足す（`r[0]`〜`r[17]` の番号をずらさないため）。
  - 接続状態の口（`backend/app/routers/google_calendar.py:242` `connection_status`）【改訂 5・R4-3】: 今は会社と DB しか受け取らない（`:243-244`）。`user: User = Depends(get_current_user)` を足し、`meet_available = await cal_svc.can_add_meet(db, tenant_id, user.id)` を返す。SELECT（`:247-253`）は今のまま。式は `can_add_meet` 1 か所だけに置き、この口で式を書かない。接続が無い会社では `_get_sync_target`（`backend/app/services/calendar_service.py:57-67`）が `('none', None)` を返すので、同じ式で偽になる。保存はしない（今ある値から毎回出す）。
- 画面の型: `frontend/src/pages/schedule/schedule-utils.ts:13` `ApiCalendarEvent` に `meet_url?: string | null`、`:46` `ScheduleItem` に `meetUrl?: string | null`、`:201` `normalizeEvent` で写す。
- 画面:
  - `meet_available` が真のときだけ、作る（短い小窓にも）・直す小窓に `Toggle`「Google Meet を付ける」。
  - 詳しくに `meet_url` があれば「Google Meet で参加」（金型 `ButtonLink`、新しい窓で開く・`rel="noopener noreferrer"`）。`https://meet.google.com/` で始まる URL のときだけ出す。
  - 送る中身【改訂 5・R4-5】: `saveEvent` の `body`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1249-1260`）に `add_meet: true` を入れるのは、`meet_available` が真で、かつ Toggle が入っているときだけ。直す小窓で予定にすでに `meetUrl` があるときは Toggle を出さず、「Google Meet で参加」だけを出す。
  - 保存のあと【改訂 4・N-2】: `saveEvent`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1247`）で `api.post<{id:number; meet_url:string|null}>`・`api.patch<…>`（`frontend/src/lib/api.ts:246`・`:253` は返事の型を受け取れる）の返事を受け取る。`add_meet: true` を送ったのに返事の `meet_url` が null なら、今ある知らせの帯 `setBanner({ type: "error", message: t("schedule.meetFailed") })`（`:1103` の状態・`:1473-1478` で `error-banner` として出る）を出す。新しい知らせの部品は作らない。予定そのものは保存済みなので小窓は閉じる。
  - 文字: `schedule.addMeet`・`schedule.joinMeet`・`schedule.meetFailed`（ja・en）。
- ADR: 新しい ADR を 1 つ起こす。中身: (1) Meet の URL は `calendar_events.meet_url` 1 か所 (2) 付けられるのはつないだ本人の予定だけ。作るも直すも 422 で止め、表にも Google にも何も残さない (3) ADR-1057 の線の内側。直す道の「持ち主を見ずに送る」受け入れ点（ADR-1057:30）は Meet には広げない (4) 取り込みは ADR-1059 の双方向のときだけ動く (5) アプリから作った予定の Meet はアプリから付ける。Google 側で足した Meet は取り込みで入らない（取り込みが直すのは `source='google'` の行だけ・`backend/app/services/calendar_service.py:486`）。`node scripts/generate-adr-index.js` を回す。`docs/adr/FEATURE-INDEX.md:34` に新しい ADR と ADR-1059 を足し、「取り込みは止めている」の古い書き方を今の形（双方向のとき 15 分おきに取り込む）に直す。
- 試験（裏側）: K13 の 4 件（作る 422・作る 422 で表に行が増えない・直す 422 で表が変わらない・どちらも Google に送らない）は**口の関数を直接呼ぶ試験**で書く。置き場所は口の試験が今ある `backend/tests/test_calendar_owner_api.py`（`from app.routers.calendar import (… update_event …)` `:10-14`、サービスを `patch("app.routers.calendar.cal_svc.update_event", new=AsyncMock())` で差し替える形 `:191`、`HTTPException` の 422 を待つ前例 `:240`）。【改訂 5・R4-2】口の SELECT が 5 列になるので、今の試験の部品 `_event_db`（`backend/tests/test_calendar_owner_api.py:178-182`。今は `first=(created_by, calendar_type, owner)` の 3 つを返す）に `google_event_id=None, meet_url=None` の既定つき引数を足し、5 つを返す形にする。今の試験 4 件（`:187`・`:212`・`:226`・`:240`）の呼び方は変えない。import（`:10-18`）に `create_event`・`CreateEventBody` を足す。作る 422 では `cal_svc.create_event` の差し替えが呼ばれないこと、直す 422 では `cal_svc.update_event` の差し替えが呼ばれないことで「表にも Google にも何も入らない」を確かめる（サービスだけの試験では 500 に変わる穴を見つけられない・N-1）。直す 422 は (1)〜(3) の欠け方ごとに 1 件ずつ。返事に `meet_url` が入ること／付かなかったとき null になること（N-2）。`can_add_meet` の真偽 4 通り（方式 3 種 × 本人かどうかの代表）。`add_meet` だけの直しで `patch` に `summary`・`start`・`end` を送らないこと（R4-1）。Meet を付けたときの `conferenceDataVersion=1` と `createRequest` の形、`pending` から読み直す道、取り込みで `meet_url` が入ること。

## 6. 代替案と選んだ理由

| 案 | 選ばなかった理由 |
|---|---|
| FullCalendar などの外部部品を入れて引っぱり操作を任せる | 前に外して内製の表にした（`frontend/src/pages/schedule/SchedulePageImpl.tsx:4`）。見た目をトークンで縛れない。今の表の作りを捨てることになる |
| 金型 `frontend/src/components/Popover.tsx` を直して予定の小窓に使う | 押す相手を子に持つ作りで合わない。直すと他の画面の小窓の動きが変わる。今回は同じ考え方の純粋な関数を予定の画面に置く |
| Meet の URL を `description` に書き込む | 説明の文と混ざる。Google から取り込んだ説明で上書きされる。置き場所が 1 か所にならない |
| Meet を全員に開く（段2 を先に） | 接続は会社で 1 つ（ADR-1057）。他人の予定がつないだ人の Google に入る。PO はまず自分だけで確かめると決めた |
| 便を 1 つにまとめる | Meet は表の列を足すので PO の GO が要る。画面だけの直しまで待たせない。1 回に 1 つ変えて測る |

## 7. リスクと対処

1. 近道が入力中に効いて文字が打てない → 5-5 の「効かない場合」を試験で確かめる（K7）。
2. 引っぱり中に押しただけの操作（今の 1 時間作成）が壊れる → 4px のしきい値で分け、両方を試験する。
3. Meet の作成が Google 側で断られる（Meet が使えないアカウント・管理者が止めている）→ 予定は保存し、`meet_url` は空、画面に「Google Meet を付けられませんでした」を出す（文字 `schedule.meetFailed`）。
   - 【改訂 5】Workspace の管理者が Meet を止めているとき、Meet 付きの作成が予定ごと断られるのか、予定は作られ Meet だけ失敗になるのかは、まだ確かめていない。予定ごと断られる場合、アプリの表には予定が残るが Google には入らず、`sync_status='failed'` になる（`backend/app/services/calendar_service.py:241-249`）。PO の Google アカウントでは本番で K12 を見るときに分かる。
   - 便3 のカードを出す前の確認（未解決の前提。済むまで便3 は「実装可能」にしない）:
     1. 本番の同期方式の今の値（R§5 未確認）。送る方式でなければ、PO に切り替えるか聞く
     2. 新しい会社の `calendar_events` がどの道で作られるか。`backend/app/services/tenant.py` に `calendar` の語は無かった（`grep -n -i "calendar" backend/app/services/tenant.py` 0 件）。新しい会社にも列が入る道を担当に調べさせる
     3. 予定の作成と Google 送信を試す今の試験の場所（R§7 未確認）
     4. 同期方式が `bidirectional` であること（K14 の前提。`write_only` では取り込みが止まる・ADR-1059「戻し方」）。1 と同じ読み取りで確かめる
   - 前提確認の結果（2026-11-05 00:37〜00:40 JST・本番の読み取り口 ADR-1024 と origin/main c310076ac の実物で確かめた）:
     1. 済み。`ai_ro.public__tenant_google_calendar_config` は 1 行だけ。会社 4・`sync_mode = bidirectional`・つないだ人あり。送る方式なので PO への切り替えの質問は要らない
     2. 済み。`calendar_events` を作るのは `migrations/078_create_calendar_events_tenant.sql:44`（今ある会社を回す）だけ。`backend/app/services/tenant.py` の `create_tenant_schema`（`:1658`）に `calendar` の語は 0 件。本番の会社は 1・3・4・5・6 の 5 社で、5 社とも `ai_ro.tenant_NNN__calendar_events` がある。便3 の移行は 078 と同じく今ある会社を回せば全社に列が入る。これから作る会社に表そのものが無い点は今からある抜けで、便3 の範囲外（残件）
     3. 済み。`backend/tests/test_calendar_service.py` の `TestCreateEvent`（`:231`。Google 送信の失敗 `:283`・つないだ人以外は送らない `:309`）と `TestToGoogleEventBody`（`:77`）。ほかに `backend/tests/test_google_calendar.py`・`backend/tests/test_google_calendar_webhook_receiver.py`
     4. 済み。1 と同じ読み取りで `bidirectional`。K14 の前提を満たす
   - §7 の 7 の基準の数（同じ読み取り）: 会社 4 の予定は 16 件。うち終日は 0 件、終日で Google に送ったものも 0 件。今の時点で Google 側にずれた終日の予定は無い。便2 の本番反映のあとにもう一度数える
   - 便3 に残るのは N-1・N-2・N-3（と任意の N-13）の設計の直しとクラウドの再審査
4. 小窓を測ってから置くので、一瞬ちらつく → 測る前は見えなくする（5-1）。
5. 月の札から種類の札を外すと種類が月で分からない → 詳しくと一覧では出す。PO が月で種類も見たいと言えば札を戻す（見本では外した形で承認済み）。
6. 行の高さが `DEFAULT_ROW_HEIGHT`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:91`）とトークン `--schedule-row-height`（`frontend/src/tokens.css:400`）の 2 か所にある（今からある）。片方だけ変えると引っぱりの時刻がずれる → 便2 では置き場所を増やさず、換算の試験で 48px を前提にした値を確かめる。1 か所にまとめるのは残件として台帳に残す。
7. すでに Google へ送ってずれた終日の予定が Google 側に残る → 直しでは自動で戻さない（送り直しは Google の予定を書き換える外向きの操作のため、勝手にしない）。便2 の本番反映のあと、件数を本番の読み取りで数えて PO に見せ、送り直すか聞く。
8. 直す口で種類（`category`）が保存されない（`backend/app/routers/calendar.py:114-121` に無い）。作る口も同じ（`CreateEventBody` `backend/app/routers/calendar.py:104-111` に無く、`backend/app/services/calendar_service.py:206` の既定 `"meeting"` が入る・N-17）。今の小窓で種類を選んで保存しても残らない、今からある不具合 → 便2 の範囲外。台帳に残件として残し、PO に別に出す。

## 8. 外部・過去事例の参照と我々への応用

- Google カレンダーの近道（出典: Google カレンダー ヘルプ「Use keyboard shortcuts in Google Calendar」https://support.google.com/calendar/answer/37034 、2026-11-04 に読んだ）: 次 `j`・`n`／今日 `t`／日 `1`・`d`／週 `2`・`w`／月 `3`・`m`／予定リスト `5`・`a`／作る `c`／一覧 `?`／戻る `Esc`。同じキーを使う。前へ（`k`）はこのページの読み取り結果に出てこなかった【未確認】。`j` と対になるキーとして `k` を使う。数字キー・`/`（探す）・`g`・`r`・`s` は今回入れない（探す機能が無い・設定画面は別）。
- Google Calendar API の Meet の付け方（Context7 で読んだ公式資料・R§5）: 5-7 の通りに従う。
- 過去事例（社内）: 予定の表は前に FullCalendar を外して内製にした（`frontend/src/pages/schedule/SchedulePageImpl.tsx:4`）。外部部品を戻さない根拠。小窓の位置ずれは金型 `frontend/src/components/Popover.tsx` で「測ってから押し戻す」に直した前例があり（`frontend/src/components/Popover.tsx:79` のコメント・押し戻しは `:80-87`）、同じ考え方を使う。
- 数字による効果の事例は持っていない。成功の判定は §2 の K で行う。

## 9. 設計審査（同一 AI による自己審査・独立した第二者レビューではない）

- 判定: 便1 = APPROVE（設計合格）／便2 = APPROVE／便3 = REVISE（§7-3 の前提確認 3 件が済むまで）
- 改訂 5 のあとの自己審査（2026-11-05）: 便3 = APPROVE（クラウドの再審査 4 回目は REVISE（軽い）。R4-1〜R4-5 を §17 のとおり直し、審査の条件「R4-1・R4-2 を直せばカードを書いてよい」を満たした）。便3 は表の列を足すので、実装のあとも PO の「GO #番号」が要る
- 改訂 4 のあとの自己審査（2026-11-05）: 便3 = REVISE のまま。§7-3 の 4 件は済み、N-1・N-2・N-3・N-13 は 5-7 に直した（§16）。クラウドの再審査で APPROVE が出るまで実装可能としない。便3 は表の列を足すので、実装のあとも PO の「GO #番号」が要る
- 根拠: 触る場所はすべて R の行番号で確かめた。色・余白は既存トークン＋新しいトークン 2 個。文字はすべて新しい `t()` のキー。金型は Toggle・Button・ButtonLink・Modal を使う。データの置き場所は Meet の URL 1 列だけで、ほかに写しを作らない。
- 未解決: §7-3 の 4 件。PO の画面での切れ方の実測（K1 で代える）。
- クラウドの設計審査 1 回目（2026-11-04・審査の記録 architect-review.md・枝 `release/schedule-gcal-alignment-review`）: 便1 = REVISE（軽い）／便2 = REVISE／便3 = REVISE。REJECT は無し。指摘の要点は実物で確かめ直し、すべて事実と一致した。改訂 1 で反映した（§12）。
- 自己審査の判定は改訂 1 のあと: 便1 = APPROVE／便2 = APPROVE／便3 = REVISE（§7-3 の前提確認 4 件が済むまで）。
- クラウドの再審査（2026-11-04・審査の記録 architect-review-2.md・枝 `release/schedule-gcal-alignment-review2`）:
  - 便1 = APPROVE。カードへの追記 N-6〜N-10（`c` の真ん中・`frontend/src/components/Popover.tsx:53`・`schedule.listView`・229 と 1 文字だけ小文字・日の一覧の小窓も Esc）を改訂 2 で反映（§13）。主な指摘は実物で確かめ、一致した。
  - 便2 = REVISE（軽い）。N-5: 終日の予定が Google で 1 日前にずれる今からある不具合（画面は `combineDateTime(date,"00:00").toISOString()` で UTC を送る `frontend/src/pages/schedule/SchedulePageImpl.tsx:1041`、裏側は `str(start_dt)[:10]` `backend/app/services/calendar_service.py:519-520`）。N-11: 行の高さは `DEFAULT_ROW_HEIGHT`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:88`・使う所 `:611`）と同じ値を使う。N-12: `category` は直す口で受け取らない（`UpdateEventBody`・`field_map`）ので試験で見ない。→ N-5 の扱いを決めてから改訂する。
  - 便3 = REVISE。N-1: 道の入口の `try/except Exception` が 422 を 500 に変える（`backend/app/routers/calendar.py:352-364`・`:421-434`）。N-2: 返事が `{"id"}` だけで Meet の失敗が画面に分からない。N-3: 直す前に `google_event_id`・`meet_url` を読む。N-13（任意）。§7-3 の 4 件も残る。
- 判定（再審査のあと）: 便1 = APPROVE（実装可能）／便2 = REVISE／便3 = REVISE。
- クラウドの再審査 3 回目（2026-11-04・審査の記録 architect-review-3.md・枝 `release/schedule-gcal-bin2-review3`・HEAD 6f5deecff）: 便2 = APPROVE。終日の直しを Python 3.12.3 で写して動かし、試験 1〜6 の期待どおりになることを確かめた。書き足し N-14〜N-19 はカードへ。N-16（秘書の下書き `frontend/src/features/secretary/SecretaryDraftEvent.tsx:50-58` も同じ形で送る）と N-17（作る口も `category` を受けない）は Opus が実物で確かめ、一致した。
- 改訂 3 のあとの自己審査（2026-11-04）: 便2 = APPROVE（自己審査。クラウドの再審査はまだ）。根拠: N-5 の原因は origin/main 0f297666c の実物で確かめた（画面 `frontend/src/pages/schedule/SchedulePageImpl.tsx:1251-1252`・裏側 `backend/app/services/calendar_service.py:518-520`・取り込み `:380-394`・上書きの条件 `WHERE calendar_events.source = 'google'`）。直す場所は関数 1 つで、表・移行・危険な道に触れない。N-11・N-12 は §5-6 に反映。未解決: すでにずれた Google 側の予定の件数（§7 の 7・本番反映のあと）。便1 の本番での K1〜K7 の PO 確認（§4 の順番）。

## 10. 維持の仕組み（守り手）

守り手: frontend/src/pages/schedule/schedule-utils.test.ts（`fitPopover` の試験。CI の frontend 試験で毎回回る）

| 守るもの | 守り手 |
|---|---|
| 小窓が画面に収まる | `frontend/src/pages/schedule/schedule-utils.test.ts` の `fitPopover` 試験（CI の frontend 試験） |
| 近道が入力中に効かない | `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` の近道試験 |
| 引っぱりの時刻換算 | `frontend/src/pages/schedule/schedule-utils.test.ts` の換算試験 |
| 終日が Google で同じ日になる | `backend/tests/test_calendar_service.py` の `TestToGoogleEventBody`（CI の backend 試験） |
| 直書きの色・文字が入らない | 今ある見張り（ADR-067 のトークン検査・ADR-027 の i18n 検査・ADR-144 の金型検査） |
| Meet は本人だけ | 便3 の裏側の試験（本人以外は 422・Google に送らない）と新しい ADR |

## 11. 実装カード

### 11-1. 便1（K1〜K7・画面だけ）

- 承認: §2 の成功条件と 3 便の計画は PO 承認済み（2026-11-04「1」。審査に通ったら便1 を実装に出す、を含む）。設計はクラウドの再審査で便1 = APPROVE。
- 担当: クラウドの Sonnet（実装役）。この §11-1 と §5-1〜§5-5 だけを実行する。§5-6・§5-7（便2・便3）には触らない。
- 枝: `origin/release/schedule-gcal-alignment` を土台に `release/schedule-gcal-bin1` を作り、そこへ push する（設計文書が同じ PR に乗る）。PR は起票しない（Opus が起票する）。main・develop・ほかの枝へ push しない。
- 行番号の基準: 設計は `origin/main` 7d56ab771。2026-11-04 時点で、それ以降の main に予定の画面・`frontend/src/tokens.css`・`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` の変更は無い（`git log 7d56ab771..origin/main -- <それらの道>` 0 件）。行がずれていたら、名前（関数名・クラス名・キー名）で探す。見つからなければ止まる。

触るファイル（これ以外は触らない）:

| ファイル | 中身 | 設計 |
|---|---|---|
| `frontend/src/pages/schedule/schedule-utils.ts` | `fitPopover`（枠なしは真ん中）・`ScheduleView` に `"list"`・`toRangeStart`/`toRangeEnd` の一覧 | 5-1・5-4・5-5 |
| `frontend/src/pages/schedule/schedule-utils.test.ts` | `fitPopover` 29 件（27＋左右に入らない 1＋枠なし 1）・一覧の範囲 3 件 | 5-1・5-4 |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 小窓を測って置く（`useLayoutEffect`・`resize`・`ResizeObserver`）・短い作る小窓・月の 1 行と「他 ◯ 件」の日の一覧の小窓・一覧の表示 `ScheduleListView`・近道・近道の一覧（金型 `Modal`） | 5-1〜5-5 |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | 小窓の部品の試験 2 件（K1 (b)）・近道 20 件（K7） | 5-1・5-5 |
| `frontend/src/pages/schedule.css` | `.schedule-popover` の見出し・中・下の帯の分け方・月の 1 行・`.schedule-kbd`・一覧の並び（トークンだけ） | 5-1・5-3・5-4・5-5 |
| `frontend/src/tokens.css` | 予定の段に `--schedule-month-dot-size: 8px;` | 5-3 |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | `schedule.moreOptions`・`schedule.listView`・`schedule.moreCount` の書き換え・`schedule.shortcuts.*`（同じキーを両方に） | 5-2〜5-5 |

触らない: 裏側（`backend/`）・`migrations/`・金型（`frontend/src/components/`）・`frontend/src/features/schedule/calendars.config.ts` の色・虫めがねボタン・`buildPopoverPosition` 以外の置き場所の計算・狭い画面の並び。

守ること:
- 画面の文字は全部 `t()`（ADR-027）。色・大きさ・余白はトークン（ADR-067）。数値の inline `maxHeight` は使わない。部品は金型（`Button`・`Modal`・`Toggle`）を先に使う（ADR-144）。
- `fitPopover` の `margin` 12 にはコメントで理由を書く（`--space-3` と同じ値・前例 `frontend/src/components/Popover.tsx:53`）。
- 近道の判定の順番は 5-5 の 1〜7 のとおり（229・1 文字だけ小文字・日の一覧の小窓も Esc で閉じる）。
- 測る前は `visibility: hidden`。`ResizeObserver` は `typeof ResizeObserver !== "undefined"` のときだけ付け、外すときに必ず外す。

想定される分かれ道（当たったら止まって報告する。推測で進めない）:
- `buildPopoverPosition` を呼ぶ所が予定の小窓以外にもある → 全部の呼び元を書き出して止まる。
- 月の「他 ◯ 件」の日の一覧の小窓を出す仕組みが今の作り（`selected`・`draft` の状態）に入らない → 新しい状態を 1 つ足す形で書き、他の状態の意味は変えない。変えないと書けないなら止まる。
- `Modal` の Esc（`frontend/src/components/Modal.tsx:73-80`）とページの Esc が二重に効く → 5-5 の 2 で先に抜ける。試験で確かめる。
- 試験の中で `getBoundingClientRect` を差し替えられない → 差し替え方を書いて止まる。

確かめ（push の前に全部回し、生の出力をファイルに残す）:
1. `cd frontend && npm run test:unit -- src/pages/schedule` → 全部合格。新しい試験の件数（`fitPopover` 29・一覧 3・部品 2・近道 20）を数えて書く。
2. `cd frontend && npx tsc --noEmit` → 0 件。
3. `cd frontend && npm run check:all` → 全部合格（ESLint・色の直書き・i18n のキー・stylelint などをまとめて回す。`frontend/package.json` の `check:all`）。
4. `cd frontend && npm run check:new-tokens` → 合格（新しいトークン 1 個）。
5. `cd frontend && npm run build` → 成功。
6. `git diff --name-only origin/release/schedule-gcal-alignment...HEAD` → 上の表のファイルだけ。

終わり方: `DONE`（push 済み・HEAD の番号・上の 1〜6 の結果）／`BLOCKED: <理由>`／`NEEDS_DECISION: <決めること>` の 1 行で終える。

### 11-2. 便2（K8〜K11・終日の直し）

- 状態: カード作成済み。実装に出すのは、PO が本番で K1〜K7 を見て合格と言ったあと（§4）。
- 担当: クラウドの Sonnet（実装役）。この §11-2 と §5-6 だけを実行する。§5-7（便3）には触らない。
- 土台: その時点の origin/main。枝 `release/schedule-gcal-bin2`。
- 触ってよいファイル（これ以外が要ると分かったら作らず NEEDS_DECISION: で止まる）:
  1. `frontend/src/pages/schedule/SchedulePageImpl.tsx`
  2. `frontend/src/pages/schedule/schedule-utils.ts`
  3. `frontend/src/pages/schedule/schedule-utils.test.ts`
  4. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`
  5. `frontend/src/pages/schedule.css`
  6. `frontend/src/tokens.css`（`--schedule-drag-ghost-bg: var(--calendar-google-blue-light);` を予定の画面の段に 1 行足すだけ）
  7. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（長さを変えるつまみの読み上げ名など、新しい文字が要るときだけ。同じキーを両方に）
  8. `docs/adr/ADR-067-design-token-enforcement.md`（「コンポーネントトークン（tokens.css）」の表に `--schedule-drag-ghost-bg` と、便1 で足して表に無い `--schedule-month-dot-size` の 2 行を足す）
  9. `backend/app/services/calendar_service.py`（`_to_google_event_body` の終日の枝 `:518-520` だけ）
  10. `backend/tests/test_calendar_service.py`
- 触らない: `frontend/src/components/`・`backend/app/routers/`・`migrations/`・`.github/`・`scripts/`・秘書の部品 `frontend/src/features/secretary/`（直しは裏側で効く・N-16）。
- 作るもの（§5-6 のとおり）:
  1. 換算の純粋な関数（位置 px・行の高さ → 15 分に丸めた分）を `schedule-utils.ts` に。行の高さは引数。画面からは `rowHeight`（`SchedulePageImpl.tsx:651`）を渡す。
  2. `canEditItem(item)` を `canEditSelected`（`:1336-1338`）から切り出し、両方で使う。判定の中身は変えない。動かせるのは `canEditItem(item) && item.source !== "shift"` だけ（K10）。
  3. 引っぱって作る（4px 以上で引っぱり・未満は今の 1 時間）・動かす・下の端で長さを変える。Pointer Events（`onPointerDown`・`setPointerCapture`）。外部の部品は入れない。
  4. 離したら `PATCH /calendar/events/{id}` に題名・開始・終了・終日・説明・場所を送る。`category` と `calendar_type` は送らない。失敗したら元の位置に戻し、今の失敗の帯（`setError` `:1271` の形）を出す。
  5. 終日の予定を動かすとき、終わりは「新しい最後の日の 23:59（日本時間）」で作る。`combineDateTime(新しい最後の日, "23:59")` を使う。次の日の 0:00 にしない（Google で 1 日長くなる・N-14）。
  6. 月の帯: 終日・複数日を週の行ごとに `grid-column: 開始 / 終了+1` の帯で出す。帯は 1 日 3 件（`dayEvents.slice(0, 3)` `:843`・N-15）と「他 ◯ 件」の数に入れない。
  7. 色・余白・大きさはトークンだけ。直書きの色・px は書かない。文字は `t()` だけ。
  8. 裏側の終日の直し（§5-6 の手順 1〜4）。日付だけの文字はそのまま（今の `[:10]` を残してもよい）。
- 試験（全部足す。消す・skip にするのは禁止）:
  1. 換算の関数: 0px・境目・15 分丸め・日をまたぐ
  2. 直せない予定（他人・シフト）は押して引いても時刻が変わらない（K10）
  3. 動かしたときの送る中身に題名・終日・説明・場所があり、`category` が無い（K9・N-12）
  4. 終日を 1 日右へ動かすと、送る `end_datetime` が新しい最後の日の 23:59（日本時間）になる（N-14）
  5. 4px 未満は今の 1 時間の作成のまま
  6. 裏側 `TestToGoogleEventBody` に §5-6 の 1〜6
  7. 裏側 `TestCreateEvent`（`backend/tests/test_calendar_service.py:231`）と `TestUpdateEvent`（`:362`）に、終日で作る・直すと Google に渡す中身の `date` が日本時間の日付と次の日になる試験を 1 件ずつ（N-19）
- 前提: 端末は日本時間（画面は端末の時刻で 00:00／23:59 を作る。日本以外の端末のずれは今からあり、便2 で増えない・N-18）。
- 確かめ（生出力は実行記録に残す）: `npm run test:unit -- src/pages/schedule`・`npx tsc --noEmit`・`npm run check:all`・`npm run check:new-tokens`・`npm run check:dark-parity`・`npm run build`・`cd backend && pytest tests/test_calendar_service.py -q`・変更ファイルが上の 10 項目だけ。
- 報告: `docs/handoff/schedule-gcal-alignment/impl-report-2.md`。コードを先に commit → 確かめ → 報告を commit・push。PR は作らない。

### 11-3. 便3

再審査の REVISE（§9）を直して、もう一度審査に通ってから書く。

## 12. 改訂 1 の記録（クラウドの設計審査 1 回目の指摘 → 直した場所）

| 指摘 | 中身 | 直した場所 |
|---|---|---|
| 行番号のずれ | `frontend/src/components/Toggle.tsx` は 41 行（部品 `:21`・入力 `:27-31`）。`frontend/src/components/Popover.tsx` は反転なしのコメント `:79`・押し戻し `:80-87`・`visible` `:110`。作る小窓の欄は `:285` から | 5-1・5-2・5-5・§8・recon §1 |
| 行番号のずれ（裏側） | Google の id を取るのは `backend/app/services/calendar_service.py:228`。取り込みの関数は `:410` から。`require_calendar_owner` は `backend/app/routers/google_calendar.py:155` | recon §5 |
| A-1 | 中身が伸びたら測り直す | 5-1（`ResizeObserver`）・K1 (b) |
| A-2 | inline の `maxHeight` は ESLint で禁止 | 5-1 の 3（CSS の上限に任せる） |
| A-3 | 日の表示で空き枠に重なることがある | 5-1 の 1（許容） |
| A-4〜A-7 | 入力中の Esc・Modal が開いているとき・Toggle・大文字小文字・Shift・押しっぱなし | 5-5 の判定の順番・K7 |
| A-9 | 「他 ◯ 件」を押すと日の枠の作る小窓も開く | 5-3（`stopPropagation`） |
| 一覧の分かれ道 | 表示ごとに分けている 4 か所と範囲の関数 | 5-4 |
| B-1 | 開始と終了だけ送ると Google の題名が空になる | 5-6（全部の欄を送る）・K9 |
| B-2〜B-4 | 位置の測り方・1 件ごとの直せる判定・月の帯の数え方 | 5-6 |
| C-1・C-2 | 作るは INSERT の前に断る。直すも本人と Google の id を確かめる | 5-7・K13 |
| C-3 | 送る欄が無いと早く戻る | 5-7 |
| C-4・C-5 | 1 件を読む関数が無い・`asyncio.sleep`・頼み直しは新しい `requestId` | 5-7 |
| C-6・C-7 | SELECT の最後に足す・画面の型 3 か所・取り込みの ON CONFLICT | 5-7 |
| C-8 | 接続状態の口は見ている人も同期方式も読まない | 5-7 |
| C-9 | `scripts/run_all_migrations.sh` への登録 | 5-7・§7-3 の 2 |
| C-10 | K14 は双方向が前提 | §7-3 の 4・K14 |
| FEATURE-INDEX | 「取り込みは止めている」が古い | 5-7 の ADR |

## 13. 改訂 2 の記録（クラウドの再審査の便1 への追記 → 直した場所）

| 指摘 | 中身 | 直した場所 |
|---|---|---|
| N-6 | `c` は押した枠が無い。月・一覧では置く基準が無い | 5-5（真ん中に出す）・5-1 の試験 |
| N-7 | 金型の余白の前例は `frontend/src/components/Popover.tsx:53` | 5-1 |
| N-8 | 表示の名前は `schedule.${nextView}View` で引く。キーは `schedule.listView` | 5-4 |
| N-9 | 229 も変換中とみなす・1 文字だけ小文字・K7 の数え方の名前 | 5-5・K7 |
| N-10 | 日の一覧の小窓も Esc と「開いている間」に入れる | 5-5 |
| 行のずれ | `formatRangeTitle` 115-120・トークンの段 392-416・表示の切り替え 1179-1190 | 5-3・5-4 |

## 14. 改訂 3 の記録（クラウドの再審査の便2 への指摘 → 直した場所）

| 指摘 | 中身 | 直した場所 |
|---|---|---|
| N-5 | 終日の予定が Google で 1 日前にずれる。PO が便2 で裏側も含めて直すと決めた（2026-11-04「1」） | §3・§4・5-6（直し方と試験 6 件）・§7 の 7・§10 |
| N-11 | 行の高さは今ある `rowHeight`（`DEFAULT_ROW_HEIGHT`）を引数で渡す。`getComputedStyle` は使わない | 5-6・§7 の 6 |
| N-12 | 直す口は `category` を受け取らない。動かすときに送らず、試験でも見ない | 5-6・§7 の 8 |
| 行のずれ | 便1 の合流で行が動いた: 保存 `:1247-1257`・`canEditSelected` `:1336-1338`・`rowHeight` `:651`・`DEFAULT_ROW_HEIGHT` `:91` | 5-6 |

## 15. 再審査 3 回目の書き足しの記録（→ 便2 のカード）

| 指摘 | 中身 | 入れた場所 |
|---|---|---|
| N-14 | 終日を動かすときの終わりは最後の日の 23:59。次の日の 0:00 だと Google で 1 日長くなる | §11-2 作るもの 5・試験 4 |
| N-15 | 1 日 3 件は今 `frontend/src/pages/schedule/SchedulePageImpl.tsx:843` | §11-2 作るもの 6 |
| N-16 | 秘書の下書きも同じ口に同じ形で送る。直しは裏側で効く | §11-2 触らない・§9 |
| N-17 | 作る口も `category` を受けない | §7 の 8 |
| N-18 | 端末は日本時間が前提 | §11-2 前提 |
| N-19 | 作る・直すの両方の道の試験 | §11-2 試験 7 |
| 軽微なずれ | §5-6 の `:517-522` は終日の分岐 518-523。直す場所（518-520）は正しい | 直さない（判断に影響なし） |

## 16. 改訂 4 の記録（便3。クラウドの再審査 2 回目の N-1・N-2・N-3・N-13 → 直した場所）

根拠は origin/main 1f017118d の実物（2026-11-05 に読んだ）。

| 指摘 | 実物 | 直した場所 |
|---|---|---|
| N-1 422 が 500 になる | 作る口 `backend/app/routers/calendar.py:352` `try`・`:359` `except Exception`／直す口 `:421` `try`・`:429` `except Exception` | 5-7 の「作る」「直す」: 判定を口の `try` の前に移した（案 a）。判定の式は `can_add_meet` 1 か所 |
| N-2 失敗を画面が知る道が無い | 返事は `{"id": event_id}` だけ（`backend/app/services/calendar_service.py:251`・`:290`・`:335`） | 5-7 の「返事」「保存のあと」: 返事に `meet_url`。画面は今ある知らせの帯（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1103`・`:1473-1478`）で `schedule.meetFailed` を出す |
| N-3 判定に要る値を先に読む | 口の `:391` は `created_by_user_id, calendar_type, user_id` だけ。サービスの `google_event_id` の読み取りは UPDATE の後（`:302-307`） | 5-7 の「直す」: 口の `:391` に `google_event_id, meet_url` を足す |
| N-13 持ち主も見る（任意） | `event_owner` は口の `:399` | 5-7 の「直す」の (3) に入れた |

## 17. 改訂 5 の記録（便3。クラウドの再審査 4 回目 REVISE（軽い）の R4-1〜R4-5 → 直した場所）

審査の結果: `origin/release/schedule-gcal-bin3-review4:docs/handoff/schedule-gcal-alignment/architect-review-4.md`。N-1・N-2・N-3・N-13 は直ったと判定された。審査は「R4-1・R4-2 を直せば、もう一度のクラウド審査なしでカードを書いてよい」とした。R4-1・R4-2・R4-4 は origin/main 1f017118d の実物で私も確かめた（`backend/app/services/calendar_service.py:509-523`・`backend/tests/test_calendar_owner_api.py:178-182`・`frontend/src/pages/schedule/schedule-utils.ts:201`）。

| 指摘 | 直した場所 |
|---|---|
| R4-1 `add_meet` だけの直しで題と時刻を消す | 5-7「直す」: そのときは `conferenceData` だけを送る。試験 1 件 |
| R4-2 口の SELECT を 5 列にすると今の試験 4 件が落ちる | 5-7「試験」: `_event_db` に既定つき引数 2 つ |
| R4-3 `meet_available` の式が 2 か所 | 5-7「接続状態の口」: `can_add_meet` を呼ぶだけ |
| R4-4 `normalizeEvent` の行 | `:201` に直した |
| R4-5 画面から何を送るか・import | 5-7「送る中身」・「試験」 |
| 注意 2 件 | §7 の 3 と ADR の (5) に書き足した |

