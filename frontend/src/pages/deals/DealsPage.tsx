/**
 * 案件管理ページ。
 *
 * 変更履歴:
 *   2026-04-16: Phase 1拡張（deal_code/stage/probability/currency/assigned_to 追加、
 *     権限チェック連動）
 *   2026-04-25: Phase 1-B-2 Step 5c-3 — 顧客セレクタを CompanyContactSelector
 *     （company + contact）に置換。一覧表示は company_id ベースに変更。
 *   2026-04-27: PR #147 review follow-up
 *     - F2: レガシー deal（company_id NULL）編集時の UX 改善
 *       - 既存 contact_id がある場合はその contact の company を初期値表示
 *       - レガシー deal を編集中である旨を注記
 *     - F6: companies 一覧をセレクタに props で渡し API 重複コールを解消
 *   2026-04-27: Phase 1-B-2 Step 5d — 旧 customer_id 経路を完全撤去。
 *     interface Deal から customer_id 削除、company_id を必須化、
 *     PR #147 F2 のレガシー deal 編集 UX も廃止（本番に該当 deal は存在しないため）。
 *   2026-06-01: migration 096 — lead_source（流入元）追加。
 *   2026-06-11: ADR-122 バッチC2 — 新規作成は Modal のまま、編集を Drawer 化。
 */

import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { Modal } from "../../components/Modal";
import { Drawer } from "../../components/Drawer";
import ConfirmModal from "../../components/ConfirmModal";
import CompanyContactSelector from "../../components/CompanyContactSelector";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { getStatusPresentation } from "../../utils/statusPresentation";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { DealFormFields } from "./DealFormFields";
import type { DealFormState } from "./DealFormFields";

interface Deal {
  id: number;
  deal_code: string | null;
  company_id: number;
  contact_id: number | null;
  lead_id: number | null;
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
  created_at: string;
  updated_at: string;
}

const LOST_REASON_CODES = [
  "price",
  "lead_time",
  "competitor",
  "spec_condition",
  "payment_terms",
  "no_response",
  "other",
] as const;

interface CompanyMini {
  id: number;
  company_code: string;
  name: string;
}

const STATUSES = ["open", "negotiating", "won", "lost", "on_hold"];
const STAGES = ["open", "negotiating", "proposal", "won", "lost", "on_hold"];

const emptyCreateForm = {
  title: "", amount: "", currency: "JPY",
  status: "open", stage: "open", probability: "10",
  lost_reason_code: "", lost_reason: "",
  assigned_to: "", expected_close_date: "", notes: "", lead_source: "",
};

const emptyEditForm: DealFormState = {
  title: "", status: "open", stage: "open",
  amount: "", expected_close_date: "", notes: "",
};

const toForm = (d: Deal): DealFormState => ({
  title: d.title,
  status: d.status,
  stage: d.stage || "open",
  amount: d.amount != null ? String(d.amount) : "",
  expected_close_date: d.expected_close_date || "",
  notes: d.notes || "",
});

