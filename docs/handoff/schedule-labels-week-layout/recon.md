# recon: 予定の画面の表示崩れ 3 件（2026-11-04）

PO 依頼（原文）: 「おそらく連携していると判断できるがスケジュールページがコードがそのまま出ていて内容が分からない、修正できる？ヘッダーの曜日と日付も折れてしまっている」
PO の画面写し: 週表示（11/1〜11/7）。予定の箱に `schedule.calendarLabels.mee…` と時刻だけが出て、題名が出ない。見出しは日〜金の 6 列で、土曜が 2 段目に落ちる。

土台: origin/main f75ab3cb9（worktree `release/schedule-labels-week-layout`）。

## 既存 ADR の検索

- `git grep -l -i -E "schedule|calendar" origin/main -- docs/adr/` → ADR-035, ADR-067, ADR-1018, ADR-1056, ADR-1057, ADR-1059 ほか
- `docs/adr/FEATURE-INDEX.md:34` カレンダー / 予定 → ADR-1057 ／ ADR-1018（Google との接続の決まり。表示の形は決めていない）
- 関係する決まり: ADR-027（画面の文字はすべて t() と ja/en 同じキー）、ADR-067（色はデザイントークン）、ADR-144（UI 部品は金型）
- 表示崩れ 3 件を決めた ADR・それに反する ADR は見つからなかった

## 【事実】1. 種類の言葉が出ず、キー名がそのまま出る

- `frontend/src/features/schedule/calendars.config.ts:26,34,42,50,58,66,74` 各種類の `labelKey: "schedule.calendarLabels.<id>"`（meeting / personal / procurement / shipping / billing / release / holiday の 7 個）
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:731-739` 週表示の予定の箱が `t(meta.labelKey)` を種類の札として出す（月表示・吹き出しも同じ札を使う）
- `frontend/src/locales/ja.json:3086` `schedule` の中に `calendarLabels` が無い。en.json も同じ（python で `d['schedule'].get('calendarLabels')` → None）
- 経緯: 7bcc80e62（#2413「スケジュール #4 calendarLabels i18n追加」）で ja/en に 7 個を入れた。bc62ed626「foundation f2 country control」（2026-06-21・国の入力の作業）が ja.json・en.json を 204 行ずつ書き換えたとき、`calendarLabels` の 7 個を消した（`git show bc62ed626 -- frontend/src/locales/ja.json` の 240-248 行目が `-` 行）。予定の画面とは関係のない作業での消えすぎ
- 消える前の値（`git show 7bcc80e62:frontend/src/locales/{ja,en}.json`）:

| id | ja | en |
|---|---|---|
| personal | 個人（担当者） | Personal |
| meeting | 商談・打合せ | Meetings |
| procurement | 仕入・入荷 | Purchasing / Inbound |
| shipping | 発送予定 / 集荷 | Shipping / Pickup |
| billing | 請求・入金期限 | Billing / Payments |
| release | 新商品の発売日 | New Releases |
| holiday | 日本の祝日 | Japan Holidays |

- なぜ機械が気づかなかったか: `frontend/scripts/check-i18n-missing-keys.js:32` の点検は `t("…")` と文字が直に書かれた呼び出ししか見ない。`labelKey: "…"` のように設定の表に置いたキーは見ない

## 【事実】2. 予定の箱に題名が出ない

- 題名のデータは届いている: 本番 DB（読み取り専用の道）`tenant_004.calendar_events` は app 9 行・google 7 行、題名が空の行 0（前回の確かめ）。裏側は `backend/app/services/calendar_service.py:134,156` で `title` をそのまま返し、画面は `frontend/src/pages/schedule/schedule-utils.ts:167` で `title: event.title` に写す
- 箱の作り: `frontend/src/pages/schedule/SchedulePageImpl.tsx:731` 題名 → `:732-739` 種類の札 → `:740-742` 時刻 の順に縦に並ぶ
- 箱の高さ: 1 時間 = `DEFAULT_ROW_HEIGHT = 48`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:88`）
- `frontend/src/pages/schedule.css:530-542` `.schedule-event` は縦並び・`overflow: hidden`
- `frontend/src/pages/schedule.css:553-561` `.schedule-event__title` は `overflow: hidden`。縦並びの中で `overflow: hidden` の子は「中身の高さより小さく縮んでよい」扱いになる
- `frontend/src/pages/schedule.css:715-723` 種類の札は `min-height: 1.5rem`（24px）で縮まない
- 中身の合計（上下の余白 4+4・題名 15・間 2・札 24・間 2・時刻 16.5 ≒ 67.5px）が 48px を超えるため、縮んでよい題名だけが高さ 0 まで縮む
- 実測（Playwright、同じ CSS の見本を about:blank に置いて高さを測った）: 今の CSS で題名の高さ **0**・札 24・時刻 16.5。題名に `flex-shrink: 0` を足すと題名の高さ **15**

## 【事実】3. 週の見出しと列が 6 列で折れる

- `frontend/src/pages/schedule.css:15` `--schedule-day-min-w: 10rem`（160px）
- `frontend/src/pages/schedule.css:476-480` `.schedule-grid__days { grid-template-columns: repeat(auto-fit, minmax(var(--schedule-day-min-w), 1fr)); }` 1 列 160px 未満になると次の段へ折り返す
- 同じ組み方を見出し（`frontend/src/pages/schedule/SchedulePageImpl.tsx:627`）・終日の行（`:647`）・本体（`:688`）の 3 か所が使う
- PO の画面では日〜金の 6 列で横幅が尽き、土曜が 2 段目へ落ちる（画面写し）
- 日表示も同じ部品（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1242` `ScheduleWeekGrid days={viewDays}`）で、1 日だけ渡す
- 狭い画面用: `frontend/src/pages/schedule.css:1270-1272`（1023px 以下）は 2 列、`:1288-1290`（767px 以下）は 1 列。これは今回の依頼の外

## 【事実】4. 色の直書き（今回は直さない）

- `frontend/src/features/schedule/calendars.config.ts:27-29` ほか 7 種類 × 3 色が `#1a73e8` などの直書き。これは既に `docs/specs/design-system/design.md:66-68` と `docs/handoff/color-tokens-ssot/recon.md:575-576,636-638` で「トークンへ移す対象」として数えられている既知の残件
- 今回の 3 件とは別の作業として扱う（変更は一度に 1 テーマ）

## 【未確認】

- 本番の画面での見え方の直し後の姿（反映後に PO の画面で確かめる）
