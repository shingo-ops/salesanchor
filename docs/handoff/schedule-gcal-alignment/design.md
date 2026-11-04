# design: 予定の画面を Google カレンダーに寄せる 段1（2026-11-04）

recon: `docs/handoff/schedule-gcal-alignment/recon.md`（以下 R§0〜R§7）
見本: canvas「予定の画面 完成予定」（週・月・一覧・操作と近道の 4 枚。PO「1」で承認）
状態: 設計案作成済み（同一 AI の自己審査 §9 済み）。成功条件（§2）は PO 承認済み（2026-11-04「1」）。クラウドの設計審査は実施中。実装は未着手。

## 1. 目的（PO の言葉で）

予定の画面の見た目と操作を Google カレンダーに近づける。作る小窓が画面から切れないようにする。アプリから Google Meet を付けられるようにする。
段1は PO 1 人で動作確認する範囲（Meet は Google をつないだ PO 本人の予定だけ）。段2（全員が自分の Google をつなぐ）は段1の確認後に別の設計で行う。

## 2. 成功条件（PO が画面で ○× を付けられる形）

| # | 便 | 基準 | 検証方法 |
|---|---|---|---|
| K1 | 1 | 作る・詳しく・直すの小窓の保存（または閉じる）ボタンと題名が、どの予定・どの空き枠を押しても画面の中に全部見える | 自動試験: 画面の高さ 600・768・900px、横 1024・1280・1920px の 9 通りで、画面の一番下と一番右の枠を押して小窓を出し、小窓の四角が画面の内側に収まるかを数で確かめる（9 通り×3 種で 27 件すべて合格）。PO は自分の画面で一番下の枠（23 時台）を押して保存ボタンが見えれば ○ |
| K2 | 1 | 小窓が画面より高いとき、題名の行と保存の行は動かず、間の欄だけが動く | 自動試験: 高さ 600px で「詳しく入れる」を開き、中を一番下まで動かしても保存ボタンの位置が変わらない。PO は画面を小さくして確かめる |
| K3 | 1 | 空き枠を押すと、題名・時刻・種類・社員にも見せるだけの短い小窓が出る。「詳しく入れる」で今の全部の欄（場所・説明など）が出る | PO が週の表示で空き枠を押して見る |
| K4 | 1 | 月の表示で、1 つの予定が 1 行（担当者の色の丸・時刻・題名）で出る。2 行に折れない | PO が今月の表示で見る。題名が長いと末尾が「…」になれば ○ |
| K5 | 1 | 月の表示の「他 ◯ 件」を押すと、その日の予定が全部並んだ小窓が出て、そこから予定を押すと詳しくが出る | PO が予定の多い日で押して見る |
| K6 | 1 | 表示の切り替えに「一覧」が増え、選んだ日から 30 日分の予定が日付ごとに並ぶ（予定の無い日は出ない） | PO が「一覧」を押して見る |
| K7 | 1 | キーボードの近道が効く: T 今日／J・→ 次／K・← 前／D 日／W 週／M 月／A 一覧／C 作る／Esc 閉じる／? 近道の一覧。文字を入れている最中は効かない | 自動試験: 各キーで表示が変わる・入力欄の中では変わらない（11 件すべて合格）。PO は T・W・M・? を押して見る |
| K8 | 2 | 週・日の表で、空いた時間を上から下へ引っぱると、その長さの枠と短い小窓が出る（15 分きざみ） | PO が引っぱって作って見る |
| K9 | 2 | 自分が直せる予定をつかんで別の時間・別の日へ動かせる。下の端を引っぱると終わる時刻が変わる。離すと保存され、Google に送ってある予定は Google でも変わる | PO が動かした後、Google カレンダーでも同じ時刻になっていれば ○ |
| K10 | 2 | 直せない予定（他人の予定・シフト）はつかめない | 自動試験: 直せない予定で押して引いても時刻が変わらない |
| K11 | 2 | 月の表示で、複数日・終日の予定が日をまたぐ 1 本の帯で出る | PO が複数日の予定のある月で見る |
| K12 | 3 | PO が作る・直す小窓で「Google Meet を付ける」を入れて保存すると、詳しくに「Google Meet で参加」が出て、押すと Meet が開く。Google カレンダー側の同じ予定にも Meet が付いている | PO が 1 件作って両方で見る |
| K13 | 3 | PO 以外の人には「Google Meet を付ける」が出ない。裏側を直接呼んでも Meet は付かない（断られる） | 自動試験: つないだ本人以外が Meet 付きで作ると 422・Google に送られない |
| K14 | 3 | Google 側で Meet を付けた予定（取り込んだ予定）にも「Google Meet で参加」が出る | PO が Google で Meet 付きの予定を作り、15 分以内にアプリで見る |

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
  1. 横: 押した枠の右に置けなければ左に置く。どちらも入らなければ画面の中に押し戻す。
  2. 縦: 押した枠の上端にそろえ、下が出るなら上へずらす。
  3. 高さ: 小窓の高さの上限 = 画面の高さ − 上下の余白。上限を返し、CSS の `max-height` にあてる。
  - `margin` は 12（`frontend/src/tokens.css:76` `--space-3: 12px` と同じ値。数字の理由をコメントに書く。前例 `frontend/src/components/Popover.tsx:55`）。
