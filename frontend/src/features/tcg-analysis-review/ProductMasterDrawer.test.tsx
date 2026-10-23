/* eslint-disable local/no-japanese-literal -- テスト: 日本語の表示が変更前と同じであることを検証する（ADR-027・precedent: InboxMessageThread.discordSendError.test.tsx） */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { api, ApiError } from "../../lib/api";
import type { AnalysisReviewItem } from "./ItemComparison";
import { ProductMasterDrawer } from "./ProductMasterDrawer";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));

const JAPANESE = /[぀-ヿ一-鿿]/;

const baseItem = (issues: string[], name = "Pika Box"): AnalysisReviewItem => ({
  extraction_item_id: "ei-1",
  source_message_id: "sm-1",
  provider: "Supplier A",
  raw_text: "",
  gemini: { name },
  system: { product_uuid: "u-0", product_id: "PM-00001", product_title: "Current Title" },
  review_issues: issues,
});

const form = {
  item: { extraction_item_id: "ei-1", source_message_id: "sm-1", raw_name: "Pika Box" },
  lookups: {
    product_kind_id: [{ id: "k1", name: "Card" }],
    work_id: [{ id: "w1", name: "Pokemon" }],
    manufacturer_id: [{ id: "m1", name: "Nintendo" }],
    product_category_id: [{ id: "c1", name: "Booster" }],
    product_format_id: [
      { id: "7", name: "Box Set", is_active: true, game_ids: ["w1"] },
      { id: "8", name: "Pack Set", is_active: true, game_ids: ["w9"] },
    ],
  },
};

const candidates = [{ product_id: "PM-00002", product_uuid: "u-2", japanese_title: "Pika Master", search_keywords: "pika" }];

function renderDrawer(issues: string[], name?: string) {
  return render(<ProductMasterDrawer item={baseItem(issues, name)} onClose={vi.fn()} />);
}

/** 画面に出る文字・aria-label・placeholder をまとめて返す */
function visibleStrings(root: HTMLElement) {
  const attrs = Array.from(root.querySelectorAll("[aria-label],[placeholder]")).map((e) => `${e.getAttribute("aria-label") ?? ""}${e.getAttribute("placeholder") ?? ""}`);
  return `${root.textContent}${attrs.join("")}${root.querySelector("aside")?.getAttribute("aria-label") ?? ""}`;
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.get).mockImplementation((async (path: string) => (path.startsWith("/tcg/products/search") ? { candidates } : form)) as typeof api.get);
  vi.mocked(api.post).mockResolvedValue({ candidates: [] });
});
afterEach(async () => {
  cleanup();
  await i18n.changeLanguage("ja");
});

const lookupSelects = () => Array.from(document.querySelectorAll<HTMLSelectElement>(".pmd-field select"));
const optionValues = (select: HTMLSelectElement) => Array.from(select.options).map((o) => o.value).filter(Boolean);
async function fillLookups() {
  const ids = ["k1", "w1", "m1", "c1"];
  ids.forEach((id, i) => fireEvent.change(lookupSelects()[i], { target: { value: id } }));
}

