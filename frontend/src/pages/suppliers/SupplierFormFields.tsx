/**
 * SupplierFormFields — 仕入先フォームフィールド（共通）
 *
 * SuppliersPage（Drawer内）と SupplierEditPage（フルページ）の両方で使用。
 * フォーム状態・onChange のみを受け取り、submit / cancel は呼び出し元が担う。
 */

import { useTranslation } from "react-i18next";

export interface SupplierFormState {
  name: string;
  contact_name: string;
  email: string;
  phone: string;
  address: string;
  notes: string;
}

interface SupplierFormFieldsProps {
  form: SupplierFormState;
  onChange: (field: keyof SupplierFormState, value: string) => void;
}

export function SupplierFormFields({ form, onChange }: SupplierFormFieldsProps) {
  const { t } = useTranslation();

  return (
    <>
      <div className="form-group">
        <label>{t("suppliers.supplierName")} *</label>
        <input
          required
          value={form.name}
          onChange={e => onChange("name", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("suppliers.contactName")}</label>
        <input
          value={form.contact_name}
          onChange={e => onChange("contact_name", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("common.email")}</label>
        <input
          type="email"
          value={form.email}
          onChange={e => onChange("email", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("common.phone")}</label>
        <input
          value={form.phone}
          onChange={e => onChange("phone", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("suppliers.address")}</label>
        <textarea
          value={form.address}
          onChange={e => onChange("address", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("common.notes")}</label>
        <textarea
          value={form.notes}
          onChange={e => onChange("notes", e.target.value)}
        />
      </div>
    </>
  );
}
