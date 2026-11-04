# architect-review: 予定の画面を Google カレンダーに寄せる 段1（2026-11-04）

- 審査した HEAD: `dfb046c0e137db7229e35834a6ac8741e50ea0ae`（`origin/release/schedule-gcal-alignment`。指定の `dfb046c0e` で始まることを `git rev-parse HEAD` で確認）
- 審査した文書: `docs/handoff/schedule-gcal-alignment/design.md`（175 行）・`recon.md`（92 行）を全文
- 審査役: クラウドの Architect（design を書いた AI とは別のセッション）。コードは直していない

| 便 | 判定 | 一言 |
|---|---|---|
| 便1（小窓・短い作る小窓・月の1行・他◯件・一覧・近道） | **REVISE**（軽い） | 方向は良い。近道の Esc と入力欄の除外がぶつかる、近道の一覧（Modal）が開いている間に他のキーが効く、K7 の件数の数え違い、「他◯件」が日の枠の押下まで拾う、一覧を足したときに直す分岐の書き漏れ、小窓の中身が変わったときに測り直さない。どれも design の文を直せば済む |
| 便2（引っぱる・動かす・長さ・月の帯） | **REVISE** | 「開始と終了だけ PATCH」は裏側の変換で Google の題名が空になる（下の B-1）。直さずに出すと Google 側のデータを壊す |
| 便3（Google Meet） | **REVISE** | 422 の場所（保存の後では遅い）、直すときの本人判定が無い、`add_meet` だけの直しが何もせず戻る、`events.get` の関数が無い、K14 の前提（取り込みの方式）が書かれていない。§7-3 の前提確認 3 件も未了のまま |

REJECT は無い。3 便とも、下の「直す案」を design に入れれば実装可能に上げてよい。

---

## 1. recon の行番号つき引用の突き合わせ（30 か所）

基準は HEAD `dfb046c0e`（recon の基準 `7d56ab771` との差は docs 1 commit だけなので、コードの行は同じはず）。

