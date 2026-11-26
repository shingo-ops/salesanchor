# 設計 schedule-settings 便3c — 小さい月カレンダーの週の始まり・初期値の読み込み失敗を画面に出す

> この文書は何か：便3b（ひとりひとりの初期値）の後に残った軽い点 2 つを直す設計です。画面だけの変更で、DB・API は変えません。

- 状態: 設計案作成済み（Opus・2026-11-26）。PO は 2026-11-26 に「1」（この 2 点を設計から本番まで進める）を選んだ。実装・マージ・本番反映までの委任は同じ流れ（design-bin3b.md の委任と同じ）
- 基準: origin/main 331c18613（#5778 の合流）
- 関連: `docs/handoff/schedule-settings/design-bin3b.md`（初期値の本体）・`docs/specs/schedule/README.md`・ADR-027（文字は `t()`）・ADR-1054（読み方は `useApiQuery`）・ADR-144（金型）

## 1. 目的（PO の言葉に寄せて）

- 「週の始まり」を月曜にした人は、右の大きい表は月曜から始まる。左の小さい月カレンダーは今も日曜から始まる。これを同じにする。
- 自分の初期値が読めなかったとき、今は何も出ない。設定ページでは保存ボタンが押せないまま、理由が分からない。予定ページは黙って標準の形で開く。読めなかったことを文で出す。

## 2. 今の実物（origin/main 331c18613）

| # | 事実 | 場所 |
|---|---|---|
| F1 | 月のマス 42 個を作る関数は、必ず日曜から始める（`-first.getDay()`） | `frontend/src/pages/schedule/schedule-utils.ts:187-191` |
| F2 | 小さい月カレンダーは F1 を `getMonthCells(currentMonth)` で呼ぶ | `frontend/src/pages/schedule/SchedulePageImpl.tsx:548` |
| F3 | 小さい月カレンダーの曜日の見出しは 2024-01-07（日曜）から 7 日を並べる＝必ず日曜から | `frontend/src/pages/schedule/SchedulePageImpl.tsx:549-552` |
| F4 | `ScheduleSidebar` は週の始まりを受け取っていない（引数は 9 個） | `frontend/src/pages/schedule/SchedulePageImpl.tsx:525-545`・呼び出し `:1647-1657` |
| F5 | 大きい表（週・月）は週の始まりに従っている（`getWeekDaysFrom(anchorDate, prefs.week_start)`・`weekStart={prefs.week_start}` → FullCalendar `firstDay`） | `SchedulePageImpl.tsx:196-201`・`:1269`・`:1699`・`frontend/src/components/CalendarView.tsx:342` |
| F6 | 月の形の `viewDays` も F1 を呼ぶ（`getMonthCells(anchorDate)`）。ただし月の形で使うのは `anchorDate` で、`viewDays` は使っていない（`viewDays` を読むのは `:1696` の `viewDays[0]` だけで、月の形では読まない） | `SchedulePageImpl.tsx:1261-1269`・`:1696` |
| F7 | 予定ページは初期値の読み込みの成否を見ていない（`prefs`・`isLoaded` だけ取る）。読めないと既定値のまま | `SchedulePageImpl.tsx:949` |
| F8 | 予定ページの失敗の文は `shownError` 1 つで、`schedule-error` の枠に出す | `SchedulePageImpl.tsx:996`・`:1678-1682` |
| F9 | 初期値の hook は `query` も返す。`useApiQuery` は `retry: 0`（1 回の失敗で `isError`） | `frontend/src/features/schedule/useCalendarPreferences.ts:55-61`・`frontend/src/lib/query/apiQuery.ts:27` |
| F10 | 設定ページは読めるまで保存ボタンを押せない（`disabled={!prefsReady}`）。読めない時の文は無い。区画の中の失敗の文は `error-message` `role="alert"`（保存の失敗だけ） | `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:161-170`・`:519`・`:619` |
| F11 | `useSeededForm` の `ready` は `data !== undefined` のときだけ真 | `frontend/src/lib/query/useSeededForm.ts:30` |
| F12 | 今ある文: `schedule.errorFetch`「予定の取得に失敗しました」・`schedule.prefsSaveError`。初期値を読めない文のキーは無い | `frontend/src/locales/ja.json:3410`・`:3591`（en の `prefsSaveError` は `:3409`） |
| F13 | 試験の置き場: `schedule-utils.test.ts`・`SchedulePageImpl.test.tsx`（初期値の擬似応答 `:54`・`:80`）・`ScheduleSettingsPage.test.tsx`（`:34`・`:57`・`:480`） | `frontend/src/pages/schedule/` |

