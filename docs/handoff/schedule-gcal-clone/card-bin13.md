# 実装カード 便13: Google Meet を押す行に・「その他のオプション」で全画面の編集（G51〜G57）（2026-11-11）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2.6（G51〜G57）・§3.18（審査は §9 の 16 回目・3 回目 APPROVE）
- PO の承認: PO の選択「1」（2026-11-11・「この形で作り、本番に出す」）。新しい金型 `FullScreenDialog` 1 つ（ADR-144）もこの承認に含む。
- 土台: ブランチ `release/schedule-gcal-full-edit-design`（055884ead＝origin/main 8d2c7e1b4 を合流済み）。このブランチの上にそのまま積む（設計・カード・実装を 1 つの PR にする。便12 #5337 と同じ形）。
- 対象 ADR: ADR-144（金型）・ADR-067（トークン）・ADR-027（i18n）・ADR-073（見本帳）・ADR-1060（Meet は保存のときに作る・外す操作は作らない）
- 行番号はすべて 055884ead の値。違っていたら中身で場所を探し、見つからなければ止める。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。設計 §3.18 とこのカードが食い違ったら止める。
- 色・寸法は var() だけ（px・色・rem の直書き禁止。新しいトークンも足さない）。UI の文字は t() だけ（見本帳の中の見本の文字は除く）。
- 確かめはクラウドの作業場所で回す: `cd frontend && npx vitest run src/components/FullScreenDialog.test.tsx src/components/Modal.test.tsx src/pages/schedule/`・`npx tsc --noEmit`・`npm run check:all`。全部 0 件の失敗になるまで直す。
- 試験が落ちたら直してよいのは §8 に書いた試験だけ。ほかの試験が落ちたら止めて返す。
- commit は `git add` に触ったファイルを名前で並べる（`git add -A`・`git add .` は使わない）。push は `git push origin release/schedule-gcal-full-edit-design`（force・rebase・amend は禁止）。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/components/FullScreenDialog.tsx`（新規） | 金型（§2） |
| `frontend/src/components/FullScreenDialog.css`（新規） | 金型の見た目（§2） |
| `frontend/src/components/FullScreenDialog.stories.tsx`（新規） | 見本帳（§2） |
| `frontend/src/components/FullScreenDialog.test.tsx`（新規） | §8 |
| `frontend/src/pages/schedule/ScheduleDraftFields.tsx`（新規） | 項目の部品と `MeetRow`（§3） |
| `frontend/src/pages/schedule/ScheduleFullEditor.tsx`（新規） | 全画面の編集（§4） |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | §5 |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | §8 |
| `frontend/src/pages/schedule.css` | 規則 4 つ（§6） |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | キー 1 つ替え・3 つ足し（§7） |
| `.claude-pipeline/active-work.d/release-schedule-gcal-full-edit-design.md` | 台帳の状態（無ければ作らない） |

触らない（変えたら差し戻し）:
- 金型 `Modal`・`Sheet`・`Drawer`・`Button`・`Toggle`・`TextField`・`CalendarView` と `frontend/src/hooks/useFocusTrap.ts`
- `frontend/src/tokens.css`・`frontend/src/constants/icons.tsx`（絵は今ある `SCHEDULE_POPOVER_ICONS.meet`・`.close` を使う）
- 詳しく見る小窓の中身・直す小窓の並び（Meet の行の置き換えだけ）・「他 N 件」の小窓・仮の箱の動き
- `saveEvent` の送る中身（`add_meet` の条件 `:1201` を含む）
- backend・migrations・`.github/workflows/`・リポジトリ直下の `scripts/`・`frontend/scripts/`

## 2. 新しい金型 FullScreenDialog

### 2-1. `frontend/src/components/FullScreenDialog.tsx`

```tsx
/**
 * FullScreenDialog 金型（窓いっぱいの入れ物・ADR-144・PO 2026-11-11 許可）
 *
 * - 一番上の帯: 左に ×・真ん中に title（中身は呼ぶ側）・右に actions
 * - Esc で閉じる（document で受けて stopPropagation。変換中の Esc は何もしない）
 * - フォーカストラップ（useFocusTrap）・開いた時は initialFocusRef（無ければ最初の押せる物）へ
 * - 閉じたら開く前の要素がまだ画面に在ればそこへ戻す
 * - role="dialog" / aria-modal / aria-label・document.body へ portal
 */
