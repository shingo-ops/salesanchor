import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { ButtonLink } from "./ButtonLink";

afterEach(cleanup);

function Location() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

function renderRouterLink(node: React.ReactNode) {
  return render(<MemoryRouter initialEntries={["/start"]}>{node}<Location /></MemoryRouter>);
}

describe("ButtonLink native link contract", () => {
  it("renders an anchor with href metadata and forwards its ref", () => {
    const ref = createRef<HTMLAnchorElement>();
    render(<ButtonLink
      ref={ref}
      href="mailto:support@example.com"
      target="_blank"
      rel="noopener noreferrer"
      download="details.txt"
      variant="secondary"
      size="sm"
      fullWidth
      layoutClassName="comp-btn-layout--ml-2"
    >Contact</ButtonLink>);
    const link = screen.getByRole("link", { name: "Contact" });
    expect(ref.current).toBe(link);
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("href")).toBe("mailto:support@example.com");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.getAttribute("download")).toBe("details.txt");
    expect(link.className).toBe("comp-btn comp-btn--secondary comp-btn--sm comp-btn--full comp-btn-layout--ml-2");
    expect(link.hasAttribute("role")).toBe(false);
  });

  it("renders a Router Link and follows an ordinary primary click", () => {
    const ref = createRef<HTMLAnchorElement>();
    renderRouterLink(<ButtonLink ref={ref} to="/next" variant="ghost">Next</ButtonLink>);
    const link = screen.getByRole("link", { name: "Next" });
    expect(ref.current).toBe(link);
    expect(link.getAttribute("href")).toBe("/next");
    fireEvent.click(link, { button: 0 });
    expect(screen.getByTestId("location").textContent).toBe("/next");
  });

  it.each([
    ["meta", { metaKey: true }],
    ["ctrl", { ctrlKey: true }],
    ["shift", { shiftKey: true }],
    ["alt", { altKey: true }],
  ])("retains Router Link %s-click behavior", (_name, modifier) => {
    renderRouterLink(<ButtonLink to="/next">Next</ButtonLink>);
    fireEvent.click(screen.getByRole("link", { name: "Next" }), { button: 0, ...modifier });
    expect(screen.getByTestId("location").textContent).toBe("/start");
  });

  it("honors caller preventDefault without navigating", () => {
    const clicked = vi.fn((event: React.MouseEvent<HTMLAnchorElement>) => event.preventDefault());
    renderRouterLink(<ButtonLink to="/next" onClick={clicked}>Next</ButtonLink>);
    fireEvent.click(screen.getByRole("link", { name: "Next" }), { button: 0 });
    expect(clicked).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("location").textContent).toBe("/start");
  });

  it("retains caller stopPropagation while navigating", () => {
    const parent = vi.fn();
    renderRouterLink(<div onClick={parent}><ButtonLink to="/next" onClick={(event) => event.stopPropagation()}>Next</ButtonLink></div>);
    fireEvent.click(screen.getByRole("link", { name: "Next" }), { button: 0 });
    expect(parent).not.toHaveBeenCalled();
    expect(screen.getByTestId("location").textContent).toBe("/next");
  });
});

const validAnchor = <ButtonLink href="/invoice" />;
const validRouter = <ButtonLink to="/invoice" />;
// @ts-expect-error href and to are exclusive.
const rejectedBoth = <ButtonLink href="/invoice" to="/invoice" />;
// @ts-expect-error A destination is required.
const rejectedNeither = <ButtonLink />;
// @ts-expect-error Links do not have Button disabled behavior.
const rejectedDisabled = <ButtonLink href="/invoice" disabled />;
// @ts-expect-error Links do not have Button loading behavior.
const rejectedLoading = <ButtonLink href="/invoice" loading />;
// @ts-expect-error Button appearance belongs to Button.css.
const rejectedClassName = <ButtonLink href="/invoice" className="custom" />;
// @ts-expect-error Button appearance belongs to Button.css.
const rejectedStyle = <ButtonLink href="/invoice" style={{ marginLeft: 1 }} />;
// @ts-expect-error tab has button-only pressed semantics.
const rejectedTab = <ButtonLink href="/invoice" variant="tab" />;
void [validAnchor, validRouter, rejectedBoth, rejectedNeither, rejectedDisabled, rejectedLoading,
  rejectedClassName, rejectedStyle, rejectedTab];
