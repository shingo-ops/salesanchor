/**
 * 会社詳細 — 基本情報タブ。
 * 編集フォームと pending_dedup_review 解消セクションを含む。
 */

import { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import type { BasicFormState, Company } from "./company-detail.types";
import { TextareaControl } from "../../components/Textarea";
import { TextFieldControl } from "../../components/TextField";

interface Props {
  basicForm: BasicFormState;
  setBasicForm: (f: BasicFormState) => void;
  basicDirty: boolean;
  setBasicDirty: (v: boolean) => void;
  basicSubmitting: boolean;
  handleBasicSubmit: (e: FormEvent) => void;
  canEdit: boolean;
  canMerge: boolean;
  company: Company;
  dedupSubmitting: boolean;
  setDedupConfirmOpen: (v: boolean) => void;
  setMergeModalOpen: (v: boolean) => void;
}

export function CompanyBasicTab({
  basicForm, setBasicForm, basicDirty, setBasicDirty, basicSubmitting,
  handleBasicSubmit, canEdit, canMerge, company, dedupSubmitting,
  setDedupConfirmOpen, setMergeModalOpen,
}: Props) {
  const { t } = useTranslation();

  return (
    <form onSubmit={handleBasicSubmit} className="form-grid">
      <div className="form-row"><label>{t("common.name")} *</label>
        <TextFieldControl required disabled={!canEdit} value={basicForm.name}
          onChange={(e) => { setBasicForm({ ...basicForm, name: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.nameEn")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.name_en}
          onChange={(e) => { setBasicForm({ ...basicForm, name_en: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.industry")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.industry}
          onChange={(e) => { setBasicForm({ ...basicForm, industry: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.website")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.website}
          onChange={(e) => { setBasicForm({ ...basicForm, website: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.priorityFocus")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.priority_focus}
          onChange={(e) => { setBasicForm({ ...basicForm, priority_focus: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.perOrderAmount")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.per_order_amount}
          onChange={(e) => { setBasicForm({ ...basicForm, per_order_amount: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.monthlyFrequency")}</label>
        <TextFieldControl type="number" min="0" disabled={!canEdit} value={basicForm.monthly_frequency}
          onChange={(e) => { setBasicForm({ ...basicForm, monthly_frequency: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.monthlyForecast")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.monthly_forecast}
          onChange={(e) => { setBasicForm({ ...basicForm, monthly_forecast: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.billingDisplayName")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.billing_display_name}
          onChange={(e) => { setBasicForm({ ...basicForm, billing_display_name: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.paymentRecipientName")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.payment_recipient_name}
          onChange={(e) => { setBasicForm({ ...basicForm, payment_recipient_name: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.fedexAccount")}</label>
        <TextFieldControl disabled={!canEdit} value={basicForm.fedex_account}
          onChange={(e) => { setBasicForm({ ...basicForm, fedex_account: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("companies.shippingNote")}</label>
        <TextareaControl disabled={!canEdit} value={basicForm.shipping_note}
          onChange={(e) => { setBasicForm({ ...basicForm, shipping_note: e.target.value }); setBasicDirty(true); }} />
      </div>
      <div className="form-row"><label>{t("common.status")}</label>
        <SelectControl fullWidth disabled={!canEdit} value={basicForm.status}
          onChange={(e) => { setBasicForm({ ...basicForm, status: e.target.value }); setBasicDirty(true); }}>
          <option value="active">active</option>
          <option value="inactive">inactive</option>
          <option value="archived">archived</option>
          <option value="pending_dedup_review">pending_dedup_review</option>
        </SelectControl>
      </div>
      <div className="form-row"><label>{t("common.notes")}</label>
        <TextareaControl disabled={!canEdit} value={basicForm.notes}
          onChange={(e) => { setBasicForm({ ...basicForm, notes: e.target.value }); setBasicDirty(true); }} />
      </div>
      {canEdit && (
        <div className="form-actions">
          <Button type="submit" variant="primary" size="md" disabled={!basicDirty || basicSubmitting}>
            {basicSubmitting ? t("common.saving") : t("companies.saveBasicInfo")}
          </Button>
        </div>
      )}

      {/* v_company_stats: 読み取り専用集計エリア */}
      <div className="form-section-divider" />
      <div className="form-row">
        <label>{t("company.stats.conversation_count")}</label>
        <span className="read-only-value">
          {company.conversation_count != null ? company.conversation_count : "—"}
        </span>
      </div>
      <div className="form-row">
        <label>{t("company.stats.last_conversation_at")}</label>
        <span className="read-only-value">
          {company.last_conversation_at
            ? new Date(company.last_conversation_at).toLocaleString("ja-JP")
            : "—"}
        </span>
      </div>

      {/* PR #145 Q2: pending_dedup_review 解消セクション */}
      {canEdit && company.status === "pending_dedup_review" && (
        <div className="dedup-resolve-section">
          <h3>{t("companies.dedupResolveTitle")}</h3>
          <p>{t("companies.dedupResolveDesc")}</p>
          <div className="dedup-resolve-actions">
            <Button variant="primary" size="md"
              type="button"

              onClick={() => setDedupConfirmOpen(true)}
              disabled={dedupSubmitting || basicDirty}
              title={basicDirty ? t("companies.dedupUnsavedHint") : ""}
            >
              {t("companies.dedupConfirmAsDistinct")}
            </Button>
            <Button variant="danger" size="md"
              type="button"

              onClick={() => setMergeModalOpen(true)}
              disabled={!canMerge || dedupSubmitting || basicDirty}
              title={
                !canMerge
                  ? t("companies.dedupMergeNoPermission")
                  : basicDirty
                    ? t("companies.dedupUnsavedHint")
                    : t("companies.dedupMergeHint")
              }
            >
              {t("companies.dedupMergeLabel")}
            </Button>
          </div>
        </div>
      )}
    </form>
  );
}