import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import ReactDOM from "react-dom";
import { Button } from "./Button";
import { X } from "../constants/icons-base";
import { useFocusTrap, getFirstFocusable } from "../hooks/useFocusTrap";
import "./FullScreenDialog.css";

interface FullScreenDialogProps {
  open: boolean;
  onClose: () => void;
  /** 読み上げの名前（t() の文字） */
  ariaLabel: string;
  /** × の読み上げ（t() の文字） */
  closeLabel: string;
  /** 一番上の帯の真ん中に置く中身 */
  title?: ReactNode;
  /** 一番上の帯の右に置く中身（保存のボタンなど） */
  actions?: ReactNode;
  /** 開いた時に最初にフォーカスする要素 */
  initialFocusRef?: RefObject<HTMLElement | null>;
  children: ReactNode;
}

export function FullScreenDialog({
  open,
  onClose,
  ariaLabel,
  closeLabel,
  title,
  actions,
  initialFocusRef,
  children,
}: FullScreenDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<Element | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  /* フォーカス: 開く直前の要素を覚え、閉じたらまだ画面に在る時だけ戻す */
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement;
      return;
    }
    const el = triggerRef.current;
    triggerRef.current = null;
    if (el instanceof HTMLElement && el.isConnected) el.focus();
  }, [open]);

  /* 開いたら initialFocusRef（無ければ最初の押せる物）へ */
  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const target = initialFocusRef?.current ?? getFirstFocusable(dialog);
    target?.focus();
  }, [open, initialFocusRef]);

  /* Esc で閉じる。変換中（isComposing・keyCode 229）は何もしない */
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (event.isComposing || event.keyCode === 229) return;
      event.stopPropagation();
      onCloseRef.current();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  useFocusTrap(open, dialogRef);

  if (!open) return null;

  return ReactDOM.createPortal(
    <div
      ref={dialogRef}
      className="comp-fullscreen-dialog"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
    >
      <div className="comp-fullscreen-dialog__header">
        <Button variant="ghost" size="md" iconOnly aria-label={closeLabel} onClick={onClose}>
          <X size={20} />
        </Button>
        <div className="comp-fullscreen-dialog__title">{title}</div>
        {actions != null && <div className="comp-fullscreen-dialog__actions">{actions}</div>}
      </div>
      <div className="comp-fullscreen-dialog__body">
        <div className="comp-fullscreen-dialog__content">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
```

注意: `useFocusTrap` の引数の型が `RefObject<HTMLDivElement | null>` と合わずに `tsc` が落ちたら、`Modal.tsx:85` と同じ渡し方（`useFocusTrap(open, dialogRef)`）なので型は合うはず。合わなければ止めて返す（hook は変えない）。

### 2-2. `frontend/src/components/FullScreenDialog.css`

```css
/**
 * FullScreenDialog 金型スタイル
 * 名前空間: .comp-fullscreen-dialog-*
 * ADR-067: 色・寸法は var() のみ（新しいトークンは足さない）
 */

.comp-fullscreen-dialog {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  color: var(--text-primary);
}

.comp-fullscreen-dialog__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: var(--topbar-height);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.comp-fullscreen-dialog__title {
  flex: 1;
  min-width: 0;
}

.comp-fullscreen-dialog__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.comp-fullscreen-dialog__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-6) var(--space-4);
}

