import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { MultiSelect } from "../../components/MultiSelect";
import { Button } from "../../components/Button";
import "./NoticeFallbackSection.css";

interface FallbackCandidate { user_id: number; name: string | null; }
interface FallbackRecipients {
  selected: number[];
  defaulted_to_owner: boolean;
  candidates: FallbackCandidate[];
}

/**
 * 通知の設定ページの区画「担当者がいないときに受け取る人」。
 * 呼び出し側が hasPermission("notifications.manage") のときだけ描く（設計 §4-改訂2）。
 * 何も選ばない = オーナー全員が受け取る。
 */
export function NoticeFallbackSection() {
  const { t } = useTranslation();
  const invalidate = useInvalidateApi();
  const q = useApiQuery<FallbackRecipients>("/notice-fallback-recipients");
  const [selected, setSelected] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const serverSelected = q.data?.selected;
  useEffect(() => {
    if (serverSelected) setSelected(serverSelected.map(String));
  }, [serverSelected]);

  const options = (q.data?.candidates ?? []).map((c) => ({
    value: String(c.user_id),
    label: c.name ?? String(c.user_id),
  }));

  const save = async () => {
    setError("");
    setSaved(false);
    try {
      await api.put<FallbackRecipients>("/notice-fallback-recipients", { user_ids: selected.map(Number) });
      await invalidate(["notice-fallback-recipients"]);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <section className="notice-fallback" data-testid="notice-fallback-section">
      <h3 className="notice-fallback__title">{t("notices.fallback.title")}</h3>
      <p className="notice-fallback__help">{t("notices.fallback.help")}</p>
      <MultiSelect
        label={t("notices.fallback.title")}
        options={options}
        selected={selected}
        onChange={(next) => { setSelected(next); setSaved(false); }}
        clearLabel={t("notices.fallback.clear")}
        allLabel={t("notices.fallback.defaultOwner")}
        countLabel={(n) => t("notices.fallback.count", { count: n })}
        testId="notice-fallback-select"
      />
      <div className="notice-fallback__actions">
        <Button variant="primary" size="md" onClick={() => void save()} data-testid="notice-fallback-save">
          {t("common.save")}
        </Button>
        {saved && <span className="notice-fallback__saved" role="status">{t("notices.fallback.saved")}</span>}
        {error && <span className="notice-fallback__error" role="alert">{error}</span>}
      </div>
    </section>
  );
}
