/**
 * Popover.test.tsx — Popover 金型の位置計算（design.md §⑤ C1〜C7・C16）
 *
 * jsdom はレイアウトを持たないため、offsetWidth/offsetHeight（パネルの大きさ）・
 * トリガーの getBoundingClientRect・window.innerWidth/innerHeight・
 * window.scrollX/scrollY をこのファイル側で差し替えて測る
 * （frontend/src/components/MultiSelect.test.tsx の render/fireEvent による
 * 書き方に倣う。offsetWidth 等の差し替えは本ファイルが初出）。
 *
 * RED-first（C16）: この spec は直す前のコード（window.scrollY/scrollX を
 * 足し、画面内に収めず、resize/scroll で測り直さない）に対して書き、
 * 赤いことを確認した記録を docs/handoff/popover-mold-fix/design.md ⑤ C16 の下に残す。
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Popover, type PopoverPlacement } from "./Popover";

afterEach(cleanup);

const PANEL_W = 200;
const PANEL_H = 100;
const GAP = 6; // px — Popover.tsx の gap と同値
const MARGIN = 8; // px — 画面端との最低間隔（ContextMenu.tsx:82 と同値）

interface RectInput {
  top: number;
  left: number;
  width: number;
  height: number;
}

function makeRect(r: RectInput): DOMRect {
  return {
    top: r.top,
    left: r.left,
    width: r.width,
    height: r.height,
    bottom: r.top + r.height,
    right: r.left + r.width,
    x: r.left,
    y: r.top,
    toJSON: () => ({}),
  } as DOMRect;
}

function stubTriggerRect(el: Element, r: RectInput): void {
  el.getBoundingClientRect = () => makeRect(r);
}

function stubViewport(innerWidth: number, innerHeight: number): void {
  Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: innerWidth });
  Object.defineProperty(window, "innerHeight", { configurable: true, writable: true, value: innerHeight });
}

function stubScroll(scrollX: number, scrollY: number): void {
  Object.defineProperty(window, "scrollX", { configurable: true, writable: true, value: scrollX });
  Object.defineProperty(window, "scrollY", { configurable: true, writable: true, value: scrollY });
}

beforeEach(() => {
  // パネルの大きさは offsetWidth/offsetHeight から読む（jsdom は常に0を返すため差し替える）
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, get: () => PANEL_W });
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: () => PANEL_H });
  // 既定のビューポート・スクロール位置（各テストで上書きする）
  stubViewport(1024, 768);
  stubScroll(0, 0);
  // requestAnimationFrame を同期化する（visible のフェードインを待たずに済ませる）
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback): number => {
    cb(0);
    return 0;
  });
});

/** Popover をレンダリングし、トリガー（span）と開いているパネルを返す */
function setup(
  placement: PopoverPlacement = "bottom",
): { trigger: HTMLElement; rerenderOpen: (open: boolean, p?: PopoverPlacement) => void; panel: () => HTMLElement } {
  function Wrapper({ open, p }: { open: boolean; p: PopoverPlacement }) {
    return (
      <Popover open={open} onOpenChange={() => {}} placement={p} content={<div>content</div>}>
        <button type="button" data-testid="trigger">
          trigger
        </button>
      </Popover>
    );
  }
  const { rerender } = render(<Wrapper open={false} p={placement} />);
  const button = document.querySelector('[data-testid="trigger"]') as HTMLElement;
  const trigger = button.parentElement as HTMLElement; // Popover.tsx: triggerRef は children を包む span
  return {
    trigger,
    rerenderOpen: (open, p = placement) => rerender(<Wrapper open={open} p={p} />),
    panel: () => document.querySelector(".comp-popover") as HTMLElement,
  };
}

function panelPos(panel: HTMLElement): { top: number; left: number } {
  return { top: parseFloat(panel.style.top), left: parseFloat(panel.style.left) };
}