| # | recon / design の引用 | 実物 | 結果 |
|---|---|---|---|
| 1 | `SchedulePageImpl.tsx:122-144` `buildPopoverPosition`、`:123-125` 320/420/12、`:142` top の clamp | 122 で関数開始、123-125 の 3 定数、142 の `const top = clamp(...)`、144 で閉じ | 一致 |
| 2 | `schedule.css:679-693` `.schedule-popover`、`:683` max-height、`:692` overflow | 679 開始・683 `max-height: min(...)`・692 `overflow: auto;`・693 閉じ | 一致 |
| 3 | `tokens.css:407` `--schedule-popover-max-h: 34rem` | 407 | 一致 |
| 4 | `tokens.css:76` `--space-3: 12px` | 76 | 一致 |
| 5 | `SchedulePageImpl.tsx:284-410` 作る小窓の欄 | 欄の箱 `schedule-popover__body--form` は 285 開始・410 閉じ（284 は `) : (`） | 1 行ずれ（軽微） |
| 6 | `:413-435` 下の帯 | 413 `schedule-popover__footer`・435 閉じ | 一致 |
| 7 | `:321`・`:336` Toggle 使用 | 321・336 に `<Toggle` | 一致 |
| 8 | `Toggle.tsx:145-165` 切替スイッチ | **ファイルは 41 行しかない**。部品は `Toggle.tsx:21`（`forwardRef<HTMLInputElement>`）、中身は `<input type="checkbox" role="switch">`（`Toggle.tsx:27-31`） | **ずれ** |
| 9 | `Popover.tsx:47-92` `calcPosition` | 47 開始・89 `return { top, left }`・90 閉じ | 終わりが 2 行ずれ（軽微） |
| 10 | `Popover.tsx:81` 反転しないコメント、`:82-89` 押し戻し | コメントは **79**、押し戻しは **80-87** | **ずれ** |
| 11 | `Popover.tsx:55` margin（design §5-1） | 55 `const margin = 8;` | 一致（値は 8。design は 12 を使う。理由が書いてあるので可） |
| 12 | `Popover.tsx:56-58`「測ってから押し戻す」前例のコメント（design §8） | 56 は scrollY を足さないコメント。押し戻しの考え方のコメントは **79** | **ずれ** |
| 13 | `Popover.tsx:112` `visible`（design §5-1） | `const [visible, setVisible]` は **110** | **ずれ** |
| 14 | `:755` `ScheduleMonthGrid`、`:801` `slice(0, 3)` | 755・801 | 一致 |
| 15 | `:805-823` 月の札、`:808` 背景色、`:815-821` 種類の札 | 805 `<button`・808 `style={{ background: ownerMeta.color ...}}`・815-821 札 | 一致 |
| 16 | `:826-828`「+N件」の span | 826 条件・827 `<span className="schedule-month__more">`・828 | 一致 |
| 17 | `schedule.css:647-665` `.schedule-month__event`、`:661-665` 最後の span | 647・661-665 | 一致 |
| 18 | `ja.json:3195` `"moreCount": "+{{count}}件"` | 3195（en.json も 3195 で `"+{{count}} more"`） | 一致 |
| 19 | `schedule-utils.ts:1` `ScheduleView`、`:54` `source`、`:147-157` 期間 | 1・54・147-157 | 一致 |
| 20 | `SchedulePageImpl.tsx:1179-1188` 日・週・月の切替 | 1180 で `(["day","week","month"] as const).map` | 一致 |
| 21 | `:1090-1096` 前後の移動、`:1123-1125` `canEditSelected`、`:1053` PATCH | 1090-1096・1123・1053 | 一致 |
| 22 | `:1160-1167` 虫めがねに `onClick` が無い | 1161-1167 の `Button`（`aria-label={t("common.search")}`）に onClick 無し | 一致 |
| 23 | `:703-709` 空き枠、`:726-729` 予定を押す、`:724` 背景色、`:891` status 取得、`:4` FullCalendar を外した | 703-709・724・726-729・891・4 | 一致 |
| 24 | `backend/app/services/google_calendar.py:41` `_SCOPES`、`:377-389`/`:385` insert、`:392-404`/`:400` patch | 41・377/385・392/400 | 一致 |
| 25 | `calendar_service.py:180-253` `create_event`、`:192-218` INSERT、`:222` 送る条件、`:229` id を使う | 180・191-217（INSERT と commit）・222。id を取るのは **228** `google_event.get("id")` | 1 行ずれ（軽微） |
| 26 | `calendar_service.py:259` `update_event`、`:309-318` Google も直す | 259・310 の `if google_event_id and sync_mode in (...)`・315 送信 | 一致 |
| 27 | `calendar_service.py:432-501` 取り込み、`:432` `_is_app_origin`、`:449` location、`:486` 更新の条件、`:509-530` `_to_google_event_body` | 取り込み関数 `upsert_from_google` は 410 開始（432 は呼び出し）・449・486 `WHERE calendar_events.source = 'google'`・509-530 | 一致（範囲の頭は 410 が正確） |
| 28 | `routers/google_calendar.py:238-264` status、`google_calendar.py:155-178` `require_calendar_owner` | status は 238（`@router.get`）・242 関数。`require_calendar_owner` は **routers** の 155。**services** の 155-178 は `exchange_code` の docstring | パスがあいまい（routers と明記すれば一致） |
| 29 | `routers/calendar.py:104-119` 作る・直すの形 | `CreateEventBody` 104・`UpdateEventBody` 114-121（`calendar_type` が 121） | 終わりが 2 行ずれ（軽微） |
| 30 | `migrations/20261103_200000_add_google_calendar_import_sync.sql:11-34`（会社ごとに回す書き方）、`FEATURE-INDEX.md:34` | 11-34 が `DO $gcal_import_uniq$ ... FOR schema_rec ...`・34 が カレンダー行 | 一致（ただし 34 行目の説明文は「取り込みは止める」のままで ADR-1059 と食い違う。§3 参照） |

