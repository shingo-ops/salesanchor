import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { HeaderButton } from "./HeaderButton";

afterEach(cleanup);

describe("HeaderButton contract", () => {
  it.each(["primary", "secondary", "ghost"] as const)(
    "delegates the %s text variant to Button with the existing public props",
    (variant) => {
      const click = vi.fn();
      const { rerender } = render(
        <HeaderButton
          variant={variant}
          onClick={click}
          aria-label="Header action"
          data-tooltip="Help"
          data-testid="header-action"
        >Action</HeaderButton>,
      );
      const button = screen.getByTestId("header-action") as HTMLButtonElement;
      expect(button.tagName).toBe("BUTTON");
      expect(button.type).toBe("button");
      expect(button.className).toBe(`comp-btn comp-btn--${variant}`);
      expect(button.getAttribute("aria-label")).toBe("Header action");
      expect(button.getAttribute("data-tooltip")).toBe("Help");
      fireEvent.click(button);
      expect(click).toHaveBeenCalledTimes(1);

      rerender(<HeaderButton variant={variant} onClick={click} disabled>Action</HeaderButton>);
      expect(button.disabled).toBe(true);
      fireEvent.click(button);
      expect(click).toHaveBeenCalledTimes(1);
    },
  );

  it("keeps the icon variant on its native icon-btn implementation", () => {
    const click = vi.fn();
    const { rerender } = render(
      <HeaderButton
        variant="icon"
        aria-label="Settings"
        data-tooltip="Open settings"
        data-testid="settings"
        onClick={click}
      ><span aria-hidden="true">x</span></HeaderButton>,
    );
    const button = screen.getByTestId("settings") as HTMLButtonElement;
    expect(button.tagName).toBe("BUTTON");
    expect(button.type).toBe("button");
    expect(button.className).toBe("icon-btn");
    expect(button.getAttribute("aria-label")).toBe("Settings");
    expect(button.getAttribute("data-tooltip")).toBe("Open settings");
    fireEvent.click(button);
    expect(click).toHaveBeenCalledTimes(1);

    rerender(<HeaderButton variant="icon" aria-label="Settings" disabled onClick={click}>x</HeaderButton>);
    expect(button.disabled).toBe(true);
    fireEvent.click(button);
    expect(click).toHaveBeenCalledTimes(1);
  });
});
