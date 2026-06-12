/**
 * リード管理ページ。
 * ステータスフィルター、見込度ランク表示、案件化機能を含む。
 *
 * 変更履歴:
 *   2026-04-16: 初版作成（Phase 1）
 *   2026-04-25: Phase 1-B-2 Step 5c-3 — 案件化モーダルの顧客セレクタを
 *     CompanyContactSelector（company + contact）に置換。
 *   2026-06-11: ADR-122 バッチC3 — 新規作成は Modal のまま、編集を Drawer 化。
 */

import { useCallback, useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { Modal } from "../../components/Modal";
import { Drawer } from "../../components/Drawer";
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
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { LeadFormFields } from "./LeadFormFields";
import type { LeadFormState } from "./LeadFormFields";

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
  channel_type: string | null;
  initiative: string | null;
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

type CreateFormState = {
  customer_name: string;
  company_name: string;
  email: string;
  phone: string;
  channel_type: string;
  initiative: string;
  type: string;
  status: string;
  temperature: string;
  estimated_scale: string;
  customer_type: string;
  response_speed: string;
  monthly_forecast: string;
  notes: string;
};

const emptyCreateForm: CreateFormState = {
  customer_name: "", company_name: "", email: "", phone: "",
  channel_type: "", initiative: "", type: "", status: "lead", temperature: "",
  estimated_scale: "", customer_type: "", response_speed: "",
  monthly_forecast: "", notes: "",
};

const emptyEditForm: LeadFormState = {
  customer_name: "", email: "", phone: "",
  status: "lead", type: "", notes: "",
};

const toForm = (l: Lead): LeadFormState => ({
  customer_name: l.customer_name,
  email: l.email || "",
  phone: l.phone || "",
  status: l.status,
  type: l.type || "",
  notes: l.notes || "",
});

/* ------------------------------------------------------------------ */
/* Main LeadsPage                                                       */
/* ------------------------------------------------------------------ */

export default function LeadsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();

  const [leads, setLeads] = useState<Lead[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  // 新規作成 Modal
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<CreateFormState>(emptyCreateForm);
  // 編集 Drawer
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Lead, LeadFormState>({ toForm, emptyForm: emptyEditForm });
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

  /* ── 新規作成（Modal） ── */
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => (v ? v : null);
    try {
      await api.post("/leads", {
        customer_name: createForm.customer_name,
        company_name: toNull(createForm.company_name),
        email: toNull(createForm.email),
        phone: toNull(createForm.phone),
        channel_type: toNull(createForm.channel_type),
        initiative: toNull(createForm.initiative),
        type: toNull(createForm.type),
        status: createForm.status,
        temperature: toNull(createForm.temperature),
        estimated_scale: toNull(createForm.estimated_scale),
        customer_type: toNull(createForm.customer_type),
        response_speed: toNull(createForm.response_speed),
        monthly_forecast: createForm.monthly_forecast ? Number(createForm.monthly_forecast) : null,
        notes: toNull(createForm.notes),
      });
      setShowCreate(false);
      setCreateForm(emptyCreateForm);
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  /* ── Drawer 編集（6項目） ── */
  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!editId || !editForm) return;
    setError("");
    const toNull = (v: string) => (v ? v : null);
    try {
      await api.patch(`/leads/${editId}`, {
        customer_name: editForm.customer_name,
        email: toNull(editForm.email),
        phone: toNull(editForm.phone),
        status: editForm.status,
        type: toNull(editForm.type),
        notes: toNull(editForm.notes),
      });
      closeDrawer();
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
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
          <button className="btn-primary" onClick={() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}>{t("leads.newLead")}</button>
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

      {/* 新規作成 Modal（全項目）*/}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t("leads.newLeadTitle")}
        size="md"
      >
        <form onSubmit={handleCreateSubmit}>
          <div className="form-group"><label>{t("leads.customerName")} *</label>
            <input required value={createForm.customer_name} onChange={(e) => setCreateForm({ ...createForm, customer_name: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.companyName")}</label>
            <input value={createForm.company_name} onChange={(e) => setCreateForm({ ...createForm, company_name: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.email")}</label>
            <input type="email" value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.phone")}</label>
            <input value={createForm.phone} onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.channelType")}</label>
            <input placeholder={t("leads.channelTypePlaceholder")} value={createForm.channel_type} onChange={(e) => setCreateForm({ ...createForm, channel_type: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.initiative")}</label>
            <select value={createForm.initiative} onChange={(e) => setCreateForm({ ...createForm, initiative: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="inbound">{t("leads.initiative_inbound")}</option>
              <option value="outbound">{t("leads.initiative_outbound")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.type")}</label>
            <select value={createForm.type} onChange={(e) => setCreateForm({ ...createForm, type: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="Inbound">{t("leads.type_inbound")}</option>
              <option value="Outbound">{t("leads.type_outbound")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.status")}</label>
            <select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>
              {LEAD_STATUSES.map((s) => <option key={s} value={s}>{translateLeadStatus(s)}</option>)}
            </select>
          </div>
          <div className="form-group"><label>{t("leads.temperature")}</label>
            <select value={createForm.temperature} onChange={(e) => setCreateForm({ ...createForm, temperature: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="Hot">{t("leads.temp_hot")}</option>
              <option value="Warm">{t("leads.temp_warm")}</option>
              <option value="Cold">{t("leads.temp_cold")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.estimatedScale")}</label>
            <select value={createForm.estimated_scale} onChange={(e) => setCreateForm({ ...createForm, estimated_scale: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="Small">{t("leads.scale_small")}</option>
              <option value="Medium">{t("leads.scale_medium")}</option>
              <option value="Large">{t("leads.scale_large")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.customerType")}</label>
            <select value={createForm.customer_type} onChange={(e) => setCreateForm({ ...createForm, customer_type: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="信頼重視">{t("leads.customerType_trust")}</option>
              <option value="価格重視">{t("leads.customerType_price")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.responseSpeed")}</label>
            <select value={createForm.response_speed} onChange={(e) => setCreateForm({ ...createForm, response_speed: e.target.value })}>
              <option value="">{t("common.notSet")}</option>
              <option value="24h以内">{t("leads.responseSpeed_24h")}</option>
              <option value="3日以内">{t("leads.responseSpeed_3days")}</option>
              <option value="3日超">{t("leads.responseSpeed_over3days")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("leads.monthlyForecast")}</label>
            <input type="number" min="0" step="1" value={createForm.monthly_forecast} onChange={(e) => setCreateForm({ ...createForm, monthly_forecast: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("leads.notes")}</label>
            <textarea value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.register")}</button>
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
            <span className="actions" onClick={(e) => e.stopPropagation()}>
              {hasPermission("leads.convert") && !l.converted_deal_id && (
                <button className="btn-sm btn-primary" onClick={(e) => { e.stopPropagation(); setConvertTarget(l); }}>{t("leads.convert")}</button>
              )}
              {hasPermission("leads.delete") && !l.converted_deal_id && (
                <button className="btn-sm" onClick={(e) => { e.stopPropagation(); setMergeSource(l); }}>{t("leads.merge")}</button>
              )}
              {hasPermission("leads.delete") && <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(l); }}>{t("common.delete")}</button>}
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
            onRowClick={hasPermission("leads.update") ? handleRowClick : undefined}
          />
        );
      })()}

      {/* 編集 Drawer（行クリックで開く・useRecordDrawer フック） */}
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={t("leads.editLead")}
        onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/crm/leads/${editId}/edit`); } : undefined}
      >
        {editForm && (
          <form onSubmit={handleEditSubmit}>
            <LeadFormFields
              form={editForm}
              onChange={(field, value) => setEditForm({ ...editForm, [field]: value })}
            />
            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={closeDrawer}>{t("common.cancel")}</button>
              <button type="submit" className="btn-primary">{t("common.update")}</button>
            </div>
          </form>
        )}
      </Drawer>

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