ずれのまとめ: 中身が別物を指すのは #8（Toggle.tsx:145-165）と #12（Popover.tsx:56-58）。行番号の小ずれは #5・#9・#10・#13・#25・#29。パスがあいまいなのは #28。設計の判断を変えるずれは無い。直す案: recon と design の該当行を上の「実物」の番号に書き換える。

---

## 2. 確かめた点ごとの所見

### 2-1. 受入条件 K1〜K14 は ○× で判定できるか

| K | 判定できるか | 所見と直す案 |
|---|---|---|
| K1 | △ | PO の確認（23 時台の枠を押して保存ボタンが見える）は ○× にできる。自動試験の「9 通り×3 種で 27 件」は純粋な関数 `fitPopover` の試験で、jsdom では小窓の高さを測れない（`getBoundingClientRect` が 0 を返す）。「3 種の高さ」を何 px とするかが書かれていない。**直す案**: 3 種の高さを決める（例: 詳しく＝実測値、短い作る小窓＝実測値、直す＝上限いっぱい `34rem` と 画面−24px の小さい方）。さらに、部品が測った値で `fitPopover` を呼び、結果を `style` に当てることを 1 件の部品試験（`getBoundingClientRect` を差し替え）で確かめる |
| K2 | △ | 「題名の行」が見出し（`.schedule-popover__header` `SchedulePageImpl.tsx:214`）なのか、作る小窓の題名の入力欄（`:287` 付近。`__body--form` の中＝動く側）なのかが読めない。design §5-1 の CSS では入力欄は動く。**直す案**: K2 を「見出しの行（閉じる・直す・消すのボタンの行）と保存の行は動かず…」に書き換える |
| K3 | ○ | ただし K3 の欄の並び（題名・時刻・種類・社員にも見せる）と §5-2（＋終日）が 1 つ違う。どちらかにそろえる |
| K4 | ○ | |
| K5 | ○ | 実装の穴は 2-4 に書く（日の枠の押下を拾う） |
| K6 | ○ | |
| K7 | △ | 近道の数は T・J・→・K・←・D・W・M・A・C・Esc・? で **12**。「11 件すべて合格」と合わない。入力欄の中で効かないことの試験も別に要る。**直す案**: 「12 キー×効く＋入力欄・IME・Ctrl/⌘/Alt 付き・小窓や近道一覧が開いている間で効かない、の計 ◯ 件」と数え直して書く |
| K8 | ○ | |
| K9 | ○ | 実装の穴は B-1（Google の題名が消える）。PO の確認に「Google 側の題名が変わっていない」も足す |
| K10 | ○ | |
| K11 | ○ | |
| K12 | ○ | 前提に「同期方式が送る方式（write_only か bidirectional）」が要る。§7-3-1 のとおり |
| K13 | ○ | ただし直す（PATCH）の道が抜けている（C-2）。「作るとき・直すときの両方で 422・Google に送られない」に広げる |
| K14 | △ | 取り込みが動くには同期方式が bidirectional であることが前提（ADR-1059:38「取り込みだけ止めるときは write_only」）。K12 は write_only でも通るが K14 は通らない。**直す案**: K14 の前提として「同期方式 bidirectional」を §7-3 に足す。15 分以内は `backend/app/tasks/google_calendar_sync.py:4`（15 分おき）と一致 |

### 2-2. 便1・便2・便3 の範囲と触らない範囲

- §3 の対象外（段2・探す・Meet を外す・種類の色・狭い画面・Google のロゴ）は明確。§4 の便の分け方も明確で、便1・2 が画面だけ、便3 が `migrations/` を含む、の線引きは合っている。
- ただし便2 は「画面だけ」と書かれているが、B-1 を画面だけで直すには「PATCH に今の全部の欄を送る」形にする必要がある（裏側の `_to_google_event_body` を直すなら便2 は裏側も触ることになり、§4 の表と食い違う）。どちらにするかを design に書く。
- 便1 の一覧を足すと、`view` を「月か日か、それ以外は週」と 3 択で分けている箇所に 4 つ目が入る。触る範囲として次を列挙しておく: `SchedulePageImpl.tsx:116-117`（見出しの文字）・`:935`（左の小さい月）・`:973`（`if (view === "month") return;` 今の時刻へ動かす処理）・`:1098-1100`（`viewDays` の 3 択。list は週に落ちる）・`schedule-utils.ts:147-157`。

