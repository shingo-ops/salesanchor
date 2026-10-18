import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RealtimeContext, type RealtimeApi, type RealtimeHandler } from "../lib/realtime/context";
import { REALTIME_DEBOUNCE_MS, useRealtimeRefresh } from "./useRealtimeRefresh";

function setup(options?: { debounceMs?: number }) {
  let handler: RealtimeHandler = () => undefined;
  const api: RealtimeApi = {
    clientId: "me",
    subscribe: (_t, h) => {
      handler = h;
      return () => undefined;
    },
  };
  const wrapper = ({ children }: { children: ReactNode }) => (
    <RealtimeContext.Provider value={api}>{children}</RealtimeContext.Provider>
  );
  const reload = vi.fn();
  renderHook(() => useRealtimeRefresh(["tcg.review"], reload, options), { wrapper });
  return { reload, emit: (ev: Parameters<RealtimeHandler>[0]) => handler(ev) };
}

function setHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", { configurable: true, value: hidden });
  document.dispatchEvent(new Event("visibilitychange"));
}

describe("useRealtimeRefresh", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setHidden(false);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("coalesces signals within the window into one reload", () => {
    const { reload, emit } = setup();
    act(() => {
      emit({ topic: "tcg.review", origin: "other" });
      emit({ topic: "tcg.review", origin: null });
      vi.advanceTimersByTime(REALTIME_DEBOUNCE_MS - 100);
      emit({ topic: "tcg.review", origin: "other" });
    });
    expect(reload).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("uses debounceMs when given", () => {
    const { reload, emit } = setup({ debounceMs: 5_000 });
    act(() => {
      emit({ topic: "tcg.review", origin: "other" });
      vi.advanceTimersByTime(REALTIME_DEBOUNCE_MS + 100);
    });
    expect(reload).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(5_000 - REALTIME_DEBOUNCE_MS);
    });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("defaults to 1.5 seconds when debounceMs is not given", () => {
    const { reload, emit } = setup();
    act(() => {
      emit({ topic: "tcg.review", origin: "other" });
      vi.advanceTimersByTime(REALTIME_DEBOUNCE_MS - 10);
    });
    expect(reload).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(20);
    });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("ignores signals originated by this client", () => {
    const { reload, emit } = setup();
    act(() => {
      emit({ topic: "tcg.review", origin: "me" });
      vi.advanceTimersByTime(REALTIME_DEBOUNCE_MS * 2);
    });
    expect(reload).not.toHaveBeenCalled();
  });

  it("defers while hidden and reloads once when visible", () => {
    const { reload, emit } = setup();
    act(() => {
      setHidden(true);
      emit({ topic: "tcg.review", origin: "other" });
      vi.advanceTimersByTime(REALTIME_DEBOUNCE_MS * 2);
    });
    expect(reload).toHaveBeenCalledTimes(0);
    act(() => setHidden(false));
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("reloads once after reconnect", () => {
    const { reload, emit } = setup();
    act(() => {
      emit({ reconnected: true });
      vi.advanceTimersByTime(REALTIME_DEBOUNCE_MS + 10);
    });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("does nothing outside the provider", () => {
    const reload = vi.fn();
    expect(() => renderHook(() => useRealtimeRefresh(["tcg.review"], reload))).not.toThrow();
    expect(reload).not.toHaveBeenCalled();
  });
});