## 3. 対象と対象外

- 対象: 小さい月カレンダーの曜日の見出しとマス（F1〜F4）・読み込み失敗の文（F7〜F10）
- 対象外: 大きい表（F5 は既に正しい）・API と DB・小さい月カレンダーの曜日名の言語（`"ja-JP"` 直書き `:551`、`formatMonthLabel(currentMonth, "ja-JP")` `:565`。今回は触らない。英語画面でも日本語の曜日が出るのは今と同じ）・便3b の審査で残した別の 2 点（大きすぎるチーム番号・権限が無い人の「誰の予定」）

## 4. 変更

### 4-1 週の始まり

1. `schedule-utils.ts:187-191` の `getMonthCells` に 2 つ目の引数 `weekStart: 0 | 1 = 0` を足す。始まりの日を `addDays(first, -((first.getDay() - weekStart + 7) % 7))` にする。マスは今と同じ 42 個。既定 0 なので、引数を渡さない呼び出しは今と同じ結果。
2. `ScheduleSidebar`（`SchedulePageImpl.tsx:525-545`）に `weekStart: 0 | 1` を足す。`getMonthCells(currentMonth, weekStart)` にする。曜日の見出しは `new Date(2024, 0, 7 + weekStart + index)` にする（2024-01-07 は日曜、+1 で月曜から）。
3. 呼び出し（`:1647-1657`）に `weekStart={prefs.week_start}` を足す。
4. 月の形の `viewDays`（`:1262`）も `getMonthCells(anchorDate, prefs.week_start)` にする。今は使われていないが、日曜固定の呼び出しを残さないため（F6）。見え方は変わらない。

### 4-2 読み込み失敗の文

1. 文を 2 つ足す（`ja.json`・`en.json` の `schedule` に同じキー）:
   - `schedule.prefsLoadError`: 「自分の初期値を読み込めませんでした。ページを開き直してください。」／ "Could not load your defaults. Please reopen the page."
   - `schedule.prefsLoadErrorSchedule`: 「自分の初期値を読み込めなかったため、標準の表示で開いています。」／ "Could not load your defaults, so the standard view is shown."
2. 設定ページ（`ScheduleSettingsPage.tsx`）: 初期値の区画の、保存の失敗の文（`:519`）の上に、`prefsQ.isError && !prefsReady` のとき `<div className="error-message" role="alert">{t("schedule.prefsLoadError")}</div>` を出す。同じ区画の今の文（`:519`）と同じ部品・同じクラス（新しい部品・色は作らない）。保存ボタンは今のまま押せない。
3. 予定ページ（`SchedulePageImpl.tsx:949`）: `useCalendarPreferences` から `query` も受け取る。`const prefsFailed = live && prefsQuery.isError && !prefsLoaded;` を作る。`shownError`（`:996`）を `error ?? (built.failed || staleFailed ? t("schedule.errorFetch") : prefsFailed ? t("schedule.prefsLoadErrorSchedule") : null)` にする。予定が取れない文の方を先に出す（予定の方が大事）。出す場所は今の `schedule-error` の枠（`:1678-1682`）。予定・形・人の選び方は今と同じく既定値で動く。
4. 見本の状態（`demoState`）のときは `live` が偽なので、2 は出ない（今の `live` の意味のまま）。

## 5. 受け入れ条件

