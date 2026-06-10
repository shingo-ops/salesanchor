/**
 * 会社管理ページ。Phase 1-B-2 Step 5c-1 で新設。
 *
 * 新 B2B モデルの会社一覧・CRUD。既存 CustomersPage と並存する（Step 5d まで）。
 * 担当者は ContactsPage で別管理、複数支店対応や詳細編集は CompanyDetailPage で。
 * 本ページは一覧 + 基本属性 + billing/delivery 1 件ずつの住所を管理する最小構成。
 *
 * 変更履歴:
 *   2026-06-11: 編集を Drawer 化（useRecordDrawer, ADR-122 バッチC）
 */

import { useEffect, useState, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Modal } from "../../components/Modal";
import { Drawer } from "../../components/Drawer";
import ConfirmModal from "../../components/ConfirmModal";
import { PageLayout } from "../../components/PageLayout";
import { usePermissions } from "../../hooks/usePermissions";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { CompanyFormFields, type CompanyFormState } from "./CompanyFormFields";

const PHONE_RE = /^(\+?\d{10,15}|0\d{9,10})$/;
const validatePhoneClient = (raw: string): string | null => {
  if (!raw) return null;
  const cleaned = raw.replace(/[\s\-()]/g, "");
  // eslint-disable-next-line local/no-japanese-literal -- TODO: i18n対応（ADR-027 既知負債）
  return PHONE_RE.test(cleaned) ? null : "電話番号の形式が正しくありません（例: 03-1234-5678）";
};

interface CompanyAddress {
  id: number;
  address_type: "billing" | "delivery";
  branch_name: string | null;
  name: string | null;
  email: string | null;
  telephone: string | null;
  tax_id: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  address_line_3: string | null;
  city: string | null;
  state: string | null;
  zip: string | null;
  country_code: string | null;
  is_default: boolean;
}

interface Company {
  id: number;
  tenant_id: number;
  company_code: string;
  lead_id: number | null;
  sales_rep_id: number | null;
  name: string;
  name_en: string | null;
  normalized_name: string | null;
  industry: string | null;
  website: string | null;
  trust_level: number | null;
  priority_focus: string | null;
  per_order_amount: string | null;
  monthly_frequency: number | null;
  monthly_forecast: string | null;
  monthly_forecast_source: string | null;
  monthly_forecast_updated_at: string | null;
  billing_display_name: string | null;
  payment_recipient_name: string | null;
  fedex_account: string | null;
  shipping_note: string | null;
  status: string;
  notes: string | null;
  addresses: CompanyAddress[];
  sales_channels: string[];
  created_at: string;
  updated_at: string;
}

type AddressFormState = {
  address_type: "billing" | "delivery";
  branch_name: string;
  name: string;
  email: string;
  telephone: string;
  tax_id: string;
  address_line_1: string;
  address_line_2: string;
  city: string;
  state: string;
  zip: string;
  country_code: string;
};

const emptyBilling: AddressFormState = {
  address_type: "billing",
  branch_name: "", name: "", email: "", telephone: "", tax_id: "",
  address_line_1: "", address_line_2: "",
  city: "", state: "", zip: "", country_code: "",
};
const emptyDelivery: AddressFormState = { ...emptyBilling, address_type: "delivery" };

type FormState = {
  company_code: string;
  name: string;
  name_en: string;
  industry: string;
  website: string;
  trust_level: string;
  priority_focus: string;
  per_order_amount: string;
  monthly_frequency: string;
  monthly_forecast: string;
  billing_display_name: string;
  payment_recipient_name: string;
  fedex_account: string;
  shipping_note: string;
  status: string;
  notes: string;
  billing: AddressFormState;
  delivery: AddressFormState;
  sales_channels: string;
};

const emptyForm: FormState = {
  company_code: "",
  name: "",
  name_en: "",
  industry: "",
  website: "",
  trust_level: "",
  priority_focus: "",
  per_order_amount: "",
  monthly_frequency: "",
  monthly_forecast: "",
  billing_display_name: "",
  payment_recipient_name: "",
  fedex_account: "",
  shipping_note: "",
  status: "active",
  notes: "",
  billing: { ...emptyBilling },
  delivery: { ...emptyDelivery },
  sales_channels: "",
};

const emptyEditForm: CompanyFormState = {
  name: "", status: "active", industry: "", priority_focus: "", notes: "",
};

const toForm = (c: Company): CompanyFormState => ({
  name: c.name || "",
  status: c.status,
  industry: c.industry || "",
  priority_focus: c.priority_focus || "",
  notes: c.notes || "",
});

type Tab = "basic" | "billing" | "delivery";

const companyDisplayName = (c: Company): string => {
  return c.billing_display_name || c.name || c.company_code || "-";
};