// スクロール分を足さない（design.md 4-1・C1・C7）
describe("Popover calcPosition - does not add window.scrollX/scrollY", () => {
  // triggerRect.bottom(330) + gap(6) = 336。scrollY(400) を足すと 736 になってしまう（旧バグ）。
  it("C1: top is 6px below the trigger bottom after scrolling 400px (scrollY not added)", () => {
    stubScroll(0, 400);
    const { trigger, rerenderOpen, panel } = setup("bottom");
    stubTriggerRect(trigger, { top: 300, left: 400, width: 80, height: 30 });

    rerenderOpen(true);

    const pos = panelPos(panel());
    expect(pos.top).toBe(330 + GAP);
  });

  it("C7: placement=top does not add scrollY/scrollX", () => {
    stubScroll(50, 400);
    const { trigger, rerenderOpen, panel } = setup("top");
    stubTriggerRect(trigger, { top: 300, left: 400, width: 80, height: 30 });

    rerenderOpen(true);

    const pos = panelPos(panel());
    expect(pos.top).toBe(300 - PANEL_H - GAP);
    expect(pos.left).toBe(400 + 40 - PANEL_W / 2);
  });

  it("C7: placement=left does not add scrollY/scrollX", () => {
    stubScroll(50, 400);
    const { trigger, rerenderOpen, panel } = setup("left");
    stubTriggerRect(trigger, { top: 300, left: 400, width: 80, height: 30 });

    rerenderOpen(true);

    const pos = panelPos(panel());
    expect(pos.top).toBe(300 + 15 - PANEL_H / 2);
    expect(pos.left).toBe(400 - PANEL_W - GAP);
  });

  it("C7: placement=right does not add scrollY/scrollX", () => {
    stubScroll(50, 400);
    const { trigger, rerenderOpen, panel } = setup("right");
    stubTriggerRect(trigger, { top: 300, left: 400, width: 80, height: 30 });

    rerenderOpen(true);

    const pos = panelPos(panel());
    expect(pos.top).toBe(300 + 15 - PANEL_H / 2);
    expect(pos.left).toBe(480 + GAP);
  });
});

// 画面内に収める（design.md 4-2・C2・C3）
describe("Popover calcPosition - clamps inside the viewport", () => {
  it("C2: left >= 8 at viewport width 360 for a trigger near the left edge", () => {
    stubViewport(360, 800);
    const { trigger, rerenderOpen, panel } = setup("bottom");
    stubTriggerRect(trigger, { top: 100, left: 2, width: 20, height: 20 });

    rerenderOpen(true);

    const pos = panelPos(panel());
    expect(pos.left).toBeGreaterThanOrEqual(MARGIN);
  });

  it("C3: right <= viewport width - 8 for a trigger near the right edge", () => {
    stubViewport(360, 800);
    const { trigger, rerenderOpen, panel } = setup("bottom");
    stubTriggerRect(trigger, { top: 100, left: 340, width: 20, height: 20 });

    rerenderOpen(true);

    const pos = panelPos(panel());
    expect(pos.left + PANEL_W).toBeLessThanOrEqual(360 - MARGIN);
  });
});

// 開いている間は測り直す（design.md 4-4・C5・C6）
describe("Popover - remeasures while open", () => {
  it("C5: follows the trigger's new position on scroll", () => {
    const { trigger, rerenderOpen, panel } = setup("bottom");
    stubTriggerRect(trigger, { top: 300, left: 400, width: 80, height: 30 });
    rerenderOpen(true);
    expect(panelPos(panel()).top).toBe(330 + GAP);

    // ページがスクロールし、ボタンが画面内で 200px 上に動いたとみなす
    stubTriggerRect(trigger, { top: 100, left: 400, width: 80, height: 30 });
    fireEvent(window, new Event("scroll"));

    expect(panelPos(panel()).top).toBe(130 + GAP);
  });

  it("C6: remeasures on resize", () => {
    stubViewport(360, 800);
    const { trigger, rerenderOpen, panel } = setup("bottom");
    stubTriggerRect(trigger, { top: 100, left: 340, width: 20, height: 20 });
    rerenderOpen(true);
    expect(panelPos(panel()).left + PANEL_W).toBeLessThanOrEqual(360 - MARGIN);

    // 画面がさらに狭くなった
    stubViewport(300, 800);
    fireEvent(window, new Event("resize"));

    expect(panelPos(panel()).left + PANEL_W).toBeLessThanOrEqual(300 - MARGIN);
  });

  it("cleans up the resize/scroll subscriptions on close (no timers)", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { trigger, rerenderOpen } = setup("bottom");
    stubTriggerRect(trigger, { top: 300, left: 400, width: 80, height: 30 });
    rerenderOpen(true);
    rerenderOpen(false);

    expect(removeSpy.mock.calls.some(([type]) => type === "scroll")).toBe(true);
    expect(removeSpy.mock.calls.some(([type]) => type === "resize")).toBe(true);
  });
});
