/**
 * ADR-1054 会話の画面の写し（lead-chat-cache-card.md）の試験。
 * 1 本目 送る path が今と同じ・2 本目 戻った時に一覧・選び肢・メッセージ・カルテを写しから先に出す（K1）・
 * 3 本目 手元の書き換えが写しに残る・4 本目 利用者が変わると前の人の写しを出さない（K5）・
 * 5 本目 カルテの保存の後の中身を写しに書く・6 本目 画面を出したまま利用者が変わっても前の人の写しを出さない（K5）・
 * 7 本目 会話を素早く切り替えて前の会話のカルテが遅れて返っても入力欄に入れない・
 * 8 本目 失敗の印は失敗した会話だけに付く・9 本目 カルテの保存の途中で会話を切り替えても遅れた保存の中身を入力欄に入れない・
 * 10 本目 写しの無い条件へ切り替えた時に空の一覧を読み込み中の印なしで出さない・
 * 11 本目 前に取りに行って失敗した条件へ戻した時に空の一覧を読み込み中の印なしで出さない・
 * 12 本目 前に失敗した条件へ戻した後に、その前の条件の取得が遅れて返っても空の一覧を読み込み中の印なしで出さない。試験の題は英語（lint の決まり local/no-japanese-literal）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));
const listConversationsMock = vi.fn();
const getMessagesMock = vi.fn();
const markReadMock = vi.fn((_leadId: number, _opened?: boolean) => Promise.resolve({ marked_count: 0 }));
const apiGetMock = vi.fn();
const apiPatchMock = vi.fn();

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));
const stableT = (key: string) => key;
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: stableT }),
}));
vi.mock("../../hooks/useIsMobile", () => ({ useIsMobile: () => false }));
vi.mock("../../hooks/useInboxSSE", () => ({ useInboxSSE: () => undefined }));
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: auth.user, loading: false }),
}));
vi.mock("../../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => apiGetMock(...args),
    post: vi.fn(() => Promise.resolve({})),
    patch: (...args: unknown[]) => apiPatchMock(...args),
    delete: vi.fn(() => Promise.resolve({})),
  },
  ApiError: class ApiError extends Error {
    status?: number;
  },
}));
vi.mock("../../lib/messages", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/messages")>();
  return {
    conversationsPath: actual.conversationsPath,
    messagesPath: actual.messagesPath,
    listConversations: (...args: unknown[]) => listConversationsMock(...args),
    markRead: (...args: [number, boolean?]) => markReadMock(...args),
    markUnread: vi.fn(() => Promise.resolve({ unmarked_count: 0 })),
    getMessages: (...args: unknown[]) => getMessagesMock(...args),
    sendMessage: vi.fn(),
    sendImageMessage: vi.fn(),
    inferPlatform: vi.fn(() => "messenger"),
  };
});

import { conversationsPath, messagesPath } from "../../lib/messages";
import { queryClient } from "../../lib/query/apiQuery";
import { useInboxState } from "./useInboxState";

const conv = (leadId: number, name: string, pageId: string) => ({
  lead_id: leadId,
  lead_code: `LD-0000${leadId}`,
  customer_name: name,
  lead_status: null,
  platform: "messenger",
  page_id: pageId,
  last_message_text: "hi",
  last_message_at: "2026-11-01T00:00:00Z",
  last_message_direction: "inbound",
  unread_count: 1,
  messaging_window_expires_at: null,
  is_new_assignment: false,
});
const CONVS = { conversations: [conv(1, "Alice", "page-1"), conv(2, "Bob", "page-2")], next_cursor: null };
const MESSAGES = { lead: { id: 1, platform: "messenger" }, messages: [{ id: 10, text: "hello" }] };
const LEAD = { id: 1, customer_name: "Alice", status: "new" };
const LEAD2 = { id: 2, customer_name: "Bob", status: "new" };
const never = () => new Promise<never>(() => {});

/** 1 回目に開いて、一覧・メッセージ・カルテが揃うまで待ち、閉じる */
async function openOnce() {
  const first = renderHook(() => useInboxState());
  await waitFor(() => expect(first.result.current.selectedLeadId).toBe(1));
  await waitFor(() => expect(first.result.current.messagesData).not.toBeNull());
  await waitFor(() => expect(first.result.current.leadDetail).not.toBeNull());
  await waitFor(() => expect(first.result.current.availablePageIds).toEqual(["page-1", "page-2"]));
  return first;
}

