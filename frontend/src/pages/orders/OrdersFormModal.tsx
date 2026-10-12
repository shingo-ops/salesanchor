/**
 * 受注管理 — 新規作成 / 編集モーダル。
 */

import { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import CompanyContactSelector from "../../components/CompanyContactSelector";
import { Modal } from "../../components/Modal";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import type { CompanyMini } from "./orders.types";
import { STATUSES } from "./orders.types";
import { TextareaControl } from "../../components/Textarea";
import { TextFieldControl } from "../../components/TextField";

interface Props {
  showForm: boolean;
  setShowForm: (v: boolean) => void;
  editId: number | null;
  form: {
    order_number: string;
    total_amount: string;
    status: string;
    notes: string;
  };
  setForm: (f: Props["form"]) => void;
  companyId: number | null;
  setCompanyId: (v: number | null) => void;
  contactId: number | null;
  setContactId: (v: number | null) => void;
  selectorError: string;
  companies: CompanyMini[];
  STATUS_LABELS: Record<string, string>;
  handleSubmit: (e: FormEvent) => void;
}

export function OrdersFormModal({
  showForm, setShowForm, editId,
  form, setForm,
  companyId, setCompanyId,
  contactId, setContactId,
  selectorError, companies,
  STATUS_LABELS, handleSubmit,
}: Props) {
  const { t } = useTranslation();

  return (
    <Modal
      open={showForm}
      onClose={() => setShowForm(false)}
      title={editId ? t("orders.editOrder") : t("orders.newOrder")}
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <CompanyContactSelector
          value={{ companyId, contactId }}
          onChange={({ companyId: c, contactId: ct }) => {
            setCompanyId(c);
            setContactId(ct);
          }}
          required={!editId}
          disabled={editId !== null}
          error={selectorError}
          companies={companies}
        />
        {editId && (
          <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginTop: -8 }}>
            {t("common.irreversible")}
          </p>
        )}
        <div className="form-group">
          <label>{t("orders.orderNumber")} *</label>
          <TextFieldControl
            required
            value={form.order_number}
            onChange={(e) => setForm({ ...form, order_number: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>{t("common.amount")}</label>
          <TextFieldControl
            type="number" min="0" step="1"
            value={form.total_amount}
            onChange={(e) => setForm({ ...form, total_amount: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>{t("common.status")}</label>
          <SelectControl fullWidth value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_LABELS[s]}</option>
            ))}
          </SelectControl>
        </div>
        <div className="form-group">
          <label>{t("common.notes")}</label>
          <TextareaControl value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </div>
        <div className="form-actions">
          <Button type="button" variant="secondary" size="md" onClick={() => setShowForm(false)}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" variant="primary" size="md">
            {editId ? t("common.update") : t("common.register")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
