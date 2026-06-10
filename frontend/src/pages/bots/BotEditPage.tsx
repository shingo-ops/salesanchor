/**
 * BotEditPage — Bot フルページ編集（/bots/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * BotFormFields を共有し、同一フォームで編集・保存できる。
 * 保存後は /bots 一覧へ戻る。
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";
import { BotFormFields, type BotFormState, type BotStaff } from "./BotFormFields";

interface Bot {
  id: number;
  display_name: string;
  purpose: string;
  status: string;
  discord_user_id: string | null;
  sender_email: string | null;
  owner_staff_id: number;
}

const emptyForm: BotFormState = {
  display_name: "", purpose: "invoice", status: "active",
  owner_staff_id: "", discord_user_id: "", sender_email: "",
};

export default function BotEditPage() {
  const { t }    = useTranslation();
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form, setForm] = useState<BotFormState>(emptyForm);
  const [staff, setStaff] = useState<BotStaff[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.get<Bot>(`/bots/${id}`),
      api.get<BotStaff[]>("/staff"),
    ])
      .then(([bot, staffList]) => {
        setForm({
          display_name: bot.display_name,
          purpose: bot.purpose,
          status: bot.status,
          owner_staff_id: String(bot.owner_staff_id),
          discord_user_id: bot.discord_user_id ?? "",
          sender_email: bot.sender_email ?? "",
        });
        setStaff(staffList);
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("common.fetchError")))
      .finally(() => setLoading(false));
  }, [id, t]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.patch(`/bots/${id}`, {
        display_name: form.display_name,
        purpose: form.purpose,
        status: form.status,
        owner_staff_id: parseInt(form.owner_staff_id, 10),
        discord_user_id: form.discord_user_id || null,
        sender_email: form.sender_email || null,
      });
      navigate("/bots");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <PageLayout navKey="nav.bots" subtitleKey="bots.subtitle">
      {error && <div className="error-message">{error}</div>}
      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <BotFormFields form={form} onChange={(f, v) => setForm((p) => ({ ...p, [f]: v }))} staff={staff} />
          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate("/bots")}
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
