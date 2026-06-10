/**
 * スタッフ管理ページ。Phase 1 再設計版。
 *
 * staff テーブル + staff_emails + staff_ui_preferences の CRUD。
 * UI設定はネストでまとめて編集可能。
 *
 * 変更履歴:
 *   2026-06-11: 編集を Drawer 化（useRecordDrawer, ADR-122 バッチB）
 */

import { useEffect, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { Drawer } from "../../components/Drawer";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { useUiPrefs } from "../../contexts/UiPrefsContext";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { PageLayout } from "../../components/PageLayout";
import { getStatusPresentation } from "../../utils/statusPresentation";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { StaffFormFields, type StaffFormState, type StaffRole } from "./StaffFormFields";

interface StaffUIPreferences {
  dark_mode: boolean;
  show_chat_menu: boolean;
  show_sales_menu: boolean;
  show_settings_menu: boolean;
  show_admin_menu: boolean;
  show_sidebar: boolean;
}

interface Staff {
  id: number;
  tenant_id: number;
  user_id: number | null;
  staff_code: string;
  surname_jp: string;
  given_name_jp: string;
  surname_kana: string | null;
  given_name_kana: string | null;
  surname_en: string | null;
  given_name_en: string | null;
  primary_email: string;
  discord_user_id: string | null;
  role_id: number;
  role_name: string | null;
  status: string;
  firebase_uid: string | null;
  emails: string[];
  ui_preferences: StaffUIPreferences | null;
  created_at: string;
  updated_at: string;
}

const emptyPrefs: StaffUIPreferences = {
  dark_mode: false,
  show_chat_menu: true,
  show_sales_menu: true,
  show_settings_menu: true,
  show_admin_menu: false,
  show_sidebar: true,
};

type CreateFormState = {
  staff_code: string;
  surname_jp: string;
  given_name_jp: string;
  surname_kana: string;
  given_name_kana: string;
  surname_en: string;
  given_name_en: string;
  primary_email: string;
  discord_user_id: string;
  role_id: string;
  status: string;
  firebase_uid: string;
  ui_preferences: StaffUIPreferences;
};

const emptyCreateForm: CreateFormState = {
  staff_code: "", surname_jp: "", given_name_jp: "",
  surname_kana: "", given_name_kana: "", surname_en: "", given_name_en: "",
  primary_email: "", discord_user_id: "", role_id: "", status: "active",
  firebase_uid: "", ui_preferences: { ...emptyPrefs },
};

const emptyEditForm: StaffFormState = {
  surname_jp: "", given_name_jp: "",
  primary_email: "", role_id: "", status: "active", discord_user_id: "",
};

const toForm = (s: Staff): StaffFormState => ({
  surname_jp: s.surname_jp,
  given_name_jp: s.given_name_jp,
  primary_email: s.primary_email,
  role_id: String(s.role_id),
  status: s.status,
  discord_user_id: s.discord_user_id ?? "",
});

export default function StaffPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const { selfStaffId } = useUiPrefs();
  const [staff, setStaff] = useState<Staff[]>([]);
  const [roles, setRoles] = useState<StaffRole[]>([]);
  // 新規作成モーダル
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<CreateFormState>(emptyCreateForm);
  // 編集ドロワー
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Staff, StaffFormState>({ toForm, emptyForm: emptyEditForm });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Staff | null>(null);

  const loadAll = async () => {
    try {
      const [s, r] = await Promise.all([
        api.get<Staff[]>("/staff"),
        api.get<StaffRole[]>("/roles"),
      ]);
      setStaff(s);
      setRoles(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadAll(); }, []);

  const toNull = (v: string) => (v ? v : null);

  /* ── 新規作成（Modal） ── */
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (submitting) return;
    setSubmitting(true);
    const payload: Record<string, unknown> = {
      surname_jp: createForm.surname_jp,
      given_name_jp: createForm.given_name_jp,
      surname_kana: toNull(createForm.surname_kana),
      given_name_kana: toNull(createForm.given_name_kana),
      surname_en: toNull(createForm.surname_en),
      given_name_en: toNull(createForm.given_name_en),
      primary_email: createForm.primary_email,
      discord_user_id: toNull(createForm.discord_user_id),
      role_id: parseInt(createForm.role_id, 10),
      status: createForm.status,
      firebase_uid: toNull(createForm.firebase_uid),
      ui_preferences: createForm.ui_preferences,
    };
    if (createForm.staff_code.trim()) payload.staff_code = createForm.staff_code.trim();
    try {
      await api.post("/staff", payload);
      setShowCreate(false);
      setCreateForm(emptyCreateForm);
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
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
      await api.patch(`/staff/${editId}`, {
        surname_jp: editForm.surname_jp,
        given_name_jp: editForm.given_name_jp,
        primary_email: editForm.primary_email,
        role_id: parseInt(editForm.role_id, 10),
        status: editForm.status,
        discord_user_id: toNull(editForm.discord_user_id),
      });
      closeDrawer();
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleteTarget(null);
    try {
      await api.delete(`/staff/${id}`);
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.deleteError"));
    }
  };

  return (
    <PageLayout
      navKey="nav.staff"
      subtitleKey="staff.subtitle"
      headerAction={hasPermission("staff.create") ? (
        <div className="page-header-actions">
          <button className="btn-primary" onClick={() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}>
            {t("staff.newStaff")}
          </button>
        </div>
      ) : undefined}
    >
      {error && <div className="error-message">{error}</div>}

      {/* 新規作成 Modal（全項目・既存 UX 保持） */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t("staff.newStaff")}
        size="md"
      >
        <form onSubmit={handleCreateSubmit}>
          <div className="form-group">
            <label>{t("staff.staffCodeLabel")}</label>
            <input value={createForm.staff_code} placeholder={t("staff.staffCodePlaceholder")} onChange={(e) => setCreateForm({ ...createForm, staff_code: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.surnameJp")} *</label>
            <input required value={createForm.surname_jp} onChange={(e) => setCreateForm({ ...createForm, surname_jp: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.givenNameJp")} *</label>
            <input required value={createForm.given_name_jp} onChange={(e) => setCreateForm({ ...createForm, given_name_jp: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.surnameKana")}</label>
            <input value={createForm.surname_kana} onChange={(e) => setCreateForm({ ...createForm, surname_kana: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.givenNameKana")}</label>
            <input value={createForm.given_name_kana} onChange={(e) => setCreateForm({ ...createForm, given_name_kana: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.surnameEn")}</label>
            <input value={createForm.surname_en} onChange={(e) => setCreateForm({ ...createForm, surname_en: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.givenNameEn")}</label>
            <input value={createForm.given_name_en} onChange={(e) => setCreateForm({ ...createForm, given_name_en: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.primaryEmail")} *</label>
            <input required type="email" value={createForm.primary_email} onChange={(e) => setCreateForm({ ...createForm, primary_email: e.target.value })} />
          </div>
          <div className="form-group"><label>Discord ID</label>
            <input value={createForm.discord_user_id} onChange={(e) => setCreateForm({ ...createForm, discord_user_id: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.role")} *</label>
            <select required value={createForm.role_id} onChange={(e) => setCreateForm({ ...createForm, role_id: e.target.value })}>
              <option value="">{t("common.pleaseSelect")}</option>
              {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div className="form-group"><label>{t("staff.status")}</label>
            <select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>
              <option value="active">{t("staff.status_active")}</option>
              <option value="inactive">{t("staff.status_inactive")}</option>
              <option value="pending">{t("staff.status_pending")}</option>
            </select>
          </div>
          <h4>{t("staff.uiPreferences")}</h4>
          {(() => {
            const labels: Record<keyof StaffUIPreferences, string> = {
              dark_mode: t("staff.darkMode"),
              show_chat_menu: t("staff.showChatMenu"),
              show_sales_menu: t("staff.showSalesMenu"),
              show_settings_menu: t("staff.showSettingsMenu"),
              show_admin_menu: t("staff.showAdminMenu"),
              show_sidebar: t("staff.showSidebar"),
            };
            return (Object.entries(labels) as Array<[keyof StaffUIPreferences, string]>).map(([k, label]) => (
              <div className="form-group" key={k}>
                <label>
                  <input type="checkbox" checked={createForm.ui_preferences[k as keyof StaffUIPreferences]} onChange={(e) => setCreateForm({ ...createForm, ui_preferences: { ...createForm.ui_preferences, [k]: e.target.checked } })} />
                  {" "}{label}
                </label>
              </div>
            ));
          })()}
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)} disabled={submitting}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? t("common.submitting") : t("common.register")}
            </button>
          </div>
        </form>
      </Modal>

      {/* 編集 Drawer（行クリックで開く・6 要点フィールド） */}
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={t("staff.editStaff")}
        onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/staff/${editId}/edit`); } : undefined}
      >
        <form onSubmit={handleEditSubmit}>
          <StaffFormFields
            form={editForm}
            onChange={(field, value) => setEditForm((prev) => ({ ...prev, [field]: value }))}
            roles={roles}
          />
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={closeDrawer}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      </Drawer>

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (() => {
        const columns: DataTableColumn<Staff>[] = [
          {
            key: "fullName",
            header: t("staff.fullName"),
            renderCell: (s) => `${s.surname_jp} ${s.given_name_jp}`,
          },
          {
            key: "email",
            header: t("common.email"),
            renderCell: (s) => (
              <>
                {s.primary_email}
                {s.emails.length > 0 && <span style={{ fontSize: "0.8em", color: "var(--text-muted)" }}> (+{s.emails.length})</span>}
              </>
            ),
          },
          {
            key: "role_name",
            header: t("staff.role"),
            renderCell: (s) => s.role_name || "-",
          },
          {
            key: "status",
            header: t("staff.status"),
            renderCell: (s) => (
              <span className={`badge badge-${getStatusPresentation("staff", s.status).badgeVariant}`}>
                {t(getStatusPresentation("staff", s.status).labelKey ?? `staff.status_${s.status}`)}
              </span>
            ),
          },
          {
            key: "actions",
            header: t("common.actions"),
            renderCell: (s) => (
              <span className="actions">
                {hasPermission("staff.update") && <button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(s); }}>{t("common.edit")}</button>}
                {hasPermission("staff.delete") && <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(s); }}>{t("common.delete")}</button>}
              </span>
            ),
          },
        ];
        return (
          <DataTable
            columns={columns}
            data={staff}
            rowKey={(s) => String(s.id)}
            onRowClick={hasPermission("staff.update") ? handleRowClick : undefined}
            emptyState={<span>{t("staff.noStaff")}</span>}
          />
        );
      })()}

      <ConfirmModal
        open={!!deleteTarget}
        title={t("staff.deleteStaff")}
        message={<><strong>{deleteTarget?.surname_jp} {deleteTarget?.given_name_jp}</strong>{t("common.deleteConfirmSuffix")}<br />{t("common.irreversible")}</>}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
