VERDICT: APPROVE

# 設計審査 2（architect）schedule-settings 便3c

- 対象: `docs/handoff/schedule-settings/design-bin3c.md`（91 行）・`card-bin3c.md`（92 行）。枝 `release/schedule-settings-bin3c` = 894ff2e9e（確認済み）
- 実物の基準: origin/main 331c18613（`git rev-parse origin/main` で確認）。製品コードは変えていない。本番には繋いでいない。
- 第1回の記録: `review-architect-bin3c-1.md`（枝 `release/schedule-settings-bin3c-review1`）

## 結論

第1回の R1・R2・L1〜L6 は全部直っている。必須の直し（R）は無い。カード変更3の試験の作り方は実物に合い、そのまま動く見込み（実行はしていない → 未確認）。軽い指摘（L）が 4 つあり、実装役が迷わないための補足。直さなくても APPROVE。

## 1. 第1回の指摘の照合

| 指摘 | 結果 | 実物の行 |
|---|---|---|
| R1 失敗の切替え | 直っている | カード :56。`answers` に `prefsFail: false as boolean`。`SchedulePageImpl.test.tsx:80-83` と `ScheduleSettingsPage.test.tsx:57-60` は実物でも `/calendar/preferences` の枝（if :80／:57、return :82／:59）。先頭で投げれば `await answers.gate.prefs`（Impl :81）より前で効く |
| R1 beforeEach の戻し | 直っている | Impl `beforeEach` は :120（`answers.prefs = null;` は :134）、Settings は :88（`answers.prefsPending = false;` は :99）。カードの「:119 付近」「:88 付近」は付近で通じる（L4） |
| R1 時計・今日から作る期待値 | 直っている | カード :57。`useFakeTimers`・`setSystemTime` は両ファイルに無い（grep 0 件）。`new Date(y, m, 1)` から `(getDay()+6)%7`／`getDay()` 日戻す式は、設計 §4-1 の式と同じ。小さい月は `currentMonth = startOfMonth(anchorDate)`（`SchedulePageImpl.tsx:1002`）で今月を指す |
| R1 取り方の class | 直っている | `.schedule-mini-calendar__weekdays span`（`SchedulePageImpl.tsx:588-589`）・`.schedule-mini-calendar__day`（:599）。ほかの場所に同じ class は無い（`grep` で :588・:599 の 2 か所だけ）。マスの中身は `date.getDate()` だけ（:608）なので `textContent` が日付の数字になる |
| R1 見出しの言語 | 直っている | カード :57。見出しは `Intl "ja-JP"`（:551）で作る。「月」「日」で正しい |
| R2 Cache の擬似応答 | 直っている | カード :60。実物の `/calendar/owners` の行は `SchedulePageCache.test.tsx:73`、`Unexpected GET` は :76。:73 の前に足せば、`/me/permissions`（:69）・`isScheduleRead`（:70-71）の後・`owners`（:73）の前になり、順序に問題なし。`/calendar/preferences` は `isScheduleRead`（:64-65）に入っていないので `hang`・`fail` の切替えの影響を受けない。触るファイル一覧にも :16 で追加済み |
| L1 行番号 | 直っている | 設計 F3 `:549-552`・§3 `:551`・F4 `:525-545`・F5 `:196-201`・F9 `:55-61`（実物と一致） |
| L2 | 直っている | F12 に en の `prefsSaveError` は :3409 と書いてある |
| L3 | 直っている | カード :49・設計 §7 に `check-error-text-next-action.js:28` の語を入れない旨 |
| L4 | 直っている | 設計 §7 に「読み直しの契機は未確認」と明記 |
| L5 | 直っている | 設計 §5 K6 に日本語の生の文字と `\u` 形の両方で数える |
| L6 | 直っている | 設計 §10 に第1回の記録と直しを書いてある（§10 :90-91） |

## 2. カード変更3 が実物で動くか

