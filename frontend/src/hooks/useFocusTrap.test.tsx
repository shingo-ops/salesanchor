/**
 * useFocusTrap.test.tsx — 宿題 C8 の単体テスト（design.md ⑤ C1〜C8・C11）
 *
 * RED-first: 直す前（Drawer/Modal/Sheet が自前の出口封じを持つ状態）は C2・C3 が赤になる
 * （docs/handoff/viewer-focus-trap/design.md ⑤。手順は「先にテストを書いて走らせる→赤を記録→実装→緑」）。
 *
 * 金型のマウント方法について: Drawer/Sheet は portalTarget を useEffect で解決する
 * （SSR 回避のための2段階マウント。design.md 4-4 の境界外・既存の作り）。open=true のまま
 * 最初からマウントすると、ポータル解決後の再コミットで `[open]` 依存の effect が
 * （値が変わらないため）再実行されず、Tab トラップが一度も有効化されない。実アプリでは
 * 必ず open=false → true の順で props が変わるため、ここでも同じ順で開く
 * （`openMold`）。C6（open=false のまま）はこの手順を使わない。
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import type { ReactElement } from "react";
import "../i18n";
import { Drawer } from "../components/Drawer";
import { Modal } from "../components/Modal";
import { Sheet } from "../components/Sheet";
import { getFocusableElements } from "./useFocusTrap";

afterEach(cleanup);

/** 中にフォーカス可能要素を持つ行（row-a・row-b）を描く children */
function rows(ids: string[]) {
  return ids.map((r) => (
    <button key={r} data-testid={`row-${r}`}>{r}</button>
  ));
}

interface MoldCase {
  name: string;
  /** open の値を渡して JSX を作る（openMold で false→true の順に rerender する） */
  element: (open: boolean, ids: string[]) => ReactElement;
  panel: () => HTMLElement;
}

const molds: MoldCase[] = [
  {
    name: "Drawer",
    element: (open, ids) => (
      <Drawer open={open} onClose={() => undefined} title="T">
        {rows(ids)}
      </Drawer>
    ),
    panel: () => screen.getByTestId("supplier-drawer"),
  },
  {
    name: "Modal",
    element: (open, ids) => (
      <Modal open={open} onClose={() => undefined} title="T">
        {rows(ids)}
      </Modal>
    ),
    panel: () => screen.getByRole("dialog"),
  },
  {
    name: "Sheet",
    element: (open, ids) => (
      <Sheet open={open} onClose={() => undefined} title="T">
        {rows(ids)}
      </Sheet>
    ),
    panel: () => screen.getByTestId("sheet-panel"),
  },
];

/** open=false でマウントしてから open=true へ rerender する（コメント参照） */
function openMold(mold: MoldCase, ids: string[]): void {
  const { rerender } = render(mold.element(false, ids));
  rerender(mold.element(true, ids));
}

describe.each(molds)("$name focus trap (C1-C6)", (mold) => {
  const { panel } = mold;

  /** row-a にフォーカスした状態を作る（C1 の前提） */
  function openAndFocusRowA(): HTMLElement {
    openMold(mold, ["a", "b"]);
    const rowA = screen.getByTestId("row-a");
    rowA.focus();
    expect(document.activeElement).toBe(rowA);
    return rowA;
  }

  it("C1: removing the focused element from the DOM moves activeElement to <body> (fixes the premise)", () => {
    const rowA = openAndFocusRowA();
    rowA.remove();
    expect(document.activeElement).toBe(document.body);
  });

  it("C2: pressing Tab from nowhere moves focus to the first element in the panel", () => {
    const rowA = openAndFocusRowA();
    rowA.remove();
    expect(document.activeElement).toBe(document.body);

    fireEvent.keyDown(document, { key: "Tab" });

    const focusable = getFocusableElements(panel());
    expect(document.activeElement).toBe(focusable[0]);
  });

  it("C3: pressing Shift+Tab from nowhere moves focus to the last element in the panel", () => {
    const rowA = openAndFocusRowA();
    rowA.remove();
    expect(document.activeElement).toBe(document.body);

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });

    const focusable = getFocusableElements(panel());
    expect(document.activeElement).toBe(focusable[focusable.length - 1]);
  });

  it("C4: when focus is on another element outside the panel, Tab does not move it", () => {
    openMold(mold, ["a", "b"]);
    const outside = document.createElement("button");
    outside.setAttribute("data-testid", "outside-button");
    document.body.appendChild(outside);
    outside.focus();
    expect(document.activeElement).toBe(outside);

    fireEvent.keyDown(document, { key: "Tab" });

    expect(document.activeElement).toBe(outside);
    outside.remove();
  });

  it("C5: Shift+Tab at the first wraps to the last, Tab at the last wraps to the first (existing wrap-around)", () => {
    openMold(mold, ["a", "b"]);
    const focusable = getFocusableElements(panel());
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    first.focus();
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);

    last.focus();
    expect(document.activeElement).toBe(last);
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(first);
  });

  it("C6: when open is false, pressing Tab does nothing (not subscribed)", () => {
    render(mold.element(false, ["a", "b"]));
    expect(document.activeElement).toBe(document.body);

    fireEvent.keyDown(document, { key: "Tab" });

    expect(document.activeElement).toBe(document.body);
  });
});

describe("getFocusableElements (C8)", () => {
  afterEach(cleanup);

  it("C8: excludes elements inside [aria-hidden='true']", () => {
    render(
      <div data-testid="container">
        <button data-testid="visible">visible</button>
        <div aria-hidden="true">
          <button data-testid="hidden">hidden</button>
        </div>
      </div>,
    );
    const container = screen.getByTestId("container");
    const focusable = getFocusableElements(container);
    expect(focusable).toContain(screen.getByTestId("visible"));
    expect(focusable).not.toContain(screen.getByTestId("hidden"));
  });
});

describe("FOCUSABLE_SELECTOR is defined in exactly one place in frontend/src (C11)", () => {
  const SRC_ROOT = join(__dirname, "..");

  function walk(dir: string, out: string[] = []): string[] {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      if (statSync(full).isDirectory()) {
        if (name === "node_modules") continue;
        walk(full, out);
      } else if (/\.tsx?$/.test(name)) {
        out.push(full);
      }
    }
    return out;
  }

  it("C11: the only `FOCUSABLE_SELECTOR =` definition is hooks/useFocusTrap.ts", () => {
    // 宣言そのもの（識別子の定義）だけを数える。import や、この説明文中の言及
    // （本テストファイル自身がコメントで識別子名に触れている分）は定義ではないため、
    // 自分自身は走査対象から外す（srOnlySsot.test.ts は .css だけを走査するため
    // この問題が起きないが、本テストは .ts(x) を走査するため明示的に除外する）。
    const definers = walk(SRC_ROOT)
      .filter((file) => file !== __filename)
      .filter((file) => /\bconst\s+FOCUSABLE_SELECTOR\s*=/.test(readFileSync(file, "utf8")))
      .map((file) => file.replace(SRC_ROOT, "frontend/src"));
    expect(definers).toEqual(["frontend/src/hooks/useFocusTrap.ts"]);
  });
});
