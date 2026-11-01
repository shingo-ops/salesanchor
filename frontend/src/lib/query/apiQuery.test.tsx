/**
 * ADR-1054 段 1: 写しの置き場の土台の試験（T1〜T9・段 2 で T11〜T13）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import { StrictMode, type ReactNode } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { QueryAuthSync } from "./QueryAuthSync";
import { apiQueryKey, invalidateApi, queryClient, splitApiPath, useApiQuery, useInvalidateApi } from "./apiQuery";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: auth.user, loading: false }),
}));
vi.mock("../auth/provider", () => ({ isSelfAuth: () => false }));
vi.mock("../auth/selfAuth", () => ({
  getAccessToken: async () => "test-token",
  expireSession: vi.fn(),
  selfRefresh: vi.fn(),
}));

function Probe({ path, testId }: { path: string; testId: string }) {
  const q = useApiQuery<string>(path);
  return (
    <div>
      <div data-testid={testId}>{q.data ?? ""}</div>
      <div data-testid={`${testId}-status`}>{q.status}</div>
    </div>
  );
}

/** keepPrevious を使う試しの部品。描いた中身を全部 renderedData に残す（K5 で描画の途中も数える） */
const renderedData: Array<string | undefined> = [];
function KeepProbe({ path, testId }: { path: string; testId: string }) {
  const q = useApiQuery<string>(path, { keepPrevious: true });
  renderedData.push(q.data);
  return (
    <div>
      <div data-testid={testId}>{q.data ?? ""}</div>
      <div data-testid={`${testId}-placeholder`}>{String(q.isPlaceholderData)}</div>
    </div>
  );
}

let latestInvalidate: ((head: readonly string[]) => Promise<void>) | null = null;
function InvalidateProbe() {
  latestInvalidate = useInvalidateApi();
  return null;
}

function Tree({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      {children}
    </QueryClientProvider>
  );
}

function keysWithUid(uid: string): number {
  return queryClient
    .getQueryCache()
    .getAll()
    .filter((query) => query.queryKey[1] === uid).length;
}

afterEach(() => {
  queryClient.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  auth.user = { uid: "uid-A" };
  renderedData.length = 0;
  latestInvalidate = null;
});

describe("splitApiPath / apiQueryKey (T1)", () => {
  it("splits words and query like design §3-2", () => {
    expect(apiQueryKey("u", "/companies?status=a")).toEqual(["api", "u", "companies", { query: "status=a" }]);
    expect(apiQueryKey("u", "/companies/5")).toEqual(["api", "u", "companies", "5", { query: "" }]);
    expect(splitApiPath("//companies/")).toEqual({ words: ["companies"], query: "" });
    expect(splitApiPath("/a?b?c")).toEqual({ words: ["a"], query: "b?c" });
  });
});

describe("invalidateApi (T2)", () => {
  it("refetches all 4 companies copies and not contacts", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `data:${path}` as never);
    const paths = ["/companies?status=a", "/companies?status=b", "/companies/5", "/companies/6", "/contacts?x=1"];
    render(
      <Tree>
        {paths.map((path, i) => (
          <Probe key={path} path={path} testId={`p${i}`} />
        ))}
      </Tree>,
    );
    for (let i = 0; i < paths.length; i++) {
      await waitFor(() => expect(screen.getByTestId(`p${i}`).textContent).toBe(`data:${paths[i]}`));
    }
    spy.mockClear();
    await act(async () => {
      await invalidateApi("uid-A", ["companies"]);
    });
    const called = spy.mock.calls.map((call) => call[0]).sort();
    expect(called).toEqual(paths.slice(0, 4).sort());
  });
});

describe("retry (T3)", () => {
  it("one failing request calls fetch at most 4 times", async () => {
    const fetchMock = vi.fn(async () => ({ status: 503, ok: false, json: async () => ({}) }) as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);
    render(
      <Tree>
        <Probe path="/retry-check" testId="r" />
      </Tree>,
    );
    await waitFor(() => expect(screen.getByTestId("r-status").textContent).toBe("error"), { timeout: 10_000 });
    expect(fetchMock).toHaveBeenCalledTimes(4);
  }, 15_000);
});

