/**
 * recentSearches.test.ts — design.md ③ Acceptance Criteria U1・U2 を固定する単体テスト
 * （docs/handoff/viewer-search-mercari/design.md）
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { addRecentSearch, clearRecentSearches, loadRecentSearches } from "./recentSearches";

beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("recentSearches", () => {
  it("U1: starts empty", () => {
    expect(loadRecentSearches()).toEqual([]);
  });

  it("U1: new entries go to the front", () => {
    addRecentSearch("a");
    addRecentSearch("b");
    expect(loadRecentSearches()).toEqual(["b", "a"]);
  });

  it("U1: re-adding an existing term moves it to the front without duplicating it", () => {
    addRecentSearch("a");
    addRecentSearch("b");
    addRecentSearch("a");
    expect(loadRecentSearches()).toEqual(["a", "b"]);
  });

  it("U1: keeps at most 10 entries, dropping the oldest", () => {
    for (let i = 0; i < 12; i++) addRecentSearch(`q${i}`);
    const list = loadRecentSearches();
    expect(list).toHaveLength(10);
    expect(list[0]).toBe("q11");
    expect(list).not.toContain("q0");
    expect(list).not.toContain("q1");
  });

  it("clearRecentSearches empties the list", () => {
    addRecentSearch("a");
    clearRecentSearches();
    expect(loadRecentSearches()).toEqual([]);
  });

  it("adding an empty term is a no-op", () => {
    addRecentSearch("a");
    addRecentSearch("");
    expect(loadRecentSearches()).toEqual(["a"]);
  });

  it("U2: a corrupted JSON value in localStorage returns an empty array, no throw", () => {
    window.localStorage.setItem("viewer:recent-searches", "{not json");
    expect(() => loadRecentSearches()).not.toThrow();
    expect(loadRecentSearches()).toEqual([]);
  });

  it("U2: a non-array JSON value in localStorage returns an empty array", () => {
    window.localStorage.setItem("viewer:recent-searches", JSON.stringify({ a: 1 }));
    expect(loadRecentSearches()).toEqual([]);
  });

  it("U2: localStorage.getItem throwing (e.g. private mode) returns an empty array, no throw", () => {
    vi.spyOn(window.localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(() => loadRecentSearches()).not.toThrow();
    expect(loadRecentSearches()).toEqual([]);
  });

  it("U2: localStorage.setItem throwing on write is swallowed (no throw), later reads stay empty", () => {
    vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    expect(() => addRecentSearch("a")).not.toThrow();
  });

  it("U2: localStorage itself being unreachable returns an empty array, no throw", () => {
    const original = Object.getOwnPropertyDescriptor(window, "localStorage");
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new Error("blocked");
      },
    });
    try {
      expect(() => loadRecentSearches()).not.toThrow();
      expect(loadRecentSearches()).toEqual([]);
      expect(() => addRecentSearch("a")).not.toThrow();
    } finally {
      if (original) Object.defineProperty(window, "localStorage", original);
    }
  });
});
