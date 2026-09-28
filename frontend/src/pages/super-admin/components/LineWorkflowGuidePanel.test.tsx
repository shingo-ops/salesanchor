import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../../i18n";
import { LineWorkflowGuidePanel } from "./LineWorkflowGuidePanel";

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}</output>;
}

function renderPanel(onNavigate = vi.fn()) {
  render(
    <MemoryRouter initialEntries={["/super-admin/analysis-rules?section=line-workflow-guide"]}>
      <LineWorkflowGuidePanel onNavigate={onNavigate} />
      <LocationProbe />
    </MemoryRouter>,
  );
  return onNavigate;
}

describe("LineWorkflowGuidePanel", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("ja");
  });

  it("renders seven structured steps and matching table-of-contents anchors", () => {
    renderPanel();

    expect(screen.getAllByTestId("line-workflow-step")).toHaveLength(7);
    expect(screen.getAllByRole("link")).toHaveLength(7);
    expect(screen.getByRole("link", {
      name: i18n.t("analysisRules.lineWorkflowGuide.steps.step1.title"),
    }).getAttribute("href")).toBe("#line-workflow-step-1");
    expect(screen.getByRole("heading", {
      name: `${i18n.t("analysisRules.lineWorkflowGuide.stepLabel", { step: 1 })}: ${i18n.t("analysisRules.lineWorkflowGuide.steps.step1.title")}`,
    }).getAttribute("tabindex")).toBe("-1");
    expect(screen.getByRole("link", {
      name: i18n.t("analysisRules.lineWorkflowGuide.steps.step7.title"),
    }).getAttribute("href")).toBe("#line-workflow-step-7");
    expect(screen.getByText(i18n.t("analysisRules.lineWorkflowGuide.exceptions.item4"))).toBeTruthy();
  });

  it("uses the hub callback for internal destinations and the existing distribution route", () => {
    const onNavigate = renderPanel();

    fireEvent.click(screen.getAllByRole("button", { name: i18n.t("analysisRules.lineWorkflowGuide.actions.openImport") })[0]);
    expect(onNavigate).toHaveBeenCalledWith("import");

    fireEvent.click(screen.getByRole("button", { name: i18n.t("analysisRules.lineWorkflowGuide.actions.openDistribution") }));
    expect(screen.getByTestId("location").textContent).toBe("/super-admin/tcg-distribution");
  });

  it("switches every visible guide label to English", async () => {
    renderPanel();

    await act(async () => {
      await i18n.changeLanguage("en");
    });

    expect(screen.getByRole("heading", { name: "LINE analysis workflow guide" })).toBeTruthy();
    expect(screen.getAllByTestId("line-workflow-step")).toHaveLength(7);
    expect(screen.getByRole("link", { name: "Import LINE records" }).getAttribute("href")).toBe(
      "#line-workflow-step-1",
    );
    expect(screen.getByRole("button", { name: "Open distribution" })).toBeTruthy();
  });
});
