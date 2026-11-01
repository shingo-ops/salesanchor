import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { SecretaryChat } from "./SecretaryChat";

const mock = vi.hoisted(() => ({
  postWithTimeout: vi.fn(),
  post: vi.fn(),
  get: vi.fn(),
  features: new Set<string>(),
  superAdmin: false,
  permissions: new Set<string>(),
}));

vi.mock("../../lib/api", () => ({
  api: { postWithTimeout: mock.postWithTimeout, post: mock.post, get: mock.get },
  ApiError: class ApiError extends Error {
    status: number;
    responseDetail: unknown;
    constructor(message: string, status: number, responseDetail: unknown) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.responseDetail = responseDetail;
    }
  },
}));
vi.mock("../../hooks/useFeatures", () => ({
  useFeatures: () => ({ loading: false, isEnabled: (k: string) => mock.features.has(k) }),
}));
vi.mock("../../hooks/useSuperAdmin", () => ({
  useSuperAdmin: () => ({ loading: false, isSuperAdmin: mock.superAdmin }),
}));
vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({ loading: false, hasPermission: (k: string) => mock.permissions.has(k) }),
}));

import { ApiError } from "../../lib/api";

const FAB = "Ask the assistant";

const allowAll = () => {
  mock.features = new Set(["secretary_chat"]);
  mock.superAdmin = true;
  mock.permissions = new Set(["customers.view", "invoices.create"]);
};

const none = { companies: [], contacts: [] };
const invoiceReply = (overrides: Record<string, unknown> = {}) => ({
  kind: "invoice",
  draft: {
    company_name: "Acme",
    contact_name: "Taro",
    items: [{ product_name: "Widget", quantity: 2, unit_price: null }],
    due_date: null,
    notes: null,
    currency: "JPY",
    ...overrides,
  },
  candidates: { companies: [{ id: 1, name: "Acme" }], contacts: [{ id: 2, name: "Taro" }] },
});
const eventReply = {
  kind: "event",
  draft: {
    title: "Meeting",
    start: "2026-11-02T10:00:00+09:00",
    end: "2026-11-02T11:00:00+09:00",
    is_all_day: false,
    location: null,
    description: null,
    calendar_type: "personal",
  },
  candidates: none,
};

const renderChat = () =>
  render(
    <MemoryRouter>
      <SecretaryChat isMobile={false} />
    </MemoryRouter>,
  );