| 基準 | 検証方法 |
|---|---|
| K1 `getMonthCells(new Date(2026, 10, 15), 1)` の 1 つ目が 2026-10-26（月曜）、42 個。`weekStart` 0 と引数なしは 1 つ目が 2026-11-01（日曜） | `schedule-utils.test.ts` に足す試験 |
| K2 初期値 `week_start: 1` の人: 小さい月カレンダーの曜日の見出しの 1 つ目が「月」、マスの 1 つ目が月曜の日付。初期値が行無し（既定）の人は 1 つ目が「日」 | `SchedulePageImpl.test.tsx` に足す試験（今の擬似応答 `:54`・`:80` を使う） |
| K3 設定ページで初期値の読み込みが失敗: 区画に `prefsLoadError` の文が `role="alert"` で出る。保存ボタンは押せない | `ScheduleSettingsPage.test.tsx` に足す試験 |
| K4 予定ページで初期値の読み込みだけが失敗: `prefsLoadErrorSchedule` の文が出る。予定は今と同じく出る。初期値が読めたときは出ない | `SchedulePageImpl.test.tsx` に足す試験 |
| K5 今ある試験がすべて通る。型・lint・i18n の点検が通る | CI（frontend の試験・型・lint・i18n キーの一致） |
| K6 本番: 配布された画面の JS に `prefsLoadErrorSchedule` の日本語の文が入っている | Opus が本番反映後に `https://app.salesanchor.jp/` の配布ファイルを読み込んで文を数える。日本語の生の文字と `\u` 形の両方で数え、合わせて 1 件以上 |

## 6. 代わりの案と選んだ理由

- 予定ページは何も出さない（設定ページだけ直す）案: 予定ページでは月曜始まりの人が日曜始まりで開いても理由が分からない。文 1 行なので出す。
- 共通の `common.fetchError`「取得に失敗しました」を使う案: 何が読めなかったか分からない。どちらのページも今は区画ごとの文を `schedule.*` に置いているので、それに合わせる。
- 新しい知らせの部品（`Callout`）を使う案: 同じ区画・同じページの今の失敗の文が `error-message`・`schedule-error` なので、それに合わせる。ページの中で失敗の見た目を 2 種類にしない。

## 7. 危険と対処

- `getMonthCells` の他の呼び出し: `SchedulePageImpl.tsx:548`・`:1262` の 2 か所だけ（`git grep -n getMonthCells origin/main -- frontend/src`）。既定 0 なので、引数を渡し忘れても今と同じ。
- 失敗の文が消えない: `shownError` は query の状態から作るので、読み直しで成功すれば消える。読み直しの契機は `useApiQuery` の既定に従う（未確認。設定ページの文は「開き直してください」なので実害は小さい）。
- 文の言葉: ja の文に `frontend/scripts/check-error-text-next-action.js:28` の `FAILURE` に当たる語を入れない（`check:error-text-next-action` の対象になり赤になる。審査1 L3）。
- 他の試験の擬似応答: `SchedulePageCache.test.tsx:69-76`（`:76`）は `/calendar/preferences` を「想定外の GET」で投げる。この便の後は失敗の文が出るので、初期値の応答を 1 行足す（審査1 R2）。
- 戻し方: この PR の revert だけ（DB・API なし）。

## 8. 維持する仕組み

- 試験 K1〜K4 が CI で毎回流れる。i18n の 2 キーの一致は CI の点検が見る。

## 9. 外部事例

- 不要。週の始まりは画面の中の並びの直しで、事例で決める点が無い。

## 10. 審査の記録

- 第1回（クラウド Sonnet・architect、2026-11-26）: REVISE。記録は `docs/handoff/schedule-settings/review-architect-bin3c-1.md`（枝 `release/schedule-settings-bin3c-review1`）。式・範囲・文・金型は正しい。必須の直し R1（試験の失敗の切替え・時計・取り方）・R2（`SchedulePageCache.test.tsx` の擬似応答）。
- 直し: R1・R2 はカードの変更3と触るファイルに入れた。L1・L2（行番号）・L4・L5（K6 の数え方）・L3 は §2・§5・§7 とカードに入れた。
- 第2回（クラウド Sonnet・architect、2026-11-26）: APPROVE。記録は `docs/handoff/schedule-settings/review-architect-bin3c-2.md`（枝 `release/schedule-settings-bin3c-review2`）。第1回の指摘は全部直っていた。軽い指摘 L1（月曜の人は待つ）・L2（K3 の取り方）・L3（Cache の試験の止め方）はカード変更3に入れた。L4 は行番号の付近で通じるため直さない。
- 状態: 設計審査済み（APPROVE）。
