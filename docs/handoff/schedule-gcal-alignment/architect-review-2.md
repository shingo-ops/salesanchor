# architect-review-2: 予定の画面を Google カレンダーに寄せる 段1 再審査（2026-11-04）

- 審査した HEAD: `df844fbde23c948b358cd4a3e4e80580093f5ac7`（`origin/release/schedule-gcal-alignment`。指定の `df844fbde` で始まることを `git rev-parse HEAD` で確認）
- 見た差分: `git diff dfb046c0e df844fbde`（design.md・recon.md の 2 ファイル、合わせて +86/−42）。前回の指摘は `origin/release/schedule-gcal-alignment-review:docs/handoff/schedule-gcal-alignment/architect-review.md`
- 審査役: クラウドの Architect（design を書いた AI とは別のセッション）。コードは直していない。試験は流していない

| 便 | 判定 | 一言 |
|---|---|---|
| 便1 | **APPROVE** | 前回の指摘はすべて直った。残りは小さな書き足し（下の N-6〜N-10）で、実装カードに書けば足りる |
| 便2 | **REVISE**（軽い） | B-1 は直った。ただし design の「全部の欄を送れば終日も崩れない」は事実と違う。終日の予定は Google で 1 日前にずれる（N-5。今もある不具合）。K9・K11 の PO 確認が × になる。扱いを決めて書けば APPROVE |
| 便3 | **REVISE** | 422 を INSERT の前に出す形は直った。ただし口（router）が例外をすべて 500 に変えるので、422 が 500 になる（N-1）。Meet が付かなかったことを画面が知る道も無い（N-2）。§7-3 の前提 4 件も未了のまま |

REJECT は無い。

---

## 1. §12 の各指摘は直ったか（実物と突き合わせ）

design の行番号は `docs/handoff/schedule-gcal-alignment/design.md`（HEAD `df844fbde`）。実物の行番号は同じ HEAD のファイル。

