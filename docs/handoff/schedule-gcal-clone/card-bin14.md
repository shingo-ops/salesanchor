# 実装カード 便14: 予定の編集画面を Google の形に・直すときも全画面（G58〜G64）（2026-11-11）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2.7（G58〜G64）・§3.19（審査は §9 に記録）
- PO の承認: 審査の後に PO へ聞く（新しい金型 EditorPage・古い金型 FullScreenDialog を消す・角の小さい塗りの欄・丸い保存・直すときも全画面）。承認の記録が §9 に無ければ着手しない。
- 土台: ブランチ `release/schedule-gcal-editor-page`（origin/main a7fbffdfe から作った）。このブランチの上にそのまま積む（設計・カード・実装を 1 つの PR にする。便13 と同じ形）。
- 対象 ADR: ADR-1074（この便で起こす）・ADR-144（金型）・ADR-067（トークン）・ADR-027（i18n）・ADR-073（見本帳）・ADR-1060（Meet）・ADR-1051（本番の画面点検 S13）
- 行番号はすべて a7fbffdfe の値。違っていたら中身で場所を探し、見つからなければ止める。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。設計 §3.19 とこのカードが食い違ったら止める。
- 色・寸法は var() だけ（px・色・rem の直書き禁止。トークンは §6 の 5 つだけ足す）。UI の文字は t() だけ（見本帳の中の見本の文字は除く）。
- 確かめはクラウドの作業場所で回す: `cd frontend && npx vitest run src/components/ src/pages/schedule/`・`npx tsc --noEmit`・`npm run check:all`。全部 0 件の失敗になるまで直す。
- 試験が落ちたら直してよいのは §9 に書いた試験だけ。ほかの試験が落ちたら止めて返す。
- commit は `git add` に触ったファイルを名前で並べる（`git add -A`・`git add .` は使わない。消すファイルは `git rm`）。push は `git push origin release/schedule-gcal-editor-page`（force・rebase・amend は禁止）。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/components/EditorPage.tsx`（新規） | 金型（§2-1） |
| `frontend/src/components/EditorPage.css`（新規） | 金型の見た目（§2-2） |
| `frontend/src/components/EditorPage.stories.tsx`（新規） | 見本帳（§2-3） |
| `frontend/src/components/EditorPage.test.tsx`（新規） | §9-1 |
| `frontend/src/components/FullScreenDialog.tsx`・`.css`・`.stories.tsx`・`.test.tsx` | `git rm` で消す（§2-4） |
| `frontend/src/components/TextField.tsx`・`Select.tsx`・`Textarea.tsx` | 種類の名前を足す（§3） |
| `frontend/src/components/Button.tsx` | 先頭の説明 `:9` の 1 行だけ（§2-1） |
| `frontend/src/components/FormField.css` | 種類の見た目（§3） |
| `frontend/src/components/TextField.stories.tsx`・`Select.stories.tsx`・`Textarea.stories.tsx` | 新しい種類の例を 1 つずつ（§3） |
| `frontend/src/tokens.css`・`frontend/src/index.css` | トークン 5 つ（§6） |
| `frontend/src/pages/schedule/ScheduleDraftFields.tsx` | 1 項目ずつの部品に分ける（§4） |
| `frontend/src/pages/schedule/ScheduleFullEditor.tsx` | EditorPage に載せ替え（§5） |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 直すときも全画面・小窓の直す形を消す（§7） |
| `frontend/src/pages/schedule.css` | `.schedule-full-editor` の 2 つの規則（`:529-537`）を §5 の規則に置き換える |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | §9-2 |
| `frontend/src/components/buttonShapeUsage.test.ts` | 使ってよい場所を 3 つ足す（§8） |
| `frontend/src/components/editorVariantUsage.test.ts`（新規） | §8 |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | キー 1 つ（§10） |
| `docs/specs/design-system/design.md` | `:262`・`:276`・`:811` に例外の 1 文ずつ（§8） |

触らない（変えたら差し戻し）:
- 金型 `Button`（説明の 1 行を除く）・`Checkbox`・`Toggle`・`Modal`・`CalendarView` と `frontend/src/hooks/useFocusTrap.ts`
- 作る小窓の見た目と動き・詳しくの小窓の中身（見出しの 1 か所を除く）・「他 N 件」の小窓・仮の箱の動き
- `saveEvent` の送る中身（`frontend/src/pages/schedule/SchedulePageImpl.tsx:988-1031`）
- `tests/prod-check/`（本番の画面点検 S13 は変えない）
- backend・migrations・`.github/workflows/`・リポジトリ直下の `scripts/`・`frontend/scripts/`

## 2. 新しい金型 EditorPage

### 2-1. `frontend/src/components/EditorPage.tsx`

振る舞い（フォーカスを覚えて戻す・初めのフォーカス・Esc・`useFocusTrap`・portal）は `frontend/src/components/FullScreenDialog.tsx:44-84` の 4 つの useEffect と `useFocusTrap(open, dialogRef)` と `if (!open) return null;` を一字一句そのまま移す。違うのは口と描く中身だけ。

```tsx
/**
 * EditorPage 金型（予定の編集などの窓いっぱいの編集画面・ADR-144・ADR-1074）
 *
 * - 上の段: 左の列に ×・題名の欄（title）・右に丸い保存
 * - lead: 札の上・題名と同じ左端に置く中身（日時の段など）
 * - 札: cardTitle を頭に置き、中に EditorPageRow を並べる（絵の列は金型が持つ）
 * - Esc で閉じる（document で受けて stopPropagation。変換中の Esc は何もしない）
 * - フォーカストラップ・開いた時は initialFocusRef（無ければ最初の押せる物）へ・閉じたら元の要素へ
 * - role="dialog" / aria-modal / aria-label・document.body へ portal
 */
