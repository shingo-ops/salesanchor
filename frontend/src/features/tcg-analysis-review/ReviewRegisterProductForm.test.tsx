import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ApiError } from "../../lib/api";
import { joinKeywordLines, ReviewRegisterProductForm } from "./ReviewRegisterProductForm";
import { checkProductDuplicates, createProduct, fetchRegistrationForm, postProductCorrection } from "./reviewActions";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("./reviewActions", () => ({
  fetchRegistrationForm: vi.fn(),
  checkProductDuplicates: vi.fn(),
  createProduct: vi.fn(),
  postProductCorrection: vi.fn(),
}));

const item = {
  extraction_item_id: "item-1",
  source_message_id: "msg-1",
  provider: "Supplier A",
  raw_text: "",
  gemini: { name: "Pika Box" },
  system: {},
};

const form = {
  item: { extraction_item_id: "item-1", source_message_id: "msg-1", raw_name: "Pika Box" },
  lookups: {
    product_kind_id: [{ id: "1", name: "Card" }],
    work_id: [{ id: "2", name: "Pokemon" }],
    manufacturer_id: [{ id: "3", name: "Nintendo" }],
    product_category_id: [{ id: "4", name: "Booster" }],
  },
};

const BODY = {
  product_kind_id: "1",
  work_id: "2",
  manufacturer_id: "3",
  product_category_id: "4",
  mark: "",
  japanese_title: "Pika Box",
  english_title: "",
  release_date: "",
  search_keywords: "Pika Box",
  exclude_keywords: "",
};

async function pick(label: string, typed: string, optionName: string) {
  const input = screen.getByRole("combobox", { name: label });
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value: typed } });
  fireEvent.click(await screen.findByRole("option", { name: optionName }, { timeout: 2000 }));
}

async function fillRequired() {
  await pick("Product type", "c", "Card");
  await pick("Title / series", "p", "Pokemon");
  await pick("Manufacturer", "n", "Nintendo");
  await pick("Category", "b", "Booster");
}

async function renderForm(onSaved = vi.fn(), onRefresh = vi.fn().mockResolvedValue(undefined)) {
  render(<ReviewRegisterProductForm item={item} onRefresh={onRefresh} onSaved={onSaved} searchDebounceMs={0} />);
  await screen.findByRole("combobox", { name: "Product type" });
  return { onSaved, onRefresh };
}

const click = (name: string) => fireEvent.click(screen.getByRole("button", { name }));

