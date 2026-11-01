/**
 * 受信箱「新規」バッジ: PC の自動選択では「開いた」扱いにしない（design.md 修正2）。
 *
 * 独立審査（Opus）のレビュー指摘（2026-10-15）:
 *   PC（非モバイル）で受信箱を開くと、先頭会話が自動選択される（useInboxState.ts の
 *   自動選択の効果）。これが selectedLeadId を立てるため、素朴な実装では
 *   markRead(selectedLeadId, true) が発火し、先頭会話の「新規」バッジが
 *   自分で開いていないのに消えてしまう（PO 決定「案ア」に反する）。
 *
 * 2026-10-17 の独立審査（docs/handoff/inbox-new-assignment-badge/review-opus.md、
 * 別ブランチ）で採用になった指摘のうち、コード/テスト側5件（D2/D3/D6/D7/D8）を
 * ここで固定する:
 *   D2: 自動選択された会話を明示的にもう一度クリックしてもバッジが消える。
 *   D3: 自動選択では URL に lead_id を書かない。
 *   D6: （本ファイルでは対象外。useInboxState.ts 側のコメント修正）
 *   D7: 一括既読（handleMarkAllRead）では新規バッジ（is_new_assignment）を消さない。
 *   D8: markRead の呼び出し全件を toEqual で固定する（toHaveBeenCalledWith は
 *       「どれか1回が一致」で通ってしまうため不十分）。
 *
 * 検証方法:
 *   useInboxState は useSearchParams / useNavigate（react-router-dom）、
 *   useInboxSSE、useIsMobile、lib/api、lib/messages に依存するため、
 *   他のフックテスト（useRealtimeRefresh.test.tsx）・コンポーネントテスト
 *   （InboxMessageThread.discordSendError.test.tsx）と同じ作法で
 *   vi.mock により外部依存を切り離し、renderHook で直接検証する。
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { queryClient } from "../../lib/query/apiQuery";

// 引数の型を明示する（省略すると vi.fn が 0 引数と推論され、
// 下の markRead ラッパー経由の呼び出しが tsc で TS2554 になる）
const markReadMock = vi.fn((_leadId: number, _opened?: boolean) =>
  Promise.resolve({ marked_count: 0 }),
);
const listConversationsMock = vi.fn();
// setSearchParams をモジュール先頭の変数に取り出し、呼ばれたか／何を渡したかを
// テストから検査できるようにする（D3 の関所）。
const setSearchParamsMock = vi.fn();
let searchParamsStub = new URLSearchParams();

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [searchParamsStub, setSearchParamsMock],
}));
// t を毎レンダー新規生成しないよう安定した参照にする（本物の react-i18next の t は
// 安定している）。不安定だと loadMessages（useCallback の依存に t を持つ）の参照が
// レンダー毎に変わり、selectedLeadId 変更時の効果が無限に再実行されてしまい、
// markRead の呼び出し回数を固定する D8 のテストが書けない。
const stableT = (key: string) => key;
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: stableT }),
}));
// PC（非モバイル）判定に固定。自動選択はモバイルでは発火しない分岐のため。
vi.mock("../../hooks/useIsMobile", () => ({ useIsMobile: () => false }));
vi.mock("../../hooks/useInboxSSE", () => ({ useInboxSSE: () => undefined }));
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "uid-test" }, loading: false }),
}));
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
vi.mock("../../lib/messages", async (importOriginal) => ({
  conversationsPath: (await importOriginal<typeof import("../../lib/messages")>()).conversationsPath,
  messagesPath: (await importOriginal<typeof import("../../lib/messages")>()).messagesPath,
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
    queryClient.clear();
    markReadMock.mockClear();
    markReadMock.mockImplementation((_leadId: number, _opened?: boolean) =>
      Promise.resolve({ marked_count: 0 }),
    );
    setSearchParamsMock.mockClear();
    listConversationsMock.mockReset().mockResolvedValue(CONV_FIXTURE);
    searchParamsStub = new URLSearchParams();
  });

  it("sends opened=false on desktop auto-select of the first conversation (keeps the badge)", async () => {
    const { result } = renderHook(() => useInboxState());

    await waitFor(() => expect(result.current.selectedLeadId).toBe(1));
    await waitFor(() => expect(markReadMock).toHaveBeenCalled());

    // D8: toHaveBeenCalledWith は「どれか1回が一致」で通ってしまうため、
    // 呼び出し全件を固定する（この時点で markRead は1回だけ呼ばれているはず）。
    expect(markReadMock.mock.calls).toEqual([[1, false]]);
  });

  it("sends opened=true when the conversation is opened explicitly via the lead_id URL param", async () => {
    searchParamsStub = new URLSearchParams("lead_id=1");

    const { result } = renderHook(() => useInboxState());

    await waitFor(() => expect(result.current.selectedLeadId).toBe(1));
    await waitFor(() => expect(markReadMock).toHaveBeenCalled());

    // D8: 呼び出し全件を固定する。
    expect(markReadMock.mock.calls).toEqual([[1, true]]);
  });

  // D2 の関所: PC の自動選択で先頭会話が選ばれた後、同じ会話をもう一度明示的に
  // 選び直すとバッジが消えること（selectLead が同じ id のとき markRead(id, true) を
  // 直接呼ぶこと）を固定する。
  it("clears the badge when re-selecting the already auto-selected conversation explicitly (D2 gate)", async () => {
    const { result } = renderHook(() => useInboxState());

    await waitFor(() => expect(result.current.selectedLeadId).toBe(1));
    await waitFor(() => expect(markReadMock).toHaveBeenCalled());
    // 自動選択分の呼び出し (1, false) をここで一度クリアし、以降の呼び出しだけを見る。
    markReadMock.mockClear();

    act(() => {
      result.current.selectLead(1);
    });

    await waitFor(() => expect(markReadMock).toHaveBeenCalled());
    expect(markReadMock.mock.calls).toEqual([[1, true]]);

    await waitFor(() =>
      expect(
        result.current.conversations.find((c) => c.lead_id === 1)?.is_new_assignment,
      ).toBe(false),
    );
  });

  // D3 の関所: 自動選択のときは setSearchParams が呼ばれない（URL に lead_id を
  // 書かない）こと、かつ明示操作では lead_id が書かれることを固定する。
  it("does not write lead_id to the URL on auto-select, but does on explicit selectLead (D3 gate)", async () => {
    const { result } = renderHook(() => useInboxState());

    await waitFor(() => expect(result.current.selectedLeadId).toBe(1));
    await waitFor(() => expect(markReadMock).toHaveBeenCalled());

    // 自動選択だけでは setSearchParams は呼ばれない。
    expect(setSearchParamsMock).not.toHaveBeenCalled();

    act(() => {
      result.current.selectLead(1);
    });

    // 明示操作では lead_id が URL に書かれる。
    await waitFor(() => expect(setSearchParamsMock).toHaveBeenCalled());
    const [params] = setSearchParamsMock.mock.calls[0] as [URLSearchParams, unknown];
    expect(params.get("lead_id")).toBe("1");
  });

  // D7 の関所: 一括既読（handleMarkAllRead）は unread_count を 0 にするが、
  // 新規バッジ（is_new_assignment）は消さないことを固定する。
  // useInboxState.ts の markRead 内 `...(opened ? { is_new_assignment: false } : {})`
  // を外すと（常に消す実装に戻すと）このテストは赤くなる想定（実施済み・報告参照）。
  it("bulk mark-all-read clears unread_count but keeps the new-assignment badge (D7 gate)", async () => {
    const { result } = renderHook(() => useInboxState());

    await waitFor(() => expect(result.current.selectedLeadId).toBe(1));
    await waitFor(() => expect(markReadMock).toHaveBeenCalled());

    // 一括既読の呼び出しだけ marked_count: 1（既読化が実際に効いた）を返すようにする。
    markReadMock.mockResolvedValueOnce({ marked_count: 1 });

    await act(async () => {
      await result.current.handleMarkAllRead();
    });

    await waitFor(() => {
      const conv = result.current.conversations.find((c) => c.lead_id === 1);
      expect(conv?.unread_count).toBe(0);
    });
    const conv = result.current.conversations.find((c) => c.lead_id === 1);
    expect(conv?.is_new_assignment).toBe(true);
  });
});
