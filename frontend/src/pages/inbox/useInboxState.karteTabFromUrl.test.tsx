/**
 * ADR-1089: 住所の lead_id で開いた会話でも、カルテの最初のタブは段階の最初のタブになる。
 * 段階はカルテ（/leads/<id>）の status から読む。1 回だけ決め、利用者が選んだタブは読み直しで戻さない。
 * 試験の題は英語（lint の決まり local/no-japanese-literal）。
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { queryClient } from "../../lib/query/apiQuery";

const listConversationsMock = vi.fn();
const apiGetMock = vi.fn();
let searchParamsStub = new URLSearchParams();

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [searchParamsStub, vi.fn()],
}));
const stableT = (key: string) => key;
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: stableT }),
}));
vi.mock("../../hooks/useIsMobile", () => ({ useIsMobile: () => false }));
vi.mock("../../hooks/useInboxSSE", () => ({ useInboxSSE: () => undefined }));
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "uid-test" }, loading: false }),
}));
vi.mock("../../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => apiGetMock(...args),
    post: vi.fn(() => Promise.resolve({})),
    patch: vi.fn(() => Promise.resolve({})),
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
    markRead: vi.fn(() => Promise.resolve({ marked_count: 0 })),
    markUnread: vi.fn(() => Promise.resolve({ unmarked_count: 0 })),
    getMessages: vi.fn(() => Promise.resolve({ messages: [] })),
    sendMessage: vi.fn(),
    sendImageMessage: vi.fn(),
    inferPlatform: vi.fn(() => "messenger"),
  };
});

import { useInboxState } from "./useInboxState";

function openFromUrl(status: string) {
  searchParamsStub = new URLSearchParams("lead_id=1");
  apiGetMock.mockImplementation((path: string) => {
    if (path === "/leads/1") return Promise.resolve({ id: 1, status });
    return Promise.reject(new Error(`unexpected path: ${path}`));
  });
  return renderHook(() => useInboxState());
}

describe("useInboxState - karte first tab when opened from URL (ADR-1089)", () => {
  beforeEach(() => {
    queryClient.clear();
    apiGetMock.mockReset();
    listConversationsMock.mockReset().mockResolvedValue({ conversations: [], next_cursor: null });
    searchParamsStub = new URLSearchParams();
  });

  it("opens the company tab for existing_customer", async () => {
    const { result } = openFromUrl("existing_customer");
    await waitFor(() => expect(result.current.leadDetail?.id).toBe(1));
    await waitFor(() => expect(result.current.karteTab).toBe("company"));
  });

  it("opens the company tab for follow_up_short", async () => {
    const { result } = openFromUrl("follow_up_short");
    await waitFor(() => expect(result.current.leadDetail?.id).toBe(1));
    await waitFor(() => expect(result.current.karteTab).toBe("company"));
  });

  it("opens the deal tab for lead and negotiating", async () => {
    for (const status of ["lead", "negotiating"]) {
      queryClient.clear();
      const { result, unmount } = openFromUrl(status);
      await waitFor(() => expect(result.current.leadDetail?.id).toBe(1));
      await waitFor(() => expect(result.current.karteTab).toBe("deal"));
      unmount();
    }
  });

  it("keeps the tab the user picked after the karte is read again", async () => {
    const { result, rerender } = openFromUrl("follow_up_short");
    await waitFor(() => expect(result.current.karteTab).toBe("company"));

    act(() => {
      result.current.setKarteTab("contact");
    });
    rerender();

    expect(result.current.karteTab).toBe("contact");
  });
});
