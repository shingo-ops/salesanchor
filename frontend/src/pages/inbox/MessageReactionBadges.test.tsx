import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { MessageReaction } from "../../lib/messages";
import { MessageReactionBadges } from "./MessageReactionBadges";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

afterEach(cleanup);

const heart = (over: Partial<MessageReaction> = {}): MessageReaction => ({
  emoji_name: "\u2764\uFE0F",
  emoji_id: null,
  emoji_animated: false,
  count: 1,
  is_mine: false,
  reactors: [],
  ...over,
});

describe("MessageReactionBadges heart", () => {
  it("shows the filled heart badge, not pressed, when only the customer reacted", () => {
    render(<MessageReactionBadges messageId={1} reactions={[heart()]} onToggleHeart={() => {}} />);
    const btn = screen.getByRole("button", { name: "inbox.addReaction" });
    expect(btn.getAttribute("aria-pressed")).toBe("false");
    expect(btn.className).toContain("comp-icon-toggle--badge");
    expect(btn.className).not.toContain("comp-icon-toggle--pressed");
    expect(btn.textContent).toContain("1");
  });

  it("shows the badge with the pressed (bordered) class when I reacted", () => {
    render(<MessageReactionBadges messageId={1} reactions={[heart({ count: 2, is_mine: true })]} onToggleHeart={() => {}} />);
    const btn = screen.getByRole("button", { name: "inbox.removeReaction" });
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    expect(btn.className).toContain("comp-icon-toggle--badge");
    expect(btn.className).toContain("comp-icon-toggle--pressed");
  });

  it("toggles with the current is_mine value on click", () => {
    const onToggleHeart = vi.fn();
    render(<MessageReactionBadges messageId={7} reactions={[heart({ is_mine: true })]} onToggleHeart={onToggleHeart} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onToggleHeart).toHaveBeenCalledWith(7, true);
  });
});
