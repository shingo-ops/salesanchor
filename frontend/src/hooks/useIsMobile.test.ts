import { renderHook, act } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useIsMobile } from "./useIsMobile";

function mockMatchMedia(matches: boolean) {
  const listeners: ((e: MediaQueryListEvent) => void)[] = [];
  const mql = {
    matches,
    addEventListener: vi.fn((_event: string, handler: (e: MediaQueryListEvent) => void) => {
      listeners.push(handler);
    }),
    removeEventListener: vi.fn((_event: string, handler: (e: MediaQueryListEvent) => void) => {
      const idx = listeners.indexOf(handler);
      if (idx !== -1) listeners.splice(idx, 1);
    }),
  };
  const mockFn = vi.fn().mockReturnValue(mql as unknown as MediaQueryList);
  vi.stubGlobal("matchMedia", mockFn);
  return { mql, mockFn, dispatchChange: (nextMatches: boolean) => {
    listeners.forEach((h) => h({ matches: nextMatches } as MediaQueryListEvent));
  }};
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useIsMobile", () => {
  it("returns true at 375px (below MOBILE_MAX)", () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it("returns false at 1280px (above MOBILE_MAX)", () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it("re-renders on change event (false → true)", () => {
    const { dispatchChange } = mockMatchMedia(false);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);

    act(() => {
      dispatchChange(true);
    });

    expect(result.current).toBe(true);
  });

  it("re-renders on change event (true → false)", () => {
    const { dispatchChange } = mockMatchMedia(true);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);

    act(() => {
      dispatchChange(false);
    });

    expect(result.current).toBe(false);
  });

  it("calls removeEventListener on unmount (cleanup)", () => {
    const { mql } = mockMatchMedia(false);
    const { unmount } = renderHook(() => useIsMobile());
    unmount();
    expect(mql.removeEventListener).toHaveBeenCalledOnce();
  });

  it("uses (max-width: 767px) media query", () => {
    const { mockFn } = mockMatchMedia(false);
    renderHook(() => useIsMobile());
    expect(mockFn).toHaveBeenCalledWith("(max-width: 767px)");
  });
});