import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import ReactDOM from "react-dom";
import { Button } from "./Button";
import { X } from "../constants/icons-base";
import { useFocusTrap, getFirstFocusable } from "../hooks/useFocusTrap";
import "./EditorPage.css";

interface EditorPageProps {
  open: boolean;
  onClose: () => void;
  /** 読み上げの名前（t() の文字） */
  ariaLabel: string;
  /** × の読み上げ（t() の文字） */
  closeLabel: string;
  /** 上の段の題名の欄（金型 TextFieldControl variant="editor-title"） */
  title: ReactNode;
  /** 保存のボタンの文字（t() の文字） */
  saveLabel: string;
  onSave: () => void;
  saveDisabled?: boolean;
  /** 開いた時に最初にフォーカスする要素 */
  initialFocusRef?: RefObject<HTMLElement | null>;
  /** 札の上に置く中身 */
  lead?: ReactNode;
  /** 札の頭の文字（t() の文字） */
  cardTitle: string;
  /** 札の中の行（EditorPageRow） */
  children: ReactNode;
}

export function EditorPage({ open, onClose, ariaLabel, closeLabel, title, saveLabel, onSave, saveDisabled = false, initialFocusRef, lead, cardTitle, children }: EditorPageProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<Element | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  /* ここに FullScreenDialog.tsx:48-81 の 3 つの useEffect をそのまま移す */

  useFocusTrap(open, dialogRef);

  if (!open) return null;

  return ReactDOM.createPortal(
    <div ref={dialogRef} className="comp-editor-page" role="dialog" aria-modal="true" aria-label={ariaLabel}>
      <div className="comp-editor-page__header">
        <div className="comp-editor-page__rail">
          <Button variant="ghost" size="md" iconOnly aria-label={closeLabel} onClick={onClose}>
            <X size={20} />
          </Button>
        </div>
        <div className="comp-editor-page__title">{title}</div>
        <Button variant="primary" size="md" shape="pill" onClick={onSave} disabled={saveDisabled}>
          {saveLabel}
        </Button>
      </div>
      <div className="comp-editor-page__body">
        {lead != null && <div className="comp-editor-page__lead">{lead}</div>}
        <section className="comp-editor-page__card" aria-label={cardTitle}>
          <div className="comp-editor-page__card-head">
            <span className="comp-editor-page__card-title">{cardTitle}</span>
          </div>
          <div className="comp-editor-page__rows">{children}</div>
        </section>
      </div>
    </div>,
    document.body,
  );
}

