# 予定の時間割・月の升目の金型（CalendarView）— recon

調べた版: salesanchor origin/main 170affc4d（2026-11-06）、agent-console origin/main 412717f（2026-11-06）。
調べた人: Opus（手元で読み取りのみ）。Context7 は月の上限で使えなかった（`Monthly quota exceeded`）ため、起動指示の代替どおり公式頁と npm・GitHub の記録を直接見た。

## 1 きっかけ（PO の決定）
- agent-console の予定画面の設計（GEN-RYU-System/agent-console PR #92、docs/handoff/schedule-board/design.md §14 D4・§15-1）で、時間割・月の升目・点線の決まりが金型に無いと分かった。
- 2026-11-06 PO「1」：問い「FullCalendar を包んだ部品を部品集に登録して、予定画面に使う【おすすめ】」への答え。
- agent-console の成功条件（１）（５）（８）（９）は PO 承認済み（2026-10-30）。この金型はその画面の部品になる。

## 2 既存 ADR の検索
- `git grep -i -l fullcalendar -- docs/adr` → 0 件。
- docs/adr/FEATURE-INDEX.md:34 のカレンダーの行は Google 連携（ADR-1057・1059・1060・1018）で、画面の部品の決まりではない。
- 守る決まり: ADR-067（トークン強制）、ADR-073（部品ごとの stories）、ADR-144（金型の登録）、ADR-027（文言は t()）。
- 部品の決まり: docs/CC_UI_GOVERNANCE.md:9-15（金型が無ければ PO 許可を得て components/ に Xxx.tsx・Xxx.css（var() のみ）・Xxx.stories.tsx で登録）。

## 3 部品の今
- frontend/package.json:73-77 に @fullcalendar/core・daygrid・interaction・react・timegrid が `^6.1.20`。package-lock.json の解決は 6.1.20（package-lock.json:1335-1337）。
- frontend/src の中で fullcalendar を読む所は 0 件（`grep -rln fullcalendar frontend/src` が空）。
- 予定ページの時間割と月の升目は pages/schedule/SchedulePageImpl.tsx の中だけ（agent-console design.md §15-1 で照合済み。:568 週・:732 月、外に出していない）。この金型ではページに手を入れない。

## 4 FullCalendar の版（公式頁・npm・GitHub、2026-11-06 に確認）
- npm の dist-tags: `latest` 7.1.4、`legacy` 6.1.22（`npm view @fullcalendar/core dist-tags`）。
- 6 系は手入れが続いている: 6.1.21（2026-06-18）、6.1.22（2026-10-16）（`npm view @fullcalendar/core time`）。
- 6.1.22 の直し（GitHub release v6.1.22）: React で `datesSet` が state を変えると「Maximum update depth exceeded」になる不具合（#7069）、`eventDisplay:'block'` で長い題名が時刻を隠す不具合（#6457）、CSP で inline style が止められると落ちる不具合（#7353。いまは警告に変わった）。
- @fullcalendar/react@6.1.20 の peerDependencies: react `^16.7.0 || ^17 || ^18 || ^19`、@fullcalendar/core `~6.1.20`。license MIT。
- 公式の v6 の頁は legacy.fullcalendar.io へ移り、頭に「FullCalendar v6 documentation, for an old release.」とある。
- v6 の CSS の変え方（legacy.fullcalendar.io/v6/css-customization）: 根のセレクタに `--fc-*` の変数を置く。変数の一覧は頁に無く、各パッケージの src/styles/vars.css を見るように書かれている。
- v7 は見た目の仕組みが変わる: `--fc-*` の多くが `--fc-classic-*` などテーマごとの名前になり、`eventClass` などの class 名の設定で見た目を当てる（fullcalendar.io/docs/upgrading-from-v6-css.md）。CSS は skeleton.css・テーマ・パレットを読み込む例になっている（fullcalendar.io/docs/color-palettes.md）。
- 10/30 の動かした比較（agent-console design.md §15-1 の表）は 6.1.20 で行った。v7 では行っていない。

## 5 見た目の決まり（トークン）
- 時間割のトークン: frontend/src/tokens.css の「Schedule page」の段（`--schedule-row-height` 48px「1時間の高さ（標準）」、`--schedule-time-gutter-width` 60px、`--schedule-now-line`、`--schedule-gridline`、`--schedule-event-radius` 6px、`--schedule-month-cell-min-h`、`--schedule-day-min-w`、`--schedule-hour-bg`、`--schedule-hour-label`、`--schedule-today`、`--schedule-slot-hover`）。
- 種類の色: tokens.css:424-430（`--cal-personal`・`--cal-meeting`・`--cal-purchase`・`--cal-shipping`・`--cal-billing`・`--cal-release`・`--cal-holiday`、それぞれ `-tint`・`-text` つき）。暗い画面の値は tokens.css:637-643。
- 面と文字: index.css:18 `--bg-surface`、:20 `--bg-hover`、:24 `--text-primary`、:26 `--text-muted`、:29 `--border`、:34 `--accent`、:52 `--danger`。暗い画面の値は index.css:226 以降。
- 影: index.css:69-77（`--shadow-xs`〜`--shadow-dropdown`）、暗い画面は :262-270。
- 点線（dashed）の線の種類と、線の太さのトークンは無い（`grep -n "dashed\|border-w" tokens.css index.css` で 0 件）。
- CSS の検査: frontend/scripts/check-css-hardcoded-colors.js（色の直書き）、check-css-hardcoded-values.js（opacity・border-radius・z-index・animation の数の直書き。tokens.css・index.css は対象外）、check-dark-parity.js（index.css の明暗の変数の一致）、check-stories-count.js（components/*.tsx に .stories.tsx が要る）。

## 6 文言
- 金型の文言は react-i18next の `t()`（例 components/NoticeBell.tsx:157）。辞書は frontend/src/locales/ja.json・en.json。
- agent-console は SA の ja.json を取り込んで自分の辞書と重ねる（agent-console src/i18n.ts:3,19）。SA に足したキーはそのまま agent-console でも引ける。

## 7 agent-console での使われ方
- `@sa` は salesanchor origin/main の frontend/src の写し（agent-console scripts/sa-sync.mjs: `git archive origin/main frontend/src` を .sa-cache/ へ展開）。写すのは frontend/src だけで、node_modules・package.json は写さない。
- agent-console の package.json に @fullcalendar は無い（origin/main package.json）。金型が @fullcalendar を読むと、agent-console 側にも同じ版の依存が要る。lucide-react など他の金型の依存と同じ扱い（agent-console 側で版を固定して入れる）。
- agent-console の見た目の検査（scripts/check-design-governance.mjs）は自分の src/ と extension/ だけを見る。.sa-cache は見ない。

## 8 CSP（inline style）
- FullCalendar v6 は実行時に `<style>` を差し込む（6.1.22 の release に「styles must be provided another way, or upgrade to v7」）。
- salesanchor: nginx/nginx.conf:96・:320 とも `style-src 'self' 'unsafe-inline'`。
- agent-console: server/http.ts:729 `style-src 'self' 'unsafe-inline'`（理由は :724 の xterm）。
- どちらも今の設定で差し込みは止められない。

## 9 時刻の扱い
- FullCalendar で `timeZone` に地名（例 Asia/Tokyo）を使うには別の部品（luxon などの plugin）が要る。既定の `local` は動かしている機械の時刻。agent-console は PO の Mac で動き、Mac は日本時間。
- 10/30 の比較は Asia/Tokyo の機械で行った（agent-console design.md §15-1）。