- 小窓の部品で `useLayoutEffect` を使い、出したあとの `getBoundingClientRect()` で測って `fitPopover` を呼ぶ。測る前は `visibility: hidden` にして、ずれた位置が一瞬見えないようにする（前例 `Popover.tsx:112` の `visible`）。画面の大きさが変わったら測り直す。
- `frontend/src/pages/schedule.css:679-693` `.schedule-popover`: 外側の `overflow: auto` をやめて `overflow: hidden`。見出し（`.schedule-popover__header`）と下の帯（`.schedule-popover__footer`）は縮まない（`flex: none`）。間の `.schedule-popover__body` だけ `flex: 1 1 auto; min-height: 0; overflow: auto`。
- 金型 `Popover.tsx` は使わない。理由: 押す相手を子に持つ作りで、押した場所の四角だけを渡せない（R§1）。金型を直すと他の画面に響く。置き場所の計算の考え方は金型と同じ（測ってから画面の中へ押し戻す）にそろえる。
- 試験: `schedule-utils.test.ts` に `fitPopover` の 27 件（K1 の 9 通り×作る・詳しく・直すの高さ）と、画面より高い場合の 3 件。

### 5-2. 便1 短い作る小窓（K3）

- 作る小窓（`mode === "create"`）で、最初は 題名・開始と終了（日付と時刻）・種類・社員にも見せる・終日 だけを出す。
- 下の帯の左に「詳しく入れる」（`Button variant="ghost"`）。押すと今の全部の欄（`SchedulePageImpl.tsx:284-410`）を出す。入れた中身は消えない（同じ `draft`）。
- 直す小窓（`mode === "edit"`）は今どおり全部の欄。
- 新しい文字: `schedule.moreOptions`（ja「詳しく入れる」・en「More options」）。

### 5-3. 便1 月の 1 行と他◯件（K4・K5）

- `SchedulePageImpl.tsx:805-823` の札を、背景なしの 1 行に変える: 担当者の色の丸（今の `ownerMeta.color`。色の意味は今と同じ「担当者」）・開始時刻（終日は時刻なし）・題名。`white-space: nowrap; overflow: hidden; text-overflow: ellipsis` を札全体にかける。月の札から種類の札（`:815-821`）は外し、種類は詳しくで見る。
- 終日の予定は今の札（背景が担当者の色）のまま 1 行にする（便2 で帯にする）。
- `:826-828` の `<span>` を `<button type="button">` にし、押すとその日の一覧の小窓を出す。小窓は 5-1 の置き場所の計算を使う。中の予定を押すと今の詳しくを出す。
- 文字: `frontend/src/locales/ja.json:3195` `"moreCount": "+{{count}}件"` → `"他 {{count}} 件"`。en は `"{{count}} more"`。
- 新しいトークン（`frontend/src/tokens.css` の予定の段 `:393-417` に足す）: `--schedule-month-dot-size: 8px;`

### 5-4. 便1 一覧の表示（K6）

