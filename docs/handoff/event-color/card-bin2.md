# 実装カード 予定ごとの色 便2 — 画面（色を選ぶ部品・色のトークン・予定の箱の色）

> この文書は何か：予定ごとの色（Google と同じ 24 色＋デフォルト）の便2 の作業指示書です。色のトークンを登録し、色を選ぶ新しい金型を作り、予定の作成と編集の画面に色の欄を足し、週・月の箱と一覧の丸に選んだ色を出します。裏側（色の欄・受け口・Google との行き来）は便1 で本番に入っており、この便では触りません。

- 設計: docs/handoff/event-color/design.md §4-7〜§4-9（便2 の前に origin/main 5db804b78 で確かめ直し、§4-8 と §4-9 を直した版）
- 現状の調べ: docs/handoff/event-color/recon.md
- 対象ADR: ADR-1081（本テーマ）、ADR-144（金型）、ADR-067（デザイントークン）、ADR-027（画面の文字）、ADR-1074（予定の画面の金型と `--gcal-*`）、ADR-1075（繰り返し）
- 状態: 設計審査済み（便1 と同じ設計の 2 回目 APPROVE）。便2 の直しは Opus が実物で確かめた。実装に進むのは 2026-11-20 の PO の「1. 色を選ぶ画面づくりに進む」による。本番に入れる前に PO にもう一度聞く約束がある
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当は PR を作るまで。マージしない
- 担当: 実装 Sonnet（クラウド）／審査・PO への確認・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（画面で色を選んで見せるだけ。裏側は便1 で済み） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に変更前後のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 は試験名を出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行番号はすべて origin/main 5db804b78 で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 予定ごとの色 便2 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 色のトークン（`frontend/src/index.css` の明るい画面と暗い画面に 24 個ずつ、`frontend/src/tokens.css` に意味のトークン 24 個）
2. トークンと裏側の値の一致の試験 `backend/tests/test_event_colors_tokens.py`（新規）
3. 予定の色の一覧 `frontend/src/pages/schedule/eventColors.ts`（新規）とその試験
4. 新しい金型 `ColorSwatchPicker`（.tsx・.css・.stories.tsx・.test.tsx）と、金型の目録への 1 行
5. 予定の画面: 下書き・保存・色の欄・箱と一覧の丸の色・仮の箱の色・欄の絵
6. 画面の文字（ja・en）
7. 試験（§4-10）

入れない:
- `backend/app/` と `migrations/` のすべて（便1 で済み）
- 持ち主の色の仕組みと設定の画面
- `frontend/src/components/CalendarView.tsx`・`CalendarView.css`（箱の描き方はそのまま。色の値を渡すだけ）
- 秘書のチャットの予定の下書き（`frontend/src/features/secretary/`）。色なしのまま
- スマホ幅の予定の画面（Android 側の担当）
- 色の一覧だけを閉じる Esc（窓ごと閉じる今の動きのまま）

