import { describe, expect, it } from "vitest";
import { buildReactionCreatePath, buildReactionDeletePath } from "./reactionPaths";

describe("buildReactionCreatePath", () => {
  it("uses the internal message id in the path", () => {
    expect(buildReactionCreatePath(12, 345)).toBe("/leads/12/messages/345/reactions");
  });
});

describe("buildReactionDeletePath", () => {
  it("encodes a unicode emoji in the path and adds no query", () => {
    expect(buildReactionDeletePath(12, 345, "👍")).toBe(
      "/leads/12/messages/345/reactions/%F0%9F%91%8D",
    );
  });

  it("sends emoji_name in the path and emoji_id as a query for custom emoji", () => {
    expect(buildReactionDeletePath(12, 345, "party", "123456789012345678")).toBe(
      "/leads/12/messages/345/reactions/party?emoji_id=123456789012345678",
    );
  });
});
