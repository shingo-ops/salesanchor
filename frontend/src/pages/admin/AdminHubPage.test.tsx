import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useIsMobile } from "../../hooks/useIsMobile";
import i18n from "../../i18n";
import AdminHubPage from "./AdminHubPage";

vi.mock("../../hooks/useIsMobile", () => ({ useIsMobile: vi.fn() }));

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
});
afterEach(() => cleanup());

const view = () => render(<MemoryRouter><AdminHubPage /></MemoryRouter>);

it("hides the bottom tab bar on desktop", () => {
  vi.mocked(useIsMobile).mockReturnValue(false);
  view();
  expect(screen.queryByRole("navigation")).toBeNull();
  expect(document.querySelector(".admin-hub-tabs")).toBeNull();
});

it("shows the bottom tab bar with all 6 tabs on mobile", () => {
  vi.mocked(useIsMobile).mockReturnValue(true);
  view();
  expect(screen.getByRole("navigation")).toBeTruthy();
  expect(document.querySelectorAll(".admin-hub-tab")).toHaveLength(6);
});
