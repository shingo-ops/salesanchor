import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import "../i18n";
import { Drawer } from "./Drawer";

// CSS はテスト環境で空に差し替わるため、ファイルを直接読む
const drawerCss = readFileSync(resolve(process.cwd(), "src/components/Drawer.css"), "utf8");
const tokensCss = readFileSync(resolve(process.cwd(), "src/tokens.css"), "utf8");

afterEach(cleanup);

const panel = () => screen.getByTestId("supplier-drawer");

describe("Drawer size", () => {
  it("has no wide class by default", () => {
    render(<Drawer open onClose={() => undefined} title="T">x</Drawer>);
    expect(panel().className).not.toContain("comp-drawer-panel--wide");
  });

  it("adds the wide class when size is wide", () => {
    render(<Drawer open onClose={() => undefined} title="T" size="wide">x</Drawer>);
    expect(panel().className).toContain("comp-drawer-panel--wide");
  });

  it("keeps the default width at 480px through the token", () => {
    expect(tokensCss).toMatch(/--drawer-panel-w-default:\s*480px/);
    expect(drawerCss).toMatch(/width:\s*var\(--drawer-panel-w-default\)/);
  });

  it("defines the wide width from the xwide modal token", () => {
    expect(tokensCss).toMatch(/--drawer-panel-w-wide:\s*var\(--modal-xwide-w\)/);
  });
});

describe("Drawer onBack (A19・design.md 4-1)", () => {
  it("does not render drawer-back when onBack is omitted (default unchanged)", () => {
    render(<Drawer open onClose={() => undefined} title="T">x</Drawer>);
    expect(screen.queryByTestId("drawer-back")).toBeNull();
  });

  it("renders drawer-back to the left of the title when onBack is given", () => {
    render(
      <Drawer open onClose={() => undefined} title="T" onBack={() => undefined} backLabel="Back">
        x
      </Drawer>,
    );
    const back = screen.getByTestId("drawer-back");
    expect(back).toBeTruthy();
    expect(back.getAttribute("aria-label")).toBe("Back");
  });

  it("calls onBack, not onClose, when the back button is clicked", () => {
    const onBack = vi.fn();
    const onClose = vi.fn();
    render(
      <Drawer open onClose={onClose} title="T" onBack={onBack} backLabel="Back">
        x
      </Drawer>,
    );
    fireEvent.click(screen.getByTestId("drawer-back"));
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });
});

describe("Drawer mobileInset (docs/handoff/viewer-filter-choices-mercari/design.md 4-1)", () => {
  it("U3: does not add comp-drawer-panel--mobile-inset when mobileInset is omitted (default unchanged)", () => {
    render(<Drawer open onClose={() => undefined} title="T">x</Drawer>);
    expect(panel().className).not.toContain("comp-drawer-panel--mobile-inset");
  });

  it("U4: adds comp-drawer-panel--mobile-inset when mobileInset is true", () => {
    render(<Drawer open onClose={() => undefined} title="T" mobileInset>x</Drawer>);
    expect(panel().className).toContain("comp-drawer-panel--mobile-inset");
  });
});

describe("Drawer onEscape (design.md 4-4)", () => {
  it("calls onEscape, not onClose, on Escape when onEscape is given", () => {
    const onClose = vi.fn();
    const onEscape = vi.fn();
    render(
      <Drawer open onClose={onClose} title="T" onEscape={onEscape}>
        x
      </Drawer>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onEscape).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("falls back to onClose on Escape when onEscape is omitted (default unchanged)", () => {
    const onClose = vi.fn();
    render(<Drawer open onClose={onClose} title="T">x</Drawer>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("the close (X) button still calls onClose even when onEscape is given", () => {
    const onClose = vi.fn();
    const onEscape = vi.fn();
    render(
      <Drawer open onClose={onClose} title="T" onEscape={onEscape}>
        x
      </Drawer>,
    );
    fireEvent.click(screen.getByTestId("drawer-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onEscape).not.toHaveBeenCalled();
  });
});
