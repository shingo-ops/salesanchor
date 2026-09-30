import { describe, expect, it } from "vitest";
import type { MessageReaction } from "../../lib/messages";
import { reactorNames, splitReactions } from "./reactionHeart";

const make = (over: Partial<MessageReaction>): MessageReaction => ({
  emoji_name: "❤️",
  emoji_id: null,
  emoji_animated: false,
  count: 1,
  is_mine: false,
  reactors: [],
  ...over,
});

describe("splitReactions", () => {
  it("returns no heart and empty others for undefined", () => {
    expect(splitReactions(undefined)).toEqual({ heart: null, others: [] });
  });

  it("separates the unicode heart from other reactions", () => {
    const heart = make({ count: 2, is_mine: true });
    const thumbs = make({ emoji_name: "👍" });
    expect(splitReactions([thumbs, heart])).toEqual({ heart, others: [thumbs] });
  });

  it("treats a custom emoji named like the heart as a non-heart reaction", () => {
    const custom = make({ emoji_id: "123456789012345678" });
    expect(splitReactions([custom])).toEqual({ heart: null, others: [custom] });
  });
});

describe("reactorNames", () => {
  it("falls back to user_id when display_name is null", () => {
    const r = make({
      reactors: [
        { user_id: "u1", display_name: "Alice" },
        { user_id: "u2", display_name: null },
      ],
    });
    expect(reactorNames(r)).toBe("Alice, u2");
  });
});