## 2. 前提の事実（origin/main 5db804b78）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 裏側の正本は 24 色の鍵と値。並びは設計 §4-1 の表 | `backend/app/services/event_colors.py`（便1 で本番済み） |
| F2 | 一覧の返しに `color_key` が入る。受け口は 24 の鍵か `""`（デフォルトに戻す）を受け、送らなければ変えない | `backend/app/services/calendar_service.py`・`backend/app/routers/calendar.py`（便1） |
| F3 | `index.css` の明るい画面は `:9`〜`:222`、`--gcal-now` は `:206`。暗い画面は `:233`〜`:437`、`--gcal-now` は `:422` | `frontend/src/index.css` |
| F4 | `tokens.css` の `:root` の終わりの `}` は `:645` | `frontend/src/tokens.css` |
| F5 | `--gcal-` を書いてよいのは `index.css`・`tokens.css` だけ | `frontend/src/components/gcalColorsUsage.test.ts` |
| F6 | `RadioControl` は本物のラジオ 1 つを返す。`className`・`style`・`type`・`role` は受けない | `frontend/src/components/RadioControl.tsx:12`〜`:16` |
| F7 | 色見本は `RadioControl` を使う決まり | `docs/CC_UI_GOVERNANCE.md`・`docs/specs/design-system/design.md:4262` |
| F8 | 今ある色見本の手本（`label` の地に色・中に見えないラジオ） | `frontend/src/pages/roles/RolesPage.tsx:497`〜`:528`・`frontend/src/pages-layout.css:271`〜`:315` |
| F9 | `Button` は `className`・`style` を受けない。`aria-expanded` などはそのまま渡る | `frontend/src/components/Button.tsx:41`・`:59`〜`:68` |
| F10 | `Popover` は体の直下に出し重なりの順は `var(--z-dropdown)`。予定の窓と編集の画面は `var(--z-modal)` で上。予定を作る窓は外を押すと閉じる | `frontend/src/components/Popover.css:201`・`frontend/src/pages/schedule.css:344`・`frontend/src/components/EditorPage.css:10`・`frontend/src/pages/schedule/SchedulePageImpl.tsx:297`〜`:309` |
| F11 | 下書きの形 `ScheduleDraft` は `:89`〜`:103`。作る場所は `createDraft`（`:142`〜`:160`）・`:962`〜`:977`・`:1204`〜`:1213` | `frontend/src/pages/schedule/SchedulePageImpl.tsx` |
| F12 | 保存の中身は `saveEvent`（`:1010`〜）の `body`（`:1012`〜`:1020`） | 同上 |
| F13 | 持ち主の色は `getOwnerMeta`（`:233`〜`:245`）。使う場所は日ごとの一覧の丸 `:645`・`:653`、予定の一覧の丸 `:712`・`:721`、仮の箱 `:1260`〜`:1262`、箱 `:1272` | 同上 |
| F14 | 箱の一覧の `useMemo` の依存の並びは `:1277`〜`:1281` | 同上 |
| F15 | 動かす保存 `patchMoved`（`:1284`〜）は `color_key` を送らない。試験 T6 が本文を `toEqual` で縛っている | 同上・`frontend/src/pages/schedule/SchedulePageImpl.test.tsx:1077`〜`:1105` |
| F16 | 3 択は `scopeChoices`（`frontend/src/pages/schedule/schedule-utils.ts:532`〜`:536`）。「繰り返しの形が変わった」の印が真だと 3 択より少なくなる | 同上 |
| F17 | 一覧の返しの形 `ApiCalendarEvent`（`:15`〜`:40`）・画面の形 `ScheduleItem`（`:54`〜`:78`）・返しから画面の形へ直す関数（`:355`〜`:381`） | `frontend/src/pages/schedule/schedule-utils.ts` |
| F18 | 色の欄を置く並び: 作る窓は `ScheduleDraftFields`（`frontend/src/pages/schedule/ScheduleDraftFields.tsx:483`〜`:515`）、編集の画面は `frontend/src/pages/schedule/ScheduleFullEditor.tsx:87`〜`:89` の種類の行の後 | 同上 |
| F19 | 窓の絵は `SCHEDULE_POPOVER_ICONS`（`frontend/src/constants/icons.tsx:372`〜`:382`）。outline の絵は `:16`〜`:92` で読み、`hi(...)` で包む（例 `:139`） | 同上 |
| F20 | `@heroicons/react` 2.2.0 に `SwatchIcon`（24/outline）がある | `frontend/node_modules/@heroicons/react/24/outline/SwatchIcon.js` |
| F21 | 画面の文字の `schedule` の塊は ja・en とも `:3336` から。`"category"` は ja の `:3447`（origin/main e4c074d30） | `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` |
| F22 | 新しいトークンを足す PR は、本文に「### デザイントークン変更時」の 4 つの印と理由が要る | `frontend/scripts/check-new-tokens.js`・`.github/PULL_REQUEST_TEMPLATE.md` |

## 3. 触るファイル（これ以外は触らない）

