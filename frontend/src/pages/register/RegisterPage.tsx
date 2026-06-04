/**
 * 顧客登録ページ（公開・認証不要）。ADR-SA-03。
 *
 * URL: /register?token=...
 * 担当者が発行したトークンで顧客が住所・連絡先を自分で登録する。
 * テナントはトークンから確定（フォーム入力ではなく構造で分離）。
 */

import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

interface TokenInfo {
  valid: boolean;
  company_name: string | null;
  lead_id: number | null;
  token_type: string | null;
}

interface AddressForm {
  address_type: string;
  branch_name: string;
  name: string;
  email: string;
  telephone: string;
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
  branch_name: "",
  name: "",
  email: "",
  telephone: "",
  tax_id: "",
  address_line_1: "",
  address_line_2: "",
  address_line_3: "",
  city: "",
  state: "",
  zip: "",
  country_code: "JP",
  is_default: false,
});

export default function RegisterPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [loading, setLoading] = useState(true);
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // Form state
  const [billingAddress, setBillingAddress] = useState<AddressForm>(emptyAddress("billing"));
  const [deliveryAddress, setDeliveryAddress] = useState<AddressForm>(emptyAddress("delivery"));
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    const addresses = [billingAddress, deliveryAddress].filter(
      (a) => a.address_line_1 || a.city || a.name
    );

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
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || t("registration.submitError"));
      }

      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("registration.submitError"));
    } finally {
      setSubmitting(false);
    }
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

  return (
    <div className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
      <h1>{t("registration.title")}</h1>
      {tokenInfo?.company_name && (
        <p style={{ color: "var(--text-secondary)", marginBottom: "var(--spacing-4)" }}>
          {t("registration.companyLabel")}: {tokenInfo.company_name}
        </p>
      )}

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Billing Address */}
        <fieldset style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" }}>
          <legend>{t("registration.billingAddress")}</legend>
          <AddressFields
            address={billingAddress}
            onChange={updateBilling}
          />
        </fieldset>

        {/* Delivery Address */}
        <fieldset style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" }}>
          <legend>{t("registration.deliveryAddress")}</legend>
          <AddressFields
            address={deliveryAddress}
            onChange={updateDelivery}
          />
        </fieldset>

        {/* Contact Info */}
        <fieldset style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" }}>
          <legend>{t("registration.contactInfo")}</legend>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            <label>
              {t("registration.contactName")}
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

function AddressFields({
  address,
  onChange,
}: {
  address: AddressForm;
  onChange: (field: keyof AddressForm, value: string | boolean) => void;
}) {
  const { t } = useTranslation();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
      <label>
        {t("registration.branchName")}
        <input
          type="text"
          className="input"
          value={address.branch_name}
          onChange={(e) => onChange("branch_name", e.target.value)}
        />
      </label>
      <label>
        {t("registration.name")}
        <input
          type="text"
          className="input"
          value={address.name}
          onChange={(e) => onChange("name", e.target.value)}
        />
      </label>
      <label>
        {t("registration.email")}
        <input
          type="email"
          className="input"
          value={address.email}
          onChange={(e) => onChange("email", e.target.value)}
        />
      </label>
      <label>
        {t("registration.telephone")}
        <input
          type="tel"
          className="input"
          value={address.telephone}
          onChange={(e) => onChange("telephone", e.target.value)}
        />
      </label>
      <label>
        {t("registration.taxId")}
        <input
          type="text"
          className="input"
          value={address.tax_id}
          onChange={(e) => onChange("tax_id", e.target.value)}
        />
      </label>
      <label>
        {t("registration.addressLine1")}
        <input
          type="text"
          className="input"
          value={address.address_line_1}
          onChange={(e) => onChange("address_line_1", e.target.value)}
        />
      </label>
      <label>
        {t("registration.addressLine2")}
        <input
          type="text"
          className="input"
          value={address.address_line_2}
          onChange={(e) => onChange("address_line_2", e.target.value)}
        />
      </label>
      <label>
        {t("registration.addressLine3")}
        <input
          type="text"
          className="input"
          value={address.address_line_3}
          onChange={(e) => onChange("address_line_3", e.target.value)}
        />
      </label>
      <div style={{ display: "flex", gap: "var(--spacing-3)" }}>
        <label style={{ flex: 1 }}>
          {t("registration.city")}
          <input
            type="text"
            className="input"
            value={address.city}
            onChange={(e) => onChange("city", e.target.value)}
          />
        </label>
        <label style={{ flex: 1 }}>
          {t("registration.state")}
          <input
            type="text"
            className="input"
            value={address.state}
            onChange={(e) => onChange("state", e.target.value)}
          />
        </label>
      </div>
      <div style={{ display: "flex", gap: "var(--spacing-3)" }}>
        <label style={{ flex: 1 }}>
          {t("registration.zip")}
          <input
            type="text"
            className="input"
            value={address.zip}
            onChange={(e) => onChange("zip", e.target.value)}
          />
        </label>
        <label style={{ flex: 1 }}>
          {t("registration.countryCode")}
          <input
            type="text"
            className="input"
            value={address.country_code}
            onChange={(e) => onChange("country_code", e.target.value)}
          />
        </label>
      </div>
    </div>
  );
}