.comp-fullscreen-dialog__content {
  width: min(var(--modal-wide-w), 100%);
  margin: 0 auto;
}
```

`1px` は `Modal.css` の `border-bottom: 1px solid var(--border-subtle)` と同じ書き方。`npm run check:css-values` が `1px` を止めたら、止めた文を写して `NEEDS_DECISION:` で返す（自分でトークンを作らない）。

### 2-3. `frontend/src/components/FullScreenDialog.stories.tsx`

`Sheet.stories.tsx` と同じ形（`title: 'Components/FullScreenDialog'`・`parameters.layout: 'fullscreen'`・`docs: { disable: true }`・`tags: []`）。物語は 1 つ `Default`（名前 `'open — 窓いっぱいの編集（× で閉じる）'`）: 開くボタン 1 つ、開くと `title` に金型 `TextFieldControl`（variant `"schedule-title"`・`aria-label="題名"`）、`actions` に金型 `Button`（primary・「保存」・押すと閉じる）、中身に文 2 行。インラインの style を書くときは `var()` だけ（`'2rem'` などの直書きは使わない）。生の `<button>` ではなく金型 `Button` を使う。

## 3. 項目の部品 `frontend/src/pages/schedule/ScheduleDraftFields.tsx`（新規）

`SchedulePageImpl.tsx` の作る小窓・直す小窓の項目（日時と終日 `:445-513`・種類 `:515-539`・Meet の参加リンク `:541`・Meet `:542-553`・社員にも見せる `:555-566`・場所 `:568-587`・説明 `:589-609`）を、そのままこの部品へ移す。題名（`:419-443`）と足の帯（`:613-`）は小窓に残す。

### 3-1. 型を外へ出す（SchedulePageImpl.tsx 側）

- `SchedulePageImpl.tsx:83-96` の `interface ScheduleDraft` を `export interface ScheduleDraft` にする（中身は変えない。`addMeet` のコメントだけ「Google Meet の行を押した印（保存時に add_meet として送る）」に替える）。
- `:218` の `function CreateRow` を `ScheduleDraftFields.tsx` へ移す（中身は変えない・`SchedulePageImpl.tsx` からは消す）。
- `type PopoverMode` は `SchedulePageImpl.tsx:81` のまま `export type PopoverMode` にする。
- 部品は `import type { ScheduleDraft, PopoverMode } from "./SchedulePageImpl"` で型だけ読む（`import type` なので循環は実行時に起きない）。`ScheduleItem` は `./schedule-utils`（`schedule-utils.ts:49`）から型で読む。`shiftDraftStart`（`schedule-utils.ts:298`）・`formatDraftDateLine`（`:102`）も `./schedule-utils` から読む。`CALENDARS`・`CalendarId` は `SchedulePageImpl.tsx` と同じ所（`../../features/schedule/calendars.config`）から読む。

### 3-2. 部品の口

```tsx
export function ScheduleDraftFields({
  mode,
  creating,
  expanded,
  item,
  draft,
  onDraftChange,
  canChangeVisibility,
  meetAvailable,
  joinMeetLink,
}: {
  mode: PopoverMode;
  /** 作る形（1 列目に絵を置く行で並べる） */
  creating: boolean;
  /** 真なら日時・場所・説明を初めから開いた形で出す（全画面の編集） */
  expanded: boolean;
  item: ScheduleItem | null;
  draft: ScheduleDraft;
  onDraftChange: (next: ScheduleDraft) => void;
  canChangeVisibility: boolean;
  meetAvailable: boolean;
  /** 小窓が作った「Google Meet で参加」のリンク（無ければ null）。作り方は小窓の 1 か所のまま */
  joinMeetLink: ReactNode;
})
```

- 部品の中で `const [dateOpen, setDateOpen] = useState(false)`・`locationOpen`・`descriptionOpen` を持つ（`:298-300` から移す）。`showDate = !creating || expanded || dateOpen`・`showLocation = !creating || expanded || locationOpen || draft.location !== ""`・`showDescription = !creating || expanded || descriptionOpen || draft.description !== ""`。
- 場所・説明の `autoFocus` は今と同じ `locationOpen`・`descriptionOpen`（expanded の時は偽のまま＝勝手にフォーカスを取らない）。
- 参加リンク `joinMeetLink`（`:328-340`）は小窓に残す（詳しく見る形の `:395` でも使う）。部品へは口 `joinMeetLink` で渡し、今の `:541` の場所に `{joinMeetLink}` を置く。
- 絵は `SCHEDULE_POPOVER_ICONS` から部品の中で取る（clock・category・meet・share・location・description・close）。`Toggle`・`SelectControl`・`TextareaControl`・`TextFieldControl`・`Button` は今の import と同じ所から読む。
- 返すのは今の並び順のまま `<>…</>`（日時→種類→参加リンク→Meet→社員にも見せる→場所→説明）。

### 3-3. Meet の行 `MeetRow`（G51・G52。今の `:542-553` の Toggle を置き換える）

同じファイルに置く:

```tsx
function MeetRow({
  creating,
  addMeet,
  onChange,
}: {
  creating: boolean;
  addMeet: boolean;
  onChange: (next: boolean) => void;
}) {
  const { t } = useTranslation();
  const MeetIcon = SCHEDULE_POPOVER_ICONS.meet;
  const CloseIcon = SCHEDULE_POPOVER_ICONS.close;
  return (
    <CreateRow creating={creating} icon={<MeetIcon size={20} aria-hidden="true" />}>
      {addMeet ? (
        <div className="schedule-meet-row">
          <span className="schedule-meet-row__text">{t("schedule.meetPending")}</span>
          <Button variant="ghost" size="sm" iconOnly aria-label={t("schedule.removeMeet")} onClick={() => onChange(false)}>
            <CloseIcon size={16} aria-hidden="true" />
          </Button>
        </div>
      ) : (
        <Button variant="ghost" size="md" fullWidth layoutClassName="schedule-popover__line" onClick={() => onChange(true)}>
          <span className="schedule-popover__line-text">{t("schedule.addMeet")}</span>
        </Button>
      )}
    </CreateRow>
  );
}
```

部品の中での使い方（今の `:542-553` の場所）:

```tsx
{meetAvailable && !item?.meetUrl && (
  <MeetRow creating={creating} addMeet={draft.addMeet} onChange={(next) => onDraftChange({ ...draft, addMeet: next })} />
)}
```

- 出す条件 `meetAvailable && !item?.meetUrl` は今と同じ。直す小窓（`creating` が偽）では `CreateRow` が中身だけを出すので、行はボタン 1 つ（または文と ×）になる。
- 種類の欄の `mode === "create"` の分かれ（`:525-529`）は `mode` を使って今のまま。部品の中の `creating ? shiftDraftStart(…) : {…}`（`:470`・`:481`）も今のまま。

### 3-4. 小窓（SchedulePopover）側の置き換え

- `:445-609` を `<ScheduleDraftFields mode={mode} creating={creating} expanded={false} item={item} draft={draft} onDraftChange={onDraftChange} canChangeVisibility={canChangeVisibility} meetAvailable={meetAvailable} joinMeetLink={joinMeetLink} />` 1 つにする。
- 小窓から消すもの: `dateOpen`・`locationOpen`・`descriptionOpen`・`showDate`・`showLocation`・`showDescription`（`:298-303`）・使わなくなった絵の変数（`ClockIcon`・`LocationIcon`・`DescriptionIcon`・`CategoryIcon`・`MeetIcon`・`ShareIcon`）。`CloseIcon`・`EditIcon`・`DeleteIcon` は見出しで使うので残す。`tsc` と lint の「使っていない」を 0 にする。
- 使わなくなった import（`Toggle`・`SelectControl`・`TextareaControl` など）は、`SchedulePageImpl.tsx` の他の場所で使っていなければ消す（`grep -n "<Toggle\|<SelectControl\|<TextareaControl\|CheckboxControl" SchedulePageImpl.tsx` で確かめる）。

## 4. 全画面の編集 `frontend/src/pages/schedule/ScheduleFullEditor.tsx`（新規・G53〜G55）

```tsx
export function ScheduleFullEditor({
  open,
  draft,
  onDraftChange,
  onClose,
  onSave,
  error,
  canChangeVisibility,
  meetAvailable,
}: {
  open: boolean;
  draft: ScheduleDraft;
  onDraftChange: (next: ScheduleDraft) => void;
  onClose: () => void;
  onSave: () => void;
  /** 保存に失敗した文（無ければ null） */
  error: string | null;
  canChangeVisibility: boolean;
  meetAvailable: boolean;
}) {
  const { t } = useTranslation();
  const titleRef = useRef<HTMLInputElement | null>(null);
  return (
    <FullScreenDialog
      open={open}
      onClose={onClose}
      ariaLabel={t("schedule.fullEditLabel")}
      closeLabel={t("common.close")}
      initialFocusRef={titleRef}
      title={
        <TextFieldControl
          variant="schedule-title"
          value={draft.title}
          onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
          placeholder={t("schedule.addTitle")}
          aria-label={t("schedule.eventTitle")}
          ref={titleRef}
        />
      }
      actions={
        <Button variant="primary" onClick={onSave} disabled={!draft.title.trim()}>
          {t("common.save")}
        </Button>
      }
    >
      <div className="schedule-full-editor">
        {error && <div className="schedule-error" role="alert">{error}</div>}
        <ScheduleDraftFields
          mode="create"
          creating
          expanded
          item={null}
          draft={draft}
          onDraftChange={onDraftChange}
          canChangeVisibility={canChangeVisibility}
          meetAvailable={meetAvailable}
          joinMeetLink={null}
        />
      </div>
    </FullScreenDialog>
  );
}
```

- `TextFieldControl` の `ref` の型が合わなければ、小窓の題名（`:428`）と同じ渡し方に合わせる。

## 5. 予定の画面につなぐ（`SchedulePageImpl.tsx`）

### 5-1. 状態（`:1033` の `draft` の次の行）

```tsx
  // 作る小窓の「その他のオプション」で開く全画面の編集（design §3.18 作り方 4）。下書きは draft 1 つのまま
  const [fullEditOpen, setFullEditOpen] = useState(false);