### 2-3. ADR との食い違い

| ADR | 結果 | 根拠・直す案 |
|---|---|---|
| ADR-027（文字は `t()`） | 食い違い無し | 新しい文字はすべて ja・en のキーで書かれている（§5-2〜5-7）。`frontend/src/locales/` は ja・en の 2 つ |
| ADR-067（トークン） | 注意 2 点 | (1) `fitPopover` が返す高さの上限を `style={{ maxHeight: 数 }}` で当てると ESLint の禁止（ADR-067「強制ルール」maxHeight の数値）に当たる。文字列（`` `${n}px` ``）か CSS 変数で当てる、と §5-1 に書く。(2) 便2 の `--schedule-drag-ghost-bg` は色の意味のトークン。ADR-067「新規トークン追加手順」4（ADR の表を更新）と、ダーク版の確認（参照先 `--calendar-google-blue-light` は `index.css:184`・`:384` に両方あるので `check:dark-parity` は通る見込み）を手順に入れる |
| ADR-144（金型） | 食い違い無し | `Popover.tsx` を使わない理由が §5-1・§6 にある。ゲートの禁止対象（生 select・生 input・自作タブ・直書きの色）は design の中に出てこない。一覧の行・「他◯件」の生 `<button>` は禁止対象外 |
| ADR-1057（接続は会社で1つ・送るのは本人の予定だけ） | **食い違いの穴 1 点** | 作る道は本人判定あり（`calendar_service.py:222`）だが、直す道は本人判定なしで Google を直す（`:310`。ADR-1057:30 で受け入れ済みの挙動）。design §5-7 の「直す」の条件に本人判定が無いので、他の管理者が PO の予定に Meet を付けられる → K13 と食い違う（C-2） |
| ADR-1059（取り込みは本人の予定を personal で） | 前提の書き漏れ | K14 は bidirectional 前提（上の K14）。取り込みはアプリで作った予定を飛ばす（`:432`）ので、アプリで作って Google 側で Meet を付けた予定は K14 の対象外になる。対象外に明記する |
| ADR-135・ADR-136 | 食い違い無し | 便3 だけ PO の「GO #番号」（§4）。なお `docs/adr/` に ADR-136 が 2 つある（`ADR-136-cc-bot-github-identity.md` と `ADR-136-company-stats-ssot.md`）。recon は正しいほうを名指ししている |
| ADR-1018（RLS） | 食い違い無し | 便3 で `tenant_google_calendar_config` の形は変えない |
| FEATURE-INDEX | 古い説明 | `docs/adr/FEATURE-INDEX.md:34` の説明が「Google→アプリの取り込みは止める」のまま（ADR-1059 で取り込みを始めた）。便3 で 34 行目に新 ADR を足すとき、説明も今の状態に直し、ADR-1059 も並べる |

### 2-4. 便1: 小窓の収まり計算と近道

**収まり計算（K1・K2）**
- 考え方は正しい: CSS の `max-height: min(34rem, 100vh − 24px)`（`schedule.css:683`）で高さが画面−24px 以下になるので、測った高さ h について `clamp(top, 12, vh − h − 12)` は常に成り立つ（12+12=24 で CSS の余白と一致）。横も `min(20rem, 100vw − 24px)` で同様。
- **A-1（穴）**: 測り直すのが「画面の大きさが変わったら」だけ（§5-1）。短い作る小窓で「詳しく入れる」を押すと高さが伸びるが、位置は伸びる前のままなので、下に置いた小窓の保存ボタンが画面の外に出る（K1・K3 が同時に壊れる）。**直す案**: 測り直しのきっかけに「中身が変わったとき」（`ResizeObserver` で小窓自身を見る、または `mode`・詳しく入れるの開閉を依存に入れた `useLayoutEffect`）を足す。
- **A-2（注意）**: 小窓の上限の高さを inline style で当てるなら ADR-067 の数値禁止に当たる（2-3）。
- A-3（注意）: 日の表示の空き枠は横幅が広く、右にも左にも入らない。§5-1 の 1「どちらも入らなければ押し戻す」で枠に重なる位置に出る。これは許容と明記しておく（今の `buildPopoverPosition` も同じ）。

