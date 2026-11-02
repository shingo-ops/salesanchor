/**
 * useHideMobileTabbar unit tests（card-a2 §13）
 */

import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { MobileTabbarContext, useHideMobileTabbar } from "./useMobileTabbarHidden";

function makeWrapper(set: (hidden: boolean) => void) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MobileTabbarContext.Provider value={set}>{children}</MobileTabbarContext.Provider>;
  };
}

describe("useHideMobileTabbar", () => {
  it("calls the provider setter with true when hidden is true", () => {
    const set = vi.fn();
    renderHook(() => useHideMobileTabbar(true), { wrapper: makeWrapper(set) });
    expect(set).toHaveBeenLastCalledWith(true);
  });

  it("calls the setter with false when hidden changes from true to false", () => {
    const set = vi.fn();
    const { rerender } = renderHook(({ hidden }) => useHideMobileTabbar(hidden), {
      wrapper: makeWrapper(set),
      initialProps: { hidden: true },
    });
    rerender({ hidden: false });
    expect(set).toHaveBeenLastCalledWith(false);
  });

  it("calls the setter with false on unmount", () => {
    const set = vi.fn();
    const { unmount } = renderHook(() => useHideMobileTabbar(true), { wrapper: makeWrapper(set) });
    set.mockClear();
    unmount();
    expect(set).toHaveBeenCalledWith(false);
  });

  it("does not throw without a provider", () => {
    expect(() => {
      renderHook(() => useHideMobileTabbar(true));
    }).not.toThrow();
  });
});
