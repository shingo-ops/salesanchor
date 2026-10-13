import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
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
