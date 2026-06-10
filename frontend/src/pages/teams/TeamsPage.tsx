/**
 * チーム管理ページ。
 * チームのCRUD＋メンバー管理。
 *
 * 変更履歴:
 *   2026-04-16: 初版作成（Phase 1）
 *   2026-06-10: 編集を Drawer 化（useRecordDrawer, ADR-122 バッチA）
 */

import { useEffect, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { Modal } from "../../components/Modal";
import { Drawer } from "../../components/Drawer";
import { usePermissions } from "../../hooks/usePermissions";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { PageLayout } from "../../components/PageLayout";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { TeamFormFields, type TeamFormState } from "./TeamFormFields";
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

const emptyForm: TeamFormState = { name: "", leader_id: "", description: "" };

const toForm = (team: Team): TeamFormState => ({
  name: team.name,
  leader_id: team.leader_id != null ? String(team.leader_id) : "",
  description: team.description ?? "",
});

export default function TeamsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const [teams, setTeams] = useState<Team[]>([]);
  // 新規作成モーダル
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<TeamFormState>(emptyForm);
  // 編集ドロワー
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Team, TeamFormState>({ toForm, emptyForm });

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

  /* ── 新規作成（Modal） ── */
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/teams", {
        name: createForm.name,
        leader_id: createForm.leader_id ? Number(createForm.leader_id) : null,
        description: createForm.description || null,
      });
      setShowCreate(false);
      setCreateForm(emptyForm);
      loadTeams();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  /* ── ドロワー内編集保存 ── */
  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!editId) return;
    try {
      await api.patch(`/teams/${editId}`, {
        name: editForm.name,
        leader_id: editForm.leader_id ? Number(editForm.leader_id) : null,
        description: editForm.description || null,
      });
      closeDrawer();
      loadTeams();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
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
          <button className="btn-primary" onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }}>
            {t("teams.newTeam")}
          </button>
        </div>
      ) : undefined}
    >
      {error && <div className="error-message">{error}</div>}

      {/* 新規作成 Modal（既存 UX 保持） */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t("teams.newTeam")}
        size="md"
      >
        <form onSubmit={handleCreateSubmit}>
          <TeamFormFields
            form={createForm}
            onChange={(field, value) => setCreateForm((prev) => ({ ...prev, [field]: value }))}
          />
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>
              {t("common.cancel")}
            </button>
            <button type="submit" className="btn-primary">{t("common.create")}</button>
          </div>
        </form>
      </Modal>

      {/* 編集 Drawer（行クリックで開く・useRecordDrawer フック） */}
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={t("teams.editTeam")}
        onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/teams/${editId}/edit`); } : undefined}
      >
        <form onSubmit={handleEditSubmit}>
          <TeamFormFields
            form={editForm}
            onChange={(field, value) => setEditForm((prev) => ({ ...prev, [field]: value }))}
          />
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={closeDrawer}>
              {t("common.cancel")}
            </button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      </Drawer>

      {/* メンバー管理 Modal（既存 UX 保持） */}
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
              <button className="btn-sm" onClick={(e) => { e.stopPropagation(); openMembers(team); }}>{t("teams.membersBtn")}</button>
              {hasPermission("teams.update") && (
                <button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(team); }}>{t("common.edit")}</button>
              )}
              {hasPermission("teams.delete") && (
                <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(team); }}>{t("common.delete")}</button>
              )}
            </span>
          )},
        ];
        return (
          <DataTable<Team>
            columns={teamColumns}
            data={teams}
            rowKey={(team) => String(team.id)}
            onRowClick={hasPermission("teams.update") ? handleRowClick : undefined}
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
