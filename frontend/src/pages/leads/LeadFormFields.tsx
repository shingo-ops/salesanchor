/**
 * LeadFormFields — リードクイック編集フォーム（Drawer用 7項目）
 *
 * LeadsPage（Drawer内）で使用する要点フィールド。
 * 全項目は LeadEditPage を参照。
 */

import { useId } from "react";
import { useTranslation } from "react-i18next";
import { CountryCombobox } from "../../components/CountryCombobox";
import { Select } from "../../components/Select";
import { LEAD_STATUS_CODES, type LeadStatusCode } from "../../constants/leadStatus";
import type { CloseReasonResponse } from "../../api/closeReasons";

export interface LeadFormState {
  customer_name: string;
  email: string;
  phone: string;
  status: string;
  type: string;
  notes: string;
  country: string;
  close_reason_id: string;
  close_reason_memo: string;
}

export interface LostReasonFieldsProps {
  status: string;
  closeReasonId: string;
  closeReasonMemo: string;
  closeReasonOptions: Pick<CloseReasonResponse, "id" | "label">[];
  onCloseReasonIdChange: (value: string) => void;
  onCloseReasonMemoChange: (value: string) => void;
}

interface Props {
  form: LeadFormState;
  onChange: (field: keyof LeadFormState, value: string) => void;
  closeReasonOptions: Pick<CloseReasonResponse, "id" | "label">[];
}

const LEAD_STATUSES: LeadStatusCode[] = [...LEAD_STATUS_CODES];

export function buildLostReasonUpdatePayload(
  status: string,
  closeReasonId: string,
  closeReasonMemo: string,
) {
  if (status !== "lost") return {};
  return {
    close_reason_memo: closeReasonMemo ? closeReasonMemo : null,
    close_reasons: closeReasonId
      ? [{ reason_id: Number(closeReasonId), is_primary: true }]
      : [],
  };
}

export function LostReasonFields({
  status,
  closeReasonId,
  closeReasonMemo,
  closeReasonOptions,
  onCloseReasonIdChange,
  onCloseReasonMemoChange,
}: LostReasonFieldsProps) {
  const { t } = useTranslation();
  const memoId = useId();
  if (status !== "lost") return null;

  return (
    <>
      <Select
        label={t("leads.lostReasonCode")}
        value={closeReasonId}
        onChange={(e) => onCloseReasonIdChange(e.target.value)}
        options={closeReasonOptions.map((option) => ({
          value: String(option.id),
          label: option.label,
        }))}
        placeholder={t("leads.lostReasonCodePlaceholder")}
      />
      <div className="form-group">
        <label htmlFor={memoId}>{t("leads.lostReason")}</label>
        <textarea
          id={memoId}
          value={closeReasonMemo}
          onChange={(e) => onCloseReasonMemoChange(e.target.value)}
          placeholder={t("leads.lostReasonPlaceholder")}
        />
      </div>
    </>
  );
}

export function LeadFormFields({ form, onChange, closeReasonOptions }: Props) {
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
      <LostReasonFields
        status={form.status}
        closeReasonId={form.close_reason_id}
        closeReasonMemo={form.close_reason_memo}
        closeReasonOptions={closeReasonOptions}
        onCloseReasonIdChange={(value) => onChange("close_reason_id", value)}
        onCloseReasonMemoChange={(value) => onChange("close_reason_memo", value)}
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