/** 札の中の 1 行（1 列目: 絵・2 列目: 中身） */
export function EditorPageRow({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <div className="comp-editor-page__row">
      <span className="comp-editor-page__row-icon">{icon}</span>
      <div className="comp-editor-page__row-body">{children}</div>
    </div>
  );
}
```

- `Button` の口 `shape="pill"` は `frontend/src/components/Button.tsx:29` に在る（a7fbffdfe）。`:9` の説明「pill はログイン画面だけ」に「と金型 EditorPage の保存（ADR-1074）」を足す（`frontend/src/components/Button.tsx` を「触る」に含める）。

### 2-2. `frontend/src/components/EditorPage.css`

```css
/**
 * EditorPage 金型スタイル
 * 名前空間: .comp-editor-page-*
 * ADR-067: 色・寸法は var() のみ。寸法は Google の予定の編集画面の実測（schedule-gcal-clone recon §8.1）に合わせる
 */

.comp-editor-page {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  color: var(--text-primary);
  overflow-y: auto;
}

.comp-editor-page__header {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-5) var(--space-4) 0 var(--space-4);
}

.comp-editor-page__rail {
  display: flex;
  justify-content: center;
  width: var(--comp-editor-rail-w);
  margin-right: calc(-1 * var(--space-8));
  flex-shrink: 0;
}

.comp-editor-page__title {
  flex: 0 1 var(--comp-editor-title-w);
  min-width: 0;
}

.comp-editor-page__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-4) var(--space-8) var(--space-4);
}

.comp-editor-page__lead {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-left: var(--comp-editor-rail-w);
  width: min(calc(var(--comp-editor-main-w) + var(--space-4)), 100%);
  box-sizing: border-box;
}

.comp-editor-page__card {
  width: min(var(--comp-editor-main-w), 100%);
  box-sizing: border-box;
  padding: var(--space-1) 0 var(--space-4) 0;
  border-radius: var(--comp-editor-card-radius);
  background: var(--bg-surface);
}

.comp-editor-page__card-head {
  display: flex;
  align-items: center;
  min-height: var(--space-12);
  padding-left: var(--comp-editor-rail-w);
}

.comp-editor-page__card-title {
  display: inline-flex;
  align-items: center;
  min-height: var(--space-12);
  border-bottom: 2px solid var(--accent);
  font-size: var(--font-sm);
  font-weight: var(--font-weight-medium);
  color: var(--accent);
}

.comp-editor-page__rows {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-right: var(--space-4);
}

.comp-editor-page__row {
  display: flex;
  align-items: flex-start;
}

.comp-editor-page__row-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--comp-editor-rail-w);
  min-height: var(--space-10);
  flex-shrink: 0;
  color: var(--text-secondary);
}

.comp-editor-page__row-body {
  flex: 1;
  min-width: 0;
}