describe("useInboxState - query cache (ADR-1054 lead chat)", () => {
  beforeEach(() => {
    queryClient.clear();
    localStorage.clear();
    auth.user = { uid: "uid-A" };
    listConversationsMock.mockReset().mockResolvedValue(CONVS);
    getMessagesMock.mockReset().mockResolvedValue(MESSAGES);
    markReadMock.mockClear();
    apiGetMock.mockReset().mockImplementation((path: string) =>
      path === "/leads/1" ? Promise.resolve(LEAD) : Promise.reject(new Error(`not used: ${path}`)),
    );
    apiPatchMock.mockReset();
  });

  it("sends the same path strings as before", () => {
    expect(conversationsPath({})).toBe("/conversations");
    expect(conversationsPath({ unread_only: false })).toBe("/conversations");
    expect(conversationsPath({ platform: "all", unread_only: true })).toBe("/conversations?unread_only=true");
    expect(conversationsPath({ platform: "instagram", unread_only: true, page_id: "page-1" })).toBe(
      "/conversations?platform=instagram&unread_only=true&page_id=page-1",
    );
    expect(messagesPath(5)).toBe("/leads/5/messages");
  });

  it("on return, shows list, page choices, messages and karte from the cache before any fetch returns (K1)", async () => {
    const first = await openOnce();
    expect(apiGetMock.mock.calls.map((call) => call[0])).toContain("/leads/1");
    first.unmount();

    // 2 回目は、どの取り方も返らない
    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);

    const second = renderHook(() => useInboxState());
    // 最初の描画で、一覧と選び肢が出ていて、読み込み中ではない
    expect(second.result.current.conversations.map((c) => c.customer_name)).toEqual(["Alice", "Bob"]);
    expect(second.result.current.convLoading).toBe(false);
    expect(second.result.current.availablePageIds).toEqual(["page-1", "page-2"]);
    // 先頭の自動選択の後、メッセージとカルテが写しから出る
    await waitFor(() => expect(second.result.current.selectedLeadId).toBe(1));
    expect(second.result.current.messagesData?.messages).toHaveLength(1);
    expect(second.result.current.leadDetail?.customer_name).toBe("Alice");
    expect(second.result.current.cardForm.customer_name).toBe("Alice");
    second.unmount();
  });

  it("keeps the mark-read change in the cache and shows it on return", async () => {
    markReadMock.mockImplementation(() => Promise.resolve({ marked_count: 1 }));
    const first = await openOnce();
    await waitFor(() =>
      expect(first.result.current.conversations.find((c) => c.lead_id === 1)?.unread_count).toBe(0),
    );
    first.unmount();

    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);
    const second = renderHook(() => useInboxState());
    expect(second.result.current.conversations.find((c) => c.lead_id === 1)?.unread_count).toBe(0);
    expect(second.result.current.conversations.find((c) => c.lead_id === 2)?.unread_count).toBe(1);
    second.unmount();
  });

  it("after a user change, does not show the previous user cache on remount (K5)", async () => {
    const first = await openOnce();
    first.unmount();

    auth.user = { uid: "uid-B" };
    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);
    const second = renderHook(() => useInboxState());
    expect(second.result.current.conversations).toEqual([]);
    expect(second.result.current.convLoading).toBe(true);
    expect(second.result.current.availablePageIds).toEqual([]);
    expect(second.result.current.selectedLeadId).toBeNull();
    expect(second.result.current.messagesData).toBeNull();
    expect(second.result.current.leadDetail).toBeNull();
    second.unmount();
  });

  it("writes the saved karte into the cache and shows it on return", async () => {
    apiPatchMock.mockResolvedValue({ ...LEAD, customer_name: "Alice renamed" });
    const first = await openOnce();
    act(() => {
      first.result.current.handleCardFieldChange("customer_name", "Alice renamed");
    });
    await act(async () => {
      await first.result.current.handleCardFieldBlur();
    });
    expect(apiPatchMock).toHaveBeenCalledTimes(1);
    expect(apiPatchMock.mock.calls[0][0]).toBe("/leads/1");
    expect(first.result.current.leadDetail?.customer_name).toBe("Alice renamed");
    first.unmount();

    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);
    const second = renderHook(() => useInboxState());
    await waitFor(() => expect(second.result.current.selectedLeadId).toBe(1));
    expect(second.result.current.leadDetail?.customer_name).toBe("Alice renamed");
    second.unmount();
  });

  it("after a user change while mounted, does not show the previous user cache (K5)", async () => {
    const view = await openOnce();
    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);
    auth.user = { uid: "uid-B" };
    view.rerender();
    expect(view.result.current.conversations).toEqual([]);
    expect(view.result.current.availablePageIds).toEqual([]);
    expect(view.result.current.messagesData).toBeNull();
    expect(view.result.current.leadDetail).toBeNull();
    view.unmount();
  });

  it("when switching A to B, a late karte response for A does not fill the form", async () => {
    let resolveA: (value: unknown) => void = () => {};
    apiGetMock.mockImplementation((path: string) => {
      if (path === "/leads/1") return new Promise((resolve) => { resolveA = resolve; });
      if (path === "/leads/2") return Promise.resolve(LEAD2);
      return Promise.reject(new Error(`not used: ${path}`));
    });
    const view = renderHook(() => useInboxState());
    await waitFor(() => expect(view.result.current.selectedLeadId).toBe(1));
    await waitFor(() => expect(apiGetMock.mock.calls.map((call) => call[0])).toContain("/leads/1"));
    act(() => {
      view.result.current.selectLead(2);
    });
    await waitFor(() => expect(view.result.current.leadDetail?.id).toBe(2));
    expect(view.result.current.cardForm.customer_name).toBe("Bob");
    await act(async () => {
      resolveA(LEAD);
    });
    expect(view.result.current.leadDetail?.id).toBe(2);
    expect(view.result.current.cardForm.customer_name).toBe("Bob");
    view.unmount();
  });

  it("marks only the failed conversation, and a cached conversation shows at once", async () => {
    const view = renderHook(() => useInboxState());
    await waitFor(() => expect(view.result.current.messagesData).not.toBeNull());
    act(() => {
      view.result.current.selectLead(2);
    });
    await waitFor(() => expect(getMessagesMock.mock.calls.map((call) => call[0])).toContain(2));
    await waitFor(() => expect(view.result.current.messagesData).not.toBeNull());

    getMessagesMock.mockRejectedValue(new Error("boom"));
    act(() => {
      view.result.current.selectLead(1);
    });
    await waitFor(() => expect(view.result.current.messagesData).toBeNull());

    getMessagesMock.mockImplementation(never);
    act(() => {
      view.result.current.selectLead(2);
    });
    expect(view.result.current.messagesData).not.toBeNull();
    view.unmount();
  });

  it("when switching A to B during a karte save, the late save for A does not fill the form", async () => {
    let resolvePatch: (value: unknown) => void = () => {};
    apiPatchMock.mockImplementation(() => new Promise((resolve) => { resolvePatch = resolve; }));
    apiGetMock.mockImplementation((path: string) => {
      if (path === "/leads/1") return Promise.resolve(LEAD);
      if (path === "/leads/2") return Promise.resolve(LEAD2);
      return Promise.reject(new Error(`not used: ${path}`));
    });
    const view = await openOnce();
    act(() => {
      view.result.current.handleCardFieldChange("customer_name", "Alice X");
    });
    let saving: Promise<void> = Promise.resolve();
    act(() => {
      saving = view.result.current.handleCardFieldBlur();
    });
    expect(apiPatchMock.mock.calls.map((call) => call[0])).toEqual(["/leads/1"]);
    act(() => {
      view.result.current.selectLead(2);
    });
    await waitFor(() => expect(view.result.current.leadDetail?.id).toBe(2));
    await waitFor(() => expect(view.result.current.cardForm.customer_name).toBe("Bob"));
    await act(async () => {
      resolvePatch({ ...LEAD, customer_name: "Alice X" });
      await saving;
    });
    expect(view.result.current.leadDetail?.id).toBe(2);
    expect(view.result.current.cardForm.customer_name).toBe("Bob");
    // 保存の中身は A の写しに入る
    expect(
      queryClient.getQueryData<{ customer_name: string }>(["api", "uid-A", "leads", "1", { query: "" }])?.customer_name,
    ).toBe("Alice X");
    view.unmount();
  });

  it("when switching to a filter with no cache, never shows an empty list without the loading mark", async () => {
    const frames: { loading: boolean; count: number }[] = [];
    const view = renderHook(() => {
      const state = useInboxState();
      frames.push({ loading: state.convLoading, count: state.conversations.length });
      return state;
    });
    await waitFor(() => expect(view.result.current.conversations).toHaveLength(2));
    await waitFor(() => expect(view.result.current.convLoading).toBe(false));
    listConversationsMock.mockImplementation(never);
    const before = frames.length;
    act(() => {
      view.result.current.setPlatformFilter("instagram");
    });
    const after = frames.slice(before);
    expect(after.length).toBeGreaterThan(0);
    // 切り替えた後のどのコマも、一覧が空なら読み込み中の印が出ている
    expect(after.filter((frame) => frame.count === 0 && !frame.loading)).toEqual([]);
    expect(view.result.current.convLoading).toBe(true);
    expect(view.result.current.conversations).toEqual([]);
    view.unmount();
  });

  it("when going back to a filter that failed before, never shows an empty list without the loading mark", async () => {
    const frames: { loading: boolean; count: number }[] = [];
    const view = renderHook(() => {
      const state = useInboxState();
      frames.push({ loading: state.convLoading, count: state.conversations.length });
      return state;
    });
    await waitFor(() => expect(view.result.current.conversations).toHaveLength(2));
    await waitFor(() => expect(view.result.current.convLoading).toBe(false));
    // instagram の条件で 1 回失敗させる（ApiError でも TypeError でもないので、送り直しの数えに入らずすぐ失敗になる）
    listConversationsMock.mockImplementation(() => Promise.reject(new Error("boom")));
    act(() => {
      view.result.current.setPlatformFilter("instagram");
    });
    await waitFor(() => expect(view.result.current.convError).toBe("inbox.fetchError"));
    // 写しのある条件（all）へ戻し、取り終えるまで待つ（返す一覧を 1 件にして、届いたことを見分ける）
    listConversationsMock.mockReset().mockResolvedValue({ conversations: [conv(1, "Alice", "page-1")], next_cursor: null });
    act(() => {
      view.result.current.setPlatformFilter("all");
    });
    await waitFor(() => expect(view.result.current.conversations).toHaveLength(1));
    await waitFor(() => expect(view.result.current.convError).toBe(""));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // 前に失敗した instagram へもう一度切り替える（今度は返さない）
    listConversationsMock.mockImplementation(never);
    const before = frames.length;
    act(() => {
      view.result.current.setPlatformFilter("instagram");
    });
    const after = frames.slice(before);
    expect(after.length).toBeGreaterThan(0);
    // 切り替えた後のどのコマも、一覧が空なら読み込み中の印が出ている
    expect(after.filter((frame) => frame.count === 0 && !frame.loading)).toEqual([]);
    expect(view.result.current.convLoading).toBe(true);
    expect(view.result.current.conversations).toEqual([]);
    view.unmount();
  });

  it("when going back to a failed filter, a late response for the previous filter does not show an empty list without the loading mark", async () => {
    const frames: { loading: boolean; count: number }[] = [];
    const view = renderHook(() => {
      const state = useInboxState();
      frames.push({ loading: state.convLoading, count: state.conversations.length });
      return state;
    });
    await waitFor(() => expect(view.result.current.conversations).toHaveLength(2));
    await waitFor(() => expect(view.result.current.convLoading).toBe(false));
    // instagram の条件で 1 回失敗させる
    listConversationsMock.mockImplementation(() => Promise.reject(new Error("boom")));
    act(() => {
      view.result.current.setPlatformFilter("instagram");
    });
    await waitFor(() => expect(view.result.current.convError).toBe("inbox.fetchError"));
    // 写しのある条件（all）へ戻す。この取得は手で返すまで返さない
    let resolveAll: ((value: unknown) => void) | undefined;
    listConversationsMock.mockReset().mockImplementation(
      () => new Promise((resolve) => {
        resolveAll = resolve;
      }),
    );
    act(() => {
      view.result.current.setPlatformFilter("all");
    });
    await waitFor(() => expect(listConversationsMock).toHaveBeenCalledTimes(1));
    // all の取得が返る前に、前に失敗した instagram へもう一度切り替える（今度は返さない）
    listConversationsMock.mockImplementation(never);
    const before = frames.length;
    act(() => {
      view.result.current.setPlatformFilter("instagram");
    });
    // 遅れて all の取得が返る
    await act(async () => {
      resolveAll?.({ conversations: [conv(1, "Alice", "page-1")], next_cursor: null });
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    const after = frames.slice(before);
    expect(after.length).toBeGreaterThan(0);
    // 切り替えた後のどのコマも、一覧が空なら読み込み中の印が出ている
    expect(after.filter((frame) => frame.count === 0 && !frame.loading)).toEqual([]);
    expect(view.result.current.convLoading).toBe(true);
    expect(view.result.current.conversations).toEqual([]);
    view.unmount();
  });
});
