# design: 予定の画面を Google カレンダーに寄せる 段1（2026-11-04）

recon: `docs/handoff/schedule-gcal-alignment/recon.md`（以下 R§0〜R§7）
見本: canvas「予定の画面 完成予定」（週・月・一覧・操作と近道の 4 枚。PO「1」で承認）
状態: 設計案作成済み（同一 AI の自己審査 §9 済み）。成功条件（§2）は PO 承認済み（2026-11-04「1」）。クラウドの設計審査 1 回目は 3 便とも REVISE（`architect-review.md`・枝 `release/schedule-gcal-alignment-review`）→ 改訂 1 で指摘を反映（§12）。改訂 1 の差分の再審査待ち。実装は未着手。

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
| K7 | 1 | キーボードの近道が効く: T 今日／J・→ 次／K・← 前／D 日／W 週／M 月／A 一覧／C 作る／Esc 閉じる／? 近道の一覧。文字を入れている最中は効かない（Esc だけは入力欄の中でも小窓を閉じる。変換中は閉じない） | 自動試験 20 件すべて合格: 12 キー（T・J・→・K・←・D・W・M・A・C・Esc・?）がそれぞれ効く 12 件＋効かない 8 件（入力欄の中で文字キー／入力欄の中で Esc は閉じる／変換中の Esc は閉じない／Ctrl 付き／⌘ 付き／Alt 付き／小窓が開いている間の文字キー／近道の一覧が開いている間の文字キー）。PO は T・W・M・? を押して見る |
| K8 | 2 | 週・日の表で、空いた時間を上から下へ引っぱると、その長さの枠と短い小窓が出る（15 分きざみ） | PO が引っぱって作って見る |
| K9 | 2 | 自分が直せる予定をつかんで別の時間・別の日へ動かせる。下の端を引っぱると終わる時刻が変わる。離すと保存され、Google に送ってある予定は Google でも変わる | PO が動かした後、Google カレンダーでも同じ時刻で、題名・終日・説明・場所が変わっていなければ ○。自動試験: 動かしたときに送る中身に題名・終日・説明・場所が入っている |
| K10 | 2 | 直せない予定（他人の予定・シフト）はつかめない | 自動試験: 直せない予定で押して引いても時刻が変わらない |
| K11 | 2 | 月の表示で、複数日・終日の予定が日をまたぐ 1 本の帯で出る | PO が複数日の予定のある月で見る |
| K12 | 3 | PO が作る・直す小窓で「Google Meet を付ける」を入れて保存すると、詳しくに「Google Meet で参加」が出て、押すと Meet が開く。Google カレンダー側の同じ予定にも Meet が付いている | PO が 1 件作って両方で見る |
| K13 | 3 | PO 以外の人には「Google Meet を付ける」が出ない。裏側を直接呼んでも Meet は付かない（断られる）。作るときも直すときも同じ | 自動試験 4 件: つないだ本人以外が Meet 付きで作る→422・表に行が増えない・Google に送られない／本人以外が Meet 付きで直す→422・表が変わらない・Google に送られない |
| K14 | 3 | Google 側で Meet を付けた予定（Google で作って取り込んだ予定）にも「Google Meet で参加」が出る。前提: 同期方式が bidirectional（取り込みが動く方式。ADR-1059）。アプリで作った予定に Google 側で後から付けた Meet は対象外 | PO が Google で Meet 付きの予定を作り、15 分以内にアプリで見る（取り込みは 15 分おき `backend/app/tasks/google_calendar_sync.py:4`） |

## 3. 対象と対象外

- 対象: 上の K1〜K14。便 1・2 は画面だけ。便 3 は画面＋裏側＋表に列を 1 つ足す。
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
| 便2 | 引っぱって作る・動かす・長さを変える・月の帯 | 無し | 同上 |
| 便3 | Meet（裏側・列 1 つ・ADR） | 有り | PO の「GO #番号」が要る（ADR-135・136） |

便1 が本番に出て PO が K1〜K7 を見たあと、便2 に進む。便3 は便2 と並べてよいが、カードを出す前に §7-3 の前提確認を済ませる。

## 5. 変更前後

### 5-1. 便1 小窓の置き場所（K1・K2）

