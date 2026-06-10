/**
 * チーム管理ページ。
 * チームのCRUD＋メンバー管理。
 *
 * 変更履歴:
 *   2026-04-16: 初版作成（Phase 1）
 */

import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { Modal } from "../../components/Modal";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import "./TeamsPage.css";

interface Team {
  id: number;
  name: string;
  leader_id: number | null;
  description: string | null;
  is_active: boolean;
  member_count: number | null;
  created_at: string;
  updated_at: string;
}

interface TeamMember {
  user_id: number;
  username: string | null;
  email: string | null;
  joined_at: string;
}

const emptyForm = { name: "", leader_id: "", description: "" };

export default function TeamsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [teams, setTeams] = useState<Team[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Team | null>(null);
  const [membersPanel, setMembersPanel] = useState<Team | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [newMemberId, setNewMemberId] = useState("");

  const loadTeams = async () => {
    try {
      const data = await api.get<Team[]>("/teams");
      setTeams(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  const loadMembers = async (teamId: number) => {
    try {
      const data = await api.get<TeamMember[]>(`/teams/${teamId}/members`);
      setMembers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadTeams(); }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      name: form.name,
      leader_id: form.leader_id ? Number(form.leader_id) : null,
      description: form.description || null,
    };
    try {
      if (editId) {
        await api.patch(`/teams/${editId}`, payload);
      } else {
        await api.post("/teams", payload);
      }
      setShowForm(false);
      setEditId(null);
      setForm(emptyForm);
      loadTeams();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleEdit = (t: Team) => {
    setEditId(t.id);
    setForm({
      name: t.name,
      leader_id: t.leader_id != null ? String(t.leader_id) : "",
      description: t.description || "",
    });
    setShowForm(true);
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleteTarget(null);
    try {
      await api.delete(`/teams/${id}`);
      loadTeams();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const openMembers = async (team: Team) => {
    setMembersPanel(team);
    await loadMembers(team.id);
  };

  const addMember = async (e: FormEvent) => {
    e.preventDefault();
    if (!membersPanel) return;
    try {
      await api.post(`/teams/${membersPanel.id}/members`, { user_id: Number(newMemberId) });
      setNewMemberId("");
      loadMembers(membersPanel.id);
      loadTeams();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    }
  };

  const removeMember = async (userId: number) => {
    if (!membersPanel) return;
    try {
      await api.delete(`/teams/${membersPanel.id}/members/${userId}`);
      loadMembers(membersPanel.id);
      loadTeams();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  return (
    <PageLayout
      navKey="nav.teams"
      subtitleKey="teams.subtitle"
      headerAction={hasPermission("teams.create") ? (
        <div className="page-header-actions">
          <button className="btn-primary" onClick={() => { setShowForm(true); setEditId(null); setForm(emptyForm); }}>{t("teams.newTeam")}</button>
        </div>
      ) : undefined}
    >
      {error && <div className="error-message">{error}</div>}

      <Modal
        open={showForm}
        onClose={() => { setShowForm(false); setEditId(null); setForm(emptyForm); }}
        title={editId ? t("teams.editTeam") : t("teams.newTeam")}
        size="md"
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group"><label>{t("teams.teamName")} *</label>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("teams.leaderUserIdLabel")}</label>
            <input type="number" min="1" value={form.leader_id} onChange={(e) => setForm({ ...form, leader_id: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("common.description")}</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => { setShowForm(false); setEditId(null); setForm(emptyForm); }}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{editId ? t("common.update") : t("common.create")}</button>
          </div>
        </form>
      </Modal>

      <Modal
        open={!!membersPanel}
        onClose={() => setMembersPanel(null)}
        title={membersPanel ? t("teams.manageMembersTitle", { name: membersPanel.name }) : ""}
        size="md"
      >
        {membersPanel && (
          <>
            {hasPermission("teams.manage_members") && (
              <form onSubmit={addMember} className="teams-add-member-form">
                <div className="form-group"><label>{t("teams.addUserIdLabel")}</label>
                  <input type="number" min="1" required value={newMemberId} onChange={(e) => setNewMemberId(e.target.value)} />
                </div>
                <button type="submit" className="btn-primary">{t("common.add")}</button>
              </form>
            )}
            {(() => {
              const memberColumns: DataTableColumn<TeamMember>[] = [
                { key: "username", header: t("teams.colUsername"), renderCell: (m) => m.username || "-" },
                { key: "email", header: t("common.email"), renderCell: (m) => m.email || "-" },
                { key: "joined_at", header: t("teams.colJoinedAt"), renderCell: (m) => new Date(m.joined_at).toLocaleDateString() },
                { key: "actions", header: t("common.actions"), renderCell: (m) => (
                  hasPermission("teams.manage_members")
                    ? <button className="btn-sm btn-danger" onClick={() => removeMember(m.user_id)}>{t("common.remove")}</button>
                    : null
                )},
              ];
              return (
                <DataTable<TeamMember>
                  columns={memberColumns}
                  data={members}
                  rowKey={(m) => String(m.user_id)}
                  emptyState={t("teams.noMembers")}
                />
              );
            })()}
          </>
        )}
      </Modal>

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (() => {
        const teamColumns: DataTableColumn<Team>[] = [
          { key: "name", header: t("teams.teamName") },
          { key: "description", header: t("common.description"), renderCell: (team) => team.description || "-" },
          { key: "member_count", header: t("teams.colMemberCount"), renderCell: (team) => String(team.member_count ?? 0) },
          { key: "leader_id", header: t("teams.colLeaderId"), renderCell: (team) => String(team.leader_id ?? "-") },
          { key: "actions", header: t("common.actions"), renderCell: (team) => (
            <span className="actions">
              <button className="btn-sm" onClick={() => openMembers(team)}>{t("teams.membersBtn")}</button>
              {hasPermission("teams.update") && <button className="btn-sm" onClick={() => handleEdit(team)}>{t("common.edit")}</button>}
              {hasPermission("teams.delete") && <button className="btn-sm btn-danger" onClick={() => setDeleteTarget(team)}>{t("common.delete")}</button>}
            </span>
          )},
        ];
        return (
          <DataTable<Team>
            columns={teamColumns}
            data={teams}
            rowKey={(team) => String(team.id)}
            emptyState={t("teams.noTeams")}
          />
        );
      })()}

      <ConfirmModal
        open={!!deleteTarget}
        title={t("teams.deleteTeam")}
        message={<><strong>{deleteTarget?.name}</strong>{t("common.deleteConfirmSuffix")}<br />{t("teams.memberDeleteNote")}</>}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