beforeEach(async () => {
  vi.resetAllMocks();
  vi.mocked(fetchRegistrationForm).mockResolvedValue(form);
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("joinKeywordLines", () => {
  it("trims each line, drops empty lines and joins with a comma", () => {
    expect(joinKeywordLines("  a \n\n b\n   \nc")).toBe("a,b,c");
  });
});

describe("ReviewRegisterProductForm", () => {
  it("shows guidance and no input when the row already has a product (404)", async () => {
    const error = Object.assign(new ApiError("PRODUCT_MASTER_V2_ALREADY_RESOLVED", 404, null), { status: 404 });
    vi.mocked(fetchRegistrationForm).mockRejectedValue(error);
    render(<ReviewRegisterProductForm item={item} onRefresh={async () => undefined} />);

    expect(await screen.findByText(/This row already has a product/)).toBeTruthy();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("shows the failure reason for another load error", async () => {
    vi.mocked(fetchRegistrationForm).mockRejectedValue(new ApiError("boom", 500, null));
    render(<ReviewRegisterProductForm item={item} onRefresh={async () => undefined} />);

    expect((await screen.findByRole("alert")).textContent).toBe("Could not register (boom)");
  });

  it("marks every empty required field and does not call the API when checking", async () => {
    await renderForm();
    fireEvent.change(screen.getByLabelText(/Japanese name/), { target: { value: "" } });

    click("Check for similar products");

    expect((await screen.findAllByText("Required")).length).toBe(5);
    expect(checkProductDuplicates).not.toHaveBeenCalled();
  });

  it("registers with no candidates, then reassigns to the new product (in this order)", async () => {
    vi.mocked(checkProductDuplicates).mockResolvedValue({ candidates: [] });
    vi.mocked(createProduct).mockResolvedValue({ ok: true, product_id: "42" });
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    const { onSaved, onRefresh } = await renderForm();
    await fillRequired();

    click("Check for similar products");
    fireEvent.click(await screen.findByRole("button", { name: "Register and reassign" }));

    await waitFor(() => expect(onRefresh).toHaveBeenCalledOnce());
    expect(checkProductDuplicates).toHaveBeenCalledWith(item, BODY);
    expect(createProduct).toHaveBeenCalledWith(item, BODY, false);
    expect(postProductCorrection).toHaveBeenCalledWith(item, "42");
    expect(vi.mocked(createProduct).mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(postProductCorrection).mock.invocationCallOrder[0],
    );
    expect(onSaved).toHaveBeenCalledWith({ variant: "info", title: "Registered new product (No. 42) and reassigned this row" });
  });

  it("sends the search keywords as one comma-joined string", async () => {
    vi.mocked(checkProductDuplicates).mockResolvedValue({ candidates: [] });
    await renderForm();
    await fillRequired();
    fireEvent.change(screen.getByLabelText(/Search keywords/), { target: { value: " a \n\n b " } });

    click("Check for similar products");

    await waitFor(() => expect(checkProductDuplicates).toHaveBeenCalledOnce());
    expect(vi.mocked(checkProductDuplicates).mock.calls[0][1].search_keywords).toBe("a,b");
  });

  const withCandidates = async () => {
    vi.mocked(checkProductDuplicates).mockResolvedValue({ candidates: [{ product_id: "7", japanese_title: "Pika Box Old" }] });
    const rendered = await renderForm();
    await fillRequired();
    click("Check for similar products");
    await screen.findByRole("group", { name: "Is the same product in this list?" });
    return rendered;
  };

  it("reassigns to the chosen candidate without registering", async () => {
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    const { onRefresh } = await withCandidates();

    fireEvent.click(screen.getByRole("radio", { name: /Pika Box Old/ }));
    click("Reassign to this product");

    await waitFor(() => expect(onRefresh).toHaveBeenCalledOnce());
    expect(postProductCorrection).toHaveBeenCalledWith(item, "7");
    expect(createProduct).not.toHaveBeenCalled();
  });

  it("registers with force when None of these is chosen", async () => {
    vi.mocked(createProduct).mockResolvedValue({ ok: true, product_id: "42" });
    vi.mocked(postProductCorrection).mockResolvedValue({ ok: true, saved: 1 });
    await withCandidates();

    fireEvent.click(screen.getByRole("radio", { name: /None of these/ }));
    click("Register and reassign");

    await waitFor(() => expect(postProductCorrection).toHaveBeenCalledWith(item, "42"));
    expect(createProduct).toHaveBeenCalledWith(item, BODY, true);
  });

  it("goes back to the candidate question when the registration finds a new duplicate", async () => {
    vi.mocked(checkProductDuplicates).mockResolvedValue({ candidates: [] });
    vi.mocked(createProduct).mockResolvedValue({ ok: false, code: "DUPLICATE_CANDIDATE", candidates: [{ product_id: "9", japanese_title: "Late Dup" }] });
    await renderForm();
    await fillRequired();
    click("Check for similar products");
    fireEvent.click(await screen.findByRole("button", { name: "Register and reassign" }));

    expect(await screen.findByRole("radio", { name: /Late Dup/ })).toBeTruthy();
    expect(postProductCorrection).not.toHaveBeenCalled();
  });

  it("retries only the reassign after it failed, never registering twice", async () => {
    vi.mocked(checkProductDuplicates).mockResolvedValue({ candidates: [] });
    vi.mocked(createProduct).mockResolvedValue({ ok: true, product_id: "42" });
    vi.mocked(postProductCorrection).mockRejectedValueOnce(new ApiError("Conflict happened", 409, null)).mockResolvedValueOnce({ ok: true, saved: 1 });
    const { onSaved } = await renderForm();
    await fillRequired();
    click("Check for similar products");
    fireEvent.click(await screen.findByRole("button", { name: "Register and reassign" }));

    expect((await screen.findByRole("alert")).textContent).toContain("New product (No. 42) was registered, but reassigning failed (Conflict happened)");
    expect(screen.queryByRole("button", { name: "Register and reassign" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Check for similar products" })).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();

    click("Retry reassign only");

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(createProduct).toHaveBeenCalledOnce();
    expect(postProductCorrection).toHaveBeenCalledTimes(2);
    expect(postProductCorrection).toHaveBeenLastCalledWith(item, "42");
  });
});