```

### 5-2. Meet を出してよいかを 1 つの変数に（`:1766-1773` の式を移す）

`canChangeVisibility`（`:1303`）の次に置く:

```tsx
  // 小窓と全画面の編集の両方に渡す（式を 2 か所に書かない・design §3.18 作り方 4）
  const popoverMeetAvailable = meetAvailable && popover !== null && (
    popover.mode === "create"
    || Boolean(popover.item && popover.item.ownerUserId === currentOwnerUserId && popover.item.googleEventId)
  );
```

`<SchedulePopover … meetAvailable={…}>`（`:1766-1773`）は `meetAvailable={popoverMeetAvailable}` にする。`saveEvent` の中の `meetAvailable`（`:1201`）は変えない。

### 5-3. 全画面を閉じる道（`:1318-1320` の効き目の次）

```tsx
  // 作る小窓でなくなったら（保存・閉じる・詳しく見る）全画面の編集も閉じる
  useEffect(() => {
    if (popover?.mode !== "create") setFullEditOpen(false);
  }, [popover]);
```

### 5-4. `saveEvent`（`:1186-1228`）

成功の道の `setError(null);`（`:1219`）の次に `setFullEditOpen(false);` を 1 行足す。それ以外は変えない。

### 5-5. 近道のキー（`:1434` の中・`:1436` の `if (event.isComposing …) return;` の前）

```tsx
    // 0. 全画面の編集が開いている間は何もしない（Esc は金型 FullScreenDialog が先に受ける・G56）
    if (fullEditOpen) return;