@media (max-width: 767px) {
  .comp-editor-page__header {
    gap: var(--space-2);
  }

  .comp-editor-page__rail {
    margin-right: 0;
    width: auto;
  }

  .comp-editor-page__title {
    flex: 1 1 auto;
  }

  .comp-editor-page__lead {
    padding-left: 0;
  }
}
```

- 位置の計算（窓 1279）: × の列は左 16（`--space-4`）から幅 64（`--comp-editor-rail-w`）で × の真ん中 x52。題名は 16+64=x80 から（列の右の `margin-right` で間の `--space-8` を打ち消す）。保存は題名 594 の後に間 32 で x706。札は x16 から幅 636。札の中の欄は 16+64=x80 から。
- 書いた後、本番と同じ窓で測った値が G60 から外れたら、余白のトークンだけを直す（外れた値と直した値を返しの報告に書く）。

### 2-3. `frontend/src/components/EditorPage.stories.tsx`

- 1 つの例「予定の編集」: `open` 真・題名の欄（`TextFieldControl variant="editor-title"`）・lead に `TextFieldControl variant="editor-filled" type="date"` 2 つ・札の中に `EditorPageRow` を 2 行（場所の欄 `editor-filled`・説明の `TextareaControl variant="editor-filled"`）。見本の文字は直書きでよい（見本帳の決まり）。

### 2-4. 古い金型を消す

- `git rm frontend/src/components/FullScreenDialog.tsx frontend/src/components/FullScreenDialog.css frontend/src/components/FullScreenDialog.stories.tsx frontend/src/components/FullScreenDialog.test.tsx`
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:1249` 前後のコメントの `FullScreenDialog` を `EditorPage` に替える。
- 終わりに `git grep -n FullScreenDialog -- frontend` が 0 件（コメントを含む）。

## 3. 塗りの欄の種類（金型 3 つ・G61）

- `frontend/src/components/TextField.tsx:35` の型に `"editor-filled" | "editor-title"` を足す。
- `frontend/src/components/Select.tsx:18` の型に `"editor-filled"` を足す。
- `frontend/src/components/Textarea.tsx:32` の型に `"editor-filled"` を足す。
- `frontend/src/components/FormField.css` の `comp-input--schedule-title` の規則（`:393-408`）の次に足す:

```css
/* editor-filled / editor-title: 編集の画面（金型 EditorPage）の欄。Google の予定の編集画面の実測（角 4px・枠なし・塗りの地・高さ 40）・ADR-1074 */
.comp-field__input.comp-input--editor-filled,
.comp-select__control.comp-select--editor-filled,
.comp-field__textarea.comp-textarea--editor-filled {
  min-height: var(--space-10);
  padding: 0 var(--space-4);
  border: none;
  border-radius: var(--radius-sm);
  background-color: var(--comp-input-filled-bg);
  font-family: revert;
  font-size: var(--font-sm);
  line-height: normal;
  transition: initial;
}

.comp-field__textarea.comp-textarea--editor-filled {
  padding: var(--space-2) var(--space-4);
}

.comp-field__input.comp-input--editor-filled:focus,
.comp-field__input.comp-input--editor-filled:focus-visible,
.comp-select__control.comp-select--editor-filled:focus,
.comp-select__control.comp-select--editor-filled:focus-visible,
.comp-field__textarea.comp-textarea--editor-filled:focus,
.comp-field__textarea.comp-textarea--editor-filled:focus-visible {
  border: none;
  box-shadow: inset 0 -2px 0 var(--accent);
  outline: none;
}

.comp-field__input.comp-input--editor-title {
  min-height: var(--space-10);
  padding: 0;
  border: none;
  border-bottom: 1px solid var(--border);
  border-radius: 0;
  background-color: transparent;
  font-size: var(--font-2xl);
  line-height: normal;
}

.comp-field__input.comp-input--editor-title:focus,
.comp-field__input.comp-input--editor-title:focus-visible {
  border-bottom: 2px solid var(--accent);
  box-shadow: none;
  outline: none;
}
```

- Select の矢印の印（indicator）は今の金型のまま（`padding-right` が矢印と重なるなら、`comp-select--karte`（`:201`）と同じ考えで右だけ広げる。重なりは見本帳で目で確かめる）。
- 3 つの金型の見本帳にそれぞれ 1 例（`editor-filled`・TextField は `editor-title` も）。

## 4. 項目の部品（`frontend/src/pages/schedule/ScheduleDraftFields.tsx`）

1 項目ずつの部品を同じファイルから出す。値を変える式は今の `ScheduleDraftFields`（`:114-269`）の式をそのまま各部品へ移す（式を 2 か所に書かない）。

