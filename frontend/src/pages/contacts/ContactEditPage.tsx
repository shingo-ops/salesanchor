/**
 * ContactEditPage — 担当者フルページ編集（/contacts/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * 全項目編集＋重複確認待ち（pending_dedup_review）の解消フローを含む。
 * 保存後は /contacts 一覧へ戻る。
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";

interface CompanyMini {
  id: number;
  company_code: string;
  name: string;
}

interface Contact {
  id: number;
  company_id: number;
  contact_code: string;
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
}

type FormState = {
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

const emptyForm: FormState = {
  company_id: "", surname: "", given_name: "", display_name: "",
  job_title: "", department: "", is_primary_contact: false,
  primary_email: "", primary_phone: "", status: "active", notes: "",
};

export default function ContactEditPage() {
  const { t }      = useTranslation();
  const { id }     = useParams<{ id: string }>();
  const navigate   = useNavigate();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [companies, setCompanies] = useState<CompanyMini[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [dedupSubmitting, setDedupSubmitting] = useState(false);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.get<Contact>(`/contacts/${id}`),
      api.get<CompanyMini[]>("/companies?per_page=100"),
    ])
      .then(([contact, cos]) => {
        setForm({
          company_id: String(contact.company_id),
          surname: contact.surname ?? "",
          given_name: contact.given_name ?? "",
          display_name: contact.display_name ?? "",
          job_title: contact.job_title ?? "",
          department: contact.department ?? "",
          is_primary_contact: contact.is_primary_contact,
          primary_email: contact.primary_email ?? "",
          primary_phone: contact.primary_phone ?? "",
          status: contact.status,
          notes: contact.notes ?? "",
        });
        setCompanies(cos);
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("common.fetchError")))
      .finally(() => setLoading(false));
  }, [id, t]);

  const toNull = (v: string) => (v ? v : null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.company_id) { setError(t("contacts.companyRequired")); return; }
    try {
      await api.patch(`/contacts/${id}`, {
        company_id: parseInt(form.company_id, 10),
        surname: toNull(form.surname),
        given_name: toNull(form.given_name),
        display_name: toNull(form.display_name),
        job_title: toNull(form.job_title),
        department: toNull(form.department),
        is_primary_contact: form.is_primary_contact,
        primary_email: toNull(form.primary_email),
        primary_phone: toNull(form.primary_phone),
        status: form.status,
        notes: toNull(form.notes),
      });
      navigate("/contacts");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleResolveAsDistinct = async () => {
    setError("");
    setDedupSubmitting(true);
    try {
      await api.patch(`/contacts/${id}`, { status: "active" });
      setForm((p) => ({ ...p, status: "active" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setDedupSubmitting(false);
    }
  };

  return (
    <PageLayout navKey="nav.contacts" subtitleKey="contacts.subtitle">
      {error && <div className="error-message">{error}</div>}
      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <div className="form-group">
            <label>{t("contacts.companyLabel")}</label>
            <select required value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
              <option value="">{t("common.pleaseSelect")}</option>
              {companies.map((c) => <option key={c.id} value={c.id}>{c.name}（{c.company_code}）</option>)}
            </select>
          </div>
          <div className="form-group"><label>{t("contacts.surname")}</label>
            <input value={form.surname} onChange={(e) => setForm({ ...form, surname: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("contacts.givenName")}</label>
            <input value={form.given_name} onChange={(e) => setForm({ ...form, given_name: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("contacts.displayName")}</label>
            <input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("contacts.position")}</label>
            <input value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("contacts.department")}</label>
            <input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
          </div>
          <div className="form-group">
            <label>
              <input type="checkbox" checked={form.is_primary_contact} onChange={(e) => setForm({ ...form, is_primary_contact: e.target.checked })} />
              {" "}{t("contacts.primaryContactHint")}
            </label>
          </div>
          <div className="form-group"><label>{t("common.email")}</label>
            <input type="email" value={form.primary_email} onChange={(e) => setForm({ ...form, primary_email: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("common.phone")}</label>
            <input value={form.primary_phone} onChange={(e) => setForm({ ...form, primary_phone: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("common.status")}</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
              <option value="archived">archived</option>
              <option value="pending_dedup_review">{t("contacts.statusPendingDedupOption")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("common.notes")}</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>

          {form.status === "pending_dedup_review" && (
            <div className="dedup-resolve-section">
              <h3>{t("contacts.dedupResolveTitle")}</h3>
              <p>{t("contacts.dedupResolveDesc")}</p>
              <div className="dedup-resolve-actions">
                <button type="button" className="btn-primary" onClick={handleResolveAsDistinct} disabled={dedupSubmitting}>
                  {t("contacts.confirmAsDistinctFull")}
                </button>
                <button type="button" disabled style={{ opacity: "var(--opacity-disabled)", cursor: "not-allowed" }}>
                  {t("contacts.mergeAsDuplicate")}
                </button>
              </div>
            </div>
          )}

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => navigate("/contacts")}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
