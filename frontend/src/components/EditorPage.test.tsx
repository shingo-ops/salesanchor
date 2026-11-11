/**
 * EditorPage.test.tsx — 金型 EditorPage の振る舞い（ADR-144・ADR-1074・card-bin14 §9-1）
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import "../i18n";
import { getFocusableElements } from "../hooks/useFocusTrap";
import { EditorPage, EditorPageRow } from "./EditorPage";

afterEach(cleanup);

const BASE = {
  title: <input aria-label="Title" />,
  saveLabel: "Save",
  onSave: () => undefined,
  cardTitle: "Details",
};

function renderDialog(props: Partial<Parameters<typeof EditorPage>[0]> = {}) {
  return render(
    <EditorPage open onClose={() => undefined} ariaLabel="Edit" closeLabel="Close" {...BASE} {...props}>
      <button data-testid="inner">inner</button>
    </EditorPage>,
  );
}

describe("EditorPage", () => {
  it("F1: renders role=dialog with aria-modal and aria-label when open, nothing when closed", () => {
    const { rerender } = renderDialog();
    const dialog = screen.getByRole("dialog", { name: "Edit" });
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    rerender(
      <EditorPage open={false} onClose={() => undefined} ariaLabel="Edit" closeLabel="Close" {...BASE}>
        x
      </EditorPage>,
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
      <EditorPage open onClose={() => undefined} ariaLabel="Edit" closeLabel="Close" initialFocusRef={ref} {...BASE}>
        <input ref={ref} data-testid="init" />
      </EditorPage>,
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
      <EditorPage open={false} onClose={() => undefined} ariaLabel="Edit" closeLabel="Close" {...BASE}>
        x
      </EditorPage>,
    );
    const el = (open: boolean) => (
      <EditorPage open={open} onClose={() => undefined} ariaLabel="Edit" closeLabel="Close" {...BASE}>
        x
      </EditorPage>
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

  it("E1: clicking save calls onSave once", () => {
    const onSave = vi.fn();
    renderDialog({ onSave });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it("E2: saveDisabled makes the save button not clickable", () => {
    const onSave = vi.fn();
    renderDialog({ onSave, saveDisabled: true });
    const save = screen.getByRole("button", { name: "Save" });
    expect((save as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(save);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("E3: renders lead, the card (aria-label and title) and EditorPageRow icon and body", () => {
    render(
      <EditorPage open onClose={() => undefined} ariaLabel="Edit" closeLabel="Close" {...BASE} lead={<p data-testid="lead">lead</p>}>
        <EditorPageRow icon={<svg data-testid="row-icon" />}>
          <span data-testid="row-body">body</span>
        </EditorPageRow>
      </EditorPage>,
    );
    expect(screen.getByTestId("lead")).toBeTruthy();
    const card = screen.getByRole("region", { name: "Details" });
    expect(card.textContent).toContain("Details");
    expect(card.contains(screen.getByTestId("row-icon"))).toBe(true);
    expect(card.contains(screen.getByTestId("row-body"))).toBe(true);
  });
});
