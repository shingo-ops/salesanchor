# 実装カード: 金型 CalendarView（FullCalendar 6.1.22 を包む）

- 設計: [design.md](design.md)（Opus 自己審査 APPROVE）。調査: [recon.md](recon.md)。決定: ADR-1065。
- PO の実装承認: 2026-11-06「1」（FullCalendar を包んだ部品を部品集に登録して予定画面に使う）。
- ブランチ: `release/calendar-component`（このブランチに積む。新しいブランチは作らない）。区分 B-1（危険パスなし）。
- 試験は Mac で流さない。CI で確かめる。

## やること（この順）
1. frontend/package.json:73-77 の @fullcalendar/core・daygrid・interaction・react・timegrid を `"6.1.22"`（`^` なし）にする。`cd frontend && npm install` で package-lock.json を更新する。lock の5つが 6.1.22 になったことを `grep -n '"node_modules/@fullcalendar' -A1 package-lock.json` で示す。
2. 6.1.22 の変数を数える: `grep -rhoE -- '--fc-[a-z0-9-]+' node_modules/@fullcalendar/{core,daygrid,timegrid}/*.js node_modules/@fullcalendar/{core,daygrid,timegrid}/internal*.js | sort -u` の生の結果を PR 本文に貼る。変数を通らない直書きの色を `grep -noE 'rgba?\([^)]*\)|#[0-9a-fA-F]{3,8}\b' 同じファイル` で拾い、出どころの class と一緒に PR 本文の表にする。
3. frontend/src/tokens.css の「Schedule page」の段に design §4-4 の3行を足す（値・コメントもそのまま）。
4. frontend/src/components/calendarView.utils.ts を作る: `computeHourRange`（design §4-5）・`eventClassNames`（§4-6）・型（§4-2）。FullCalendar を import しない。
5. frontend/src/components/CalendarView.tsx を作る: design §4-2 の props、§4-3 の表どおりの値。`moreLinkClick` と `showNonCurrentDates` は design §4-3-1 のとおりにする（公式頁と 6.1.22 の実物は Opus が確かめ済み。クラウドから公式頁は読めないので読みに行かない）。
6. frontend/src/components/CalendarView.css を作る: design §4-7。`--fc-*` は手順2で数えた全部を `.comp-calendar` に置く。値は var() だけ。px・#・rgb の直書きをしない。
7. frontend/src/locales/ja.json・en.json に design §4-8 の2キーを足す。
8. frontend/src/components/CalendarView.stories.tsx を作る: design §4-9 の7つ。形は components/Badge.stories.tsx に合わせる（`title: 'Components/CalendarView'`・`tags: ['autodocs']`・`@storybook/react-vite`）。
9. frontend/src/components/CalendarView.test.tsx を作る: design §7 の T1〜T5。
10. 提出前: `bash scripts/dev/check-before-submit.sh` を流し、生の結果をファイルに残してパスを報告する。frontend の `npm run lint`・`npm run check:css-colors`・`npm run check:css-values`・`npm run check:stories`・`npm run check:dark-parity`・`npx tsc --noEmit` が package.json にあれば流す（無い名前は無いと書く）。vitest は流さず CI に任せる。
11. commit（1つでよい）→ push。PR は作らない（Opus が作る）。

## 触らない
- pages/schedule/ 以下・ほかの components・index.css・nginx・backend・migrations・.github・scripts。
- 上の「やること」に無いファイル。要りそうなら止めて `NEEDS_DECISION:` で報告する。

## 想定される分かれ道
- npm install で @fullcalendar 以外の版が lock で動いた → その差分を PR 本文に全部書く。@fullcalendar 以外の package.json は変えない。
- `--fc-*` の数が 6.1.20（core 27・daygrid 6・timegrid 11）と違う → 6.1.22 の実物に合わせる。違いを PR 本文に書く。
- 1時間の高さの calc が既存の CSS 検査で止められる → 検査の文を貼って止める。検査を変えない。
- `@fullcalendar/core/locales/ja` が型で読めない → 止めて報告する。

## 終わりの報告
- 最後の行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 問い`。HEAD の sha・変更ファイル一覧（`git diff --name-only origin/main...HEAD`）・各検査の終了コードを付ける。
