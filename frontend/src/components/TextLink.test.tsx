import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TextLink } from "./TextLink";

afterEach(cleanup);

describe("TextLink", () => {
  it("renders a type=button with the root class when onClick is given", () => {
    const click = vi.fn();
    const ref = createRef<HTMLButtonElement | HTMLAnchorElement>();
    render(<TextLink ref={ref} onClick={click}>Forgot</TextLink>);
    const button = screen.getByRole("button", { name: "Forgot" });
    expect(ref.current).toBe(button);
    expect(button.getAttribute("type")).toBe("button");
    expect(button.classList.contains("comp-text-link")).toBe(true);
    expect(button.hasAttribute("to")).toBe(false);
    fireEvent.click(button);
    expect(click).toHaveBeenCalledTimes(1);
  });

  it("renders a router link with the root class when to is given", () => {
    render(<MemoryRouter><TextLink to="/login">Back</TextLink></MemoryRouter>);
    const link = screen.getByRole("link", { name: "Back" });
    expect(link.getAttribute("href")).toBe("/login");
    expect(link.classList.contains("comp-text-link")).toBe(true);
  });
});

// Exactly one of onClick / to; appearance belongs to TextLink.css.
const validButton = <TextLink onClick={() => {}} />;
const validLink = <MemoryRouter><TextLink to="/x" /></MemoryRouter>;
// @ts-expect-error neither onClick nor to.
const rejectedNeither = <TextLink />;
// @ts-expect-error both onClick and to.
const rejectedBoth = <TextLink to="/x" onClick={() => {}} />;
// @ts-expect-error appearance belongs to TextLink.css.
const rejectedClassName = <TextLink onClick={() => {}} className="custom" />;
void [validButton, validLink, rejectedNeither, rejectedBoth, rejectedClassName];
