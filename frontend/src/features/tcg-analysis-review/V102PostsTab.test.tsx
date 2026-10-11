import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { api } from "../../lib/api";
import { V102PostsTab } from "./V102PostsTab";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  ApiError: class extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

const JOB = "job-1";
const SOURCE = "source-1";
const listResponse = {
  items: [
    {
      job_id: JOB, source_message_id: SOURCE, provider: "Supplier A", line_posted_at: "2026-10-09T01:00:00Z",
      job_review_reason_details: [{ code: "ext_code", source: "gemini", fix_stage: "extraction" }],
      item_count: 3, extraction_item_count: 2,
    },
  ],
  total: 1, limit: 20, offset: 0,
};
const detailResponse = {
  job_id: JOB, source_message_id: SOURCE, provider: "Supplier A", line_posted_at: "2026-10-09T01:00:00Z",
  lines: [{ number: 1, text: "line one" }, { number: 2, text: "line two" }, { number: 3, text: "line three" }],
  job_review_reason_details: [],
  items: [
    { id: "item-1", gemini_index: 0, source_lines: [1, 2], raw_price: "100", raw_quantity: null, review_reason_details: [] },
    { id: "item-2", gemini_index: 1, source_lines: [3], raw_price: null, raw_quantity: "2", review_reason_details: [] },
  ],
};

function mockGets(list = listResponse) {
  vi.mocked(api.get).mockImplementation((path: string) =>
    Promise.resolve(path.startsWith(`/tcg/v102/posts/${JOB}`) ? detailResponse : list),
  );
}

async function openModal() {
  render(<V102PostsTab />);
  const cell = await screen.findByText("Supplier A");
  fireEvent.click(cell);
  return screen.findByRole("dialog");
}

const linesInputs = () => screen.getAllByLabelText("Line numbers") as HTMLInputElement[];
const priceInputs = () => screen.getAllByLabelText("Price") as HTMLInputElement[];
const quantityInputs = () => screen.getAllByLabelText("Quantity") as HTMLInputElement[];

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  mockGets();
});
afterEach(() => cleanup());

describe("V102PostsTab list", () => {
  it("shows the posts with their counts", async () => {
    render(<V102PostsTab />);
    expect(await screen.findByText("Supplier A")).toBeTruthy();
    expect(screen.getByText("2 / 3")).toBeTruthy();
    expect(api.get).toHaveBeenCalledWith("/tcg/v102/posts?offset=0&limit=20");
  });

  it("shows an empty state when there are no posts", async () => {
    mockGets({ items: [], total: 0, limit: 20, offset: 0 });
    render(<V102PostsTab />);
    expect(await screen.findByText("No posts to fix")).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("opens the edit modal when a row is clicked", async () => {
    const dialog = await openModal();
    expect(within(dialog).getByText("Fix the transcription")).toBeTruthy();
    await waitFor(() => expect(linesInputs().map((i) => i.value)).toEqual(["1,2", "3"]));
    expect(api.get).toHaveBeenCalledWith(`/tcg/v102/posts/${JOB}`);
    expect(within(dialog).getByText("line two")).toBeTruthy();
  });
});

describe("V102PostEditModal save", () => {
  it.each([
    ["zero", "0"],
    ["over the line count", "4"],
    ["duplicate", "1,1"],
    ["not an integer", "1.5"],
    ["empty", ""],
  ])("does not save when the line numbers are %s", async (_name, value) => {
    await openModal();
    await waitFor(() => expect(linesInputs()).toHaveLength(2));
    fireEvent.change(linesInputs()[0], { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(api.put).not.toHaveBeenCalled();
    await waitFor(() => expect(document.querySelector(".comp-field--error")).not.toBeNull());
  });

  it("does not save when every item is deleted", async () => {
    await openModal();
    await waitFor(() => expect(linesInputs()).toHaveLength(2));
    for (const button of screen.getAllByRole("button", { name: "Delete" }).filter((b) => b.textContent === "Delete")) {
      fireEvent.click(button);
    }
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(api.put).not.toHaveBeenCalled();
    expect(await screen.findByText("There are no items. Keep at least one")).toBeTruthy();
  });

  it("does not save a price longer than 200 characters", async () => {
    await openModal();
    await waitFor(() => expect(priceInputs()).toHaveLength(2));
    fireEvent.change(priceInputs()[0], { target: { value: "x".repeat(201) } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(api.put).not.toHaveBeenCalled();
    expect(await screen.findByText("Use 200 characters or fewer")).toBeTruthy();
  });

  it("sends blank price and quantity as null and new items without an id", async () => {
    vi.mocked(api.put).mockResolvedValue({ changed: true, item_ids: ["item-1", "item-2", "item-3"], enqueued: true });
    await openModal();
    await waitFor(() => expect(linesInputs()).toHaveLength(2));
    fireEvent.change(priceInputs()[0], { target: { value: "" } });
    fireEvent.change(quantityInputs()[0], { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Add item" }));
    await waitFor(() => expect(linesInputs()).toHaveLength(3));
    fireEvent.change(linesInputs()[2], { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.put).toHaveBeenCalledOnce());
    expect(api.put).toHaveBeenCalledWith(`/tcg/v102/posts/${JOB}/items`, {
      source_message_id: SOURCE,
      items: [
        { id: "item-1", source_lines: [1, 2], raw_price: null, raw_quantity: "5" },
        { id: "item-2", source_lines: [3], raw_price: null, raw_quantity: "2" },
        { source_lines: [2], raw_price: null, raw_quantity: null },
      ],
    });
    expect(await screen.findByText("Saved. Re-running the analysis")).toBeTruthy();
  });

  it("says there are no changes when the server reports changed=false", async () => {
    vi.mocked(api.put).mockResolvedValue({ changed: false, item_ids: ["item-1", "item-2"], enqueued: false });
    await openModal();
    await waitFor(() => expect(linesInputs()).toHaveLength(2));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("No changes")).toBeTruthy();
  });

  it("shows the API message in a warning when the server answers 422", async () => {
    const { ApiError } = await import("../../lib/api");
    vi.mocked(api.put).mockRejectedValue(new ApiError("source_lines out of range", 422, undefined));
    await openModal();
    await waitFor(() => expect(linesInputs()).toHaveLength(2));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("source_lines out of range");
  });
});
