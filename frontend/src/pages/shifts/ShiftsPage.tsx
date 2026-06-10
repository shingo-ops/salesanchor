import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { Modal } from "../../components/Modal";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";

interface Shift { id: number; user_id: number; shift_date: string; start_time: string; end_time: string; shift_type: string; notes: string | null; created_at: string; }

export default function ShiftsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ user_id: "", shift_date: "", start_time: "09:00", end_time: "18:00", shift_type: "normal", notes: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try { setShifts(await api.get<Shift[]>("/shifts")); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.fetchError")); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    try {
      await api.post("/shifts", { user_id: Number(form.user_id), shift_date: form.shift_date, start_time: form.start_time, end_time: form.end_time, shift_type: form.shift_type, notes: form.notes || null });
      setShowForm(false); load();
    } catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }
  };

  const handleDelete = async (id: number) => {
    try { await api.delete(`/shifts/${id}`); load(); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.deleteError")); }
  };

  return (
    <PageLayout
      navKey="nav.shifts"
      subtitleKey="shifts.subtitle"
      headerAction={hasPermission("shifts.manage") ? (
        <div className="page-header-actions">
          <button className="btn-primary" onClick={() => setShowForm(true)}>{t("shifts.newShift")}</button>
        </div>
      ) : undefined}
    >
      {error && <div className="error-message">{error}</div>}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={t("shifts.newShift")}
        size="md"
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group"><label>{t("shifts.userId")} *</label><input type="number" min="1" required value={form.user_id} onChange={e => setForm({ ...form, user_id: e.target.value })} /></div>
          <div className="form-group"><label>{t("common.date")} *</label><input type="date" required value={form.shift_date} onChange={e => setForm({ ...form, shift_date: e.target.value })} /></div>
          <div className="form-group"><label>{t("shifts.startTime")} *</label><input type="time" required value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })} /></div>
          <div className="form-group"><label>{t("shifts.endTime")} *</label><input type="time" required value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })} /></div>
          <div className="form-group"><label>{t("shifts.shiftType")}</label>
            <select value={form.shift_type} onChange={e => setForm({ ...form, shift_type: e.target.value })}>
              <option value="normal">{t("shifts.type_normal")}</option><option value="early">{t("shifts.type_early")}</option><option value="late">{t("shifts.type_late")}</option><option value="night">{t("shifts.type_night")}</option><option value="off">{t("shifts.type_off")}</option>
            </select>
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.register")}</button>
          </div>
        </form>
      </Modal>
      {loading ? <div className="loading">{t("common.loading")}</div> : (() => {
        const columns: DataTableColumn<Shift>[] = [
          {
            key: "shift_date",
            header: t("common.date"),
          },
          {
            key: "user_id",
            header: t("shifts.userId"),
            renderCell: (s) => String(s.user_id),
          },
          {
            key: "start_time",
            header: t("shifts.colStart"),
          },
          {
            key: "end_time",
            header: t("shifts.colEnd"),
          },
          {
            key: "shift_type",
            header: t("shifts.shiftType"),
            renderCell: (s) => <span className="badge badge-negotiating">{s.shift_type}</span>,
          },
          {
            key: "actions",
            header: t("common.actions"),
            renderCell: (s) => (
              <span className="actions">
                {hasPermission("shifts.manage") && <button className="btn-sm btn-danger" onClick={() => handleDelete(s.id)}>{t("common.delete")}</button>}
              </span>
            ),
          },
        ];
        return (
          <DataTable
            columns={columns}
            data={shifts}
            rowKey={(s) => String(s.id)}
            emptyState={<span>{t("shifts.noShifts")}</span>}
          />
        );
      })()}
    </PageLayout>
  );
}