共通の口:
```ts
type Appearance = "popover" | "page";
interface FieldProps {
  appearance: Appearance;
  mode: PopoverMode;
  draft: ScheduleDraft;
  onDraftChange: (next: ScheduleDraft) => void;
}
```

- `DraftDateFields`（口 `creating`・`expanded` は popover のときだけ使う）:
  - popover: 今の `:114-182` と同じ（Toggle・文字つき・閉じた 1 行）。
  - page: 1 段目 `<div className="schedule-editor-dates">` に 始まりの日（`editor-filled`・`type="date"`・`aria-label={t("schedule.eventStart")}`）・始まりの時刻（終日でないとき・`aria-label={`${t("schedule.eventStart")} ${t("schedule.time")}`}`）・`<span aria-hidden="true">{t("schedule.rangeSeparator")}</span>`・終わりの時刻（同じく `eventEnd`）・終わりの日（`eventEnd`）。2 段目に金型 `Checkbox`（`label={t("schedule.allDay")}`・`checked={draft.allDay}`・`onChange` は今の Toggle の式 `:121-126` と同じ中身）。
  - 始まりを変えたときの式: `mode === "create"` なら `shiftDraftStart`、そうでなければ値だけ替える（今の `creating` の分かれ方 `:137`・`:147` と同じ。作るは creating と mode=create が同じ）。
- `DraftCategoryField`: 今の `:184-208`。page のときは `SelectControl variant="editor-filled"`・`fullWidth`・`aria-label={t("schedule.category")}`・文字なし。
- `DraftMeetField`（口に `item: ScheduleItem | null`・`meetAvailable: boolean`）: 「Google Meet で参加」のリンク（今の `SchedulePageImpl.tsx:290-301` の式と `MEET_URL_PREFIX` `:96` をここへ移す）と、`meetAvailable && !item?.meetUrl` のときの `MeetRow`（`:44-72`）。page のときは `CreateRow` で包まない（行は呼ぶ側の `EditorPageRow`）。何も出さないときは `null` を返す。
- `DraftShareField`（`canChangeVisibility` が偽なら null）: 今の `:215-226` の Toggle のまま（page でも Toggle。Google に同じ項目が無いため）。
- `DraftLocationField`・`DraftDescriptionField`: 今の `:228-269`。page のときは `editor-filled`・文字なし・`aria-label` に今の文字のキー（`schedule.eventLocation`・`schedule.eventDescription`）・初めから開いた形。説明は `rows={8}`。
- `ScheduleDraftFields`（作る小窓が使う）は口を `mode`・`creating`・`expanded`・`item`・`draft`・`onDraftChange`・`canChangeVisibility`・`meetAvailable` にし（`joinMeetLink` を外す）、中で `appearance="popover"` の部品を今と同じ順（日時・種類・Meet・社員にも見せる・場所・説明）に並べるだけ。作る小窓の DOM は今と同じになる。

## 5. `frontend/src/pages/schedule/ScheduleFullEditor.tsx`

- 口に `mode: "create" | "edit"` と `item: ScheduleItem | null` を足す。
- `EditorPage` を使う: `ariaLabel={t("schedule.fullEditLabel")}`・`closeLabel={t("common.close")}`・`title` は今の題名の欄を `variant="editor-title"` に替えたもの（`ref={titleRef}`・`initialFocusRef={titleRef}` はそのまま）・`saveLabel={t("common.save")}`・`onSave={onSave}`・`saveDisabled={!draft.title.trim()}`・`cardTitle={t("schedule.eventDetail")}`。
- `lead`: `{error && <div className="schedule-error" role="alert">{error}</div>}` と `<DraftDateFields appearance="page" …/>`。
- 札の中（この順・G62）: `DraftMeetField`（null でないときだけ `EditorPageRow icon={Meet の絵}` で包む）→ `EditorPageRow`（場所の絵）`DraftLocationField` → `EditorPageRow`（種類の絵）`DraftCategoryField` → `canChangeVisibility` のとき `EditorPageRow`（共有の絵）`DraftShareField` → `EditorPageRow`（説明の絵）`DraftDescriptionField`。絵は `SCHEDULE_POPOVER_ICONS` の今のもの（`size={20}`・`aria-hidden="true"`）。
- `frontend/src/pages/schedule.css` の `:529-537` を次に置き換える:

