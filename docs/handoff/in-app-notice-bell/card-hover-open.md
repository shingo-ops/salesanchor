# 実装カード: PC の鈴はマウスを乗せると一覧が開く（design.md §7-3-改訂6）

- 設計: docs/handoff/in-app-notice-bell/design.md §7-3-改訂6（Architect 自己審査 APPROVE）
- PO 承認: 「鈴をクリックしたら開く→カーソルを合わせたら開くに変更できる？」（2026-11-04）／離れたときは「1」（離して少し経つと自動で閉じる、2026-11-04）
- ブランチ: release/notice-bell-hover-open（origin/main 8d661d747 から）
- 触ってよいファイル（この 5 つと報告書 docs/handoff/in-app-notice-bell/impl-report-hover-open.md だけ）:
  - frontend/src/components/Popover.tsx
  - frontend/src/components/NoticeBell.tsx
  - frontend/src/components/Popover.test.tsx
  - frontend/src/components/Popover.stories.tsx
  - frontend/tests-e2e/visual-language/notice-bell.spec.ts
- 触らない: Popover の位置の計算（`calcPosition` と位置を測る useEffect）・Popover.css・NoticeBell.css・MultiSelect・tokens.css・i18n（ja.json / en.json）・backend・openapi.json。スマホの形（NoticeBell.tsx の `variant === "tab"` の分岐）は 1 文字も変えない

## §1 frontend/src/components/Popover.tsx

(1) 冒頭の説明書き（:1-9）の「- open / onOpenChange による制御式 API」の次の行に足す:

```ts
 * - openOnHover: マウスを乗せると開き、離れて少し経つと閉じる（押しても開ける。既定は false）
```

(2) `PopoverProps`（:23-36）の `className?: string;` の後に足す:

```ts
  /** true のとき、マウスを乗せると開き、離れて hoverCloseDelay ms 経つと閉じる（押しても開ける） */
  openOnHover?: boolean;
  /** 乗せてから開くまでの ms（デフォルト: 150。Tooltip・HoverCard と同じ） */
  hoverOpenDelay?: number;
  /** 離れてから閉じるまでの ms（デフォルト: 300。鈴と一覧の間を動く間に閉じないため） */
  hoverCloseDelay?: number;
```

(3) 関数の引数（:85-92）を次にする:

```ts
export function Popover({
  children,
  content,
  placement = "bottom",
  open: controlledOpen,
  onOpenChange,
  className = "",
  openOnHover = false,
  hoverOpenDelay = 150,
  hoverCloseDelay = 300,
}: PopoverProps) {
```

(4) `setOpen` の useCallback（:102-108）の直後に足す:

```ts
  // 乗せて開く（openOnHover）。待ちの時計は 1 つだけ持つ
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const openedByHoverRef = useRef(false);

  const clearHoverTimer = useCallback(() => {
    if (hoverTimerRef.current !== null) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
  }, []);

  const handleHoverEnter = useCallback(() => {
    if (!openOnHover) return;
    clearHoverTimer();
    if (isOpen) return;
    hoverTimerRef.current = setTimeout(() => {
      hoverTimerRef.current = null;
      openedByHoverRef.current = true;
      setOpen(true);
    }, hoverOpenDelay);
  }, [openOnHover, clearHoverTimer, isOpen, hoverOpenDelay, setOpen]);

  const handleHoverLeave = useCallback(() => {
    if (!openOnHover) return;
    clearHoverTimer();
    if (!isOpen) return;
    hoverTimerRef.current = setTimeout(() => {
      hoverTimerRef.current = null;
      setOpen(false);
    }, hoverCloseDelay);
  }, [openOnHover, clearHoverTimer, isOpen, hoverCloseDelay, setOpen]);

  // 閉じたら「乗せて開いた」印を消す。部品が消えるときは待ちの時計を止める
  useEffect(() => {
    if (!isOpen) openedByHoverRef.current = false;
  }, [isOpen]);
  useEffect(() => () => clearHoverTimer(), [clearHoverTimer]);
```

(5) `handleTriggerClick`（:151）を次にする:

```ts
  const handleTriggerClick = () => {
    clearHoverTimer();
    // 乗せて開いた直後の 1 回目の押しでは閉じない（乗せて開いたのに押すと閉じる食い違いを防ぐ）
    if (openOnHover && isOpen && openedByHoverRef.current) {
      openedByHoverRef.current = false;
      return;
    }
    openedByHoverRef.current = false;
    setOpen(!isOpen);
  };
```

(6) トリガーの `<span>`（:163-170）に 2 つ足す（他は変えない）:

```tsx
      <span
        ref={triggerRef}
        className={className || undefined}
        style={{ display: "inline-flex" }}
        onClick={handleTriggerClick}
        onMouseEnter={handleHoverEnter}
        onMouseLeave={handleHoverLeave}
      >
```

(7) パネルの `<div>`（:174-179）に 2 つ足す（他は変えない）:

```tsx
          <div
            ref={panelRef}
            className={panelCls}
            role="dialog"
            style={{ top: pos.top, left: pos.left }}
            onMouseEnter={handleHoverEnter}
            onMouseLeave={handleHoverLeave}
          >
```

## §2 frontend/src/components/NoticeBell.tsx（2 か所だけ）