変更前（`frontend/src/pages/schedule/SchedulePageImpl.tsx:122-144`）: 高さ 420px の決め打ちで位置を出す。

変更後:
- `frontend/src/pages/schedule/schedule-utils.ts` に純粋な関数 `fitPopover(anchor, size, viewport, margin)` を足す。`size` は出したあとに測った幅と高さ。
  1. 横: 押した枠の右に置けなければ左に置く。どちらも入らなければ画面の中に押し戻す（日の表示の横に広い空き枠では枠に重なる位置に出る。今の `buildPopoverPosition` と同じで、許容する）。
  2. 縦: 押した枠の上端にそろえ、下が出るなら上へずらす: `top = clamp(anchor.top, margin, viewportH − h − margin)`。
  3. 高さの上限は今の CSS（`schedule.css:683` `max-height: min(var(--schedule-popover-max-h), calc(100vh - var(--space-6)))`。`--space-6` = 24px = 上下の余白 12px×2）に任せ、`fitPopover` は高さを返さない。CSS が h ≤ 画面の高さ−24px を保つので、2 の式は常に画面の内側に収まる。inline の `maxHeight` は使わない（ESLint `frontend/eslint.config.js:111` が数値の `maxHeight` を禁止・ADR-067）。
  - `margin` は 12（`frontend/src/tokens.css:76` `--space-3: 12px` と同じ値。数字の理由をコメントに書く。前例 `frontend/src/components/Popover.tsx:55`）。
- 小窓の部品で `useLayoutEffect` を使い、出したあとの `getBoundingClientRect()` で測って `fitPopover` を呼ぶ。測る前は `visibility: hidden` にして、ずれた位置が一瞬見えないようにする（前例 `Popover.tsx:110` の `visible`）。
- 測り直すきっかけは 2 つ: 画面の大きさが変わったとき（`resize`）と、小窓の中身の高さが変わったとき（小窓自身を `ResizeObserver` で見る。「詳しく入れる」で伸びたときなど）。jsdom には `ResizeObserver` が無いので、無ければ付けない（`typeof ResizeObserver !== "undefined"` で確かめる）。部品の試験では差し替えて呼ぶ。
- `frontend/src/pages/schedule.css:679-693` `.schedule-popover`: 外側の `overflow: auto` をやめて `overflow: hidden`。見出し（`.schedule-popover__header`）と下の帯（`.schedule-popover__footer`）は縮まない（`flex: none`）。間の `.schedule-popover__body` だけ `flex: 1 1 auto; min-height: 0; overflow: auto`。
- 金型 `Popover.tsx` は使わない。理由: 押す相手を子に持つ作りで、押した場所の四角だけを渡せない（R§1）。金型を直すと他の画面に響く。置き場所の計算の考え方は金型と同じ（測ってから画面の中へ押し戻す）にそろえる。
- 試験: `schedule-utils.test.ts` に `fitPopover` の 27 件（K1 (a) の 9 通り×高さ 3 種）と、右にも左にも入らない場合の 1 件。`SchedulePageImpl.test.tsx` に K1 (b) の部品の試験 2 件。

### 5-2. 便1 短い作る小窓（K3）

- 作る小窓（`mode === "create"`）で、最初は 題名・開始と終了（日付と時刻）・種類・社員にも見せる・終日 だけを出す。
- 下の帯の左に「詳しく入れる」（`Button variant="ghost"`）。押すと今の全部の欄（`SchedulePageImpl.tsx:285-410`）を出す。伸びたら 5-1 の `ResizeObserver` で置き直す。入れた中身は消えない（同じ `draft`）。
- 直す小窓（`mode === "edit"`）は今どおり全部の欄。
- 新しい文字: `schedule.moreOptions`（ja「詳しく入れる」・en「More options」）。

### 5-3. 便1 月の 1 行と他◯件（K4・K5）

