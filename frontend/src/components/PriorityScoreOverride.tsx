/**
 * ADR-107 (ADR-SA-14): 顧客優先度スコア人手上書きUI。
 *
 * ADR-107 §C: 人が上書き可能・上書き保存（埋もれさせない）。v1 = 保存のみ。
 * 閲覧は analytics.customer_priority.view、上書きは analytics.customer_priority.override 権限必要。
 */

import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import { usePermissions } from "../hooks/usePermissions";
import type { CustomerScoreData } from "./PriorityScoreBadge";

interface Props {
  leadId: number;
  currentScore: CustomerScoreData;
  onUpdated: (newScore: CustomerScoreData) => void;
}

function tierFromScore(score: number): CustomerScoreData["tier"] {
  if (score >= 0.65) return "最有望";
  if (score >= 0.35) return "有望";
  return "要観察";
}

export default function PriorityScoreOverride({ leadId, currentScore, onUpdated }: Props) {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [open, setOpen] = useState(false);
  const [sliderValue, setSliderValue] = useState(
    Math.round((currentScore.override_score ?? currentScore.score) * 100)
  );
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!hasPermission("analytics.customer_priority.override")) {
    return null;
  }

  const previewTier = tierFromScore(sliderValue / 100);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updated = await api.post<CustomerScoreData>(
        `/leads/${leadId}/priority-score/override`,
        { override_score: sliderValue / 100, override_note: note || null }
      );
      onUpdated(updated);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <button className="btn-sm" onClick={() => setOpen(true)}>
        {t("priority.overrideTitle")}
      </button>

      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{t("priority.overrideTitle")}</h3>
            <p className="text-muted">{t("priority.overrideWarning")}</p>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>
                  {t("priority.overrideScore")}: {sliderValue}%
                  {" "}→ {t(`priority.tier.${previewTier}`)}
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={sliderValue}
                  onChange={(e) => setSliderValue(Number(e.target.value))}
                />
              </div>

              <div className="form-group">
                <label>{t("priority.overrideNote")}</label>
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  maxLength={500}
                  placeholder={t("priority.overrideNotePlaceholder")}
                />
              </div>

              {error && <div className="error-message">{error}</div>}

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setOpen(false)}
                >
                  {t("common.cancel")}
                </button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? t("common.saving") : t("common.save")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
