# カード 便2.1: 予定の画面の升目を画面の下まで伸ばす（G10 の直し）

設計: `docs/handoff/schedule-gcal-clone/design.md` §2 G10・G13、§3.2「月の高さ」行。前の便: `docs/handoff/schedule-gcal-clone/card-bin2.md`（#5232・本番反映 2026-11-07 08:17 JST）。
成功条件の PO 承認: 2026-11-06（「1.」）。この便は承認済みの G10 を満たすための直しで、成功条件は変えない。

## 枝と作業場所
- 枝 `release/schedule-fill-height-v2`（Opus が `origin/main` から作成済み・このカードを載せて push 済み）。この枝を checkout して作業する。

## 実物で確かめた事実（2026-11-07 08:2x JST・Opus・本番 https://app.salesanchor.jp/schedule・窓の高さ 1448）
- 月の表示の升目の下端は 636px（窓 1448）。G10「升目が画面の下まで届く」は不合格。週の表示も高さ 541px で、見えるのは約 4.8 時間分、下に約 800px の空き。
- 1 時間の高さ 96px・目盛りは 0 時から 23 時までの 24 本・開いた位置は 7 時（scrollTop 673）は合格。
- 高さの元をたどった値（画面の要素を内側から外側へ）:
  - `.fc` 541 → `.comp-calendar--fill` 541 → `.schedule-calendar` 541（flex: 1）→ `.schedule-main__surface` 575（flex: 1）→ `main.schedule-main` 575 → `.schedule-shell__content` 575（display: grid・flex: 1）→ `.page-layout-content--no-scroll` **1370（display: block）** → `.page-layout` 1448。
  - 原因: `.schedule-shell__content` の親 `.page-layout-content`（`frontend/src/components/PageLayout.tsx:55`・`frontend/src/pages-layout.css:89-96,105-109`）は flex の箱ではない（display: block）。そのため `frontend/src/pages/schedule.css:97` の `flex: 1` は効かず、高さが中身の高さ（575px）で止まる。`:97` の注記「.schedule-page flex column」は今の並びと合わない。
- 直しの試し（Opus がこのタブにだけ一時的に style を差し込み、確かめた後に消した。本番は変えていない）: `@media (min-width:1024px){.schedule-shell__content{height:100%}}` で、月の下端 1431・5 段の高さ 260〜263px、週の下端 1431・時間割の見える高さ 1261px・1 時間 96px のまま、`.page-layout-content` のはみ出し 0。

## 1. 触るファイルと触らないファイル
- 触る: `frontend/src/pages/schedule.css` の 1 か所だけ（下の 2）。
- 触らない: `frontend/src/pages-layout.css`・`frontend/src/components/PageLayout.tsx`（ほかの画面も使う共通の枠。変えると受信箱など他の画面の高さが変わる）、`frontend/src/components/CalendarView.*`、`frontend/src/tokens.css`、`SchedulePageImpl.tsx`、裏側すべて。

## 2. schedule.css の変更（`frontend/src/pages/schedule.css:92-100` の直後に足す）

変更前（`:92-100`・そのまま残す。`:97` の注記だけ下のように直す）:
```css
  flex: 1;        /* consume remaining height in .schedule-page flex column */
```
変更後の `:97`:
```css
  flex: 1;        /* the parent .page-layout-content is display:block, so height comes from the rule below */
```

`:100` の `}` の直後に足す（空行 1 つを挟む）:
```css
/* 幅 1024px 以上: 親 .page-layout-content（display:block・高さ確定）いっぱいに伸ばし、升目を画面の下まで届かせる（G10・G13）。
   1023px 以下は今のまま（1 列に並ぶため 100% にすると左の欄が高さを取り、升目が隠れる） */
@media (min-width: 1024px) {
  .schedule-shell__content {
    height: 100%;
  }
}
```
- 数値・色は足さない（`100%` と既存の区切り幅 1024px だけ。1023px の既存の @media `:1097` と対）。
- 新しいトークンは作らない。

## 3. 試験
- jsdom は高さを測れないので、画面の試験は足さない。今の試験が通ることだけ確かめる。

## 4. 確かめるコマンド（クラウドで実行し、生の出力をファイルに残す）
```
cd frontend
npm ci
npx vitest run src/pages/schedule src/components/CalendarView > /tmp/vitest.txt 2>&1; echo exit=$?
npm run check:all > /tmp/checkall.txt 2>&1; echo exit=$?
npm run build > /tmp/build.txt 2>&1; echo exit=$?
git diff --stat origin/main...HEAD
```
- 期待: vitest 全件合格・check:all エラー 0・build 合格・diff は `frontend/src/pages/schedule.css` と本カード・台帳だけ。

## 5. 受入れ（本番反映後に Opus が画面で確かめる・窓の高さ 1448）
|基準|検証方法|
|---|---|
| 月の表示の升目の下端が窓の下から 40px 以内 | 本番で `.fc` の下端を測る（今は 636 → 1400 以上） |
| 週の表示の時間割の見える高さが 1000px 以上・1 時間 96px のまま | `.fc-scroller` の最後の clientHeight と `.fc-timegrid-slot-lane` の高さを測る |
| 画面全体に縦のはみ出しが出ない | `.page-layout-content` の scrollHeight − clientHeight が 0 |
| 幅 1023px 以下の見た目が変わらない | 窓を幅 900 にして、直す前と同じく左の欄の下に升目が出ることを見る |

## 6. 想定される分かれ道（出たら止める）
- `check:all` が `@media (min-width: 1024px)` の書き方で止める → 止めて Opus に報告（勝手に別の書き方にしない）。
- `:92-100` の中身が上と違う（main が動いた）→ 止めて報告。
- 試験が赤 → 直さずに止めて報告。

## 7. 審査の記録
- 実装（クラウド Sonnet・2026-11-07 08:42 JST・bd8b7ccd4）: 差分は `schedule.css` の 9 行追加・1 行削除で、§2 の文と一字一句同じ（Opus が `git diff origin/main...origin/release/schedule-fill-height-v2` で確認）。
- 検証（クラウド Sonnet 実行）: vitest `Tests 129 passed (129)`・`Test Files 4 passed (6)`。残り 2 ファイルはブラウザ型の試験で、クラウドに chromium が無く起動できなかった（エラーは `Executable doesn't exist` の 1 種だけ）。この 2 ファイルは CI で流れるので、Opus の判断で先へ進めた。check:all は終了コード 0（0 errors・59 warnings。いずれも既存の警告）。build は終了コード 0。push 前の入口の検査で落ちた検査は 0 件。
- §6 の分かれ道: 1 回目の実行は vitest の終了コード 1 で止まった（上の chromium の件）。カードの規則どおりで、変更は無かった。
- 設計の審査: 変更は 1 ファイルの CSS 1 規則で、本番の画面で同じ規則を差し込んで測っている（「実物で確かめた事実」の最後の項）。そのためクラウドの別審査は回さず、マージ前の Reviewer（Opus）の審査で兼ねる。
