import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import i18n from "../../i18n";
import { ReviewCsvPanel } from "./ReviewCsvPanel";

vi.mock("../../lib/api", async importOriginal => ({
  ...await importOriginal<typeof import("../../lib/api")>(),
  api: { postForm: vi.fn(), getBlob: vi.fn() },
}));

const sample = () => new File(["a,b"], "fix.csv", { type: "text/csv" });
const preview = {
  total_rows: 3, digest: "a".repeat(64),
  applies: [{ line: 2, extraction_item_id: "i1", kind: "product", product_code: "PM-00001", name: "Pikachu" }],
  errors: [{ line: 3, extraction_item_id: "i2", code: "REVIEW_CSV_STALE_REVISION", detail: "" }],
};

async function choose() {
  fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [sample()] } });
  fireEvent.click(screen.getByRole("button", { name: "Review contents" }));
  await screen.findByRole("region", { name: "Review" });
}

beforeEach(async () => { vi.resetAllMocks(); await i18n.changeLanguage("en"); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("review CSV panel", () => {
  it("downloads the export through the authenticated blob API", async () => {
    vi.mocked(api.getBlob).mockResolvedValue(new Blob(["x"]));
    URL.createObjectURL = vi.fn(() => "blob:x");
    URL.revokeObjectURL = vi.fn();
    render(<ReviewCsvPanel onDone={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Download CSV" }));
    await waitFor(() => expect(api.getBlob).toHaveBeenCalledWith("/tcg/review/csv/export"));
  });

  it("rejects a non-CSV file before sending anything", () => {
    render(<ReviewCsvPanel onDone={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [new File(["x"], "a.txt")] } });
    expect(screen.getByRole("alert").textContent).toContain("CSV file");
    expect(api.postForm).not.toHaveBeenCalled();
  });

  it("shows items to apply and errors with reasons after the preview", async () => {
    vi.mocked(api.postForm).mockResolvedValueOnce(preview);
    render(<ReviewCsvPanel onDone={vi.fn()} />);
    await choose();
    expect(screen.getByText("Set product to PM-00001")).toBeTruthy();
    expect(screen.getByText(/changed after the download/)).toBeTruthy();
    expect(screen.getByText("Rows: 3 / To apply: 1 / Errors: 1")).toBeTruthy();
    expect(api.postForm).toHaveBeenCalledTimes(1);
  });

  it("sends the commit once with the confirmed digest", async () => {
    vi.mocked(api.postForm).mockResolvedValueOnce(preview).mockResolvedValueOnce({ saved: 1, failed: [], reanalyze_jobs: 1, errors: [] });
    render(<ReviewCsvPanel onDone={vi.fn()} />);
    await choose();
    const button = screen.getByRole("button", { name: "Apply" });
    fireEvent.click(button); fireEvent.click(button);
    await screen.findByRole("status");
    expect(api.postForm).toHaveBeenCalledTimes(2);
    const form = vi.mocked(api.postForm).mock.calls[1][1] as FormData;
    expect(vi.mocked(api.postForm).mock.calls[1][0]).toBe("/tcg/review/csv/commit");
    expect(form.get("confirmed_digest")).toBe("a".repeat(64));
    expect(screen.getByRole("status").textContent).toContain("Applied: 1");
  });

  it("disables apply when nothing can be applied", async () => {
    vi.mocked(api.postForm).mockResolvedValueOnce({ ...preview, applies: [] });
    render(<ReviewCsvPanel onDone={vi.fn()} />);
    await choose();
    expect((screen.getByRole("button", { name: "Apply" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("returns to file selection on a 409 and never as uncertain", async () => {
    vi.mocked(api.postForm).mockResolvedValueOnce(preview).mockRejectedValueOnce(new ApiError("REVIEW_CSV_DIGEST_MISMATCH", 409, null));
    render(<ReviewCsvPanel onDone={vi.fn()} />);
    await choose();
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    await screen.findByRole("alert");
    expect(screen.getByLabelText("CSV file")).toBeTruthy();
  });

  it("treats a server error on commit as uncertain and offers no retry", async () => {
    vi.mocked(api.postForm).mockResolvedValueOnce(preview).mockRejectedValueOnce(new ApiError("HTTP 500", 500, null));
    render(<ReviewCsvPanel onDone={vi.fn()} />);
    await choose();
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    await screen.findByRole("alert");
    expect(screen.queryByLabelText("CSV file")).toBeNull();
    expect(screen.queryByRole("button", { name: "Apply" })).toBeNull();
  });
});
