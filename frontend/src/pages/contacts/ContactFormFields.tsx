/**
 * ContactFormFields — 担当者クイック編集フォーム（Drawer用 6項目）
 *
 * ContactsPage（Drawer内）で使用する要点フィールド。
 * 全項目は ContactEditPage を参照。
 */

import { useTranslation } from "react-i18next";
import { Select } from "../../components/Select";

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
  const companyOptions = companies.map((c) => ({
    value: String(c.id),
    label: `${c.name}（${c.company_code}）`,
  }));
  const statusOptions = [
    { value: "active", label: t("customers.status_active") },
    { value: "inactive", label: t("customers.status_inactive") },
    { value: "archived", label: t("customers.status_archived") },
    { value: "pending_dedup_review", label: t("contacts.statusPendingDedupOption") },
  ];
  return (
    <>
      <Select
        label={t("contacts.companyLabel")}
        required
        value={form.company_id}
        onChange={(e) => onChange("company_id", e.target.value)}
        options={companyOptions}
        placeholder={t("common.pleaseSelect")}
      />
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
      <Select
        label={t("common.status")}
        value={form.status}
        onChange={(e) => onChange("status", e.target.value)}
        options={statusOptions}
      />
    </>
  );
}
