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

  const requiredMark = <span style={{ color: "var(--color-red-500)", fontWeight: "var(--font-weight-bold)" }}>*</span>;

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
        <h1>{t("registration.changeBillingCompleteTitle")}</h1>
        <p>{t("registration.changeBillingCompleteMessage")}</p>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
      {/* Language toggle */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "var(--spacing-3)" }}>
        <button type="button" className="btn btn-ghost" onClick={toggleLang} style={{ fontSize: "var(--font-size-sm)" }}>
          {currentLang === "en" ? t("registration.switchToJapanese") : t("registration.switchToEnglish")}
        </button>
      </div>

      <h1>{t("registration.changeBillingTitle")}</h1>
      {tokenInfo?.company_name && (
        <p style={{ color: "var(--text-secondary)", marginBottom: "var(--spacing-4)" }}>
          {t("registration.companyLabel")}: {tokenInfo.company_name}
        </p>
      )}

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit}>
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
                  value={address.telephone_dial}
                  onChange={(val) => {
                    const found = COUNTRIES.find((c) => `${c.dial} ${c.code}` === val);
                    updateAddress("telephone_dial", found ? found.dial : val);
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
                value={address.telephone_number}
                onChange={(e) => updateAddress("telephone_number", e.target.value.replace(/[^\d]/g, ""))}
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
                value={address.email}
                onChange={(e) => updateAddress("email", e.target.value)}
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
                value={address.tax_id}
                onChange={(e) => updateAddress("tax_id", e.target.value)}
              />
            </label>

            {/* 6. Address Line 1 */}
            <label>
              {t("registration.addressLine1")} {requiredMark}
              <input
                type="text"
                className="input"
                value={address.address_line_1}
                onChange={(e) => updateAddress("address_line_1", e.target.value)}
                required
              />
            </label>

            {/* 7. Address Line 2 */}
            <label>
              {t("registration.addressLine2Hint")}
              <input
                type="text"
                className="input"
                value={address.address_line_2}
                onChange={(e) => updateAddress("address_line_2", e.target.value)}
              />
            </label>

            {/* 8. City */}
            <label>
              {t("registration.city")}
              <input
                type="text"
                className="input"
                value={address.city}
                onChange={(e) => updateAddress("city", e.target.value)}
              />
            </label>

            {/* 9. State */}
            <label>
              {t("registration.state")}
              <input
                type="text"
                className="input"
                value={address.state}
                onChange={(e) => updateAddress("state", e.target.value)}
              />
            </label>

            {/* 10. ZIP */}
            <label>
              {t("registration.zip")}
              <input
                type="text"
                className="input"
                value={address.zip}
                onChange={(e) => updateAddress("zip", e.target.value)}
              />
            </label>

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

        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ width: "100%" }}
        >
          {submitting ? t("common.saving") : t("registration.changeBillingSubmit")}
        </button>
      </form>
    </div>
  );
}
