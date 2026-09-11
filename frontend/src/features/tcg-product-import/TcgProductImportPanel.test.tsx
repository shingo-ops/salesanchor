import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import i18n from "../../i18n";
import { TcgProductImportPanel } from "./TcgProductImportPanel";
vi.mock("../../lib/api", () => ({ api: { postForm: vi.fn() }, ApiError: class extends Error {} }));
const sample = () => new File(["mark,japanese_title\nA,Fixture"], "products.csv", { type: "text/csv" });
const preview = { filename: "products.csv", digest: "a".repeat(64), file_errors: [], total: 2, ok: 1, blocked: 1, rows: [
  { row_no: "2", japanese_title: "Fixture", mark: "A", blocking: [], warnings: ["NO_SEARCH_KEYWORD"] },
  { row_no: "3", japanese_title: "Invalid", mark: "B", blocking: ["RELEASE_DATE_FORMAT"], warnings: [] },
] };
async function review() {
  fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [sample()] } });
  fireEvent.click(screen.getByRole("button", { name: "Review contents" }));
  await screen.findByRole("region", { name: "Review contents" });
}
beforeEach(async () => { vi.resetAllMocks(); await i18n.changeLanguage("en"); });
afterEach(cleanup);
describe("product import confirmation", () => {
  it("does not send until review, then submits the exact file and digest once", async () => {
    vi.mocked(api.postForm).mockResolvedValueOnce(preview).mockResolvedValueOnce({ job_id: "receipt-1", total: 2, created: 1, skipped: 1 });
    render(<TcgProductImportPanel onDone={vi.fn()} />);
    expect(api.postForm).not.toHaveBeenCalled();
    await review();
    expect(api.postForm).toHaveBeenCalledTimes(1);
    expect(screen.getByText("No search keywords are specified.")).toBeTruthy();
    expect(screen.getByText("Use YYYY-MM-DD for the release date.")).toBeTruthy();
    const button = screen.getByRole("button", { name: "Confirm warnings and import" });
    fireEvent.click(button); fireEvent.click(button);
    await screen.findByText("Total: 2 / Registered: 1 / Skipped: 1");
    expect(api.postForm).toHaveBeenCalledTimes(2);
    const submitted = vi.mocked(api.postForm).mock.calls[1];
    expect(submitted[0]).toBe("/tcg/products/import/commit");
    expect(submitted[1].get("confirmed_digest")).toBe(preview.digest);
    expect(submitted[1].get("file")).toBe(vi.mocked(api.postForm).mock.calls[0][1].get("file"));
  });
  it("invalidates confirmation when choosing a replacement", async () => {
    vi.mocked(api.postForm).mockResolvedValue(preview);
    render(<TcgProductImportPanel onDone={vi.fn()} />); await review();
    fireEvent.click(screen.getByRole("button", { name: "Choose another file" }));
    expect(screen.queryByRole("button", { name: "Confirm warnings and import" })).toBeNull();
    expect((screen.getByRole("button", { name: "Review contents" }) as HTMLButtonElement).disabled).toBe(true);
    expect(api.postForm).toHaveBeenCalledTimes(1);
  });
  it("refuses to register when all rows are blocked", async () => {
    vi.mocked(api.postForm).mockResolvedValue({ ...preview, ok: 0 });
    render(<TcgProductImportPanel onDone={vi.fn()} />); await review();
    expect((screen.getByRole("button", { name: "Confirm warnings and import" }) as HTMLButtonElement).disabled).toBe(true);
  });
  it("locks registration after an uncertain response without retrying", async () => {
    vi.mocked(api.postForm).mockResolvedValueOnce(preview).mockRejectedValueOnce(new Error("network"));
    render(<TcgProductImportPanel onDone={vi.fn()} />); await review();
    fireEvent.click(screen.getByRole("button", { name: "Confirm warnings and import" }));
    await screen.findByRole("alert");
    expect(screen.queryByRole("button", { name: "Confirm warnings and import" })).toBeNull();
    expect(screen.queryByLabelText("CSV file")).toBeNull();
    expect(api.postForm).toHaveBeenCalledTimes(2);
  });
  it("rejects wrong extension, empty and oversized files before requests", () => {
    render(<TcgProductImportPanel onDone={vi.fn()} />);
    for (const file of [new File(["x"], "a.txt"), new File([], "a.csv"), new File([new Uint8Array(2097153)], "a.csv")]) {
      fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [file] } });
      expect(screen.getByRole("alert")).toBeTruthy();
    }
    expect(api.postForm).not.toHaveBeenCalled();
  });
  it("takes a dropped file and ignores drops while the request is pending", async () => {
    let finish!: (value: typeof preview) => void;
    vi.mocked(api.postForm).mockImplementation(() => new Promise(resolve => { finish = resolve as typeof finish; }));
    render(<TcgProductImportPanel onDone={vi.fn()} />);
    const region = screen.getByRole("region");
    fireEvent.drop(region, { dataTransfer: { files: [sample()] } });
    fireEvent.click(screen.getByRole("button", { name: "Review contents" }));
    fireEvent.drop(region, { dataTransfer: { files: [sample(), sample()] } });
    finish(preview);
    await screen.findByRole("region", { name: "Review contents" });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(api.postForm).toHaveBeenCalledTimes(1);
  });
  it("keeps preview errors separate from a successful empty result", async () => {
    vi.mocked(api.postForm).mockRejectedValue(new Error("offline"));
    render(<TcgProductImportPanel onDone={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [sample()] } });
    fireEvent.click(screen.getByRole("button", { name: "Review contents" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("No products have been registered"));
    expect(screen.queryByRole("button", { name: "Confirm warnings and import" })).toBeNull();
  });
});
