import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { api, ApiError } from "../../lib/api";
import type { AnalysisReviewItem } from "./ItemComparison";
import { ReviewValueFixForm, type ValueRowKey } from "./ReviewValueFixForm";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error { status: number; constructor(message: string, status: number) { super(message); this.status = status; } },
}));

const item: AnalysisReviewItem = {
  extraction_item_id: "item-1", source_message_id: "msg-1", provider: "P", raw_text: "", gemini: {},
  system: { quantity: "3", price: "1200", unit: "BOX", note: "old memo", status: "In Stock" },
};
const options = { units: ["BOX", "CASE"], statuses: ["In Stock", "Sold out"] };

const renderForm = (rowKey: ValueRowKey, onRefresh = vi.fn().mockResolvedValue(undefined)) => {
  render(<ReviewValueFixForm item={item} rowKey={rowKey} onRefresh={onRefresh} />);
  return { onRefresh };
};

beforeEach(async () => {
  vi.resetAllMocks();
  vi.mocked(api.get).mockResolvedValue(options);
  vi.mocked(api.post).mockResolvedValue({ ok: true, saved: 1 });
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("ReviewValueFixForm (K3)", () => {
  it("quantity is a number input starting at the system value; save posts {source_message_id, field, value} once, then refreshes", async () => {
    const { onRefresh } = renderForm("quantity");
    const input = screen.getByLabelText("Quantity") as HTMLInputElement;
    expect(input.type).toBe("number");
    expect(input.value).toBe("3");

    fireEvent.change(input, { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: "Save this value" }));

    await waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1));
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/value-override", { source_message_id: "msg-1", field: "quantity", value: "7" });
    expect(api.get).not.toHaveBeenCalled();
  });

  it("price posts field=price", async () => {
    renderForm("price");
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "1500" } });
    fireEvent.click(screen.getByRole("button", { name: "Save this value" }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/value-override", { source_message_id: "msg-1", field: "price", value: "1500" }));
  });

  it("unit is a select filled from value-options", async () => {
    renderForm("unit");
    await screen.findByRole("option", { name: "CASE" });
    expect(api.get).toHaveBeenCalledWith("/tcg/review/value-options");

    fireEvent.change(screen.getByLabelText("Unit"), { target: { value: "CASE" } });
    fireEvent.click(screen.getByRole("button", { name: "Save this value" }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/value-override", { source_message_id: "msg-1", field: "unit", value: "CASE" }));
  });

  it("sale status is a select posting field=status", async () => {
    renderForm("saleStatus");
    await screen.findByRole("option", { name: "Sold out" });

    fireEvent.change(screen.getByLabelText("Sale status"), { target: { value: "Sold out" } });
    fireEvent.click(screen.getByRole("button", { name: "Save this value" }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/value-override", { source_message_id: "msg-1", field: "status", value: "Sold out" }));
  });

  it("memo is a textarea with a 2000 character limit, and may be saved empty", async () => {
    renderForm("memo");
    const area = screen.getByLabelText("Memo") as HTMLTextAreaElement;
    expect(area.tagName).toBe("TEXTAREA");
    expect(area.maxLength).toBe(2000);
    expect(area.value).toBe("old memo");

    fireEvent.change(area, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Save this value" }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/value-override", { source_message_id: "msg-1", field: "note", value: "" }));
  });

  it("does not save an empty quantity", () => {
    renderForm("quantity");
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "" } });

    expect((screen.getByRole("button", { name: "Save this value" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("422 and 409 show their own messages and do not refresh; other errors show the generic one", async () => {
    const { onRefresh } = renderForm("quantity");
    const save = () => fireEvent.click(screen.getByRole("button", { name: "Save this value" }));

    vi.mocked(api.post).mockRejectedValueOnce(new ApiError("x", 422, null));
    save();
    expect(await screen.findByText("This value cannot be used. Please check it")).toBeTruthy();

    vi.mocked(api.post).mockRejectedValueOnce(new ApiError("x", 409, null));
    save();
    expect(await screen.findByText("This item cannot be fixed. Please reopen the screen")).toBeTruthy();

    vi.mocked(api.post).mockRejectedValueOnce(new ApiError("x", 500, null));
    save();
    expect(await screen.findByText("Could not save. Please try again")).toBeTruthy();
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("shows the load failure when the options cannot be read", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("boom"));
    renderForm("unit");

    expect(await screen.findByText("Could not load the choices")).toBeTruthy();
  });
});
