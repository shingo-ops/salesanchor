/**
 * Address Addition Page (public, no auth). ADR-SA-03 + ADR-126 v2.
 *
 * URL: /register/address?token=...
 * Appends a new address to the existing company (does not overwrite).
 * Displays in English by default (ADR-126 Section 4).
 */

import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { COUNTRIES, type CountryEntry } from "../../constants/countries";
import { Button } from "../../components/Button";
import { TextField, TextFieldControl } from "../../components/TextField";
import { TwoColumn } from "../../components/TwoColumn";
import { DELIVERY_ADDRESS_LINE_MAX, deliveryAddressLineError } from "../../utils/addressRules";
import { CountryCombobox } from "./CountryCombobox";
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

const emptyAddress = (): AddressForm => ({
  address_type: "delivery",
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
  is_default: false,
});

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

export default function RegisterAddressPage() {
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

  const [address, setAddress] = useState<AddressForm>(emptyAddress());

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

  const combinePhone = (addr: AddressForm): string => {
    if (!addr.telephone_number) return "";
    return `${addr.telephone_dial}${addr.telephone_number.replace(/^0+/, "")}`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // 送り先の住所1〜3の決まり違反は送らない（欄の赤と文で知らせる）
    if ([address.address_line_1, address.address_line_2, address.address_line_3].some((v) => deliveryAddressLineError(v) !== null)) {
      return;
    }
    setSubmitting(true);
    setError("");

    try {
      const res = await fetch("/api/v1/public/register/address", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          address: {
            ...address,
            telephone: combinePhone(address),
          },
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
        <h1>{t("registration.addressAddedTitle")}</h1>
        <p>{t("registration.addressAddedMessage")}</p>
      </div>
    );
  }

  const lineRuleText = (value: string): string | undefined => {
    const key = deliveryAddressLineError(value);
    return key ? t(key, { max: DELIVERY_ADDRESS_LINE_MAX }) : undefined;
  };

  const updateField = (field: keyof AddressForm, value: string | boolean) =>
    setAddress((prev) => ({ ...prev, [field]: value }));

  const requiredMark = <span style={{ color: "var(--danger)", fontWeight: "var(--font-weight-bold)" }}>*</span>;

  return (
    <div className="page-container" style={{ maxWidth: "var(--max-width-public-form)", margin: "0 auto", padding: 0 }}>
      {/* Title row with language toggle (K1) */}
      <div className="page-header">
        <h1>{t("registration.addAddressTitle")}</h1>
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
          <legend style={{ fontWeight: "var(--font-weight-bold)" }}>{t("registration.addressDetails")}</legend>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            {/* Recipient Name */}
            <label>
              {t("registration.recipientName")} {requiredMark}
              <TextFieldControl
                type="text"
                value={address.name}
                onChange={(e) => updateField("name", e.target.value)}
              />
            </label>

            {/* Telephone (dial code + number) */}
            <label>{t("registration.telephone")}</label>
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <div className="field-w-xs" style={{ flexShrink: 0 }}>
                <CountryCombobox
                  entries={COUNTRIES}
                  value={address.telephone_dial}
                  onChange={(val) => updateField("telephone_dial", val)}
                  displayFn={(c) => c.dial}
                  optionLabelFn={(c) => `${c.dial} ${c.name}`}
                  filterFn={(c, q) =>
                    c.name.toLowerCase().includes(q) ||
                    c.code.toLowerCase().includes(q) ||
                    c.dial.includes(q)
                  }
                  id="address-dial"
                />
              </div>
              <TextFieldControl
                type="tel"
                style={{ flex: 1 }}
                value={address.telephone_number}
                onChange={(e) => updateField("telephone_number", e.target.value.replace(/[^\d]/g, ""))}
                placeholder="1234567890"
              />
            </div>

            {/* Email */}
            <label>
              {t("registration.shippingEmail")}
              <TextFieldControl
                type="email"
                value={address.email}
                onChange={(e) => updateField("email", e.target.value)}
              />
            </label>

            {/* Tax ID */}
            <label>
              {t("registration.taxIdFull")}
              <TextFieldControl
                type="text"
                value={address.tax_id}
                onChange={(e) => updateField("tax_id", e.target.value)}
              />
            </label>

            {/* Address Line 1 */}
            <TextField
              label={t("registration.addressLine1")}
              required
              fullWidth
              value={address.address_line_1}
              onChange={(e) => updateField("address_line_1", e.target.value)}
              error={lineRuleText(address.address_line_1)}
            />

            {/* Address Line 2 */}
            <TextField
              label={t("registration.addressLine2")}
              fullWidth
              value={address.address_line_2}
              onChange={(e) => updateField("address_line_2", e.target.value)}
              error={lineRuleText(address.address_line_2)}
            />

            {/* Address Line 3 */}
            <TextField
              label={t("registration.addressLine3")}
              fullWidth
              value={address.address_line_3}
              onChange={(e) => updateField("address_line_3", e.target.value)}
              error={lineRuleText(address.address_line_3)}
            />

            {/* City */}
            <label>
              {t("registration.city")}
              <TextFieldControl
                type="text"
                value={address.city}
                onChange={(e) => updateField("city", e.target.value)}
              />
            </label>

            {/* State + ZIP (K3) */}
            <TwoColumn ratio="1:1" gap="4">
              <label>
                {t("registration.state")}
                <TextFieldControl
                  type="text"
                  value={address.state}
                  onChange={(e) => updateField("state", e.target.value)}
                />
              </label>
              <label>
                {t("registration.zip")}
                <TextFieldControl
                  type="text"
                  value={address.zip}
                  onChange={(e) => updateField("zip", e.target.value)}
                />
              </label>
            </TwoColumn>

            {/* Country */}
            <label>
              {t("registration.country")} {requiredMark}
            </label>
            <CountryCombobox
              entries={COUNTRIES}
              value={address.country_code}
              onChange={(val) => {
                const found = COUNTRIES.find((c) => `${c.name} (${c.code})` === val);
                updateField("country_code", found ? found.code : val);
              }}
              displayFn={(c) => `${c.name} (${c.code})`}
              filterFn={(c, q) =>
                c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
              }
              id="address-country"
            />
          </div>
        </fieldset>

        <Button loading={submitting} variant="primary" size="md" fullWidth
          type="submit"

          disabled={submitting}

        >
          {t("registration.addAddress")}
        </Button>
      </form>
    </div>
  );
}
