/**
 * LeadEditPage — リードフルページ編集（/crm/leads/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * 全項目を編集可能。保存後は /crm/leads 一覧へ戻る。
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";
import { LEAD_STATUS_CODES, type LeadStatusCode } from "../../constants/leadStatus";

interface Lead {
  id: number;
  customer_name: string;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  source: string | null;
  type: string | null;
  status: string;
  temperature: string | null;
  estimated_scale: string | null;
  customer_type: string | null;
  response_speed: string | null;
  monthly_forecast: number | null;
  notes: string | null;
}

type FormState = {
  customer_name: string;
  company_name: string;
  email: string;
  phone: string;
  source: string;
  type: string;
  status: string;
  temperature: string;
  estimated_scale: string;
  customer_type: string;
  response_speed: string;
  monthly_forecast: string;
  notes: string;
};

const emptyForm: FormState = {
  customer_name: "", company_name: "", email: "", phone: "",
  source: "", type: "", status: "lead", temperature: "",
  estimated_scale: "", customer_type: "", response_speed: "",
  monthly_forecast: "", notes: "",
};

const LEAD_STATUSES: LeadStatusCode[] = [...LEAD_STATUS_CODES];

export default function LeadEditPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api.get<Lead>(`/leads/${id}`)
      .then((lead) => {
        setForm({
          customer_name: lead.customer_name,
          company_name: lead.company_name || "",
          email: lead.email || "",
          phone: lead.phone || "",
          source: lead.source || "",
          type: lead.type || "",
          status: lead.status,
          temperature: lead.temperature || "",
          estimated_scale: lead.estimated_scale || "",
          customer_type: lead.customer_type || "",
          response_speed: lead.response_speed || "",
          monthly_forecast: lead.monthly_forecast != null ? String(lead.monthly_forecast) : "",
          notes: lead.notes || "",
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("common.fetchError")))
      .finally(() => setLoading(false));
  }, [id, t]);

  const toNull = (v: string) => (v ? v : null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.patch(`/leads/${id}`, {
        customer_name: form.customer_name,
        company_name: toNull(form.company_name),
        email: toNull(form.email),
        phone: toNull(form.phone),
        source: toNull(form.source),
        type: toNull(form.type),
        status: form.status,
        temperature: toNull(form.temperature),
        estimated_scale: toNull(form.estimated_scale),
        customer_type: toNull(form.customer_type),
        response_speed: toNull(form.response_speed),
        monthly_forecast: form.monthly_forecast ? Number(form.monthly_forecast) : null,
        notes: toNull(form.notes),
      });
      navigate("/crm/leads");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <PageLayout navKey="nav.leadsSection" subtitleKey="leads.subtitle">
      {error && <div className="error-message">{error}</div>}
      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <div className="form-group"><label>{t("leads.customerName")} *</label>
            <input required value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.companyName")}</label>
            <input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.email")}</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.phone")}</label>
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.source")}</label>
            <input placeholder={t("leads.sourcePlaceholder")} value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.type")}</label>
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="Inbound">{t("leads.type_inbound")}</option>
              <option value="Outbound">{t("leads.type_outbound")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.status")}</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              {LEAD_STATUSES.map((s) => (
                <option key={s} value={s}>{t(`leads.statusCode.${s}`, { defaultValue: s })}</option>
              ))}
            </select>
          </div>
          <div className="form-group"><label>{t("leads.temperature")}</label>
            <select value={form.temperature} onChange={(e) => setForm({ ...form, temperature: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="Hot">{t("leads.temp_hot")}</option>
              <option value="Warm">{t("leads.temp_warm")}</option>
              <option value="Cold">{t("leads.temp_cold")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.estimatedScale")}</label>
            <select value={form.estimated_scale} onChange={(e) => setForm({ ...form, estimated_scale: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="Small">{t("leads.scale_small")}</option>
              <option value="Medium">{t("leads.scale_medium")}</option>
              <option value="Large">{t("leads.scale_large")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.customerType")}</label>
            <select value={form.customer_type} onChange={(e) => setForm({ ...form, customer_type: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="信頼重視">{t("leads.customerType_trust")}</option>
              <option value="価格重視">{t("leads.customerType_price")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.responseSpeed")}</label>
            <select value={form.response_speed} onChange={(e) => setForm({ ...form, response_speed: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="24h以内">{t("leads.responseSpeed_24h")}</option>
              <option value="3日以内">{t("leads.responseSpeed_3days")}</option>
              <option value="3日超">{t("leads.responseSpeed_over3days")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.monthlyForecast")}</label>
            <input type="number" min="0" step="1" value={form.monthly_forecast} onChange={(e) => setForm({ ...form, monthly_forecast: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.notes")}</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => navigate("/crm/leads")}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
