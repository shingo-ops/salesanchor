import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { SecretaryChat } from "./SecretaryChat";

const mock = vi.hoisted(() => ({
  postWithTimeout: vi.fn(),
  post: vi.fn(),
  get: vi.fn(),
  speech: vi.fn(),
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
vi.mock("./secretaryApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./secretaryApi")>()),
  fetchSecretarySpeech: mock.speech,
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
import { queryClient } from "../../lib/query/apiQuery";
import { apiErrorReasonMessage } from "../../lib/apiErrorReason";

const FAB = "Ask the assistant";

const allowAll = () => {
  mock.features = new Set(["secretary_chat"]);
  mock.superAdmin = true;
  mock.permissions = new Set(["customers.view", "invoices.create"]);
};

const none = { companies: [], contacts: [] };
// invoice-create-portfolio 便D: 会社 1・担当者 2 の請求書の材料（通貨と支払方法の候補の正本）
const DRAFT_CTX_PATH = "/invoices/draft-context?company_id=1&contact_id=2";
const DRAFT_CTX = {
  company_id: 1, ship_to: null, bill_to: null, contact_name: "Taro", contact_email: null,
  issuer_region: "JP", origin_country_code: "JP", destination_country_code: "US", destination_postal_code: null,
  currencies: ["JPY", "USD"], fx_rates: [], default_currency: "JPY", currency: null,
  payment_methods: [{ id: 3, method_type: "bank", display_name: "Main bank", wise_currency: null }],
  tax_rate_percent: null, incoterms: "DAP",
};
let draftCtx: Record<string, unknown> = DRAFT_CTX;
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
    is_meeting: false,
    add_meet: null,
    meet_available: false,
    ask: null,
    ask_count: 0,
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
  draftCtx = DRAFT_CTX;
  mock.get.mockImplementation(async (url: string) => (url === DRAFT_CTX_PATH ? draftCtx : []));
  await i18n.changeLanguage("en");
});
afterEach(() => {
  cleanup();
  queryClient.clear();
});

/** 便D: 支払方法を選び「送料を請求しない」にチェックする（チャットで作れる条件） */
async function decideInvoice() {
  const payment = (await screen.findByTestId("secretary-invoice-payment")) as HTMLSelectElement;
  await waitFor(() => expect(Array.from(payment.options).map((o) => o.value)).toEqual(["", "bank:3"]));
  fireEvent.change(payment, { target: { value: "bank:3" } });
  fireEvent.click(screen.getByTestId("secretary-invoice-shipping-none"));
}

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
    expect(mock.postWithTimeout).toHaveBeenCalledWith("/assistant/messages", { text: "make something", karte: null }, 100000);
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

  it("shows the authFailed text on 503 auth_failed, not the rephrase text", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 503, { code: "auth_failed" }));
    renderChat();
    await sendMessage();
    expect(await screen.findByText("The assistant's key no longer works. Please tell your administrator.")).toBeTruthy();
    expect(screen.queryByText(/rephrase/)).toBeNull();
  });

  it("shows the agentFailed text in full on 502 agent_failed, not the generic text", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 502, { code: "agent_failed" }));
    renderChat();
    await sendMessage();
    expect(
      await screen.findByText("Something went wrong. Please wait a moment and send it again."),
    ).toBeTruthy();
    expect(screen.queryByText(/Please try again/)).toBeNull();
  });

  it("shows the rulesTooLong text on 413 rules_too_long", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 413, { code: "rules_too_long" }));
    renderChat();
    await sendMessage();
    expect(
      await screen.findByText("Your message and the company rules are too long together. Shorten the message or remove some rules."),
    ).toBeTruthy();
  });

  it("shows the unreadable text on 502 unreadable", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 502, { code: "unreadable" }));
    renderChat();
    await sendMessage();
    expect(await screen.findByText("I could not understand that. Please rephrase")).toBeTruthy();
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
    expect(create.disabled).toBe(true);
    await decideInvoice();
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
      shipping: { mode: "none" },
      payment_method_ref: { method_type: "bank", id: 3 },
    });
    expect(await screen.findByText(/Invoice created/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open invoice" }).getAttribute("href")).toBe("/invoices/77");
  });

  it("blocks Create and shows the decimals text when the unit price has 3 decimal places", async () => {
    mock.postWithTimeout.mockResolvedValue(invoiceReply());
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "1000.255" } });
    expect(screen.getByText("Unit price can have up to 2 decimal places.")).toBeTruthy();
    expect(create.disabled).toBe(true);
  });

  it.each([1000.5, 1000.25])("sends the unit price %s as is", async (price) => {
    mock.postWithTimeout.mockResolvedValue(invoiceReply());
    mock.post.mockResolvedValue({ id: 78 });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: String(price) } });
    expect(screen.queryByText("Unit price can have up to 2 decimal places.")).toBeNull();
    await decideInvoice();
    expect(create.disabled).toBe(false);
    fireEvent.click(create);
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(mock.post).toHaveBeenCalledWith(
      "/invoices",
      expect.objectContaining({ items: [{ product_name: "Widget", quantity: 2, unit_price: price }] }),
    );
  });

  it("keeps a drafted unit price of 1000.255 as is, shows the decimals text and blocks Create", async () => {
    mock.postWithTimeout.mockResolvedValue(
      invoiceReply({ items: [{ product_name: "Widget", quantity: 2, unit_price: 1000.255 }] }),
    );
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect((screen.getByLabelText("Unit price") as HTMLInputElement).value).toBe("1000.255");
    expect(screen.getByText("Unit price can have up to 2 decimal places.")).toBeTruthy();
    expect(create.disabled).toBe(true);
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
    await decideInvoice();
    expect(create.disabled).toBe(false);
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: qty } });
    expect(create.disabled).toBe(true);
  });
});

