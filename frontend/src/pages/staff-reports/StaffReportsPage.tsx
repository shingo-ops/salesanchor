import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { Modal } from "../../components/Modal";
import { Select } from "../../components/Select";

interface StaffReport {
  id: number; report_code: string | null; report_type: string; user_id: number; period: string;
  review: string | null; goals: string | null; challenges: string | null;
  reviewer_comment: string | null; reviewed_at: string | null; submitted_at: string | null; created_at: string;
}
export default function StaffReportsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const TYPE_LABELS: Record<string, string> = {
    daily: "Daily",
    weekly: "Weekly",
    monthly: "Monthly",
  };
  const [reports, setReports] = useState<StaffReport[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ report_type: "daily", period: "", review: "", goals: "", challenges: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");

  const load = async () => {
    try { setReports(await api.get<StaffReport[]>(`/staff-reports${typeFilter ? `?report_type=${typeFilter}` : ""}`)); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.fetchError")); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [typeFilter]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    try {
      await api.post("/staff-reports", {
        report_type: form.report_type, period: form.period, review: form.review,
        goals: form.goals || null, challenges: form.challenges || null,
      });
      setShowForm(false); setForm({ report_type: "daily", period: "", review: "", goals: "", challenges: "" }); load();
    } catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }
  };

  return (
    <PageLayout
      navKey="nav.reports"
      subtitleKey="reports.subtitle"
    >
      <ContentToolbar
        left={
          <Select
            className="field-h-md field-w-sm"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            placeholder={t("common.all")}
            options={Object.entries(TYPE_LABELS).map(([k, v]) => ({
              value: k,
              label: v,
            }))}
          />
        }
        right={hasPermission("staff_reports.create") ? (
          <button className="btn-primary field-h-md" onClick={() => setShowForm(true)}>{t("common.add")}</button>
        ) : undefined}
      />
      {error && <div className="error-message">{error}</div>}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={t("common.add")}
        size="md"
      >
        <form onSubmit={handleSubmit}>
          <Select
            label={t("common.type")}
            value={form.report_type}
            onChange={(e) => setForm({ ...form, report_type: e.target.value })}
            options={Object.entries(TYPE_LABELS).map(([k, v]) => ({
              value: k,
              label: v,
            }))}
          />
          <div className="form-group"><label>{t("common.date")} *</label><input required value={form.period} onChange={e => setForm({ ...form, period: e.target.value })} /></div>
          <div className="form-group"><label>{t("common.description")} *</label><textarea required value={form.review} onChange={e => setForm({ ...form, review: e.target.value })} style={{ minHeight: 'var(--textarea-min-h-lg)' }} /></div>
          <div className="form-group"><label>{t("common.notes")}</label><textarea value={form.goals} onChange={e => setForm({ ...form, goals: e.target.value })} /></div>
          <div className="form-group"><label>{t("common.notes")}</label><textarea value={form.challenges} onChange={e => setForm({ ...form, challenges: e.target.value })} /></div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.add")}</button>
          </div>
        </form>
      </Modal>
      {loading ? <div className="loading">{t("common.loading")}</div> : (
        <table className="data-table">
          <thead><tr><th>{t("common.code")}</th><th>{t("common.type")}</th><th>{t("common.date")}</th><th>{t("common.createdAt")}</th><th>{t("common.status")}</th></tr></thead>
          <tbody>
            {reports.map(r => (
              <tr key={r.id}>
                <td className="mono">{r.report_code || "-"}</td>
                <td><span className="badge badge-negotiating">{TYPE_LABELS[r.report_type] || r.report_type}</span></td>
                <td>{r.period}</td>
                <td>{r.submitted_at ? new Date(r.submitted_at).toLocaleDateString() : "-"}</td>
                <td>{r.reviewed_at ? <span className="badge badge-won">{t("common.confirm")}</span> : <span className="badge badge-pending">{t("common.notSet")}</span>}</td>
              </tr>
            ))}
            {reports.length === 0 && <tr><td colSpan={5} className="empty">{t("common.noData")}</td></tr>}
          </tbody>
        </table>
      )}
    </PageLayout>
  );
}