- `SchedulePageImpl.tsx:805-823` の札を、背景なしの 1 行に変える: 担当者の色の丸（今の `ownerMeta.color`。色の意味は今と同じ「担当者」）・開始時刻（終日は時刻なし）・題名。`white-space: nowrap; overflow: hidden; text-overflow: ellipsis` を札全体にかける。月の札から種類の札（`:815-821`）は外し、種類は詳しくで見る。
- 終日の予定は今の札（背景が担当者の色）のまま 1 行にする（便2 で帯にする）。
- `:826-828` の `<span>` を `<button type="button">` にし、押すとその日の一覧の小窓を出す。押したときは `event.stopPropagation()` する（日の枠 `:797` の `onClick` が作る小窓を開くため。予定の札 `:810` と同じ止め方）。小窓は 5-1 の置き場所の計算を使う。中の予定を押すと今の詳しくを出す。
- 文字: `frontend/src/locales/ja.json:3195` `"moreCount": "+{{count}}件"` → `"他 {{count}} 件"`。en は `"{{count}} more"`。
- 新しいトークン（`frontend/src/tokens.css` の予定の段 `:393-417` に足す）: `--schedule-month-dot-size: 8px;`

### 5-4. 便1 一覧の表示（K6）

- `frontend/src/pages/schedule/schedule-utils.ts:1` `ScheduleView` に `"list"` を足す。`toRangeStart` は選んだ日の 0 時、`toRangeEnd` は 30 日後。前後の移動（`SchedulePageImpl.tsx:1090-1096`）は 30 日ずつ。
- 表示の切り替え（`:1179-1188`）に「一覧」を足す。文字 `schedule.viewList`（ja「一覧」・en「Schedule」）。
- 一覧の部品は新しく `ScheduleListView`（`SchedulePageImpl.tsx` の中）。日付ごとに 1 段、左に日付の丸（今日は `--schedule-today`）、右に予定の行（色の丸・時刻・題名・種類）。行は `<button>` で、押すと詳しく。予定の無い日は出さない。全部無いときは今の空の表示を使う。
- 見出しの日付は `Intl.DateTimeFormat`（今の `formatDayLabel` と同じ道具）で出す。
- 「月か日か、それ以外は週」と分けている箇所に一覧を入れる（触る場所の全部）:
  - `SchedulePageImpl.tsx:115-118` `formatRangeTitle`: 一覧は「開始日 - 30 日後の前日」。
  - `:935` 左の小さい月の基準: 一覧は `startOfMonth(anchorDate)`（週と同じ）でよい。
  - `:973` 今の時刻へ動かす処理: 一覧でも動かさない（`view === "month" || view === "list"` で戻る）。
  - `:1098-1102` `viewDays`: 一覧は使わない（一覧は `ScheduleListView` が範囲の予定から日を作る）。
  - `schedule-utils.ts:147-157` `toRangeStart`・`toRangeEnd`。
- 試験: `toRangeStart`・`toRangeEnd` の一覧 3 件（30 日分・月をまたぐ・年をまたぐ）。

### 5-5. 便1 キーボードの近道（K7）

- `SchedulePageImpl.tsx` の本体に `useEffect` で `window` の `keydown` を 1 つだけ付ける（外すときに必ず外す）。
- 判定の順番（上から見て最初に当たったもので決める）:
  1. `event.isComposing` → 何もしない（変換の取消を優先）。
  2. 近道の一覧（Modal）が開いている → 何もしない（Esc は金型 `Modal.tsx:73-80` が閉じる。ページ側は何もしない）。
  3. `Escape` → 予定の小窓が開いていれば閉じる。入力欄の中でも効く。
  4. 予定の小窓が開いている → ここで終わり（文字キーは効かない）。
  5. `Ctrl`・`⌘`（`metaKey`）・`Alt` が押されている → 何もしない。`Shift` は除外しない（`?` は Shift で出すため）。
  6. `event.target` が `input`・`textarea`・`select`・`[contenteditable]` → 何もしない。切替スイッチ `Toggle` は `<input type="checkbox">`（`frontend/src/components/Toggle.tsx:27-31`）なのでここで止まる（安全側）。`<button>` にフォーカスがあるときは効く（Google カレンダーと同じ）。
  7. `event.key` を小文字にそろえて（CapsLock 対策）キーの表で引く。押しっぱなし（`event.repeat`）でも効く（`j` を押し続けると進み続ける。Google と同じ）。
