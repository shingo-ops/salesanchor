/**
 * ADR-1090 §4-3: カルテの欄を離れたときの保存で、段階（status）と registration_completed を送らない試験。
 * 開いている間に入金などで自動で既存顧客になった人を、手元の古い段階で戻さないため。
 * 試験の題は英語（lint の決まり local/no-japanese-literal）。
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));
const listConversationsMock = vi.fn();
const getMessagesMock = vi.fn();
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
    markRead: vi.fn(() => Promise.resolve({ marked_count: 0 })),
    markUnread: vi.fn(() => Promise.resolve({ unmarked_count: 0 })),
    getMessages: (...args: unknown[]) => getMessagesMock(...args),
    sendMessage: vi.fn(),
    sendImageMessage: vi.fn(),
    inferPlatform: vi.fn(() => "messenger"),
  };
});

import { queryClient } from "../../lib/query/apiQuery";
import { useInboxState } from "./useInboxState";

const conv = {
  lead_id: 1,
  lead_code: "LD-00001",
  customer_name: "Alice",
  lead_status: null,
  platform: "messenger",
  page_id: "page-1",
  last_message_text: "hi",
  last_message_at: "2026-11-01T00:00:00Z",
  last_message_direction: "inbound",
  unread_count: 1,
  messaging_window_expires_at: null,
  is_new_assignment: false,
};
// 開いた時点の控え: 商談中。registration_completed も入っている
const LEAD = { id: 1, lead_code: "LD-00001", customer_name: "Alice", status: "negotiating", registration_completed: true };

describe("useInboxState - karte blur save (ADR-1090)", () => {
  beforeEach(() => {
    queryClient.clear();
    localStorage.clear();
    auth.user = { uid: "uid-A" };
    listConversationsMock.mockReset().mockResolvedValue({ conversations: [conv], next_cursor: null });
    getMessagesMock.mockReset().mockResolvedValue({ lead: { id: 1, platform: "messenger" }, messages: [] });
    apiGetMock.mockReset().mockImplementation((path: string) =>
      path === "/leads/1" ? Promise.resolve(LEAD) : Promise.reject(new Error(`not used: ${path}`)),
    );
    apiPatchMock.mockReset().mockResolvedValue({ ...LEAD, customer_name: "Alice renamed" });
  });

  it("does not send status or registration_completed in the PATCH", async () => {
    const view = renderHook(() => useInboxState());
    await waitFor(() => expect(view.result.current.leadDetail).not.toBeNull());
    expect(view.result.current.cardForm.status).toBe("negotiating");
    act(() => {
      view.result.current.handleCardFieldChange("customer_name", "Alice renamed");
    });
    await act(async () => {
      await view.result.current.handleCardFieldBlur();
    });
    expect(apiPatchMock).toHaveBeenCalledTimes(1);
    const [path, payload] = apiPatchMock.mock.calls[0] as [string, Record<string, unknown>];
    expect(path).toBe("/leads/1");
    expect(payload.customer_name).toBe("Alice renamed");
    expect("status" in payload).toBe(false);
    expect("registration_completed" in payload).toBe(false);
    expect("id" in payload).toBe(false);
    view.unmount();
  });
});
