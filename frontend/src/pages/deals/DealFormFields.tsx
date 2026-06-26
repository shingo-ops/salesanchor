/**
 * DealFormFields — 案件クイック編集フォーム（Drawer用 6項目）
 *
 * DealsPage（Drawer内）で使用する要点フィールド。
 * 全項目（CompanyContactSelector含む）は DealEditPage を参照。
 */

import { useTranslation } from "react-i18next";
import { Select } from "../../components/Select";

export interface DealFormState {
  title: string;
  status: string;
  stage: string;
  amount: string;
  expected_close_date: string;
  notes: string;
}

const STATUSES = ["open", "negotiating", "won", "lost", "on_hold"];
const STAGES = ["open", "negotiating", "proposal", "won", "lost", "on_hold"];

interface Props {
  form: DealFormState;
  onChange: (field: keyof DealFormState, value: string) => void;
}

export function DealFormFields({ form, onChange }: Props) {
  const { t } = useTranslation();
  const statusOptions = STATUSES.map((s) => ({ value: s, label: t(`deals.status_${s}`) }));
  const stageOptions = STAGES.map((s) => ({ value: s, label: t(`deals.stage_${s}`) }));
  return (
    <>
      <div className="form-group">
        <label>{t("deals.dealTitle")} *</label>
        <input
          required
          value={form.title}
          onChange={(e) => onChange("title", e.target.value)}
        />
      </div>
      <Select
        label={t("common.status")}
        value={form.status}
        onChange={(e) => onChange("status", e.target.value)}
        options={statusOptions}
      />
      <Select
        label={t("dashboard.stage")}
        value={form.stage}
        onChange={(e) => onChange("stage", e.target.value)}
        options={stageOptions}
      />
      <div className="form-group">
        <label>{t("deals.amount")}</label>
        <input
          type="number"
          min="0"
          step="1"
          value={form.amount}
          onChange={(e) => onChange("amount", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("deals.expectedCloseDate")}</label>
        <input
          type="date"
          value={form.expected_close_date}
          onChange={(e) => onChange("expected_close_date", e.target.value)}
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
