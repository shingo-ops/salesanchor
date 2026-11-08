# 実装カード 便8: 残りの部品を決められた部品に差し替える（G26〜G30）（2026-11-08）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2.3・§3.13（PO の選択「1」2026-11-08・審査は §9 の 11 回目）
- 土台: origin/main 36ea9b7b2。ブランチ `release/schedule-mold-bin8-impl`
- 成功条件: G26〜G30（design.md §2.3）
- 対象 ADR: ADR-144（金型を使う）・ADR-067（トークン）・ADR-027（文言は t()）・ADR-1065（金型 CalendarView）
- 行番号はすべて origin/main 36ea9b7b2 の値。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。
- 作業は必ず `bash scripts/new-worktree.sh release/schedule-mold-bin8-impl --claude` で作った作業場所の中で行う。
- 金型（`frontend/src/components/` の中の部品）は変えない。使うだけ。新しいトークン・新しい文言キーは足さない。
- 色・寸法の直書き禁止。css の値は `var()` と言葉の値だけ。
- 試験はクラウドの作業場所で回す（`cd frontend && npx vitest run src/pages/schedule/ src/features/schedule/ src/components/CalendarView.test.tsx`・`npx tsc --noEmit`・`npm run lint`・`node scripts/check-css-hardcoded-values.js`・`node scripts/check-css-hardcoded-colors.js`・`npm run check:dark-parity`）。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | ボタン 5 つ・札 1 つ・import（§2） |
| `frontend/src/features/schedule/calendars.config.ts` | `badgeVariant` を足し、色 3 つと `cssVar` を消す（§3） |
| `frontend/src/pages/schedule/schedule-owner.ts` | 持ち主の色が無い時の色（§4） |
| `frontend/src/pages/schedule.css` | 規則 1 つを消し、1 つを 2 行にする（§5） |
| `frontend/src/components.css` | `.modal-icon-btn` の 3 つを消す（§5） |
| `frontend/src/tokens.css` | `:81` の説明の文を直す（§5） |
| `frontend/src/features/schedule/calendars.config.test.ts`・`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | 試験（§6） |
| .claude-pipeline/active-work.d/release-schedule-mold-bin8-impl.md | 台帳（new-worktree.sh が作る形のまま・状態を更新） |

触らない（変えたら差し戻し）:
- `frontend/src/components/` の中のファイル全部（`CalendarView.stories.tsx` も変えない。`DEFAULT_OWNER_COLOR` の値が変わるだけで、そのまま動く）
- `frontend/src/pages/schedule/ScheduleSettingsPage.tsx`
- `SchedulePageImpl.tsx` の `:637`・`:753`・`:821` の生の `<button>` と `:290`・`:740` の小窓の外枠（B 組・PO に聞く）
- `schedule.css` の `@media` の中
- 移行（migrations）・`.github/workflows/`・リポジトリ直下の `scripts/`・backend・`frontend/scripts/`

## 2. SchedulePageImpl.tsx

### 2-1 import
`:13` の次に `import { Badge } from "../../components/Badge";` を足す。
`:28` を次にする（`cssVar` を外す）:
```ts
import { CALENDARS, CALENDAR_MAP, type CalendarId } from "../../features/schedule/calendars.config";
```

### 2-2 種類の札（`:298-305`）
前:
```tsx
            {!creating && meta && (
              <span
                className="schedule-category-chip"
                style={{ background: cssVar(meta.tintVar), color: cssVar(meta.textVar) }}
              >
                {t(meta.labelKey)}
              </span>
            )}
```
後:
```tsx
            {!creating && meta && (
              <Badge variant={meta.badgeVariant} size="md">
                {t(meta.labelKey)}
              </Badge>
            )}
```

### 2-3 詳しくの小窓のボタン 3 つ（`:308-330`）
前:
```tsx
            {mode === "detail" && canEdit && item && (
              <button
                className="modal-icon-btn"
                onClick={onSave}
                aria-label={t("schedule.editEvent")}
                title={t("schedule.editEvent")}
              >
                <EditIcon size={18} />
              </button>
            )}
            {mode !== "create" && canEdit && item && (
              <button
                className="modal-icon-btn modal-icon-btn--danger"
                onClick={onDelete}
                aria-label={t("schedule.deleteEvent")}
                title={t("schedule.deleteEvent")}
              >
                <DeleteIcon size={18} />
              </button>
            )}
            <button className="modal-icon-btn" onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </button>
```
後:
```tsx
            {mode === "detail" && canEdit && item && (
              <Button
                variant="ghost"
                size="md"
                iconOnly
                onClick={onSave}
                aria-label={t("schedule.editEvent")}
                title={t("schedule.editEvent")}
              >
                <EditIcon size={18} />
              </Button>
            )}
            {mode !== "create" && canEdit && item && (
              <Button
                variant="ghost"
                size="md"
                iconOnly
                onClick={onDelete}
                aria-label={t("schedule.deleteEvent")}
                title={t("schedule.deleteEvent")}
              >
                <DeleteIcon size={18} />
              </Button>
            )}
            <Button variant="ghost" size="md" iconOnly onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </Button>