- キー: `t` 今日／`j`・`ArrowRight` 次／`k`・`ArrowLeft` 前／`d` 日／`w` 週／`m` 月／`a` 一覧／`c` 作る（今日の 9 時の短い小窓）／`Escape` 小窓を閉じる／`?` 近道の一覧。12 キー。
- 近道の一覧は金型 `frontend/src/components/Modal.tsx` で出す。キーの見た目は新しいクラス `.schedule-kbd`（トークンだけで書く）。
- 文字: `schedule.shortcuts.title` と各キーの説明 10 個（ja・en 同じキー。J と → ・K と ← は 1 行にまとめる）。
- 試験: K7 の 20 件を `SchedulePageImpl.test.tsx` に置く。

### 5-6. 便2 引っぱる・動かす・長さを変える・月の帯（K8〜K11）

- 外部の部品は入れない（今は無い・R§4。前に FullCalendar を外した経緯 `SchedulePageImpl.tsx:4`）。Pointer Events（`onPointerDown`・`setPointerCapture`）で書く。
- 時刻への換算は純粋な関数にして `schedule-utils.ts` に置く: 位置(px) → 分 = `px / 行の高さ × 60` を 15 分に丸める。行の高さは CSS の `--schedule-row-height` を `getComputedStyle` で読む（数字を書き写さない）。位置(px) は「押した日の列の `getBoundingClientRect().top` からの差」で測る（列の四角は表が縦に動いた分を含むので、動いた量を別に足さない）。
- 引っぱって作る: 空き枠で押して 4px 以上動いたら引っぱりとみなし、薄い枠を出す。離すと 5-2 の短い小窓。4px 未満なら今の「押して 1 時間」。
- 動かす・長さを変える: 今の `canEditSelected`（`SchedulePageImpl.tsx:1123-1125`。選んだ 1 件用）の中身を、予定を 1 件受け取る関数 `canEditItem(item)` に切り出して両方で使う（判定の中身は変えない）。かつ `source !== "shift"` の予定だけ。
- 離したときの送り方（Google の予定を壊さないため）: `PATCH /calendar/events/{id}` に、今の保存（`SchedulePageImpl.tsx:1038-1047`）と同じ形で、題名・開始・終了・終日・種類・説明・場所を送る（題名などは動かす予定の今の値）。開始と終了だけを送ると、裏側が Google へ送る中身を送られた欄だけで作る（`backend/app/services/calendar_service.py:314` → `:512` `"summary": payload.get("title", "")`）ため、Google 側の題名が空で上書きされ、終日も崩れる（`:517-522`）。この形にすれば便2 は画面だけで済む（裏側は触らない）。`calendar_type` は送らない（見せ方は変えない）。失敗したら元の位置に戻し、今の失敗の帯を出す。
- 月の帯: 終日・複数日の予定を週の行ごとに `grid-column: 開始 / 終了+1` の帯で出す。月で日をまたいで動かすのも同じ PATCH。帯は帯の段に出し、1 日 3 件（`:801`）と「他 ◯ 件」の数には入れない（3 件と数えるのは時刻つきの予定だけ）。
- 新しいトークン: `--schedule-drag-ghost-bg`（`var(--calendar-google-blue-light)` を指す。参照先はライト `frontend/src/index.css:184`・ダーク `:384` の両方にある）。ADR-067「新規トークン追加手順」に従い、ADR の表も直す。
- 試験: 換算の関数（境目・15 分丸め・日をまたぐ）と、直せない予定が動かないこと（K10）と、動かしたときの送る中身に題名・終日・説明・場所が入っていること（K9）。

### 5-7. 便3 Google Meet（K12〜K14）

