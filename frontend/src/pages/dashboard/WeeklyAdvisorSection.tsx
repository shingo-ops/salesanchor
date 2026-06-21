import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { DashboardIcons } from "../../constants/icons";
import { getWeeklyAdvisorDefensive, type WeeklyAdvisorAction } from "../../api/funnel";
import "./WeeklyAdvisorSection.css";

const WeeklyIcon = DashboardIcons.reminder;

function formatMoney(value: number): string {
  return `¥${value.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}`;
}

function formatScore(value: number): string {
  return value.toLocaleString("ja-JP", { maximumFractionDigits: 1 });
}

function formatDate(value: string | null): string {
  return value ? value.slice(0, 10) : "-";
}

function typeLabelKey(type: WeeklyAdvisorAction["type"]): string {
  switch (type) {
    case "reorder":
      return "dashboard.weeklyTypeReorder";
    case "churn_risk":
      return "dashboard.weeklyTypeChurnRisk";
    case "comm_low":
      return "dashboard.weeklyTypeCommLow";
  }
}

function renderReason(action: WeeklyAdvisorAction, t: (key: string, opts?: Record<string, unknown>) => string) {
  const { reason } = action;
  if (action.type === "reorder") {
    return (
      <>
        <span>{t("dashboard.weeklyLastOrder")}: {formatDate(reason.last_order_at)}</span>
        <span>{t("dashboard.weeklyAvgInterval")}: {reason.avg_interval_days ?? "-"}{t("common.unitDay")}</span>
        <span>{t("dashboard.weeklyElapsed")}: {reason.days_since_last_order ?? "-"}{t("common.unitDay")}</span>
      </>
    );
  }

  if (action.type === "churn_risk") {
    return (
      <>
        <span>{t("dashboard.weeklyPaceScore")}: {reason.pace_score ?? 0}</span>
        <span>{t("dashboard.weeklyContactScore")}: {reason.contact_score ?? 0}</span>
        <span>{t("dashboard.weeklyDeclineScore")}: {reason.decline_score ?? 0}</span>
        <span>{t("dashboard.weeklyTotalScore")}: {reason.total_score ?? 0}</span>
      </>
    );
  }

  return (
    <>
      <span>{t("dashboard.weeklyLastContact")}: {formatDate(reason.last_contact_at)}</span>
      <span>{t("dashboard.weeklyElapsed")}: {reason.days_since_contact ?? "-"}{t("common.unitDay")}</span>
    </>
  );
}

export function WeeklyAdvisorSection() {
  const { t } = useTranslation();
  const [actions, setActions] = useState<WeeklyAdvisorAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    getWeeklyAdvisorDefensive("mine", "3m")
      .then((res) => {
        if (!active) return;
        setActions(res.actions);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : t("common.errorLoad"));
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [t]);

  return (
    <div className="db-section-card db-weekly-card" data-testid="weekly-advisor-section">
      <div className="db-section-header">
        <WeeklyIcon aria-hidden="true" className="db-section-icon" />
        <h3>
          {t("dashboard.weeklyTitle")}
          <span className="db-weekly-ai-pill">{t("dashboard.weeklyAiTag")}</span>
        </h3>
      </div>
      <p className="db-weekly-subtitle">{t("dashboard.weeklySubtitle")}</p>

      {loading ? (
        <div className="db-loading">{t("dashboard.weeklyLoading")}</div>
      ) : error ? (
        <div className="db-weekly-error">{error}</div>
      ) : actions.length === 0 ? (
        <p className="db-weekly-empty">{t("dashboard.weeklyEmpty")}</p>
      ) : (
        <ul className="db-weekly-list" aria-label={t("dashboard.weeklyTitle")}>
          {actions.map((action) => (
            <li key={`${action.type}-${action.company_id}-${action.rank}`} className={`db-weekly-item db-weekly-item--${action.type}`} data-testid="weekly-advisor-item">
              <div className="db-weekly-item-head">
                <span className="db-weekly-rank">#{action.rank}</span>
                <span className="db-weekly-type">{t(typeLabelKey(action.type))}</span>
                <span className="db-weekly-score-label">{t("dashboard.weeklyScore")}: <strong>{formatScore(action.score)}</strong></span>
              </div>

              <div className="db-weekly-company">{action.company_name}</div>

              <div className="db-weekly-meta">
                <span>{t("dashboard.weeklyExpectedValue")}: {formatMoney(action.expected_value)}</span>
                <span>{action.suggested_action}</span>
              </div>

              <div className="db-weekly-reason">
                <span className="db-weekly-reason-title">{t("dashboard.weeklyReason")}</span>
                <div className="db-weekly-reason-rows">
                  {renderReason(action, t)}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