const defaultAddress = (c: Company, t: "billing" | "delivery"): CompanyAddress | undefined => {
  const list = c.addresses.filter((a) => a.address_type === t);
  return list.find((a) => a.is_default) || list[0];
};

const addressDisplay = (a: CompanyAddress | undefined): string => {
  if (!a) return "-";
  return a.email || a.telephone || a.city || "-";
};

export default function CompaniesPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [search, setSearch] = useState("");
  // 新規作成モーダル
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<FormState>(emptyForm);
  const [activeTab, setActiveTab] = useState<Tab>("basic");
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [addressesDirty, setAddressesDirty] = useState(false);
  // 編集ドロワー
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Company, CompanyFormState>({ toForm, emptyForm: emptyEditForm });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Company | null>(null);

  const loadCompanies = async () => {
    try {
      // per_page=100 で全件を一画面に表示（highlife-jpn: 49 社、将来の増加余地あり）
      const parts: string[] = ["per_page=100"];
      if (search) parts.push(`search=${encodeURIComponent(search)}`);
      const data = await api.get<Company[]>(`/companies?${parts.join("&")}`);
      setCompanies(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadCompanies(); }, [search]);

  const toNull = (v: string) => (v ? v : null);

  /* ── 新規作成（Modal） ── */
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const phoneErr = validatePhoneClient(createForm.billing.telephone);
    if (phoneErr) {
      setPhoneError(phoneErr);
      setActiveTab("billing");
      return;
    }
    setPhoneError(null);

    const addressHasAnyValue = (a: AddressFormState) =>
      a.branch_name || a.name || a.email || a.telephone || a.tax_id ||
      a.address_line_1 || a.address_line_2 ||
      a.city || a.state || a.zip || a.country_code;

    const addresses: Record<string, unknown>[] = [];
    if (addressHasAnyValue(createForm.billing)) {
      addresses.push({
        address_type: "billing",
        branch_name: toNull(createForm.billing.branch_name),
        name: toNull(createForm.billing.name),
        email: toNull(createForm.billing.email),
        telephone: toNull(createForm.billing.telephone),
        tax_id: toNull(createForm.billing.tax_id),
        address_line_1: toNull(createForm.billing.address_line_1),
        address_line_2: toNull(createForm.billing.address_line_2),
        city: toNull(createForm.billing.city),
        state: toNull(createForm.billing.state),
        zip: toNull(createForm.billing.zip),
        country_code: toNull(createForm.billing.country_code),
        is_default: true,
      });
    }
    if (addressHasAnyValue(createForm.delivery)) {
      addresses.push({
        address_type: "delivery",
        branch_name: toNull(createForm.delivery.branch_name),
        name: toNull(createForm.delivery.name),
        email: toNull(createForm.delivery.email),
        telephone: toNull(createForm.delivery.telephone),
        tax_id: toNull(createForm.delivery.tax_id),
        address_line_1: toNull(createForm.delivery.address_line_1),
        address_line_2: toNull(createForm.delivery.address_line_2),
        city: toNull(createForm.delivery.city),
        state: toNull(createForm.delivery.state),
        zip: toNull(createForm.delivery.zip),
        country_code: toNull(createForm.delivery.country_code),
        is_default: true,
      });
    }

    const salesChannels = createForm.sales_channels
      .split(/[,、，]/)
      .map((s) => s.trim())
      .filter(Boolean);

    const payload: Record<string, unknown> = {
      name: createForm.name.trim(),
      name_en: toNull(createForm.name_en),
      industry: toNull(createForm.industry),
      website: toNull(createForm.website),
      priority_focus: toNull(createForm.priority_focus),
      per_order_amount: createForm.per_order_amount || null,
      monthly_frequency: createForm.monthly_frequency ? parseInt(createForm.monthly_frequency, 10) : null,
      monthly_forecast: createForm.monthly_forecast || null,
      billing_display_name: toNull(createForm.billing_display_name),
      payment_recipient_name: toNull(createForm.payment_recipient_name),
      fedex_account: toNull(createForm.fedex_account),
      shipping_note: toNull(createForm.shipping_note),
      status: createForm.status || "active",
      notes: toNull(createForm.notes),
      sales_channels: salesChannels,
      addresses,
    };
    if (createForm.company_code.trim()) {
      payload.company_code = createForm.company_code.trim();
    }

    if (submitting) return;
    setSubmitting(true);
    try {
      await api.post("/companies", payload);
      setShowCreate(false);
      setCreateForm(emptyForm);
      setActiveTab("basic");
      setAddressesDirty(false);
      loadCompanies();
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
      await api.patch(`/companies/${editId}`, {
        name: editForm.name,
        status: editForm.status,
        industry: toNull(editForm.industry),
        priority_focus: toNull(editForm.priority_focus),
        notes: toNull(editForm.notes),
      });
      closeDrawer();
      loadCompanies();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/companies/${deleteTarget.id}`);
      setDeleteTarget(null);
      loadCompanies();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
      setDeleteTarget(null);
    }
  };

  // PR #145 Q2: pending_dedup_review の件数を一覧サマリで提示し、解消フローへの導線を強める
  const pendingDedupCount = companies.filter((c) => c.status === "pending_dedup_review").length;

  return (
    <PageLayout
      navKey="nav.companies"
      subtitleKey="companies.subtitle"
      headerAction={
        <div className="page-header-actions">
          {pendingDedupCount > 0 && (
            <span className="dedup-summary">
              {t("companies.pendingDedupCount", { count: pendingDedupCount })}
            </span>
          )}
          <input
            type="text"
            placeholder={t("companies.searchPlaceholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          {hasPermission("customers.create") && (
            <button
              className="btn-primary"
              onClick={() => {
                setCreateForm(emptyForm);
                setActiveTab("basic");
                setPhoneError(null);
                setAddressesDirty(false);
                setShowCreate(true);
              }}
            >
              + {t("companies.newCompany")}
            </button>
          )}
        </div>
      }
    >

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <p>{t("common.loading")}</p>
      ) : (() => {
        const columns: DataTableColumn<Company>[] = [
          { key: "name", header: t("common.name"), renderCell: (c) => (
            /* 詳細ページへ: multi_branch 住所編集 / 担当者タブ / 販売チャネル */
            <Link to={`/companies/${c.id}`}>{companyDisplayName(c)}</Link>
          )},
          { key: "industry", header: t("companies.industry"), renderCell: (c) => c.industry || "-" },
          { key: "status", header: t("common.status"), renderCell: (c) => <span className={`status-badge status-${c.status}`}>{c.status}</span> },
          { key: "billing", header: t("companies.billing"), renderCell: (c) => addressDisplay(defaultAddress(c, "billing")) },
          { key: "delivery", header: t("companies.delivery"), renderCell: (c) => addressDisplay(defaultAddress(c, "delivery")) },
          { key: "actions", header: t("common.actions"), renderCell: (c) => (
            <>
              <Link to={`/companies/${c.id}`} className="btn-sm" onClick={(e) => e.stopPropagation()}>{t("companies.viewDetail")}</Link>
              {hasPermission("customers.update") && (
                <button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(c); }}>{t("common.edit")}</button>
              )}
              {hasPermission("customers.delete") && (
                <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(c); }}>{t("common.delete")}</button>
              )}
            </>
          )},
        ];
        return (
          <DataTable<Company>
            columns={columns}
            data={companies}
            rowKey={(c) => String(c.id)}
            rowClassName={(c) => c.status === "pending_dedup_review" ? "row-pending-dedup" : ""}
            onRowClick={hasPermission("customers.update") ? handleRowClick : undefined}
            emptyState={t("companies.noCompanies")}
          />
        );
      })()}

      {/* 新規作成 Modal（全項目・既存 UX 保持） */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t("companies.newCompany")}
        size="lg"
      >
        <div className="modal-content-wide">
          <div className="tabs">
            <button className={`tab ${activeTab === "basic" ? "active" : ""}`} onClick={() => setActiveTab("basic")}>{t("companies.basicInfo")}</button>
            <button className={`tab ${activeTab === "billing" ? "active" : ""}`} onClick={() => setActiveTab("billing")}>{t("companies.billing")}</button>
            <button className={`tab ${activeTab === "delivery" ? "active" : ""}`} onClick={() => setActiveTab("delivery")}>{t("companies.delivery")}</button>
          </div>

            <form onSubmit={handleCreateSubmit} className="form-grid">
              {activeTab === "basic" && (
                <>
                  <div className="form-row">
                    <label>{t("companies.companyCodeLabel")}</label>
                    <input value={createForm.company_code} onChange={(e) => setCreateForm({ ...createForm, company_code: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.nameLabel")}</label>
                    <input required value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.nameEn")}</label>
                    <input value={createForm.name_en} onChange={(e) => setCreateForm({ ...createForm, name_en: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.industry")}</label>
                    <input value={createForm.industry} onChange={(e) => setCreateForm({ ...createForm, industry: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.website")}</label>
                    <input value={createForm.website} onChange={(e) => setCreateForm({ ...createForm, website: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.priorityFocus")}</label>
                    <input value={createForm.priority_focus} onChange={(e) => setCreateForm({ ...createForm, priority_focus: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.perOrderAmount")}</label>
                    <input value={createForm.per_order_amount} onChange={(e) => setCreateForm({ ...createForm, per_order_amount: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.monthlyFrequency")}</label>
                    <input type="number" min="0" value={createForm.monthly_frequency} onChange={(e) => setCreateForm({ ...createForm, monthly_frequency: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.monthlyForecast")}</label>
                    <input value={createForm.monthly_forecast} onChange={(e) => setCreateForm({ ...createForm, monthly_forecast: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.billingDisplayName")}</label>
                    <input value={createForm.billing_display_name} onChange={(e) => setCreateForm({ ...createForm, billing_display_name: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.paymentRecipientName")}</label>
                    <input value={createForm.payment_recipient_name} onChange={(e) => setCreateForm({ ...createForm, payment_recipient_name: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.fedexAccount")}</label>
                    <input value={createForm.fedex_account} onChange={(e) => setCreateForm({ ...createForm, fedex_account: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.shippingNote")}</label>
                    <textarea value={createForm.shipping_note} onChange={(e) => setCreateForm({ ...createForm, shipping_note: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("companies.salesChannelsLabel")}</label>
                    <input value={createForm.sales_channels} onChange={(e) => setCreateForm({ ...createForm, sales_channels: e.target.value })} />
                  </div>
                  <div className="form-row">
                    <label>{t("common.status")}</label>
                    <select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>
                      <option value="active">active</option>
                      <option value="inactive">inactive</option>
                      <option value="archived">archived</option>
                      <option value="pending_dedup_review">pending_dedup_review</option>
                    </select>
                  </div>
                  <div className="form-row">
                    <label>{t("common.notes")}</label>
                    <textarea value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />
                  </div>
                </>
              )}

              {(activeTab === "billing" || activeTab === "delivery") && (() => {
                const key = activeTab;
                const addr = createForm[key];
                const setAddr = (patch: Partial<AddressFormState>) => {
                  setAddressesDirty(true);
                  setCreateForm({ ...createForm, [key]: { ...addr, ...patch } });
                };
                return (
                  <>
                    <div className="form-row">
                      <label>{t("companies.branchNameLabel")}</label>
                      <input value={addr.branch_name} onChange={(e) => setAddr({ branch_name: e.target.value })} />
                    </div>
                    <div className="form-row"><label>{t("companies.contactName")}</label><input value={addr.name} onChange={(e) => setAddr({ name: e.target.value })} /></div>
                    <div className="form-row"><label>{t("common.email")}</label><input type="email" value={addr.email} onChange={(e) => setAddr({ email: e.target.value })} /></div>
                    <div className="form-row">
                      <label>{t("common.phone")}</label>
                      <input value={addr.telephone} onChange={(e) => setAddr({ telephone: e.target.value })} />
                      {key === "billing" && phoneError && <span className="field-error">{t("companies.phoneError")}</span>}
                    </div>
                    <div className="form-row"><label>{t("companies.taxId")}</label><input value={addr.tax_id} onChange={(e) => setAddr({ tax_id: e.target.value })} /></div>
                    <div className="form-row"><label>{t("shipping.address1")}</label><input value={addr.address_line_1} onChange={(e) => setAddr({ address_line_1: e.target.value })} /></div>
                    <div className="form-row"><label>{t("shipping.address2")}</label><input value={addr.address_line_2} onChange={(e) => setAddr({ address_line_2: e.target.value })} /></div>
                    <div className="form-row"><label>{t("shipping.city")}</label><input value={addr.city} onChange={(e) => setAddr({ city: e.target.value })} /></div>
                    <div className="form-row"><label>{t("shipping.stateCode")}</label><input value={addr.state} onChange={(e) => setAddr({ state: e.target.value })} /></div>
                    <div className="form-row"><label>{t("shipping.zipCode")}</label><input value={addr.zip} onChange={(e) => setAddr({ zip: e.target.value })} /></div>
                    <div className="form-row"><label>{t("companies.countryCodeWithHint")}</label><input value={addr.country_code} onChange={(e) => setAddr({ country_code: e.target.value })} maxLength={2} /></div>
                  </>
                );
              })()}

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
        title={t("companies.editCompany")}
        onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/crm/companies/${editId}`); } : undefined}
      >
        <form onSubmit={handleEditSubmit}>
          <CompanyFormFields
            form={editForm}
            onChange={(field, value) => setEditForm((prev) => ({ ...prev, [field]: value }))}
          />
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={closeDrawer}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      </Drawer>

      <ConfirmModal
        open={deleteTarget !== null}
        title={t("companies.deleteCompany")}
        message={
          deleteTarget
            ? t("companies.deleteConfirmMessage", {
                name: companyDisplayName(deleteTarget),
                code: deleteTarget.company_code,
              })
            : ""
        }
        confirmLabel={t("common.delete")}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