- 新規: `frontend/src/components/ColorSwatchPicker.tsx`・`frontend/src/components/ColorSwatchPicker.css`・`frontend/src/components/ColorSwatchPicker.stories.tsx`・`frontend/src/components/ColorSwatchPicker.test.tsx`・`frontend/src/pages/schedule/eventColors.ts`・`frontend/src/pages/schedule/eventColors.test.ts`・`backend/tests/test_event_colors_tokens.py`
- 変更: `frontend/src/index.css`・`frontend/src/tokens.css`・`frontend/src/constants/icons.tsx`・`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`・`frontend/src/pages/schedule/schedule-utils.ts`・`frontend/src/pages/schedule/SchedulePageImpl.tsx`・`frontend/src/pages/schedule/ScheduleDraftFields.tsx`・`frontend/src/pages/schedule/ScheduleFullEditor.tsx`・`docs/CC_UI_GOVERNANCE.md`
- 試験の変更: `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`
- 設計とこのカード: `docs/handoff/event-color/design.md`・`docs/handoff/event-color/card-bin2.md`。作業場所を作った直後に `git checkout origin/release/event-color-bin2 -- docs/handoff/event-color/design.md docs/handoff/event-color/card-bin2.md` で取り込み、同じ PR に入れる（中身は変えない。§13 の報告欄だけ追記してよい）

型を直したために別の試験ファイルが型の誤りで落ちるときは、その試験ファイルに `colorKey` を足すだけ直してよい（報告に名前を書く）。

## 4. 作り方

### 4-1. 色のトークン

`frontend/src/index.css`:
- 明るい画面: `:206`（`--gcal-now: #db372d;`）の次の行から 24 行。暗い画面: `:422`（`--gcal-now: #f55e57;`）の次の行から同じ 24 行（v1 は同じ値）。
- 並びと値は設計 §4-1 の表のとおり（1 文字も変えない）。鍵の `_` は `-` にして名に使う。

```css
  /* 予定ごとの色（ADR-1081）。Google の予定のラベル 24 色。値の正本は backend/app/services/event_colors.py（試験で照らす） */
  --gcal-event-radicchio:           #ad1457;
  --gcal-event-cherry-blossom:      #d81b60;
  /* … 残り 22 個 … */
```

`… 残り 22 個 …` は省略の印。実物には 24 個すべてを書く。

`frontend/src/tokens.css`: `:root` の終わりの `}`（`:645`）の直前に 24 行。

```css
  /* ── 予定ごとの色（ADR-1081）。部品と画面はこちらを使う ── */
  --event-color-radicchio:       var(--gcal-event-radicchio);
  --event-color-cherry-blossom:  var(--gcal-event-cherry-blossom);
  /* … 残り 22 個 … */
```

### 4-2. トークンと裏側の値の一致の試験（新規 `backend/tests/test_event_colors_tokens.py`）

- 画面のファイルの読み方は `backend/tests/seed_data.py:22` の形（`Path(__file__).resolve().parents[2] / "frontend" / ...`）。
- 試験 1: `frontend/src/index.css` の `:root {`（`:9`）から最初の `}` までの中の `--gcal-event-<名>: <値>;` を全部拾い、名の `-` を `_` に戻した「鍵 → 値（小文字）」の表が `EVENT_COLORS` と同じ（数も 24）。
- 試験 2: `:root.force-dark {` の塊でも 24 個そろっている（鍵が `EVENT_COLORS` と同じ）。
- 試験 3: `frontend/src/tokens.css` に `--event-color-<名>: var(--gcal-event-<名>);` が 24 個。
- 試験 4: `frontend/src/pages/schedule/eventColors.ts` の `EVENT_COLOR_KEYS` の配列の文字の並びが `EVENT_COLOR_KEYS`（裏側）と同じ。
- 試験 5: `frontend/src/locales/ja.json`・`en.json` の `schedule.eventColors` に 24 の鍵と `default` がある（JSON として読む）。

### 4-3. 予定の色の一覧（新規 `frontend/src/pages/schedule/eventColors.ts`）

色の値は書かない。

