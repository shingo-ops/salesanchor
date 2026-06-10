/**
 * LeadFormFields — リードクイック編集フォーム（Drawer用 6項目）
 *
 * LeadsPage（Drawer内）で使用する要点フィールド。
 * 全項目は LeadEditPage を参照。
 */

import { useTranslation } from "react-i18next";
import { LEAD_STATUS_CODES, type LeadStatusCode } from "../../constants/leadStatus";

export interface LeadFormState {
  customer_name: string;
  email: string;
  phone: string;
  status: string;
  type: string;
  notes: string;
}

interface Props {
  form: LeadFormState;
  onChange: (field: keyof LeadFormState, value: string) => void;
}

const LEAD_STATUSES: LeadStatusCode[] = [...LEAD_STATUS_CODES];

export function LeadFormFields({ form, onChange }: Props) {
  const { t } = useTranslation();
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
      <div className="form-group">
        <label>{t("leads.status")}</label>
        <select
          value={form.status}
          onChange={(e) => onChange("status", e.target.value)}
        >
          {LEAD_STATUSES.map((s) => (
            <option key={s} value={s}>{t(`leads.statusCode.${s}`, { defaultValue: s })}</option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label>{t("leads.type")}</label>
        <select
          value={form.type}
          onChange={(e) => onChange("type", e.target.value)}
        >
          <option value="">{t("common.notSet")}</option>
          <option value="Inbound">{t("leads.type_inbound")}</option>
          <option value="Outbound">{t("leads.type_outbound")}</option>
        </select>
      </div>
      <div className="form-group">
        <label>{t("leads.notes")}</label>
        <textarea
          value={form.notes}
          onChange={(e) => onChange("notes", e.target.value)}
        />
      </div>
    </>
  );
}
