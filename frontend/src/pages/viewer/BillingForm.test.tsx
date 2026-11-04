import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "i18next";
import "./i18n";
import { ViewerApiError } from "./api";
import ViewerApp from "./ViewerApp";

const apiMock = vi.hoisted(() => ({
  openBillingForm: vi.fn(),
  submitBillingForm: vi.fn(),
}));
vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, ...apiMock };
});

const k = (key: string): string => i18n.t(key);
const EMPTY = {
  party_type: null,
  bill_to_name: "",
  contact_name: "",
  postal_code: "",
  address: "",
  phone: "",
  invoice_email: "",
};

const typeInto = (label: string, value: string) => {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const input = screen.getByLabelText(new RegExp(`^${escaped}\\*?$`)) as HTMLInputElement;
  fireEvent.change(input, { target: { value } });
};

beforeEach(() => {
  apiMock.openBillingForm.mockReset();
  apiMock.submitBillingForm.mockReset();
  window.localStorage.clear();
  window.history.replaceState(null, "", "/viewer/#billing=KEY123");
});
afterEach(() => cleanup());

describe("BillingFormView via #billing=", () => {
  it("opens with the key from the hash, removes it from the URL and fills the previous values", async () => {
    apiMock.openBillingForm.mockResolvedValue({
      ...EMPTY,
      party_type: "individual",
      bill_to_name: "Test Person",
      postal_code: "1000001",
    });
    render(<ViewerApp />);
    await screen.findByTestId("viewer-billing-form");
    expect(apiMock.openBillingForm).toHaveBeenCalledWith("KEY123");
    expect(window.location.hash).toBe("");
    expect((screen.getByLabelText(new RegExp(`^${k("viewer.billing.billToName")}\\*?$`)) as HTMLInputElement).value).toBe(
      "Test Person",
    );
  });

  it("shows the contact field only for a company", async () => {
    apiMock.openBillingForm.mockResolvedValue(EMPTY);
    render(<ViewerApp />);
    await screen.findByTestId("viewer-billing-form");
    expect(screen.queryByTestId("viewer-billing-contact")).toBeNull();
    fireEvent.click(screen.getByTestId("viewer-billing-company"));
    expect(screen.getByTestId("viewer-billing-contact")).toBeTruthy();
    fireEvent.click(screen.getByTestId("viewer-billing-individual"));
    expect(screen.queryByTestId("viewer-billing-contact")).toBeNull();
  });

  it("shows only the invalid notice for an invalid key", async () => {
    apiMock.openBillingForm.mockRejectedValue(new ViewerApiError(400, "viewer_billing_form_invalid"));
    render(<ViewerApp />);
    expect(await screen.findByTestId("viewer-billing-invalid")).toBeTruthy();
    expect(screen.queryByTestId("viewer-billing-form")).toBeNull();
  });

  it("submits the values and shows the done notice", async () => {
    apiMock.openBillingForm.mockResolvedValue(EMPTY);
    apiMock.submitBillingForm.mockResolvedValue({ status: "saved" });
    render(<ViewerApp />);
    await screen.findByTestId("viewer-billing-form");
    fireEvent.click(screen.getByTestId("viewer-billing-company"));
    typeInto(k("viewer.billing.billToName"), "Test Corp");
    typeInto(k("viewer.billing.contactName"), "Contact Test");
    typeInto(k("viewer.billing.postalCode"), "100-0001");
    typeInto(k("viewer.billing.address"), "Test Address 1-1");
    typeInto(k("viewer.billing.phone"), "03-0000-0000");
    fireEvent.submit(screen.getByTestId("viewer-billing-form"));
    await screen.findByTestId("viewer-billing-done");
    expect(apiMock.submitBillingForm).toHaveBeenCalledWith(
      "KEY123",
      expect.objectContaining({ party_type: "company", bill_to_name: "Test Corp", contact_name: "Contact Test" }),
    );
  });

  it("keeps the form and shows an error when the server says 422", async () => {
    apiMock.openBillingForm.mockResolvedValue({ ...EMPTY, party_type: "individual" });
    apiMock.submitBillingForm.mockRejectedValue(new ViewerApiError(422, "viewer_billing_invalid:phone"));
    render(<ViewerApp />);
    await screen.findByTestId("viewer-billing-form");
    typeInto(k("viewer.billing.billToName"), "Test Person");
    typeInto(k("viewer.billing.postalCode"), "1000001");
    typeInto(k("viewer.billing.address"), "Test Address");
    typeInto(k("viewer.billing.phone"), "12");
    fireEvent.submit(screen.getByTestId("viewer-billing-form"));
    await waitFor(() => expect(screen.getByTestId("viewer-billing-error").textContent).toBe(k("viewer.billing.invalidInput")));
    expect(screen.getByTestId("viewer-billing-form")).toBeTruthy();
  });

  it("requires choosing company or individual before sending", async () => {
    apiMock.openBillingForm.mockResolvedValue(EMPTY);
    render(<ViewerApp />);
    await screen.findByTestId("viewer-billing-form");
    fireEvent.submit(screen.getByTestId("viewer-billing-form"));
    expect((await screen.findByTestId("viewer-billing-error")).textContent).toBe(k("viewer.billing.partyRequired"));
    expect(apiMock.submitBillingForm).not.toHaveBeenCalled();
  });
});
