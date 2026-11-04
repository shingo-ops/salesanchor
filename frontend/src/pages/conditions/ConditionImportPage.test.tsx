import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { usePermissions } from "../../hooks/usePermissions";
import i18n from "../../i18n";
import ConditionImportPage from "./ConditionImportPage";

vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }));

const mockPermissions = (granted: string[]) =>
  vi.mocked(usePermissions).mockReturnValue({
    loading: false,
    hasPermission: (key: string) => granted.includes(key),
    hasAny: (...keys: string[]) => keys.some((k) => granted.includes(k)),
  } as unknown as ReturnType<typeof usePermissions>);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
});
afterEach(() => cleanup());

const view = () =>
  render(
    <MemoryRouter>
      <ConditionImportPage />
    </MemoryRouter>,
  );

it("shows the denied message and no import panel with only conditions.view", () => {
  mockPermissions(["conditions.view"]);
  view();
  expect(screen.getByRole("alert").textContent).toBe(i18n.t("productCsv.denied"));
  expect(screen.queryByLabelText(i18n.t("conditionCsv.selectFile"))).toBeNull();
});

it("shows the import panel with create, update and delete", () => {
  mockPermissions(["conditions.view", "conditions.create", "conditions.update", "conditions.delete"]);
  view();
  expect(screen.queryByRole("alert")).toBeNull();
});
