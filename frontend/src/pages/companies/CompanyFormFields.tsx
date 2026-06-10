/**
 * CompanyFormFields — 会社クイック編集フォーム（Drawer用 6項目）
 *
 * CompaniesPage（Drawer内）で使用する要点フィールド。
 * 全項目は CompanyDetailPage を参照。
 */

import { useTranslation } from "react-i18next";

export interface CompanyFormState {
  name: string;
  status: string;
  industry: string;
  trust_level: string;
  priority_focus: string;
  notes: string;
}

interface Props {
  form: CompanyFormState;
  onChange: (field: keyof CompanyFormState, value: string) => void;
}

export function CompanyFormFields({ form, onChange }: Props) {
  const { t } = useTranslation();
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
      <div className="form-group">
        <label>{t("common.status")}</label>
        <select
          value={form.status}
          onChange={(e) => onChange("status", e.target.value)}
        >
          <option value="active">active</option>
          <option value="inactive">inactive</option>
          <option value="archived">archived</option>
          <option value="pending_dedup_review">pending_dedup_review</option>
        </select>
      </div>
      <div className="form-group">
        <label>{t("companies.industry")}</label>
        <input
          value={form.industry}
          onChange={(e) => onChange("industry", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("companies.trustLevel")}</label>
        <input
          type="number"
          min="0"
          max="5"
          value={form.trust_level}
          onChange={(e) => onChange("trust_level", e.target.value)}
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