- `frontend/src/pages/schedule/schedule-utils.ts:1` `ScheduleView` に `"list"` を足す。`toRangeStart` は選んだ日の 0 時、`toRangeEnd` は 30 日後。前後の移動（`SchedulePageImpl.tsx:1090-1096`）は 30 日ずつ。
- 表示の切り替え（`:1179-1188`）に「一覧」を足す。文字 `schedule.viewList`（ja「一覧」・en「Schedule」）。
- 一覧の部品は新しく `ScheduleListView`（`SchedulePageImpl.tsx` の中）。日付ごとに 1 段、左に日付の丸（今日は `--schedule-today`）、右に予定の行（色の丸・時刻・題名・種類）。行は `<button>` で、押すと詳しく。予定の無い日は出さない。全部無いときは今の空の表示を使う。
- 見出しの日付は `Intl.DateTimeFormat`（今の `formatDayLabel` と同じ道具）で出す。

### 5-5. 便1 キーボードの近道（K7）

- `SchedulePageImpl.tsx` の本体に `useEffect` で `window` の `keydown` を 1 つだけ付ける（外すときに必ず外す）。
- 効かない場合: `event.isComposing`、`event.target` が `input`・`textarea`・`select`・`[contenteditable]`、`Ctrl`・`⌘`・`Alt` が押されている。小窓が開いているときは `Esc` だけ効く。
- キー: `t` 今日／`j`・`ArrowRight` 次／`k`・`ArrowLeft` 前／`d` 日／`w` 週／`m` 月／`a` 一覧／`c` 作る（今日の 9 時の短い小窓）／`Escape` 小窓を閉じる／`?` 近道の一覧。
- 近道の一覧は金型 `frontend/src/components/Modal.tsx` で出す。キーの見た目は新しいクラス `.schedule-kbd`（トークンだけで書く）。
- 文字: `schedule.shortcuts.title` と各キーの説明 10 個（ja・en 同じキー）。

### 5-6. 便2 引っぱる・動かす・長さを変える・月の帯（K8〜K11）

- 外部の部品は入れない（今は無い・R§4。前に FullCalendar を外した経緯 `SchedulePageImpl.tsx:4`）。Pointer Events（`onPointerDown`・`setPointerCapture`）で書く。
- 時刻への換算は純粋な関数にして `schedule-utils.ts` に置く: 位置(px) → 分 = `px / 行の高さ × 60` を 15 分に丸める。行の高さは CSS の `--schedule-row-height` を `getComputedStyle` で読む（数字を書き写さない）。
- 引っぱって作る: 空き枠で押して 4px 以上動いたら引っぱりとみなし、薄い枠を出す。離すと 5-2 の短い小窓。4px 未満なら今の「押して 1 時間」。
- 動かす・長さを変える: `canEditSelected` と同じ判定（持ち主または担当者を管理できる人）で、かつ `source !== "shift"` の予定だけ。離したら `PATCH /calendar/events/{id}` に開始と終了だけ送る（今の口・R§4）。失敗したら元の位置に戻し、今の失敗の帯を出す。
- 月の帯: 終日・複数日の予定を週の行ごとに `grid-column: 開始 / 終了+1` の帯で出す。月で日をまたいで動かすのも同じ PATCH。
- 新しいトークン: `--schedule-drag-ghost-bg`（`var(--calendar-google-blue-light)` を指す）。
- 試験: 換算の関数（境目・15 分丸め・日をまたぐ）と、直せない予定が動かないこと（K10）。

### 5-7. 便3 Google Meet（K12〜K14）

