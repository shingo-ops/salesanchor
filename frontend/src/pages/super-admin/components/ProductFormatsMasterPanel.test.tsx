/**
 * ProductFormatsMasterPanel テスト（ADR-1020 便2b-2）
 *
 * カバー:
 *   - 一覧の「使えるゲーム」列
 *   - 無効なゲームは選択肢に出ない
 *   - 新規: POST の後に PUT で置き換え
 *   - 編集: ゲームが変わらなければ PUT を呼ばない／変わったら選んだ一覧で置き換え
 *   - 外せないとき: ドロワーを開いたまま理由を出す
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../../lib/api";
import i18n from "../../../i18n";
import { ProductFormatsMasterPanel } from "./ProductFormatsMasterPanel";

vi.mock("../../../lib/api", () => {
  class ApiError extends Error {
    status: number;
    responseDetail: unknown;
    constructor(message: string, status: number, detail?: unknown) {
      super(message);
      this.status = status;
      this.responseDetail = detail;
    }
  }
  return {
    api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
    ApiError,
  };
});

const formatRow = {
  id: 7,
  code: "BOX",
  name: "Booster Box",
  name_en: null,
  line_id: null,
  display_order: 100,
  is_active: true,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
  game_ids: [1, 2],
};

const games = [
  { id: 1, code: "pokemon", name_ja: "Pokemon", name_en: null, is_active: true },
  { id: 2, code: "onepiece", name_ja: "One Piece", name_en: null, is_active: true },
  { id: 3, code: "old", name_ja: "Old Game", name_en: null, is_active: false },
];

const formatsCalls = () =>
  vi.mocked(api.get).mock.calls.filter(c => c[0] === "/super-admin/product-formats").length;

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path === "/super-admin/product-formats") return Promise.resolve([formatRow]);
    if (path === "/super-admin/product-lines") return Promise.resolve([]);
    if (path === "/super-admin/tcg/types") return Promise.resolve(games);
    return Promise.resolve([]);
  });
});

afterEach(() => cleanup());

const openEdit = async () => {
  render(<ProductFormatsMasterPanel />);
  fireEvent.click(await screen.findByText("Booster Box"));
  await screen.findByTestId("product-format-games-option-1");
};

const toggleGame = (id: number) => {
  fireEvent.click(screen.getByTestId(`product-format-games-option-${id}`));
};

it("lists usable games for each format", async () => {
  render(<ProductFormatsMasterPanel />);
  expect(await screen.findByText("Pokemon, One Piece")).toBeTruthy();
});

it("does not offer inactive games", async () => {
  render(<ProductFormatsMasterPanel />);
  await screen.findByText("Booster Box");
  fireEvent.click(screen.getByTestId("product-formats-new"));
  expect(await screen.findByTestId("product-format-games-option-1")).toBeTruthy();
  expect(screen.queryByTestId("product-format-games-option-3")).toBeNull();
});

it("shows every active game as a checkbox right after the drawer opens, without a button", async () => {
  await openEdit();
  expect(screen.getByTestId("product-format-games-option-1")).toBeTruthy();
  expect(screen.getByTestId("product-format-games-option-2")).toBeTruthy();
  expect(screen.queryByTestId("product-format-games-option-3")).toBeNull();
  expect(screen.queryByTestId("product-format-games-button")).toBeNull();
});

it("checks the games already saved for the format", async () => {
  await openEdit();
  expect((screen.getByTestId("product-format-games-option-1") as HTMLInputElement).checked).toBe(true);
  expect((screen.getByTestId("product-format-games-option-2") as HTMLInputElement).checked).toBe(true);
});

it("creates a format and then replaces its games", async () => {
  vi.mocked(api.post).mockResolvedValue({ ...formatRow, id: 50, game_ids: [] });
  vi.mocked(api.put).mockResolvedValue({ ...formatRow, id: 50, game_ids: [1] });
  render(<ProductFormatsMasterPanel />);
  await screen.findByText("Booster Box");
  fireEvent.click(screen.getByTestId("product-formats-new"));
  const dialog = await screen.findByRole("dialog");
  const inputs = dialog.querySelectorAll("input[required]");
  fireEvent.change(inputs[0], { target: { value: "NEWFMT" } });
  fireEvent.change(inputs[1], { target: { value: "New Format" } });
  toggleGame(1);
  fireEvent.click(screen.getByRole("button", { name: "Create" }));
  await waitFor(() =>
    expect(api.put).toHaveBeenCalledWith("/super-admin/product-formats/50/games", { game_ids: [1] })
  );
  expect(api.post).toHaveBeenCalledTimes(1);
  // ADR-1038 便3a: 旧列 type_master_id の単独欄は無く、送信にも含めない
  expect(vi.mocked(api.post).mock.calls[0][1]).not.toHaveProperty("type_master_id");
});

it("skips the games call when games are unchanged", async () => {
  vi.mocked(api.patch).mockResolvedValue(formatRow);
  await openEdit();
  const dialog = await screen.findByRole("dialog");
  const nameInput = within(dialog).getByDisplayValue("Booster Box");
  fireEvent.change(nameInput, { target: { value: "Booster Box 2" } });
  fireEvent.click(screen.getByRole("button", { name: "Update" }));
  await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
  expect(api.put).not.toHaveBeenCalled();
});

it("sends sorted game ids when games change", async () => {
  vi.mocked(api.patch).mockResolvedValue(formatRow);
  vi.mocked(api.put).mockResolvedValue({ ...formatRow, game_ids: [2] });
  await openEdit();
  toggleGame(1);
  fireEvent.click(screen.getByRole("button", { name: "Update" }));
  await waitFor(() =>
    expect(api.put).toHaveBeenCalledWith("/super-admin/product-formats/7/games", { game_ids: [2] })
  );
});

it("keeps the drawer open and explains a game in use", async () => {
  vi.mocked(api.patch).mockResolvedValue(formatRow);
  vi.mocked(api.put).mockRejectedValue(new ApiError("PRODUCT_FORMAT_GAME_IN_USE", 409, undefined));
  await openEdit();
  const before = formatsCalls();
  toggleGame(2);
  fireEvent.click(screen.getByRole("button", { name: "Update" }));
  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toContain("Products with this sub-category use that game");
  expect(screen.getByRole("button", { name: "Update" })).toBeTruthy();
  await waitFor(() => expect(formatsCalls()).toBeGreaterThan(before));
  expect(formatsCalls()).toBeGreaterThanOrEqual(2);
});