**近道（K7）が入力中に誤動作しないか**
- **A-4（穴）Esc と入力欄の除外がぶつかる**: §5-5 は「`event.target` が input・textarea・select なら効かない」と「小窓が開いているときは Esc だけ効く」を並べている。作る小窓では題名の入力欄にフォーカスがある（`TextFieldControl`、`:287`）ので、書いたとおりに作ると入力中の Esc で小窓が閉じない。**直す案**: 「Esc は入力欄の中でも効く（ただし `isComposing` 中は効かない＝変換の取消を優先）。文字のキーだけ入力欄の除外を受ける」と書く。
- **A-5（穴）近道の一覧（Modal）が開いている間に他のキーが効く**: 金型 `Modal.tsx:74-80` は document で Esc だけを見る。ページの window の `keydown` は止まらないので、一覧を開いたまま `w`・`m` を押すと裏の表示が変わり、`c` で作る小窓が Modal の後ろに出る。**直す案**: 「小窓または近道の一覧が開いているときは、Esc（と一覧の上での ?）以外は効かない」と書き、試験に入れる。
- A-6（注意）`Toggle` は `<input type="checkbox">`（`Toggle.tsx:27-31`）なので、スイッチにフォーカスがあると近道は効かない。安全側なので可。ボタン（`<button>`）にフォーカスがあるときは効く。これで良いかを明記する。
- A-7（注意）文字の比較: CapsLock で `event.key` が大文字になる。`?` は Shift を押して出す。除外条件に Shift を入れない・文字は小文字にそろえて比べる、と書く。押しっぱなし（`event.repeat`）で `j` が連続して進むのを許すかも決める。
- A-8（注意）ほかの画面の document の `keydown`（`MobileShell.tsx:97` は Esc だけ）との重なりは見当たらない。

**月の「他◯件」（K5）**
- **A-9（穴）**: 月の日の枠は `onClick={(event) => onSelectDay(date, ...)}`（`SchedulePageImpl.tsx:797`）で作る小窓を開く。`:827` の span を button にするだけだと押下が枠へ伝わり、一覧の小窓と作る小窓が両方開く。今の予定の札は `event.stopPropagation()`（`:810`）で止めている。**直す案**: §5-3 に「`stopPropagation` する（予定の札と同じ）」と書く。

**一覧（K6）**: 2-2 の分岐の列挙を §5-4 に足す。`toRangeStart`・`toRangeEnd` の list の試験（30 日・月をまたぐ・夏時間なし）を §5-4 の試験に足す。

### 2-5. 便2

