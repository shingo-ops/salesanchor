import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { conditionBadgeVariant } from "../../features/inventory/conditionBadge";
import ja from "../../locales/viewer/ja.json";
import { buildViewerColumns, formatPostedAt, formatPrice } from "./viewerColumns";
import type { ViewerTableRow } from "./types";

// 画面の文字は viewer 辞書から引く（キーを文字で直書きしない）
const dict = ja as unknown as { viewer: { offerType: Record<string, string> } };
const t = ((k: string) => k.split(".").reduce<unknown>((o, p) => (o as Record<string, unknown>)[p], ja) as string) as never;

const base: ViewerTableRow = {
  idx: 0, posted_at: "2026-10-16 09:30:00", mark: "M1", japanese_title: "Name", english_title: "En", condition: "sealed",
  unit_price: "1200", quantity: "3", note_ja: "", status: "In Stock", release_date: "", series: "S", provider: "P",
  search_keywords: "", ship_ja: "", offer_type: "in_stock",
};
const cols = buildViewerColumns({ t });
const cell = (key: string, row: ViewerTableRow) => render(<div>{cols.find((c) => c.key === key)!.renderCell!(row, "0")}</div>);

afterEach(() => cleanup());

describe("viewer offer type cell (4 cases)", () => {
  it("in stock: blue text class, no badge", () => {
    const { container } = cell("offer_type", base);
    expect(container.textContent).toBe(dict.viewer.offerType.in_stock);
    expect(container.querySelector(".inventory-cell__offer--instock")).not.toBeNull();
    expect(container.querySelector(".comp-badge")).toBeNull();
  });
  it("pre-order: orange text class, no badge", () => {
    const { container } = cell("offer_type", { ...base, status: "Pre-order", offer_type: "pre_order" });
    const el = container.querySelector(".inventory-cell__offer--preorder");
    expect(el).not.toBeNull();
    expect(el?.textContent).toBe(dict.viewer.offerType.pre_order);
    expect(container.querySelector(".comp-badge")).toBeNull();
    expect(container.querySelector(".badge-negotiating")).toBeNull();
  });
  it("other status: status text", () => {
    const { container } = cell("offer_type", { ...base, status: "Sold", offer_type: null });
    expect(container.textContent).toBe("Sold");
  });
  it("empty status: dash", () => {
    const { container } = cell("offer_type", { ...base, status: "", offer_type: null });
    expect(container.textContent).toBe("-");
  });
});

describe("viewer condition cell", () => {
  it.each(["Sealed box", "Damaged sealed box", "No shrink box", "Opened box", "Case", "Bulk"])("uses conditionBadgeVariant for %s", (cond) => {
    const { container } = cell("condition", { ...base, condition: cond });
    expect(container.querySelector(`.inventory-cell__condition--${conditionBadgeVariant(cond)}`)?.textContent).toBe(cond);
    expect(container.querySelector(".comp-badge")).toBeNull();
  });
});

describe("viewer value formatting", () => {
  it("formats price and posted_at", () => {
    expect(formatPrice("1200")).toBe("¥1,200");
    expect(formatPrice("")).toBe("");
    expect(formatPostedAt("2026-10-16 09:30:00")).toBe("10-16 09:30");
    expect(formatPostedAt("")).toBe("");
  });
});

describe("viewer block frames (ADR-1014 rev 2026-10-19 (3))", () => {
  it("frames the cheapest price in the price cell and the most-stock quantity in the quantity cell", () => {
    const price = cell("unit_price", { ...base, badge_cheapest: true } as never);
    const p = price.container.querySelector('[data-testid="block-frame-cheapest"]');
    expect(p?.classList.contains("inventory-cell__value--cheapest")).toBe(true);
    expect(p?.getAttribute("title")).toBe(ja.viewer.badge.cheapest);
    expect(price.container.querySelector('[data-testid="block-frame-most-stock"]')).toBeNull();
    cleanup();
    const qty = cell("quantity", { ...base, badge_most_stock: true } as never);
    const q = qty.container.querySelector('[data-testid="block-frame-most-stock"]');
    expect(q?.classList.contains("inventory-cell__value--most-stock")).toBe(true);
    expect(q?.getAttribute("title")).toBe(ja.viewer.badge.mostStock);
    expect(qty.container.querySelector('[data-testid="block-frame-cheapest"]')).toBeNull();
  });
  it("keeps the value in the same container without a frame or title when the flags are false or absent", () => {
    const a = cell("unit_price", { ...base, badge_cheapest: false, badge_most_stock: false } as never);
    const ap = a.container.querySelector(".inventory-cell__value");
    expect(ap).not.toBeNull();
    expect(ap?.className).toBe("inventory-cell__value");
    expect(ap?.hasAttribute("title")).toBe(false);
    cleanup();
    const b = cell("quantity", base);
    const bq = b.container.querySelector(".inventory-cell__value");
    expect(bq).not.toBeNull();
    expect(bq?.className).toBe("inventory-cell__value");
    expect(bq?.hasAttribute("title")).toBe(false);
  });
  it("shows no badge in the price and quantity cells", () => {
    const a = cell("unit_price", { ...base, badge_cheapest: true } as never);
    expect(a.container.querySelector(".comp-badge")).toBeNull();
    cleanup();
    const b = cell("quantity", { ...base, badge_most_stock: true } as never);
    expect(b.container.querySelector(".comp-badge")).toBeNull();
  });
});

describe("viewer title ellipsis and wrapped note/ship (ADR-1014 rev 2026-10-20)", () => {
  it("wraps both title lines in a HoverCard trigger and drops the title attribute", () => {
    const { container } = cell("name", { ...base, japanese_title: "Long Name", english_title: "Long English" });
    const top = container.querySelector(".inventory-cell__title");
    const sub = container.querySelector(".inventory-cell__sub");
    expect(top?.classList.contains("inventory-cell__clip")).toBe(true);
    expect(top?.hasAttribute("title")).toBe(false);
    expect(top?.hasAttribute("data-hover-card-clip")).toBe(true);
    expect(top?.closest(".comp-hover-card-trigger")).not.toBeNull();
    expect(sub?.classList.contains("inventory-cell__clip")).toBe(true);
    expect(sub?.hasAttribute("title")).toBe(false);
    expect(sub?.hasAttribute("data-hover-card-clip")).toBe(true);
    expect(sub?.closest(".comp-hover-card-trigger")).not.toBeNull();
  });
  it("omits the sub line without english_title", () => {
    const { container } = cell("name", { ...base, english_title: "" });
    expect(container.querySelector(".inventory-cell__sub")).toBeNull();
  });
  it.each(["note", "ship"])("wraps %s with the wrap class (not nowrap)", (key) => {
    const { container } = cell(key, { ...base, note_ja: "memo", ship_ja: "ship" });
    expect(container.querySelector(".inventory-cell__wrap")).not.toBeNull();
    expect(container.querySelector(".inventory-cell__nowrap")).toBeNull();
  });
  it.each(["note", "ship"])("keeps the %s wrap element empty when the value is empty", (key) => {
    const { container } = cell(key, { ...base, note_ja: "", ship_ja: "" });
    const el = container.querySelector(".inventory-cell__wrap");
    expect(el).not.toBeNull();
    expect(el!.matches(":empty")).toBe(true);
  });
});