- :44 変更前: `  /** "floating" = 右上の丸い鈴（PC）。"tab" = スマホの下のタブの 1 つ */`
- :44 変更後: `  /** "floating" = 右上の鈴（PC。マウスを乗せると開く）。"tab" = スマホの下のタブの 1 つ */`
- :141 変更前: `    <Popover placement="bottom" open={open} onOpenChange={handleOpenChange} content={content}>`
- :141 変更後: `    <Popover placement="bottom" openOnHover open={open} onOpenChange={handleOpenChange} content={content}>`

## §3 frontend/src/components/Popover.test.tsx（末尾に describe を 1 つ足す）

既存の `setup` は使わず、この describe の中で `onOpenChange` を記録する制御式の包みを作る。`vi.useFakeTimers()` を describe の beforeEach、`vi.useRealTimers()` を afterEach で呼ぶ。`fireEvent.mouseEnter` / `fireEvent.mouseLeave` / `fireEvent.click` と `act(() => vi.advanceTimersByTime(n))` を使う（`act` は `@testing-library/react` から import を足す）。足す it は次の 6 つ:

1. openOnHover: 乗せて 149ms では開かず、150ms で開く（`.comp-popover` が出る）
2. openOnHover: 開いたあとトリガーから出て 299ms ではまだ開いていて、300ms で閉じる
3. openOnHover: トリガーから出て 300ms 以内にパネルに入ると閉じない（さらに 1000ms 進めても開いたまま）
4. openOnHover: 乗せて開いた直後にトリガーを押しても閉じない。もう一度押すと閉じる
5. openOnHover: 乗せて 150ms 経つ前に押すと開き、そのあと時計を進めても開いたまま（開閉が二重にならない）
6. openOnHover が無いとき: 乗せて 1000ms 進めても開かない（今までどおり押したときだけ）

包みの例（この形で書く）:

```tsx
function HoverHarness({ openOnHover = true }: { openOnHover?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen} openOnHover={openOnHover} content={<div>content</div>}>
      <button type="button" data-testid="hover-trigger">
        trigger
      </button>
    </Popover>
  );
}
```

（`useState` は `react` から import を足す。トリガーの span は `button.parentElement`。パネルは `document.querySelector(".comp-popover")`）

## §4 frontend/src/components/Popover.stories.tsx（末尾に 1 つ足す）

```tsx
// ── 乗せて開く（openOnHover）────────────────────────────────────────────
export const OpenOnHover: Story = {
  args: {
    content: <SampleContent />,
    placement: "bottom",
    openOnHover: true,
  },
  render: (args) => (
    <Popover {...args}>
      <button type="button">乗せると開く</button>
    </Popover>
  ),
};
```

## §5 frontend/tests-e2e/visual-language/notice-bell.spec.ts（末尾の `test.describe` の中、最後の test の後に 1 つ足す）

```ts
  test("PC: 押さずに乗せるだけで一覧が開き、一覧へ動かしても開いたまま、外へ出すと閉じる", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "vl-desktop-1280", "1280 のみ");
    await setup(page, 3);
    const btn = page.locator(".notice-bell-btn");
    await expect(btn).toBeVisible({ timeout: 10_000 });
    const panel = page.locator(".notice-panel");
    await expect(panel).toHaveCount(0);
    await btn.hover();
    await expect(panel).toBeVisible();
    await page.locator(".notice-row").first().hover();
    await page.waitForTimeout(500);
    await expect(panel).toBeVisible();
    await page.mouse.move(10, 700);
    await expect(panel).toHaveCount(0);
  });
```

## 想定される分岐（推測で埋めず止まる）

- 変更前の Popover.tsx / NoticeBell.tsx の行が上と一致しない（行番号のずれ以上の違い）→ NEEDS_DECISION:
- 既存の e2e（K1・K3・0 件・スマホ）が、乗せて開く待ちと押しの重なりで落ちる → 待ち時間や押しの扱いを自分で変えず NEEDS_DECISION:（落ちた試験名と最後の数行を報告書に書く）
- 追加の e2e で `page.mouse.move(10, 700)` の位置が別の部品の上で閉じない → 位置を変えてよいのは「鈴と一覧の外」の範囲だけ。変えた座標と理由を報告書に書く
- 色・寸法の直値（#xxx・px）を書きたくなった → 書かずに NEEDS_DECISION:
- lint の react-hooks 規則で依存配列の指摘が出る → 指摘どおり依存を足してよい。動きを変える書き換えはしない

## 確かめ（Mac では流さない。クラウドで流す）

1. `cd frontend && npm ci`
2. `npx vitest run src/components/Popover.test.tsx src/components/MultiSelect.test.tsx`
3. `npx playwright test tests-e2e/visual-language/notice-bell.spec.ts --project=vl-desktop-1280 --project=vl-mobile-390`（ブラウザが無ければ `npx playwright install chromium` を先に。入れられなければ流せなかったと書く）
4. `npm run lint` → `npx tsc --noEmit`
5. リポジトリ直下で `bash scripts/dev/check-before-submit.sh`

報告書 docs/handoff/in-app-notice-bell/impl-report-hover-open.md に、各確かめの最後の数行の生出力・変えたファイルと行数・最終 HEAD・DONE / BLOCKED: / NEEDS_DECISION: のどれかを書く。
