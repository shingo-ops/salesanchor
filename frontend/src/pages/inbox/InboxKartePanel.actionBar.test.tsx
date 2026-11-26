/**
 * ADR-1090 §4-3: カルテの下の帯（ActionBar）の出し分けの試験。
 * 帯はすべての段階で出す。大きいボタンは段階で決め、メニューのリンクは「登録が済んでいるか」だけで決める。
 * 試験の題は英語（lint の決まり local/no-japanese-literal）。
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ja from "../../locales/ja.json";

const lookup = (key: string): string => {
  const v = key.split(".").reduce<unknown>(
    (o, k) => (o && typeof o === "object" ? (o as Record<string, unknown>)[k] : undefined),
    ja,
  );
  return typeof v === "string" ? v : key;
};

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: lookup, i18n: { language: "ja" } }),
}));
vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({ loading: false, hasPermission: () => true }),
}));
vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(() => Promise.resolve([])), post: vi.fn(() => Promise.resolve({})) },
}));

import { ActionBar } from "./InboxKartePanel";

const CONVERT = lookup("inbox.actionConvert");
const INVOICE = lookup("inbox.actionCreateInvoice");
const REGISTER = lookup("registration.generateLink");
const ADD_ADDRESS = lookup("registration.generateAddressLink");
const CHANGE_BILLING = lookup("registration.generateChangeBillingLink");

function renderBar(status: string, registrationCompleted: boolean) {
  render(
    <ActionBar
      status={status}
      registrationCompleted={registrationCompleted}
      leadId={1}
      onConvertLead={vi.fn()}
      onCreateInvoice={vi.fn()}
      canMerge={true}
      onMerge={vi.fn()}
    />,
  );
}

describe("Karte action bar (ADR-1090)", () => {
  afterEach(cleanup);

  it.each([
    ["negotiating", INVOICE],
    ["follow_up_short", INVOICE],
    ["follow_up_long", INVOICE],
    ["existing_customer", INVOICE],
    ["lead", CONVERT],
  ])("status %s shows the primary button", (status, label) => {
    renderBar(status, false);
    expect(screen.getByTestId("karte-action-bar")).toBeTruthy();
    expect(screen.getByTestId("karte-action-primary").textContent).toBe(label);
  });

  it.each(["lost", "out_of_scope"])("status %s shows the bar without a primary button", (status) => {
    renderBar(status, false);
    expect(screen.getByTestId("karte-action-bar")).toBeTruthy();
    expect(screen.queryByTestId("karte-action-primary")).toBeNull();
    expect(screen.getByTestId("karte-action-overflow")).toBeTruthy();
  });

  it.each(["lead", "negotiating", "follow_up_short", "existing_customer", "lost"])(
    "status %s, not registered: menu has only the registration link",
    (status) => {
      renderBar(status, false);
      fireEvent.click(screen.getByTestId("karte-action-overflow"));
      expect(screen.getByText(REGISTER)).toBeTruthy();
      expect(screen.queryByText(ADD_ADDRESS)).toBeNull();
      expect(screen.queryByText(CHANGE_BILLING)).toBeNull();
    },
  );

  it.each(["lead", "negotiating", "follow_up_long", "existing_customer", "lost"])(
    "status %s, registered: menu has add-address and change-billing, no registration link",
    (status) => {
      renderBar(status, true);
      fireEvent.click(screen.getByTestId("karte-action-overflow"));
      expect(screen.queryByText(REGISTER)).toBeNull();
      expect(screen.getByText(ADD_ADDRESS)).toBeTruthy();
      expect(screen.getByText(CHANGE_BILLING)).toBeTruthy();
    },
  );
});