| 前回の指摘 | design の直した行 | 実物 | 結果 |
|---|---|---|---|
| 行番号: Toggle | 108・recon §1 `Toggle.tsx:21`・`:27-31` | `Toggle.tsx:21` `forwardRef`、`:27-31` `<input ... type="checkbox" role="switch">` | 直った |
| 行番号: Popover の反転なし・押し戻し・visible | 64・173・recon §1 `:79`・`:80-87`・`:110` | `Popover.tsx:79` コメント、`:80-87` 押し戻し、`:110` `useState(false)` | 直った |
| 行番号: Popover の margin | 63 `Popover.tsx:55` | **`:55` はコメント**（「パネルは position: fixed…」）。`const margin = 8;` は **`:53`**。前回の審査表 #11 の「55」も誤りだった | **不足**（N-7。:53 に直す） |
| 行番号: 作る小窓の欄 | 73・recon `:285-410` | `SchedulePageImpl.tsx:285` `<div className="schedule-popover__body schedule-popover__body--form">`、410 で閉じる | 直った |
| 行番号（裏側） | recon §5 `:228`・`:410`・`routers/google_calendar.py:155` | `calendar_service.py:228` `google_event.get("id")`、`:410` `async def upsert_from_google` | 直った |
| A-1 中身が伸びたら測り直す | 65・K1(b)（16） | `ResizeObserver` と jsdom で無いときの扱いまで書かれている | 直った |
| A-2 inline maxHeight | 62 | `frontend/eslint.config.js:111` が style の数値 `maxHeight` を禁止。CSS `schedule.css:683` に任せる形 | 直った |
| A-3 横に広い空き枠 | 60 | 許容と明記 | 直った |
| A-4 入力中の Esc | 105（判定の 3） | — | 直った |
| A-5 近道の一覧が開いている間 | 104（判定の 2） | `Modal.tsx:73-80` は document で Esc を受けて `stopPropagation`。ページは window で受けるので、Esc は Modal 側で止まる。2 で他のキーも止まる | 直った |
| A-6 Toggle・button | 108 | — | 直った |
| A-7 CapsLock・Shift・押しっぱなし | 107・109 | — | 直った（小さな書き足し N-9） |
| A-9 他◯件が日の枠の押下を拾う | 81 | `SchedulePageImpl.tsx:797` 日の枠の `onClick`、`:810` 札の `stopPropagation` | 直った |
| 一覧の分かれ道 | 91-97 | `:115` `formatRangeTitle`（**115-120**。design は 115-118）・`:935` `currentMonth`・`:973` `if (view === "month") return;`・`:1098-1102` `viewDays`・`schedule-utils.ts:147-157` | 直った（範囲の終わりが 2 行ずれ。軽微）。ただし文字のキー名が合わない（N-8） |
| K2 の題名の行 | 17 | `.schedule-popover__header` を指す書き方になった | 直った |
| K3 と §5-2 の欄 | 18・72 | どちらも終日を含む | 直った |
| K7 の件数 | 22・110・113 | 12 キー＋8 件＝20 件 | 直った（ラベルの小さな誤り N-9） |
| B-1 Google の題名が空になる | 121・K9（24） | `calendar_service.py:314` → `:512` `"summary": payload.get("title", "")`。全部の欄を送る形で題名は守られる | 直った（ただし終日は N-5） |
| B-2 位置の測り方 | 118 | — | 直った |
| B-3 1 件ごとの直せる判定 | 120 | `:1123-1125` `canEditSelected` | 直った |
| B-4 月の帯の数え方 | 122 | `:801` `slice(0, 3)` | 直った |
| ADR-067 新トークンの手順 | 123 | `index.css:184`（ライト `#e8f0fe`）・`:384`（ダーク `#1e3a5f`） | 直った |
| C-1 422 の場所 | 131・K13（28） | 作る道の INSERT は `calendar_service.py:191-217`、`_get_sync_target` は `:57` | サービスの中は直った。**口で 500 になる**（N-1）→ **不足** |
| C-2 直すときの本人判定 | 132 | `:309-310` 持ち主を見ずに送る・ADR-1057:30（「ほかの管理者がアプリで直す・消すと、それも Google に反映される」） | 直った（注意 N-13） |
| C-3 add_meet だけの直し | 132 | `:289-290` `if not set_clauses: return {"id": event_id}` | 直った |
| C-4 1 件を読む関数 | 133 | `services/google_calendar.py` の関数は `get_events` 348・`create_event` 377・`update_event` 392・`delete_event` 407。`get_event` は無い | 直った（足すと明記） |
| C-5 pending・頼み直し | 134 | `asyncio.sleep`・新しい `requestId` | 直った。ただし失敗を画面が知る道が無い（N-2） |
| C-6 SELECT の最後 | 136 | `calendar_service.py:134-138` の列は 18 個（`r[0]`〜`r[17]`、`:152-169`）。`meet_url` は `r[18]` になる | 直った |
| C-6 画面の型 | 138 | `schedule-utils.ts:13` `ApiCalendarEvent`・`:46` `ScheduleItem`・`:159` `normalizeEvent` | 直った |
| C-7 取り込みの ON CONFLICT | 135 | `:476-486` | 直った |
| C-8 接続状態の口 | 137 | `routers/google_calendar.py:242` 関数、`:243-244` 引数は会社と DB だけ、`:249` SELECT は `calendar_id, connected_at` だけ | 直った（注意 N-4） |
| C-9 run_all_migrations | 128・163 | `scripts/run_all_migrations.sh:377` `078`、`:1217`（最終行）が `20261103_200000_...` | 直った |
| C-10・K14 の前提 | 29・165 | ADR-1059「戻し方」の 38 行目「取り込みだけ止めるときは、同期方式を write_only にする」 | 直った |
| K12 の前提（送る方式） | 162 | — | 直った（§7-3 の 1） |
| FEATURE-INDEX | 143 | `docs/adr/FEATURE-INDEX.md:34` は「Google→アプリの取り込みは止める」のまま（直すのは便3 の中） | 直った（予定として書かれた） |

まとめ: 上の表 35 項目のうち、直ったのは 33、不足は 2（Popover の margin の行番号・C-1 の口の 500）。

