import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HoverCard, HoverCardHost } from "./HoverCard";

function setClip(el: HTMLElement, scrollWidth: number, clientWidth: number) {
  Object.defineProperty(el, "scrollWidth", { configurable: true, value: scrollWidth });
  Object.defineProperty(el, "clientWidth", { configurable: true, value: clientWidth });
}

function setup(subtitle: string | null, clipped: boolean) {
  render(
    <>
      <HoverCard title="Long product name" subtitle={subtitle}>
        <div data-testid="clip" data-hover-card-clip>
          Long product name
        </div>
      </HoverCard>
      <HoverCardHost />
    </>,
  );
  const clip = screen.getByTestId("clip");
  setClip(clip, clipped ? 300 : 100, 100);
  return clip.closest(".comp-hover-card-trigger") as HTMLElement;
}

describe("HoverCard", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows title and subtitle 150ms after hover when clipped", () => {
    const trigger = setup("Long name", true);
    fireEvent.mouseEnter(trigger);
    expect(screen.queryByRole("tooltip")).toBeNull();
    act(() => {
      vi.advanceTimersByTime(150);
    });
    const tip = screen.getByRole("tooltip");
    expect(tip.textContent).toContain("Long product name");
    expect(tip.textContent).toContain("Long name");
    fireEvent.mouseLeave(trigger);
  });

  it("does not show when not clipped", () => {
    const trigger = setup("Long name", false);
    fireEvent.mouseEnter(trigger);
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("closes on mouseleave", () => {
    const trigger = setup("Long name", true);
    fireEvent.mouseEnter(trigger);
    act(() => {
      vi.advanceTimersByTime(150);
    });
    expect(screen.getByRole("tooltip")).toBeTruthy();
    fireEvent.mouseLeave(trigger);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("has no second-line element when subtitle is empty", () => {
    const trigger = setup(null, true);
    fireEvent.mouseEnter(trigger);
    act(() => {
      vi.advanceTimersByTime(150);
    });
    const tip = screen.getByRole("tooltip");
    expect(tip.querySelector(".comp-hover-card__title")).not.toBeNull();
    expect(tip.querySelector(".comp-hover-card__subtitle")).toBeNull();
    fireEvent.mouseLeave(trigger);
  });

  it("closes when the trigger is removed while open", () => {
    const { rerender } = render(
      <>
        <HoverCard title="Long product name" subtitle="Long name">
          <div data-testid="clip" data-hover-card-clip>
            Long product name
          </div>
        </HoverCard>
        <HoverCardHost />
      </>,
    );
    const clip = screen.getByTestId("clip");
    setClip(clip, 300, 100);
    fireEvent.mouseEnter(clip.closest(".comp-hover-card-trigger") as HTMLElement);
    act(() => {
      vi.advanceTimersByTime(150);
    });
    expect(screen.getByRole("tooltip")).toBeTruthy();
    rerender(
      <>
        <HoverCardHost />
      </>,
    );
    expect(screen.queryByRole("tooltip")).toBeNull();
  });
});