describe("ProductMasterDrawer registration (ja)", () => {
  beforeEach(async () => { await i18n.changeLanguage("ja"); });

  it("shows the same Japanese text as before", async () => {
    renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    expect(await screen.findByText("商品マスタ新規登録")).toBeTruthy();
    expect(await screen.findByText("登録内容確認")).toBeTruthy();
    expect(screen.getByText("大分類: 未選択")).toBeTruthy();
    expect(screen.getByText("マーク: 未入力")).toBeTruthy();
    expect(screen.getByText("日本語タイトル: Pika Box")).toBeTruthy();
    expect(screen.getByRole("button", { name: "重複候補を確認" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "商品マスタに登録" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "閉じる" })).toBeTruthy();
    expect(document.querySelector("aside")?.getAttribute("aria-label")).toBe("商品マスタメンテナンス");
    expect(lookupSelects()[0].options[0].textContent).toBe("選択してください");
  });

  it("uses the shared control classes for inputs, textareas and buttons", async () => {
    renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("登録内容確認");
    const inputs = Array.from(document.querySelectorAll<HTMLInputElement>(".pmd-field input:not([type=checkbox])"));
    expect(inputs.length).toBe(4);
    for (const input of inputs) expect(input.className).toContain("comp-field__input");
    expect(lookupSelects().length).toBe(5);
    for (const select of lookupSelects()) expect(select.className).toContain("comp-select__control");
    const textareas = Array.from(document.querySelectorAll<HTMLTextAreaElement>(".pmd-field textarea"));
    expect(textareas.length).toBe(2);
    for (const textarea of textareas) expect(textarea.className).toContain("comp-field__textarea");
    for (const button of Array.from(document.querySelectorAll(".pmd-actions button"))) expect(button.className).toContain("comp-btn");
    expect(document.querySelector(".pmd-head button")?.className).toContain("comp-btn--icon-only");
  });

  it("keeps the register buttons disabled until every required value is set", async () => {
    renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("登録内容確認");
    const check = screen.getByRole("button", { name: "重複候補を確認" }) as HTMLButtonElement;
    const register = screen.getByRole("button", { name: "商品マスタに登録" }) as HTMLButtonElement;
    expect(check.disabled).toBe(true);
    expect(register.disabled).toBe(true);
    await fillLookups();
    expect(check.disabled).toBe(false);
    expect(register.disabled).toBe(false);
    const title = document.querySelectorAll<HTMLInputElement>(".pmd-field input")[1];
    fireEvent.change(title, { target: { value: "" } });
    expect(check.disabled).toBe(true);
    expect(register.disabled).toBe(true);
  });

  it("asks for confirmation when duplicates are found", async () => {
    vi.mocked(api.post).mockResolvedValue({ candidates: [{ product_id: "PM-00002", japanese_title: "Pika Dup", search_keywords: "" }] });
    renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("登録内容確認");
    await fillLookups();
    fireEvent.click(screen.getByRole("button", { name: "重複候補を確認" }));
    expect(await screen.findByText("既存商品の可能性があります（確認してください）")).toBeTruthy();
    expect(screen.getByText("重複候補を確認しました（新規商品です）")).toBeTruthy();
    expect((screen.getByRole("button", { name: "商品マスタに登録" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("checkbox", { name: "重複候補を確認しました（新規商品です）" }));
    expect((screen.getByRole("button", { name: "商品マスタに登録" }) as HTMLButtonElement).disabled).toBe(false);
  });
  it("offers only the formats of the chosen work and sends the format and blank marks", async () => {
    renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("登録内容確認");
    await fillLookups();
    expect(optionValues(lookupSelects()[4])).toEqual(["7"]);
    fireEvent.change(lookupSelects()[4], { target: { value: "7" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "英語タイトル：調べたが存在しない" }));
    fireEvent.click(screen.getByRole("button", { name: "商品マスタに登録" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        "/tcg/products",
        expect.objectContaining({ product_format_id: 7, blank_confirmations: ["name_en"], force: false }),
      ),
    );
  });

  it("uses select controls, not typed search inputs, for the five lookup fields", async () => {
    renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("登録内容確認");
    expect(lookupSelects().length).toBe(5);
    expect(document.querySelectorAll("[list], [id^=lookup-]").length).toBe(0);
  });

  it("disables the format select until a work is chosen", async () => {
    renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("登録内容確認");
    expect(lookupSelects()[4].disabled).toBe(true);
    fireEvent.change(lookupSelects()[1], { target: { value: "w1" } });
    expect(lookupSelects()[4].disabled).toBe(false);
  });

  it("offers only the children of the chosen work, and resets the format when the work changes", async () => {
    const wideForm = {
      ...form,
      lookups: { ...form.lookups, work_id: [{ id: "w1", name: "Pokemon" }, { id: "w9", name: "Other" }] },
    };
    vi.mocked(api.get).mockImplementation((async (path: string) => (path.startsWith("/tcg/products/search") ? { candidates } : wideForm)) as typeof api.get);
    renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("登録内容確認");
    fireEvent.change(lookupSelects()[1], { target: { value: "w1" } });
    expect(optionValues(lookupSelects()[4])).toEqual(["7"]);
    fireEvent.change(lookupSelects()[4], { target: { value: "7" } });
    expect(lookupSelects()[4].value).toBe("7");
    fireEvent.change(lookupSelects()[1], { target: { value: "w9" } });
    expect(optionValues(lookupSelects()[4])).toEqual(["8"]);
    expect(lookupSelects()[4].value).toBe("");
  });
});

describe("ProductMasterDrawer registration (en)", () => {
  beforeEach(async () => { await i18n.changeLanguage("en"); });

  it("shows no Japanese text, aria-label or placeholder", async () => {
    const { container } = renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    expect(await screen.findByText("Review entry")).toBeTruthy();
    expect(screen.getByText("New product master entry")).toBeTruthy();
    expect(screen.getByText("Major category: Not selected")).toBeTruthy();
    expect(screen.getByText("Mark: Not entered")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Check for duplicates" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Register in product master" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Close" })).toBeTruthy();
    expect(lookupSelects()[0].options[0].textContent).toBe("Select");
    expect(visibleStrings(container)).not.toMatch(JAPANESE);
  });

  it("shows the duplicate warning and the error line in English", async () => {
    vi.mocked(api.post).mockResolvedValue({ candidates: [{ product_id: "PM-00002", japanese_title: "Pika Dup", search_keywords: "" }] });
    const { container } = renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("Review entry");
    await fillLookups();
    fireEvent.click(screen.getByRole("button", { name: "Check for duplicates" }));
    expect(await screen.findByText("This may be an existing product (please check)")).toBeTruthy();
    expect(screen.getByText("I checked the possible duplicates (this is a new product)")).toBeTruthy();
    expect(visibleStrings(container)).not.toMatch(JAPANESE);
  });
});

describe("ProductMasterDrawer search keyword mode", () => {
  it("ja: keeps the sentence with the bold name", async () => {
    await i18n.changeLanguage("ja");
    renderDrawer(["PRODUCT_ID_UNRESOLVED"]);
    expect(screen.getByText("マスタ検索・検索キーワード追記")).toBeTruthy();
    const intro = document.querySelector(".pmd-body p") as HTMLElement;
    expect(intro.textContent).toBe("Gemini抽出名「Pika Box」を既存商品の検索キーワードに追記します。");
    expect(intro.querySelector("strong")?.textContent).toBe("Pika Box");
    expect(screen.getByRole("button", { name: "マスタを検索" })).toBeTruthy();
  });

  it("en: renders the bold name without escaping a user supplied ampersand", async () => {
    await i18n.changeLanguage("en");
    const { container } = renderDrawer(["PRODUCT_ID_UNRESOLVED"], "A&B <i>Box");
    const intro = container.querySelector(".pmd-body p") as HTMLElement;
    expect(intro.textContent).toBe("Add the Gemini extracted name “A&B <i>Box” to an existing product's search keywords.");
    expect(intro.querySelector("strong")?.textContent).toBe("A&B <i>Box");
    expect(intro.querySelector("i")).toBeNull();
    expect(visibleStrings(container)).not.toMatch(JAPANESE);
  });

  it("en: search results use the ghost button and show the add button after selecting", async () => {
    await i18n.changeLanguage("en");
    const { container } = renderDrawer(["PRODUCT_ID_UNRESOLVED"]);
    fireEvent.click(screen.getByRole("button", { name: "Search master" }));
    const candidate = await waitFor(() => {
      const el = container.querySelector(".pmd-search-candidate button");
      if (!el) throw new Error("no candidate yet");
      return el as HTMLElement;
    });
    expect(candidate.className).toContain("comp-btn--ghost");
    expect(candidate.className).toContain("pmd-candidate-btn");
    expect(candidate.querySelector("strong")?.textContent).toBe("PM-00002");
    fireEvent.click(candidate);
    expect(screen.getByRole("button", { name: "Add keyword" })).toBeTruthy();
    expect(screen.getByText("Keyword to add:")).toBeTruthy();
    expect(visibleStrings(container)).not.toMatch(JAPANESE);
  });
});

describe("ProductMasterDrawer excluded mode", () => {
  it("ja: shows the same text as before", async () => {
    await i18n.changeLanguage("ja");
    renderDrawer(["EXCLUDED"]);
    expect(screen.getByText("除外対象")).toBeTruthy();
    expect(screen.getByText("この商品は商品マスタの除外キーワードに一致したため、解析から除外されています。")).toBeTruthy();
    expect(screen.getByText("除外キーワードの確認・変更は 商品マスタV2 シートの Exclude Keywords 列から直接行ってください。")).toBeTruthy();
    expect(screen.getByText("（編集機能は今後のリリースで追加予定）")).toBeTruthy();
  });

  it("en: leaves only the sheet name in Japanese", async () => {
    await i18n.changeLanguage("en");
    const { container } = renderDrawer(["EXCLUDED"]);
    expect(screen.getByText("Excluded")).toBeTruthy();
    expect(visibleStrings(container).replace("商品マスタV2", "")).not.toMatch(JAPANESE);
  });
});

describe("ProductMasterDrawer assign mode", () => {
  it("ja: shows the buttons and keeps change disabled until a product is selected", async () => {
    await i18n.changeLanguage("ja");
    renderDrawer([]);
    const change = screen.getByRole("button", { name: "商品を変更する" }) as HTMLButtonElement;
    expect(change.disabled).toBe(true);
    expect(screen.getByRole("button", { name: "確認済みとして記録" })).toBeTruthy();
    expect(change.className).toContain("comp-btn--primary");
    const input = document.querySelector(".pmd-field input") as HTMLInputElement;
    expect(input.className).toContain("comp-field__input");
    expect(input.placeholder).toBe("商品名を入力");
  });

  it("en: shows no Japanese text", async () => {
    await i18n.changeLanguage("en");
    const { container } = renderDrawer([]);
    expect(visibleStrings(container)).not.toMatch(JAPANESE);
  });
});

describe("ProductMasterDrawer required fields error (ADR-1020)", () => {
  it("shows field names instead of the REQUIRED_FIELDS_MISSING code when registration is blocked", async () => {
    await i18n.changeLanguage("en");
    vi.mocked(api.post).mockImplementation((async (path: string) => {
      if (path === "/tcg/products") throw Object.assign(new ApiError("REQUIRED_FIELDS_MISSING:name_en", 422, null), { status: 422 });
      return { candidates: [] };
    }) as typeof api.post);
    const { container } = renderDrawer(["PRODUCT_MASTER_UNREGISTERED"]);
    await screen.findByText("Review entry");
    await fillLookups();
    fireEvent.click(screen.getByRole("button", { name: "Register in product master" }));
    await waitFor(() => expect(container.textContent).toContain("Cannot register because required fields are empty: English name"));
    expect(container.textContent).not.toContain("REQUIRED_FIELDS_MISSING");
  });
});