```

### 2-4 その日の一覧の小窓の閉じる（`:744-746`）
前:
```tsx
            <button className="modal-icon-btn" onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </button>
```
後:
```tsx
            <Button variant="ghost" size="md" iconOnly onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </Button>
```

### 2-5 知らせの帯の ×（`:1532-1538`）
前:
```tsx
                <button
                  onClick={() => setBanner(null)}
                  className="schedule-banner__close"
                  aria-label={t("common.close")}
                >
                  ×
                </button>
```
後:
```tsx
                <Button
                  variant="ghost"
                  size="sm"
                  iconOnly
                  layoutClassName="schedule-banner__close"
                  onClick={() => setBanner(null)}
                  aria-label={t("common.close")}
                >
                  <BannerCloseIcon size={16} />
                </Button>
```
`BannerCloseIcon` は、この帯を描く関数（`banner` の `useState` がある `:938` の関数）の中で、`return` より前に `const BannerCloseIcon = SCHEDULE_POPOVER_ICONS.close;` と 1 行足して作る。

## 3. calendars.config.ts

- 先頭に `import type { BadgeVariant } from "../../components/Badge";` を足す。
- `CalendarMeta`（`:10-17`）の `colorVar`・`tintVar`・`textVar` の 3 行を消し、`labelKey` の次に `badgeVariant: BadgeVariant;` を足す。
- `CALENDARS`（`:19-76`）の各項目の `colorVar`・`tintVar`・`textVar` の 3 行を消し、`labelKey` の次に `badgeVariant` を足す: meeting=`"info"`・personal=`"purple"`・procurement=`"success"`・shipping=`"danger"`・billing=`"warning"`・release=`"neutral"`・holiday=`"purple"`。
- `cssVar`（`:82-84`）を消す。
- 消した後、このファイルに `#` の色が 0 件。

## 4. schedule-owner.ts

- `:34` を `export const DEFAULT_OWNER_COLOR = "var(--calendar-google-blue)";` にする。直前の行に説明 `/** 持ち主が見つからない時に画面に描く色。持ち主の色の正本はサーバー（backend/app/routers/calendar.py の _DEFAULT_OWNER_COLOR） */` を足す。
- `:43` を `    color: owner.color,` にする。

## 5. css

- `frontend/src/pages/schedule.css:381-390`（`.schedule-category-chip` の規則とその後の空行）を消す。
- `frontend/src/pages/schedule.css:1026-1032` を次にする:
```css
.schedule-banner__close {
  margin-left: var(--space-3);
  vertical-align: middle;
}
```
- `frontend/src/components.css:362-386`（説明の 1 行 `/* ヘッダー内アイコンボタン（ゴミ箱・閉じる） */`・`.modal-icon-btn`・`.modal-icon-btn:hover`・`.modal-icon-btn--danger:hover` とその後の空行）を消す。`.modal h3` の規則（`:387`）は残す。
- `frontend/src/tokens.css:81` の説明 `/* アイコンボタン・中型クリックターゲット（.modal-icon-btn 等） */` を `/* アイコンボタン・中型クリックターゲット */` にする。値は変えない。

## 6. 試験

- `calendars.config.test.ts` に足す:
  (a) 7 種類の `badgeVariant` が §3 の対応どおり（`Object.fromEntries(CALENDARS.map((c) => [c.id, c.badgeVariant]))` を表と `toEqual` で比べる）。
  (b) `JSON.stringify(CALENDARS)` に `/#[0-9a-fA-F]{3,8}\b/` が当たらない。
- `SchedulePageImpl.test.tsx` に足す（今の `describe` の書き方と `apiEvent({})`・`view()` を使う）:
  (c) 自分の予定（`answers.events = [apiEvent({})]`・種類 meeting）を押して詳しくの小窓を開くと、名前 `schedule.editEvent`・`schedule.deleteEvent`・`common.close` のボタンの class に `comp-btn--ghost` と `comp-btn--icon-only` があり、`document.querySelectorAll(".modal-icon-btn").length` が 0。
  (d) 同じ小窓で、`document.querySelector(".schedule-popover .comp-badge")`（札）が在り、class に `comp-badge--info` と `comp-badge--soft` があり、`style` 属性が無く、文字が `i18n.t("schedule.calendarLabels.meeting")`（同じ文字は左の欄にも出るので、文字で探さない）。
  (e) `render(<MemoryRouter initialEntries={["/schedule?connected=true"]}><SchedulePage /></MemoryRouter>)` で帯が出て、帯の中の名前 `common.close` のボタンの class に `comp-btn--sm`・`comp-btn--icon-only`・`schedule-banner__close` があり、中に `svg` がある。押すと `i18n.t("schedule.connectSuccess")` の文字が消える。
- 既存の試験は全部通ること（直す・消すのボタンを名前で押す既存の試験 `:174`・`:741` などは、名前が変わらないので通る）。

## 7. 返事

DONE と HEAD の SHA・試験の結果の数（通った／落ちた）・tsc・lint・css 検査・dark-parity の結果・G29 の数え（4 ファイルの `grep -cE "#[0-9a-fA-F]{3,8}\b"` の値）。止めたときは `BLOCKED:` か `NEEDS_DECISION:` と理由。