- 表: 会社ごとの `calendar_events` に `meet_url TEXT NULL` を 1 つ足す（`migrations/` に新しいファイル。`migrations/20261103_200000_add_google_calendar_import_sync.sql:11-34` と同じ「会社ごとに回す・何度流しても同じ」書き方）。`scripts/run_all_migrations.sh` の末尾に 1 行登録する（前例 `:1217`。表を作るのは `:377` の `078`）。Meet の URL の置き場所はこの列 1 か所だけ。
- 裏側:
  - `backend/app/routers/calendar.py:104-112` `CreateEventBody` に `add_meet: bool = False`、`:114-121` `UpdateEventBody` に `add_meet: Optional[bool] = None` を足す。
  - 作る（`backend/app/services/calendar_service.py:180` `create_event`）: `add_meet` が真なら、**表に入れる前（`:193` の INSERT より前）に** `_get_sync_target`（`:57`）で送る条件（`:222` と同じ）を確かめる。満たさなければ 422「Google Meet は Google カレンダーをつないだ本人の予定にだけ付けられます」を返し、表には何も入れない（今は `:193-217` で入れて commit してから送る条件を見るため、後で断ると予定だけ残る）。満たせば Google に送る中身へ `conferenceData.createRequest = {requestId: <毎回新しい uuid4>, conferenceSolutionKey: {type: "hangoutsMeet"}}` を足す。
  - 直す（`update_event` `:259`）: `add_meet` が真なら、最初に (1) `_get_sync_target` で送る方式かつ `connected_by == 見ている人`、(2) その予定に `google_event_id` がある、の 2 つを確かめ、どちらかが無ければ 422 で何も変えない（今の直す道は持ち主を見ずに送る `:309-310`・ADR-1057:30 の受け入れ点。Meet だけは本人に絞る）。`meet_url` が空のときだけ `patch` に `createRequest`（新しい `requestId`）を付ける。今は送る欄が 1 つも無いと `:289-290`（`if not set_clauses: return {"id": event_id}`）で何もせず戻るので、`add_meet` だけ送られた場合もこの早戻りの前に Meet を処理する。画面は直す小窓から送るとき今の保存（`:1038-1047`）と同じ全部の欄を送るので、通常はこの場合に当たらない。
  - `backend/app/services/google_calendar.py:377` `create_event`・`:392` `update_event` に `conference: bool = False` を足し、真のときだけ `conferenceDataVersion=1` を付けて呼ぶ。1 件を読む関数 `get_event(db, tenant_id, event_id)` を新しく足す（今は `get_events` `:348`・`create_event` `:377`・`update_event` `:392`・`delete_event` `:407` だけで、1 件を読む関数が無い）。
  - 返事の `hangoutLink` を `meet_url` に入れる。`conferenceData.createRequest.status.statusCode` が `pending` で `hangoutLink` が無いときは、`await asyncio.sleep(1)` をはさんで 2 回まで `get_event` で読み直す（同期の `time.sleep` は使わない）。それでも無ければ `meet_url` は空のままにし、警告を記録に残す（予定そのものは保存済み）。PO がもう一度「Google Meet を付ける」を押すと直す道を通り、新しい `requestId` で頼み直す。
  - 取り込み（`calendar_service.py:410` `upsert_from_google`）: `google_event.get("hangoutLink")` を `meet_url` に入れる。INSERT の列と値に `meet_url` を足し、`:476-486` の `ON CONFLICT ... DO UPDATE SET` に `meet_url = EXCLUDED.meet_url` を足す（`source='google'` の行だけ・今の条件 `:486` のまま）。
  - 予定の一覧（`calendar_service.py:134` の SELECT）: `ce.meet_url` を SELECT の**最後**（`created_by_name` の後）に足し、返す辞書に `"meet_url"` を足す（`r[0]`〜`r[17]` の番号をずらさないため）。
  - 接続状態の口（`backend/app/routers/google_calendar.py:242` `connection_status`）: 今は会社と DB しか受け取らず（`:243-244`）、同期方式も読まない。`user: User = Depends(get_current_user)` を足し、SELECT に `sync_mode`・`connected_by_user_id` を足して `meet_available: bool` を返す。真 = 接続あり かつ `connected_by_user_id == user.id` かつ 同期方式が `bidirectional` か `write_only`。保存はしない（今ある値から毎回出す）。
- 画面の型: `frontend/src/pages/schedule/schedule-utils.ts:13` `ApiCalendarEvent` に `meet_url?: string | null`、`:46` `ScheduleItem` に `meetUrl?: string | null`、`:159` `normalizeEvent` で写す。
- 画面:
  - `meet_available` が真のときだけ、作る（短い小窓にも）・直す小窓に `Toggle`「Google Meet を付ける」。
  - 詳しくに `meet_url` があれば「Google Meet で参加」（金型 `ButtonLink`、新しい窓で開く・`rel="noopener noreferrer"`）。`https://meet.google.com/` で始まる URL のときだけ出す。
  - 文字: `schedule.addMeet`・`schedule.joinMeet`（ja・en）。
