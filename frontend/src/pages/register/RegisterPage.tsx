/**
 * Customer Registration Page (public, no auth). ADR-SA-03 + ADR-126 v2.
 *
 * URL: /register?token=...
 * Displays in English by default (ADR-126 Section 4) with language toggle.
 * Section 1: Billing Address Registration
 * Section 2: Shipping Address Registration (hidden when "Ship to the same address.")
 * Contact person section at bottom.
 */

import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { COUNTRIES } from "../../constants/countries";
import { CountryCombobox } from "./CountryCombobox";

interface TokenInfo {
  valid: boolean;
  company_name: string | null;
  lead_id: number | null;
  token_type: string | null;
}

interface AddressForm {
  address_type: string;
  name: string;
  email: string;
  telephone: string;
  telephone_dial: string;
  telephone_number: string;
  tax_id: string;
  address_line_1: string;
  address_line_2: string;
  address_line_3: string;
  city: string;
  state: string;
  zip: string;
  country_code: string;
  is_default: boolean;
}

const emptyAddress = (type: string): AddressForm => ({
  address_type: type,
  name: "",
  email: "",
  telephone: "",
  telephone_dial: "+1",
  telephone_number: "",
  tax_id: "",
  address_line_1: "",
  address_line_2: "",
  address_line_3: "",
  city: "",
  state: "",
  zip: "",
  country_code: "US",
  is_default: type === "billing",
});

type ShippingChoice = "proceed" | "same";

