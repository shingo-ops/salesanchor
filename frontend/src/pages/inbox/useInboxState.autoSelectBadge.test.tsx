/**
 * 受信箱「新規」バッジ: PC の自動選択では「開いた」扱いにしない（design.md 修正2）。
 *
 * 独立審査（Opus）のレビュー指摘（2026-10-15）:
 *   PC（非モバイル）で受信箱を開くと、先頭会話が自動選択される（useInboxState.ts の
 *   自動選択の効果）。これが selectedLeadId を立てるため、素朴な実装では
 *   markRead(selectedLeadId, true) が発火し、先頭会話の「新規」バッジが
 *   自分で開いていないのに消えてしまう（PO 決定「案ア」に反する）。
 *
 * 検証方法:
 *   useInboxState は useSearchParams / useNavigate（react-router-dom）、
 *   useInboxSSE、useIsMobile、lib/api、lib/messages に依存するため、
 *   他のフックテスト（useRealtimeRefresh.test.tsx）・コンポーネントテスト
 *   （InboxMessageThread.discordSendError.test.tsx）と同じ作法で
 *   vi.mock により外部依存を切り離し、renderHook で直接検証する。
 */
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// 引数の型を明示する（省略すると vi.fn が 0 引数と推論され、
// 下の markRead ラッパー経由の呼び出しが tsc で TS2554 になる）
const markReadMock = vi.fn((_leadId: number, _opened?: boolean) =>
  Promise.resolve({ marked_count: 0 }),
);
const listConversationsMock = vi.fn();
let searchParamsStub = new URLSearchParams();

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [searchParamsStub, vi.fn()],
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
// PC（非モバイル）判定に固定。自動選択はモバイルでは発火しない分岐のため。
vi.mock("../../hooks/useIsMobile", () => ({ useIsMobile: () => false }));
vi.mock("../../hooks/useInboxSSE", () => ({ useInboxSSE: () => undefined }));
vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(() => Promise.reject(new Error("not used in this test"))),
    post: vi.fn(() => Promise.resolve({})),
    patch: vi.fn(() => Promise.resolve({})),
    delete: vi.fn(() => Promise.resolve({})),
  },
  ApiError: class ApiError extends Error {
    status?: number;
  },
}));
vi.mock("../../lib/messages", () => ({
  listConversations: (...args: unknown[]) => listConversationsMock(...args),
  markRead: (...args: [number, boolean?]) => markReadMock(...args),
  markUnread: vi.fn(() => Promise.resolve({ unmarked_count: 0 })),
  getMessages: vi.fn(() => Promise.resolve({ messages: [] })),
  sendMessage: vi.fn(),
  sendImageMessage: vi.fn(),
  inferPlatform: vi.fn(() => "messenger"),
}));

import { useInboxState } from "./useInboxState";

const CONV_FIXTURE = {
  conversations: [
    {
      lead_id: 1,
      lead_code: "LD-00001",
      customer_name: "Alice",
      lead_status: null,
      platform: "messenger",
      page_id: null,
      last_message_text: "hi",
      last_message_at: "2026-10-15T00:00:00Z",
      last_message_direction: "inbound",
      unread_count: 1,
      messaging_window_expires_at: null,
      is_new_assignment: true,
    },
  ],
  next_cursor: null,
};

describe("useInboxState - new-assignment badge: auto-select vs explicit open", () => {
  beforeEach(() => {
    markReadMock.mockClear();
    listConversationsMock.mockReset().mockResolvedValue(CONV_FIXTURE);
    searchParamsStub = new URLSearchParams();
  });

  it("sends opened=false on desktop auto-select of the first conversation (keeps the badge)", async () => {
    const { result } = renderHook(() => useInboxState());

    await waitFor(() => expect(result.current.selectedLeadId).toBe(1));
    await waitFor(() => expect(markReadMock).toHaveBeenCalled());

    expect(markReadMock).toHaveBeenCalledWith(1, false);
  });

  it("sends opened=true when the conversation is opened explicitly via the lead_id URL param", async () => {
    searchParamsStub = new URLSearchParams("lead_id=1");

    const { result } = renderHook(() => useInboxState());

    await waitFor(() => expect(result.current.selectedLeadId).toBe(1));
    await waitFor(() => expect(markReadMock).toHaveBeenCalled());

    expect(markReadMock).toHaveBeenCalledWith(1, true);
  });
});