```ts
/**
 * 予定ごとの色（ADR-1081）。鍵の並びは裏側の正本 backend/app/services/event_colors.py と同じ
 * （backend/tests/test_event_colors_tokens.py が照らす）。色の値はトークン --event-color-* にだけある。
 */
export const EVENT_COLOR_KEYS = [
  "radicchio", "cherry_blossom", "flamingo", "tomato", "tangerine", "pumpkin",
  "mango", "banana", "citron", "avocado", "pistachio", "basil",
  "sage", "eucalyptus", "peacock", "cobalt", "lavender", "blueberry",
  "wisteria", "amethyst", "grape", "cocoa", "graphite", "birch",
] as const;

export type EventColorKey = (typeof EVENT_COLOR_KEYS)[number];

export function isEventColorKey(value: unknown): value is EventColorKey {
  return typeof value === "string" && (EVENT_COLOR_KEYS as readonly string[]).includes(value);
}

/** 色のトークンの文字。鍵の _ は - にする */
export function eventColorVar(key: EventColorKey): string {
  return `var(--event-color-${key.replace(/_/g, "-")})`;
}

/** 画面の文字の鍵 */
export function eventColorLabelKey(key: EventColorKey | null): string {
  return key === null ? "schedule.eventColors.default" : `schedule.eventColors.${key}`;
}

/** 予定の色を決める場所は 1 つ（箱・一覧の丸・仮の箱が通る）。色なしは持ち主の色 */
export function eventDisplayColor(colorKey: EventColorKey | null | undefined, ownerColor: string): string {
  return colorKey ? eventColorVar(colorKey) : ownerColor;
}
```

試験 `eventColors.test.ts`: 24 個・重なりなし・`eventColorVar("cherry_blossom")` が `var(--event-color-cherry-blossom)`・`isEventColorKey("red")` が偽・`eventDisplayColor(null, X)` が `X`。

### 4-4. 新しい金型 `ColorSwatchPicker`

ADR-144 の金型。予定のことは知らない。

```ts
export interface ColorSwatchOption {
  /** null はデフォルト */
  value: string | null;
  /** 読み上げと見出しに使う名（呼ぶ側が t() で渡す） */
  label: string;
  /** 丸の地。var(--...) の文字か、呼ぶ側の色の値をそのまま */
  color: string;
}
export interface ColorSwatchPickerProps {
  /** 欄の名（radiogroup と開くボタンの読み上げ） */
  label: string;
  options: ColorSwatchOption[];
  value: string | null;
  onChange: (value: string | null) => void;
  /** ラジオの name（同じ画面に 2 つ出ても混ざらない名を呼ぶ側が渡す） */
  name: string;
  /** 外側配置専用のクラス（Button の layoutClassName と同じ考え） */
  layoutClassName?: string;
}
```

形:
1. 外側は `<div className="comp-color-swatch-picker [layoutClassName]">`。
2. 開くボタンは金型 `Button`（`variant="ghost"`・`size="sm"`・`aria-expanded={open}`・`aria-label={`${label}: ${今の選択肢の label}`}`）。中に `<span className="comp-color-swatch-picker__dot" style={{ background: 今の選択肢の color }} aria-hidden="true" />` と今の選択肢の名。
3. 開いている間だけ、その下に `<div className="comp-color-swatch-picker__grid" role="radiogroup" aria-label={label}>`。体の外へ移さない（`createPortal` と `Popover` を使わない）。
4. 丸 1 つ: `<label className={"comp-color-swatch-picker__swatch" + (選ばれていれば " comp-color-swatch-picker__swatch--selected" : "")} style={{ background: option.color }} title={option.label}>` の中に `<RadioControl name={name} value={option.value ?? ""} checked={選ばれている} onChange={() => onChange(option.value)} aria-label={option.label} />`。
5. 丸を選んでも一覧は開いたまま（Google と同じく続けて見比べられる）。開くボタンをもう一度押すと閉じる。

`ColorSwatchPicker.css`（色・寸法・角・影はトークンだけ。hex・rgba・数の z-index を書かない）:

