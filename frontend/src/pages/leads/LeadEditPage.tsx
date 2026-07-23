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
import { CountryCombobox } from "../../components/CountryCombobox";
import { ChannelTypeCombobox } from "../../components/ChannelTypeCombobox";
import { Select } from "../../components/Select";
import { api } from "../../lib/api";
import { LEAD_STATUS_CODES, type LeadStatusCode } from "../../constants/leadStatus";
import { getCloseReasons, type CloseReasonResponse } from "../../api/closeReasons";
import { LostReasonFields, buildLostReasonUpdatePayload } from "./LeadFormFields";

interface Lead {
  id: number;
  customer_name: string;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  channel_type: string | null;
  initiative: string | null;
  type: string | null;
  status: string;
  temperature: string | null;
  estimated_scale: string | null;
  customer_type: string | null;
  response_speed: string | null;
  monthly_forecast: number | null;
  notes: string | null;
  country: string | null;
}

type FormState = {
  customer_name: string;
  company_name: string;
  email: string;
  phone: string;
  channel_type: string;
  initiative: string;
  type: string;
  status: string;
  temperature: string;
  estimated_scale: string;
  customer_type: string;
  response_speed: string;
  monthly_forecast: string;
  notes: string;
  country: string;
  close_reason_id: string;
  close_reason_memo: string;
};

const emptyForm: FormState = {
  customer_name: "", company_name: "", email: "", phone: "",
  channel_type: "", initiative: "", type: "", status: "lead", temperature: "",
  estimated_scale: "", customer_type: "", response_speed: "",
  monthly_forecast: "", notes: "", country: "",
  close_reason_id: "", close_reason_memo: "",
};

const LEAD_STATUSES: LeadStatusCode[] = [...LEAD_STATUS_CODES];

