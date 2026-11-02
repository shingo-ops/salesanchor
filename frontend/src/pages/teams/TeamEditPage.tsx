/**
 * TeamEditPage — チームフルページ編集（/teams/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * TeamFormFields を共有し、同一フォームで編集・保存できる。
 * 保存後は /teams 一覧へ戻る。
 */

import { LoadingBlock } from "../../components/loading";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import { TeamFormFields, type TeamFormState } from "./TeamFormFields";

const emptyForm: TeamFormState = { name: "", leader_id: "", description: "" };

type TeamDetail = { id: number; name: string; leader_id: number | null; description: string | null };

const formFromTeam = (team: TeamDetail): TeamFormState => ({
  name: team.name,
  leader_id: team.leader_id != null ? String(team.leader_id) : "",
  description: team.description ?? "",
});

export default function TeamEditPage() {
  const { t }      = useTranslation();
  const { id }     = useParams<{ id: string }>();
  const navigate   = useNavigate();
  const teamQ = useApiQuery<TeamDetail>(`/teams/${id}`, { enabled: id !== undefined });
  const { form, setForm, ready } = useSeededForm(`team/${id}`, teamQ.data, formFromTeam, emptyForm);
  const [error, setError] = useState("");
  const loading = teamQ.error === null && !ready;
  const shownError = error || (teamQ.error ? (teamQ.error instanceof Error ? teamQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.patch(`/teams/${id}`, {
        name: form.name,
        leader_id: form.leader_id ? Number(form.leader_id) : null,
        description: form.description || null,
      });
      void invalidate(["teams", id ?? ""]);
      navigate("/teams");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <PageLayout navKey="nav.teams" subtitleKey="teams.subtitle">
      {shownError && <div className="error-message">{shownError}</div>}
      {loading ? (
        <LoadingBlock />
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <TeamFormFields form={form} onChange={(f, v) => setForm((p) => ({ ...p, [f]: v }))} />
          <div className="form-actions">
            <Button
              type="button"
              variant="secondary" size="md"
              onClick={() => navigate("/teams")}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" variant="primary" size="md">
              {t("common.update")}
            </Button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
