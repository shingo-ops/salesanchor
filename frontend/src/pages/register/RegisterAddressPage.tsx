/**
 * Address Addition Page (public, no auth). ADR-SA-03 + ADR-126 v2.
 *
 * URL: /register/address?token=...
 * Appends a new address to the existing company (does not overwrite).
 * Displays in English by default (ADR-126 Section 4).
 */

import { useState, useEffect, useMemo, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { COUNTRIES, type CountryEntry } from "../../constants/countries";

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

/** Combobox with search filtering for country / dial code selection. */
function CountryCombobox({
  entries,
  value,
  onChange,
  displayFn,
  filterFn,
  id,
}: {
  entries: readonly CountryEntry[];
  value: string;
  onChange: (val: string) => void;
  displayFn: (c: CountryEntry) => string;
  filterFn: (c: CountryEntry, q: string) => boolean;
  id: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtered = useMemo(
    () => (query ? entries.filter((c) => filterFn(c, query.toLowerCase())) : entries),
    [entries, query, filterFn],
  );

  const selectedDisplay = useMemo(() => {
    const found = entries.find((c) => displayFn(c) === value || c.code === value || c.dial === value);
    return found ? displayFn(found) : value;
  }, [entries, value, displayFn]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <input
        id={id}
        type="text"
        className="input"
        value={open ? query : selectedDisplay}
        onChange={(e) => {
          setQuery(e.target.value);
          if (!open) setOpen(true);
        }}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        autoComplete="off"
      />
      {open && filtered.length > 0 && (
        <ul
          style={{
            position: "absolute",
            zIndex: 10,
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            maxHeight: "200px",
            overflow: "auto",
            width: "100%",
            margin: 0,
            padding: 0,
            listStyle: "none",
          }}
        >
          {filtered.map((c) => (
            <li
              key={c.code + c.dial}
              style={{
                padding: "var(--spacing-2) var(--spacing-3)",
                cursor: "pointer",
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(displayFn(c));
                setOpen(false);
                setQuery("");
              }}
            >
              {displayFn(c)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
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
        <h1>{t("registration.addressAddedTitle")}</h1>
        <p>{t("registration.addressAddedMessage")}</p>
      </div>
    );
  }

  const updateField = (field: keyof AddressForm, value: string | boolean) =>
    setAddress((prev) => ({ ...prev, [field]: value }));

  const requiredMark = <span style={{ color: "var(--color-red-500)", fontWeight: "var(--font-weight-bold)" }}>*</span>;

  return (
    <div className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
      {/* Language toggle */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "var(--spacing-3)" }}>
        <button type="button" className="btn btn-ghost" onClick={toggleLang} style={{ fontSize: "var(--font-size-sm)" }}>
          {currentLang === "en" ? t("registration.switchToJapanese") : t("registration.switchToEnglish")}
        </button>
      </div>

      <h1>{t("registration.addAddressTitle")}</h1>
      {tokenInfo?.company_name && (
        <p style={{ color: "var(--text-secondary)", marginBottom: "var(--spacing-4)" }}>
          {t("registration.companyLabel")}: {tokenInfo.company_name}
        </p>
      )}

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit}>
        <fieldset style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" }}>
          <legend style={{ fontWeight: "var(--font-weight-bold)" }}>{t("registration.addressDetails")}</legend>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)", marginBottom: "var(--spacing-3)" }}>
            <label>
              {t("registration.addressType")}
              <select
                className="input"
                value={address.address_type}
                onChange={(e) => updateField("address_type", e.target.value)}
              >
                <option value="billing">{t("registration.billingAddress")}</option>
                <option value="delivery">{t("registration.deliveryAddress")}</option>
              </select>
            </label>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            {/* Recipient Name */}
            <label>
              {t("registration.recipientName")} {requiredMark}
              <input
                type="text"
                className="input"
                value={address.name}
                onChange={(e) => updateField("name", e.target.value)}
              />
            </label>

            {/* Telephone (dial code + number) */}
            <label>{t("registration.telephone")}</label>
            <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
              <div style={{ width: "140px", flexShrink: 0 }}>
                <CountryCombobox
                  entries={COUNTRIES}
                  value={address.telephone_dial}
                  onChange={(val) => {
                    const found = COUNTRIES.find((c) => `${c.dial} ${c.code}` === val);
                    updateField("telephone_dial", found ? found.dial : val);
                  }}
                  displayFn={(c) => `${c.dial} ${c.code}`}
                  filterFn={(c, q) =>
                    c.name.toLowerCase().includes(q) ||
                    c.code.toLowerCase().includes(q) ||
                    c.dial.includes(q)
                  }
                  id="address-dial"
                />
              </div>
              <input
                type="tel"
                className="input"
                style={{ flex: 1 }}
                value={address.telephone_number}
                onChange={(e) => updateField("telephone_number", e.target.value.replace(/[^\d]/g, ""))}
                placeholder="1234567890"
              />
            </div>

            {/* Email */}
            <label>
              {t("registration.shippingEmail")}
              <input
                type="email"
                className="input"
                value={address.email}
                onChange={(e) => updateField("email", e.target.value)}
              />
            </label>

            {/* Tax ID */}
            <label>
              {t("registration.taxIdFull")}
              <input
                type="text"
                className="input"
                value={address.tax_id}
                onChange={(e) => updateField("tax_id", e.target.value)}
              />
            </label>

            {/* Address Line 1 */}
            <label>
              {t("registration.addressLine1")} {requiredMark}
              <input
                type="text"
                className="input"
                value={address.address_line_1}
                onChange={(e) => updateField("address_line_1", e.target.value)}
              />
            </label>

            {/* Address Line 2 */}
            <label>
              {t("registration.addressLine2")}
              <input
                type="text"
                className="input"
                value={address.address_line_2}
                onChange={(e) => updateField("address_line_2", e.target.value)}
              />
            </label>

            {/* Address Line 3 */}
            <label>
              {t("registration.addressLine3")}
              <input
                type="text"
                className="input"
                value={address.address_line_3}
                onChange={(e) => updateField("address_line_3", e.target.value)}
              />
            </label>

            {/* City */}
            <label>
              {t("registration.city")}
              <input
                type="text"
                className="input"
                value={address.city}
                onChange={(e) => updateField("city", e.target.value)}
              />
            </label>

            {/* State */}
            <label>
              {t("registration.state")}
              <input
                type="text"
                className="input"
                value={address.state}
                onChange={(e) => updateField("state", e.target.value)}
              />
            </label>

            {/* ZIP */}
            <label>
              {t("registration.zip")}
              <input
                type="text"
                className="input"
                value={address.zip}
                onChange={(e) => updateField("zip", e.target.value)}
              />
            </label>

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

        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ width: "100%" }}
        >
          {submitting ? t("common.saving") : t("registration.addAddress")}
        </button>
      </form>
    </div>
  );
}
