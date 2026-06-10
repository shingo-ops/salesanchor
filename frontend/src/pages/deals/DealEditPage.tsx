/**
 * DealEditPage — 案件フルページ編集（/deals/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * 全項目（CompanyContactSelector 含む）を編集可能。
 * 保存後は /deals 一覧へ戻る。
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";
import CompanyContactSelector from "../../components/CompanyContactSelector";

interface Deal {
  id: number;
  company_id: number;
  contact_id: number | null;
  title: string;
  amount: number | null;
  currency: string | null;
  status: string;
  stage: string | null;
  probability: number | null;
  lost_reason: string | null;
  lost_reason_code: string | null;
  assigned_to: number | null;
  expected_close_date: string | null;
  notes: string | null;
  lead_source: string | null;
}

interface CompanyMini {
  id: number;
  company_code: string;
  name: string;
}

const STATUSES = ["open", "negotiating", "won", "lost", "on_hold"];
const STAGES = ["open", "negotiating", "proposal", "won", "lost", "on_hold"];
const LOST_REASON_CODES = [
  "price", "lead_time", "competitor", "spec_condition",
  "payment_terms", "no_response", "other",
] as const;

type FormState = {
  title: string;
  amount: string;
  currency: string;
  status: string;
  stage: string;
  probability: string;
  lost_reason_code: string;
  lost_reason: string;
  assigned_to: string;
  expected_close_date: string;
  notes: string;
  lead_source: string;
};

const emptyForm: FormState = {
  title: "", amount: "", currency: "JPY",
  status: "open", stage: "open", probability: "10",
  lost_reason_code: "", lost_reason: "",
  assigned_to: "", expected_close_date: "", notes: "", lead_source: "",
};

export default function DealEditPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [companies, setCompanies] = useState<CompanyMini[]>([]);
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [contactId, setContactId] = useState<number | null>(null);
  const [selectorError, setSelectorError] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.get<Deal>(`/deals/${id}`),
      api.get<CompanyMini[]>("/companies?per_page=100"),
    ])
      .then(([deal, cs]) => {
        setForm({
          title: deal.title,
          amount: deal.amount != null ? String(deal.amount) : "",
          currency: deal.currency || "JPY",
          status: deal.status,
          stage: deal.stage || "open",
          probability: deal.probability != null ? String(deal.probability) : "10",
          lost_reason_code: deal.lost_reason_code || "",
          lost_reason: deal.lost_reason || "",
          assigned_to: deal.assigned_to != null ? String(deal.assigned_to) : "",
          expected_close_date: deal.expected_close_date || "",
          notes: deal.notes || "",
          lead_source: deal.lead_source || "",
        });
        setCompanies(cs);
        setCompanyId(deal.company_id);
        setContactId(deal.contact_id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("common.fetchError")))
      .finally(() => setLoading(false));
  }, [id, t]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSelectorError("");
    setError("");
    if (contactId === null) {
      setSelectorError(t("companyContactSelector.contactRequired"));
      return;
    }
    try {
      await api.patch(`/deals/${id}`, {
        company_id: companyId,
        contact_id: contactId,
        title: form.title,
        amount: form.amount ? Number(form.amount) : null,
        currency: form.currency,
        status: form.status,
        stage: form.stage,
        probability: form.probability ? Number(form.probability) : null,
        lost_reason_code: form.lost_reason_code || null,
        lost_reason: form.lost_reason_code === "other" ? (form.lost_reason || null) : null,
        assigned_to: form.assigned_to ? Number(form.assigned_to) : null,
        expected_close_date: form.expected_close_date || null,
        notes: form.notes || null,
        lead_source: form.lead_source || null,
      });
      navigate("/deals");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <PageLayout navKey="nav.deals" subtitleKey="deals.subtitle">
      {error && <div className="error-message">{error}</div>}
      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <CompanyContactSelector
            value={{ companyId, contactId }}
            onChange={({ companyId: c, contactId: ct }) => {
              setCompanyId(c);
              setContactId(ct);
            }}
            required
            error={selectorError}
            companies={companies}
          />
          <div className="form-group"><label>{t("deals.leadSource")}</label>
            <input
              value={form.lead_source}
              placeholder={t("deals.leadSourcePlaceholder")}
              maxLength={50}
              onChange={(e) => setForm({ ...form, lead_source: e.target.value })}
            />
          </div>
          <div className="form-group"><label>{t("deals.dealTitle")} *</label>
            <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("deals.amount")}</label>
            <input type="number" min="0" step="1" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("common.currency")}</label>
            <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
              <option value="JPY">JPY</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
          <div className="form-group"><label>{t("common.status")}</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              {STATUSES.map((s) => <option key={s} value={s}>{t(`deals.status_${s}`)}</option>)}
            </select>
          </div>
          <div className="form-group"><label>{t("dashboard.stage")}</label>
            <select value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value })}>
              {STAGES.map((s) => <option key={s} value={s}>{t(`deals.stage_${s}`)}</option>)}
            </select>
          </div>
          <div className="form-group"><label>{t("deals.probability")}</label>
            <input type="number" min="0" max="100" value={form.probability} onChange={(e) => setForm({ ...form, probability: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("deals.assignedTo")}</label>
            <input type="number" min="1" value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("deals.expectedCloseDate")}</label>
            <input type="date" value={form.expected_close_date} onChange={(e) => setForm({ ...form, expected_close_date: e.target.value })} />
          </div>
          {form.status === "lost" && (
            <>
              <div className="form-group"><label>{t("deals.lostReasonCode")}</label>
                <select
                  value={form.lost_reason_code}
                  onChange={(e) => setForm({ ...form, lost_reason_code: e.target.value })}
                >
                  <option value="">{t("deals.lostReasonCodePlaceholder")}</option>
                  {LOST_REASON_CODES.map((code) => (
                    <option key={code} value={code}>{t(`deals.lostReasonCode_${code}`)}</option>
                  ))}
                </select>
              </div>
              {form.lost_reason_code === "other" && (
                <div className="form-group"><label>{t("deals.lostReason")}</label>
                  <textarea
                    value={form.lost_reason}
                    placeholder={t("deals.lostReasonPlaceholder")}
                    onChange={(e) => setForm({ ...form, lost_reason: e.target.value })}
                  />
                </div>
              )}
            </>
          )}
          <div className="form-group"><label>{t("common.notes")}</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => navigate("/deals")}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