export default function DealsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const [deals, setDeals] = useState<Deal[]>([]);
  const [companies, setCompanies] = useState<CompanyMini[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  // 新規作成 Modal
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState(emptyCreateForm);
  const [createCompanyId, setCreateCompanyId] = useState<number | null>(null);
  const [createContactId, setCreateContactId] = useState<number | null>(null);
  const [selectorError, setSelectorError] = useState("");
  // 編集 Drawer
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Deal, DealFormState>({ toForm, emptyForm: emptyEditForm });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Deal | null>(null);

  const loadDeals = async () => {
    try {
      const params = statusFilter ? `?status=${statusFilter}` : "";
      const data = await api.get<Deal[]>(`/deals${params}`);
      setDeals(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  const loadCompanies = async () => {
    try {
      const data = await api.get<CompanyMini[]>("/companies?per_page=100");
      setCompanies(data.map((c) => ({ id: c.id, company_code: c.company_code, name: c.name })));
    } catch { /* ignore */ }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadDeals(); }, [statusFilter]);
  useEffect(() => { loadCompanies(); }, []);

  const resetCreateSelector = () => {
    setCreateCompanyId(null);
    setCreateContactId(null);
    setSelectorError("");
  };

  /* ── 新規作成（Modal） ── */
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSelectorError("");
    if (createContactId === null) {
      setSelectorError(t("companyContactSelector.contactRequired"));
      return;
    }
    try {
      await api.post("/deals", {
        company_id: createCompanyId,
        contact_id: createContactId,
        title: createForm.title,
        amount: createForm.amount ? Number(createForm.amount) : null,
        currency: createForm.currency,
        status: createForm.status,
        stage: createForm.stage,
        probability: createForm.probability ? Number(createForm.probability) : null,
        lost_reason_code: createForm.lost_reason_code || null,
        lost_reason: createForm.lost_reason_code === "other" ? (createForm.lost_reason || null) : null,
        assigned_to: createForm.assigned_to ? Number(createForm.assigned_to) : null,
        expected_close_date: createForm.expected_close_date || null,
        notes: createForm.notes || null,
        lead_source: createForm.lead_source || null,
      });
      setShowCreate(false);
      setCreateForm(emptyCreateForm);
      resetCreateSelector();
      loadDeals();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  /* ── Drawer 編集（6項目） ── */
  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!editId || !editForm) return;
    setError("");
    try {
      await api.patch(`/deals/${editId}`, {
        title: editForm.title,
        status: editForm.status,
        stage: editForm.stage,
        amount: editForm.amount ? Number(editForm.amount) : null,
        expected_close_date: editForm.expected_close_date || null,
        notes: editForm.notes || null,
      });
      closeDrawer();
      loadDeals();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleteTarget(null);
    try {
      await api.delete(`/deals/${id}`);
      loadDeals();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const fmt = (n: number, ccy: string | null) => {
    const cur = ccy || "JPY";
    try {
      return n.toLocaleString("ja-JP", { style: "currency", currency: cur });
    } catch {
      return `${cur} ${n.toLocaleString()}`;
    }
  };
  const companyName = (id: number | null) => {
    if (!id) return "-";
    const c = companies.find((c) => c.id === id);
    return c ? `${c.name}（${c.company_code}）` : `#${id}`;
  };

  return (
    <PageLayout
      navKey="nav.deals"
      subtitleKey="deals.subtitle"
      headerAction={hasPermission("deals.create") ? (
        <div className="page-header-actions">
          <button
            className="btn-primary"
            onClick={() => {
              setShowCreate(true);
              setCreateForm(emptyCreateForm);
              resetCreateSelector();
            }}
          >
            {t("deals.newDeal")}
          </button>
        </div>
      ) : undefined}
    >
      <div className="filter-bar">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">{t("deals.allStatuses")}</option>
          {STATUSES.map((s) => <option key={s} value={s}>{t(`deals.status_${s}`)}</option>)}
        </select>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* 新規作成 Modal（全項目）*/}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t("deals.newDeal")}
        size="md"
      >
        <form onSubmit={handleCreateSubmit}>
          <CompanyContactSelector
            value={{ companyId: createCompanyId, contactId: createContactId }}
            onChange={({ companyId: c, contactId: ct }) => {
              setCreateCompanyId(c);
              setCreateContactId(ct);
            }}
            required
            error={selectorError}
            companies={companies}
          />
          <div className="form-group"><label>{t("deals.leadSource")}</label>
            <input
              value={createForm.lead_source}
              placeholder={t("deals.leadSourcePlaceholder")}
              maxLength={50}
              onChange={(e) => setCreateForm({ ...createForm, lead_source: e.target.value })}
            />
          </div>
          <div className="form-group"><label>{t("deals.dealTitle")} *</label>
            <input required value={createForm.title} onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("deals.amount")}</label>
            <input type="number" min="0" step="1" value={createForm.amount} onChange={(e) => setCreateForm({ ...createForm, amount: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("common.currency")}</label>
            <select value={createForm.currency} onChange={(e) => setCreateForm({ ...createForm, currency: e.target.value })}>
              <option value="JPY">JPY</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
          <div className="form-group"><label>{t("common.status")}</label>
            <select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>
              {STATUSES.map((s) => <option key={s} value={s}>{t(`deals.status_${s}`)}</option>)}
            </select>
          </div>
          <div className="form-group"><label>{t("dashboard.stage")}</label>
            <select value={createForm.stage} onChange={(e) => setCreateForm({ ...createForm, stage: e.target.value })}>
              {STAGES.map((s) => <option key={s} value={s}>{t(`deals.stage_${s}`)}</option>)}
            </select>
          </div>
          <div className="form-group"><label>{t("deals.probability")}</label>
            <input type="number" min="0" max="100" value={createForm.probability} onChange={(e) => setCreateForm({ ...createForm, probability: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("deals.assignedTo")}</label>
            <input type="number" min="1" value={createForm.assigned_to} onChange={(e) => setCreateForm({ ...createForm, assigned_to: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("deals.expectedCloseDate")}</label>
            <input type="date" value={createForm.expected_close_date} onChange={(e) => setCreateForm({ ...createForm, expected_close_date: e.target.value })} />
          </div>
          {createForm.status === "lost" && (
            <>
              <div className="form-group"><label>{t("deals.lostReasonCode")}</label>
                <select
                  value={createForm.lost_reason_code}
                  onChange={(e) => setCreateForm({ ...createForm, lost_reason_code: e.target.value })}
                >
                  <option value="">{t("deals.lostReasonCodePlaceholder")}</option>
                  {LOST_REASON_CODES.map((code) => (
                    <option key={code} value={code}>{t(`deals.lostReasonCode_${code}`)}</option>
                  ))}
                </select>
              </div>
              {createForm.lost_reason_code === "other" && (
                <div className="form-group"><label>{t("deals.lostReason")}</label>
                  <textarea
                    value={createForm.lost_reason}
                    placeholder={t("deals.lostReasonPlaceholder")}
                    onChange={(e) => setCreateForm({ ...createForm, lost_reason: e.target.value })}
                  />
                </div>
              )}
            </>
          )}
          <div className="form-group"><label>{t("common.notes")}</label>
            <textarea value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.register")}</button>
          </div>
        </form>
      </Modal>

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (() => {
        const columns: DataTableColumn<Deal>[] = [
          { key: "title", header: t("deals.dealTitle") },
          { key: "company_id", header: t("common.company"), renderCell: (d) => companyName(d.company_id) },
          { key: "lead_source", header: t("deals.leadSource"), renderCell: (d) => d.lead_source || "-" },
          { key: "amount", header: t("deals.amount"), renderCell: (d) => d.amount ? fmt(d.amount, d.currency) : "-" },
          { key: "stage", header: t("dashboard.stage"), renderCell: (d) => d.stage ? (t(`deals.stage_${d.stage}`) || d.stage) : "-" },
          { key: "probability", header: t("deals.probability"), renderCell: (d) => d.probability != null ? `${d.probability}%` : "-" },
          { key: "status", header: t("common.status"), renderCell: (d) => <span className={`badge badge-${getStatusPresentation("deal", d.status).badgeVariant}`}>{t(`deals.status_${d.status}`) || d.status}</span> },
          { key: "actions", header: t("common.actions"), renderCell: (d) => (
            <span className="actions" onClick={(e) => e.stopPropagation()}>
              {hasPermission("deals.delete") && <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(d); }}>{t("common.delete")}</button>}
            </span>
          )},
        ];
        return (
          <DataTable<Deal>
            columns={columns}
            data={deals}
            rowKey={(d) => String(d.id)}
            emptyState={t("deals.noDeals")}
            onRowClick={hasPermission("deals.update") ? handleRowClick : undefined}
          />
        );
      })()}

      {/* 編集 Drawer（行クリックで開く・useRecordDrawer フック） */}
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={t("deals.editDeal")}
        onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/deals/${editId}/edit`); } : undefined}
      >
        {editForm && (
          <form onSubmit={handleEditSubmit}>
            <DealFormFields
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

      <ConfirmModal
        open={!!deleteTarget}
        title={t("deals.deleteDeal")}
        message={
          <>
            <strong>{deleteTarget?.title}</strong> {t("deals.deleteConfirmSuffix")}<br />
            {t("deals.deleteConstraint")}<br />
            {t("common.irreversible")}
          </>
        }
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
