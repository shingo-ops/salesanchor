/**
 * 住所追加ページ（公開・認証不要）。ADR-SA-03。
 *
 * URL: /register/address?token=...
 * 既存の住所を上書きせず、新しい住所を追加する。
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

const emptyAddress = (): AddressForm => ({
  address_type: "delivery",
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

export default function RegisterAddressPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

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
          address,
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
        <h1>{t("registration.addressAddedTitle")}</h1>
        <p>{t("registration.addressAddedMessage")}</p>
      </div>
    );
  }

  const updateField = (field: keyof AddressForm, value: string | boolean) =>
    setAddress((prev) => ({ ...prev, [field]: value }));

  return (
    <div className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
      <h1>{t("registration.addAddressTitle")}</h1>
      {tokenInfo?.company_name && (
        <p style={{ color: "var(--text-secondary)", marginBottom: "var(--spacing-4)" }}>
          {t("registration.companyLabel")}: {tokenInfo.company_name}
        </p>
      )}

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit}>
        <fieldset style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" }}>
          <legend>{t("registration.addressDetails")}</legend>
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
            <label>
              {t("registration.branchName")}
              <input
                type="text"
                className="input"
                value={address.branch_name}
                onChange={(e) => updateField("branch_name", e.target.value)}
              />
            </label>
            <label>
              {t("registration.name")}
              <input
                type="text"
                className="input"
                value={address.name}
                onChange={(e) => updateField("name", e.target.value)}
              />
            </label>
            <label>
              {t("registration.email")}
              <input
                type="email"
                className="input"
                value={address.email}
                onChange={(e) => updateField("email", e.target.value)}
              />
            </label>
            <label>
              {t("registration.telephone")}
              <input
                type="tel"
                className="input"
                value={address.telephone}
                onChange={(e) => updateField("telephone", e.target.value)}
              />
            </label>
            <label>
              {t("registration.taxId")}
              <input
                type="text"
                className="input"
                value={address.tax_id}
                onChange={(e) => updateField("tax_id", e.target.value)}
              />
            </label>
            <label>
              {t("registration.addressLine1")}
              <input
                type="text"
                className="input"
                value={address.address_line_1}
                onChange={(e) => updateField("address_line_1", e.target.value)}
              />
            </label>
            <label>
              {t("registration.addressLine2")}
              <input
                type="text"
                className="input"
                value={address.address_line_2}
                onChange={(e) => updateField("address_line_2", e.target.value)}
              />
            </label>
            <label>
              {t("registration.addressLine3")}
              <input
                type="text"
                className="input"
                value={address.address_line_3}
                onChange={(e) => updateField("address_line_3", e.target.value)}
              />
            </label>
            <div style={{ display: "flex", gap: "var(--spacing-3)" }}>
              <label style={{ flex: 1 }}>
                {t("registration.city")}
                <input
                  type="text"
                  className="input"
                  value={address.city}
                  onChange={(e) => updateField("city", e.target.value)}
                />
              </label>
              <label style={{ flex: 1 }}>
                {t("registration.state")}
                <input
                  type="text"
                  className="input"
                  value={address.state}
                  onChange={(e) => updateField("state", e.target.value)}
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
                  onChange={(e) => updateField("zip", e.target.value)}
                />
              </label>
              <label style={{ flex: 1 }}>
                {t("registration.countryCode")}
                <input
                  type="text"
                  className="input"
                  value={address.country_code}
                  onChange={(e) => updateField("country_code", e.target.value)}
                />
              </label>
            </div>
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
