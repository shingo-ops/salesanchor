/**
 * Change Billing Address Page (public, no auth). ADR-SA-03 + ADR-126 v2 + ADR-127.
 *
 * URL: /register/change-billing?token=...
 * Displays in English by default (ADR-126 Section 4) with language toggle.
 * Billing-only form; address_type is fixed to "billing".
 * Backend applies 案B: 旧行降格(is_default=false)→新行INSERT(is_default=true) in one transaction.
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
import { LoadingBlock } from "../../components/loading";

interface TokenInfo {
  valid: boolean;
  company_name: string | null;
  lead_id: number | null;
  token_type: string | null;
}

interface AddressForm {
  address_type: "billing";
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
  is_default: true;
}

const emptyBillingAddress = (): AddressForm => ({
  address_type: "billing",
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
  is_default: true,
});

const KNOWN_ERROR_CODES = new Set([
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

export default function RegisterChangeBillingPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  // ADR-126: English default for public form
  useEffect(() => {
    const lang = searchParams.get("lang") || "en";
    i18n.changeLanguage(lang);
    return () => {
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
  const [address, setAddress] = useState<AddressForm>(emptyBillingAddress());

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

  const updateAddress = (field: keyof AddressForm, value: string) =>
    setAddress((prev) => ({ ...prev, [field]: value }));

  /** Combine dial code + number into a single international phone string. */
  const combinePhone = (): string => {
    if (!address.telephone_number) return "";
    return `${address.telephone_dial}${address.telephone_number.replace(/^0+/, "")}`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!billingDisplayName.trim()) {
      setError(t("registration.billingNameRequired"));
      return;
    }
    if (!address.telephone_number.trim()) {
      setError(t("registration.telephoneRequired"));
      return;
    }
    if (!address.email.trim()) {
      setError(t("registration.emailRequired"));
      return;
    }
    if (!address.address_line_1.trim()) {
      setError(t("registration.addressLine1Required"));
      return;
    }
    if (!address.country_code.trim()) {
      setError(t("registration.countryRequired"));
      return;
    }

    setSubmitting(true);

    try {
      const res = await fetch("/api/v1/public/register/change-billing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          address: {
            ...address,
            telephone: combinePhone(),
          },
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

  const requiredMark = <span style={{ color: "var(--danger)", fontWeight: "var(--font-weight-bold)" }}>*</span>;

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
        <h1>{t("registration.changeBillingCompleteTitle")}</h1>
        <p>{t("registration.changeBillingCompleteMessage")}</p>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ maxWidth: "var(--max-width-public-form)", margin: "0 auto", padding: 0 }}>
      {/* Title row with language toggle (K1) */}
      <div className="page-header">
        <h1>{t("registration.changeBillingTitle")}</h1>
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
                  value={address.telephone_dial}
                  onChange={(val) => updateAddress("telephone_dial", val)}
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
                value={address.telephone_number}
                onChange={(e) => updateAddress("telephone_number", e.target.value.replace(/[^\d]/g, ""))}
                placeholder="1234567890"
                required
              />
            </div>

            {/* 3. Email Address */}
            <label>
              {t("registration.emailAddress")} {requiredMark}
              <TextFieldControl
                type="email"
                value={address.email}
                onChange={(e) => updateAddress("email", e.target.value)}
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
                value={address.tax_id}
                onChange={(e) => updateAddress("tax_id", e.target.value)}
              />
            </label>

            {/* 6. Address Line 1 */}
            <TextField
              label={t("registration.addressLine1")}
              required
              fullWidth
              value={address.address_line_1}
              onChange={(e) => updateAddress("address_line_1", e.target.value)}
            />

            {/* 7. Address Line 2 */}
            <TextField
              label={t("registration.addressLine2Hint")}
              fullWidth
              value={address.address_line_2}
              onChange={(e) => updateAddress("address_line_2", e.target.value)}
            />

            {/* 7b. Address Line 3 (K9) */}
            <TextField
              label={t("registration.addressLine3")}
              fullWidth
              value={address.address_line_3}
              onChange={(e) => updateAddress("address_line_3", e.target.value)}
            />

            {/* 8. City */}
            <label>
              {t("registration.city")}
              <TextFieldControl
                type="text"
                value={address.city}
                onChange={(e) => updateAddress("city", e.target.value)}
              />
            </label>

            {/* 9. State + 10. ZIP (K3) */}
            <TwoColumn ratio="1:1" gap="4">
              <label>
                {t("registration.state")}
                <TextFieldControl
                  type="text"
                  value={address.state}
                  onChange={(e) => updateAddress("state", e.target.value)}
                />
              </label>
              <label>
                {t("registration.zip")}
                <TextFieldControl
                  type="text"
                  value={address.zip}
                  onChange={(e) => updateAddress("zip", e.target.value)}
                />
              </label>
            </TwoColumn>

            {/* 11. Country */}
            <label>
              {t("registration.country")} {requiredMark}
            </label>
            <CountryCombobox
              entries={COUNTRIES}
              value={address.country_code}
              onChange={(val) => {
                const found = COUNTRIES.find((c) => `${c.name} (${c.code})` === val);
                updateAddress("country_code", found ? found.code : val);
              }}
              displayFn={(c) => `${c.name} (${c.code})`}
              filterFn={(c, q) =>
                c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
              }
              id="billing-country"
            />
          </div>
        </fieldset>

        <Button loading={submitting} variant="primary" size="md" fullWidth
          type="submit"

          disabled={submitting}

        >
          {t("registration.changeBillingSubmit")}
        </Button>
      </form>
    </div>
  );
}
