VERDICT: REVISE

# 設計審査 1（architect）schedule-settings 便3c

- 対象: `docs/handoff/schedule-settings/design-bin3c.md`・`card-bin3c.md`（枝 `release/schedule-settings-bin3c` = abe07dbab で確認済み）
- 実物の基準: origin/main 331c18613（確認済み）。この枝は main に対して設計とカードの 1 commit だけ（`git rev-list --count abe07dbab..origin/main` は 0）
- 製品コードは変えていない。本番には繋いでいない。

## 結論

設計の中身（式・範囲・文・金型）は正しい。実装が迷う所はカードの試験の手順だけ（R1・R2）。R を直せば APPROVE。

## 1. §2 F1〜F13 の照合（git show origin/main:<path> で全部確認）

| # | 結果 | 実物 |
|---|---|---|
| F1 | 一致 | `schedule-utils.ts:187-191`（`addDays(first, -first.getDay())` は :189） |
| F2 | 一致 | `SchedulePageImpl.tsx:548` |
| F3 | 一致 | `:549-552`（`"ja-JP"` 直書きは :551。設計の §3 は「:550」と書いている → L1） |
| F4 | ほぼ一致 | 関数は `:525-545`（設計は 524 始まり → L1）。引数 9 個・呼び出し `:1647-1657` は一致 |
| F5 | ほぼ一致 | `getWeekDaysFrom` は `:196-201`（コメントが :196）。`:1269`・`:1699`・`CalendarView.tsx:342` は未突合の 1 点を除き一致（CalendarView 側は読んでいない → 未確認） |
| F6 | 一致 | `viewDays` は `:1261-1269` で宣言、読むのは `:1696` の `viewDays[0]`（月の形では `anchorDate` を使う）だけ。`git grep` で他に無いことを確認 |
| F7 | 一致 | `:949` は `{ prefs, isLoaded: prefsLoaded }` だけ受ける |
| F8 | 一致 | `:996` `shownError`、`:1678-1682` の `schedule-error` |
| F9 | 行番号が違う | hook は `useCalendarPreferences.ts:55-61`（`query` を返すのは :60）。設計は :61-67 → L1。`apiQuery.ts:27` の `retry: 0` は一致 |
| F10 | 一致 | `ScheduleSettingsPage.tsx:161-170`・`:519`・`:619`。`:519` は `prefsError`（保存の失敗）だけ |
| F11 | 一致 | `useSeededForm.ts:30` |
| F12 | 一致 | ja `:3410`・`:3591`。en は `prefsSaveError` が :3409（ja とずれる。キーは同じ） |
| F13 | 一致 | 試験の置き場・擬似応答の行（`SchedulePageImpl.test.tsx:54`（コメント行）・`:80`、`ScheduleSettingsPage.test.tsx:34`・`:57`・`:480`）。ただし擬似応答は成功を返すだけ（R1） |

## 2. §4 の式・§5 K1 の計算（node で実測）

- 式 `addDays(first, -((first.getDay() - weekStart + 7) % 7))`: 2024〜2028 年の全 60 か月 × weekStart 0/1 で、1 つ目の曜日が weekStart と一致・月初以前・月初から 6 日以内・42 個で月末まで届く、を全部確認（違反 0）。
- K1: 2026-11-01 は日曜。weekStart 0 → 2026-11-01（日曜）、weekStart 1 → 2026-10-26（月曜）。設計の日付と一致。
- 見出し: 2024-01-07 は日曜、`7 + weekStart` で 2024-01-08 は月曜。正しい。

## 3. 観点ごと

- 範囲の漏れ（getMonthCells）: src の呼び出しは `SchedulePageImpl.tsx:548`・`:1262` の 2 か所だけ。試験は `getMonthCells` を使っていない（`getWeekDays` のみ）。既定 0 なので渡し忘れても今と同じ。範囲は足りている。
- 擬似データ: 2 つの擬似応答に失敗の切替えが無い（R1）。さらに `SchedulePageCache.test.tsx:69-76` は `/calendar/preferences` に「想定外の GET」で投げるため、この便の後はそのファイルの全試験で `prefsLoadErrorSchedule` の文が出る（R2）。
- i18n: ja/en の同じキー 2 つで足りる。`prefsLoadError`・`prefsLoadErrorSchedule` の ja の文に「失敗」「エラー」「できません」が入らないので `check-error-text-next-action.js` の対象外（増えた・減ったの赤は出ない）。文に「失敗」を足すと赤になるので足さないこと（L3）。
- 金型: 設定ページは `:519` と同じ `error-message` `role="alert"`、予定ページは既存の `schedule-error`。新しい部品・CSS・色は無い。`check:page-size`: `ScheduleSettingsPage.tsx` は 760 行・上限 800 で、足すのは数行のため問題なし。
- 失敗の文が出る・消える条件: 設定ページ `prefsQ.isError && !prefsReady`、予定ページ `live && prefsQuery.isError && !prefsLoaded`。どちらも query の状態から作るので、読み直しで成功すれば消える。見本の状態は `live` が偽で出ない。`error`・`built.failed`・`staleFailed` が先に勝つ並びも式として正しい（`?:` は右結合）。再読み込みが起きる条件（画面に戻る等）は未確認 → L4。
- カードだけで迷わないか: 変更1・変更2 の本体は迷わない。試験（変更3）が迷う（R1）。

