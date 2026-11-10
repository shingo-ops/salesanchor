/**
 * FullScreenDialog.test.tsx — 金型 FullScreenDialog の振る舞い（ADR-144・card-bin13 §8-1）
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import "../i18n";
import { getFocusableElements } from "../hooks/useFocusTrap";
import { FullScreenDialog } from "./FullScreenDialog";

afterEach(cleanup);

function renderDialog(props: Partial<Parameters<typeof FullScreenDialog>[0]> = {}) {
  return render(
    <FullScreenDialog open onClose={() => undefined} ariaLabel="Edit" closeLabel="Close" {...props}>
      <button data-testid="inner">inner</button>
    </FullScreenDialog>,
  );
}

describe("FullScreenDialog", () => {
  it("F1: renders role=dialog with aria-modal and aria-label when open, nothing when closed", () => {
    const { rerender } = renderDialog();
    const dialog = screen.getByRole("dialog", { name: "Edit" });
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    rerender(
      <FullScreenDialog open={false} onClose={() => undefined} ariaLabel="Edit" closeLabel="Close">
        x
      </FullScreenDialog>,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("F2: clicking the close button calls onClose once", () => {
    const onClose = vi.fn();
    renderDialog({ onClose });
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("F3: Escape calls onClose once and stops propagation to window listeners", () => {
    const onClose = vi.fn();
    const windowListener = vi.fn();
    window.addEventListener("keydown", windowListener);
    renderDialog({ onClose });
    fireEvent.keyDown(document, { key: "Escape" });
    window.removeEventListener("keydown", windowListener);
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(windowListener).not.toHaveBeenCalled();
  });

  it("F4: Escape during IME composition does nothing", () => {
    const onClose = vi.fn();
    renderDialog({ onClose });
    fireEvent.keyDown(document, { key: "Escape", isComposing: true });
    fireEvent.keyDown(document, { key: "Escape", keyCode: 229 });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("F5: focuses initialFocusRef when given, otherwise the first focusable (close button)", () => {
    const ref = createRef<HTMLInputElement>();
    const first = render(
      <FullScreenDialog open onClose={() => undefined} ariaLabel="Edit" closeLabel="Close" initialFocusRef={ref}>
        <input ref={ref} data-testid="init" />
      </FullScreenDialog>,
    );
    expect(document.activeElement).toBe(screen.getByTestId("init"));
    first.unmount();
    renderDialog();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Close" }));
  });

  it("F6: Tab at the last focusable wraps to the first", () => {
    renderDialog();
    const focusable = getFocusableElements(screen.getByRole("dialog"));
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(first);
  });

  it("F7: returns focus to the opener on close; no move and no error if the opener is gone", () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const { rerender } = render(
      <FullScreenDialog open={false} onClose={() => undefined} ariaLabel="Edit" closeLabel="Close">
        x
      </FullScreenDialog>,
    );
    const el = (open: boolean) => (
      <FullScreenDialog open={open} onClose={() => undefined} ariaLabel="Edit" closeLabel="Close">
        x
      </FullScreenDialog>
    );
    rerender(el(true));
    expect(document.activeElement).not.toBe(opener);
    rerender(el(false));
    expect(document.activeElement).toBe(opener);

    rerender(el(true));
    opener.remove();
    expect(() => rerender(el(false))).not.toThrow();
    expect(document.activeElement).toBe(document.body);
  });
});
