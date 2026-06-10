/**
 * TeamEditPage — チームフルページ編集（/teams/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * TeamFormFields を共有し、同一フォームで編集・保存できる。
 * 保存後は /teams 一覧へ戻る。
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";
import { TeamFormFields, type TeamFormState } from "./TeamFormFields";

const emptyForm: TeamFormState = { name: "", leader_id: "", description: "" };

export default function TeamEditPage() {
  const { t }      = useTranslation();
  const { id }     = useParams<{ id: string }>();
  const navigate   = useNavigate();
  const [form, setForm] = useState<TeamFormState>(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api
      .get<{ id: number; name: string; leader_id: number | null; description: string | null }>(
        `/teams/${id}`,
      )
      .then((team) =>
        setForm({
          name: team.name,
          leader_id: team.leader_id != null ? String(team.leader_id) : "",
          description: team.description ?? "",
        }),
      )
      .catch((e) => setError(e instanceof Error ? e.message : t("common.fetchError")))
      .finally(() => setLoading(false));
  }, [id, t]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.patch(`/teams/${id}`, {
        name: form.name,
        leader_id: form.leader_id ? Number(form.leader_id) : null,
        description: form.description || null,
      });
      navigate("/teams");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <PageLayout navKey="nav.teams" subtitleKey="teams.subtitle">
      {error && <div className="error-message">{error}</div>}
      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <TeamFormFields form={form} onChange={(f, v) => setForm((p) => ({ ...p, [f]: v }))} />
          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate("/teams")}
            >
              {t("common.cancel")}
            </button>
            <button type="submit" className="btn-primary">
              {t("common.update")}
            </button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
