/**
 * TenantPolicyPage (ADR-106: tenant policy settings)
 *
 * Tenant admin can configure inventory aggregation filter, quote validity,
 * currency, document language, duty incoterms, and issue mode.
 *
 * Permissions:
 *   tenant.profile.view - view
 *   tenant.profile.edit - save
 *
 * Related:
 *   backend/app/routers/tenant_policy.py
 *   migrations/20260604_050000_add_tenant_policy_columns.sql
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";

interface TenantPolicy {
  inventory_agg_filter: "none" | "cheapest" | "balanced";
  agg_price_threshold_jpy: number;
  agg_qty_threshold: number;
  quote_validity_days: number;
  default_currency: string;
  document_language: string;
  duty_incoterms: "DAP" | "DDU" | "DDP";
  issue_mode: "paypal_auto" | "paypal_manual" | "pdf" | "wise_pdf";
}

interface FormState {
  inventory_agg_filter: string;
  agg_price_threshold_jpy: string;
  agg_qty_threshold: string;
  quote_validity_days: string;
  default_currency: string;
  document_language: string;
  duty_incoterms: string;
  issue_mode: string;
}

const emptyForm: FormState = {
  inventory_agg_filter: "none",
  agg_price_threshold_jpy: "0",
  agg_qty_threshold: "0",
  quote_validity_days: "1",
  default_currency: "JPY",
  document_language: "en",
  duty_incoterms: "DAP",
  issue_mode: "pdf",
};

export default function TenantPolicyPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();

  const backAction = (
    <button
      type="button"
      className="btn-secondary"
      onClick={() => navigate(-1)}
      data-testid="tenant-policy-back"
    >
      {t("common.back")}
    </button>
  );

  const [form, setForm] = useState<FormState>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const canView = hasPermission("tenant.profile.view");
  const canEdit = hasPermission("tenant.profile.edit");

  useEffect(() => {
    let alive = true;
    const fetchPolicy = async () => {
      try {
        const data = await api.get<TenantPolicy>("/admin/tenant-policy");
        if (!alive) return;
        setForm({
          inventory_agg_filter: data.inventory_agg_filter,
          agg_price_threshold_jpy: String(data.agg_price_threshold_jpy),
          agg_qty_threshold: String(data.agg_qty_threshold),
          quote_validity_days: String(data.quote_validity_days),
          default_currency: data.default_currency,
          document_language: data.document_language,
          duty_incoterms: data.duty_incoterms,
          issue_mode: data.issue_mode,
        });
      } catch (e) {
        if (alive)
          setError(e instanceof Error ? e.message : t("common.fetchError"));
      } finally {
        if (alive) setLoading(false);
      }
    };
    if (canView) fetchPolicy();
    else setLoading(false);
    return () => {
      alive = false;
    };
  }, [canView, t]);

  const handleChange =
    (key: keyof FormState) =>
    (
      e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
    ) => {
      setForm((prev) => ({ ...prev, [key]: e.target.value }));
    };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setSaving(true);
    try {
      const payload = {
        inventory_agg_filter: form.inventory_agg_filter,
        agg_price_threshold_jpy: Number(form.agg_price_threshold_jpy),
        agg_qty_threshold: Number(form.agg_qty_threshold),
        quote_validity_days: Number(form.quote_validity_days),
        default_currency: form.default_currency,
        document_language: form.document_language,
        duty_incoterms: form.duty_incoterms,
        issue_mode: form.issue_mode,
      };
      await api.put("/admin/tenant-policy", payload);
      setInfo(t("tenantPolicy.saved"));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("common.operationError"),
      );
    } finally {
      setSaving(false);
    }
  };

  if (!canView) {
    return (
      <PageLayout navKey="nav.tenantPolicy" headerAction={backAction}>
        <div className="error-message">
          {t("tenantPolicy.permissionRequired")}
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      navKey="nav.tenantPolicy"
      subtitleKey="tenantPolicy.subtitle"
      headerAction={backAction}
    >
      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <form
          className="form"
          onSubmit={handleSave}
          data-testid="tenant-policy-form"
        >
          {error && <div className="error-message">{error}</div>}
          {info && (
            <div className="info-message" data-testid="tenant-policy-info">
              {info}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="tp-agg-filter">
              {t("tenantPolicy.inventoryAggFilter")}
            </label>
            <select
              id="tp-agg-filter"
              data-testid="tp-agg-filter"
              value={form.inventory_agg_filter}
              onChange={handleChange("inventory_agg_filter")}
              disabled={!canEdit}
            >
              <option value="none">
                {t("tenantPolicy.inventoryAggFilterNone")}
              </option>
              <option value="cheapest">
                {t("tenantPolicy.inventoryAggFilterCheapest")}
              </option>
              <option value="balanced">
                {t("tenantPolicy.inventoryAggFilterBalanced")}
              </option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="tp-price-threshold">
              {t("tenantPolicy.aggPriceThresholdJpy")}
            </label>
            <input
              id="tp-price-threshold"
              data-testid="tp-price-threshold"
              type="number"
              min={0}
              value={form.agg_price_threshold_jpy}
              onChange={handleChange("agg_price_threshold_jpy")}
              disabled={!canEdit}
            />
          </div>

          <div className="form-group">
            <label htmlFor="tp-qty-threshold">
              {t("tenantPolicy.aggQtyThreshold")}
            </label>
            <input
              id="tp-qty-threshold"
              data-testid="tp-qty-threshold"
              type="number"
              min={0}
              value={form.agg_qty_threshold}
              onChange={handleChange("agg_qty_threshold")}
              disabled={!canEdit}
            />
          </div>

          <div className="form-group">
            <label htmlFor="tp-validity-days">
              {t("tenantPolicy.quoteValidityDays")}
            </label>
            <input
              id="tp-validity-days"
              data-testid="tp-validity-days"
              type="number"
              min={1}
              max={365}
              value={form.quote_validity_days}
              onChange={handleChange("quote_validity_days")}
              disabled={!canEdit}
            />
          </div>

          <div className="form-group">
            <label htmlFor="tp-currency">
              {t("tenantPolicy.defaultCurrency")}
            </label>
            <input
              id="tp-currency"
              data-testid="tp-currency"
              type="text"
              maxLength={10}
              value={form.default_currency}
              onChange={handleChange("default_currency")}
              disabled={!canEdit}
            />
          </div>

          <div className="form-group">
            <label htmlFor="tp-doc-language">
              {t("tenantPolicy.documentLanguage")}
            </label>
            <input
              id="tp-doc-language"
              data-testid="tp-doc-language"
              type="text"
              maxLength={10}
              value={form.document_language}
              onChange={handleChange("document_language")}
              disabled={!canEdit}
            />
          </div>

          <div className="form-group">
            <label htmlFor="tp-incoterms">
              {t("tenantPolicy.dutyIncoterms")}
            </label>
            <select
              id="tp-incoterms"
              data-testid="tp-incoterms"
              value={form.duty_incoterms}
              onChange={handleChange("duty_incoterms")}
              disabled={!canEdit}
            >
              <option value="DAP">DAP</option>
              <option value="DDU">DDU</option>
              <option value="DDP">DDP</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="tp-issue-mode">
              {t("tenantPolicy.issueMode")}
            </label>
            <select
              id="tp-issue-mode"
              data-testid="tp-issue-mode"
              value={form.issue_mode}
              onChange={handleChange("issue_mode")}
              disabled={!canEdit}
            >
              <option value="paypal_auto">
                {t("tenantPolicy.issueModePaypalAuto")}
              </option>
              <option value="paypal_manual">
                {t("tenantPolicy.issueModePaypalManual")}
              </option>
              <option value="pdf">{t("tenantPolicy.issueModePdf")}</option>
              <option value="wise_pdf">
                {t("tenantPolicy.issueModeWisePdf")}
              </option>
            </select>
          </div>

          {canEdit && (
            <div className="form-actions">
              <button
                type="submit"
                className="btn-primary"
                disabled={saving}
                data-testid="tenant-policy-save"
              >
                {saving ? t("common.saving") : t("common.save")}
              </button>
            </div>
          )}
        </form>
      )}
    </PageLayout>
  );
}
