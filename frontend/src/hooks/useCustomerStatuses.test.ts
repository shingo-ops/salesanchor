/* eslint-disable local/no-japanese-literal */
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CUSTOMER_STATUS_TEST_ROWS } from "../test-utils/customerStatusRows.test.fixture";
import type { CustomerStatusRow } from "../lib/customerStatuses";
import { useCustomerStatuses } from "./useCustomerStatuses";

const state = vi.hoisted(() => ({
  data: undefined as CustomerStatusRow[] | undefined,
  isLoading: false,
  isError: false,
  language: "ja",
}));
vi.mock("../lib/query/apiQuery", () => ({
  useApiQuery: () => ({ data: state.data, isLoading: state.isLoading, isError: state.isError }),
}));
vi.mock("react-i18next", () => ({ useTranslation: () => ({ i18n: { language: state.language } }) }));

const rows = (): CustomerStatusRow[] => CUSTOMER_STATUS_TEST_ROWS.map((r) => ({ ...r }));
const values = (list: { value: string }[]) => list.map((o) => o.value);

beforeEach(() => {
  state.data = rows();
  state.isLoading = false;
  state.isError = false;
  state.language = "ja";
});

describe("useCustomerStatuses", () => {
  it("returns 3 options for create and 4 for edit, in sort_order", () => {
    state.data = rows().reverse();
    const { result } = renderHook(() => useCustomerStatuses());
    expect(values(result.current.options("create"))).toEqual(["active", "inactive", "archived"]);
    expect(values(result.current.options("edit"))).toEqual(["active", "inactive", "archived", "pending_dedup_review"]);
  });

  it("drops a row from create but keeps it in edit when selectable_on_create is FALSE", () => {
    const changed = rows();
    changed[1].selectable_on_create = false;
    state.data = changed;
    const { result } = renderHook(() => useCustomerStatuses());
    expect(values(result.current.options("create"))).toEqual(["active", "archived"]);
    expect(values(result.current.options("edit"))).toHaveLength(4);
    expect(values(result.current.options("edit"))).toContain("inactive");
  });

  it("drops an is_active FALSE row from both, except edit keeps the current value", () => {
    const changed = rows();
    changed[2].is_active = false;
    state.data = changed;
    const { result } = renderHook(() => useCustomerStatuses());
    expect(values(result.current.options("create"))).toEqual(["active", "inactive"]);
    expect(values(result.current.options("edit"))).toEqual(["active", "inactive", "pending_dedup_review"]);
    expect(values(result.current.options("edit", "archived"))).toEqual(["active", "inactive", "archived", "pending_dedup_review"]);
  });

  it("uses name_en when the language is en", () => {
    state.language = "en";
    const { result } = renderHook(() => useCustomerStatuses());
    expect(result.current.options("edit")[0].label).toBe("Active");
    expect(result.current.nameOf("pending_dedup_review")).toBe("Pending duplicate check");
  });

  it("uses name_ja when the language starts with ja", () => {
    state.language = "ja-JP";
    const { result } = renderHook(() => useCustomerStatuses());
    expect(result.current.nameOf("active")).toBe("有効");
  });

  it("returns empty options and the code itself while loading or on error", () => {
    state.data = undefined;
    state.isLoading = true;
    const { result } = renderHook(() => useCustomerStatuses());
    expect(result.current.options("create")).toEqual([]);
    expect(result.current.options("edit", "active")).toEqual([]);
    expect(result.current.nameOf("active")).toBe("active");
    expect(result.current.isLoading).toBe(true);
    state.isLoading = false;
    state.isError = true;
    const failed = renderHook(() => useCustomerStatuses());
    expect(failed.result.current.isError).toBe(true);
    expect(failed.result.current.options("edit")).toEqual([]);
  });
});
