/**
 * リード管理ページ。
 * ステータスフィルター、見込度ランク表示、案件化機能を含む。
 *
 * 変更履歴:
 *   2026-04-16: 初版作成（Phase 1）
 *   2026-04-25: Phase 1-B-2 Step 5c-3 — 案件化モーダルの顧客セレクタを
 *     CompanyContactSelector（company + contact）に置換。
 */

import { useCallback, useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Modal } from "../../components/Modal";
import ConfirmModal from "../../components/ConfirmModal";
import CompanyContactSelector from "../../components/CompanyContactSelector";
import MergeLeadModal from "../../components/MergeLeadModal";
import PriorityScoreBadge, { type CustomerScoreData } from "../../components/PriorityScoreBadge";
import { usePermissions } from "../../hooks/usePermissions";
import { useSSE } from "../../hooks/useSSE";
import { PageLayout } from "../../components/PageLayout";
import { getStatusPresentation } from "../../utils/statusPresentation";
import { LEAD_STATUS_CODES, type LeadStatusCode } from "../../constants/leadStatus";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";

/* ------------------------------------------------------------------ */
/* Lead types                                                           */
/* ------------------------------------------------------------------ */

interface Lead {
  id: number;
  lead_code: string | null;
  customer_name: string;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  source: string | null;
  type: string | null;
  status: string;
  temperature: string | null;
  estimated_scale: string | null;
  customer_type: string | null;
  response_speed: string | null;
  monthly_forecast: number | null;
  prospect_rank: string | null;
  assigned_to: number | null;
  converted_deal_id: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  discord_user_id: string | null;
  discord_role_sync_status: string | null;
  // ADR-107: 優先度スコア（社内専用・顧客非公開）
  priority_score?: CustomerScoreData | null;
}

type FormState = {
  customer_name: string;
  company_name: string;
  email: string;
  phone: string;
  source: string;
  type: string;
  status: string;
  temperature: string;
  estimated_scale: string;
  customer_type: string;
  response_speed: string;
  monthly_forecast: string;
  notes: string;
};

const emptyForm: FormState = {
  customer_name: "", company_name: "", email: "", phone: "",
  source: "", type: "", status: "lead", temperature: "",
  estimated_scale: "", customer_type: "", response_speed: "",
  monthly_forecast: "", notes: "",
};

/* ------------------------------------------------------------------ */
/* Main LeadsPage                                                       */
/* ------------------------------------------------------------------ */

