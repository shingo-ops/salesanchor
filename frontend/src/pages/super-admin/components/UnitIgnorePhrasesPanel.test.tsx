/**
 * UnitIgnorePhrasesPanel テスト（単位にしない言い回しの一覧・追加・編集・無効化・削除）
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import i18n from "../../../i18n";
import { UnitIgnorePhrasesPanel } from "./UnitIgnorePhrasesPanel";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  ApiError: class extends Error {},
}));

const PATH = "/super-admin/unit-ignore-phrases";

const rows = [
  { id: 1, phrase: "ALPHA PHRASE", note: "note a", is_active: true, created_at: "", updated_at: "" },
  { id: 2, phrase: "BETA PHRASE", note: null, is_active: false, created_at: "", updated_at: "" },
];

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockResolvedValue(rows);
  vi.mocked(api.post).mockResolvedValue({});
  vi.mocked(api.patch).mockResolvedValue({});
  vi.mocked(api.delete).mockResolvedValue(undefined);
});

afterEach(() => cleanup());

it("loads and lists phrases from the API", async () => {
  render(<UnitIgnorePhrasesPanel />);
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(PATH));
  await screen.findByText("ALPHA PHRASE");
  expect(screen.getByText("BETA PHRASE")).toBeTruthy();
});

it("creates a phrase with note via the drawer form", async () => {
  render(<UnitIgnorePhrasesPanel />);
  await screen.findByText("ALPHA PHRASE");
  fireEvent.click(screen.getByTestId("unit-ignore-new"));
  fireEvent.change(await screen.findByLabelText(/^Phrase \*/), { target: { value: "NEW PHRASE" } });
  fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "why" } });
  fireEvent.click(screen.getByTestId("unit-ignore-submit"));
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith(PATH, { phrase: "NEW PHRASE", note: "why", is_active: true }),
  );
});

it("edits a phrase and can deactivate it via PATCH", async () => {
  render(<UnitIgnorePhrasesPanel />);
  fireEvent.click(await screen.findByText("ALPHA PHRASE"));
  fireEvent.click(await screen.findByLabelText(/Active/));
  fireEvent.click(screen.getByTestId("unit-ignore-submit"));
  await waitFor(() =>
    expect(api.patch).toHaveBeenCalledWith(`${PATH}/1`, { phrase: "ALPHA PHRASE", note: "note a", is_active: false }),
  );
});

it("deletes the selected phrase after confirmation", async () => {
  render(<UnitIgnorePhrasesPanel />);
  await screen.findByText("ALPHA PHRASE");
  fireEvent.click(screen.getAllByRole("checkbox")[1]);
  fireEvent.click(screen.getByTestId("unit-ignore-bulk-delete"));
  const deleteButtons = await screen.findAllByRole("button", { name: "Delete" });
  fireEvent.click(deleteButtons[deleteButtons.length - 1]);
  await waitFor(() => expect(api.delete).toHaveBeenCalled());
});