### 新しく書かれた行番号の突き合わせ（上の表に無いもの）

| design の行 | 引用 | 実物 | 結果 |
|---|---|---|---|
| 62 | `schedule.css:683` の `max-height` の式 | 一致 | 一致 |
| 63 | `tokens.css:76` `--space-3: 12px` | 一致 | 一致 |
| 66 | `schedule.css:679-693` | 679 開始・692 `overflow: auto;`・693 閉じ | 一致 |
| 82 | `ja.json:3195` `"moreCount": "+{{count}}件"` | 一致（en も 3195） | 一致 |
| 83 | `tokens.css` 予定の段 `:393-417` | 見出しのコメントは **392**、最後の予定のトークンは 416（417 は空行） | 1 行ずれ（軽微） |
| 87 | `:1090-1096` 前後の移動 | 一致 | 一致 |
| 88 | `:1179-1188` 表示の切り替え | 1179 `<div className="schedule-view-switch"`・1180 `map`・1190 閉じ | 範囲の終わりが 2 行ずれ（軽微） |
| 118 | `--schedule-row-height` を `getComputedStyle` で読む | トークンは `tokens.css:400` 48px。ただし表の描画の計算は `SchedulePageImpl.tsx:611` `const rowHeight = DEFAULT_ROW_HEIGHT;`（`:88` で 48） | 値は同じ。N-11 |
| 121 | `:1038-1047` 今の保存 | 1039 `const body`〜1047、1048-1050 `calendar_type` | 一致 |
| 121 | `calendar_service.py:517-522` | 終日の分岐は **518-523** | 1 行ずれ（軽微）。中身は N-5 |
| 128 | `migrations/20261103_200000_add_google_calendar_import_sync.sql:11-34` | 11 `DO $gcal_import_uniq$`・34 で閉じる | 一致 |
| 130 | `routers/calendar.py:104-112`・`:114-121` | `CreateEventBody` 104-111（112 は空行）・`UpdateEventBody` 114-121 | 一致 |
| 131 | `:193` の INSERT | 193 は INSERT の文の行（`db.execute` は 191） | 一致 |
| 143 | ADR-1057:30 | 一致 | 一致 |
| 29 | `backend/app/tasks/google_calendar_sync.py:4` 15 分おき | 一致 | 一致 |

---

## 2. 改訂で生まれた穴・残った穴

### 便1

**5-5 の判定の順番**: 1 変換中 → 2 近道の一覧 → 3 Esc → 4 小窓が開いている → 5 修飾キー → 6 入力欄 → 7 表を引く、の順は正しい。Esc を修飾キー・入力欄の判定より前に置いたので、入力中の Esc で小窓が閉じる。近道の一覧が開いているときの Esc は、金型が document で受けて `stopPropagation`（`Modal.tsx:75`）するため window まで来ない。2 と矛盾しない。ページに他の Modal・Drawer は無い（`SchedulePageImpl.tsx` の import に Modal・Drawer は無く、設定は `:1174` で別の画面へ移る）。順番の穴は見つからなかった。

- **N-6（書き足し）** `c` で出す作る小窓の置き場所: 「今日の 9 時の短い小窓」は、月・一覧の表示では押した枠が無い。`fitPopover(anchor, …)` に枠が無いときの決まり（例: 画面の中央。今の `buildPopoverPosition` の `anchor === null` の分岐 `SchedulePageImpl.tsx:126-131` と同じ）を書く。
- **N-7（行番号）** design 63 の「前例 `Popover.tsx:55`」は `:53`（`const margin = 8;`）。
- **N-8（食い違い）** 一覧の文字のキー名: 表示の切り替えはキーを `` t(`schedule.${nextView}View`) ``（`SchedulePageImpl.tsx:1188`）で組み立てる。今のキーは `schedule.dayView`・`weekView`・`monthView`（`ja.json:3215-3217`）。design 88 の新しいキー `schedule.viewList` では切り替えのボタンに文字が出ない。**直す案**: キーを `schedule.listView` にする。
- **N-9（書き足し）** (a) 小文字にそろえるのは 1 文字のキーだけ（`ArrowRight` などはそのまま比べる）。(b) Safari は変換を確定・取り消した直後の keydown で `isComposing` が偽のことがある。1 に `event.keyCode === 229` も足す。(c) K7 の「効かない 8 件」に「入力欄の中で Esc は閉じる」（効く場合）が入っている。数は 20 件のままでよいので、「効く 12＋入力・修飾・開いている間 8」と呼び方を直す。
- **N-10（書き足し）** 5-5 の 3・4 の「予定の小窓」に、5-3 の「その日の一覧の小窓」も入ると書く（Esc で閉じる・開いている間は文字キーが効かない）。

