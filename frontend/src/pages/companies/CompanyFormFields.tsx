/**
 * CompanyFormFields — 会社クイック編集フォーム（Drawer用 6項目）
 *
 * CompaniesPage（Drawer内）で使用する要点フィールド。
 * 全項目は CompanyDetailPage を参照。
 */

import { useTranslation } from "react-i18next";
import { Select } from "../../components/Select";

export interface CompanyFormState {
  name: string;
  status: string;
  industry: string;
  priority_focus: string;
  notes: string;
}

interface Props {
  form: CompanyFormState;
  onChange: (field: keyof CompanyFormState, value: string) => void;
}

export function CompanyFormFields({ form, onChange }: Props) {
  const { t } = useTranslation();
  const statusOptions = [
    { value: "active", label: t("customers.status_active") },
    { value: "inactive", label: t("customers.status_inactive") },
    { value: "archived", label: t("customers.status_archived") },
    { value: "pending_dedup_review", label: t("customers.status_pending_dedup") },
  ];
  return (
    <>
      <div className="form-group">
        <label>{t("companies.nameLabel")}</label>
        <input
          required
          value={form.name}
          onChange={(e) => onChange("name", e.target.value)}
        />
      </div>
      <Select
        label={t("common.status")}
        value={form.status}
        onChange={(e) => onChange("status", e.target.value)}
        options={statusOptions}
      />
      <div className="form-group">
        <label>{t("companies.industry")}</label>
        <input
          value={form.industry}
          onChange={(e) => onChange("industry", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("companies.priorityFocus")}</label>
        <input
          value={form.priority_focus}
          onChange={(e) => onChange("priority_focus", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("common.notes")}</label>
        <textarea
          value={form.notes}
          onChange={(e) => onChange("notes", e.target.value)}
        />
      </div>
    </>
  );
}
