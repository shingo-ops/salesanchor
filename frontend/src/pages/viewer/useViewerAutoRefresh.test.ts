import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { VIEWER_REFRESH_MS, useViewerAutoRefresh } from "./useViewerAutoRefresh";

function setHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });
}

beforeEach(() => {
  vi.useFakeTimers();
  setHidden(false);
});
afterEach(() => {
  vi.useRealTimers();
  setHidden(false);
});

describe("useViewerAutoRefresh", () => {
  it("T1: calls refresh once per minute while enabled", () => {
    const refresh = vi.fn();
    renderHook(() => useViewerAutoRefresh(true, refresh));
    vi.advanceTimersByTime(VIEWER_REFRESH_MS - 1);
    expect(refresh).toHaveBeenCalledTimes(0);
    vi.advanceTimersByTime(1);
    expect(refresh).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(VIEWER_REFRESH_MS);
    expect(refresh).toHaveBeenCalledTimes(2);
  });

  it("T2: does nothing when disabled", () => {
    const refresh = vi.fn();
    renderHook(() => useViewerAutoRefresh(false, refresh));
    vi.advanceTimersByTime(VIEWER_REFRESH_MS * 3);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("T3: holds while the tab is hidden and calls once when it becomes visible", () => {
    const refresh = vi.fn();
    renderHook(() => useViewerAutoRefresh(true, refresh));
    setHidden(true);
    vi.advanceTimersByTime(VIEWER_REFRESH_MS * 2);
    expect(refresh).not.toHaveBeenCalled();
    setHidden(false);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(refresh).toHaveBeenCalledTimes(1);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("T4: does not call after unmount", () => {
    const refresh = vi.fn();
    const { unmount } = renderHook(() => useViewerAutoRefresh(true, refresh));
    unmount();
    vi.advanceTimersByTime(VIEWER_REFRESH_MS * 3);
    expect(refresh).not.toHaveBeenCalled();
  });
});
