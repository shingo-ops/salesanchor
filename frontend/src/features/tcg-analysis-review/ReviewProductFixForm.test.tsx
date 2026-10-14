import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ApiError } from "../../lib/api";
import { ReviewProductFixForm } from "./ReviewProductFixForm";
import { addSearchKeyword, postProductCorrection } from "./reviewActions";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("./reviewActions", () => ({
  postProductCorrection: vi.fn(),
  addSearchKeyword: vi.fn(),
  searchProductOptions: vi.fn(async () => [{ value: "new-uuid", label: "New Product", productId: "42" }]),
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

describe("ReviewProductFixForm search keyword", () => {
  const renderWithKeyword = (onSaved = vi.fn()) =>
    render(
      <ReviewProductFixForm item={item} onRefresh={async () => undefined} searchDebounceMs={0} suggestKeyword="Pika Box" onSaved={onSaved} />,
    );
  const reassign = () => {
    fireEvent.click(screen.getByRole("button", { name: "Reassign to this product" }));
  };

  it("shows no keyword question without suggestKeyword", () => {
    render(<ReviewProductFixForm item={item} onRefresh={async () => undefined} />);

    expect(screen.queryByRole("group")).toBeNull();
  });

  it("asks about the keyword with the default Don't add, and does not add it", async () => {
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    renderWithKeyword();

    expect(screen.queryByRole("group", { name: "Add “Pika Box” as a search keyword?" })).toBeNull();
    await pickCandidate();
    expect(screen.getByRole("group", { name: "Add “Pika Box” as a search keyword?" })).toBeTruthy();
    expect((screen.getByRole("radio", { name: "Don't add" }) as HTMLInputElement).checked).toBe(true);
    reassign();

    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("Reassigned"));
    expect(addSearchKeyword).not.toHaveBeenCalled();
  });

  it("reassigns then adds the keyword with the product number when Add is chosen", async () => {
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    vi.mocked(addSearchKeyword).mockResolvedValue({ ok: true });
    const onSaved = vi.fn();
    renderWithKeyword(onSaved);

    await pickCandidate();
    fireEvent.click(screen.getByRole("radio", { name: "Add" }));
    reassign();

    await waitFor(() => expect(addSearchKeyword).toHaveBeenCalledWith("42", "Pika Box"));
    expect(postProductCorrection).toHaveBeenCalledWith(item, "new-uuid");
    expect(screen.getByRole("status").textContent).toContain("Reassigned and added the search keyword");
    expect(onSaved).toHaveBeenCalledWith({ variant: "info", title: "Reassigned and added the search keyword" });
  });

  it("shows the already-exists reason when the keyword was already registered (HTTP 200, ok false)", async () => {
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    vi.mocked(addSearchKeyword).mockResolvedValue({ ok: false, code: "KEYWORD_ALREADY_EXISTS" });
    renderWithKeyword();

    await pickCandidate();
    fireEvent.click(screen.getByRole("radio", { name: "Add" }));
    reassign();

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Reassigned, but the search keyword was not added (This keyword already exists)",
    );
  });

  it("shows the code when the keyword is refused for another reason", async () => {
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    vi.mocked(addSearchKeyword).mockResolvedValue({ ok: false, code: "SOME_CODE" });
    renderWithKeyword();

    await pickCandidate();
    fireEvent.click(screen.getByRole("radio", { name: "Add" }));
    reassign();

    expect((await screen.findByRole("alert")).textContent).toContain("(SOME_CODE)");
  });

  it("shows the API error message when adding the keyword throws", async () => {
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    vi.mocked(addSearchKeyword).mockRejectedValue(new ApiError("Not found", 404, null));
    renderWithKeyword();

    await pickCandidate();
    fireEvent.click(screen.getByRole("radio", { name: "Add" }));
    reassign();

    expect((await screen.findByRole("alert")).textContent).toContain("(Not found)");
  });

  it("does not add the keyword when the reassign fails", async () => {
    vi.mocked(postProductCorrection).mockRejectedValue(new ApiError("Conflict happened", 409, null));
    renderWithKeyword();

    await pickCandidate();
    fireEvent.click(screen.getByRole("radio", { name: "Add" }));
    reassign();

    expect((await screen.findByRole("alert")).textContent).toContain("Conflict happened");
    expect(addSearchKeyword).not.toHaveBeenCalled();
  });
});
