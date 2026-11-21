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

import { useState, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { Button } from "../../components/Button";
import { Drawer } from "../../components/Drawer";
import ConfirmModal from "../../components/ConfirmModal";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { usePermissions } from "../../hooks/usePermissions";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { CompanyFormFields, type CompanyFormState } from "./CompanyFormFields";
import { ButtonLink } from "../../components/ButtonLink";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock, Spinner } from "../../components/loading";
import { getStatusPresentation } from "../../utils/statusPresentation";
import { useCustomerStatuses } from "../../hooks/useCustomerStatuses";
import { CUSTOMER_STATUS_CODES } from "../../lib/customerStatuses";

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

const emptyEditForm: CompanyFormState = {
  name: "", status: CUSTOMER_STATUS_CODES.active, industry: "", priority_focus: "", notes: "",
};

const toForm = (c: Company): CompanyFormState => ({
  name: c.name || "",
  status: c.status,
  industry: c.industry || "",
  priority_focus: c.priority_focus || "",
  notes: c.notes || "",
});

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

/** 書いた後に取り直す写しの頭（ADR-1054） */
const COMPANIES_HEAD = ["companies"] as const;

export default function CompaniesPage() {
  const { t } = useTranslation();
  const customerStatuses = useCustomerStatuses();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  // 編集ドロワー
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Company, CompanyFormState>({ toForm, emptyForm: emptyEditForm });

  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Company | null>(null);

  // per_page=100 で全件を一画面に表示（highlife-jpn: 49 社、将来の増加余地あり）
  const parts: string[] = ["per_page=100"];
  if (search) parts.push(`search=${encodeURIComponent(search)}`);
  // 写しを先に出して裏で取り直す。検索を変えた時は前の行を出したまま取る（ADR-1054 段 2）
  const companiesQuery = useApiQuery<Company[]>(`/companies?${parts.join("&")}`, { keepPrevious: true });
  const invalidate = useInvalidateApi();
  const companies = companiesQuery.data ?? [];
  const shownError = error || (companiesQuery.error
    ? (companiesQuery.error instanceof Error ? companiesQuery.error.message : t("common.fetchError"))
    : "");
  /** 書いた後に一覧を取り直す（検索の違う写しも含む） */
  const loadCompanies = () => { void invalidate(COMPANIES_HEAD); };

  const toNull = (v: string) => (v ? v : null);

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
  const pendingDedupCount = companies.filter((c) => c.status === CUSTOMER_STATUS_CODES.pendingDedupReview).length;
  const headerAction = (
    <div className="page-header-actions">
      {pendingDedupCount > 0 && (
        <span className="dedup-summary">
          {t("companies.pendingDedupCount", { count: pendingDedupCount })}
        </span>
      )}
    </div>
  );
  return (
    <PageLayout
      navKey="nav.companies"
      subtitleKey="companies.subtitle"
      headerLeft={companiesQuery.isFetching && !companiesQuery.isPending ? <Spinner size="sm" /> : undefined}
      headerAction={headerAction}
    >

      {shownError && <div className="error-banner">{shownError}</div>}
      <ContentToolbar
        left={
          <TextFieldControl
            type="text"
            className="field-w-md"
            placeholder={t("companies.searchPlaceholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        }
      />

      {companiesQuery.isPending ? (
        <LoadingBlock />
      ) : (() => {
        const columns: DataTableColumn<Company>[] = [
          { key: "name", header: t("common.name"), renderCell: (c) => (
            /* 詳細ページへ: multi_branch 住所編集 / 担当者タブ / 販売チャネル */
            <Link to={`/companies/${c.id}`}>{companyDisplayName(c)}</Link>
          )},
          { key: "industry", header: t("companies.industry"), renderCell: (c) => c.industry || "-" },
          { key: "status", header: t("common.status"), renderCell: (c) => <span className={`badge badge-${getStatusPresentation("company", c.status).badgeVariant}`}>{customerStatuses.nameOf(c.status)}</span> },
          { key: "billing", header: t("companies.billing"), renderCell: (c) => addressDisplay(defaultAddress(c, "billing")) },
          { key: "delivery", header: t("companies.delivery"), renderCell: (c) => addressDisplay(defaultAddress(c, "delivery")) },
          { key: "actions", header: t("common.actions"), renderCell: (c) => (
            <>
              <ButtonLink variant="secondary" size="sm" to={`/companies/${c.id}`} onClick={(e) => e.stopPropagation()}>{t("companies.viewDetail")}</ButtonLink>
              {hasPermission("customers.update") && (
                <Button variant="secondary" size="sm" onClick={(e) => { e.stopPropagation(); handleRowClick(c); }}>{t("common.edit")}</Button>
              )}
              {hasPermission("customers.delete") && (
                <Button variant="danger" size="sm" onClick={(e) => { e.stopPropagation(); setDeleteTarget(c); }}>{t("common.delete")}</Button>
              )}
            </>
          )},
        ];
        return (
          <DataTable<Company>
            columns={columns}
            data={companies}
            rowKey={(c) => String(c.id)}
            rowClassName={(c) => c.status === CUSTOMER_STATUS_CODES.pendingDedupReview ? "row-pending-dedup" : ""}
            onRowClick={hasPermission("customers.update") ? handleRowClick : undefined}
            emptyState={t("companies.noCompanies")}
          />
        );
      })()}

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
            <Button variant="secondary" size="md" type="button" onClick={closeDrawer}>{t("common.cancel")}</Button>
            <Button variant="primary" size="md" type="submit">{t("common.update")}</Button>
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