describe("K5: user change clears copies (T4)", () => {
  it("A -> logout -> B never shows A's content", async () => {
    const releases: Array<() => void> = [];
    vi.spyOn(api, "get").mockImplementation(async () => {
      const uid = auth.user?.uid;
      if (uid === "uid-A") return `secret-${uid}` as never;
      return new Promise((resolve) => {
        releases.push(() => resolve(`secret-${uid}` as never));
      }) as never;
    });
    const tree = () => (
      <Tree>
        <Probe path="/companies" testId="k5" />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("k5").textContent).toBe("secret-uid-A"));

    let seenA = 0;
    const observer = new MutationObserver(() => {
      if (document.body.textContent?.includes("secret-uid-A")) seenA += 1;
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });

    auth.user = null;
    rerender(tree());
    expect(screen.getByTestId("k5").textContent).toBe("");
    expect(keysWithUid("uid-A")).toBe(0);

    auth.user = { uid: "uid-B" };
    rerender(tree());
    expect(screen.getByTestId("k5").textContent).toBe("");
    await waitFor(() => expect(releases.length).toBeGreaterThan(0));
    act(() => {
      releases.forEach((release) => release());
    });
    await waitFor(() => expect(screen.getByTestId("k5").textContent).toBe("secret-uid-B"));

    observer.disconnect();
    expect(seenA).toBe(0);
    expect(keysWithUid("uid-A")).toBe(0);
  });
});

describe("direct switch A -> B keeps B reachable (T5)", () => {
  it("after switching, invalidateApi for B refetches B", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `${auth.user?.uid}:${path}` as never);
    const tree = () => (
      <Tree>
        <Probe path="/companies" testId="sw" />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("sw").textContent).toBe("uid-A:/companies"));

    auth.user = { uid: "uid-B" };
    rerender(tree());
    await waitFor(() => expect(screen.getByTestId("sw").textContent).toBe("uid-B:/companies"));
    expect(keysWithUid("uid-A")).toBe(0);
    expect(keysWithUid("uid-B")).toBe(1);

    spy.mockClear();
    await act(async () => {
      await invalidateApi("uid-B", ["companies"]);
    });
    expect(spy).toHaveBeenCalledWith("/companies");
  });
});

describe("same user does not clear (T6)", () => {
  it("rerender with the same uid under StrictMode keeps the copy", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => `keep:${path}` as never);
    const tree = () => (
      <StrictMode>
        <Tree>
          <Probe path="/companies" testId="same" />
        </Tree>
      </StrictMode>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("same").textContent).toBe("keep:/companies"));
    auth.user = { uid: "uid-A" };
    rerender(tree());
    expect(screen.getByTestId("same").textContent).toBe("keep:/companies");
    expect(keysWithUid("uid-A")).toBe(1);
  });
});

describe("defaults (T7)", () => {
  it("retry 0, gcTime 30 min, staleTime not set", () => {
    const defaults = queryClient.getDefaultOptions().queries;
    expect(defaults?.retry).toBe(0);
    expect(defaults?.gcTime).toBe(30 * 60 * 1000);
    expect(defaults?.staleTime).toBeUndefined();
  });
});

describe("clear runs before any passive effect (T8)", () => {
  it("a reader placed before QueryAuthSync still gets B after A -> B", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `${auth.user?.uid}:${path}` as never);
    const tree = () => (
      <QueryClientProvider client={queryClient}>
        <Probe path="/companies" testId="early" />
        <QueryAuthSync />
      </QueryClientProvider>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("early").textContent).toBe("uid-A:/companies"));

    auth.user = { uid: "uid-B" };
    rerender(tree());
    await waitFor(() => expect(screen.getByTestId("early").textContent).toBe("uid-B:/companies"));
    expect(keysWithUid("uid-A")).toBe(0);
    expect(keysWithUid("uid-B")).toBe(1);

    spy.mockClear();
    await act(async () => {
      await invalidateApi("uid-B", ["companies"]);
    });
    expect(spy).toHaveBeenCalledWith("/companies");
  });
});