async function sendMessage(text = "hello") {
  fireEvent.click(screen.getByRole("button", { name: FAB }));
  const box = await screen.findByLabelText(/Tell me what you need/);
  fireEvent.change(box, { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

beforeEach(async () => {
  vi.clearAllMocks();
  allowAll();
  mock.get.mockResolvedValue([]);
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("SecretaryChat visibility", () => {
  it("shows the button only when the feature and super admin are both on", () => {
    mock.features = new Set();
    const { unmount } = renderChat();
    expect(screen.queryByRole("button", { name: FAB })).toBeNull();
    unmount();

    allowAll();
    mock.superAdmin = false;
    const second = renderChat();
    expect(screen.queryByRole("button", { name: FAB })).toBeNull();
    second.unmount();

    allowAll();
    renderChat();
    expect(screen.getByRole("button", { name: FAB })).toBeTruthy();
  });

  it.each(["customers.view", "invoices.create"])("hides the button without %s", (missing) => {
    mock.permissions.delete(missing);
    renderChat();
    expect(screen.queryByRole("button", { name: FAB })).toBeNull();
  });

  it("hides the button on a 403", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("forbidden", 403, "forbidden"));
    renderChat();
    await sendMessage();
    await waitFor(() => expect(screen.queryByRole("button", { name: FAB })).toBeNull());
  });
});

describe("SecretaryChat sending", () => {
  it("calls postWithTimeout with the 100 second limit", async () => {
    mock.postWithTimeout.mockResolvedValue({ kind: "unknown", draft: { reply: "ok" }, candidates: none });
    renderChat();
    await sendMessage("make something");
    await screen.findByText("ok");
    expect(mock.postWithTimeout).toHaveBeenCalledWith("/assistant/messages", { text: "make something" }, 100000);
  });

  it("shows the reply as plain text, not HTML", async () => {
    mock.postWithTimeout.mockResolvedValue({ kind: "unknown", draft: { reply: "<b>x</b>" }, candidates: none });
    const { container } = renderChat();
    await sendMessage();
    await screen.findByText("<b>x</b>");
    expect(document.body.querySelector(".comp-chat-bubble b")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
  });

  it("shows the timeout text on AbortError", async () => {
    const abort = new Error("aborted");
    abort.name = "AbortError";
    mock.postWithTimeout.mockRejectedValue(abort);
    renderChat();
    await sendMessage();
    expect(await screen.findByText(/took too long/)).toBeTruthy();
  });

  it("shows the notReady text on 503 not_ready", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 503, { code: "not_ready" }));
    renderChat();
    await sendMessage();
    expect(await screen.findByText("The assistant is not ready yet")).toBeTruthy();
  });

  it("shows the generic text for other failures, and error status only on the assistant bubble", async () => {
    mock.postWithTimeout.mockRejectedValue(new Error("network"));
    renderChat();
    await sendMessage("hi");
    expect(await screen.findByText(/Something went wrong/)).toBeTruthy();
    expect(document.body.querySelectorAll(".comp-chat-bubble--outbound.comp-chat-bubble--error").length).toBe(0);
    expect(document.body.querySelectorAll(".comp-chat-bubble--inbound.comp-chat-bubble--error").length).toBe(1);
  });
});

describe("SecretaryChat invoice draft", () => {
  it("blocks Create while a unit price is empty, then sends only the decided fields", async () => {
    mock.postWithTimeout.mockResolvedValue(invoiceReply());
    mock.post.mockResolvedValue({ id: 77 });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect(create.disabled).toBe(true);
    expect(mock.post).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "1500" } });
    expect(create.disabled).toBe(false);
    fireEvent.click(create);

    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(mock.post).toHaveBeenCalledWith("/invoices", {
      company_id: 1,
      contact_id: 2,
      currency: "JPY",
      due_date: null,
      notes: null,
      items: [{ product_name: "Widget", quantity: 2, unit_price: 1500 }],
    });
    expect(await screen.findByText(/Invoice created/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open invoice" }).getAttribute("href")).toBe("/invoices/77");
  });

  it("blocks Create until company and contact are decided", async () => {
    mock.postWithTimeout.mockResolvedValue({
      ...invoiceReply({ items: [{ product_name: "Widget", quantity: 1, unit_price: 100 }] }),
      candidates: none,
    });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect(create.disabled).toBe(true);
  });

  it.each(["0", "1.5"])("blocks Create when the quantity is %s", async (qty) => {
    mock.postWithTimeout.mockResolvedValue(
      invoiceReply({ items: [{ product_name: "Widget", quantity: 1, unit_price: 100 }] }),
    );
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect(create.disabled).toBe(false);
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: qty } });
    expect(create.disabled).toBe(true);
  });
});

describe("SecretaryChat event draft", () => {
  it("starts as personal and only mentions the whole company when shared", async () => {
    mock.postWithTimeout.mockResolvedValue(eventReply);
    renderChat();
    await sendMessage();
    const select = (await screen.findByLabelText("Visibility")) as HTMLSelectElement;
    expect(select.value).toBe("personal");
    expect(screen.queryByText("Visible to everyone in your company")).toBeNull();

    fireEvent.change(select, { target: { value: "shared" } });
    const note = screen.getByText("Visible to everyone in your company");
    expect(note.textContent).not.toMatch(/Google/i);
  });

  it("posts the event to /calendar/events without category", async () => {
    mock.postWithTimeout.mockResolvedValue(eventReply);
    mock.post.mockResolvedValue({});
    renderChat();
    await sendMessage();
    fireEvent.click(await screen.findByRole("button", { name: "Create" }));
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    const [path, body] = mock.post.mock.calls[0];
    expect(path).toBe("/calendar/events");
    expect(body).toMatchObject({ title: "Meeting", is_all_day: false, calendar_type: "personal" });
    expect(body).not.toHaveProperty("category");
  });
});
