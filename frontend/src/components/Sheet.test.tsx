/**
 * Sheet.test.tsx — 宿題 E4 の単体テスト（design.md 4-2 S1〜S7）
 *
 * 製品コードは1行も変えない。ここで固定するのは Sheet の「今の振る舞い」
 * （中身の残存・開閉クラス・オーバーレイの有無・読み上げ名・Esc・フッタの有無）。
 * 共通の仕掛け（出口封じ・閉じている間の無効化）は useFocusTrap.test.tsx が担当する。
 *
 * Sheet は portalTarget を useEffect で後から決める2段構え（design.md 4-1）。
 * open=true の状態を見るテストは open=false で描いてから open=true へ rerender する
 * （useFocusTrap.test.tsx の openMold と同じ理由）。
 */
import { cleanup, fireEvent, render, screen, type RenderResult } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactElement } from "react";
import "../i18n";
import { Sheet } from "./Sheet";

afterEach(cleanup);

const panel = () => screen.getByTestId("sheet-panel");
const overlay = () => document.querySelector(".comp-sheet-overlay");

function sheet(open: boolean, onClose: () => void, extra?: { footer?: ReactElement }): ReactElement {
  return (
    <Sheet open={open} onClose={onClose} title="My Title" footer={extra?.footer}>
      x
    </Sheet>
  );
}

/** open=false で描いてから open=true へ差し替える（コメント参照） */
function openSheet(onClose: () => void, extra?: { footer?: ReactElement }): RenderResult {
  const result = render(sheet(false, onClose, extra));
  result.rerender(sheet(true, onClose, extra));
  return result;
}

describe("Sheet", () => {
  it("S1: keeps the panel in the DOM when open is false, without the --open class", () => {
    render(sheet(false, () => undefined));
    expect(panel()).toBeTruthy();
    expect(panel().className).not.toContain("comp-sheet-panel--open");
  });

  it("S2: adds the --open class when open is true", () => {
    openSheet(() => undefined);
    expect(panel().className).toContain("comp-sheet-panel--open");
  });

  it("S3: has no overlay when open is false, and has one when open is true", () => {
    render(sheet(false, () => undefined));
    expect(overlay()).toBeNull();

    openSheet(() => undefined);
    expect(overlay()).not.toBeNull();
  });

  it("S4: clicking the overlay calls onClose", () => {
    const onClose = vi.fn();
    openSheet(onClose);
    fireEvent.click(overlay() as Element);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("S5: clicking the close (X) button calls onClose once", () => {
    const onClose = vi.fn();
    openSheet(onClose);
    fireEvent.click(screen.getByTestId("sheet-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("S6: pressing Escape calls onClose", () => {
    const onClose = vi.fn();
    openSheet(onClose);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("S7: the accessible name matches the title, and the footer renders only when given", () => {
    openSheet(() => undefined);
    expect(panel().getAttribute("aria-modal")).toBe("true");
    expect(screen.getByRole("dialog", { name: "My Title" })).toBe(panel());
    expect(document.querySelector(".comp-sheet-footer")).toBeNull();
    cleanup();

    openSheet(() => undefined, { footer: <span>F</span> });
    expect(document.querySelector(".comp-sheet-footer")).not.toBeNull();
  });

  it("S8: moves focus to the first focusable element inside the panel when opened", () => {
    openSheet(() => undefined);
    expect(document.activeElement).toBe(screen.getByTestId("sheet-close"));
  });

  it("S9: restores focus to the previously focused element after closing", () => {
    // Sheet は portalTarget を後から決める2段構え：
    // open=false で描く → 外側ボタンに focus() → open=true へ rerender → open=false へ rerender
    function Wrapper({ open }: { open: boolean }) {
      return (
        <div>
          <button>Outer</button>
          {sheet(open, () => undefined)}
        </div>
      );
    }
    const { rerender } = render(<Wrapper open={false} />);
    const outer = screen.getByRole("button", { name: "Outer" });
    outer.focus();
    rerender(<Wrapper open={true} />);
    rerender(<Wrapper open={false} />);
    expect(document.activeElement).toBe(outer);
  });
});
