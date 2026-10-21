import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useExpiryRefresh } from "./useExpiryRefresh";

function setHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", { configurable: true, value: hidden });
  document.dispatchEvent(new Event("visibilitychange"));
}

describe("useExpiryRefresh", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setHidden(false);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("calls reload once after seconds plus jitter", () => {
    const reload = vi.fn();
    renderHook(() => useExpiryRefresh(120, reload, 2_000, 0));
    act(() => {
      vi.advanceTimersByTime(121_000);
    });
    expect(reload).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(1_500);
    });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("never fires before the 60 second minimum", () => {
    const reload = vi.fn();
    renderHook(() => useExpiryRefresh(5, reload, 0, 0));
    act(() => {
      vi.advanceTimersByTime(59_000);
    });
    expect(reload).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(1_500);
    });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("does nothing when seconds is null", () => {
    const reload = vi.fn();
    renderHook(() => useExpiryRefresh(null, reload, 0, 0));
    act(() => {
      vi.advanceTimersByTime(200_000_000);
    });
    expect(reload).not.toHaveBeenCalled();
  });

  it("holds while hidden and fires once when visible again", () => {
    const reload = vi.fn();
    renderHook(() => useExpiryRefresh(60, reload, 0, 0));
    act(() => {
      setHidden(true);
      vi.advanceTimersByTime(61_000);
    });
    expect(reload).not.toHaveBeenCalled();
    act(() => {
      setHidden(false);
    });
    expect(reload).toHaveBeenCalledTimes(1);
    act(() => {
      setHidden(false);
    });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("re-arms the timer when resetKey changes", () => {
    const reload = vi.fn();
    const { rerender } = renderHook(({ k }) => useExpiryRefresh(60, reload, 0, k), { initialProps: { k: 0 } });
    act(() => {
      vi.advanceTimersByTime(50_000);
    });
    rerender({ k: 1 });
    act(() => {
      vi.advanceTimersByTime(50_000);
    });
    expect(reload).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(11_000);
    });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("clears the timer on unmount", () => {
    const reload = vi.fn();
    const { unmount } = renderHook(() => useExpiryRefresh(60, reload, 0, 0));
    unmount();
    act(() => {
      vi.advanceTimersByTime(120_000);
    });
    expect(reload).not.toHaveBeenCalled();
  });
});
