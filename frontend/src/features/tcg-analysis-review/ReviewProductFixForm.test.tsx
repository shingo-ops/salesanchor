import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ApiError } from "../../lib/api";
import { ReviewProductFixForm } from "./ReviewProductFixForm";
import { postProductCorrection } from "./reviewActions";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("./reviewActions", () => ({
  postProductCorrection: vi.fn(),
  searchProductOptions: vi.fn(async () => [{ value: "new-uuid", label: "New Product" }]),
}));

const item = {
  extraction_item_id: "item-1",
  source_message_id: "msg-1",
  system: { product_uuid: "old-uuid", product_title: "Old Product" },
};

async function pickCandidate() {
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value: "New" } });
  fireEvent.click(await screen.findByRole("option", { name: "New Product" }, { timeout: 2000 }));
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("ReviewProductFixForm", () => {
  it("shows the labelled Product field, the current product, and a disabled reassign button until a candidate is chosen", () => {
    render(<ReviewProductFixForm item={item} onRefresh={async () => undefined} searchDebounceMs={0} />);

    expect(screen.getByText("Product").tagName).toBe("LABEL");
    expect(screen.getByText("Current: Old Product")).toBeTruthy();
    const button = screen.getByRole("button", { name: "Reassign to this product" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("shows a dash when there is no current product", () => {
    render(<ReviewProductFixForm item={{ ...item, system: {} }} onRefresh={async () => undefined} />);

    expect(screen.getByText("Current: —")).toBeTruthy();
  });

  it("posts the correction with the chosen product, then shows the info callout and reloads", async () => {
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<ReviewProductFixForm item={item} onRefresh={onRefresh} searchDebounceMs={0} />);

    await pickCandidate();
    const button = screen.getByRole("button", { name: "Reassign to this product" }) as HTMLButtonElement;
    expect(button.disabled).toBe(false);
    fireEvent.click(button);

    await waitFor(() => expect(onRefresh).toHaveBeenCalledOnce());
    expect(postProductCorrection).toHaveBeenCalledWith(item, "new-uuid");
    expect(screen.getByRole("status").textContent).toContain("Reassigned");
  });

  it("shows a warning callout and does not reload when saving fails", async () => {
    vi.mocked(postProductCorrection).mockRejectedValue(new Error("boom"));
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<ReviewProductFixForm item={item} onRefresh={onRefresh} searchDebounceMs={0} />);

    await pickCandidate();
    fireEvent.click(screen.getByRole("button", { name: "Reassign to this product" }));

    expect((await screen.findByRole("alert")).textContent).toContain("Failed to reassign");
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("uses the API error message when the error is an ApiError", async () => {
    vi.mocked(postProductCorrection).mockRejectedValue(new ApiError("Conflict happened", 409, null));
    render(<ReviewProductFixForm item={item} onRefresh={async () => undefined} searchDebounceMs={0} />);

    await pickCandidate();
    fireEvent.click(screen.getByRole("button", { name: "Reassign to this product" }));

    expect((await screen.findByRole("alert")).textContent).toContain("Conflict happened");
  });

  it("keeps the success callout and shows no failure when only the reload fails after saving", async () => {
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    const onRefresh = vi.fn().mockRejectedValue(new Error("reload failed"));
    render(<ReviewProductFixForm item={item} onRefresh={onRefresh} searchDebounceMs={0} />);

    await pickCandidate();
    fireEvent.click(screen.getByRole("button", { name: "Reassign to this product" }));

    await waitFor(() => expect(onRefresh).toHaveBeenCalledOnce());
    expect(screen.getByRole("status").textContent).toContain("Reassigned");
    expect(screen.queryByText("Failed to reassign")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