```css
/* 編集の画面の日時の段（design §3.19・G60）。狭い窓では折り返す */
.schedule-editor-dates {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
```

## 6. トークン（G60・G61・G63）

- `frontend/src/tokens.css` の `--schedule-create-title-size`（`:414`）の次:
```css
  --comp-editor-rail-w:      4rem;     /* 編集の画面の絵の列の幅（64px・Google 実測: 絵の真ん中 x48・欄 x80・ADR-1074） */
  --comp-editor-title-w:     37.125rem; /* 編集の画面の題名の欄の幅（594px・Google 実測） */
  --comp-editor-main-w:      39.75rem; /* 編集の画面の札の幅（636px・Google 実測） */
  --comp-editor-card-radius: 1.75rem;  /* 編集の画面の札の角（28px・Google 実測） */
```
- `frontend/src/index.css` の明るい表示（`--link-active-bg` `:37` の次）に `--comp-input-filled-bg: var(--link-active-bg);  /* 編集の画面の塗りの欄の地（Google 実測 rgb(233,238,246) に最も近い既存の色・ADR-1074） */`、暗い表示（`:242` の次）に `--comp-input-filled-bg: var(--bg-subtle);  /* 暗い札 --bg-surface の上で見える地 */`。
- PR 本文の「デザイントークン変更時」の点検を ✅ にする（`check-new-tokens.js`）。

## 7. 予定の画面（`frontend/src/pages/schedule/SchedulePageImpl.tsx`）

1. `openEdit`（`:975-982`）: 今の `setPopover({ … mode: "edit" … })` の後に `setError(null);` と `setFullEditOpen(true);`。
2. 閉じる useEffect（`:1132-1134`）の条件を `if (popover === null || popover.mode === "detail") setFullEditOpen(false);` に。
3. `ScheduleFullEditor`（`:1587-`）: `open={fullEditOpen && (popover?.mode === "create" || popover?.mode === "edit")}`・`mode={popover?.mode === "edit" ? "edit" : "create"}`・`item={popover?.item ?? null}`・`onClose={() => { setFullEditOpen(false); setError(null); if (popover?.mode === "edit") setPopover(null); }}`。
4. 小窓（`SchedulePopover`）の直す形を消す: `:311` の見出しは `t("schedule.eventDetail")` だけに・`:394-404` の文字つきの題名の枝・`:432-440` の `mode !== "detail"` の下の段（保存・取り消し）。小窓の本体（`:380-418`）は作るときだけ描く形になる。`ScheduleDraftFields` へ渡していた `joinMeetLink`（`:417`）を外す。詳しくの中身（`:358`）は今と同じリンクを出し続けるが、リンクの宛先を決める式（`:290`・`MEET_URL_PREFIX` `:96`）は `ScheduleDraftFields.tsx` から出す関数 `meetJoinUrl(item: ScheduleItem | null): string | null` 1 つに移し、詳しくの小窓と `DraftMeetField` の両方がそれを呼ぶ（式を 2 か所に書かない）。
5. 詳しくの小窓の鉛筆の絵（`:322-330`）と下の「予定を編集」のボタン（`:441` 以降）は今と同じく `openEdit` を呼ぶ（変えない）。
6. 近道の判定（`:1249-1250`）は `fullEditOpen` だけを見ている（a7fbffdfe で確かめた）ので変えない。直すときも `fullEditOpen` が真になるので近道は効かない。コメントの金型の名前だけ `EditorPage` に替える。

## 8. 守り手と決まりの文書