- 表: 会社ごとの `calendar_events` に `meet_url TEXT NULL` を 1 つ足す（`migrations/` に新しいファイル。`migrations/20261103_200000_add_google_calendar_import_sync.sql:11-34` と同じ「会社ごとに回す・何度流しても同じ」書き方）。Meet の URL の置き場所はこの列 1 か所だけ。
- 裏側:
  - `backend/app/routers/calendar.py:104-119` の作る・直すの形に `add_meet: bool = False` を足す。
  - `backend/app/services/calendar_service.py:180` `create_event`: `add_meet` が真で、送る条件（`:222` と同じ）を満たさなければ 422「Google Meet は Google カレンダーをつないだ本人の予定にだけ付けられます」。満たせば Google に送る中身へ `conferenceData.createRequest = {requestId: "sa-<会社>-<予定>-<ランダム>", conferenceSolutionKey: {type: "hangoutsMeet"}}` を足す。
  - `backend/app/services/google_calendar.py:377` `create_event`・`:392` `update_event` に `conference=False` を足し、真のときだけ `conferenceDataVersion=1` を付けて呼ぶ。
  - 返事の `hangoutLink` を `meet_url` に入れる。`conferenceData.createRequest.status.statusCode` が `pending` で `hangoutLink` が無いときは、1 秒おきに 2 回まで `events.get` で読み直す。それでも無ければ `meet_url` は空のままにし、警告を記録に残す（予定そのものは保存済み）。
  - 直す（`update_event` `:259`）: `add_meet` が真で、`google_event_id` があり、`meet_url` が空のときだけ、`patch` に同じ `createRequest` を付ける。
  - 取り込み（`calendar_service.py:432-501`）: `google_event.get("hangoutLink")` を `meet_url` に入れる（`source='google'` の行だけ・今の更新の条件 `:486` のまま）。
  - 接続状態の口（`backend/app/routers/google_calendar.py:238-264`）に `meet_available: bool` を足す。真 = 接続あり かつ `connected_by_user_id == 見ている人` かつ 同期方式が送る方式。保存はしない（今ある値から毎回出す）。
  - 予定の一覧の返事に `meet_url` を足す。
- 画面:
  - `meet_available` が真のときだけ、作る（短い小窓にも）・直す小窓に `Toggle`「Google Meet を付ける」。
  - 詳しくに `meet_url` があれば「Google Meet で参加」（金型 `ButtonLink`、新しい窓で開く・`rel="noopener noreferrer"`）。`https://meet.google.com/` で始まる URL のときだけ出す。
  - 文字: `schedule.addMeet`・`schedule.joinMeet`（ja・en）。
- ADR: 新しい ADR を 1 つ起こす（Meet の URL は `calendar_events.meet_url` 1 か所・付けられるのはつないだ本人の予定だけ・ADR-1057 の線の内側）。`node scripts/generate-adr-index.js` を回す。`docs/adr/FEATURE-INDEX.md:34` に足す。

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
4. 小窓を測ってから置くので、一瞬ちらつく → 測る前は見えなくする（5-1）。
5. 月の札から種類の札を外すと種類が月で分からない → 詳しくと一覧では出す。PO が月で種類も見たいと言えば札を戻す（見本では外した形で承認済み）。

## 8. 外部・過去事例の参照と我々への応用

- Google カレンダーの近道（出典: Google カレンダー ヘルプ「Use keyboard shortcuts in Google Calendar」https://support.google.com/calendar/answer/37034 、2026-11-04 に読んだ）: 次 `j`・`n`／今日 `t`／日 `1`・`d`／週 `2`・`w`／月 `3`・`m`／予定リスト `5`・`a`／作る `c`／一覧 `?`／戻る `Esc`。同じキーを使う。前へ（`k`）はこのページの読み取り結果に出てこなかった【未確認】。`j` と対になるキーとして `k` を使う。数字キー・`/`（探す）・`g`・`r`・`s` は今回入れない（探す機能が無い・設定画面は別）。
- Google Calendar API の Meet の付け方（Context7 で読んだ公式資料・R§5）: 5-7 の通りに従う。
- 過去事例（社内）: 予定の表は前に FullCalendar を外して内製にした（`SchedulePageImpl.tsx:4`）。外部部品を戻さない根拠。小窓の位置ずれは金型 `Popover.tsx` で「測ってから押し戻す」に直した前例があり（`Popover.tsx:56-58` のコメント）、同じ考え方を使う。
- 数字による効果の事例は持っていない。成功の判定は §2 の K で行う。

## 9. 設計審査（同一 AI による自己審査・独立した第二者レビューではない）

- 判定: 便1 = APPROVE（設計合格）／便2 = APPROVE／便3 = REVISE（§7-3 の前提確認 3 件が済むまで）
- 根拠: 触る場所はすべて R の行番号で確かめた。色・余白は既存トークン＋新しいトークン 2 個。文字はすべて新しい `t()` のキー。金型は Toggle・Button・ButtonLink・Modal を使う。データの置き場所は Meet の URL 1 列だけで、ほかに写しを作らない。
- 未解決: §7-3 の 3 件。PO の画面での切れ方の実測（K1 で代える）。
- クラウドの設計審査: 未実施（PO の §2 承認のあとに出す）。

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