- **B-1（穴・データを壊す）**: §5-6「離したら PATCH に開始と終了だけ送る」。口は送られなかった欄を落として渡す（`routers/calendar.py:382` `body.model_dump(exclude_none=True)`）。裏側の `update_event` は送られた欄だけを表に入れる（`calendar_service.py:271-286`）が、Google へ送る中身は `_to_google_event_body(payload)`（`:314`）で作り、`"summary": payload.get("title", "")`（`:512`）なので **Google の予定の題名が空で上書きされる**。`is_all_day` も無いので終日の予定は時刻つきとして送られる（`:517-522`）。今の保存（`SchedulePageImpl.tsx:1038-1047`）は全部の欄を送るので起きていない。**直す案**（どちらか）: (a) 画面から、動かす予定の今の題名・終日・説明・場所も含めて送る（便2 は画面だけのまま。§5-6 に明記）。(b) 裏側で Google へ送る中身を表の今の行から作る（便2 が裏側を触る。§4 の表を直す）。(a) を勧める。どちらでも K9 の PO 確認に「Google 側の題名が変わっていない」を足す。
- B-2（注意）位置→分の換算の起点: 週の表は縦に動く箱の中にある。「位置(px)」を、押した日の列の `getBoundingClientRect().top` からの差で測る、と書く（箱の動いた量を足し忘れる誤りを防ぐ）。
- B-3（注意）`canEditSelected`（`:1123`）は選んだ 1 件用の値。予定ごとに判定する関数に切り出す、と書く。
- B-4（注意）月の帯（K11）を入れると、1 日 3 件（`:801`）の数え方と「他◯件」の数が帯の分だけ変わる。帯を何件として数えるかを決める。

### 2-6. 便3（Meet）の穴

- **C-1（穴）422 の場所**: 今の `create_event` は先に INSERT して commit する（`calendar_service.py:191-217`）。送る条件を見るのはその後（`:220-222`）。§5-7 の書き方だと、本人以外が `add_meet` 付きで作ると「予定は保存済みなのに 422」になる。**直す案**: 「`add_meet` の判定は INSERT の前に行い、422 のときは何も保存しない」と書く。K13 の試験に「表に行が増えていない」を足す。
- **C-2（穴）直すときの本人判定**: §5-7「直す: `add_meet` が真で、`google_event_id` があり、`meet_url` が空のときだけ」に本人判定が無い。直す道は他の管理者でも Google を直す（`:310`・ADR-1057:30）ので、他の管理者が PO の予定に Meet を付けられる。**直す案**: 直すときも「`connected_by == user_id` かつ送る方式」でなければ 422。`google_event_id` が無い予定（送っていない予定）に `add_meet` が来たら 422 にするか無視するかを決めて書く。
- **C-3（穴）`add_meet` だけの直しが何もしない**: `update_event` は表に入れる欄が無いと `return {"id": event_id}`（`:289-290`）で Google を呼ばずに戻る。画面が `add_meet` だけを送る作りだと Meet は付かない。**直す案**: 早く戻る条件に `add_meet` を入れる、または画面は常に全部の欄を送ると決める。
- **C-4（穴）`events.get` の関数が無い**: `services/google_calendar.py` の関数は `get_events`（348・一覧）・`create_event`（377）・`update_event`（392）・`delete_event`（407）だけ。§5-7 の「1 秒おきに 2 回まで `events.get`」を書くには新しい関数 `get_event(db, tenant_id, event_id)` が要る。待つのは `asyncio.sleep`（`time.sleep` は他の要求を止める）と書く。
- **C-5（穴）pending の後で Meet が付いたとき**: 2 回読んでも `hangoutLink` が無ければ `meet_url` は空のまま（§5-7）。ところが取り込みはアプリで作った予定を飛ばす（`:432`）ので、後で Google 側に Meet が付いても `meet_url` に入る道が無い。**直す案**: (a) 画面に「付けられませんでした」を出して PO がもう一度押せば `meet_url` 空なので直すの道で付く（今の設計のまま）と明記する、または (b) 詳しくを開いたときに読み直す。(a) で足りる。なお、Meet の作成が非同期のとき 2 回目の `patch` に新しい `requestId` を送ると Meet が 2 つできる心配は、`hangoutLink` が予定に 1 つしか持てないので実害は無いが、同じ `requestId` を使い回すと Google は同じ要求とみなす。直すとき（2 回目）は新しい `requestId` を作る、と書く。
- C-6（注意）列を足したあとの読み出し: 一覧の SELECT は位置で読む（`calendar_service.py:135`・`:162` `r[10]`）。`meet_url` は SELECT の最後に足す、と書く（途中に入れると後ろの番号がずれる）。画面の `ApiCalendarEvent`（`schedule-utils.ts:13`）・`ScheduleItem`（`:46`）・`normalizeEvent`（`:159`）にも足す。
- C-7（注意）取り込みの更新: `ON CONFLICT ... DO UPDATE SET`（`:476-486`）に `meet_url = EXCLUDED.meet_url` を足す、と書く（Google で Meet を外したら空に戻る）。INSERT の列にも足す。
- C-8（注意）接続状態の口: 今の `connection_status`（`routers/google_calendar.py:242-245`）は見ている人を受け取っていない（`get_current_tenant` と `get_db` だけ）。`meet_available` を出すには人の依存を足す。同期方式も今は読んでいない（SELECT は `calendar_id, connected_at` だけ）。
- C-9（前提・§7-3 の 2 の手がかり）: `backend/app/services/tenant.py` に `calendar_events` の作成は無い。表は `migrations/078_create_calendar_events_tenant.sql` で作られ、`scripts/run_all_migrations.sh:377` で流れている。新しい列の migration も `scripts/run_all_migrations.sh` に足す（前例 `:1217` が `20261103_200000_add_google_calendar_import_sync.sql`）。新しい会社に表がどう入るか（078 を流し直すのか）は未確認のまま。§7-3 の 2 として残す。
- C-10（前提）§7-3 の 3 件（本番の同期方式・新しい会社の表の作られ方・試験の場所）は design 上まだ未解決。これが済むまで便3 を「実装可能」にしない、という design §9 の判断には同意する。K14 の前提（bidirectional）を 1 件目に足す。

