import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import i18n from "../../i18n";
import { ReviewRowActions, type ReviewRowItem } from "./ReviewRowActions";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));

const makeItem = (overrides: Partial<ReviewRowItem> = {}): ReviewRowItem => ({
  extraction_item_id: "item-1",
  source_message_id: "msg-1",
  system: { product_uuid: "old-uuid", product_title: "Old Product" },
  is_v102: true,
  review_reason_details: [
    { code: "product_not_in_master", source: "system", fix_stage: "analysis" },
    { code: "condition_unknown", source: "system", fix_stage: "analysis", ackable: false },
    { code: "pid_unresolved", source: "system", fix_stage: "analysis", ackable: true },
  ],
  ...overrides,
});

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockResolvedValue({
    candidates: [{ product_id: "PM-00002", product_uuid: "new-uuid", japanese_title: "New Product", search_keywords: "" }],
  });
  vi.mocked(api.post).mockResolvedValue({ ok: true, saved: 1 });
});
afterEach(() => cleanup());

describe("ReviewRowActions", () => {
  it("shows nothing for a v6 item", () => {
    const { container } = render(<ReviewRowActions item={makeItem({ is_v102: false })} onSaved={() => undefined} />);
    expect(container.innerHTML).toBe("");
  });

  it("posts the same product correction as the drawer when a candidate is chosen, then shows Saved and reloads", async () => {
    const onSaved = vi.fn();
    render(<ReviewRowActions item={makeItem()} onSaved={onSaved} />);
    const input = screen.getByRole("combobox");
    expect((input as HTMLInputElement).value).toBe("Old Product");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "New" } });
    fireEvent.click(await screen.findByRole("option", { name: "New Product" }, { timeout: 2000 }));
    await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
    expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/corrections", {
      source_message_id: "msg-1",
      fields: [{ field_name: "product_id", system_value: "old-uuid", human_value: "new-uuid" }],
    });
    expect(await screen.findByText("Saved")).toBeTruthy();
    expect((screen.getByRole("combobox") as HTMLInputElement).value).toBe("New Product");
    expect(onSaved).toHaveBeenCalledOnce();
  });

  it("does not save while only typing", async () => {
    render(<ReviewRowActions item={makeItem()} onSaved={() => undefined} />);
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "New" } });
    await screen.findByRole("option", { name: "New Product" }, { timeout: 2000 });
    expect(api.post).not.toHaveBeenCalled();
  });

  it("sends only the ackable reasons together with keep-as-is", async () => {
    const onSaved = vi.fn();
    render(<ReviewRowActions item={makeItem()} onSaved={onSaved} />);
    fireEvent.click(screen.getByRole("button", { name: "Keep as is: item-1" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
    expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/review-ack", {
      source_message_id: "msg-1",
      codes: ["product_not_in_master", "pid_unresolved"],
    });
    expect(await screen.findByText("Saved")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Keep as is: item-1" })).toBeNull();
    expect(onSaved).toHaveBeenCalledOnce();
  });

  it("has no keep-as-is button when no reason can be acknowledged", () => {
    const item = makeItem({ review_reason_details: [{ code: "condition_unknown", source: "system", fix_stage: "analysis", ackable: false }] });
    render(<ReviewRowActions item={item} onSaved={() => undefined} />);
    expect(screen.queryByRole("button", { name: "Keep as is: item-1" })).toBeNull();
    expect(screen.getByRole("combobox")).toBeTruthy();
  });

  it("shows an error badge with the reason and does not reload when saving fails", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("nope"));
    const onSaved = vi.fn();
    render(<ReviewRowActions item={makeItem()} onSaved={onSaved} />);
    fireEvent.click(screen.getByRole("button", { name: "Keep as is: item-1" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.queryByText(/Could not save/)).toBeTruthy());
    expect(onSaved).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Keep as is: item-1" })).toBeTruthy();
  });

  it("does not let clicks reach a parent row", () => {
    const onRowClick = vi.fn();
    render(
      <div onClick={onRowClick}>
        <ReviewRowActions item={makeItem()} onSaved={() => undefined} />
      </div>,
    );
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("button", { name: "Keep as is: item-1" }));
    expect(onRowClick).not.toHaveBeenCalled();
  });
});
