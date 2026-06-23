import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Button } from "../../components/Button";
import { DashboardIcons } from "../../constants/icons";
import {
  getPriorityProspects,
  type PriorityProspectAxisBreakdown,
  type PriorityProspectItem,
} from "../../api/funnel";
import type { LeadDetail } from "../inbox/inbox.types";
import "./WeeklyAdvisorSection.css";
import "./PriorityProspectsSection.css";

const PriorityIcon = DashboardIcons.trendUp;

interface ComposerState {
  phase: "idle" | "editing" | "saved";
  draftAction: string;
  draftDate: string;
  loadingLead: boolean;
  saving: boolean;
  error: string | null;
}

function formatMoney(value: number): string {
  return `¥${value.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}`;
}

function formatScore(value: number): string {
  return value.toLocaleString("ja-JP", { maximumFractionDigits: 1 });
}

function formatPct(value: number): string {
  return `${value.toLocaleString("ja-JP", { maximumFractionDigits: 1 })}%`;
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

const AXIS_LABEL_KEYS: Record<string, string> = {
  channel_type: "dashboard.priorityAxisChannelType",
  country: "dashboard.priorityAxisCountry",
  sales_form: "dashboard.priorityAxisSalesForm",
  temperature: "dashboard.priorityAxisTemperature",
  response_speed: "dashboard.priorityAxisResponseSpeed",
};

function renderAxis(
  axis: PriorityProspectAxisBreakdown,
  t: (key: string, opts?: Record<string, unknown>) => string,
) {
  const axisLabel = AXIS_LABEL_KEYS[axis.axis] ?? axis.axis;
  return (
    <span key={`${axis.axis}:${axis.value}`} className="db-priority-axis-chip">
      <span className="db-priority-axis-label">{t(axisLabel)}:</span>
      <span className="db-priority-axis-value">{axis.value}</span>
    </span>
  );
}

function renderFlags(
  flags: string[],
  t: (key: string, opts?: Record<string, unknown>) => string,
) {
  const hasAxisLowSample = flags.some((flag) => flag.endsWith(":low_sample"));
  const hasUnsetForecast = flags.includes("monthly_forecast_unset");
  return (
    <>
      {hasAxisLowSample && <span className="db-priority-flag">{t("dashboard.prioritySampleLow")}</span>}
      {hasUnsetForecast && <span className="db-priority-flag">{t("dashboard.priorityAmountUnset")}</span>}
    </>
  );
}

function leadLabel(
  detail: LeadDetail | undefined,
  fallbackId: number,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  return detail?.customer_name || detail?.company_name || t("dashboard.priorityFallbackLead", { id: fallbackId });
}

export function PriorityProspectsSection() {
  const { t } = useTranslation();
  const [items, setItems] = useState<PriorityProspectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [composerByLeadId, setComposerByLeadId] = useState<Record<number, ComposerState>>({});
  const [leadDetails, setLeadDetails] = useState<Record<number, LeadDetail>>({});

  const getComposer = useCallback((leadId: number): ComposerState => {
    return composerByLeadId[leadId] ?? initialComposerState();
  }, [composerByLeadId]);

  const updateComposer = useCallback((leadId: number, patch: Partial<ComposerState>) => {
    setComposerByLeadId((prev) => {
      const current = prev[leadId] ?? initialComposerState();
      return {
        ...prev,
        [leadId]: {
          ...current,
          ...patch,
        },
      };
    });
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    getPriorityProspects("mine")
      .then(async (res) => {
        if (!active) return;
        setItems(res.items);

        const detailEntries = await Promise.allSettled(
          res.items.map(async (item) => {
            const detail = await api.get<LeadDetail>(`/leads/${item.lead_id}`);
            return [item.lead_id, detail] as const;
          }),
        );

        if (!active) return;
        const nextDetails: Record<number, LeadDetail> = {};
        for (const entry of detailEntries) {
          if (entry.status === "fulfilled") {
            const [leadId, detail] = entry.value;
            nextDetails[leadId] = detail;
          }
        }
        setLeadDetails(nextDetails);
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

  const beginFollowUp = useCallback((item: PriorityProspectItem) => {
    const currentLead = leadDetails[item.lead_id];
    setComposerByLeadId((prev) => {
      const current = prev[item.lead_id] ?? initialComposerState();
      const nextAction = current.phase === "editing" || current.phase === "saved"
        ? current.draftAction
        : item.suggested_action;
      const nextDate = current.phase === "editing" || current.phase === "saved"
        ? current.draftDate
        : defaultDueDate();

      return {
        ...prev,
        [item.lead_id]: {
          ...current,
          phase: "editing",
          draftAction: nextAction,
          draftDate: nextDate,
          loadingLead: !currentLead,
          error: null,
          saving: false,
        },
      };
    });

    if (!currentLead) {
      void api.get<LeadDetail>(`/leads/${item.lead_id}`)
        .then((detail) => {
          setLeadDetails((prev) => ({ ...prev, [item.lead_id]: detail }));
        })
        .finally(() => {
          updateComposer(item.lead_id, { loadingLead: false });
        })
        .catch(() => {
          // 既存のフォロー導線は維持する。詳細取得失敗でも composer は開く。
        });
    }
  }, [leadDetails, updateComposer]);

  const closeComposer = useCallback((item: PriorityProspectItem) => {
    setComposerByLeadId((prev) => {
      const current = prev[item.lead_id];
      if (!current) return prev;
      return {
        ...prev,
        [item.lead_id]: {
          ...current,
          phase: current.phase === "saved" ? "saved" : "idle",
          loadingLead: false,
          saving: false,
          error: null,
        },
      };
    });
  }, []);

  const saveFollowUp = useCallback(async (item: PriorityProspectItem) => {
    const current = composerByLeadId[item.lead_id];
    if (!current) return;

    const snapshot = leadDetails[item.lead_id];
    if (snapshot?.next_action) {
      const confirmed = window.confirm(t("dashboard.weeklyOverwriteWarning"));
      if (!confirmed) return;
    }

    updateComposer(item.lead_id, { saving: true, error: null });

    try {
      await api.patch<LeadDetail>(`/leads/${item.lead_id}`, {
        next_action: current.draftAction,
        next_action_date: current.draftDate || null,
      });

      setLeadDetails((prev) => ({
        ...prev,
        [item.lead_id]: {
          ...(prev[item.lead_id] ?? {
            id: item.lead_id,
            lead_code: null,
            customer_name: "",
            company_name: null,
            email: null,
            phone: null,
            status: "lead",
            temperature: null,
            estimated_scale: null,
            customer_type: null,
            response_speed: null,
            monthly_forecast: null,
            prospect_rank: null,
            notes: null,
            next_action: null,
            next_action_date: null,
            challenge: null,
            meeting_memo: null,
            meeting_impression: null,
            cs_memo: null,
            sales_form: null,
            competitor_check: null,
            per_order_amount: null,
            monthly_frequency: null,
            nickname: null,
            country: null,
            target_titles: null,
            messenger_link: null,
            discord_id: null,
            instagram_link: null,
            whatsapp_link: null,
            discord_user_id: null,
            discord_dm_channel_id: null,
            discord_guild_channel_id: null,
            discord_role_sync_status: null,
            discord_role_sync_at: null,
            sales_form_selections: [],
            sales_form_options: [],
          }),
          next_action: current.draftAction,
          next_action_date: current.draftDate || null,
        },
      }));
      updateComposer(item.lead_id, {
        phase: "saved",
        saving: false,
        loadingLead: false,
        error: null,
      });
    } catch (err: unknown) {
      updateComposer(item.lead_id, {
        saving: false,
        error: err instanceof Error ? err.message : t("common.saveError"),
      });
    }
  }, [composerByLeadId, leadDetails, t, updateComposer]);

  return (
    <div className="db-section-card db-priority-card" data-testid="priority-prospects-section">
      <div className="db-section-header">
        <PriorityIcon aria-hidden="true" className="db-section-icon" />
        <h3>
          {t("dashboard.priorityTitle")}
          <span className="db-priority-ai-pill">{t("dashboard.priorityAiTag")}</span>
        </h3>
      </div>
      <p className="db-priority-subtitle">{t("dashboard.prioritySubtitle")}</p>

      {loading ? (
        <div className="db-priority-loading">{t("dashboard.weeklyLoading")}</div>
      ) : error ? (
        <div className="db-priority-error">{error}</div>
      ) : items.length === 0 ? (
        <p className="db-priority-empty">{t("dashboard.priorityEmpty")}</p>
      ) : (
        <ul className="db-priority-list" aria-label={t("dashboard.priorityTitle")}>
          {items.map((item) => {
            const composer = getComposer(item.lead_id);
            const detail = leadDetails[item.lead_id];
            const isAdded = composer.phase === "saved";
            const showComposer = composer.phase === "editing";
            const hasAxisLowSample = item.low_sample_flags.some((flag) => flag.endsWith(":low_sample"));

            return (
              <li
                key={item.lead_id}
                className={`db-priority-item${hasAxisLowSample ? " db-priority-item--no-sample" : ""}`}
                data-testid="priority-prospect-item"
              >
                <div className="db-priority-item-head">
                  <span className="db-priority-badge">{t("dashboard.priorityOpportunity")}</span>
                  <span className="db-priority-type">{t("dashboard.priorityTypeLabel")}</span>
                  <span className="db-priority-score-label">
                    {t("dashboard.priorityRankScore")}: <strong>{formatScore(item.rank_score)}</strong>
                  </span>
                </div>

                <div className="db-priority-company">
                  {leadLabel(detail, item.lead_id, t)}
                </div>

                <div className="db-priority-meta">
                  <span>{t("dashboard.priorityEaseLabel")}: {formatPct(item.ease_pct)}</span>
                  <span>{t("dashboard.priorityMonthlyForecast")}: {formatMoney(item.monthly_forecast)}</span>
                </div>

                <div className="db-priority-flag-row">
                  {renderFlags(item.low_sample_flags, t)}
                </div>

                <div className="db-priority-axis" aria-label={t("dashboard.priorityAxisBreakdown")}>
                  {item.axis_breakdown.map((axis) => renderAxis(axis, t))}
                </div>

                <div className="db-weekly-followup-row">
                  {isAdded ? (
                    <span className="db-priority-added-badge" data-testid="priority-followup-added">
                      {t("dashboard.weeklyAdded")}
                    </span>
                  ) : (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="db-priority-followup-btn"
                      onClick={() => beginFollowUp(item)}
                      data-testid="priority-followup-open"
                    >
                      {t("dashboard.weeklyAddFollowUp")}
                    </Button>
                  )}
                </div>

                {showComposer && (
                  <div className="db-weekly-composer" data-testid="priority-followup-composer">
                    {composer.loadingLead ? (
                      <div className="db-weekly-composer-loading">{t("common.loading")}</div>
                    ) : null}

                    {detail?.next_action ? (
                      <div className="db-weekly-composer-warning">
                        {t("dashboard.weeklyOverwriteWarning")}
                        <span className="db-weekly-composer-warning-value">
                          {detail.next_action}
                          {detail.next_action_date ? ` / ${detail.next_action_date}` : ""}
                        </span>
                      </div>
                    ) : null}

                    <div className="db-weekly-composer-field">
                      <label className="db-weekly-composer-label" htmlFor={`priority-action-${item.lead_id}`}>
                        {t("leads.nextAction")}
                      </label>
                      <textarea
                        id={`priority-action-${item.lead_id}`}
                        className="db-weekly-composer-input"
                        rows={3}
                        value={composer.draftAction}
                        onChange={(e) => updateComposer(item.lead_id, { draftAction: e.target.value })}
                      />
                    </div>

                    <div className="db-weekly-composer-field">
                      <label className="db-weekly-composer-label" htmlFor={`priority-date-${item.lead_id}`}>
                        {t("leads.nextActionDate")}
                      </label>
                      <input
                        id={`priority-date-${item.lead_id}`}
                        className="db-weekly-composer-input"
                        type="date"
                        value={composer.draftDate}
                        onChange={(e) => updateComposer(item.lead_id, { draftDate: e.target.value })}
                      />
                    </div>

                    {composer.error ? (
                      <div className="db-weekly-composer-error">{composer.error}</div>
                    ) : null}

                    <div className="db-weekly-composer-actions">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => saveFollowUp(item)}
                        loading={composer.saving}
                        disabled={composer.loadingLead}
                        data-testid="priority-followup-save"
                      >
                        {t("common.add")}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => closeComposer(item)}
                        disabled={composer.saving}
                      >
                        {t("common.cancel")}
                      </Button>
                    </div>
                  </div>
                )}

                {isAdded && !showComposer && (
                  <div className="db-priority-added-note" data-testid="priority-followup-saved">
                    {t("dashboard.weeklyAdded")}
                    {detail?.next_action_date ? ` / ${detail.next_action_date}` : ""}
                    {detail?.next_action ? ` — ${detail.next_action}` : ""}
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="db-priority-edit-btn"
                      onClick={() => beginFollowUp(item)}
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
