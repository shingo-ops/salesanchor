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
    expect(container.querySelector(`.comp-badge--${conditionBadgeVariant(cond)}`)?.textContent).toBe(cond);
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