describe("SecretaryChat invoice draft (invoice-create-portfolio bin D)", () => {
  const ready = () => invoiceReply({ items: [{ product_name: "Widget", quantity: 1, unit_price: 100 }] });

  it("K2: currency and payment choices come from draft-context, not a fixed list", async () => {
    mock.postWithTimeout.mockResolvedValue(ready());
    renderChat();
    await sendMessage();
    const currency = (await screen.findByTestId("secretary-invoice-currency")) as HTMLSelectElement;
    await waitFor(() => expect(Array.from(currency.options).map((o) => o.value)).toEqual(["", "JPY", "USD"]));
    expect(currency.value).toBe("JPY");
    expect(mock.get).toHaveBeenCalledWith(DRAFT_CTX_PATH);
  });

  it("K19: Create stays disabled until \"Do not charge shipping\" is ticked, and the body has no tax or shipping fee", async () => {
    mock.postWithTimeout.mockResolvedValue(ready());
    mock.post.mockResolvedValue({ id: 80 });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    const payment = (await screen.findByTestId("secretary-invoice-payment")) as HTMLSelectElement;
    await waitFor(() => expect(payment.options.length).toBe(2));
    fireEvent.change(payment, { target: { value: "bank:3" } });
    expect(create.disabled).toBe(true);
    fireEvent.click(screen.getByTestId("secretary-invoice-shipping-none"));
    expect(create.disabled).toBe(false);
    fireEvent.click(create);
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    const body = mock.post.mock.calls[0][1] as Record<string, unknown>;
    expect(body.shipping).toEqual({ mode: "none" });
    expect("tax_amount" in body).toBe(false);
    expect("shipping_fee" in body).toBe(false);
  });

  it("K19: a 409 duty_needs_carrier shows the Japanese wording, not the code, and creates nothing", async () => {
    await i18n.changeLanguage("ja");
    const wording = apiErrorReasonMessage("duty_needs_carrier");
    expect(wording).toBeTruthy();
    expect(wording).not.toBe("duty_needs_carrier");
    mock.postWithTimeout.mockResolvedValue(ready());
    mock.post.mockRejectedValue(new ApiError(wording as string, 409, "duty_needs_carrier"));
    renderChat();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("secretary.open") }));
    const box = await screen.findByLabelText(i18n.t("secretary.placeholder"));
    fireEvent.change(box, { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("secretary.send") }));
    await decideInvoice();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("secretary.create") }));
    expect(await screen.findByText(wording as string)).toBeTruthy();
    expect(screen.queryByText("duty_needs_carrier")).toBeNull();
    expect(screen.queryByRole("link", { name: i18n.t("secretary.link.invoice") })).toBeNull();
  });

  it("no payment destinations: Create is allowed without one and the hint is shown", async () => {
    draftCtx = { ...DRAFT_CTX, payment_methods: [] };
    mock.postWithTimeout.mockResolvedValue(ready());
    mock.post.mockResolvedValue({ id: 81 });
    renderChat();
    await sendMessage();
    expect(await screen.findByTestId("secretary-invoice-no-payment")).toBeTruthy();
    fireEvent.click(screen.getByTestId("secretary-invoice-shipping-none"));
    const create = screen.getByRole("button", { name: "Create" }) as HTMLButtonElement;
    expect(create.disabled).toBe(false);
    fireEvent.click(create);
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect((mock.post.mock.calls[0][1] as Record<string, unknown>).payment_method_ref).toBeNull();
  });

  it("issuer region missing: the bill-to hint is shown and Create stays disabled", async () => {
    draftCtx = { ...DRAFT_CTX, issuer_region: null };
    mock.postWithTimeout.mockResolvedValue(ready());
    renderChat();
    await sendMessage();
    expect(await screen.findByTestId("secretary-invoice-bill-to")).toBeTruthy();
    fireEvent.click(screen.getByTestId("secretary-invoice-shipping-none"));
    expect((screen.getByRole("button", { name: "Create" }) as HTMLButtonElement).disabled).toBe(true);
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

  it("asks one missing field, then sends the karte back on the next message", async () => {
    const askReply = {
      ...eventReply,
      draft: { ...eventReply.draft, end: null, is_meeting: true, ask: "end", ask_count: 1 },
    };
    mock.postWithTimeout.mockResolvedValueOnce(askReply).mockResolvedValueOnce(eventReply);
    renderChat();
    await sendMessage("meeting tomorrow at 10");
    expect(await screen.findByText(i18n.t("secretary.ask.end"))).toBeTruthy();
    expect(screen.getByText("Meeting")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Create" })).toBeNull();

    const box = screen.getByLabelText(/Tell me what you need/);
    fireEvent.change(box, { target: { value: "until 11" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByRole("button", { name: "Create" });
    const [, body] = mock.postWithTimeout.mock.calls[1];
    expect(body.karte).toMatchObject({ title: "Meeting", end: null, is_meeting: true, asked: "end", asked_count: 1 });
  });

  it("cannot create while a time is empty", async () => {
    mock.postWithTimeout.mockResolvedValue({ ...eventReply, draft: { ...eventReply.draft, end: null } });
    renderChat();
    await sendMessage();
    const create = (await screen.findByRole("button", { name: "Create" })) as HTMLButtonElement;
    expect(create.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2026-11-02" } });
    expect(create.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("End time"), { target: { value: "11:00" } });
    expect(create.disabled).toBe(false);
  });

  it("shows the Meet checkbox only when Meet is available and sends add_meet when checked", async () => {
    mock.postWithTimeout.mockResolvedValue({ ...eventReply, draft: { ...eventReply.draft, meet_available: true, add_meet: true } });
    mock.post.mockResolvedValue({});
    renderChat();
    await sendMessage();
    const meet = (await screen.findByLabelText(i18n.t("schedule.addMeet"))) as HTMLInputElement;
    expect(meet.checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(mock.post.mock.calls[0][1]).toMatchObject({ add_meet: true });
  });

  it("hides the Meet checkbox and never sends add_meet when Meet is not available", async () => {
    mock.postWithTimeout.mockResolvedValue(eventReply);
    mock.post.mockResolvedValue({});
    renderChat();
    await sendMessage();
    fireEvent.click(await screen.findByRole("button", { name: "Create" }));
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(screen.queryByLabelText(i18n.t("schedule.addMeet"))).toBeNull();
    expect(mock.post.mock.calls[0][1]).not.toHaveProperty("add_meet");
  });
});

// 便2: 声で返事（V3）。AudioContext は偽物。読み上げの頼み（fetchSecretarySpeech）の回数を数える
describe("SecretaryChat voice reply", () => {
  const TOGGLE = "Voice conversation";
  let decoded: { connect: ReturnType<typeof vi.fn>; start: ReturnType<typeof vi.fn> } | null = null;

  beforeEach(() => {
    decoded = null;
    mock.speech.mockResolvedValue(new Blob(["x"]));
    class FakeAudioContext {
      destination = {};
      resume = vi.fn().mockResolvedValue(undefined);
      close = vi.fn().mockResolvedValue(undefined);
      decodeAudioData = vi.fn().mockResolvedValue({});
      createBufferSource() {
        const source = {
          buffer: null as unknown,
          onended: null as null | (() => void),
          connect: vi.fn(),
          stop: vi.fn(),
          start: vi.fn(() => {
            queueMicrotask(() => source.onended?.());
          }),
        };
        decoded = source;
        return source;
      }
    }
    Object.defineProperty(window, "AudioContext", { value: FakeAudioContext, configurable: true, writable: true });
  });

  async function openChat() {
    fireEvent.click(screen.getByRole("button", { name: FAB }));
    return (await screen.findByRole("switch", { name: TOGGLE })) as HTMLInputElement;
  }

  it("V3-a: the toggle is off right after opening", async () => {
    renderChat();
    const toggle = await openChat();
    expect(toggle.checked).toBe(false);
  });

  it("V3-b: never asks for speech while the toggle is off", async () => {
    mock.postWithTimeout.mockResolvedValue({ kind: "unknown", draft: { reply: "ok. next." }, candidates: none });
    renderChat();
    await sendMessage();
    await screen.findByText("ok. next.");
    expect(mock.speech).not.toHaveBeenCalled();
  });

  it("V3-c: asks for speech with the first sentence once the toggle is on", async () => {
    const reply = "Hello! Tomorrow?";
    mock.postWithTimeout.mockResolvedValue({ kind: "unknown", draft: { reply }, candidates: none });
    renderChat();
    const toggle = await openChat();
    fireEvent.click(toggle);
    const box = await screen.findByLabelText(/Tell me what you need/);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(reply);
    await waitFor(() => expect(mock.speech).toHaveBeenCalled());
    expect(mock.speech.mock.calls[0][0]).toBe("Hello!");
    await waitFor(() => expect(decoded?.start).toHaveBeenCalled());
  });

  it("V3-d: shows the failure line and keeps the text reply when speech fails", async () => {
    mock.speech.mockRejectedValue(new ApiError("x", 503, { code: "tts_not_configured" }));
    mock.postWithTimeout.mockResolvedValue({ kind: "unknown", draft: { reply: "plain reply" }, candidates: none });
    renderChat();
    const toggle = await openChat();
    fireEvent.click(toggle);
    const box = await screen.findByLabelText(/Tell me what you need/);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("plain reply")).toBeTruthy();
    expect(await screen.findByText(i18n.t("secretary.voiceFailed"))).toBeTruthy();
  });

  it("V3-e: the toggle goes back to off after closing and reopening", async () => {
    renderChat();
    const toggle = await openChat();
    fireEvent.click(toggle);
    expect(toggle.checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    const reopened = await openChat();
    await waitFor(() => expect(reopened.checked).toBe(false));
  });

  it("V3-f: turning the toggle off while waiting neither asks for speech nor shows the failure line", async () => {
    let resolveReply!: (v: unknown) => void;
    mock.postWithTimeout.mockReturnValue(
      new Promise((r) => {
        resolveReply = r;
      }),
    );
    renderChat();
    const toggle = await openChat();
    fireEvent.click(toggle);
    const box = await screen.findByLabelText(/Tell me what you need/);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(mock.postWithTimeout).toHaveBeenCalled());
    fireEvent.click(toggle);
    resolveReply({ kind: "unknown", draft: { reply: "late reply" }, candidates: none });
    await screen.findByText("late reply");
    expect(mock.speech).not.toHaveBeenCalled();
    expect(screen.queryByText(i18n.t("secretary.voiceFailed"))).toBeNull();
  });

  it("V3-g: a reply sent before closing is not read aloud after reopening with the toggle on", async () => {
    let resolveReply!: (v: unknown) => void;
    mock.postWithTimeout.mockReturnValue(
      new Promise((r) => {
        resolveReply = r;
      }),
    );
    renderChat();
    const toggle = await openChat();
    fireEvent.click(toggle);
    const box = await screen.findByLabelText(/Tell me what you need/);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(mock.postWithTimeout).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    const reopened = await openChat();
    fireEvent.click(reopened);
    resolveReply({ kind: "unknown", draft: { reply: "old reply" }, candidates: none });
    await Promise.resolve();
    await Promise.resolve();
    expect(mock.speech).not.toHaveBeenCalled();
  });
});

// 便T: 声の聞き取りの印。SpeechRecognition は偽物に差し替え、試験の後で元に戻す
describe("SecretaryChat listen mark", () => {
  const LISTEN = "Speak to type";
  const JP_TEXT = String.fromCharCode(0x3053, 0x3093, 0x306b, 0x3061, 0x306f);
  type Win = { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown };
  const win = window as unknown as Win;
  let saved: unknown;
  let savedWebkit: unknown;
  let instances: FakeRec[] = [];

  class FakeRec {
    lang = "";
    interimResults = false;
    continuous = false;
    maxAlternatives = 1;
    onresult: ((ev: unknown) => void) | null = null;
    onerror: ((ev: unknown) => void) | null = null;
    onend: (() => void) | null = null;
    start = vi.fn();
    stop = vi.fn();
    abort = vi.fn();
    constructor() {
      instances.push(this);
    }
  }

  const renderMobile = () =>
    render(
      <MemoryRouter>
        <SecretaryChat isMobile={true} />
      </MemoryRouter>,
    );

  beforeEach(() => {
    saved = win.SpeechRecognition;
    savedWebkit = win.webkitSpeechRecognition;
    instances = [];
    win.SpeechRecognition = FakeRec;
    delete win.webkitSpeechRecognition;
  });
  afterEach(() => {
    if (saved === undefined) delete win.SpeechRecognition;
    else win.SpeechRecognition = saved;
    if (savedWebkit === undefined) delete win.webkitSpeechRecognition;
    else win.webkitSpeechRecognition = savedWebkit;
  });

  const openMobile = async () => {
    renderMobile();
    fireEvent.click(screen.getByRole("button", { name: FAB }));
    await screen.findByLabelText(/Tell me what you need/);
  };

  it("has a listen mark when isMobile is false", async () => {
    renderChat();
    fireEvent.click(screen.getByRole("button", { name: FAB }));
    await screen.findByLabelText(/Tell me what you need/);
    expect(screen.getByRole("button", { name: LISTEN })).toBeTruthy();
  });

  it("has a listen mark when isMobile is true", async () => {
    await openMobile();
    expect(screen.getByRole("button", { name: LISTEN })).toBeTruthy();
  });

  it("shows the listening text after pressing the mark", async () => {
    await openMobile();
    fireEvent.click(screen.getByRole("button", { name: LISTEN }));
    expect(await screen.findByText(i18n.t("secretary.listen.listening"))).toBeTruthy();
    expect(instances[0].start).toHaveBeenCalledTimes(1);
  });

  it("puts a final sentence into the box and does not send it", async () => {
    await openMobile();
    fireEvent.click(screen.getByRole("button", { name: LISTEN }));
    const result = Object.assign([{ transcript: JP_TEXT }], { isFinal: true });
    act(() => {
      instances[0].onresult?.({ resultIndex: 0, results: [result] });
    });
    const box = screen.getByLabelText(/Tell me what you need/) as HTMLTextAreaElement;
    await waitFor(() => expect(box.value).toBe(JP_TEXT));
    expect(mock.postWithTimeout).not.toHaveBeenCalled();
  });

  const finalResult = (transcript: string) => Object.assign([{ transcript }], { isFinal: true });
  const interimResult = (transcript: string) => Object.assign([{ transcript }], { isFinal: false });

  it("shows interim text in the box, makes it read-only and blocks sending while listening", async () => {
    await openMobile();
    fireEvent.click(screen.getByRole("button", { name: LISTEN }));
    act(() => {
      instances[0].onresult?.({ resultIndex: 0, results: [interimResult(JP_TEXT)] });
    });
    const box = screen.getByLabelText(/Tell me what you need/) as HTMLTextAreaElement;
    await waitFor(() => expect(box.value).toBe(JP_TEXT));
    expect(box.readOnly).toBe(true);
    const sendBtn = screen.getByRole("button", { name: i18n.t("secretary.send") }) as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(true);
  });

  it("stops at the max length, shows the too-long text and stops listening", async () => {
    await openMobile();
    fireEvent.click(screen.getByRole("button", { name: LISTEN }));
    act(() => {
      instances[0].onresult?.({ resultIndex: 0, results: [finalResult("a".repeat(1001))] });
    });
    const box = screen.getByLabelText(/Tell me what you need/) as HTMLTextAreaElement;
    await waitFor(() => expect(box.value.length).toBe(1000));
    expect(instances[0].stop).toHaveBeenCalled();
    // 実機では stop の後に onend が来る（偽物は来ないので試験で出す）
    act(() => {
      instances[0].onend?.();
    });
    expect(await screen.findByText(i18n.t("secretary.listen.tooLong", { max: 1000 }))).toBeTruthy();
  });

  it("clears the too-long text when the box is edited by hand", async () => {
    await openMobile();
    fireEvent.click(screen.getByRole("button", { name: LISTEN }));
    act(() => {
      instances[0].onresult?.({ resultIndex: 0, results: [finalResult("a".repeat(1000))] });
    });
    const tooLongText = i18n.t("secretary.listen.tooLong", { max: 1000 });
    act(() => {
      instances[0].onend?.();
    });
    expect(await screen.findByText(tooLongText)).toBeTruthy();
    const box = screen.getByLabelText(/Tell me what you need/) as HTMLTextAreaElement;
    await waitFor(() => expect(box.readOnly).toBe(false));
    fireEvent.change(box, { target: { value: "abc" } });
    await waitFor(() => expect(screen.queryByText(tooLongText)).toBeNull());
  });

  it("says it is unavailable when there is no recognition class", async () => {
    delete win.SpeechRecognition;
    await openMobile();
    fireEvent.click(screen.getByRole("button", { name: LISTEN }));
    expect(await screen.findByText(i18n.t("secretary.listen.error.unsupported"))).toBeTruthy();
  });

  it("aborts the recognition when the window is closed", async () => {
    await openMobile();
    fireEvent.click(screen.getByRole("button", { name: LISTEN }));
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(instances[0].abort).toHaveBeenCalled();
  });
});

// 便V: 声で会話（交代で話す型）。偽の AudioContext と偽の聞き取りを両方入れる
describe("SecretaryChat voice conversation", () => {
  const TOGGLE = "Voice conversation";
  const LISTEN = "Speak to type";
  type Win = { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown };
  const win = window as unknown as Win;
  let saved: unknown;
  let savedWebkit: unknown;
  let instances: ConvRec[] = [];

  class ConvRec {
    lang = "";
    interimResults = false;
    continuous = false;
    maxAlternatives = 1;
    onresult: ((ev: unknown) => void) | null = null;
    onerror: ((ev: unknown) => void) | null = null;
    onend: (() => void) | null = null;
    start = vi.fn();
    stop = vi.fn();
    abort = vi.fn();
    constructor() {
      instances.push(this);
    }
  }

  const startCount = () => instances.reduce((n, r) => n + r.start.mock.calls.length, 0);
  const live = () => instances[instances.length - 1];
  const finalOf = (transcript: string) => Object.assign([{ transcript }], { isFinal: true });
  const interimOf = (transcript: string) => Object.assign([{ transcript }], { isFinal: false });
  const hear = (text: string, rec: ConvRec = live()) => {
    act(() => {
      rec.onresult?.({ resultIndex: 0, results: [finalOf(text)] });
    });
  };
  const spoken = () => mock.speech.mock.calls.map((c) => String(c[0])).join(" ");
  const unknownReply = (reply: string) => ({ kind: "unknown", draft: { reply }, candidates: none });
  const flush = () =>
    act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });
  /** 次の読み上げの最初の片を止めておく。返した関数で放す */
  const holdNextSpeech = () => {
    let release: () => void = () => {};
    mock.speech.mockImplementationOnce(
      () =>
        new Promise<Blob>((resolve) => {
          release = () => resolve(new Blob(["x"]));
        }),
    );
    return () => release();
  };

  beforeEach(() => {
    saved = win.SpeechRecognition;
    savedWebkit = win.webkitSpeechRecognition;
    instances = [];
    win.SpeechRecognition = ConvRec;
    delete win.webkitSpeechRecognition;
    mock.speech.mockReset();
    mock.speech.mockResolvedValue(new Blob(["x"]));
    mock.postWithTimeout.mockReset();
    mock.post.mockReset();
    class FakeAudioContext {
      destination = {};
      resume = vi.fn().mockResolvedValue(undefined);
      close = vi.fn().mockResolvedValue(undefined);
      decodeAudioData = vi.fn().mockResolvedValue({});
      createBufferSource() {
        const source = {
          buffer: null as unknown,
          onended: null as null | (() => void),
          connect: vi.fn(),
          stop: vi.fn(),
          start: vi.fn(() => {
            queueMicrotask(() => source.onended?.());
          }),
        };
        return source;
      }
    }
    Object.defineProperty(window, "AudioContext", { value: FakeAudioContext, configurable: true, writable: true });
  });
  afterEach(() => {
    vi.useRealTimers();
    if (saved === undefined) delete win.SpeechRecognition;
    else win.SpeechRecognition = saved;
    if (savedWebkit === undefined) delete win.webkitSpeechRecognition;
    else win.webkitSpeechRecognition = savedWebkit;
  });

  const openChat = async () => {
    renderChat();
    fireEvent.click(screen.getByRole("button", { name: FAB }));
    return (await screen.findByRole("switch", { name: TOGGLE })) as HTMLInputElement;
  };
  const openVoice = async () => {
    const toggle = await openChat();
    fireEvent.click(toggle);
    return toggle;
  };
  /** 聞き取った文で送り、返事の読み上げの終わりでまた聞くところまで進める */
  const sayAndAnswered = async (text: string, sentCount: number, startsAfter: number) => {
    hear(text);
    await waitFor(() => expect(mock.postWithTimeout).toHaveBeenCalledTimes(sentCount), { timeout: 4000 });
    await waitFor(() => expect(startCount()).toBe(startsAfter), { timeout: 4000 });
  };
  const SLOW = 20000;

  it("T1: starts listening once when turned on", async () => {
    await openVoice();
    expect(instances.length).toBe(1);
    expect(startCount()).toBe(1);
  });

  it("T2: sends after 1000ms of silence, not at 999ms; not with interim text or hand-typed text", async () => {
    mock.postWithTimeout.mockResolvedValue(unknownReply("Okay."));
    await openVoice();
    vi.useFakeTimers();
    hear("hello");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(999);
    });
    expect(mock.postWithTimeout).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(mock.postWithTimeout).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it("T2: interim text blocks the automatic send", async () => {
    await openVoice();
    vi.useFakeTimers();
    hear("hello");
    act(() => {
      live().onresult?.({ resultIndex: 0, results: [interimOf("and more")] });
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(mock.postWithTimeout).not.toHaveBeenCalled();
  });

  it("T2: hand-typed text alone is not sent automatically", async () => {
    await openVoice();
    vi.useFakeTimers();
    const box = screen.getByLabelText(/Tell me what you need/);
    fireEvent.change(box, { target: { value: "typed" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(mock.postWithTimeout).not.toHaveBeenCalled();
  });

  it("T3: never sends automatically when the voice conversation is off", async () => {
    await openChat();
    fireEvent.click(await screen.findByRole("button", { name: LISTEN }));
    vi.useFakeTimers();
    hear("hello");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(mock.postWithTimeout).not.toHaveBeenCalled();
  });

  it("T4: listens again after the reply is read", async () => {
    mock.postWithTimeout.mockResolvedValue(unknownReply("Hello there."));
    await openVoice();
    await sayAndAnswered("hi", 1, 2);
    expect(spoken()).toContain("Hello there.");
  }, SLOW);

  it("T4: when reading fails, shows the note, does not listen again and turns the toggle off", async () => {
    mock.speech.mockRejectedValue(new ApiError("x", 503, { code: "tts_not_configured" }));
    mock.postWithTimeout.mockResolvedValue(unknownReply("plain reply"));
    const toggle = await openVoice();
    hear("hi");
    expect(await screen.findByText(i18n.t("secretary.voiceFailed"), undefined, { timeout: 4000 })).toBeTruthy();
    await waitFor(() => expect(toggle.checked).toBe(false));
    expect(startCount()).toBe(1);
  }, SLOW);

  it("T5: reads the confirmation, then a spoken yes creates the event once", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(eventReply);
    mock.post.mockResolvedValue({});
    await openVoice();
    await sayAndAnswered("meeting tomorrow", 1, 2);
    expect(spoken()).toContain("Add Meeting on");
    hear("yes");
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1), { timeout: 4000 });
    expect(mock.post.mock.calls[0][0]).toBe("/calendar/events");
    await waitFor(() => expect(startCount()).toBe(3), { timeout: 4000 });
    expect(spoken()).toContain(i18n.t("secretary.created.event"));
    expect(mock.postWithTimeout).toHaveBeenCalledTimes(1);
  }, SLOW);

  it("T6: a spoken no creates nothing and reads the not-created line", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(eventReply);
    await openVoice();
    await sayAndAnswered("meeting tomorrow", 1, 2);
    hear("no");
    await waitFor(() => expect(startCount()).toBe(3), { timeout: 4000 });
    expect(mock.post).not.toHaveBeenCalled();
    expect(spoken()).toContain(i18n.t("secretary.voiceMode.notCreated"));
    expect(mock.postWithTimeout).toHaveBeenCalledTimes(1);
  }, SLOW);

  it("T7: two unclear answers read askAgain then checkScreen and create nothing", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(eventReply);
    await openVoice();
    await sayAndAnswered("meeting tomorrow", 1, 2);
    hear("uh");
    await waitFor(() => expect(startCount()).toBe(3), { timeout: 4000 });
    expect(spoken()).toContain(i18n.t("secretary.voiceMode.askAgain"));
    hear("hmm");
    await waitFor(() => expect(startCount()).toBe(4), { timeout: 4000 });
    const all = spoken();
    expect(all.indexOf(i18n.t("secretary.voiceMode.askAgain"))).toBeLessThan(
      all.indexOf(i18n.t("secretary.voiceMode.checkScreen")),
    );
    expect(mock.post).not.toHaveBeenCalled();
    expect(mock.postWithTimeout).toHaveBeenCalledTimes(1);
  }, SLOW);

  it("T8: an invoice draft reads only the fixed line and a spoken yes does not create it", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(invoiceReply()).mockResolvedValue(unknownReply("Okay."));
    await openVoice();
    await sayAndAnswered("invoice for Acme", 1, 2);
    const all = spoken();
    expect(all).toContain(i18n.t("secretary.voiceMode.invoiceReady"));
    expect(all).not.toContain("Acme");
    expect(all).not.toContain("Widget");
    hear("yes");
    await waitFor(() => expect(mock.postWithTimeout).toHaveBeenCalledTimes(2), { timeout: 4000 });
    expect(mock.post).not.toHaveBeenCalled();
  }, SLOW);

  it("T9: closing the window drops the pending confirmation", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(eventReply).mockResolvedValue(unknownReply("Okay."));
    await openVoice();
    await sayAndAnswered("meeting tomorrow", 1, 2);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    fireEvent.click(screen.getByRole("button", { name: FAB }));
    fireEvent.click(await screen.findByRole("switch", { name: TOGGLE }));
    hear("yes");
    await waitFor(() => expect(mock.postWithTimeout).toHaveBeenCalledTimes(2), { timeout: 4000 });
    expect(mock.post).not.toHaveBeenCalled();
  }, SLOW);

  it("T10: sending by hand during a reading stops the old reading from opening the mic", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(unknownReply("Hello there.")).mockReturnValueOnce(new Promise(() => {}));
    await openVoice();
    const release = holdNextSpeech();
    hear("hi");
    await waitFor(() => expect(mock.speech).toHaveBeenCalledTimes(1), { timeout: 4000 });
    const box = screen.getByLabelText(/Tell me what you need/);
    fireEvent.change(box, { target: { value: "again" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(mock.postWithTimeout).toHaveBeenCalledTimes(2));
    release();
    await flush();
    expect(startCount()).toBe(1);
  }, SLOW);

  it("T11: pressing Create with the mic open aborts first and ignores speech heard while reading", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(eventReply);
    mock.post.mockResolvedValue({});
    await openVoice();
    await sayAndAnswered("meeting tomorrow", 1, 2);
    const open = live();
    const release = holdNextSpeech();
    fireEvent.click(await screen.findByRole("button", { name: "Create" }));
    await waitFor(() => expect(open.abort).toHaveBeenCalled());
    await waitFor(() => expect(mock.speech.mock.calls.length).toBeGreaterThanOrEqual(2));
    const lastSpeech = Math.max(...mock.speech.mock.invocationCallOrder);
    expect(open.abort.mock.invocationCallOrder[0]).toBeLessThan(lastSpeech);
    hear("yes", open);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 1300));
    });
    expect(mock.postWithTimeout).toHaveBeenCalledTimes(1);
    release();
    await flush();
  }, SLOW);

  it("T12: Create during the confirmation reading opens the mic only after the created line", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(eventReply);
    mock.post.mockResolvedValue({});
    await openVoice();
    const release = holdNextSpeech();
    hear("meeting tomorrow");
    await waitFor(() => expect(mock.speech).toHaveBeenCalledTimes(1), { timeout: 4000 });
    fireEvent.click(await screen.findByRole("button", { name: "Create" }));
    await waitFor(() => expect(startCount()).toBe(2), { timeout: 4000 });
    release();
    await flush();
    expect(startCount()).toBe(2);
    expect(mock.post).toHaveBeenCalledTimes(1);
    expect(mock.postWithTimeout).toHaveBeenCalledTimes(1);
  }, SLOW);

  it("T13: pressing the mic mark during a reading stops it and the old reading does not open the mic", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(unknownReply("Hello there."));
    await openVoice();
    const release = holdNextSpeech();
    hear("hi");
    await waitFor(() => expect(mock.speech).toHaveBeenCalledTimes(1), { timeout: 4000 });
    fireEvent.click(screen.getByRole("button", { name: LISTEN }));
    expect(startCount()).toBe(2);
    release();
    await flush();
    expect(startCount()).toBe(2);
  }, SLOW);

  it("T14: unmounting during a reading does not open the mic afterwards", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(unknownReply("Hello there."));
    const { unmount } = renderChat();
    fireEvent.click(screen.getByRole("button", { name: FAB }));
    fireEvent.click(await screen.findByRole("switch", { name: TOGGLE }));
    expect(startCount()).toBe(1);
    const release = holdNextSpeech();
    hear("hi");
    await waitFor(() => expect(mock.speech).toHaveBeenCalledTimes(1), { timeout: 4000 });
    unmount();
    release();
    await flush();
    expect(startCount()).toBe(1);
  }, SLOW);
});