---

## 3. 便ごとの判定

### 便1 — REVISE（軽い）

根拠: A-1（`SchedulePageImpl.tsx` 予定の小窓は中身で高さが変わるのに §5-1 は画面の大きさの変化でしか測り直さない）、A-4（§5-5 の除外と Esc が矛盾。題名欄 `:287` 付近）、A-5（`Modal.tsx:74-80` は Esc しか見ない）、A-9（`:797` の日の枠の onClick）、K7 の件数（12 キー）、K2 の「題名の行」のあいまいさ、一覧で増える分岐（`:116`・`:935`・`:973`・`:1098-1100`）、ADR-067 の maxHeight。
直す案: 上の各「直す案」を design §2・§5-1・§5-3・§5-4・§5-5 に入れる。入れたら APPROVE でよい（再審査は差分だけで足りる）。

### 便2 — REVISE

根拠: B-1（`calendar_service.py:512` で題名が空になり Google の予定を壊す。`:517-522` で終日が崩れる）。B-2〜B-4 は書き足し。
直す案: §5-6 に「動かしたときの PATCH は、題名・開始・終了・終日・説明・場所を送る（今の保存 `SchedulePageImpl.tsx:1038-1047` と同じ形）」を足し、K9 の確認に「Google 側の題名が変わらない」を足す。試験に「動かしたときの送る中身に題名がある」を足す。

### 便3 — REVISE

根拠: C-1（`calendar_service.py:191-217` で保存が先）、C-2（`:310` 直す道に本人判定が無い・ADR-1057:30）、C-3（`:289-290` 早く戻る）、C-4（`google_calendar.py` に 1 件読む関数が無い）、C-5（`:432` で取り込みが飛ばす）、K14 の前提（ADR-1059:38）、§7-3 の未了 3 件。
直す案: C-1〜C-8 を §5-7 に入れ、K13 を「作る・直すの両方」に、K14 に前提を足す。§7-3 に「同期方式が bidirectional か（K14 用）」を足し、3＋1 件を確かめてから実装カードを書く。新しい ADR には「直すときも本人だけ」「`meet_url` 1 か所」「取り込みでも `hangoutLink` を読む」を入れる。

---

## 4. この審査でやっていないこと

- コードは直していない。試験は流していない（設計審査のため）。
- 本番の同期方式・つないだ Google アカウントで Meet が使えるかは見ていない（未確認のまま。recon §5 と同じ）。
- canvas の見本は見ていない（この環境から読めない）。
