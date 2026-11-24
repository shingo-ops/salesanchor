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
import { Button } from "../../components/Button";
import { TextField, TextFieldControl } from "../../components/TextField";
import { TwoColumn } from "../../components/TwoColumn";
import { DELIVERY_ADDRESS_LINE_MAX, deliveryAddressLineError } from "../../utils/addressRules";
import { Radio } from "../../components/Radio";
import { LoadingBlock } from "../../components/loading";

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

const KNOWN_ERROR_CODES = new Set([
  "already_registered",
  "invalid_token",
  "company_not_found",
  "unexpected_error",
]);

function resolveErrorCode(code: unknown, t: (key: string) => string): string {
  if (typeof code === "string" && KNOWN_ERROR_CODES.has(code)) {
    return t(`registration.error.${code}`);
  }
  return t("registration.submitError");
}

type Translate = (key: string, options?: Record<string, unknown>) => string;

/** 住所1〜3の決まり違反の文（合えば undefined）。画面の決まりは utils/addressRules.ts の1か所。 */
function lineRuleText(value: string, t: Translate): string | undefined {
  const key = deliveryAddressLineError(value);
  return key ? t(key, { max: DELIVERY_ADDRESS_LINE_MAX }) : undefined;
}

const hasLineViolation = (a: AddressForm) =>
  [a.address_line_1, a.address_line_2, a.address_line_3].some((v) => deliveryAddressLineError(v) !== null);

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
    // 請求先は「Ship to the same address.」の時だけ決まりを当てる（欄の赤と文で知らせる）
    if (shippingChoice === "same" && hasLineViolation(billingAddress)) {
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
      if (hasLineViolation(deliveryAddress)) {
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
          : resolveErrorCode(rawDetail, t);
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
      <div className="page-container" style={{ maxWidth: "var(--max-width-public-form)", margin: "0 auto", padding: 0 }}>
        <LoadingBlock />
      </div>
    );
  }

  if (error && !tokenInfo) {
    return (
      <div className="page-container" style={{ maxWidth: "var(--max-width-public-form)", margin: "0 auto", padding: 0 }}>
        <div className="error-banner">{error}</div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="page-container" style={{ maxWidth: "var(--max-width-public-form)", margin: "0 auto", padding: 0 }}>
        <h1>{t("registration.completeTitle")}</h1>
        <p>{t("registration.completeMessage")}</p>
      </div>
    );
  }

  const updateBilling = (field: keyof AddressForm, value: string | boolean) =>
    setBillingAddress((prev) => ({ ...prev, [field]: value }));
  const updateDelivery = (field: keyof AddressForm, value: string | boolean) =>
    setDeliveryAddress((prev) => ({ ...prev, [field]: value }));

  // 請求先に決まりを当てるのは「Ship to the same address.」の時だけ（K8・D2）
  const billingRule = shippingChoice === "same";

  const requiredMark = <span style={{ color: "var(--danger)", fontWeight: "var(--font-weight-bold)" }}>*</span>;

  return (
    <div className="page-container" style={{ maxWidth: "var(--max-width-public-form)", margin: "0 auto", padding: 0 }}>
      {/* Title row with language toggle (K1) */}
      <div className="page-header">
        <h1>{t("registration.title")}</h1>
        <Button variant="ghost" size="md" type="button" onClick={toggleLang}>
          {currentLang === "en" ? t("registration.switchToJapanese") : t("registration.switchToEnglish")}
        </Button>
      </div>
      {tokenInfo?.company_name && (
        <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
          {t("registration.companyLabel")}: {tokenInfo.company_name}
        </p>
      )}

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Section 1: Billing Address Registration */}
        <fieldset style={{ border: "none", borderRadius: "var(--radius-md)", padding: 0, marginBottom: "var(--space-4)" }}>
          <legend style={{ fontWeight: "var(--font-weight-bold)" }}>{t("registration.section1Title")}</legend>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            {/* 1. Billing Name */}
            <label>
              {t("registration.billingName")} {requiredMark}
              <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", margin: "0 0 var(--space-1)" }}>
                {t("registration.billingNameHint")}
              </p>
              <TextFieldControl
                type="text"
                value={billingDisplayName}
                onChange={(e) => setBillingDisplayName(e.target.value)}
                required
              />
            </label>

            {/* 2. Telephone Number (dial code combo + number) */}
            <label>
              {t("registration.telephone")} {requiredMark}
            </label>
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <div className="field-w-xs" style={{ flexShrink: 0 }}>
                <CountryCombobox
                  entries={COUNTRIES}
                  value={billingAddress.telephone_dial}
                  onChange={(val) => updateBilling("telephone_dial", val)}
                  displayFn={(c) => c.dial}
                  optionLabelFn={(c) => `${c.dial} ${c.name}`}
                  filterFn={(c, q) =>
                    c.name.toLowerCase().includes(q) ||
                    c.code.toLowerCase().includes(q) ||
                    c.dial.includes(q)
                  }
                  id="billing-dial"
                />
              </div>
              <TextFieldControl
                type="tel"
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
              <TextFieldControl
                type="email"
                value={billingAddress.email}
                onChange={(e) => updateBilling("email", e.target.value)}
                required
              />
            </label>

            {/* 4. Payment Account Name (optional) */}
            <label>
              {t("registration.paymentRecipientName")}
              <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", margin: "0 0 var(--space-1)" }}>
                {t("registration.paymentRecipientNameHint")}
              </p>
              <TextFieldControl
                type="text"
                value={paymentRecipientName}
                onChange={(e) => setPaymentRecipientName(e.target.value)}
              />
            </label>

            {/* 5. Tax ID (optional) */}
            <label>
              {t("registration.taxIdFull")}
              <TextFieldControl
                type="text"
                value={billingAddress.tax_id}
                onChange={(e) => updateBilling("tax_id", e.target.value)}
              />
            </label>

            {/* 6. Address Line 1 */}
            <TextField
              label={t("registration.addressLine1")}
              required
              fullWidth
              value={billingAddress.address_line_1}
              onChange={(e) => updateBilling("address_line_1", e.target.value)}
              error={billingRule ? lineRuleText(billingAddress.address_line_1, t) : undefined}
            />

            {/* 7. Address Line 2 */}
            <TextField
              label={t("registration.addressLine2Hint")}
              fullWidth
              value={billingAddress.address_line_2}
              onChange={(e) => updateBilling("address_line_2", e.target.value)}
              error={billingRule ? lineRuleText(billingAddress.address_line_2, t) : undefined}
            />

            {/* 7b. Address Line 3 (K9) */}
            <TextField
              label={t("registration.addressLine3")}
              fullWidth
              value={billingAddress.address_line_3}
              onChange={(e) => updateBilling("address_line_3", e.target.value)}
              error={billingRule ? lineRuleText(billingAddress.address_line_3, t) : undefined}
            />

            {/* 8. City */}
            <label>
              {t("registration.city")}
              <TextFieldControl
                type="text"
                value={billingAddress.city}
                onChange={(e) => updateBilling("city", e.target.value)}
              />
            </label>

            {/* 9. State + 10. ZIP (K3) */}
            <TwoColumn ratio="1:1" gap="4">
              <label>
                {t("registration.state")}
                <TextFieldControl
                  type="text"
                  value={billingAddress.state}
                  onChange={(e) => updateBilling("state", e.target.value)}
                />
              </label>
              <label>
                {t("registration.zip")}
                <TextFieldControl
                  type="text"
                  value={billingAddress.zip}
                  onChange={(e) => updateBilling("zip", e.target.value)}
                />
              </label>
            </TwoColumn>

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
            <div style={{ marginTop: "var(--space-3)" }}>
              <p style={{ fontWeight: "var(--font-weight-bold)", marginBottom: "var(--space-2)" }}>
                {t("registration.shippingQuestion")} {requiredMark}
              </p>
              <div>
                <Radio
                  name="shipping_choice"
                  value="proceed"
                  checked={shippingChoice === "proceed"}
                  onChange={() => setShippingChoice("proceed")}
                  label={t("registration.proceedToRegister")}
                />
              </div>
              <div>
                <Radio
                  name="shipping_choice"
                  value="same"
                  checked={shippingChoice === "same"}
                  onChange={() => setShippingChoice("same")}
                  label={t("registration.shipToSameAddress")}
                />
              </div>
            </div>
          </div>
        </fieldset>

        {/* Section 2: Shipping Address Registration (hidden when "same") */}
        {shippingChoice === "proceed" && (
          <fieldset style={{ border: "none", borderRadius: "var(--radius-md)", padding: 0, marginBottom: "var(--space-4)" }}>
            <legend style={{ fontWeight: "var(--font-weight-bold)" }}>{t("registration.section2Title")}</legend>
            <ShippingAddressFields
              address={deliveryAddress}
              onChange={updateDelivery}
            />
          </fieldset>
        )}

        {/* Contact Info */}
        <fieldset style={{ border: "none", borderRadius: "var(--radius-md)", padding: 0, marginBottom: "var(--space-4)" }}>
          <legend style={{ fontWeight: "var(--font-weight-bold)", padding: "0 var(--space-2)" }}>
            {t("registration.contactInfo")}
          </legend>
          <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", margin: "0 0 var(--space-3)" }}>
            {t("registration.contactHint")}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <label>
              {t("registration.contactName")}
              <TextFieldControl
                type="text"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
              />
            </label>
            <label>
              {t("registration.contactEmail")}
              <TextFieldControl
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
              />
            </label>
            <label>
              {t("registration.contactTelephone")}
              <TextFieldControl
                type="tel"
                value={contactTelephone}
                onChange={(e) => setContactTelephone(e.target.value)}
              />
            </label>
          </div>
        </fieldset>

        <Button loading={submitting} variant="primary" size="md" fullWidth
          type="submit"

          disabled={submitting}

        >
          {t("registration.submit")}
        </Button>
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
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {/* 1. Recipient Name */}
      <label>
        {t("registration.recipientName")} <span style={{ color: "var(--danger)", fontWeight: "var(--font-weight-bold)" }}>*</span>
        <TextFieldControl
          type="text"
          value={address.name}
          onChange={(e) => onChange("name", e.target.value)}
          required
        />
      </label>

      {/* 2. Telephone Number (optional for shipping) */}
      <label>{t("registration.telephone")}</label>
      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        <div className="field-w-xs" style={{ flexShrink: 0 }}>
          <CountryCombobox
            entries={COUNTRIES}
            value={address.telephone_dial}
            onChange={(val) => onChange("telephone_dial", val)}
            displayFn={(c) => c.dial}
            optionLabelFn={(c) => `${c.dial} ${c.name}`}
            filterFn={(c, q) =>
              c.name.toLowerCase().includes(q) ||
              c.code.toLowerCase().includes(q) ||
              c.dial.includes(q)
            }
            id="shipping-dial"
          />
        </div>
        <TextFieldControl
          type="tel"
          style={{ flex: 1 }}
          value={address.telephone_number}
          onChange={(e) => onChange("telephone_number", e.target.value.replace(/[^\d]/g, ""))}
          placeholder="1234567890"
        />
      </div>

      {/* 3. Email Address (optional for shipping) */}
      <label>
        {t("registration.shippingEmail")}
        <TextFieldControl
          type="email"
          value={address.email}
          onChange={(e) => onChange("email", e.target.value)}
        />
      </label>

      {/* 4. Tax ID (optional) */}
      <label>
        {t("registration.taxIdFull")}
        <TextFieldControl
          type="text"
          value={address.tax_id}
          onChange={(e) => onChange("tax_id", e.target.value)}
        />
      </label>

      {/* 5. Address Line 1 */}
      <TextField
        label={t("registration.addressLine1")}
        required
        fullWidth
        value={address.address_line_1}
        onChange={(e) => onChange("address_line_1", e.target.value)}
        error={lineRuleText(address.address_line_1, t)}
      />

      {/* 6. Address Line 2 */}
      <TextField
        label={t("registration.addressLine2")}
        fullWidth
        value={address.address_line_2}
        onChange={(e) => onChange("address_line_2", e.target.value)}
        error={lineRuleText(address.address_line_2, t)}
      />

      {/* 7. Address Line 3 (shipping only, ADR-126) */}
      <TextField
        label={t("registration.addressLine3")}
        fullWidth
        value={address.address_line_3}
        onChange={(e) => onChange("address_line_3", e.target.value)}
        error={lineRuleText(address.address_line_3, t)}
      />

      {/* 8. City */}
      <label>
        {t("registration.city")}
        <TextFieldControl
          type="text"
          value={address.city}
          onChange={(e) => onChange("city", e.target.value)}
        />
      </label>

      {/* 9. State + 10. ZIP (K3) */}
      <TwoColumn ratio="1:1" gap="4">
        <label>
          {t("registration.state")}
          <TextFieldControl
            type="text"
            value={address.state}
            onChange={(e) => onChange("state", e.target.value)}
          />
        </label>
        <label>
          {t("registration.zip")}
          <TextFieldControl
            type="text"
            value={address.zip}
            onChange={(e) => onChange("zip", e.target.value)}
          />
        </label>
      </TwoColumn>

      {/* 11. Country */}
      <label>
        {t("registration.country")} <span style={{ color: "var(--danger)", fontWeight: "var(--font-weight-bold)" }}>*</span>
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
