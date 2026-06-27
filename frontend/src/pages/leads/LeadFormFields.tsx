/**
 * LeadFormFields — リードクイック編集フォーム（Drawer用 7項目）
 *
 * LeadsPage（Drawer内）で使用する要点フィールド。
 * 全項目は LeadEditPage を参照。
 */

import { useTranslation } from "react-i18next";
import { CountryCombobox } from "../../components/CountryCombobox";
import { Select } from "../../components/Select";
import { LEAD_STATUS_CODES, type LeadStatusCode } from "../../constants/leadStatus";

export interface LeadFormState {
  customer_name: string;
  email: string;
  phone: string;
  status: string;
  type: string;
  notes: string;
  country: string;
}

interface Props {
  form: LeadFormState;
  onChange: (field: keyof LeadFormState, value: string) => void;
}

const LEAD_STATUSES: LeadStatusCode[] = [...LEAD_STATUS_CODES];

export function LeadFormFields({ form, onChange }: Props) {
  const { t } = useTranslation();
  const statusOptions = LEAD_STATUSES.map((s) => ({
    value: s,
    label: t(`leads.statusCode.${s}`, { defaultValue: s }),
  }));
  const typeOptions = [
    { value: "Inbound", label: t("leads.type_inbound") },
    { value: "Outbound", label: t("leads.type_outbound") },
  ];
  return (
    <>
      <div className="form-group">
        <label>{t("leads.customerName")} *</label>
        <input
          required
          value={form.customer_name}
          onChange={(e) => onChange("customer_name", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("leads.email")}</label>
        <input
          type="email"
          value={form.email}
          onChange={(e) => onChange("email", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("leads.phone")}</label>
        <input
          value={form.phone}
          onChange={(e) => onChange("phone", e.target.value)}
        />
      </div>
      <Select
        label={t("leads.status")}
        value={form.status}
        onChange={(e) => onChange("status", e.target.value)}
        options={statusOptions}
      />
      <Select
        label={t("leads.type")}
        value={form.type}
        onChange={(e) => onChange("type", e.target.value)}
        options={typeOptions}
        placeholder={t("common.notSet")}
      />
      <div className="form-group">
        <label>{t("leads.notes")}</label>
        <textarea
          value={form.notes}
          onChange={(e) => onChange("notes", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("leads.country")}</label>
        <CountryCombobox
          id="lead-form-country"
          value={form.country}
          onChange={(value) => onChange("country", value)}
          placeholder={t("common.search")}
        />
      </div>
    </>
  );
}
