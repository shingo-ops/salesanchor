import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import i18n from "../../i18n";
import { TcgProductDetailDrawer } from "./TcgProductDetailDrawer";
import { addExcludeWord } from "./productDetailModel";
vi.mock("../../lib/api", async importOriginal => ({ ...await importOriginal<typeof import("../../lib/api")>(), api: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
const lookups = { product_kind_id: [], work_id: [{ id: "3", name: "Game A", is_active: true }, { id: "4", name: "Game B", is_active: true }], manufacturer_id: [], product_category_id: [], product_format_id: [{ id: "7", name: "Booster Box", is_active: true, game_ids: ["3"] }, { id: "8", name: "Starter Deck", is_active: true, game_ids: ["4"] }] };
const collision = {
  product_id: "42", name: "Other Box", work_name: "Some Work", matched_value: "ST01", matched_field: "mark",
  suggest_add_to_this: ["other box"], suggest_add_to_other: ["fixture"], already_excluded_by_this: [], already_excluded_by_other: [],
};
beforeEach(async () => { vi.resetAllMocks(); await i18n.changeLanguage("en"); vi.mocked(api.get).mockResolvedValue({ lookups }); });
afterEach(cleanup);
async function createProduct(response: unknown, onClose = vi.fn()) {
  vi.mocked(api.post).mockResolvedValueOnce(response);
  render(<TcgProductDetailDrawer productId={null} open mode="create" onClose={onClose} onSaved={vi.fn()} />);
  const title = await screen.findByLabelText(/Japanese name/);
  fireEvent.change(title, { target: { value: "Fixture" } });
  fireEvent.submit(title.closest("form") as HTMLFormElement);
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  return onClose;
}
describe("TcgProductDetailDrawer code collisions", () => {
  it("keeps the drawer open and shows the warning when the create response has collisions", async () => {
    const onClose = await createProduct({ ok: true, product_id: "1", code_collisions: [collision] });
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Other Box (Some Work)");
    expect(alert.textContent).toContain("ST01");
    expect(alert.textContent).toContain("other box");
    expect(alert.textContent).toContain("fixture");
    expect(onClose).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Create" }) as HTMLButtonElement).disabled).toBe(true);
  });
  it("says exclude keywords are registered when there is nothing to suggest", async () => {
    await createProduct({ ok: true, product_id: "1", code_collisions: [{ ...collision, suggest_add_to_this: [], suggest_add_to_other: [] }] });
    expect((await screen.findByRole("alert")).textContent).toContain("Exclude keywords are already registered");
  });
  it("closes as before when there are no collisions", async () => {
    const onClose = await createProduct({ ok: true, product_id: "1", code_collisions: [] });
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("The product code overlaps existing products")).toBeNull();
  });
  it("closes as before when the response has no code_collisions field", async () => {
    const onClose = await createProduct({ ok: true, product_id: "1" });
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });
});

const REVISION = "a".repeat(64);
const detailOf = (id: string, exclude: string[]) => ({
  revision: REVISION, lookups,
  product: { id, code: "PM-" + id, japanese_title: "Other Box", english_title: null, mark: "ST01", release_date: null,
    product_kind_id: null, work_id: "3", manufacturer_id: null, product_category_id: null,
    search_keywords: ["ob"], exclude_keywords: exclude, required_output_value: null, category_class: "x", is_active: true, created_at: "2026-01-01",
    product_format_id: null, blank_confirmations: [] as string[] },
});
function routeGet(detail: unknown) {
  vi.mocked(api.get).mockImplementation(async (url: string) => url.startsWith("/tcg/products/detail/") ? detail : { lookups });
}
const confirmAdd = () => fireEvent.click(screen.getByRole("button", { name: "Add" }));
describe("adding exclude keywords from the collision notice", () => {
  const withCollision = () => createProduct({ ok: true, product_id: "1", code_collisions: [collision] });
  it("adds to the other product via the detail PUT with the latest revision after confirming", async () => {
    routeGet(detailOf("42", ["old"])); vi.mocked(api.put).mockResolvedValue(detailOf("42", ["old", "fixture"]));
    await withCollision();
    fireEvent.click(await screen.findByRole("button", { name: "Add to that product" }));
    expect(screen.getByText(/Add "fixture" to the exclude keywords of Other Box \(Some Work\)/)).toBeTruthy();
    expect(api.put).not.toHaveBeenCalled();
    confirmAdd();
    await screen.findByText("Added");
    expect(api.get).toHaveBeenCalledWith("/tcg/products/detail/42");
    const [url, body] = vi.mocked(api.put).mock.calls[0] as [string, Record<string, unknown>];
    expect(url).toBe("/tcg/products/detail/42");
    expect(body.revision).toBe(REVISION);
    expect(body.exclude_keywords).toEqual(["old", "fixture"]);
    expect(body.search_keywords).toEqual(["ob"]);
    expect(body.japanese_title).toBe("Other Box");
    expect(screen.queryByRole("button", { name: "Add to that product" })).toBeNull();
  });
  it("shows already registered without calling PUT when the word exists", async () => {
    routeGet(detailOf("42", ["fixture"]));
    await withCollision();
    fireEvent.click(await screen.findByRole("button", { name: "Add to that product" })); confirmAdd();
    await screen.findByText("Already registered");
    expect(api.put).not.toHaveBeenCalled();
  });
  it("shows an error and keeps the button when saving fails", async () => {
    routeGet(detailOf("42", [])); vi.mocked(api.put).mockRejectedValue(new Error("boom"));
    await withCollision();
    fireEvent.click(await screen.findByRole("button", { name: "Add to that product" })); confirmAdd();
    await screen.findByText(/Could not add the keyword/);
    expect(screen.getByRole("button", { name: "Add to that product" })).toBeTruthy();
  });
  it("shows the conflict message on a revision conflict (409)", async () => {
    routeGet(detailOf("42", [])); vi.mocked(api.put).mockRejectedValue(new ApiError("conflict", 409, null));
    await withCollision();
    fireEvent.click(await screen.findByRole("button", { name: "Add to that product" })); confirmAdd();
    await screen.findByText(/This product was changed elsewhere/);
  });
  it("adds to the just-created product via the same PUT after confirming", async () => {
    routeGet(detailOf("1", [])); vi.mocked(api.put).mockResolvedValue(detailOf("1", ["other box"]));
    await withCollision();
    fireEvent.click(await screen.findByRole("button", { name: "Add to this product" })); confirmAdd();
    await screen.findByText("Added");
    const [url, body] = vi.mocked(api.put).mock.calls[0] as [string, Record<string, unknown>];
    expect(url).toBe("/tcg/products/detail/1");
    expect(body.exclude_keywords).toEqual(["other box"]);
  });
  it("only fills the exclude keywords field when editing, without calling the API", async () => {
    routeGet(detailOf("7", ["old"]));
    vi.mocked(api.put).mockResolvedValue({ ...detailOf("7", ["old"]), code_collisions: [collision] });
    render(<TcgProductDetailDrawer productId={7} mode="edit" onClose={vi.fn()} onSaved={vi.fn()} />);
    const title = await screen.findByLabelText(/Japanese name/);
    fireEvent.change(title, { target: { value: "Other Box 2" } });
    fireEvent.submit(title.closest("form") as HTMLFormElement);
    fireEvent.click(await screen.findByRole("button", { name: "Add to this product" }));
    await screen.findByText(/Added to the field/);
    expect((screen.getByRole("textbox", { name: /Exclusion keywords/ }) as HTMLTextAreaElement).value).toBe("old\nother box");
    expect(api.put).toHaveBeenCalledTimes(1);
  });
});

describe("ADR-1020 format and blank confirmations", () => {
  const combo = (name: RegExp) => screen.getByRole("combobox", { name });
  const box = (name: string) => screen.getByRole("checkbox", { name }) as HTMLInputElement;
  const renderEdit = (product: Record<string, unknown>) => {
    const base = detailOf("42", []);
    routeGet({ ...base, product: { ...base.product, ...product } });
    render(<TcgProductDetailDrawer productId={42} onClose={vi.fn()} onSaved={vi.fn()} />);
  };
  const saveWithNewTitle = async () => {
    const title = await screen.findByLabelText(/Japanese name/);
    fireEvent.change(title, { target: { value: "Changed" } });
    fireEvent.submit(title.closest("form") as HTMLFormElement);
  };
  it("offers only formats linked to the chosen work and sends them on create", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ ok: true, product_id: "1" });
    render(<TcgProductDetailDrawer productId={null} open mode="create" onClose={vi.fn()} onSaved={vi.fn()} />);
    const title = await screen.findByLabelText(/Japanese name/);
    fireEvent.change(combo(/^Work/), { target: { value: "3" } });
    expect(screen.getByRole("option", { name: "Booster Box" })).toBeTruthy();
    expect(screen.queryByRole("option", { name: "Starter Deck" })).toBeNull();
    fireEvent.change(combo(/^Format/), { target: { value: "7" } });
    fireEvent.click(box("English name: checked, none exists"));
    fireEvent.change(title, { target: { value: "Fixture" } });
    fireEvent.submit(title.closest("form") as HTMLFormElement);
    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect(body.product_format_id).toBe(7);
    expect(body.blank_confirmations).toEqual(["name_en"]);
  });
  it("clears the format when the work changes to an unlinked one", async () => {
    render(<TcgProductDetailDrawer productId={null} open mode="create" onClose={vi.fn()} onSaved={vi.fn()} />);
    await screen.findByLabelText(/Japanese name/);
    fireEvent.change(combo(/^Work/), { target: { value: "3" } });
    fireEvent.change(combo(/^Format/), { target: { value: "7" } });
    expect((combo(/^Format/) as HTMLSelectElement).value).toBe("7");
    fireEvent.change(combo(/^Work/), { target: { value: "4" } });
    expect((combo(/^Format/) as HTMLSelectElement).value).toBe("");
  });
  it("unticks and disables the confirmation once a value is entered", async () => {
    render(<TcgProductDetailDrawer productId={null} open mode="create" onClose={vi.fn()} onSaved={vi.fn()} />);
    await screen.findByLabelText(/Japanese name/);
    fireEvent.click(box("Model number: checked, none exists"));
    expect(box("Model number: checked, none exists").checked).toBe(true);
    fireEvent.change(screen.getByLabelText(/Model number/, { selector: "input[type=text], input:not([type])" }), { target: { value: "ST01" } });
    expect(box("Model number: checked, none exists").checked).toBe(false);
    expect(box("Model number: checked, none exists").disabled).toBe(true);
  });
  it("loads saved format and confirmations in edit mode and resends them", async () => {
    vi.mocked(api.put).mockResolvedValue(detailOf("42", []));
    renderEdit({ work_id: "3", product_format_id: 7, blank_confirmations: ["mark"], mark: null });
    await screen.findByLabelText(/Japanese name/);
    expect((combo(/^Format/) as HTMLSelectElement).value).toBe("7");
    expect(box("Model number: checked, none exists").checked).toBe(true);
    await saveWithNewTitle();
    await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
    const body = vi.mocked(api.put).mock.calls[0][1] as Record<string, unknown>;
    expect(body.product_format_id).toBe(7);
    expect(body.blank_confirmations).toEqual(["mark"]);
  });
  it("shows the missing notice without blocking save", async () => {
    vi.mocked(api.put).mockResolvedValue(detailOf("42", []));
    renderEdit({ english_title: null, blank_confirmations: [] });
    await screen.findByLabelText(/Japanese name/);
    expect(screen.getAllByText(/Not entered yet\. Enter a value/).length).toBeGreaterThan(0);
    await saveWithNewTitle();
    await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  });
  it("refuses to open a detail without blank_confirmations", async () => {
    const base = detailOf("42", []);
    const { blank_confirmations: _omit, ...product } = base.product;
    routeGet({ ...base, product });
    render(<TcgProductDetailDrawer productId={42} onClose={vi.fn()} onSaved={vi.fn()} />);
    await screen.findByText(/Could not load the product details/);
    expect(screen.queryByLabelText(/Japanese name/)).toBeNull();
    expect(api.put).not.toHaveBeenCalled();
  });
  it("keeps confirmations and format when adding an exclude word", async () => {
    const base = detailOf("42", []);
    routeGet({ ...base, product: { ...base.product, product_format_id: 7, blank_confirmations: ["name_en"] } });
    vi.mocked(api.put).mockResolvedValue(base);
    await expect(addExcludeWord(42, "fixture")).resolves.toBe("added");
    const body = vi.mocked(api.put).mock.calls[0][1] as Record<string, unknown>;
    expect(body.blank_confirmations).toEqual(["name_en"]);
    expect(body.product_format_id).toBe(7);
  });
});
