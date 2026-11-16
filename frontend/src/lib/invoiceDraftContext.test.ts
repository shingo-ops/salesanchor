// invoice-create-portfolio 便D: 請求書の材料から候補を作る関数（design.md §3-2・§8 K2/K3）
import { describe, expect, it } from "vitest";
import {
  currencyChoices,
  draftContextPath,
  draftContextPathForInvoice,
  effectivePaymentKey,
  formatMoney,
  fxRateFor,
  isCreatableItem,
  isValidQuantity,
  isValidUnitPrice,
  paymentChoicesFor,
  paymentKey,
  paymentRefFromKey,
  resolveCurrency,
  uncomputedReasonKey,
  addressLine,
  type DraftContext,
} from "./invoiceDraftContext";

const CTX: DraftContext = {
  company_id: 4,
  ship_to: null,
  bill_to: null,
  contact_name: null,
  contact_email: null,
  issuer_region: "JP",
  origin_country_code: "JP",
  destination_country_code: "US",
  destination_postal_code: "10001",
  currencies: ["JPY", "USD"],
  fx_rates: [{ currency: "USD", rate: 150.5, fetched_at: "2026-11-15T00:00:00Z" }],
  default_currency: "USD",
  currency: null,
  payment_methods: [
    { id: 3, method_type: "bank", display_name: "Main bank", wise_currency: null },
    { id: 4, method_type: "wise", display_name: "Wise USD", wise_currency: "USD" },
    { id: null, method_type: "paypal", display_name: null, wise_currency: null },
  ],
  tax_rate_percent: null,
  incoterms: "DAP",
};

describe("invoiceDraftContext", () => {
  it("builds the draft-context paths", () => {
    expect(draftContextPath(4, null)).toBe("/invoices/draft-context?company_id=4");
    expect(draftContextPath(4, 5)).toBe("/invoices/draft-context?company_id=4&contact_id=5");
    expect(draftContextPathForInvoice(9)).toBe("/invoices/draft-context?invoice_id=9");
  });

  it("K3: Wise rows are offered only for their own currency", () => {
    expect(paymentChoicesFor(CTX, "USD").map(paymentKey)).toEqual(["bank:3", "wise:4", "paypal:"]);
    expect(paymentChoicesFor(CTX, "JPY").map(paymentKey)).toEqual(["bank:3", "paypal:"]);
    expect(paymentChoicesFor(CTX, "").map(paymentKey)).toEqual(["bank:3", "paypal:"]);
    expect(paymentChoicesFor(null, "USD")).toEqual([]);
  });

  it("K3: a choice that left the list is cleared", () => {
    expect(effectivePaymentKey(paymentChoicesFor(CTX, "USD"), "wise:4")).toBe("wise:4");
    expect(effectivePaymentKey(paymentChoicesFor(CTX, "JPY"), "wise:4")).toBe("");
  });

  it("turns a key back into the reference sent to the server", () => {
    const choices = paymentChoicesFor(CTX, "USD");
    expect(paymentRefFromKey(choices, "bank:3")).toEqual({ method_type: "bank", id: 3 });
    expect(paymentRefFromKey(choices, "paypal:")).toEqual({ method_type: "paypal", id: null });
    expect(paymentRefFromKey(choices, "bank:99")).toBeNull();
  });

  it("K2: currency comes only from the server list", () => {
    expect(currencyChoices(CTX)).toEqual(["JPY", "USD"]);
    expect(resolveCurrency(CTX, "")).toBe("USD");
    expect(resolveCurrency(CTX, "JPY")).toBe("JPY");
    expect(resolveCurrency(CTX, "EUR")).toBe("");
    expect(resolveCurrency({ ...CTX, default_currency: "EUR" }, "")).toBe("");
    expect(resolveCurrency(null, "USD")).toBe("");
  });

  it("finds the exchange rate row", () => {
    expect(fxRateFor(CTX, "USD")?.rate).toBe(150.5);
    expect(fxRateFor(CTX, "JPY")).toBeNull();
  });

  it("formats money and returns null for missing values", () => {
    expect(formatMoney(null, "USD")).toBeNull();
    expect(formatMoney("", "USD")).toBeNull();
    expect(formatMoney("abc", "USD")).toBeNull();
    expect(formatMoney("1234.5", "USD")).not.toBeNull();
  });

  it("checks quantity, price and creatable rows", () => {
    expect(isValidQuantity(1)).toBe(true);
    expect(isValidQuantity(0)).toBe(false);
    expect(isValidQuantity(1.5)).toBe(false);
    expect(isValidUnitPrice(10.25)).toBe(true);
    expect(isValidUnitPrice(10.255)).toBe(false);
    expect(isValidUnitPrice(-1)).toBe(false);
    expect(isCreatableItem({ product_name: "Card", quantity: 2, unit_price: 10 })).toBe(true);
    expect(isCreatableItem({ product_name: " ", quantity: 2, unit_price: 10 })).toBe(false);
    expect(isCreatableItem({ product_name: "Card", quantity: 2, unit_price: 0 })).toBe(false);
  });

  it("maps uncomputed reasons to wording keys", () => {
    expect(uncomputedReasonKey("tax_rate")).toBe("apiError.taxRate");
    expect(uncomputedReasonKey("no_such_reason")).toBe("invoiceForm.notComputed");
  });

  it("joins an address into one line", () => {
    expect(addressLine(null)).toBe("");
    expect(
      addressLine({ company_name: null, billing_display_name: null, label: null, postal_code: "10001", address: "1 Main St", city: "New York", state: "NY", country: "US", phone: null }),
    ).toBe("10001 NY New York 1 Main St US");
  });
});
