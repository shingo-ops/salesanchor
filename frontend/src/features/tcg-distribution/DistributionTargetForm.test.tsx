import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { DistributionTargetForm } from "./DistributionTargetForm";

vi.mock("./distributionApi", () => ({
  createTarget: vi.fn(),
  updateTarget: vi.fn(),
  verifySpreadsheetAccess: vi.fn(),
}));

const IDS = ["dist-name", "dist-spreadsheet-id", "dist-sheet-name"];
const input = (id: string) => document.getElementById(id) as HTMLInputElement;

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("DistributionTargetForm text inputs (design.md §AY-2x)", () => {
  it("renders the 3 text inputs with the TextFieldControl class and no invalid class", () => {
    render(<DistributionTargetForm target={null} onClose={vi.fn()} onSaved={vi.fn()} />);
    for (const id of IDS) {
      expect(input(id).classList.contains("comp-field__input")).toBe(true);
      expect(input(id).classList.contains("comp-field__input--invalid")).toBe(false);
      expect(input(id).classList.contains("dist-input")).toBe(false);
    }
  });

  it("marks all 3 inputs invalid when saving empty, and clears the one that is typed into", () => {
    render(<DistributionTargetForm target={null} onClose={vi.fn()} onSaved={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    for (const id of IDS) {
      expect(input(id).classList.contains("comp-field__input--invalid")).toBe(true);
      expect(input(id).hasAttribute("invalid")).toBe(false);
    }
    fireEvent.change(input("dist-name"), { target: { value: "Client" } });
    expect(input("dist-name").classList.contains("comp-field__input--invalid")).toBe(false);
    expect(input("dist-spreadsheet-id").classList.contains("comp-field__input--invalid")).toBe(true);
    expect(input("dist-sheet-name").classList.contains("comp-field__input--invalid")).toBe(true);
  });
});