```css
/* ColorSwatchPicker — 色見本の金型（ADR-1081・ADR-144）。手本は pages-layout.css の .color-swatch。全値は CSS 変数（ADR-067） */
.comp-color-swatch-picker { display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-2); }
.comp-color-swatch-picker__dot { display: inline-block; width: var(--size-checkbox); height: var(--size-checkbox); border-radius: var(--radius-full); }
.comp-color-swatch-picker__grid { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.comp-color-swatch-picker__swatch {
  position: relative;
  width: var(--space-6);
  height: var(--space-6);
  border-radius: var(--radius-full);
  border: 2px solid transparent;
  cursor: pointer;
}
.comp-color-swatch-picker__swatch--selected {
  border-color: var(--text-primary);
  box-shadow: 0 0 0 2px var(--bg-surface) inset, var(--shadow-drop-sm);
}
.comp-color-swatch-picker__swatch:has(input:focus-visible) { box-shadow: var(--focus-ring-shadow); }
.comp-color-swatch-picker__swatch input[type="radio"] {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}
```

`2px` の枠と影の広がりは手本（`frontend/src/pages-layout.css:282`・`:291`）と同じ書き方。CSS の見張り（§5-2）が止めたら、止めた原文を貼って NEEDS_DECISION:（勝手に新しいトークンを作らない）。

`ColorSwatchPicker.stories.tsx`: `RadioControl.stories.tsx` の形。地の色は `var(--event-color-*)` を何個かと `var(--accent)` をデフォルトとして並べる（色の値を書かない）。

`ColorSwatchPicker.test.tsx`:
- 開く前は radiogroup が無く、ボタンを押すと出る（`aria-expanded` が true）。
- 渡した選択肢の数だけラジオが出る（25 個を渡して 25 個）。
- 今の値のラジオだけ `checked`。
- 丸を押すと `onChange` に値（デフォルトは `null`）が届く。
- 矢印キーで動けるのは本物のラジオで同じ `name` だから。試験では、全部のラジオの `name` が同じで `type="radio"` であることを確かめる（jsdom は矢印キーの動きを持たないため）。
- 地の色は渡した文字のまま（`style.background` が `var(--event-color-...)`）。

`docs/CC_UI_GOVERNANCE.md` の「## 金型の目録」の表の最後に 1 行: `| \`ColorSwatchPicker\` | 色見本から 1 つ選ぶ欄（押すと下に丸の一覧が開く。中は RadioControl） | \`frontend/src/components/ColorSwatchPicker.tsx\` |`（表の書式は既存の行に合わせる）。

### 4-5. 画面の文字（`frontend/src/locales/ja.json`・`en.json`）

`schedule` の塊の `"category"`（ja `:3447`・en は同じ塊の `"category"`）の次に:
- `"eventColor"`: ja `予定の色` ／ en `Event color`
- `"eventColors"`: `{ "default": ..., "radicchio": ..., … 24 個 }`。名は設計 §4-1 の表の ja・en の列のまま。`default` は ja `デフォルト` ／ en `Default`。

ja と en の鍵は同じにする（ADR-027）。

### 4-6. 欄の絵（`frontend/src/constants/icons.tsx`）

- outline の import の並び（`:16`〜`:92`）に `SwatchIcon as SwatchOutlineIcon,`。
- `hi(...)` の並び（`:139` 付近）に `const SwatchOutline = hi(SwatchOutlineIcon);`。
- `SCHEDULE_POPOVER_ICONS`（`:372`〜）の `share` の次に `color: SwatchOutline, // SwatchIcon outline — 予定の色の行（ADR-1081）`。

### 4-7. 一覧の返しと画面の形（`frontend/src/pages/schedule/schedule-utils.ts`）

- `ApiCalendarEvent`（`:15`〜）の最後に `color_key?: string | null;`
- `ScheduleItem`（`:54`〜）の最後に `/** 予定の色（ADR-1081）。null は持ち主の色 */ colorKey?: EventColorKey | null;`
- 返しから画面の形へ直す関数（`:355`〜）の返しに `colorKey: isEventColorKey(event.color_key) ? event.color_key : null,`（知らない値は色なしとして扱う）。
- シフトの形（`normalizeShift`）は触らない（`colorKey` は省略可）。
- `scopeChoices`（`:532`〜`:536`）は触らない。

