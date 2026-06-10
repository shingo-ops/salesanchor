/**
 * 担当者管理ページ。Phase 1-B-2 Step 5c-1 で新設。
 *
 * 新 B2B モデルの担当者一覧・CRUD。
 * 担当者は必ず 1 つの会社に紐付く（company_id 必須）。
 * 会社別絞り込みフィルタあり。
 * Step 5c-2 で CompanyDetailPage からネスト編集できるようになる予定。
 *
 * 変更履歴:
 *   2026-06-11: 編集を Drawer 化（useRecordDrawer, ADR-122 バッチB）
 */

import { useEffect, useState, FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Modal } from "../../components/Modal";
import { Drawer } from "../../components/Drawer";
import ConfirmModal from "../../components/ConfirmModal";
import { PageLayout } from "../../components/PageLayout";
import { usePermissions } from "../../hooks/usePermissions";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import ContactChannelLinks from "../../components/ContactChannelLinks";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { ContactFormFields, type ContactFormState, type ContactCompany } from "./ContactFormFields";

interface Contact {
  id: number;
  tenant_id: number;
  company_id: number;
  contact_code: string;
  lead_id: number | null;
  surname: string | null;
  given_name: string | null;
  display_name: string | null;
  job_title: string | null;
  department: string | null;
  is_primary_contact: boolean;
  primary_email: string | null;
  primary_phone: string | null;
  status: string;
  notes: string | null;
  emails: { id: number; email: string; purpose: string | null }[];
  discord: {
    is_joined: boolean;
    channel_id: string | null;
    user_id: string | null;
    invoice_webhook: string | null;
    shipment_webhook: string | null;
  } | null;
  contact_channels: { id: number; channel: string; purpose: string | null; is_primary: boolean }[];
  created_at: string;
  updated_at: string;
}

type CreateFormState = {
  contact_code: string;
  company_id: string;
  surname: string;
  given_name: string;
  display_name: string;
  job_title: string;
  department: string;
  is_primary_contact: boolean;
  primary_email: string;
  primary_phone: string;
  status: string;
  notes: string;
};

const emptyCreateForm: CreateFormState = {
  contact_code: "", company_id: "", surname: "", given_name: "",
  display_name: "", job_title: "", department: "", is_primary_contact: false,
  primary_email: "", primary_phone: "", status: "active", notes: "",
};

const emptyEditForm: ContactFormState = {
  company_id: "", surname: "", given_name: "",
  primary_email: "", primary_phone: "", status: "active",
};

const toForm = (c: Contact): ContactFormState => ({
  company_id: String(c.company_id),
  surname: c.surname ?? "",
  given_name: c.given_name ?? "",
  primary_email: c.primary_email ?? "",
  primary_phone: c.primary_phone ?? "",
  status: c.status,
});

const contactDisplayName = (c: Contact): string => {
  if (c.display_name) return c.display_name;
  const combined = `${c.surname || ""} ${c.given_name || ""}`.trim();
  return combined || c.contact_code || "-";
};