describe("logout does not refetch the old user's copies (T9)", () => {
  it("api.get is not called between logout and the next login", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `${auth.user?.uid}:${path}` as never);
    const tree = () => (
      <Tree>
        <Probe path="/companies" testId="nofetch" />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("nofetch").textContent).toBe("uid-A:/companies"));
    spy.mockClear();

    auth.user = null;
    rerender(tree());
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    expect(spy).not.toHaveBeenCalled();
    expect(queryClient.getQueryCache().getAll().filter((query) => query.state.fetchStatus === "fetching").length).toBe(0);
  });
});

describe("keepPrevious keeps the same user's rows while the next ones load (T11)", () => {
  it("old rows stay until the new rows arrive", async () => {
    let release: (value: string) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/companies?page=2") return new Promise<string>((resolve) => { release = resolve; }) as never;
      return `rows:${path}` as never;
    });
    const tree = (path: string) => (
      <Tree>
        <KeepProbe path={path} testId="keep" />
      </Tree>
    );
    const { rerender } = render(tree("/companies?page=1"));
    await waitFor(() => expect(screen.getByTestId("keep").textContent).toBe("rows:/companies?page=1"));

    rerender(tree("/companies?page=2"));
    expect(screen.getByTestId("keep").textContent).toBe("rows:/companies?page=1");
    expect(screen.getByTestId("keep-placeholder").textContent).toBe("true");

    await act(async () => {
      release("rows:/companies?page=2");
    });
    await waitFor(() => expect(screen.getByTestId("keep").textContent).toBe("rows:/companies?page=2"));
    expect(screen.getByTestId("keep-placeholder").textContent).toBe("false");
  });
});

describe("K5: keepPrevious never carries A's rows to B (T12)", () => {
  it("A -> B with a slow B fetch renders A's rows 0 times", async () => {
    let releaseB: (value: string) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async () => {
      const uid = auth.user?.uid;
      if (uid === "uid-B") return new Promise<string>((resolve) => { releaseB = resolve; }) as never;
      return `secret-${uid}` as never;
    });
    const tree = () => (
      <Tree>
        <KeepProbe path="/companies" testId="k5keep" />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("k5keep").textContent).toBe("secret-uid-A"));

    const from = renderedData.length;
    auth.user = { uid: "uid-B" };
    rerender(tree());
    expect(screen.getByTestId("k5keep").textContent).toBe("");

    await act(async () => {
      releaseB("secret-uid-B");
    });
    await waitFor(() => expect(screen.getByTestId("k5keep").textContent).toBe("secret-uid-B"));
    expect(renderedData.slice(from).filter((data) => data === "secret-uid-A").length).toBe(0);
    expect(keysWithUid("uid-A")).toBe(0);
  });
});

describe("useInvalidateApi (T13)", () => {
  it("refetches the current user's copies and does nothing when logged out", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `${auth.user?.uid}:${path}` as never);
    const tree = () => (
      <Tree>
        <Probe path="/companies?x=1" testId="inv" />
        <InvalidateProbe />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("inv").textContent).toBe("uid-A:/companies?x=1"));
    spy.mockClear();

    await act(async () => {
      await latestInvalidate?.(["companies"]);
    });
    expect(spy.mock.calls.map((call) => call[0])).toEqual(["/companies?x=1"]);

    auth.user = null;
    rerender(tree());
    spy.mockClear();
    await act(async () => {
      await latestInvalidate?.(["companies"]);
    });
    expect(spy).not.toHaveBeenCalled();
  });
});