### 4-8. 予定の画面（`frontend/src/pages/schedule/SchedulePageImpl.tsx`）

1. `ScheduleDraft`（`:89`〜`:103`）の最後に `/** 予定の色（ADR-1081）。null はデフォルト（持ち主の色） */ colorKey: EventColorKey | null;`
2. `createDraft`（`:142`〜）の返しに `colorKey: item?.colorKey ?? null,`。`:962`〜`:977` と `:1204`〜`:1213` の `setDraft({...})` に `colorKey: null,`。
3. 保存の `body`（`:1012`〜`:1020`）の `location` の次に `color_key: draft.colorKey ?? "",`（いつも送る。裏側は変わったときだけ Google に送る・設計 §4-9）。
4. 繰り返しの保存（`:1069`〜`:1077`）の「繰り返しの形が変わった」の印には色を入れない（3 択がすべて出る）。
5. 動かす保存 `patchMoved`（`:1284`〜）は触らない（`color_key` を送らない）。
6. 色を決める場所を 1 つにする: 次の 4 か所を `eventDisplayColor` に通す。
   - 日ごとの一覧の丸 `:653`: 前 `style={{ background: ownerMeta.color }}` → 後 `style={{ background: eventDisplayColor(item.colorKey, ownerMeta.color) }}`
   - 予定の一覧の丸 `:721`: 同じ
   - 箱 `:1272`: 前 `color: getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId).color,` → 後 `color: eventDisplayColor(item.colorKey, getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId).color),`
   - 仮の箱 `:1260`〜`:1262`: 前 `color: currentOwnerUserId != null ? getOwnerMeta(...).color : undefined,` → 後 `color: draft.colorKey ? eventColorVar(draft.colorKey) : (currentOwnerUserId != null ? getOwnerMeta(ownerByUserId, currentOwnerUserId, currentOwnerUserId).color : undefined),`
   - 依存の並び（`:1277`〜`:1281`）の `draft.title` の次に `draft.colorKey`。
7. デフォルトの丸に使う持ち主の色を 1 か所で出す: 窓と編集の画面を出す前（`:1668` の手前）に
   `const draftOwnerColor = getOwnerMeta(ownerByUserId, popover?.item?.ownerUserId ?? null, currentOwnerUserId).color;`
   （作るときは item が無いので `currentOwnerUserId` の色になる。`getOwnerMeta` の `:238` の決まり）。
   これを `SchedulePopover`（`:1670`〜）と `ScheduleFullEditor`（`:1688`〜）に `ownerColor={draftOwnerColor}` で渡す。
8. `SchedulePopover` の props に `ownerColor: string` を足し、`ScheduleDraftFields`（`:419`〜`:428`）へそのまま渡す。

### 4-9. 色の欄（`ScheduleDraftFields.tsx`・`ScheduleFullEditor.tsx`）

`frontend/src/pages/schedule/ScheduleDraftFields.tsx` の `DraftCategoryField` の直後に足す:

```tsx
export function DraftColorField({ appearance, draft, onDraftChange, ownerColor }: FieldProps & { ownerColor: string }) {
  const { t } = useTranslation();
  const ColorIcon = SCHEDULE_POPOVER_ICONS.color;
  const options: ColorSwatchOption[] = [
    { value: null, label: t(eventColorLabelKey(null)), color: ownerColor },
    ...EVENT_COLOR_KEYS.map((key) => ({ value: key, label: t(eventColorLabelKey(key)), color: eventColorVar(key) })),
  ];
  const picker = (
    <ColorSwatchPicker
      label={t("schedule.eventColor")}
      name={`schedule-event-color-${appearance}`}
      options={options}
      value={draft.colorKey}
      onChange={(value) => onDraftChange({ ...draft, colorKey: isEventColorKey(value) ? value : null })}
    />
  );
  if (appearance === "page") return picker;
  return (
    <CreateRow creating icon={<ColorIcon size={20} aria-hidden="true" />}>
      {picker}
    </CreateRow>
  );
}
```

