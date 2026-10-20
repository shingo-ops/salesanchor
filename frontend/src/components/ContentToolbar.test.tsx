import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ContentToolbar, ContentToolbarRange } from "./ContentToolbar";

describe("ContentToolbar", () => {
  it("without bottom slots keeps the legacy single-row DOM", () => {
    const { container } = render(<ContentToolbar left={<span>L</span>} right={<span>R</span>} />);
    expect(container.innerHTML).toBe(
      '<div class="content-toolbar"><div class="content-toolbar__left"><span>L</span></div><div class="content-toolbar__right"><span>R</span></div></div>',
    );
  });

  it("bottomLeft renders the two-row DOM", () => {
    const { container } = render(
      <ContentToolbar left={<span>L</span>} bottomLeft={<span>BL</span>} bottomRight={<span>BR</span>} />,
    );
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toBe("content-toolbar content-toolbar--two-rows");
    const rows = root.querySelectorAll(":scope > .content-toolbar__row");
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toBe("L");
    expect(rows[1].textContent).toBe("BLBR");
  });

  it("bottomRight alone also renders two rows", () => {
    const { container } = render(<ContentToolbar bottomRight={<span>BR</span>} />);
    expect(container.querySelectorAll(".content-toolbar__row").length).toBe(2);
  });
});

describe("ContentToolbarRange", () => {
  it("exposes testids, values and onChange", () => {
    const onMin = vi.fn();
    const onMax = vi.fn();
    render(
      <ContentToolbarRange
        minValue="1" maxValue="9" onMinChange={onMin} onMaxChange={onMax}
        minPlaceholder="a" maxPlaceholder="b" minAriaLabel="amin" maxAriaLabel="amax"
        testIdPrefix="x-range"
      />,
    );
    const min = screen.getByTestId("x-range-min") as HTMLInputElement;
    const max = screen.getByTestId("x-range-max") as HTMLInputElement;
    expect(min.value).toBe("1");
    expect(max.value).toBe("9");
    fireEvent.change(min, { target: { value: "5" } });
    fireEvent.change(max, { target: { value: "50" } });
    expect(onMin).toHaveBeenCalledWith("5");
    expect(onMax).toHaveBeenCalledWith("50");
  });
});
