/**
 * Modal.test.tsx — 宿題 E4 の単体テスト（design.md 4-2 M1〜M10）
 *
 * 製品コードは1行も変えない。ここで固定するのは Modal の「今の振る舞い」
 * （開閉・読み上げ名・大きさ・背景クリック・Esc・フッタの有無）。
 * 共通の仕掛け（出口封じ・閉じている間の無効化）は useFocusTrap.test.tsx が担当する。
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import { Modal } from "./Modal";

afterEach(cleanup);

// ✕ の読み上げ名は辞書の common.close 由来（design.md 4-1）。日本語リテラルを書かずに辞書から取る。
const closeLabel = i18n.t("common.close");

describe("Modal", () => {
  it("M1: renders nothing when open is false", () => {
    render(
      <Modal open={false} onClose={() => undefined} title="T">
        x
      </Modal>,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("M2: renders role=dialog, aria-modal=true and an accessible name matching the title when open", () => {
    render(
      <Modal open onClose={() => undefined} title="My Title">
        x
      </Modal>,
    );
    const dialog = screen.getByRole("dialog", { name: "My Title" });
    expect(dialog.getAttribute("aria-modal")).toBe("true");
  });

  it("M3: defaults to the md size (comp-modal-dialog--md)", () => {
    render(
      <Modal open onClose={() => undefined} title="T">
        x
      </Modal>,
    );
    expect(screen.getByRole("dialog").className).toContain("comp-modal-dialog--md");
  });

  it("M4: applies the lg size class when size=\"lg\"", () => {
    render(
      <Modal open onClose={() => undefined} title="T" size="lg">
        x
      </Modal>,
    );
    expect(screen.getByRole("dialog").className).toContain("comp-modal-dialog--lg");
  });

  it("M5: clicking the close (X) button calls onClose once", () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="T">
        x
      </Modal>,
    );
    fireEvent.click(screen.getByRole("button", { name: closeLabel }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("M6: clicking the overlay calls onClose by default", () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="T">
        x
      </Modal>,
    );
    fireEvent.click(screen.getByRole("dialog").parentElement as HTMLElement);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("M7: clicking the overlay does not call onClose when dismissOnOverlay is false", () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="T" dismissOnOverlay={false}>
        x
      </Modal>,
    );
    fireEvent.click(screen.getByRole("dialog").parentElement as HTMLElement);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("M8: clicking inside the dialog body does not call onClose", () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="T">
        x
      </Modal>,
    );
    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("M9: pressing Escape calls onClose", () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="T">
        x
      </Modal>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("M10: renders the footer only when the footer prop is given", () => {
    const { rerender } = render(
      <Modal open onClose={() => undefined} title="T">
        x
      </Modal>,
    );
    expect(document.querySelector(".comp-modal-footer")).toBeNull();

    rerender(
      <Modal open onClose={() => undefined} title="T" footer={<span>F</span>}>
        x
      </Modal>,
    );
    expect(document.querySelector(".comp-modal-footer")).not.toBeNull();
  });

  it('M11: applies the xl size class when size="xl"', () => {
    render(
      <Modal open onClose={() => undefined} title="T" size="xl">
        x
      </Modal>,
    );
    expect(screen.getByRole("dialog").className).toContain("comp-modal-dialog--xl");
  });

  it("M12: moves focus to the first focusable element inside the dialog when opened", () => {
    render(
      <Modal open onClose={() => undefined} title="T">
        x
      </Modal>,
    );
    expect(document.activeElement).toBe(screen.getByRole("button", { name: closeLabel }));
  });

  it("M13: restores focus to the previously focused element after closing", () => {
    // 外側ボタン＋Modal を同じ木に描き、rerender で open だけ切り替える（外側ボタンは作り直されない）
    function Wrapper({ open }: { open: boolean }) {
      return (
        <div>
          <button>Outer</button>
          <Modal open={open} onClose={() => undefined} title="T">
            x
          </Modal>
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