（`FieldProps` の今の形に `mode` が要るなら、呼ぶ側は `DraftCategoryField` と同じ渡し方にする。`CreateRow` の受ける形は `DraftCategoryField` の `:313` と同じ）

- `ScheduleDraftFields`（`:483`〜）の props に `ownerColor: string` を足し、`<DraftCategoryField .../>` の次の行に `<DraftColorField {...common} mode={mode} ownerColor={ownerColor} />`。
- `ScheduleFullEditor.tsx`: props に `ownerColor: string`。種類の行（`:87`〜`:89`）の次に
  `<EditorPageRow icon={<ColorIcon size={20} aria-hidden="true" />}><DraftColorField {...common} mode={mode} ownerColor={ownerColor} /></EditorPageRow>`
  （`ColorIcon` は同じファイルの他の絵と同じく `SCHEDULE_POPOVER_ICONS.color` から取る）。

### 4-10. 試験（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` に足す）

既存の試験の形（`apiEvent({...})`・`calendarProps.current`・`api.post`/`api.patch` の呼ばれ方）をなぞる。

| # | 試験 |
|---|---|
| C1 | 色なしの予定の箱は持ち主の色のまま（`calendarProps.current.events` の該当の `color` が今と同じ値） |
| C2 | `color_key: "tomato"` の予定の箱の `color` が `var(--event-color-tomato)` |
| C3 | 予定の一覧の表示で、`color_key` ありの予定の丸の `style.background` が `var(--event-color-...)` |
| C4 | 作る窓で色の欄を開き、丸を選んで保存すると `api.post` の本文の `color_key` が選んだ鍵 |
| C5 | 色に触らずに保存すると本文の `color_key` が `""` |
| C6 | 色のある予定を直す画面を開くと、その色のラジオが `checked` |
| C7 | 作る窓で色を選ぶと、仮の箱（id `pending`）の `color` がその色のトークン |
| C8 | 繰り返しの予定で色だけ変えて保存すると、3 択の窓に 3 つ（1 回目でない回）の選択肢が出る |
| C9 | 動かす保存の本文に `color_key` が無い（既存の T6 が通ることで足りる。T6 は変えない） |
| C10 | 色の欄の丸を押しても作る窓が閉じない（窓の外を押したと見なされない） |

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は作業場所の外の /tmp/CC報告ファイル/event-color/bin2/ に置く）

1. 画面の試験: `cd <作業場所>/frontend && npx vitest run src/components/ColorSwatchPicker.test.tsx src/pages/schedule/eventColors.test.ts src/pages/schedule/SchedulePageImpl.test.tsx src/pages/schedule/SchedulePageCache.test.tsx src/pages/schedule/schedule-utils.test.ts src/components/gcalColorsUsage.test.ts --reporter=verbose > /tmp/CC報告ファイル/event-color/bin2/vitest.txt 2>&1; echo rc=$?; grep -c "✓" /tmp/CC報告ファイル/event-color/bin2/vitest.txt; grep -E "✗|×|FAIL" /tmp/CC報告ファイル/event-color/bin2/vitest.txt | head -20`
2. 画面の見張り: `npm run check:all > /tmp/CC報告ファイル/event-color/bin2/check-all.txt 2>&1; echo rc=$?; tail -30 /tmp/CC報告ファイル/event-color/bin2/check-all.txt`。あわせて `npx tsc --noEmit -p . > /tmp/CC報告ファイル/event-color/bin2/tsc.txt 2>&1; echo rc=$?; head -20 /tmp/CC報告ファイル/event-color/bin2/tsc.txt` と `node scripts/check-new-tokens.js` の出力を貼る（PR 本文の印は §10 で付ける）。
3. 裏側の一致の試験: `cd <作業場所>/backend && python -m pytest tests/test_event_colors_tokens.py -v > /tmp/CC報告ファイル/event-color/bin2/pytest.txt 2>&1; echo rc=$?; grep -E "PASSED|FAILED|ERROR" /tmp/CC報告ファイル/event-color/bin2/pytest.txt`
4. 色の値を書き写していないこと: `git grep -n -i "#ad1457" -- frontend/src` の結果が `frontend/src/index.css` の 2 行だけ。
5. 触ったファイルが §3 だけで、削除の塊が無いこと: `git diff --stat origin/main...HEAD` を貼る。