- K1（schedule-utils.test.ts）: 2026-11-15 基準で weekStart 1 → 2026-10-26、0・引数なし → 2026-11-01。第1回で node 実測済み（全 60 か月 × 0/1 で違反 0）。変更なし。
- 失敗の切替え: 擬似応答は `api.get` の `vi.fn(async ...)`。throw は reject になり、`useApiQuery` は `retry: 0`（`apiQuery.ts` の `QueryClient` 既定）なので 1 回で `isError`。`afterEach` が `queryClient.clear()`（Impl :149・Settings の afterEach）を流すので、前の試験の成功した写しは残らない。切替えを戻す `beforeEach` と合わせて、次の試験に漏れない。
- K3: 保存ボタンの取り方は既存の `saveButton()`（`ScheduleSettingsPage.test.tsx:485` で使用）がある。`role="alert"` はほかに :682 の `categoryError` があるが、これは種類の保存失敗のときだけで、K3 の状態では出ない。
- K4: 予定ページは `prefsFail=true` の間も `/calendar/events` などは `answers.events` を返すので、予定は出る。`errorFetch` が先に勝つ式（設計 §4-2 の 3）なので、予定の読みが成功している限り `prefsLoadErrorSchedule` が出る。
- 他のファイル: `batch3bPages.test.tsx:76` は設定ページを描くが、擬似応答は未登録 path に `[]` を返す（:91 の `answer`）ので `/calendar/preferences` は成功扱い（空配列）で、新しい文は出ない。`i18n` も `t(key)=key` の擬似なので文の確認には影響しない。そのほかのファイル（`editorVariantUsage.test.ts`・`gcalColorsUsage.test.ts`）は文字列の検査だけ。

## 3. 必須の直し（R）

なし。

## 4. 軽い指摘（L）

- **L1（カード 変更3・K2）**: `week_start: 1` の人の確認は、初期値が非同期で届くまで 1 つ目が「日」のまま。`waitFor` で待つこと、と 1 行足すと迷わない。実物の同種の試験 `SchedulePageImpl.test.tsx:2110-2113`（B1）が `answers.prefs = { ...DEFAULT_PREFS, week_start: 1 }` ＋ `waitFor` の形で、これに合わせればよい。既定（行無し）の人は待たずに通るので、待つのは月曜の人だけ。
- **L2（カード 変更3・K3）**: 保存ボタンは既存の `saveButton()`（`ScheduleSettingsPage.test.tsx:485`）、文の確認は `screen.findByText(i18n.t("schedule.prefsLoadError"))`（:476 と同じ書き方）を使う、と書くと迷わない。`getByRole("alert")` は別の失敗の文が出る状態で複数一致し得るため。
- **L3（カード 変更3・Cache）**: 初期値の応答を足すと、`SchedulePageCache.test.tsx` の全試験で初めて `prefsLoaded` が真になる（今は :76 で投げるため常に偽）。`SchedulePageImpl.tsx:1023`（初期の形の適用）・`:1034-1054`（人の初期の選び方）の副作用が走る。応答は `default_view: "week"`・`open_owners: "self"` で今の既定と同じなので、読み回数の確認（`readsOf` が :112・:131・:161 で 1 や 0 を数える）は変わらない見込み（実行していない → 未確認）。カード :62 の BLOCKED の条件は「ほかのファイル」向けなので、「Cache の試験が足した行で落ちたら、その試験名で BLOCKED:」と 1 行足すと実装が迷わない。
- **L4（カード :56）**: Impl の `beforeEach` は :120（「:119 付近」で通じる）。実装の邪魔にはならない。

## 5. 新しい問題の探索

- 見つからなかった（R なし）。`getMonthCells` の呼び出しは第1回の確認どおり 2 か所（`SchedulePageImpl.tsx:548`・`:1262`）。`ScheduleSettingsPage.tsx` は 760 行（上限 800）で足すのは数行。
- 未確認: `frontend/node_modules` がこの場所に無いため、vitest・tsc・eslint・`check:error-text-next-action` を実行していない。設計・カードの動作は実物の行の読み取りだけの確認。

## 6. 確認した事実

- 枝 894ff2e9e は abe07dbab の次の 1 commit（`git log --oneline` で確認）。差分は設計とカードの 2 ファイルのみ（`git diff --stat abe07dbab 894ff2e9e`）。
- 試験ファイルの行は origin/main 331c18613 の内容を、この枝の作業場所（main に対して docs だけの差分）で読んだ。