## 4. 必須の直し（R）

- **R1（カード 変更3・K2・K3・K4）: 試験の作り方が足りない。** 直す場所は `card-bin3c.md` の「変更3 試験」。
  - K3・K4 の「初期値の GET を失敗させる」は、今の擬似応答に切替えが無い。`SchedulePageImpl.test.tsx:80-83` と `ScheduleSettingsPage.test.tsx:57-60` は `/calendar/preferences` に必ず成功を返す。`answers` に失敗の切替え（例: `prefsFail: boolean`）を足し、その枝で例外を投げる、と書く。`SchedulePageImpl.test.tsx` の `beforeEach`（`:119` 付近）・`ScheduleSettingsPage.test.tsx` の `beforeEach` で戻すことも書く（戻さないと次の試験に残る）。
  - K2 の「マスの 1 つ目が月曜の日付」は、この試験が時計を固定していない（`useFakeTimers`・`setSystemTime` の使用なし）ため、今の月で変わる。「試験の中で `new Date()` から今月 1 日を求め、月曜始まりの 1 つ目の日付を期待値にする」か、時計を固定するかを指定する。
  - 見出しとマスの取り方の指定が無い。マスは `<button className="schedule-mini-calendar__day">`（`SchedulePageImpl.tsx:597-608`）、見出しは `.schedule-mini-calendar__weekdays` の `<span>`（`:588-589`）。取り方（`container.querySelector` 等）を 1 行で指定する。
  - 見出しの文字は `Intl` の `"ja-JP"` で作られるので、画面の言語が en でも「月」「日」になる（§3 対象外と同じ）。K2 の期待値は日本語の曜日名、と書く。
- **R2（カード 変更3 または停止条件）: `SchedulePageCache.test.tsx` は触らないファイルだが、この変更で擬似応答の想定外の GET が表に出る。** `SchedulePageCache.test.tsx:75` は `/calendar/preferences` で例外を投げる。実装後は同ファイルの全画面で初期値の失敗の文が `schedule-error` に出る。今ある確認は `errorFetch` の有無だけ（`:50`・`:153`）で、`errorFetch` が先に勝つので落ちない見込み（実行はしていない → 未確認）。カードに「SchedulePageCache.test.tsx は触らない・落ちたら停止条件」ではなく、「同ファイルの擬似応答は初期値を投げる。文が出ても落ちないことを試験で確かめ、落ちたら BLOCKED:」と書く。落ちる場合の直し方（同ファイルに初期値の応答を足す）も、触るファイル一覧への追加として決める。

## 5. 軽い指摘（L）

- **L1** 行番号の細かいずれ: F3/§3 の `"ja-JP"` は `:551`（設計は :550）、F4 の関数は `:525` 始まり、F9 の hook は `useCalendarPreferences.ts:55-61`、F5 の `getWeekDaysFrom` は `:196-201`。実装に影響しない。直すなら設計の表だけ。
- **L2** F12: en の `prefsSaveError` は :3409（ja は :3410）。「`prefsSaveError` の次に置く」は両方で通じる。
- **L3** カード「変更2」に「ja の文に『失敗』『エラー』『できません』を入れない（`check:error-text-next-action` が赤になる）」と 1 行足すと、実装が文を変えても安全。
- **L4** 「失敗の文が消える条件」: 読み直しで成功すれば消えるが、読み直しが起きる契機（画面に戻る・フォーカスの戻り）は `queryClient` の既定に依存し、未確認。設計 §7 は「消えない」を心配しているが、設定ページの文言は「ページを開き直してください」なので実害は小さい。
- **L5** K6（本番の JS の中の文の数え方）: 文字が `\u` で出力される場合は 0 件になり得る。Opus が数えるときは日本語の生の文字と `\u` 形の両方で数える、と書くと迷わない。
- **L6** 設計 §10「審査の記録」は空のまま。審査 1 の結果（本ファイル）を指す 1 行を、直したあとに足す。

## 6. 確認した事実と未確認

- 確認: 上の F1〜F13 の実物・`getMonthCells` の呼び出し 3 件（定義 1・呼び出し 2）・K1 の日付と式（node 実測）・`check-error-text-next-action.js` の仕組み・`ScheduleSettingsPage.tsx` の行数（760）。
- 未確認: 実装後に試験・型・lint が通るか（実行していない）・`CalendarView.tsx:342` の中身・再読み込みの契機。