```

### 5-6. 小窓の「その他のオプション」

- `SchedulePopover` の口に `onMoreOptions: () => void` を足す（型の欄にも足す）。
- 足の帯の作る形の「その他のオプション」（`:616-627`）を次にする（いつも出す・押すと全画面を開く）。続く「保存」（`:628-630`）は今のまま:

```tsx
              <Button variant="ghost" onClick={onMoreOptions}>
                {t("schedule.moreOptions")}
              </Button>
```

- ページ側で `onMoreOptions={() => { setError(null); setFullEditOpen(true); }}` を渡す。

### 5-7. 描く所（`:1752-1775`）

```tsx
      {popover && !fullEditOpen && (
        <SchedulePopover
          …今のまま…
          meetAvailable={popoverMeetAvailable}
          onMoreOptions={() => { setError(null); setFullEditOpen(true); }}
        />
      )}

      <ScheduleFullEditor
        open={fullEditOpen && popover?.mode === "create"}
        draft={draft}
        onDraftChange={setDraft}
        onClose={() => { setFullEditOpen(false); setError(null); }}
        onSave={saveEvent}
        error={error}
        canChangeVisibility={canChangeVisibility}
        meetAvailable={popoverMeetAvailable}
      />
```

- 全画面の間も `popover` は残るので、仮の箱（`pendingVisible`・`:1318-1320`）と下書きは残る。閉じると小窓が同じ `popover.anchor` で描き直され、`placed` で題名の欄へフォーカスが移る（`:304-307`・G56）。

## 6. `frontend/src/pages/schedule.css`（`.schedule-create-row > :not(.schedule-create-row__icon)` の規則 `:510-512` の次に足す）

```css
/* Google Meet の行（design §3.18 作り方 1・G51）。押した後は文と × を横に並べる */
.schedule-meet-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.schedule-meet-row__text {
  flex: 1;
  min-width: 0;
  color: var(--text-primary);
}

