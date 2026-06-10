/**
 * ContactFormFields — 担当者クイック編集フォーム（Drawer用 6項目）
 *
 * ContactsPage（Drawer内）で使用する要点フィールド。
 * 全項目は ContactEditPage を参照。
 */

import { useTranslation } from "react-i18next";

export interface ContactFormState {
  company_id: string;
  surname: string;
  given_name: string;
  primary_email: string;
  primary_phone: string;
  status: string;
}

export interface ContactCompany {
  id: number;
  company_code: string;
  name: string;
}

interface Props {
  form: ContactFormState;
  onChange: (field: keyof ContactFormState, value: string) => void;
  companies: ContactCompany[];
}

export function ContactFormFields({ form, onChange, companies }: Props) {
  const { t } = useTranslation();
  return (
    <>
      <div className="form-group">
        <label>{t("contacts.companyLabel")}</label>
        <select
          required
          value={form.company_id}
          onChange={(e) => onChange("company_id", e.target.value)}
        >
          <option value="">{t("common.pleaseSelect")}</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}（{c.company_code}）
            </option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label>{t("contacts.surname")}</label>
        <input
          value={form.surname}
          onChange={(e) => onChange("surname", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("contacts.givenName")}</label>
        <input
          value={form.given_name}
          onChange={(e) => onChange("given_name", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("common.email")}</label>
        <input
          type="email"
          value={form.primary_email}
          onChange={(e) => onChange("primary_email", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("common.phone")}</label>
        <input
          value={form.primary_phone}
          onChange={(e) => onChange("primary_phone", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("common.status")}</label>
        <select
          value={form.status}
          onChange={(e) => onChange("status", e.target.value)}
        >
          <option value="active">active</option>
          <option value="inactive">inactive</option>
          <option value="archived">archived</option>
          <option value="pending_dedup_review">{t("contacts.statusPendingDedupOption")}</option>
        </select>
      </div>
    </>
  );
}
