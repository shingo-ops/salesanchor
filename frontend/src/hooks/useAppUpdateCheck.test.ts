import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAppUpdateCheck } from "./useAppUpdateCheck";

const CURRENT = "/assets/main-AAAA1111.js";
const NEWER = "/assets/main-BBBB2222.js";

function setHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", { configurable: true, value: hidden });
  document.dispatchEvent(new Event("visibilitychange"));
}

function html(entry: string) {
  return `<!doctype html><html><head><script type="module" crossorigin src="${entry}"></script></head><body></body></html>`;
}

function mockFetch(entry: string) {
  const fn = vi.fn(async () => new Response(html(entry), { status: 200 }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

function installCurrentScript(src: string | null) {
  document.head.querySelectorAll("script[data-test-entry]").forEach((el) => el.remove());
  if (!src) return;
  const el = document.createElement("script");
  el.type = "module";
  el.src = src;
  el.setAttribute("data-test-entry", "1");
  document.head.appendChild(el);
}

/** 表に戻った状態を作る（一度裏に回して戻す） */
async function comeBack(afterMs: number) {
  await act(async () => {
    setHidden(true);
    vi.advanceTimersByTime(afterMs);
    setHidden(false);
  });
}

describe("useAppUpdateCheck", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setHidden(false);
    installCurrentScript(CURRENT);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    installCurrentScript(null);
  });

  it("K1: shows the notice on the first check after returning when the entry name differs", async () => {
    const fetchMock = mockFetch(NEWER);
    const { result } = renderHook(() => useAppUpdateCheck());
    expect(result.current).toBe(false);
    await comeBack(61_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/", expect.objectContaining({ cache: "no-store" }));
    expect(result.current).toBe(true);
  });

  it("K2: no notice when the name is the same, and a second check within 60s does not fetch", async () => {
    const fetchMock = mockFetch(CURRENT);
    const { result } = renderHook(() => useAppUpdateCheck());
    await comeBack(61_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.current).toBe(false);
    await comeBack(30_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await comeBack(31_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("K3: does not fetch while hidden, and stops fetching once a new version is found", async () => {
    const fetchMock = mockFetch(NEWER);
    const { result } = renderHook(() => useAppUpdateCheck());
    await act(async () => {
      setHidden(true);
      vi.advanceTimersByTime(30 * 60_000);
    });
    expect(fetchMock).not.toHaveBeenCalled();
    await act(async () => {
      setHidden(false);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.current).toBe(true);
    await comeBack(30 * 60_000);
    await act(async () => {
      vi.advanceTimersByTime(30 * 60_000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("K3: checks every 10 minutes while visible", async () => {
    const fetchMock = mockFetch(CURRENT);
    renderHook(() => useAppUpdateCheck());
    await act(async () => {
      vi.advanceTimersByTime(10 * 60_000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async () => {
      vi.advanceTimersByTime(10 * 60_000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("K4: shows nothing and does not fetch when the current entry name is unavailable", async () => {
    installCurrentScript(null);
    const fetchMock = mockFetch(NEWER);
    const { result } = renderHook(() => useAppUpdateCheck());
    await comeBack(61_000);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current).toBe(false);
  });

  it("K4: shows nothing and does not throw when fetch fails or the response has no entry name", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("network");
    });
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useAppUpdateCheck());
    await comeBack(61_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.current).toBe(false);

    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html></html>", { status: 200 })));
    await comeBack(61_000);
    expect(result.current).toBe(false);

    vi.stubGlobal("fetch", vi.fn(async () => new Response(html(NEWER), { status: 500 })));
    await comeBack(61_000);
    expect(result.current).toBe(false);
  });

  it("aborts a fetch that never answers after 10 seconds and fetches again on the next check", async () => {
    const fetchMock = vi.fn(
      (_url: string, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useAppUpdateCheck());
    await comeBack(61_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async () => {
      vi.advanceTimersByTime(10_000);
    });
    expect(result.current).toBe(false);
    await comeBack(61_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("clears listeners on unmount", async () => {
    const fetchMock = mockFetch(NEWER);
    const { unmount } = renderHook(() => useAppUpdateCheck());
    unmount();
    await comeBack(30 * 60_000);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("clears the pending abort timer on unmount", async () => {
    const fetchMock = vi.fn(() => new Promise<Response>(() => undefined));
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = renderHook(() => useAppUpdateCheck());
    await comeBack(61_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const before = vi.getTimerCount();
    unmount();
    // interval と打ち切り用タイマーの2つが片付く
    expect(vi.getTimerCount()).toBe(before - 2);
  });
});
