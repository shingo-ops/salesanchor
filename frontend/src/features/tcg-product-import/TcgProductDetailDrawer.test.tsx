import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import i18n from "../../i18n";
import { TcgProductDetailDrawer } from "./TcgProductDetailDrawer";
vi.mock("../../lib/api", async importOriginal => ({ ...await importOriginal<typeof import("../../lib/api")>(), api: { get: vi.fn(), post: vi.fn() } }));
const lookups = { product_kind_id: [], work_id: [], manufacturer_id: [], product_category_id: [] };
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