## 6. 分岐ごとの対処

- §2 の行や §4 の「前」のコードが作業場所の origin/main と合わない → 合わない部分の原文を貼って NEEDS_DECISION:（直さずに止める）
- 行番号が数行ずれているだけで中身が同じ → ずれた行で直し、報告に書く（記録のみで続行）
- 見張り（§5-2）が新しい書き方を止めた → 止めた原文を貼って NEEDS_DECISION:（ui-allow を足さない・新しいトークンを勝手に作らない）
- C10 が落ちる（丸を押すと窓が閉じる）→ 原文を貼って NEEDS_DECISION:
- 手元で流せない試験がある → 「流せなかった」と書き、CI に任せる（記録のみで続行）
- CI が落ちる → 担当は待たない。Opus が読む

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 色の欄が 25 個の丸を出し、選んだ色が保存の本文に入る | ColorSwatchPicker.test.tsx・C4〜C6 |
| 箱・一覧の丸・仮の箱が同じ色の決め方を通る（色なしは持ち主の色） | C1〜C3・C7 |
| 繰り返しで色だけ変えると 3 択がすべて出る・動かす保存は色を送らない | C8・T6 |
| 色の値は `index.css` だけ・トークンと裏側の値が一致 | §5-3・§5-4 |
| 画面の見張りと型の確かめがすべて通る | §5-2 |
| 触ったファイルが §3 だけ | §5-5 |
| 必須チェックがすべて緑 | PR の checks |

## 8. 反映の手順（Opus が行う。担当はしない）

1. CI 緑 → 審査役（reviewer・opus）APPROVE → PR に「確認済み：」コメント。
2. 本番に入れる前に PO に聞く（2026-11-20 の約束）。PO の返事の後でマージする。
3. マージ後、配備の記録で画面の組み立てが本番に入ったことを確かめ、PO に K1・K2・K5・K6 と K3・K4 の目視をお願いする。

## 9. 弊害と戻し方

- 色なしの予定は今と同じ見た目（`eventDisplayColor` が持ち主の色を返す）。
- 戻すときはこの PR を戻すだけ。裏側は `color_key` を送られなければ変えないので、画面だけ戻しても保存は壊れない。
- 明るい色（バナナ等）の上の白い文字の読みにくさは設計 §6 のとおり別の話として数える。

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/event-color-bin2-impl --claude`（origin/main 起点）。クラウドで clone した場合も、commit の前に必ずこの手順で作業場所を作る。出力はパイプに通さない。作成後に `git worktree list` で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- push は `git push -u origin HEAD`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/event-color-bin2-impl -1 --oneline` で実在を確かめる。`--no-verify` は使わない
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿う:
  - `### 標準ワークフロー確認` に recon（docs/handoff/event-color/recon.md）・設計（docs/handoff/event-color/design.md）・このカード・ADR-1081
  - `### デザイントークン変更時` の 4 つの印をすべて `[x]` にし、概要に理由を書く: 「予定ごとの色（ADR-1081）。Google の予定のラベル 24 色を画面に出すため、色の値 `--gcal-event-*` を index.css の明るい画面と暗い画面に、部品が使う `--event-color-*` を tokens.css に足した。今あるトークンに同じ 24 色は無い（`--gcal-*` は予定の画面の地の色だけ）」
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。良い例: `触るファイル: frontend/src/index.css, frontend/src/tokens.css` ／ 禁止形: 行を分ける・バッククォートで囲む・「（新規）」などの注記を付ける
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-5 の出力（長いものは生出力のパスと要点の行）／PR の URL／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない。CI・デプロイは待たない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

以上（カードの終わり）