### 便2

- **N-5（穴・今もある不具合が K9・K11 で表に出る）** 終日の予定の日付が Google で 1 日前にずれる。
  - 画面は終日を `combineDateTime(date, "00:00").toISOString()`（`SchedulePageImpl.tsx:1041`）で送る。`combineDateTime` は端末の時刻で `new Date("YYYY-MM-DDT00:00:00")` を作る（`schedule-utils.ts:75-77`・`:95-96`）。`toISOString()` は UTC の文字なので、日本の端末では 11 月 5 日 0 時が `2026-11-04T15:00:00.000Z` になる。
  - 裏側は終日のとき `{"date": str(start_dt)[:10]}`（`calendar_service.py:519-520`）で先頭 10 文字を取る → `2026-11-04`。終わりは 23:59 → `2026-11-05T14:59Z` → `2026-11-05`。Google の終日の終わりは翌日を指す決まりなので、Google では 11 月 4 日の 1 日の予定になる（推測。コードを読んだ結果で、本番の Google では見ていない）。
  - 今の保存でも同じことが起きている。design 121 の「開始と終了だけを送ると…終日も崩れる。この形にすれば便2 は画面だけで済む」は、題名については正しいが、終日については正しくない。K9 の PO 確認（「終日が変わっていなければ ○」）と、K11 の月の帯で終日の予定を動かす操作で × になる見込み。
  - **直す案**（どれか 1 つを design に書く）: (a) 裏側 `_to_google_event_body` で終日の日付を日本時間に直して取り、終わりは翌日にする（便2 が裏側を 1 か所触る。§3・§4 の「画面だけ」を直し、裏側の試験を足す）。(b) 別の小さな直しとして便2 の前に出す。(c) 便2 では終日の予定を Google に送ったときの確認を K9 から外し、既知の不具合として PO に出す。(a) か (b) を勧める。
- **N-11（注意）** 行の高さ: 表の位置の計算は定数 `DEFAULT_ROW_HEIGHT`（`SchedulePageImpl.tsx:88`・`:611`）、design は CSS 変数を読む。今は同じ 48px。換算は表を描くのと同じ値を使う、と書く（片方だけ変わってずれるのを防ぐ）。
- **N-12（注意）** 送る中身の「種類」: `UpdateEventBody`（`routers/calendar.py:114-121`）に `category` が無く、裏側の `field_map`（`calendar_service.py:271-280`）にも無い。送っても捨てられる（今の保存と同じ）。害は無いが、試験で「種類が送られて直る」を確かめないこと。

### 便3