/* 全画面の編集（design §3.18 作り方 4・G53）。項目は作る小窓と同じ行の形で縦に並べる */
.schedule-full-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.schedule-full-editor .schedule-popover__line {
  justify-content: flex-start;
}
```

## 7. 文言（ADR-027）

`frontend/src/locales/ja.json`・`en.json` の `schedule` の中:

| キー | ja | en |
|---|---|---|
| `addMeet`（`:3351` の文を替える） | Google Meet のビデオ会議を追加 | Add Google Meet video conferencing |
| `meetPending`（新規・`addMeet` の次） | Google Meet のビデオ会議（保存すると参加用のリンクができます） | Google Meet video conferencing (the join link is created when you save) |
| `removeMeet`（新規） | Google Meet を外す | Remove Google Meet |
| `fullEditLabel`（新規） | 予定の編集 | Edit event |

## 8. 試験

### 8-1. `frontend/src/components/FullScreenDialog.test.tsx`（新規）

`Modal.test.tsx` の書き方に合わせる。1 本ずつ:
1. `open` で `role="dialog"` が出て `aria-modal="true"`・`aria-label` が渡した文。`open={false}` で無い。
2. × を押すと `onClose` が 1 回。
3. Esc（`fireEvent.keyDown(document, { key: "Escape" })`）で `onClose` が 1 回。window に付けた keydown の受け手が呼ばれない（stopPropagation）。
4. 変換中の Esc（`{ key: "Escape", isComposing: true }` と `{ key: "Escape", keyCode: 229 }`）では `onClose` が呼ばれない。
5. 開くと `initialFocusRef` の要素にフォーカス。渡さなければ最初の押せる物（×）。
6. 最後の押せる物で Tab を押すと最初へ戻る（`Modal.test.tsx` に Tab の試験があればその形を写す。無ければ `useFocusTrap` の試験の形を写す）。
7. 開く前にフォーカスしていたボタンへ、閉じた後に戻る。開く前の要素を画面から消してから閉じると、フォーカスは移らず例外も出ない。

### 8-2. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`

