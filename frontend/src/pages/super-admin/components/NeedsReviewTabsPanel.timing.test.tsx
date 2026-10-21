import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import i18n from "../../../i18n";
import NeedsReviewTabsPanel from "./NeedsReviewTabsPanel";

let fireRealtime: () => void = () => undefined;

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("../../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));
vi.mock("../../../hooks/useRealtimeRefresh", () => ({
  useRealtimeRefresh: (_topics: readonly string[], reload: () => void) => {
    fireRealtime = reload;
  },
}));
vi.mock("../../../features/tcg-analysis-review/V102PostsTab", () => ({ V102PostsTab: () => <div>posts-tab</div> }));
vi.mock("../../../features/tcg-review-csv/ReviewCsvPanel", () => ({
  ReviewCsvPanel: ({ onDone }: { onDone: () => void }) => <button onClick={onDone}>csv-done</button>,
}));

const TIMING_PATH = "/tcg/analysis-results/client-timing";

const makeItem = (id: string, name: string) => ({
  extraction_item_id: id,
  source_message_id: `source-${id}`,
  provider: "Supplier A",
  raw_text: "",
  gemini: { name, span: "" },
  system: {},
  review_issues: [],
  condition_review: null,
  review_reason_details: [],
});

const response = (items: ReturnType<typeof makeItem>[], total = items.length) => ({
  items, total, item_total: total, offset: 0, limit: 20, providers: [], works: [],
});

// requestAnimationFrame を手で進める（2段待ちを確かめるため）
let frames = new Map<number, FrameRequestCallback>();
let nextFrameId = 1;
const flushFrames = () =>
  act(async () => {
    for (let i = 0; i < 5; i++) {
      const pending = [...frames.values()];
      frames = new Map();
      pending.forEach((cb) => cb(performance.now()));
      await Promise.resolve();
    }
  });
const stepOneFrame = () =>
  act(async () => {
    const pending = [...frames.values()];
    frames = new Map();
    pending.forEach((cb) => cb(performance.now()));
    await Promise.resolve();
  });

const timingPosts = () => vi.mocked(api.post).mock.calls.filter(([p]) => p === TIMING_PATH);
const view = () => render(<MemoryRouter><NeedsReviewTabsPanel /></MemoryRouter>);

beforeEach(async () => {
  vi.resetAllMocks();
  frames = new Map();
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    const id = nextFrameId++;
    frames.set(id, cb);
    return id;
  });
  vi.stubGlobal("cancelAnimationFrame", (id: number) => {
    frames.delete(id);
  });
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockImplementation(() => Promise.resolve(response([makeItem("a", "Card A")], 40)));
  vi.mocked(api.post).mockResolvedValue(undefined);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("review timing", () => {
  // 注: entry はファイル内の最初の mount だけ "first" になるので、最初のテストで first と return を両方確かめる
  it("sends once after two frames with typed fields (entry first), then return after a re-mount", async () => {
    const first = view();
    await screen.findByText("Card A");
    await act(async () => {}); // effect を流して最初の frame を予約させる
    expect(timingPosts()).toHaveLength(0); // まだ2段待っていない
    await stepOneFrame();
    expect(timingPosts()).toHaveLength(0);
    await stepOneFrame();
    expect(timingPosts()).toHaveLength(1);
    const [path, body] = timingPosts()[0] as [string, Record<string, unknown>];
    expect(path).toBe(TIMING_PATH);
    expect(Object.keys(body).sort()).toEqual(["doc_ms", "entry", "list_ms", "page_size", "panel_ms", "rows"]);
    for (const key of ["panel_ms", "list_ms", "doc_ms"]) {
      expect(typeof body[key]).toBe("number");
      expect(body[key] as number).toBeGreaterThanOrEqual(0);
      expect(body[key] as number).toBeLessThanOrEqual(120000);
    }
    expect(body.rows).toBe(1);
    expect(body.page_size).toBe(25);
    expect(body.entry).toBe("first");

    first.unmount();
    view();
    await screen.findByText("Card A");
    await flushFrames();
    expect(timingPosts()).toHaveLength(2);
    expect((timingPosts()[1][1] as { entry: string }).entry).toBe("return");
  });

  it("does not send again for a realtime reload, paging or a tab round trip", async () => {
    view();
    await screen.findByText("Card A");
    await flushFrames();
    expect(timingPosts()).toHaveLength(1);

    act(() => fireRealtime());
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledTimes(2));
    await flushFrames();

    fireEvent.click(screen.getByRole("button", { name: "next page" }));
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledTimes(3));
    await screen.findByText("Card A");
    await flushFrames();

    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledTimes(4));
    fireEvent.click(screen.getByRole("tab", { name: "Production review" }));
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledTimes(5));
    await screen.findByText("Card A");
    await flushFrames();

    expect(timingPosts()).toHaveLength(1);
  });

  it("sends even when the list is empty (rows 0)", async () => {
    vi.mocked(api.get).mockImplementation(() => Promise.resolve(response([])));
    view();
    await screen.findByText("No items need review");
    await flushFrames();
    expect(timingPosts()).toHaveLength(1);
    expect((timingPosts()[0][1] as { rows: number }).rows).toBe(0);
  });

  it("does not send when the fetch fails, and sends when a later reload first shows the list", async () => {
    vi.mocked(api.get).mockImplementationOnce(() => Promise.reject(new Error("boom")));
    view();
    await screen.findByRole("alert");
    await flushFrames();
    expect(timingPosts()).toHaveLength(0);

    act(() => fireRealtime());
    await screen.findByText("Card A");
    await flushFrames();
    expect(timingPosts()).toHaveLength(1);
  });

  it("shows nothing and does not throw when the timing POST fails", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("down"));
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    view();
    await screen.findByText("Card A");
    await flushFrames();
    await waitFor(() => expect(timingPosts()).toHaveLength(1));
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(consoleSpy).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("does not send when the panel moves to another tab before the first frame pair, or unmounts", async () => {
    const mounted = view();
    await screen.findByText("Card A");
    fireEvent.click(screen.getByRole("tab", { name: "Checked" }));
    await flushFrames();
    expect(timingPosts()).toHaveLength(0);
    mounted.unmount();

    const second = view();
    await screen.findByText("Card A");
    second.unmount();
    await flushFrames();
    expect(timingPosts()).toHaveLength(0);
  });

  it("does not send again for a reload after saving", async () => {
    view();
    await screen.findByText("Card A");
    await flushFrames();
    expect(timingPosts()).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "csv-done" }));
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledTimes(2));
    await screen.findByText("Card A");
    await flushFrames();
    expect(timingPosts()).toHaveLength(1);
  });

  it("sends once with the list_ms of the reload when the first fetch is cancelled (R-5)", async () => {
    let clock = 0;
    vi.spyOn(performance, "now").mockImplementation(() => clock);
    let resolveFirst: (v: unknown) => void = () => undefined;
    let resolveSecond: (v: unknown) => void = () => undefined;
    vi.mocked(api.get)
      .mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }))
      .mockImplementationOnce(() => new Promise((r) => { resolveSecond = r; }));
    view();
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledTimes(1));
    clock = 1000;
    act(() => fireRealtime()); // 最初の取得を取り消して読み直す
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledTimes(2));
    clock = 1300;
    await act(async () => resolveSecond(response([makeItem("a", "Card A")])));
    await screen.findByText("Card A");
    await flushFrames();
    clock = 5000;
    await act(async () => resolveFirst(response([makeItem("old", "Card Old")])));
    await flushFrames();
    expect(screen.queryByText("Card Old")).toBeNull();
    expect(timingPosts()).toHaveLength(1);
    expect((timingPosts()[0][1] as { list_ms: number }).list_ms).toBe(300);
  });
});