export default function LeadEditPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [closeReasonOptions, setCloseReasonOptions] = useState<CloseReasonResponse[]>([]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    const load = async () => {
      try {
        const lead = await api.get<Lead>(`/leads/${id}`);
        if (cancelled) return;
        setForm({
          customer_name: lead.customer_name,
          company_name: lead.company_name || "",
          email: lead.email || "",
          phone: lead.phone || "",
          channel_type: lead.channel_type || "",
          initiative: lead.initiative || "",
          type: lead.type || "",
          status: lead.status,
          temperature: lead.temperature || "",
          estimated_scale: lead.estimated_scale || "",
          customer_type: lead.customer_type || "",
          response_speed: lead.response_speed || "",
          monthly_forecast: lead.monthly_forecast != null ? String(lead.monthly_forecast) : "",
          notes: lead.notes || "",
          country: lead.country || "",
          close_reason_id: "",
          close_reason_memo: "",
        });
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : t("common.fetchError"));
        if (!cancelled) setLoading(false);
        return;
      }

      try {
        const reasons = await getCloseReasons("lost");
        if (!cancelled) setCloseReasonOptions(reasons);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : t("common.fetchError"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [id, t]);

  const toNull = (v: string) => (v ? v : null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const lostReasonPayload = buildLostReasonUpdatePayload(
        form.status,
        form.close_reason_id,
        form.close_reason_memo,
      );
      await api.patch(`/leads/${id}`, {
        customer_name: form.customer_name,
        company_name: toNull(form.company_name),
        email: toNull(form.email),
        phone: toNull(form.phone),
        channel_type: toNull(form.channel_type),
        initiative: toNull(form.initiative),
        type: toNull(form.type),
        status: form.status,
        temperature: toNull(form.temperature),
        estimated_scale: toNull(form.estimated_scale),
        customer_type: toNull(form.customer_type),
        response_speed: toNull(form.response_speed),
        monthly_forecast: form.monthly_forecast ? Number(form.monthly_forecast) : null,
        notes: toNull(form.notes),
        country: toNull(form.country),
        ...lostReasonPayload,
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
          <div className="form-group"><label>{t("leads.channelType")}</label>
            <ChannelTypeCombobox
              id="lead-channel-type"
              value={form.channel_type}
              onChange={(value) => setForm({ ...form, channel_type: value })}
              placeholder={t("leads.channelTypePlaceholder")}
            />
          </div>
          <Select
            label={t("leads.initiative")}
            value={form.initiative}
            onChange={(e) => setForm({ ...form, initiative: e.target.value })}
            options={[
              { value: "", label: t("common.notSet") },
              { value: "inbound", label: t("leads.initiative_inbound") },
              { value: "outbound", label: t("leads.initiative_outbound") },
            ]}
          />
          <Select
            label={t("leads.type")}
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value })}
            options={[
              { value: "", label: t("common.notSet") },
              { value: "Inbound", label: t("leads.type_inbound") },
              { value: "Outbound", label: t("leads.type_outbound") },
            ]}
          />
          <Select
            label={t("leads.status")}
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
            options={LEAD_STATUSES.map((s) => ({
              value: s,
              label: t(`leads.statusCode.${s}`, { defaultValue: s }),
            }))}
          />
          <LostReasonFields
            status={form.status}
            closeReasonId={form.close_reason_id}
            closeReasonMemo={form.close_reason_memo}
            closeReasonOptions={closeReasonOptions}
            onCloseReasonIdChange={(value) => setForm({ ...form, close_reason_id: value })}
            onCloseReasonMemoChange={(value) => setForm({ ...form, close_reason_memo: value })}
          />
          <Select
            label={t("leads.temperature")}
            value={form.temperature}
            onChange={(e) => setForm({ ...form, temperature: e.target.value })}
            options={[
              { value: "", label: t("common.notSet") },
              { value: "Hot", label: t("leads.temp_hot") },
              { value: "Warm", label: t("leads.temp_warm") },
              { value: "Cold", label: t("leads.temp_cold") },
            ]}
          />
          <Select
            label={t("leads.estimatedScale")}
            value={form.estimated_scale}
            onChange={(e) => setForm({ ...form, estimated_scale: e.target.value })}
            options={[
              { value: "", label: t("common.notSet") },
              { value: "Small", label: t("leads.scale_small") },
              { value: "Medium", label: t("leads.scale_medium") },
              { value: "Large", label: t("leads.scale_large") },
            ]}
          />
          <Select
            label={t("leads.customerType")}
            value={form.customer_type}
            onChange={(e) => setForm({ ...form, customer_type: e.target.value })}
            options={[
              { value: "", label: t("common.notSet") },
              // eslint-disable-next-line local/no-japanese-literal -- DB value
              { value: "信頼重視", label: t("leads.customerType_trust") },
              // eslint-disable-next-line local/no-japanese-literal -- DB value
              { value: "価格重視", label: t("leads.customerType_price") },
            ]}
          />
          <Select
            label={t("leads.responseSpeed")}
            value={form.response_speed}
            onChange={(e) => setForm({ ...form, response_speed: e.target.value })}
            options={[
              { value: "", label: t("common.notSet") },
              // eslint-disable-next-line local/no-japanese-literal -- DB value
              { value: "24h以内", label: t("leads.responseSpeed_24h") },
              // eslint-disable-next-line local/no-japanese-literal -- DB value
              { value: "3日以内", label: t("leads.responseSpeed_3days") },
              // eslint-disable-next-line local/no-japanese-literal -- DB value
              { value: "3日超", label: t("leads.responseSpeed_over3days") },
            ]}
          />
          <div className="form-group"><label>{t("leads.monthlyForecast")}</label>
            <input type="number" min="0" step="1" value={form.monthly_forecast} onChange={(e) => setForm({ ...form, monthly_forecast: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.notes")}</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.country")}</label>
            <CountryCombobox
              id="lead-country"
              value={form.country}
              onChange={(value) => setForm({ ...form, country: value })}
              placeholder={t("common.search")}
            />
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