export default function ContactsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [companies, setCompanies] = useState<ContactCompany[]>([]);
  const [companyFilter, setCompanyFilter] = useState(searchParams.get("company_id") || "");
  const [search, setSearch] = useState("");
  // 新規作成モーダル
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<CreateFormState>(emptyCreateForm);
  // 編集ドロワー
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Contact, ContactFormState>({ toForm, emptyForm: emptyEditForm });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Contact | null>(null);
  const [dedupConfirmTarget, setDedupConfirmTarget] = useState<Contact | null>(null);
  const [dedupSubmitting, setDedupSubmitting] = useState(false);

  const loadContacts = async () => {
    try {
      const parts: string[] = [];
      if (search) parts.push(`search=${encodeURIComponent(search)}`);
      if (companyFilter) parts.push(`company_id=${encodeURIComponent(companyFilter)}`);
      parts.push("per_page=100");
      const data = await api.get<Contact[]>(`/contacts?${parts.join("&")}`);
      setContacts(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  const loadCompanies = async () => {
    try {
      const data = await api.get<ContactCompany[]>("/companies?per_page=100");
      setCompanies(data.map((c) => ({ id: c.id, company_code: c.company_code, name: c.name })));
    } catch {
      // 静かに無視
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadContacts(); }, [search, companyFilter]);
  useEffect(() => { loadCompanies(); }, []);

  const companyName = (company_id: number): string => {
    const c = companies.find((x) => x.id === company_id);
    return c ? `${c.name}（${c.company_code}）` : `#${company_id}`;
  };

  const toNull = (v: string) => (v ? v : null);

  /* ── 新規作成（Modal） ── */
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!createForm.company_id) { setError(t("contacts.companyRequired")); return; }
    if (submitting) return;
    setSubmitting(true);
    const payload: Record<string, unknown> = {
      company_id: parseInt(createForm.company_id, 10),
      surname: toNull(createForm.surname),
      given_name: toNull(createForm.given_name),
      display_name: toNull(createForm.display_name),
      job_title: toNull(createForm.job_title),
      department: toNull(createForm.department),
      is_primary_contact: createForm.is_primary_contact,
      primary_email: toNull(createForm.primary_email),
      primary_phone: toNull(createForm.primary_phone),
      status: createForm.status || "active",
      notes: toNull(createForm.notes),
    };
    if (createForm.contact_code.trim()) payload.contact_code = createForm.contact_code.trim();
    try {
      await api.post("/contacts", payload);
      setShowCreate(false);
      setCreateForm(emptyCreateForm);
      loadContacts();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSubmitting(false);
    }
  };

  /* ── ドロワー内編集保存（6 要点フィールド） ── */
  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!editId) return;
    try {
      await api.patch(`/contacts/${editId}`, {
        company_id: parseInt(editForm.company_id, 10),
        surname: toNull(editForm.surname),
        given_name: toNull(editForm.given_name),
        primary_email: toNull(editForm.primary_email),
        primary_phone: toNull(editForm.primary_phone),
        status: editForm.status,
      });
      closeDrawer();
      loadContacts();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/contacts/${deleteTarget.id}`);
      setDeleteTarget(null);
      loadContacts();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
      setDeleteTarget(null);
    }
  };

  const handleResolveAsDistinct = async () => {
    if (!dedupConfirmTarget) return;
    setError("");
    setDedupSubmitting(true);
    try {
      await api.patch(`/contacts/${dedupConfirmTarget.id}`, { status: "active" });
      setDedupConfirmTarget(null);
      await loadContacts();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
      setDedupConfirmTarget(null);
    } finally {
      setDedupSubmitting(false);
    }
  };

  const pendingDedupCount = contacts.filter((c) => c.status === "pending_dedup_review").length;

  return (
    <PageLayout
      navKey="nav.contacts"
      subtitleKey="contacts.subtitle"
      headerAction={
        <div className="page-header-actions">
          {pendingDedupCount > 0 && (
            <span className="dedup-summary">
              {t("contacts.pendingDedupCount", { count: pendingDedupCount })}
            </span>
          )}
          {hasPermission("customers.create") && (
            <button
              className="btn-primary"
              onClick={() => {
                setCreateForm({ ...emptyCreateForm, company_id: companyFilter });
                setShowCreate(true);
              }}
            >
              + {t("contacts.newContact")}
            </button>
          )}
        </div>
      }
    >
      <div className="filter-bar">
        <select value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)} className="search-input">
          <option value="">{t("contacts.allCompanies")}</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}（{c.company_code}）</option>
          ))}
        </select>
        <input
          type="text"
          placeholder={t("contacts.searchPlaceholder")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* 新規作成 Modal（全項目・既存 UX 保持） */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t("contacts.newContact")}
        size="lg"
      >
        <div className="modal-content-wide">
          <form onSubmit={handleCreateSubmit} className="form-grid">
            <div className="form-row">
              <label>{t("contacts.contactCodeLabel")}</label>
              <input value={createForm.contact_code} onChange={(e) => setCreateForm({ ...createForm, contact_code: e.target.value })} />
            </div>
            <div className="form-row">
              <label>{t("contacts.companyLabel")}</label>
              <select required value={createForm.company_id} onChange={(e) => setCreateForm({ ...createForm, company_id: e.target.value })}>
                <option value="">{t("common.pleaseSelect")}</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.name}（{c.company_code}）</option>)}
              </select>
            </div>
            <div className="form-row"><label>{t("contacts.surname")}</label>
              <input value={createForm.surname} onChange={(e) => setCreateForm({ ...createForm, surname: e.target.value })} />
            </div>
            <div className="form-row"><label>{t("contacts.givenName")}</label>
              <input value={createForm.given_name} onChange={(e) => setCreateForm({ ...createForm, given_name: e.target.value })} />
            </div>
            <div className="form-row"><label>{t("contacts.displayName")}</label>
              <input value={createForm.display_name} onChange={(e) => setCreateForm({ ...createForm, display_name: e.target.value })} />
            </div>
            <div className="form-row"><label>{t("contacts.position")}</label>
              <input value={createForm.job_title} onChange={(e) => setCreateForm({ ...createForm, job_title: e.target.value })} />
            </div>
            <div className="form-row"><label>{t("contacts.department")}</label>
              <input value={createForm.department} onChange={(e) => setCreateForm({ ...createForm, department: e.target.value })} />
            </div>
            <div className="form-row">
              <label>
                <input type="checkbox" checked={createForm.is_primary_contact} onChange={(e) => setCreateForm({ ...createForm, is_primary_contact: e.target.checked })} />
                {" "}{t("contacts.primaryContactHint")}
              </label>
            </div>
            <div className="form-row"><label>{t("common.email")}</label>
              <input type="email" value={createForm.primary_email} onChange={(e) => setCreateForm({ ...createForm, primary_email: e.target.value })} />
            </div>
            <div className="form-row"><label>{t("common.phone")}</label>
              <input value={createForm.primary_phone} onChange={(e) => setCreateForm({ ...createForm, primary_phone: e.target.value })} />
            </div>
            <div className="form-row"><label>{t("common.status")}</label>
              <select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>
                <option value="active">active</option>
                <option value="inactive">inactive</option>
                <option value="archived">archived</option>
              </select>
            </div>
            <div className="form-row"><label>{t("common.notes")}</label>
              <textarea value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />
            </div>
            <div className="form-actions">
              <button type="button" onClick={() => setShowCreate(false)} disabled={submitting}>{t("common.cancel")}</button>
              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? t("common.saving") : t("common.register")}
              </button>
            </div>
          </form>
        </div>
      </Modal>

      {/* 編集 Drawer（行クリックで開く・6 要点フィールド） */}
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={t("contacts.editContact")}
        onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/contacts/${editId}/edit`); } : undefined}
      >
        <form onSubmit={handleEditSubmit}>
          <ContactFormFields
            form={editForm}
            onChange={(field, value) => setEditForm((prev) => ({ ...prev, [field]: value }))}
            companies={companies}
          />
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={closeDrawer}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      </Drawer>

      {loading ? (
        <p>{t("common.loading")}</p>
      ) : (() => {
        const columns: DataTableColumn<Contact>[] = [
          { key: "name", header: t("common.name"), renderCell: (c) => contactDisplayName(c) },
          { key: "company_id", header: t("common.company"), renderCell: (c) => companyName(c.company_id) },
          { key: "job_title", header: t("contacts.position"), renderCell: (c) => c.job_title || "-" },
          { key: "primary_email", header: t("common.email"), renderCell: (c) => c.primary_email || "-" },
          { key: "primary_phone", header: t("common.phone"), renderCell: (c) => c.primary_phone || "-" },
          { key: "is_primary_contact", header: t("contacts.isPrimary"), renderCell: (c) => c.is_primary_contact ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "" },
          { key: "status", header: t("common.status"), renderCell: (c) => <span className={`status-badge status-${c.status}`}>{c.status}</span> },
          { key: "channels", header: t("nav.channels"), renderCell: (c) =>
            c.contact_channels.length > 0 ? <ContactChannelLinks contactId={c.id} /> : null
          },
          { key: "actions", header: t("common.actions"), renderCell: (c) => (
            <>
              {hasPermission("customers.update") && (
                <button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(c); }}>{t("common.edit")}</button>
              )}
              {hasPermission("customers.update") && c.status === "pending_dedup_review" && (
                <button className="btn-sm" onClick={(e) => { e.stopPropagation(); setDedupConfirmTarget(c); }}>
                  {t("contacts.confirmAsDistinct")}
                </button>
              )}
              {hasPermission("customers.delete") && (
                <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(c); }}>{t("common.delete")}</button>
              )}
            </>
          )},
        ];
        return (
          <DataTable<Contact>
            columns={columns}
            data={contacts}
            rowKey={(c) => String(c.id)}
            rowClassName={(c) => c.status === "pending_dedup_review" ? "row-pending-dedup" : ""}
            onRowClick={hasPermission("customers.update") ? handleRowClick : undefined}
            emptyState={t("contacts.noContacts")}
          />
        );
      })()}

      <ConfirmModal
        open={deleteTarget !== null}
        title={t("contacts.deleteContact")}
        message={deleteTarget ? t("contacts.deleteConfirmMessage", { name: contactDisplayName(deleteTarget), code: deleteTarget.contact_code }) : ""}
        confirmLabel={t("common.delete")}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
      <ConfirmModal
        open={dedupConfirmTarget !== null}
        title={t("contacts.dedupConfirmTitle")}
        message={dedupConfirmTarget ? t("contacts.dedupConfirmMessage", { name: contactDisplayName(dedupConfirmTarget), code: dedupConfirmTarget.contact_code }) : ""}
        confirmLabel={t("contacts.changeToActive")}
        onConfirm={handleResolveAsDistinct}
        onCancel={() => setDedupConfirmTarget(null)}
        danger={false}
      />
    </PageLayout>
  );
}
