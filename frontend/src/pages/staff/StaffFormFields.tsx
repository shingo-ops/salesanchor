/**
 * StaffFormFields — スタッフクイック編集フォーム（Drawer用 6項目）
 *
 * StaffPage（Drawer内）で使用する要点フィールド。
 * 全項目は StaffEditPage を参照。
 */

import { useTranslation } from "react-i18next";

export interface StaffFormState {
  surname_jp: string;
  given_name_jp: string;
  primary_email: string;
  role_id: string;
  status: string;
  discord_user_id: string;
}

export interface StaffRole {
  id: number;
  name: string;
}

interface Props {
  form: StaffFormState;
  onChange: (field: keyof StaffFormState, value: string) => void;
  roles: StaffRole[];
}

export function StaffFormFields({ form, onChange, roles }: Props) {
  const { t } = useTranslation();
  return (
    <>
      <div className="form-group">
        <label>{t("staff.surnameJp")} *</label>
        <input
          required
          value={form.surname_jp}
          onChange={(e) => onChange("surname_jp", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("staff.givenNameJp")} *</label>
        <input
          required
          value={form.given_name_jp}
          onChange={(e) => onChange("given_name_jp", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("staff.primaryEmail")} *</label>
        <input
          required
          type="email"
          value={form.primary_email}
          onChange={(e) => onChange("primary_email", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("staff.role")} *</label>
        <select
          required
          value={form.role_id}
          onChange={(e) => onChange("role_id", e.target.value)}
        >
          <option value="">{t("common.pleaseSelect")}</option>
          {roles.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label>{t("staff.status")}</label>
        <select
          value={form.status}
          onChange={(e) => onChange("status", e.target.value)}
        >
          <option value="active">{t("staff.status_active")}</option>
          <option value="inactive">{t("staff.status_inactive")}</option>
          <option value="pending">{t("staff.status_pending")}</option>
        </select>
      </div>
      <div className="form-group">
        <label>Discord ID</label>
        <input
          value={form.discord_user_id}
          onChange={(e) => onChange("discord_user_id", e.target.value)}
        />
      </div>
    </>
  );
}
