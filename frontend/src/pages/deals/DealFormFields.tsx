/**
 * DealFormFields — 案件クイック編集フォーム（Drawer用 6項目）
 *
 * DealsPage（Drawer内）で使用する要点フィールド。
 * 全項目（CompanyContactSelector含む）は DealEditPage を参照。
 */

import { useTranslation } from "react-i18next";

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
      <div className="form-group">
        <label>{t("common.status")}</label>
        <select
          value={form.status}
          onChange={(e) => onChange("status", e.target.value)}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{t(`deals.status_${s}`)}</option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label>{t("dashboard.stage")}</label>
        <select
          value={form.stage}
          onChange={(e) => onChange("stage", e.target.value)}
        >
          {STAGES.map((s) => (
            <option key={s} value={s}>{t(`deals.stage_${s}`)}</option>
          ))}
        </select>
      </div>
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