Meet の試験（`:436-557`）を読み替える:
- `screen.findByRole("switch", { name: addMeetLabel() })` → `screen.findByRole("button", { name: addMeetLabel() })`。`queryByRole("switch", …)` → `queryByRole("button", …)`。
- `:472-474` の `toggle.checked` の確かめは消し、押した後に `screen.getByText(i18n.t("schedule.meetPending"))` と `screen.getByRole("button", { name: i18n.t("schedule.removeMeet") })` が在ることに替える。
- 試験の名前の "toggle" は "Meet row" に替える（中身の意味は同じ）。

足す試験（同じ `describe` の中・`enableMeet()` を使う）:
1. 作る小窓で Meet の行を押してから × を押すと、元の行に戻り（`addMeetLabel()` のボタンが在る）、保存の POST に `add_meet` が無い。
2. 作る小窓・直す小窓（自分の Google の予定で Meet 無し）・全画面の編集の 3 か所で `screen.queryByRole("switch", { name: /Google Meet/ })` が null。

「その他のオプション」の試験（`:726-738`）を書き替える（名前 "the footer has more options then save and no cancel; more options opens the full editor"）:
- 足の帯のボタンの並びが `[moreOptions, save]`・取り消しが無い（今のまま）。
- 題名に「試し」を入れてから「その他のオプション」を押すと、`screen.getByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })` が在る。その中の題名の欄の値が「試し」・始まりの日付と時刻の欄の値が小窓の下書きと同じ・場所と説明の欄が在る。`.schedule-popover` は無い。

全画面の編集の試験（`describe("SchedulePage full editor (G53-G56)")` を新しく足す。作る小窓を開く手順は上の試験と同じ `openTimed` を使う）:
1. × で dialog が消え、`.schedule-popover` が在り、題名が「試し」のまま、仮の箱（`pendingOf()`）が在る。その間 `api.post`・`api.patch` が 0 回。
2. Esc でも 1 と同じ。
3. dialog の「保存」で `api.post` が 1 回、送った中身が、同じ下書きを小窓の「保存」で送った時と同じ（`title`・`start_datetime`・`end_datetime`・`is_all_day`・`category`）。成功で dialog も `.schedule-popover` も無い。
4. `api.post` を `mockRejectedValueOnce(new Error("boom"))` にして dialog の「保存」を押すと、dialog が在り、`within(dialog).getByText("boom")` が在る。続けて × で閉じると、`.schedule-error` に "boom" が無い。
5. dialog が開いた状態で `fireEvent.keyDown(document.body, { key: "m" })`（今の近道の試験 `:793` と同じ送り方）を送っても表示が月に変わらない（今の近道の試験が見ている印で確かめる）。
6. × で閉じた後、`await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText(i18n.t("schedule.eventTitle"))))`。
7. 変換中の Esc（`fireEvent.keyDown(document, { key: "Escape", isComposing: true })`）で dialog が残る。

## 9. 終わりの確かめと返し方

- `cd frontend && npx vitest run src/components/FullScreenDialog.test.tsx src/components/Modal.test.tsx src/pages/schedule/`・`npx tsc --noEmit`・`npm run check:all` の結果の最後の行を返す（全部の失敗 0）。
- `git diff --stat origin/main...HEAD` を返す。§1 の「触る」以外のファイルが出たら止める（設計の文書 `docs/handoff/schedule-gcal-clone/` は除く）。
- 最後の行は `DONE <commit の sha>` か `BLOCKED: <理由>` か `NEEDS_DECISION: <聞くこと>`。
