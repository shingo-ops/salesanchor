/**
 * StaffEditPage — スタッフフルページ編集（/staff/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * 全項目編集 + UI設定（ui_preferences）を含む。
 * 自分のレコード編集時は UiPrefsContext を refresh する。
 * 保存後は /staff 一覧へ戻る。
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";
import { useUiPrefs } from "../../contexts/UiPrefsContext";

interface StaffUIPreferences {
  dark_mode: boolean;
  show_chat_menu: boolean;
  show_sales_menu: boolean;
  show_settings_menu: boolean;
  show_admin_menu: boolean;
  show_sidebar: boolean;
}

interface Role {
  id: number;
  name: string;
}

interface Staff {
  id: number;
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
  status: string;
  firebase_uid: string | null;
  ui_preferences: StaffUIPreferences | null;
}

const emptyPrefs: StaffUIPreferences = {
  dark_mode: false,
  show_chat_menu: true,
  show_sales_menu: true,
  show_settings_menu: true,
  show_admin_menu: false,
  show_sidebar: true,
};

type FormState = {
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

const emptyForm: FormState = {
  surname_jp: "", given_name_jp: "",
  surname_kana: "", given_name_kana: "",
  surname_en: "", given_name_en: "",
  primary_email: "", discord_user_id: "",
  role_id: "", status: "active",
  firebase_uid: "", ui_preferences: { ...emptyPrefs },
};

export default function StaffEditPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { refresh: refreshUiPrefs, selfStaffId } = useUiPrefs();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [roles, setRoles] = useState<Role[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.get<Staff>(`/staff/${id}`),
      api.get<Role[]>("/roles"),
    ])
      .then(([staff, rs]) => {
        setForm({
          surname_jp: staff.surname_jp,
          given_name_jp: staff.given_name_jp,
          surname_kana: staff.surname_kana ?? "",
          given_name_kana: staff.given_name_kana ?? "",
          surname_en: staff.surname_en ?? "",
          given_name_en: staff.given_name_en ?? "",
          primary_email: staff.primary_email,
          discord_user_id: staff.discord_user_id ?? "",
          role_id: String(staff.role_id),
          status: staff.status,
          firebase_uid: staff.firebase_uid ?? "",
          ui_preferences: staff.ui_preferences || { ...emptyPrefs },
        });
        setRoles(rs);
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("common.fetchError")))
      .finally(() => setLoading(false));
  }, [id, t]);

  const toNull = (v: string) => (v ? v : null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.patch(`/staff/${id}`, {
        surname_jp: form.surname_jp,
        given_name_jp: form.given_name_jp,
        surname_kana: toNull(form.surname_kana),
        given_name_kana: toNull(form.given_name_kana),
        surname_en: toNull(form.surname_en),
        given_name_en: toNull(form.given_name_en),
        primary_email: form.primary_email,
        discord_user_id: toNull(form.discord_user_id),
        role_id: parseInt(form.role_id, 10),
        status: form.status,
        firebase_uid: toNull(form.firebase_uid),
        ui_preferences: form.ui_preferences,
      });
      const editedSelf = selfStaffId !== null && Number(id) === selfStaffId;
      if (editedSelf) await refreshUiPrefs();
      navigate("/staff");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <PageLayout navKey="nav.staff" subtitleKey="staff.subtitle">
      {error && <div className="error-message">{error}</div>}
      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <div className="form-group"><label>{t("staff.surnameJp")} *</label>
            <input required value={form.surname_jp} onChange={(e) => setForm({ ...form, surname_jp: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.givenNameJp")} *</label>
            <input required value={form.given_name_jp} onChange={(e) => setForm({ ...form, given_name_jp: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.surnameKana")}</label>
            <input value={form.surname_kana} onChange={(e) => setForm({ ...form, surname_kana: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.givenNameKana")}</label>
            <input value={form.given_name_kana} onChange={(e) => setForm({ ...form, given_name_kana: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.surnameEn")}</label>
            <input value={form.surname_en} onChange={(e) => setForm({ ...form, surname_en: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.givenNameEn")}</label>
            <input value={form.given_name_en} onChange={(e) => setForm({ ...form, given_name_en: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.primaryEmail")} *</label>
            <input required type="email" value={form.primary_email} onChange={(e) => setForm({ ...form, primary_email: e.target.value })} />
          </div>
          <div className="form-group"><label>Discord ID</label>
            <input value={form.discord_user_id} onChange={(e) => setForm({ ...form, discord_user_id: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("staff.role")} *</label>
            <select required value={form.role_id} onChange={(e) => setForm({ ...form, role_id: e.target.value })}>
              <option value="">{t("common.pleaseSelect")}</option>
              {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div className="form-group"><label>{t("staff.status")}</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="active">{t("staff.status_active")}</option>
              <option value="inactive">{t("staff.status_inactive")}</option>
              <option value="pending">{t("staff.status_pending")}</option>
            </select>
          </div>
          <div className="form-group"><label>Firebase UID</label>
            <input value={form.firebase_uid} onChange={(e) => setForm({ ...form, firebase_uid: e.target.value })} />
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
                  <input
                    type="checkbox"
                    checked={form.ui_preferences[k]}
                    onChange={(e) => setForm({ ...form, ui_preferences: { ...form.ui_preferences, [k]: e.target.checked } })}
                  />
                  {" "}{label}
                </label>
              </div>
            ));
          })()}

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => navigate("/staff")}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
