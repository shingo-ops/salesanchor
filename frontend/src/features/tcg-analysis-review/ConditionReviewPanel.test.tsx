import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { api, ApiError } from "../../lib/api";
import { ConditionReviewPanel } from "./ConditionReviewPanel";
import type { AnalysisReviewItem } from "./ItemComparison";
import { hasNeedsReview } from "./reviewIssues";

vi.mock("../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error { status: number; constructor(message: string, status: number) { super(message); this.status=status; } } }));
const item: AnalysisReviewItem = { extraction_item_id: "item", source_message_id: "source", provider: "Test", raw_text: "",
  gemini: { name: "Original", state: "Empty", memo: "" }, system: { condition: "Empty box" },
  condition_review: { condition_id: "empty", review_version: "a".repeat(64), needs_review: true,
    review_reasons: "empty_box", confirmed: false, classification: "positive" } };
const options = [{ id: "empty", code: "CN0011", canonical: "Empty box" }, { id: "normal", code: "CN0003", canonical: "Sealed box" }];

describe("ConditionReviewPanel", () => {
  beforeEach(async () => { vi.resetAllMocks(); await i18n.changeLanguage("en"); vi.mocked(api.get).mockResolvedValue(options); });
  it("confirms without enabling other manual fields and refreshes the list", async () => {
    const refresh=vi.fn().mockResolvedValue(undefined);
    vi.mocked(api.post).mockResolvedValue({ ok:true, saved:1,condition_review:{needs_review:false} });
    render(<ConditionReviewPanel item={item} onRefresh={refresh} />);
    await waitFor(() => expect((screen.getByRole("button",{name:"Confirm empty box"}) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button",{name:"Confirm empty box"}));
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(api.post).toHaveBeenCalledWith("/tcg/items/item/corrections",expect.objectContaining({source_message_id:"source",
      condition_review:expect.objectContaining({decision:"confirm",condition_id:"empty",expected_review_version:"a".repeat(64)})}));
    expect(screen.queryByRole("textbox")).toBeNull();
  });
  it("keeps other unresolved reasons visibly pending", async () => {
    vi.mocked(api.post).mockResolvedValue({ok:true,saved:1,condition_review:{needs_review:true}});
    render(<ConditionReviewPanel item={item} onRefresh={vi.fn().mockResolvedValue(undefined)} />);
    await waitFor(() => expect((screen.getByRole("button",{name:"Confirm empty box"}) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button",{name:"Confirm empty box"}));
    expect(await screen.findByText("Condition confirmed. Other issues still prevent delivery.")).toBeTruthy();
  });
  it("requires a selected correction for ambiguous input", async () => {
    vi.mocked(api.post).mockResolvedValue({ok:true,saved:1,condition_review:{needs_review:false}});
    render(<ConditionReviewPanel item={{...item,condition_review:{...item.condition_review!,classification:"ambiguous"}}} onRefresh={vi.fn().mockResolvedValue(undefined)} />);
    expect((screen.getByRole("button",{name:"Confirm empty box"}) as HTMLButtonElement).disabled).toBe(true);
    await screen.findByRole("option",{name:"Sealed box"});
    fireEvent.change(screen.getByRole("combobox"),{target:{value:"normal"}});
    fireEvent.click(screen.getByRole("button",{name:"Save selected condition"}));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith(expect.anything(),expect.objectContaining({condition_review:expect.objectContaining({decision:"correct",condition_id:"normal"})})));
  });
  it("blocks a double click while saving", async () => {
    vi.mocked(api.post).mockReturnValue(new Promise(() => {}));
    render(<ConditionReviewPanel item={item} onRefresh={vi.fn()} />);
    const button=screen.getByRole("button",{name:"Confirm empty box"});
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(button);fireEvent.click(button);
    expect(api.post).toHaveBeenCalledOnce();
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });
  it("reloads after 409 and asks for another confirmation", async () => {
    const refresh=vi.fn().mockResolvedValue(undefined);
    vi.mocked(api.post).mockRejectedValue(new ApiError("stale",409,null));
    render(<ConditionReviewPanel item={item} onRefresh={refresh} />);
    await waitFor(() => expect((screen.getByRole("button",{name:"Confirm empty box"}) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button",{name:"Confirm empty box"}));
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(api.post).toHaveBeenCalledOnce();
  });
  it("marks empty-only review rows as needing review", () => { expect(hasNeedsReview(["CONDITION_REVIEW_REQUIRED"])).toBe(true); });
});