export default function RegisterPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  // ADR-126: English default for public form, but don't change global fallbackLng
  useEffect(() => {
    const lang = searchParams.get("lang") || "en";
    i18n.changeLanguage(lang);
    return () => {
      // Restore default language when leaving page
      i18n.changeLanguage("ja");
    };
  }, [searchParams]);

  const [loading, setLoading] = useState(true);
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // Form state
  const [billingDisplayName, setBillingDisplayName] = useState("");
  const [paymentRecipientName, setPaymentRecipientName] = useState("");
  const [billingAddress, setBillingAddress] = useState<AddressForm>(emptyAddress("billing"));
  const [deliveryAddress, setDeliveryAddress] = useState<AddressForm>(emptyAddress("delivery"));
  const [shippingChoice, setShippingChoice] = useState<ShippingChoice>("same");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactTelephone, setContactTelephone] = useState("");

  useEffect(() => {
    if (!token) {
      setError(t("registration.invalidToken"));
      setLoading(false);
      return;
    }

    fetch(`/api/v1/public/register?token=${encodeURIComponent(token)}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(t("registration.invalidToken"));
        }
        return res.json();
      })
      .then((data: TokenInfo) => {
        setTokenInfo(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || t("registration.invalidToken"));
        setLoading(false);
      });
  }, [token, t]);

  /** Combine dial code + number into a single international phone string. */
  const combinePhone = (addr: AddressForm): string => {
    if (!addr.telephone_number) return "";
    return `${addr.telephone_dial}${addr.telephone_number.replace(/^0+/, "")}`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Front-end required field validation
    if (!billingDisplayName.trim()) {
      setError(t("registration.billingNameRequired"));
      return;
    }
    if (!billingAddress.telephone_number.trim()) {
      setError(t("registration.telephoneRequired"));
      return;
    }
    if (!billingAddress.email.trim()) {
      setError(t("registration.emailRequired"));
      return;
    }
    if (!billingAddress.address_line_1.trim()) {
      setError(t("registration.addressLine1Required"));
      return;
    }
    if (!billingAddress.country_code.trim()) {
      setError(t("registration.countryRequired"));
      return;
    }
    if (!contactName.trim()) {
      setError(t("registration.contactNameRequired"));
      return;
    }
    if (!contactEmail.trim() && !contactTelephone.trim()) {
      setError(t("registration.contactContactRequired"));
      return;
    }

    setSubmitting(true);

    // Prepare billing address with combined phone
    const billingData = {
      ...billingAddress,
      name: billingDisplayName,
      telephone: combinePhone(billingAddress),
    };

    // Build addresses array
    const addresses = [billingData];

    if (shippingChoice === "proceed") {
      // Shipping address validation
      if (!deliveryAddress.name.trim()) {
        setError(t("registration.recipientNameRequired"));
        setSubmitting(false);
        return;
      }
      if (!deliveryAddress.address_line_1.trim()) {
        setError(t("registration.shippingAddressLine1Required"));
        setSubmitting(false);
        return;
      }
      if (!deliveryAddress.country_code.trim()) {
        setError(t("registration.shippingCountryRequired"));
        setSubmitting(false);
        return;
      }
      addresses.push({
        ...deliveryAddress,
        telephone: combinePhone(deliveryAddress),
      });
    } else {
      // "Ship to the same address." -> duplicate billing as delivery
      addresses.push({
        ...billingData,
        address_type: "delivery",
        is_default: true,
      });
    }

    try {
      const res = await fetch("/api/v1/public/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          addresses,
          contact_name: contactName || undefined,
          contact_email: contactEmail || undefined,
          contact_telephone: contactTelephone || undefined,
          billing_display_name: billingDisplayName || undefined,
          payment_recipient_name: paymentRecipientName || undefined,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const rawDetail = body?.detail;
        const msg = Array.isArray(rawDetail)
          ? rawDetail.map((d: { msg?: string; message?: string }) => d.msg ?? d.message ?? t("registration.submitError")).join(", ")
          : rawDetail ?? t("registration.submitError");
        throw new Error(msg);
      }

      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("registration.submitError"));
    } finally {
      setSubmitting(false);
    }
  };

  const currentLang = i18n.language;
  const toggleLang = () => {
    const next = currentLang === "en" ? "ja" : "en";
    i18n.changeLanguage(next);
  };

  if (loading) {
    return (
      <div className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
        <p>{t("common.loading")}</p>
      </div>
    );
  }

  if (error && !tokenInfo) {
    return (
      <div className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
        <div className="error-banner">{error}</div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
        <h1>{t("registration.completeTitle")}</h1>
        <p>{t("registration.completeMessage")}</p>
      </div>
    );
  }

  const updateBilling = (field: keyof AddressForm, value: string | boolean) =>
    setBillingAddress((prev) => ({ ...prev, [field]: value }));
  const updateDelivery = (field: keyof AddressForm, value: string | boolean) =>
    setDeliveryAddress((prev) => ({ ...prev, [field]: value }));

  const requiredMark = <span style={{ color: "var(--color-red-500)", fontWeight: "var(--font-weight-bold)" }}>*</span>;

  return (
    <div className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
      {/* Language toggle */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "var(--spacing-3)" }}>
        <button type="button" className="btn btn-ghost" onClick={toggleLang} style={{ fontSize: "var(--font-size-sm)" }}>
          {currentLang === "en" ? t("registration.switchToJapanese") : t("registration.switchToEnglish")}
        </button>
      </div>

      <h1>{t("registration.title")}</h1>
      {tokenInfo?.company_name && (
        <p style={{ color: "var(--text-secondary)", marginBottom: "var(--spacing-4)" }}>
          {t("registration.companyLabel")}: {tokenInfo.company_name}
        </p>
      )}

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Section 1: Billing Address Registration */}
        <fieldset style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" }}>
          <legend style={{ fontWeight: "var(--font-weight-bold)" }}>{t("registration.section1Title")}</legend>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            {/* 1. Billing Name */}
            <label>
              {t("registration.billingName")} {requiredMark}
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", margin: "0 0 var(--spacing-1)" }}>
                {t("registration.billingNameHint")}
              </p>
              <input
                type="text"
                className="input"
                value={billingDisplayName}
                onChange={(e) => setBillingDisplayName(e.target.value)}
                required
              />
            </label>

            {/* 2. Telephone Number (dial code combo + number) */}
            <label>
              {t("registration.telephone")} {requiredMark}
            </label>
            <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
              <div style={{ width: "140px", flexShrink: 0 }}>
                <CountryCombobox
                  entries={COUNTRIES}
                  value={billingAddress.telephone_dial}
                  onChange={(val) => {
                    const found = COUNTRIES.find((c) => `${c.dial} ${c.code}` === val);
                    updateBilling("telephone_dial", found ? found.dial : val);
                  }}
                  displayFn={(c) => `${c.dial} ${c.code}`}
                  filterFn={(c, q) =>
                    c.name.toLowerCase().includes(q) ||
                    c.code.toLowerCase().includes(q) ||
                    c.dial.includes(q)
                  }
                  id="billing-dial"
                />
              </div>
              <input
                type="tel"
                className="input"
                style={{ flex: 1 }}
                value={billingAddress.telephone_number}
                onChange={(e) => updateBilling("telephone_number", e.target.value.replace(/[^\d]/g, ""))}
                placeholder="1234567890"
                required
              />
            </div>

            {/* 3. Email Address */}
            <label>
              {t("registration.emailAddress")} {requiredMark}
              <input
                type="email"
                className="input"
                value={billingAddress.email}
                onChange={(e) => updateBilling("email", e.target.value)}
                required
              />
            </label>

            {/* 4. Payment Account Name (optional) */}
            <label>
              {t("registration.paymentRecipientName")}
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", margin: "0 0 var(--spacing-1)" }}>
                {t("registration.paymentRecipientNameHint")}
              </p>
              <input
                type="text"
                className="input"
                value={paymentRecipientName}
                onChange={(e) => setPaymentRecipientName(e.target.value)}
              />
            </label>

            {/* 5. Tax ID (optional) */}
            <label>
              {t("registration.taxIdFull")}
              <input
                type="text"
                className="input"
                value={billingAddress.tax_id}
                onChange={(e) => updateBilling("tax_id", e.target.value)}
              />
            </label>

            {/* 6. Address Line 1 */}
            <label>
              {t("registration.addressLine1")} {requiredMark}
              <input
                type="text"
                className="input"
                value={billingAddress.address_line_1}
                onChange={(e) => updateBilling("address_line_1", e.target.value)}
                required
              />
            </label>

            {/* 7. Address Line 2 */}
            <label>
              {t("registration.addressLine2Hint")}
              <input
                type="text"
                className="input"
                value={billingAddress.address_line_2}
                onChange={(e) => updateBilling("address_line_2", e.target.value)}
              />
            </label>

            {/* 8. City */}
            <label>
              {t("registration.city")}
              <input
                type="text"
                className="input"
                value={billingAddress.city}
                onChange={(e) => updateBilling("city", e.target.value)}
              />
            </label>

            {/* 9. State */}
            <label>
              {t("registration.state")}
              <input
                type="text"
                className="input"
                value={billingAddress.state}
                onChange={(e) => updateBilling("state", e.target.value)}
              />
            </label>

            {/* 10. ZIP */}
            <label>
              {t("registration.zip")}
              <input
                type="text"
                className="input"
                value={billingAddress.zip}
                onChange={(e) => updateBilling("zip", e.target.value)}
              />
            </label>

            {/* 11. Country */}
            <label>
              {t("registration.country")} {requiredMark}
            </label>
            <CountryCombobox
              entries={COUNTRIES}
              value={billingAddress.country_code}
              onChange={(val) => {
                // Extract alpha-2 code from display string or use directly
                const found = COUNTRIES.find((c) => `${c.name} (${c.code})` === val);
                updateBilling("country_code", found ? found.code : val);
              }}
              displayFn={(c) => `${c.name} (${c.code})`}
              filterFn={(c, q) =>
                c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
              }
              id="billing-country"
            />

            {/* 12. Shipping question */}
            <div style={{ marginTop: "var(--spacing-3)" }}>
              <p style={{ fontWeight: "var(--font-weight-bold)", marginBottom: "var(--spacing-2)" }}>
                {t("registration.shippingQuestion")} {requiredMark}
              </p>
              <label style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="shipping_choice"
                  value="proceed"
                  checked={shippingChoice === "proceed"}
                  onChange={() => setShippingChoice("proceed")}
                />
                {t("registration.proceedToRegister")}
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", cursor: "pointer", marginTop: "var(--spacing-1)" }}>
                <input
                  type="radio"
                  name="shipping_choice"
                  value="same"
                  checked={shippingChoice === "same"}
                  onChange={() => setShippingChoice("same")}
                />
                {t("registration.shipToSameAddress")}
              </label>
            </div>
          </div>
        </fieldset>

        {/* Section 2: Shipping Address Registration (hidden when "same") */}
        {shippingChoice === "proceed" && (
          <fieldset style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" }}>
            <legend style={{ fontWeight: "var(--font-weight-bold)" }}>{t("registration.section2Title")}</legend>
            <ShippingAddressFields
              address={deliveryAddress}
              onChange={updateDelivery}
            />
          </fieldset>
        )}

        {/* Contact Info */}
        <fieldset style={{ border: "2px solid var(--color-primary)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" }}>
          <legend style={{ fontWeight: "var(--font-weight-bold)", padding: "0 var(--spacing-2)" }}>
            {t("registration.contactInfo")}
          </legend>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", margin: "0 0 var(--spacing-3)" }}>
            {t("registration.contactHint")}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            <label>
              {t("registration.contactName")} {requiredMark}
              <input
                type="text"
                className="input"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
              />
            </label>
            <label>
              {t("registration.contactEmail")}
              <input
                type="email"
                className="input"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
              />
            </label>
            <label>
              {t("registration.contactTelephone")}
              <input
                type="tel"
                className="input"
                value={contactTelephone}
                onChange={(e) => setContactTelephone(e.target.value)}
              />
            </label>
          </div>
        </fieldset>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ width: "100%" }}
        >
          {submitting ? t("common.saving") : t("registration.submit")}
        </button>
      </form>
    </div>
  );
}

/** Section 2 fields for shipping address (ADR-126 Section 2). */
function ShippingAddressFields({
  address,
  onChange,
}: {
  address: AddressForm;
  onChange: (field: keyof AddressForm, value: string | boolean) => void;
}) {
  const { t } = useTranslation();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
      {/* 1. Recipient Name */}
      <label>
        {t("registration.recipientName")} <span style={{ color: "var(--color-red-500)", fontWeight: "var(--font-weight-bold)" }}>*</span>
        <input
          type="text"
          className="input"
          value={address.name}
          onChange={(e) => onChange("name", e.target.value)}
          required
        />
      </label>

      {/* 2. Telephone Number (optional for shipping) */}
      <label>{t("registration.telephone")}</label>
      <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
        <div style={{ width: "140px", flexShrink: 0 }}>
          <CountryCombobox
            entries={COUNTRIES}
            value={address.telephone_dial}
            onChange={(val) => {
              const found = COUNTRIES.find((c) => `${c.dial} ${c.code}` === val);
              onChange("telephone_dial", found ? found.dial : val);
            }}
            displayFn={(c) => `${c.dial} ${c.code}`}
            filterFn={(c, q) =>
              c.name.toLowerCase().includes(q) ||
              c.code.toLowerCase().includes(q) ||
              c.dial.includes(q)
            }
            id="shipping-dial"
          />
        </div>
        <input
          type="tel"
          className="input"
          style={{ flex: 1 }}
          value={address.telephone_number}
          onChange={(e) => onChange("telephone_number", e.target.value.replace(/[^\d]/g, ""))}
          placeholder="1234567890"
        />
      </div>

      {/* 3. Email Address (optional for shipping) */}
      <label>
        {t("registration.shippingEmail")}
        <input
          type="email"
          className="input"
          value={address.email}
          onChange={(e) => onChange("email", e.target.value)}
        />
      </label>

      {/* 4. Tax ID (optional) */}
      <label>
        {t("registration.taxIdFull")}
        <input
          type="text"
          className="input"
          value={address.tax_id}
          onChange={(e) => onChange("tax_id", e.target.value)}
        />
      </label>

      {/* 5. Address Line 1 */}
      <label>
        {t("registration.addressLine1")} <span style={{ color: "var(--color-red-500)", fontWeight: "var(--font-weight-bold)" }}>*</span>
        <input
          type="text"
          className="input"
          value={address.address_line_1}
          onChange={(e) => onChange("address_line_1", e.target.value)}
          required
        />
      </label>

      {/* 6. Address Line 2 */}
      <label>
        {t("registration.addressLine2")}
        <input
          type="text"
          className="input"
          value={address.address_line_2}
          onChange={(e) => onChange("address_line_2", e.target.value)}
        />
      </label>

      {/* 7. Address Line 3 (shipping only, ADR-126) */}
      <label>
        {t("registration.addressLine3")}
        <input
          type="text"
          className="input"
          value={address.address_line_3}
          onChange={(e) => onChange("address_line_3", e.target.value)}
        />
      </label>

      {/* 8. City */}
      <label>
        {t("registration.city")}
        <input
          type="text"
          className="input"
          value={address.city}
          onChange={(e) => onChange("city", e.target.value)}
        />
      </label>

      {/* 9. State */}
      <label>
        {t("registration.state")}
        <input
          type="text"
          className="input"
          value={address.state}
          onChange={(e) => onChange("state", e.target.value)}
        />
      </label>

      {/* 10. ZIP */}
      <label>
        {t("registration.zip")}
        <input
          type="text"
          className="input"
          value={address.zip}
          onChange={(e) => onChange("zip", e.target.value)}
        />
      </label>

      {/* 11. Country */}
      <label>
        {t("registration.country")} <span style={{ color: "var(--color-red-500)", fontWeight: "var(--font-weight-bold)" }}>*</span>
      </label>
      <CountryCombobox
        entries={COUNTRIES}
        value={address.country_code}
        onChange={(val) => {
          const found = COUNTRIES.find((c) => `${c.name} (${c.code})` === val);
          onChange("country_code", found ? found.code : val);
        }}
        displayFn={(c) => `${c.name} (${c.code})`}
        filterFn={(c, q) =>
          c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
        }
        id="shipping-country"
      />
    </div>
  );
}
