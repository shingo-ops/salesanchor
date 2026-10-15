import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { postProductCorrection, postReviewAck, postReviewAckRevoke, searchProductOptions } from "./reviewActions";

vi.mock("../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));

const item = { extraction_item_id: "item/1", source_message_id: "msg-1", system: { product_uuid: "old-uuid" } };

beforeEach(() => vi.resetAllMocks());

describe("reviewActions", () => {
  it("posts a product correction with the current product as system_value", async () => {
    vi.mocked(api.post).mockResolvedValue({ ok: true, saved: 1 });
    await postProductCorrection(item, "new-uuid");
    expect(api.post).toHaveBeenCalledWith("/tcg/items/item%2F1/corrections", {
      source_message_id: "msg-1",
      fields: [{ field_name: "product_id", system_value: "old-uuid", human_value: "new-uuid" }],
    });
  });

  it("uses an empty system_value when the item has no product yet", async () => {
    vi.mocked(api.post).mockResolvedValue({ ok: true, saved: 1 });
    await postProductCorrection({ ...item, system: {} }, "new-uuid");
    expect(vi.mocked(api.post).mock.calls[0][1]).toEqual({
      source_message_id: "msg-1",
      fields: [{ field_name: "product_id", system_value: "", human_value: "new-uuid" }],
    });
  });

  it("posts review-ack with the given codes", async () => {
    vi.mocked(api.post).mockResolvedValue({ ok: true, saved: 2 });
    await postReviewAck({ ...item, extraction_item_id: "item-1" }, ["a", "b"]);
    expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/review-ack", { source_message_id: "msg-1", codes: ["a", "b"] });
  });

  it("posts review-ack revoke with only the source message id", async () => {
    vi.mocked(api.post).mockResolvedValue({ ok: true, saved: 1 });
    await postReviewAckRevoke({ ...item, extraction_item_id: "item-1" });
    expect(api.post).toHaveBeenCalledWith("/tcg/items/item-1/review-ack/revoke", { source_message_id: "msg-1" });
  });

  it("maps search candidates to name labels with product_uuid values", async () => {
    vi.mocked(api.get).mockResolvedValue({
      candidates: [{ product_id: "PM-00001", product_uuid: "uuid-1", japanese_title: "Alpha", search_keywords: "" }],
    });
    const options = await searchProductOptions("al pha");
    expect(api.get).toHaveBeenCalledWith("/tcg/products/search?query=al+pha");
    expect(options).toEqual([{ value: "uuid-1", label: "Alpha", productId: "PM-00001" }]);
  });
});