- **N-1（穴）422 が 500 になる**: 作る口は `try: … await cal_svc.create_event(…) except Exception: raise HTTPException(500)`（`routers/calendar.py:352-364`）、直す口も同じ（`:421-434`）。design 131-132 のようにサービスの中で 422 を出すと（`HTTPException` は `Exception` の仲間）、口が拾って 500「イベントの作成に失敗しました」に変える。K13 の自動試験 4 件は 422 を待つので通らない。**直す案**: (a) 判定を口の側で、サービスを呼ぶ前に行う（`_get_sync_target` を口から呼ぶ。直すときは口で既に予定の行を読んでいる `:390-393` ので、`google_event_id`・`meet_url` もそこで読める）、または (b) 口の `except` の前に `except HTTPException: raise` を足す。(a) を勧める（作る道で「INSERT の前に断る」が口の段で保証される）。
- **N-2（穴）Meet が付かなかったことを画面が知る道が無い**: 作るも直すも返事は `{"id": …}` だけ（`calendar_service.py:251`・`:290`）。Google への送信の失敗は中で拾って `sync_status='failed'` にするだけ（`:241-249`）。§7 の 3（160 行目）の「画面に『Google Meet を付けられませんでした』を出す」と 134 行目の pending で空のまま、を画面が判断する材料が無い。**直す案**: 返事に `meet_url`（付いたときの URL か null）を足し、画面は「Meet を付けるを入れて保存したのに `meet_url` が null」のとき `schedule.meetFailed` を出す、と 5-7 の画面に書く。試験に 1 件足す。
- **N-3（書き足し）** 直すときの判定に要る値: 今の直す道で読むのは `google_event_id` だけ（`calendar_service.py:302-307`、しかも UPDATE の後）。「`meet_url` が空のときだけ」「`google_event_id` がある」を UPDATE の前に判定するには、`google_event_id`・`meet_url` を先に読む、と書く（N-1 の (a) なら口の `:391` の SELECT に足す）。
- **N-4（注意）** 接続状態は管理者だけ読む（`SchedulePageImpl.tsx:891` `enabled: isTenantAdmin`）。つなげるのは管理者なので段1 では足りる。段2 で全員に開くときに外す、と書いておく。
- **N-13（注意）** 直すときの判定は「つないだ人 == 見ている人」と「`google_event_id` がある」。予定の持ち主（`user_id`）が見ている人であることは見ていない。今は Google に送られるのがつないだ人の予定だけ（`:222`）、取り込みの持ち主もつないだ人なので実害は無い。ADR の文（「本人の予定だけ」）とそろえるなら、口で読んでいる `event_owner`（`routers/calendar.py:399`）== 見ている人 も条件に足す。
- §7-3 の 4 件（161-165 行目）は未了のまま。design 182 の「便3 は REVISE（4 件が済むまで）」に同意する。

---

## 3. 便ごとの判定と直す案

### 便1 — APPROVE

根拠: 前回の A-1〜A-9・K2・K3・K7・一覧の分かれ道は、design 16-22・60-113 で直り、引用した行は実物と一致した（Popover の margin の行番号だけ :55→:53）。5-5 の判定の順番に穴は無い。
実装カードに書き足すこと: N-6（`c` の置き場所）・N-7（:53）・N-8（キー名 `schedule.listView`）・N-9・N-10。design を直さずカードに書いてもよい。

### 便2 — REVISE（軽い）

根拠: N-5。`SchedulePageImpl.tsx:1041`（`toISOString()` で UTC の文字）と `calendar_service.py:519-520`（先頭 10 文字）で、終日の予定は Google で 1 日前になる。design 121 の「終日も崩れない」は事実と違い、K9・K11 の PO 確認が × になる見込み。
直す案: N-5 の (a)〜(c) のどれにするかを design §5-6 と §3・§4 に書く。N-11・N-12 を書き足す。直したら差分だけの確認で APPROVE でよい。

### 便3 — REVISE

根拠: N-1（`routers/calendar.py:359-364`・`:429-434` で 422 が 500 になり K13 が通らない）、N-2（`calendar_service.py:251` 返事が id だけで、§7 の 3 の表示ができない）、N-3、§7-3 の 4 件が未了。
直す案: 5-7 に「Meet の判定は口でサービスを呼ぶ前に行う（N-1 の (a)）」「返事に `meet_url` を足し、画面は null なら meetFailed を出す（N-2）」「判定に使う `google_event_id`・`meet_url` を UPDATE の前に読む（N-3）」を足す。§7-3 の 4 件を済ませてから実装カードを書く。

---

## 4. この審査でやっていないこと

- コードは直していない。試験は流していない（設計審査のため）。
- N-5 の 1 日ずれは、コードを読んで出した推測。本番の Google の画面では見ていない（未確認）。端末の時刻が日本であることが前提。
- 本番の同期方式・つないだ Google アカウントで Meet が使えるかは見ていない（未確認のまま）。
- canvas の見本は見ていない（この環境から読めない）。
