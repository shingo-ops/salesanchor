/* eslint-disable local/no-japanese-literal -- テスト: PO 指定の日本語文言・テスト名を検証する（ADR-159） */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";

const navigateMock = vi.fn();
let permissions: string[] = [];

vi.mock("react-router-dom", () => ({ useNavigate: () => navigateMock }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "ja" } }),
}));
vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({ hasPermission: (p: string) => permissions.includes(p) }),
}));
vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(() => Promise.resolve([])), post: vi.fn(() => Promise.resolve({})) },
}));

import { InboxMessageThread } from "./InboxMessageThread";

type Props = ComponentProps<typeof InboxMessageThread>;

function renderThread(overrides: Partial<Props>) {
  const submitSend = vi.fn();
  const retrySend = vi.fn();
  const props = {
    selectedLeadId: 1,
    selectedConversation: null,
    leadDetail: null,
    messagesData: null,
    msgLoading: false,
    msgError: null,
    avatarErrors: new Set<number>(),
    handleAvatarError: vi.fn(),
    handleMarkUnread: vi.fn(),
    handleExclude: vi.fn(),
    handleDeleteLead: vi.fn(),
    showKartePanel: false,
    openKartePanel: vi.fn(),
    closeKartePanel: vi.fn(),
    inboxSettings: { showRightPanel: false },
    messageListRef: { current: null },
    draft: "入力中の文",
    setDraft: vi.fn(),
    sending: false,
    sendError: "Send failed",
    sendErrorReason: "generic",
    sendErrorCode: null,
    sendDisabled: false,
    canSend: true,
    discordChannelMissing: false,
    trimmedDraft: "入力中の文",
    submitSend,
    retrySend,
    handleKeyDown: vi.fn(),
    attachedFile: null,
    setAttachedFile: vi.fn(),
    clearAttachment: vi.fn(),
    recipientLanguageSetting: "auto",
    setRecipientLanguage: vi.fn(),
    sendReaction: vi.fn(),
    deleteReaction: vi.fn(),
    ...overrides,
  } as unknown as Props;
  render(<InboxMessageThread {...props} />);
  return { submitSend, retrySend };
}

beforeEach(() => {
  navigateMock.mockClear();
  permissions = [];
});
afterEach(cleanup);

describe("InboxMessageThread Discord 送信エラー表示（ADR-159）", () => {
  it("STAFF_EN_NAME_REQUIRED: 文言とボタンを出し、押すとアカウント設定へ遷移する", () => {
    renderThread({ sendErrorReason: "STAFF_EN_NAME_REQUIRED" });
    expect(screen.getByRole("alert").textContent).toContain("inbox.sendError.discordEnNameRequired");
    fireEvent.click(screen.getByRole("button", { name: "inbox.sendError.ctaOpenAccountSettings" }));
    expect(navigateMock).toHaveBeenCalledWith("/account/settings");
  });

  it("STAFF_EN_NAME_INVALID: アカウント設定へ遷移するボタンを出す", () => {
    renderThread({ sendErrorReason: "STAFF_EN_NAME_INVALID" });
    expect(screen.getByRole("alert").textContent).toContain("inbox.sendError.discordEnNameInvalid");
    fireEvent.click(screen.getByRole("button", { name: "inbox.sendError.ctaOpenAccountSettings" }));
    expect(navigateMock).toHaveBeenCalledWith("/account/settings");
  });

  it("DISCORD_SEND_FAILED: 「もう一度送る」で再送する（遷移しない）", () => {
    const { submitSend, retrySend } = renderThread({ sendErrorReason: "DISCORD_SEND_FAILED" });
    expect(screen.getByRole("alert").textContent).toContain("inbox.sendError.discordSendFailed");
    fireEvent.click(screen.getByRole("button", { name: "inbox.sendError.ctaRetry" }));
    // 下書き（draft_id）経由の送信でも同じ紐付けで再送できるよう、専用の retrySend を呼ぶ
    expect(retrySend).toHaveBeenCalledTimes(1);
    expect(submitSend).not.toHaveBeenCalled();
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("DISCORD_SEND_FAILED: 送信中は再送ボタンを押せない", () => {
    renderThread({ sendErrorReason: "DISCORD_SEND_FAILED", sending: true });
    const button = screen.getByRole("button", { name: "inbox.sendError.ctaRetry" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("DISCORD_WEBHOOK_PERMISSION: 管理者には Discord 設定へのボタンを出す", () => {
    permissions = ["tenant.profile.edit"];
    renderThread({ sendErrorReason: "DISCORD_WEBHOOK_PERMISSION" });
    expect(screen.getByRole("alert").textContent).toContain("inbox.sendError.discordWebhookPermissionAdmin");
    fireEvent.click(screen.getByRole("button", { name: "inbox.sendError.ctaOpenDiscordConfig" }));
    expect(navigateMock).toHaveBeenCalledWith("/admin/discord-config");
  });

  it("DISCORD_WEBHOOK_PERMISSION: 管理者以外にはボタンを出さず管理者への連絡を案内する", () => {
    renderThread({ sendErrorReason: "DISCORD_WEBHOOK_PERMISSION" });
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("inbox.sendError.discordWebhookPermissionStaff");
    expect(alert.querySelector("button")).toBeNull();
  });

  it("従来の送信エラー（generic）は文言のみでボタンを出さない", () => {
    renderThread({ sendErrorReason: "generic" });
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("inbox.sendError.generic");
    expect(alert.querySelector("button")).toBeNull();
  });

  it("送信失敗後も入力した文が入力欄に残る", () => {
    renderThread({ sendErrorReason: "DISCORD_SEND_FAILED", draft: "入力中の文" });
    expect((screen.getByDisplayValue("入力中の文") as HTMLTextAreaElement).value).toBe("入力中の文");
  });
});