export default function LeadsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();

  const [leads, setLeads] = useState<Lead[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Lead | null>(null);
  const [mergeSource, setMergeSource] = useState<Lead | null>(null);
  const [convertTarget, setConvertTarget] = useState<Lead | null>(null);
  const [convertForm, setConvertForm] = useState({ title: "", amount: "" });
  const [convertCompanyId, setConvertCompanyId] = useState<number | null>(null);
  const [convertContactId, setConvertContactId] = useState<number | null>(null);
  const [convertSelectorError, setConvertSelectorError] = useState("");

  // ADR-109: status codes with i18n labels
  const LEAD_STATUSES: LeadStatusCode[] = [...LEAD_STATUS_CODES];
  const translateLeadStatus = (status: string) =>
    t(`leads.statusCode.${status}`, { defaultValue: status });

  const loadLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
      const data = await api.get<Lead[]>(`/leads${params}`);
      setLeads(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, t]);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  // Phase 3 SSE: 他スタッフのリード作成・更新・削除を即時反映
  useSSE({
    endpoint: "/api/v1/leads/stream",
    onUpdate: useCallback(() => { loadLeads(); }, [loadLeads]),
  });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => (v ? v : null);
    const payload = {
      customer_name: form.customer_name,
      company_name: toNull(form.company_name),
      email: toNull(form.email),
      phone: toNull(form.phone),
      source: toNull(form.source),
      type: toNull(form.type),
      status: form.status,
      temperature: toNull(form.temperature),
      estimated_scale: toNull(form.estimated_scale),
      customer_type: toNull(form.customer_type),
      response_speed: toNull(form.response_speed),
      monthly_forecast: form.monthly_forecast ? Number(form.monthly_forecast) : null,
      notes: toNull(form.notes),
    };
    try {
      if (editId) {
        await api.patch(`/leads/${editId}`, payload);
      } else {
        await api.post("/leads", payload);
      }
      setShowForm(false);
      setEditId(null);
      setForm(emptyForm);
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleEdit = (l: Lead) => {
    setEditId(l.id);
    setForm({
      customer_name: l.customer_name,
      company_name: l.company_name || "",
      email: l.email || "",
      phone: l.phone || "",
      source: l.source || "",
      type: l.type || "",
      status: l.status,
      temperature: l.temperature || "",
      estimated_scale: l.estimated_scale || "",
      customer_type: l.customer_type || "",
      response_speed: l.response_speed || "",
      monthly_forecast: l.monthly_forecast != null ? String(l.monthly_forecast) : "",
      notes: l.notes || "",
    });
    setShowForm(true);
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleteTarget(null);
    try {
      await api.delete(`/leads/${id}`);
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const closeConvert = () => {
    setConvertTarget(null);
    setConvertForm({ title: "", amount: "" });
    setConvertCompanyId(null);
    setConvertContactId(null);
    setConvertSelectorError("");
  };

  const performConvert = async (e: FormEvent) => {
    e.preventDefault();
    if (!convertTarget) return;
    setConvertSelectorError("");
    if (convertContactId === null) {
      setConvertSelectorError(t("companyContactSelector.contactRequired"));
      return;
    }
    try {
      await api.post(`/leads/${convertTarget.id}/convert`, {
        company_id: convertCompanyId,
        contact_id: convertContactId,
        title: convertForm.title,
        amount: convertForm.amount ? Number(convertForm.amount) : null,
      });
      closeConvert();
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    }
  };

  const rankBadge = (rank: string | null) => {
    if (!rank) return "-";
    const p = getStatusPresentation("prospectRank", rank);
    return <span className={`badge badge-${p.badgeVariant}`}>{rank}</span>;
  };

  return (
    <PageLayout
      navKey="nav.leadsSection"
      subtitleKey="leads.subtitle"
      headerAction={hasPermission("leads.create") ? (
        <div className="page-header-actions">
          <button className="btn-primary" onClick={() => { setShowForm(true); setEditId(null); setForm(emptyForm); }}>{t("leads.newLead")}</button>
        </div>
      ) : undefined}
    >
      <div className="filter-bar">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">{t("leads.allStatuses")}</option>
          {LEAD_STATUSES.map((s) => <option key={s} value={s}>{translateLeadStatus(s)}</option>)}
        </select>
      </div>

      {error && <div className="error-message">{error}</div>}

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t("leads.editLead") : t("leads.newLeadTitle")}
        size="md"
      >
        <form onSubmit={handleSubmit}>
              <div className="form-group"><label>{t("leads.customerName")} *</label>
                <input required value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("leads.companyName")}</label>
                <input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("leads.email")}</label>
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("leads.phone")}</label>
                <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("leads.source")}</label>
                <input placeholder={t("leads.sourcePlaceholder")} value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("leads.type")}</label>
                <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  <option value="Inbound">{t("leads.type_inbound")}</option>
                  <option value="Outbound">{t("leads.type_outbound")}</option>
                </select>
              </div>
              <div className="form-group"><label>{t("leads.status")}</label>
                <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                  {LEAD_STATUSES.map((s) => <option key={s} value={s}>{translateLeadStatus(s)}</option>)}
                </select>
              </div>
              <div className="form-group"><label>{t("leads.temperature")}</label>
                <select value={form.temperature} onChange={(e) => setForm({ ...form, temperature: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  <option value="Hot">{t("leads.temp_hot")}</option>
                  <option value="Warm">{t("leads.temp_warm")}</option>
                  <option value="Cold">{t("leads.temp_cold")}</option>
                </select>
              </div>
              <div className="form-group"><label>{t("leads.estimatedScale")}</label>
                <select value={form.estimated_scale} onChange={(e) => setForm({ ...form, estimated_scale: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  <option value="Small">{t("leads.scale_small")}</option>
                  <option value="Medium">{t("leads.scale_medium")}</option>
                  <option value="Large">{t("leads.scale_large")}</option>
                </select>
              </div>
              <div className="form-group"><label>{t("leads.customerType")}</label>
                <select value={form.customer_type} onChange={(e) => setForm({ ...form, customer_type: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  <option value="信頼重視">{t("leads.customerType_trust")}</option>
                  <option value="価格重視">{t("leads.customerType_price")}</option>
                </select>
              </div>
              <div className="form-group"><label>{t("leads.responseSpeed")}</label>
                <select value={form.response_speed} onChange={(e) => setForm({ ...form, response_speed: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  <option value="24h以内">{t("leads.responseSpeed_24h")}</option>
                  <option value="3日以内">{t("leads.responseSpeed_3days")}</option>
                  <option value="3日超">{t("leads.responseSpeed_over3days")}</option>
                </select>
              </div>
              <div className="form-group"><label>{t("leads.monthlyForecast")}</label>
                <input type="number" min="0" step="1" value={form.monthly_forecast} onChange={(e) => setForm({ ...form, monthly_forecast: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("leads.notes")}</label>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</button>
                <button type="submit" className="btn-primary">{editId ? t("common.update") : t("common.register")}</button>
              </div>
        </form>
      </Modal>

      <Modal
        open={!!convertTarget}
        onClose={closeConvert}
        title={t("leads.convertLead")}
        size="md"
      >
        <p>{t("leads.title")} <strong>{convertTarget?.customer_name}</strong> {t("leads.convertConfirm")}</p>
        <form onSubmit={performConvert}>
          <CompanyContactSelector
            value={{ companyId: convertCompanyId, contactId: convertContactId }}
            onChange={({ companyId, contactId }) => {
              setConvertCompanyId(companyId);
              setConvertContactId(contactId);
            }}
            required
            error={convertSelectorError}
          />
          <div className="form-group"><label>{t("leads.dealTitle")} *</label>
            <input required value={convertForm.title} onChange={(e) => setConvertForm({ ...convertForm, title: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.dealAmount")}</label>
            <input type="number" min="0" step="1" value={convertForm.amount} onChange={(e) => setConvertForm({ ...convertForm, amount: e.target.value })} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={closeConvert}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("leads.convert")}</button>
          </div>
        </form>
      </Modal>

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (() => {
        const baseColumns: DataTableColumn<Lead>[] = [
          { key: "customer_name", header: t("leads.customerName") },
          { key: "company_name", header: t("leads.companyName"), renderCell: (l) => l.company_name || "-" },
          { key: "status", header: t("leads.status"), renderCell: (l) => <span className={`badge badge-${getStatusPresentation("lead", l.status).badgeVariant}`}>{translateLeadStatus(l.status)}</span> },
          { key: "temperature", header: t("leads.temperature"), renderCell: (l) => l.temperature || "-" },
          { key: "prospect_rank", header: t("leads.prospectRank"), renderCell: (l) => rankBadge(l.prospect_rank) },
        ];
        const priorityCol: DataTableColumn<Lead> = {
          key: "priority_score", header: t("priority.sectionTitle"), renderCell: (l) => <PriorityScoreBadge score={l.priority_score} />,
        };
        const trailingColumns: DataTableColumn<Lead>[] = [
          { key: "discord", header: "Discord", renderCell: (l) => (
            l.discord_user_id ? (
              <span className={`badge badge-sm discord-sync-${l.discord_role_sync_status ?? "not_linked"}`}
                    title={t(`discordConfig.syncStatus.${l.discord_role_sync_status ?? "not_linked"}`)}>
                D
              </span>
            ) : null
          )},
          { key: "actions", header: t("leads.actions"), renderCell: (l) => (
            <span className="actions">
              {hasPermission("leads.update") && <button className="btn-sm" onClick={() => handleEdit(l)}>{t("common.edit")}</button>}
              {hasPermission("leads.convert") && !l.converted_deal_id && (
                <button className="btn-sm btn-primary" onClick={() => setConvertTarget(l)}>{t("leads.convert")}</button>
              )}
              {hasPermission("leads.delete") && !l.converted_deal_id && (
                <button className="btn-sm" onClick={() => setMergeSource(l)}>{t("leads.merge")}</button>
              )}
              {hasPermission("leads.delete") && <button className="btn-sm btn-danger" onClick={() => setDeleteTarget(l)}>{t("common.delete")}</button>}
            </span>
          )},
        ];
        const columns = [
          ...baseColumns,
          ...(hasPermission("analytics.customer_priority.view") ? [priorityCol] : []),
          ...trailingColumns,
        ];
        return (
          <DataTable<Lead>
            columns={columns}
            data={leads}
            rowKey={(l) => String(l.id)}
            emptyState={t("leads.noLeads")}
          />
        );
      })()}

      <MergeLeadModal
        open={!!mergeSource}
        source={mergeSource ?? { id: 0, lead_code: null, customer_name: "" }}
        onMerged={() => {
          setMergeSource(null);
          loadLeads();
        }}
        onCancel={() => setMergeSource(null)}
      />

      <ConfirmModal
        open={!!deleteTarget}
        title={t("leads.deleteLead")}
        message={<><strong>{deleteTarget?.customer_name}</strong> {t("leads.deleteConfirm")}<br />{t("common.irreversible")}</>}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