- ADR: 新しい ADR を 1 つ起こす。中身: (1) Meet の URL は `calendar_events.meet_url` 1 か所 (2) 付けられるのはつないだ本人の予定だけ。作るも直すも 422 で止め、表にも Google にも何も残さない (3) ADR-1057 の線の内側。直す道の「持ち主を見ずに送る」受け入れ点（ADR-1057:30）は Meet には広げない (4) 取り込みは ADR-1059 の双方向のときだけ動く。`node scripts/generate-adr-index.js` を回す。`docs/adr/FEATURE-INDEX.md:34` に新しい ADR と ADR-1059 を足し、「取り込みは止めている」の古い書き方を今の形（双方向のとき 15 分おきに取り込む）に直す。
- 試験（裏側）: K13 の 4 件（作る 422・作る 422 で表に行が増えない・直す 422 で表が変わらない・どちらも Google に送らない）。Meet を付けたときの `conferenceDataVersion=1` と `createRequest` の形、`pending` から読み直す道、取り込みで `meet_url` が入ること。

## 6. 代替案と選んだ理由

| 案 | 選ばなかった理由 |
|---|---|
| FullCalendar などの外部部品を入れて引っぱり操作を任せる | 前に外して内製の表にした（`SchedulePageImpl.tsx:4`）。見た目をトークンで縛れない。今の表の作りを捨てることになる |
| 金型 `Popover.tsx` を直して予定の小窓に使う | 押す相手を子に持つ作りで合わない。直すと他の画面の小窓の動きが変わる。今回は同じ考え方の純粋な関数を予定の画面に置く |
| Meet の URL を `description` に書き込む | 説明の文と混ざる。Google から取り込んだ説明で上書きされる。置き場所が 1 か所にならない |
| Meet を全員に開く（段2 を先に） | 接続は会社で 1 つ（ADR-1057）。他人の予定がつないだ人の Google に入る。PO はまず自分だけで確かめると決めた |
| 便を 1 つにまとめる | Meet は表の列を足すので PO の GO が要る。画面だけの直しまで待たせない。1 回に 1 つ変えて測る |

## 7. リスクと対処

1. 近道が入力中に効いて文字が打てない → 5-5 の「効かない場合」を試験で確かめる（K7）。
2. 引っぱり中に押しただけの操作（今の 1 時間作成）が壊れる → 4px のしきい値で分け、両方を試験する。
3. Meet の作成が Google 側で断られる（Meet が使えないアカウント・管理者が止めている）→ 予定は保存し、`meet_url` は空、画面に「Google Meet を付けられませんでした」を出す（文字 `schedule.meetFailed`）。
   - 便3 のカードを出す前の確認（未解決の前提。済むまで便3 は「実装可能」にしない）:
     1. 本番の同期方式の今の値（R§5 未確認）。送る方式でなければ、PO に切り替えるか聞く
     2. 新しい会社の `calendar_events` がどの道で作られるか。`backend/app/services/tenant.py` に `calendar` の語は無かった（`grep -n -i "calendar" backend/app/services/tenant.py` 0 件）。新しい会社にも列が入る道を担当に調べさせる
     3. 予定の作成と Google 送信を試す今の試験の場所（R§7 未確認）
     4. 同期方式が `bidirectional` であること（K14 の前提。`write_only` では取り込みが止まる・ADR-1059「戻し方」）。1 と同じ読み取りで確かめる
4. 小窓を測ってから置くので、一瞬ちらつく → 測る前は見えなくする（5-1）。
5. 月の札から種類の札を外すと種類が月で分からない → 詳しくと一覧では出す。PO が月で種類も見たいと言えば札を戻す（見本では外した形で承認済み）。

## 8. 外部・過去事例の参照と我々への応用

