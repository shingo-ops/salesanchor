import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { Button } from "../../components/Button";
import { DashboardIcons } from "../../constants/icons";
import { getWeeklyAdvisorDefensive, type WeeklyAdvisorAction } from "../../api/funnel";
import type { LeadDetail } from "../inbox/inbox.types";
import "./WeeklyAdvisorSection.css";

const WeeklyIcon = DashboardIcons.reminder;

interface ComposerState {
  phase: "idle" | "editing" | "saved";
  draftAction: string;
  draftDate: string;
  loadingLead: boolean;
  saving: boolean;
  error: string | null;
}

interface LeadSnapshot {
  next_action: string | null;
  next_action_date: string | null;
}

function formatMoney(value: number): string {
  return `¥${value.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}`;
}

function formatScore(value: number): string {
  return value.toLocaleString("ja-JP", { maximumFractionDigits: 1 });
}

function formatDate(value: string | null): string {
  return value ? value.slice(0, 10) : "-";
}

function toDateInputValue(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addBusinessDays(base: Date, businessDays: number): Date {
  const result = new Date(base);
  let remaining = businessDays;
  while (remaining > 0) {
    result.setDate(result.getDate() + 1);
    const day = result.getDay();
    if (day !== 0 && day !== 6) remaining -= 1;
  }
  return result;
}

function defaultDueDate(): string {
  return toDateInputValue(addBusinessDays(new Date(), 3));
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

function initialComposerState(): ComposerState {
  return {
    phase: "idle",
    draftAction: "",
    draftDate: defaultDueDate(),
    loadingLead: false,
    saving: false,
    error: null,
  };
}

export function WeeklyAdvisorSection() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [actions, setActions] = useState<WeeklyAdvisorAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [composerByCompanyId, setComposerByCompanyId] = useState<Record<number, ComposerState>>({});
  const [leadSnapshots, setLeadSnapshots] = useState<Record<number, LeadSnapshot>>({});

  const getComposer = useCallback((companyId: number): ComposerState => {
    return composerByCompanyId[companyId] ?? initialComposerState();
  }, [composerByCompanyId]);

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

  const closeComposer = useCallback((action: WeeklyAdvisorAction) => {
    setComposerByCompanyId((prev) => {
      const current = prev[action.company_id];
      if (!current) return prev;
      return {
        ...prev,
        [action.company_id]: {
          ...current,
          phase: current.phase === "saved" ? "saved" : "idle",
          loadingLead: false,
          saving: false,
          error: null,
        },
      };
    });
  }, []);

  const updateComposer = useCallback((companyId: number, patch: Partial<ComposerState>) => {
    setComposerByCompanyId((prev) => {
      const current = prev[companyId] ?? initialComposerState();
      return {
        ...prev,
        [companyId]: {
          ...current,
          ...patch,
        },
      };
    });
  }, []);

  const loadLeadSnapshot = useCallback(async (companyId: number, leadId: number) => {
    if (leadSnapshots[leadId]) {
      updateComposer(companyId, { loadingLead: false });
      return;
    }
    try {
      const detail = await api.get<LeadDetail>(`/leads/${leadId}`);
      setLeadSnapshots((prev) => ({
        ...prev,
        [leadId]: {
          next_action: detail.next_action,
          next_action_date: detail.next_action_date,
        },
      }));
    } catch {
      // lead が取得できなくても、フォロー追加の導線自体は継続する
    } finally {
      updateComposer(companyId, { loadingLead: false });
    }
  }, [leadSnapshots, updateComposer]);

  const beginFollowUp = useCallback((action: WeeklyAdvisorAction) => {
    const leadId = action.lead_id;
    if (leadId == null) {
      navigate(`/companies/${action.company_id}`);
      return;
    }

    setComposerByCompanyId((prev) => {
      const current = prev[action.company_id] ?? initialComposerState();
      const nextAction = current.phase === "editing" || current.phase === "saved"
        ? current.draftAction
        : action.suggested_action;
      const nextDate = current.phase === "editing" || current.phase === "saved"
        ? current.draftDate
        : defaultDueDate();

      return {
        ...prev,
        [action.company_id]: {
          ...current,
          phase: "editing",
          draftAction: nextAction,
          draftDate: nextDate,
          loadingLead: !leadSnapshots[leadId],
          error: null,
          saving: false,
        },
      };
    });

    void loadLeadSnapshot(action.company_id, leadId);
  }, [leadSnapshots, loadLeadSnapshot, navigate]);

  const saveFollowUp = useCallback(async (action: WeeklyAdvisorAction) => {
    if (!action.lead_id) return;
    const current = composerByCompanyId[action.company_id];
    if (!current) return;

    const snapshot = leadSnapshots[action.lead_id];
    if (snapshot?.next_action) {
      const confirmed = window.confirm(t("dashboard.weeklyOverwriteWarning"));
      if (!confirmed) return;
    }

    updateComposer(action.company_id, { saving: true, error: null });

    try {
      await api.patch<LeadDetail>(`/leads/${action.lead_id}`, {
        next_action: current.draftAction,
        next_action_date: current.draftDate || null,
      });

      setLeadSnapshots((prev) => ({
        ...prev,
        [action.lead_id as number]: {
          next_action: current.draftAction,
          next_action_date: current.draftDate || null,
        },
      }));
      updateComposer(action.company_id, {
        phase: "saved",
        saving: false,
        loadingLead: false,
        error: null,
      });
    } catch (err: unknown) {
      updateComposer(action.company_id, {
        saving: false,
        error: err instanceof Error ? err.message : t("common.saveError"),
      });
    }
  }, [composerByCompanyId, leadSnapshots, t, updateComposer]);

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
        <div className="db-weekly-loading">{t("dashboard.weeklyLoading")}</div>
      ) : error ? (
        <div className="db-weekly-error">{error}</div>
      ) : actions.length === 0 ? (
        <p className="db-weekly-empty">{t("dashboard.weeklyEmpty")}</p>
      ) : (
        <ul className="db-weekly-list" aria-label={t("dashboard.weeklyTitle")}>
          {actions.map((action) => {
            const composer = getComposer(action.company_id);
            const snapshot = action.lead_id ? leadSnapshots[action.lead_id] : null;
            const isAdded = composer.phase === "saved";
            const canAdd = !!action.lead_id;
            const showComposer = composer.phase === "editing";

            return (
              <li
                key={`${action.type}-${action.company_id}-${action.rank}`}
                className={`db-weekly-item db-weekly-item--${action.type}`}
                data-testid="weekly-advisor-item"
              >
                <div className="db-weekly-item-head">
                  <span className="db-weekly-rank">#{action.rank}</span>
                  <span className="db-weekly-type">{t(typeLabelKey(action.type))}</span>
                  <span className="db-weekly-score-label">
                    {t("dashboard.weeklyScore")}: <strong>{formatScore(action.score)}</strong>
                  </span>
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

                <div className="db-weekly-followup-row">
                  {canAdd ? (
                    <>
                      {isAdded ? (
                        <span className="db-weekly-added-badge" data-testid="weekly-followup-added">
                          {t("dashboard.weeklyAdded")}
                        </span>
                      ) : (
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          className="db-weekly-followup-btn"
                          onClick={() => beginFollowUp(action)}
                          data-testid="weekly-followup-open"
                        >
                          {t("dashboard.weeklyAddFollowUp")}
                        </Button>
                      )}
                    </>
                  ) : (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="db-weekly-followup-btn"
                      onClick={() => navigate(`/companies/${action.company_id}`)}
                      data-testid="weekly-company-open"
                    >
                      {t("dashboard.weeklyOpenCompany")}
                    </Button>
                  )}
                </div>

                {showComposer && canAdd && (
                  <div className="db-weekly-composer" data-testid="weekly-followup-composer">
                    {composer.loadingLead ? (
                      <div className="db-weekly-composer-loading">{t("common.loading")}</div>
                    ) : null}

                    {snapshot?.next_action ? (
                      <div className="db-weekly-composer-warning">
                        {t("dashboard.weeklyOverwriteWarning")}
                        <span className="db-weekly-composer-warning-value">
                          {snapshot.next_action}
                          {snapshot.next_action_date ? ` / ${snapshot.next_action_date}` : ""}
                        </span>
                      </div>
                    ) : null}

                    <div className="db-weekly-composer-field">
                      <label className="db-weekly-composer-label" htmlFor={`weekly-action-${action.company_id}`}>
                        {t("leads.nextAction")}
                      </label>
                      <textarea
                        id={`weekly-action-${action.company_id}`}
                        className="db-weekly-composer-input"
                        rows={3}
                        value={composer.draftAction}
                        onChange={(e) => updateComposer(action.company_id, { draftAction: e.target.value })}
                      />
                    </div>

                    <div className="db-weekly-composer-field">
                      <label className="db-weekly-composer-label" htmlFor={`weekly-date-${action.company_id}`}>
                        {t("leads.nextActionDate")}
                      </label>
                      <input
                        id={`weekly-date-${action.company_id}`}
                        className="db-weekly-composer-input"
                        type="date"
                        value={composer.draftDate}
                        onChange={(e) => updateComposer(action.company_id, { draftDate: e.target.value })}
                      />
                    </div>

                    {composer.error ? (
                      <div className="db-weekly-composer-error">{composer.error}</div>
                    ) : null}

                    <div className="db-weekly-composer-actions">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => saveFollowUp(action)}
                        loading={composer.saving}
                        disabled={composer.loadingLead}
                        data-testid="weekly-followup-save"
                      >
                        {t("common.add")}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => closeComposer(action)}
                        disabled={composer.saving}
                      >
                        {t("common.cancel")}
                      </Button>
                    </div>
                  </div>
                )}

                {isAdded && !showComposer && (
                  <div className="db-weekly-added-note" data-testid="weekly-followup-saved">
                    {t("dashboard.weeklyAdded")}
                    {snapshot?.next_action_date ? ` / ${snapshot.next_action_date}` : ""}
                    {snapshot?.next_action ? ` — ${snapshot.next_action}` : ""}
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="db-weekly-edit-btn"
                      onClick={() => beginFollowUp(action)}
                    >
                      {t("common.edit")}
                    </Button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