- `frontend/src/components/buttonShapeUsage.test.ts` の `ALLOWED`（`:13-19`）に `"components/EditorPage.tsx"`・`"components/EditorPage.stories.tsx"`・`"components/EditorPage.test.tsx"` を足す。
- 新しい `frontend/src/components/editorVariantUsage.test.ts`: `buttonShapeUsage.test.ts` と同じ作り（src の .tsx を全部読み、使ってよい場所の外で見つけたら落ちる）。探す形は `/["']editor-(?:filled|title)["']/`。使ってよい場所: `components/TextField.tsx`・`components/Select.tsx`・`components/Textarea.tsx`・`components/TextField.stories.tsx`・`components/Select.stories.tsx`・`components/Textarea.stories.tsx`・`components/EditorPage.stories.tsx`・`components/EditorPage.test.tsx`・`pages/schedule/ScheduleDraftFields.tsx`・`pages/schedule/ScheduleFullEditor.tsx`・`pages/schedule/SchedulePageImpl.test.tsx`・`pages/design-preview/`。試験の中に「今 1 件以上見つかる」ことも書く（探し方が壊れて 0 件で通るのを防ぐ）。
- `docs/specs/design-system/design.md`: `:262` と `:276`（丸いボタンはログインだけ）の後に「例外: 金型 EditorPage の保存（ADR-1074）」、`:811`（入力欄は完全に丸い）の後に「例外: 金型 EditorPage の中の欄は種類 `editor-filled`（角 `--radius-sm`・塗りの地・ADR-1074）。使う場所は `frontend/src/components/editorVariantUsage.test.ts` が止める」を 1 文ずつ。

## 9. 試験

### 9-1. `frontend/src/components/EditorPage.test.tsx`（新規）

- `frontend/src/components/FullScreenDialog.test.tsx` の F1〜F7 を名前と描く物だけ EditorPage に替えて移す（確かめる中身は変えない）。
- 足す: E1 保存を押すと `onSave` が 1 回／E2 `saveDisabled` で保存が押せない／E3 `lead`・`cardTitle`（札の `aria-label` と文字）・`EditorPageRow` の絵と中身が出る。

### 9-2. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`

- 今の直すの試験（`:171`・`:183`・`:507-547`・`:571-590`・`:1009`（T7）・`:1054`・`:1163`・`:1175`）: 「予定を編集」を押した後に探す場所を、名前「予定の編集」の dialog の中に替える。確かめる中身（送る宛先・中身・見え方）は変えない。題名の欄は `schedule.eventTitle` の名前で探す。
- 全画面の試験（`:760-884`）: 札の中の並びに合わせて探し方だけ替える。
- 足す:
  - H1 直すから開くと dialog が出て、題名の欄がその予定の題名・`.schedule-popover` が 0 個。
  - H2 直すから開いて × で閉じると dialog も小窓も 0 個で、`fetch` の PATCH・POST が 0 回。Esc でも同じ。
  - H3 直すの保存で PATCH が `/calendar/events/<数字>` へ 1 回・成功で dialog が閉じる。失敗（500）では dialog が開いたままで `role="alert"` が dialog の中に在る。
  - H4 札の中の並び: Meet（出るとき）→場所→種類→社員にも見せる→説明（DOM の順）。
  - H5 編集画面の終日は `role="checkbox"`（名前「終日」）で、`role="switch"`（名前「終日」）が 0 個。作る小窓では今どおり switch。

## 10. 文言（ADR-027）

- `frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の `schedule` の中に `"rangeSeparator"`: ja「〜」・en「–」。ほかのキーは足さない・替えない。

## 11. 終わりの確かめと返し方

- §0 の 3 つの確かめが 0 件の失敗。`git grep -n FullScreenDialog -- frontend` が 0 件。`git diff --stat origin/main...HEAD` が §1 の「触る」の中だけ。
- 返す: `DONE` と commit の sha・確かめの生出力の置き場所、または `BLOCKED:`／`NEEDS_DECISION:` と理由。