- Google カレンダーの近道（出典: Google カレンダー ヘルプ「Use keyboard shortcuts in Google Calendar」https://support.google.com/calendar/answer/37034 、2026-11-04 に読んだ）: 次 `j`・`n`／今日 `t`／日 `1`・`d`／週 `2`・`w`／月 `3`・`m`／予定リスト `5`・`a`／作る `c`／一覧 `?`／戻る `Esc`。同じキーを使う。前へ（`k`）はこのページの読み取り結果に出てこなかった【未確認】。`j` と対になるキーとして `k` を使う。数字キー・`/`（探す）・`g`・`r`・`s` は今回入れない（探す機能が無い・設定画面は別）。
- Google Calendar API の Meet の付け方（Context7 で読んだ公式資料・R§5）: 5-7 の通りに従う。
- 過去事例（社内）: 予定の表は前に FullCalendar を外して内製にした（`SchedulePageImpl.tsx:4`）。外部部品を戻さない根拠。小窓の位置ずれは金型 `Popover.tsx` で「測ってから押し戻す」に直した前例があり（`Popover.tsx:79` のコメント・押し戻しは `:80-87`）、同じ考え方を使う。
- 数字による効果の事例は持っていない。成功の判定は §2 の K で行う。

## 9. 設計審査（同一 AI による自己審査・独立した第二者レビューではない）

- 判定: 便1 = APPROVE（設計合格）／便2 = APPROVE／便3 = REVISE（§7-3 の前提確認 3 件が済むまで）
- 根拠: 触る場所はすべて R の行番号で確かめた。色・余白は既存トークン＋新しいトークン 2 個。文字はすべて新しい `t()` のキー。金型は Toggle・Button・ButtonLink・Modal を使う。データの置き場所は Meet の URL 1 列だけで、ほかに写しを作らない。
- 未解決: §7-3 の 4 件。PO の画面での切れ方の実測（K1 で代える）。
- クラウドの設計審査 1 回目（2026-11-04・`docs/handoff/schedule-gcal-alignment/architect-review.md`・枝 `release/schedule-gcal-alignment-review`）: 便1 = REVISE（軽い）／便2 = REVISE／便3 = REVISE。REJECT は無し。指摘の要点は実物で確かめ直し、すべて事実と一致した。改訂 1 で反映した（§12）。
- 自己審査の判定は改訂 1 のあと: 便1 = APPROVE／便2 = APPROVE／便3 = REVISE（§7-3 の前提確認 4 件が済むまで）。クラウドの再審査の結果で確定する。

## 10. 維持の仕組み（守り手）

| 守るもの | 守り手 |
|---|---|
| 小窓が画面に収まる | `schedule-utils.test.ts` の `fitPopover` 試験（CI の frontend 試験） |
| 近道が入力中に効かない | `SchedulePageImpl.test.tsx` の近道試験 |
| 引っぱりの時刻換算 | `schedule-utils.test.ts` の換算試験 |
| 直書きの色・文字が入らない | 今ある見張り（ADR-067 のトークン検査・ADR-027 の i18n 検査・ADR-144 の金型検査） |
| Meet は本人だけ | 便3 の裏側の試験（本人以外は 422・Google に送らない）と新しい ADR |

## 11. 実装カード

§2 の PO 承認とクラウドの設計審査のあとで、便ごとに書く（便1 から）。

## 12. 改訂 1 の記録（クラウドの設計審査 1 回目の指摘 → 直した場所）

| 指摘 | 中身 | 直した場所 |
|---|---|---|
| 行番号のずれ | `Toggle.tsx` は 41 行（部品 `:21`・入力 `:27-31`）。`Popover.tsx` は反転なしのコメント `:79`・押し戻し `:80-87`・`visible` `:110`。作る小窓の欄は `:285` から | 5-1・5-2・5-5・§8・recon §1 |
| 行番号のずれ（裏側） | Google の id を取るのは `calendar_service.py:228`。取り込みの関数は `:410` から。`require_calendar_owner` は `routers/google_calendar.py:155` | recon §5 |
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
| C-9 | `run_all_migrations.sh` への登録 | 5-7・§7-3 の 2 |
| C-10 | K14 は双方向が前提 | §7-3 の 4・K14 |
| FEATURE-INDEX | 「取り込みは止めている」が古い | 5-7 の ADR |
