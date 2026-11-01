import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Button } from "../../components/Button";
import { TextareaControl } from "../../components/Textarea";
import { TextFieldControl } from "../../components/TextField";
import { DashboardIcons } from "../../constants/icons";
import {
  FUNNEL_MOCK,
  PRIORITY_PROSPECTS_PATH,
  type PriorityProspectAxisBreakdown,
  type PriorityProspectItem,
  type PriorityProspectsResponse,
} from "../../api/funnel";
import type { LeadDetail } from "../inbox/inbox.types";
import "./WeeklyAdvisorSection.css";
import "./PriorityProspectsSection.css";
import { LoadingBlock } from "../../components/loading";
import { useApiQueries, useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { MOCK_PRIORITY_PROSPECTS } from "../../mocks/funnelFixtures";

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
  const invalidate = useInvalidateApi();
  // 見本の時（開発・E2E）は今までどおり一覧を通信せずに出す
  const listQuery = useApiQuery<PriorityProspectsResponse>(PRIORITY_PROSPECTS_PATH, { enabled: !FUNNEL_MOCK });
  // 「?? []」が描画ごとに新しい並びを作らないよう包む（第 1 版で react-hooks/exhaustive-deps の警告が 0→1 になった）
  const listItems = listQuery.data?.items;
  const items: PriorityProspectItem[] = useMemo(
    () => (FUNNEL_MOCK ? MOCK_PRIORITY_PROSPECTS.items : listItems ?? []),
    [listItems],
  );
  const detailQueries = useApiQueries<LeadDetail>(items.map((item) => `/leads/${item.lead_id}`));
  // 一覧と、一覧に出た人の中身がそろうまで読み込み中にする（今と同じ）。取れなかった人は名前の代わりの言葉を出す（今と同じ）
  const loading = (!FUNNEL_MOCK && listQuery.isPending) || detailQueries.some((q) => q.isPending);
  const error = FUNNEL_MOCK ? null : listQuery.error ? listQuery.error.message || t("common.errorLoad") : null;
  const leadDetails = useMemo(() => {
    const byLeadId: Record<number, LeadDetail> = {};
    items.forEach((item, index) => {
      const detail = detailQueries[index]?.data;
      if (detail) byLeadId[item.lead_id] = detail;
    });
    return byLeadId;
  }, [items, detailQueries]);
  const [composerByLeadId, setComposerByLeadId] = useState<Record<number, ComposerState>>({});

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
      void invalidate(["leads", String(item.lead_id)]).finally(() => {
        updateComposer(item.lead_id, { loadingLead: false });
      });
    }
  }, [invalidate, leadDetails, updateComposer]);

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

      void invalidate(["leads", String(item.lead_id)]);
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
  }, [composerByLeadId, invalidate, leadDetails, t, updateComposer]);

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
        <LoadingBlock label={t("dashboard.weeklyLoading")} />
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
                      <LoadingBlock />
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
                      <TextareaControl
                        id={`priority-action-${item.lead_id}`}
                        variant="composer"
                        rows={3}
                        value={composer.draftAction}
                        onChange={(e) => updateComposer(item.lead_id, { draftAction: e.target.value })}
                      />
                    </div>

                    <div className="db-weekly-composer-field">
                      <label className="db-weekly-composer-label" htmlFor={`priority-date-${item.lead_id}`}>
                        {t("leads.nextActionDate")}
                      </label>
                      <TextFieldControl
                        id={`priority-date-${item.lead_id}`}
                        variant="composer"
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
                      layoutClassName="db-priority-edit-btn"
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
