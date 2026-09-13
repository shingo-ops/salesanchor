/**
 * 目標設定ページ。
 *
 * ダッシュボードの「目標を設定する」ボタンから遷移する。
 * チームリーダー: チーム目標 + 個人目標を入力可能
 * 一般担当者: 自分の個人目標のみ入力可能
 *
 * ルート: /goals/settings
 *
 * 変更履歴:
 *   2026-05-25: 初版作成（ダッシュボード強化）
 */

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { STATUS_ICONS } from "../../constants/icons";
import "./GoalSettingPage.css";

const CheckIcon = STATUS_ICONS.check;

// ─── 型定義 ──────────────────────────────────────────────────

type KpiType =
  | "revenue"
  | "deal_count"
  | "close_rate"
  | "lead_count"
  | "conversion_rate";

type PeriodType = "monthly" | "weekly";

interface GoalResponse {
  id: number;
  user_id: number | null;
  team_id: number | null;
  period_type: PeriodType;
  period_year: number;
  period_num: number;
  kpi_type: KpiType;
  target_value: number;
}

interface Team {
  id: number;
  name: string;
  leader_id: number | null;
}

interface CurrentUser {
  id: number;
  role: string;
}

interface GoalAdviceInputs {
  monthly_kgi: number;
  kgi_type: "revenue" | "wins";
  period: string;
  scope: string;
}

interface GoalAdviceRatesUsed {
  unit_price: number | null;
  win_rate: number | null;
  deal_rate: number | null;
}

interface GoalAdviceRequired {
  wins: number | null;
  deals: number | null;
  leads: number | null;
}

interface GoalAdviceWorkingDays {
  remaining_month: number;
  remaining_week: number;
  shift_status: "submitted" | "not_submitted";
}

interface GoalAdviceResponse {
  inputs: GoalAdviceInputs;
  rates_used: GoalAdviceRatesUsed;
  monthly_required: GoalAdviceRequired;
  weekly_required: GoalAdviceRequired;
  working_days: GoalAdviceWorkingDays;
  data_sufficient: boolean;
}

// ─── 定数 ────────────────────────────────────────────────────

const INDIVIDUAL_KPIS: KpiType[] = ["revenue", "deal_count", "close_rate"];
const TEAM_KPIS: KpiType[] = [
  "revenue",
  "deal_count",
  "close_rate",
  "lead_count",
  "conversion_rate",
];

const KPI_LABEL_KEYS: Record<KpiType, string> = {
  revenue:         "dashboard.kpiRevenue",
  deal_count:      "dashboard.kpiDealCount",
  close_rate:      "dashboard.kpiCloseRate",
  lead_count:      "dashboard.kpiLeadCount",
  conversion_rate: "dashboard.kpiConversionRate",
};

const KPI_PLACEHOLDER: Record<KpiType, string> = {
  revenue:         "3000000",
  deal_count:      "10",
  close_rate:      "30",
  lead_count:      "20",
  conversion_rate: "50",
};

const ADVICE_PERIOD = "3m";

function formatAdviceNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  return new Intl.NumberFormat("ja-JP", {
    maximumFractionDigits: 2,
  }).format(value);
}

function currentYearMonth() {
  const d = new Date();
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

function currentYearWeek() {
  const d = new Date();
  const startOfYear = new Date(d.getFullYear(), 0, 1);
  const week = Math.ceil(
    ((d.getTime() - startOfYear.getTime()) / 86400000 + startOfYear.getDay() + 1) / 7
  );
  return { year: d.getFullYear(), week };
}

// ─── GoalInputRow ─────────────────────────────────────────────

interface GoalInputRowProps {
  kpiType: KpiType;
  value: string;
  onChange: (v: string) => void;
  saved: boolean;
  t: (k: string) => string;
}

function GoalInputRow({ kpiType, value, onChange, saved, t }: GoalInputRowProps) {
  return (
    <div className="gs-row">
      <label className="gs-label">{t(KPI_LABEL_KEYS[kpiType])}</label>
      <div className="gs-input-wrap">
        <input
          type="number"
          min="0"
          step="1"
          className={`gs-input${saved ? " gs-input-saved" : ""}`}
          placeholder={KPI_PLACEHOLDER[kpiType]}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        {saved && <span className="gs-saved-mark"><CheckIcon size={14} aria-hidden="true" /></span>}
      </div>
    </div>
  );
}

// ─── GoalBlock（月次/週次 × 個人/チーム） ───────────────────────

interface GoalBlockProps {
  title: string;
  kpis: KpiType[];
  values: Record<KpiType, string>;
  savedKeys: Set<KpiType>;
  onChange: (kpi: KpiType, v: string) => void;
  onSave: () => void;
  saving: boolean;
  t: (k: string) => string;
}

function GoalBlock({
  title, kpis, values, savedKeys, onChange, onSave, saving, t,
}: GoalBlockProps) {
  return (
    <div className="gs-block">
      <h4 className="gs-block-title">{title}</h4>
      <div className="gs-rows">
        {kpis.map((kpi) => (
          <GoalInputRow
            key={kpi}
            kpiType={kpi}
            value={values[kpi] ?? ""}
            onChange={(v) => onChange(kpi, v)}
            saved={savedKeys.has(kpi)}
            t={t}
          />
        ))}
      </div>
      <button className="btn-primary gs-save-btn" onClick={onSave} disabled={saving}>
        {saving ? t("common.saving") : t("goals.save")}
      </button>
    </div>
  );
}

interface AdvisorMetricRowProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  recommended: number | null | undefined;
  testId: string;
}

function AdvisorMetricRow({ label, value, onChange, recommended, testId }: AdvisorMetricRowProps) {
  return (
    <div className="gs-advisor__metric" data-testid={testId}>
      <div className="gs-advisor__metric-head">
        <span className="gs-advisor__metric-label">{label}</span>
        <span className="gs-advisor__metric-rec">
          {recommended === null || recommended === undefined
            ? "—"
            : `おすすめ ${formatAdviceNumber(recommended)}`}
        </span>
      </div>
      <input
        type="number"
        min="0"
        step="1"
        className="gs-input gs-advisor__metric-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label={label}
      />
    </div>
  );
}

interface GoalAdvisorPanelProps {
  defaultMonthlyKgi: string;
  t: (k: string, options?: Record<string, unknown>) => string;
}

function GoalAdvisorPanel({ defaultMonthlyKgi, t }: GoalAdvisorPanelProps) {
  const [monthlyKgi, setMonthlyKgi] = useState(defaultMonthlyKgi);
  const [kgiType, setKgiType] = useState<"revenue" | "wins">("revenue");
  const [advice, setAdvice] = useState<GoalAdviceResponse | null>(null);
  const [draft, setDraft] = useState({ leads: "", deals: "", wins: "" });
  const [loadingAdvice, setLoadingAdvice] = useState(false);
  const [advisorError, setAdvisorError] = useState("");
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const seededMonthlyRef = useRef(false);

  useEffect(() => {
    if (seededMonthlyRef.current) return;
    if (!defaultMonthlyKgi) return;
    setMonthlyKgi(defaultMonthlyKgi);
    seededMonthlyRef.current = true;
  }, [defaultMonthlyKgi]);

  useEffect(() => {
    if (!advice) return;
    setDraft({
      leads: advice.weekly_required.leads === null ? "" : String(Math.round(advice.weekly_required.leads)),
      deals: advice.weekly_required.deals === null ? "" : String(Math.round(advice.weekly_required.deals)),
      wins: advice.weekly_required.wins === null ? "" : String(Math.round(advice.weekly_required.wins)),
    });
  }, [advice]);

  const fetchAdvice = async () => {
    const parsedMonthly = Number(monthlyKgi);
    if (!monthlyKgi.trim() || Number.isNaN(parsedMonthly)) {
      setAdvisorError(t("goals.advisorMonthlyRequired"));
      return;
    }

    setLoadingAdvice(true);
    setAdvisorError("");

    try {
      const params = new URLSearchParams({
        monthly_kgi: String(parsedMonthly),
        kgi_type: kgiType,
        scope: "mine",
        period: ADVICE_PERIOD,
      });
      const result = await api.get<GoalAdviceResponse>(`/analytics/new-goal-advice?${params.toString()}`);
      setAdvice(result);
      setGeneratedAt(new Date().toLocaleString("ja-JP", { hour12: false }));
      setDraft({
        leads: result.data_sufficient && result.weekly_required.leads !== null ? String(Math.round(result.weekly_required.leads)) : "",
        deals: result.data_sufficient && result.weekly_required.deals !== null ? String(Math.round(result.weekly_required.deals)) : "",
        wins: result.data_sufficient && result.weekly_required.wins !== null ? String(Math.round(result.weekly_required.wins)) : "",
      });
    } catch (e: unknown) {
      setAdvisorError((e as Error).message);
      setAdvice(null);
      setGeneratedAt(null);
      setDraft({ leads: "", deals: "", wins: "" });
    } finally {
      setLoadingAdvice(false);
    }
  };

  const monthlyRequired = advice ? advice.monthly_required : null;
  const weeklyRequired = advice ? advice.weekly_required : null;
  const ratesUsed = advice ? advice.rates_used : null;
  const workingDays = advice ? advice.working_days : null;
  const insufficient = advice ? !advice.data_sufficient : false;

  return (
    <section className="gs-advisor" data-testid="goal-advisor-card">
      <div className="gs-advisor__eyebrow">
        <span className="gs-advisor__pill">{t("goals.aiLabel")}</span>
        <span className="gs-advisor__eyebrow-text">{t("goals.advisorEyebrow")}</span>
      </div>

      <div className="gs-advisor__grid">
        <div className="gs-advisor__main">
          <div className="gs-advisor__header">
            <h3 className="gs-advisor__title">{t("goals.advisorTitle")}</h3>
            <p className="gs-advisor__lead">{t("goals.advisorLead")}</p>
          </div>

          <div className="gs-advisor__form">
            <label className="gs-label" htmlFor="advisor-monthly-kgi">
              {t("goals.advisorMonthlyLabel")}
            </label>
            <div className="gs-advisor__monthly-row">
              <input
                id="advisor-monthly-kgi"
                data-testid="goal-advisor-monthly-kgi"
                type="number"
                min="0"
                step="1"
                className="gs-input gs-advisor__monthly-input"
                value={monthlyKgi}
                onChange={(e) => setMonthlyKgi(e.target.value)}
                placeholder={t("goals.advisorMonthlyPlaceholder")}
              />
              <div className="gs-advisor__toggle" role="group" aria-label={t("goals.advisorTypeLabel")}>
                <button
                  type="button"
                  data-testid="goal-advisor-type-revenue"
                  className={`gs-advisor__toggle-btn${kgiType === "revenue" ? " is-active" : ""}`}
                  onClick={() => setKgiType("revenue")}
                >
                  {t("goals.advisorTypeRevenue")}
                </button>
                <button
                  type="button"
                  data-testid="goal-advisor-type-wins"
                  className={`gs-advisor__toggle-btn${kgiType === "wins" ? " is-active" : ""}`}
                  onClick={() => setKgiType("wins")}
                >
                  {t("goals.advisorTypeWins")}
                </button>
              </div>
              <button
                type="button"
                className="btn-primary gs-advisor__run-btn"
                data-testid="goal-advisor-generate"
                onClick={fetchAdvice}
                disabled={loadingAdvice}
              >
                {loadingAdvice ? t("common.loading") : t("goals.advisorGenerate")}
              </button>
            </div>
            <p className="gs-advisor__scope-note">{t("goals.advisorScopeMine")}</p>
          </div>

          {advisorError && <div className="gs-advisor__alert gs-advisor__alert--danger">{advisorError}</div>}
          {insufficient && (
            <div className="gs-advisor__alert gs-advisor__alert--warning">
              {t("goals.advisorInsufficient")}
            </div>
          )}
          {advice?.working_days.shift_status === "not_submitted" && (
            <div className="gs-advisor__alert gs-advisor__alert--soft">
              {t("goals.advisorShiftNotSubmitted")}
            </div>
          )}

          {advice && (
            <div className="gs-advisor__plan">
              <div className="gs-advisor__plan-head">
                <div>
                  <p className="gs-advisor__plan-kicker">{t("goals.aiLabel")}</p>
                  <h4 className="gs-advisor__plan-title">{t("goals.advisorPlanTitle")}</h4>
                </div>
                <p className="gs-advisor__plan-note">{t("goals.advisorPlanNote")}</p>
              </div>

              <div className="gs-advisor__metric-grid">
                <AdvisorMetricRow
                  label={t("goals.advisorLeads")}
                  value={draft.leads}
                  onChange={(value) => setDraft((prev) => ({ ...prev, leads: value }))}
                  recommended={weeklyRequired?.leads}
                  testId="goal-advisor-weekly-leads"
                />
                <AdvisorMetricRow
                  label={t("goals.advisorDeals")}
                  value={draft.deals}
                  onChange={(value) => setDraft((prev) => ({ ...prev, deals: value }))}
                  recommended={weeklyRequired?.deals}
                  testId="goal-advisor-weekly-deals"
                />
                <AdvisorMetricRow
                  label={t("goals.advisorWins")}
                  value={draft.wins}
                  onChange={(value) => setDraft((prev) => ({ ...prev, wins: value }))}
                  recommended={weeklyRequired?.wins}
                  testId="goal-advisor-weekly-wins"
                />
              </div>
            </div>
          )}
        </div>

        <aside className="gs-advisor__aside">
          <div className="gs-advisor__aside-card">
            <div className="gs-advisor__aside-head">
              <span className="gs-advisor__aside-kicker">{t("goals.advisorEvidenceLabel")}</span>
              <span className={`gs-advisor__status${advice?.working_days.shift_status === "submitted" ? " is-positive" : ""}`}>
                {advice ? t(`goals.shiftStatus_${advice.working_days.shift_status}`) : t("goals.advisorWaiting")}
              </span>
            </div>

            <dl className="gs-advisor__facts">
              <div>
                <dt>{t("goals.advisorUnitPrice")}</dt>
                <dd>{ratesUsed === null || ratesUsed.unit_price === null ? "—" : `¥${formatAdviceNumber(ratesUsed.unit_price)}`}</dd>
              </div>
              <div>
                <dt>{t("goals.advisorWinRate")}</dt>
                <dd>{ratesUsed === null || ratesUsed.win_rate === null ? "—" : `${formatAdviceNumber(ratesUsed.win_rate)}%`}</dd>
              </div>
              <div>
                <dt>{t("goals.advisorDealRate")}</dt>
                <dd>{ratesUsed === null || ratesUsed.deal_rate === null ? "—" : `${formatAdviceNumber(ratesUsed.deal_rate)}%`}</dd>
              </div>
              <div>
                <dt>{t("goals.advisorWorkingDays")}</dt>
                <dd>
                  {workingDays
                    ? t("goals.advisorWorkingDaysValue", {
                      month: workingDays.remaining_month,
                      week: workingDays.remaining_week,
                    })
                    : "—"}
                </dd>
              </div>
            </dl>

            <details className="gs-advisor__details">
              <summary>{t("goals.advisorShowReasoning")}</summary>
              <div className="gs-advisor__details-body">
                <p className="gs-advisor__details-note">{t("goals.advisorDecisionNote")}</p>
                <ol className="gs-advisor__steps">
                  <li>{t("goals.advisorStep1", { value: formatAdviceNumber(advice?.inputs.monthly_kgi) || "—" })}</li>
                  <li>
                    {t("goals.advisorStep2", {
                      unitPrice: ratesUsed === null || ratesUsed.unit_price === null ? "—" : `¥${formatAdviceNumber(ratesUsed.unit_price)}`,
                      wins: monthlyRequired === null ? "—" : formatAdviceNumber(monthlyRequired.wins) || "—",
                    })}
                  </li>
                  <li>
                    {t("goals.advisorStep3", {
                      winRate: ratesUsed === null || ratesUsed.win_rate === null ? "—" : `${formatAdviceNumber(ratesUsed.win_rate)}%`,
                      dealRate: ratesUsed === null || ratesUsed.deal_rate === null ? "—" : `${formatAdviceNumber(ratesUsed.deal_rate)}%`,
                    })}
                  </li>
                </ol>
                <div className="gs-advisor__reason-grid">
                  <div>
                    <span>{t("goals.advisorMonthlyRequired")}</span>
                    <strong>{monthlyRequired === null || monthlyRequired.wins === null ? "—" : formatAdviceNumber(monthlyRequired.wins)}</strong>
                  </div>
                  <div>
                    <span>{t("goals.advisorWeeklyRequired")}</span>
                    <strong>{weeklyRequired === null || weeklyRequired.wins === null ? "—" : formatAdviceNumber(weeklyRequired.wins)}</strong>
                  </div>
                  <div>
                    <span>{t("goals.advisorGeneratedAt")}</span>
                    <strong>{generatedAt ?? "—"}</strong>
                  </div>
                </div>
              </div>
            </details>
          </div>
        </aside>
      </div>
    </section>
  );
}

// ─── メインコンポーネント ──────────────────────────────────────

export default function GoalSettingPage() {
  const { t } = useTranslation();

  const [teams, setTeams] = useState<Team[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);

  // 個人目標 value マップ
  const [indivMonthValues, setIndivMonthValues] = useState<Record<KpiType, string>>({} as Record<KpiType, string>);
  const [indivWeekValues, setIndivWeekValues] = useState<Record<KpiType, string>>({} as Record<KpiType, string>);
  // チーム目標 value マップ
  const [teamMonthValues, setTeamMonthValues] = useState<Record<KpiType, string>>({} as Record<KpiType, string>);
  const [teamWeekValues, setTeamWeekValues] = useState<Record<KpiType, string>>({} as Record<KpiType, string>);

  const [savedIndivMonth, setSavedIndivMonth] = useState<Set<KpiType>>(new Set());
  const [savedIndivWeek, setSavedIndivWeek] = useState<Set<KpiType>>(new Set());
  const [savedTeamMonth, setSavedTeamMonth] = useState<Set<KpiType>>(new Set());
  const [savedTeamWeek, setSavedTeamWeek] = useState<Set<KpiType>>(new Set());

  const [savingIndivMonth, setSavingIndivMonth] = useState(false);
  const [savingIndivWeek, setSavingIndivWeek] = useState(false);
  const [savingTeamMonth, setSavingTeamMonth] = useState(false);
  const [savingTeamWeek, setSavingTeamWeek] = useState(false);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [monthlyAdvisorSeed, setMonthlyAdvisorSeed] = useState("");
  const advisorSeededRef = useRef(false);

  const { year: curYear, month: curMonth } = currentYearMonth();
  const { year: weekYear, week: curWeek } = currentYearWeek();

  const isLeader = (user: CurrentUser | null, team: Team | null) =>
    user?.role === "admin" ||
    (team !== null && team.leader_id === user?.id);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get<{ id: number; role: string }>("/auth/me"),
      api.get<Team[]>("/teams"),
    ])
      .then(([me, teamList]) => {
        setCurrentUser(me);
        setTeams(teamList);
        if (teamList.length > 0) setSelectedTeamId(teamList[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // 既存目標をロード
  useEffect(() => {
    if (!currentUser) return;
    // 個人目標
    api
      .get<GoalResponse[]>(`/goals?user_id=${currentUser.id}&period_year=${curYear}`)
      .then((rows) => {
        const mvals: Record<string, string> = {};
        const wvals: Record<string, string> = {};
        rows.forEach((r) => {
          if (r.period_type === "monthly" && r.period_num === curMonth)
            mvals[r.kpi_type] = String(r.target_value);
          if (r.period_type === "weekly" && r.period_num === curWeek)
            wvals[r.kpi_type] = String(r.target_value);
        });
        setIndivMonthValues(mvals as Record<KpiType, string>);
        setIndivWeekValues(wvals as Record<KpiType, string>);
        if (!advisorSeededRef.current && mvals.revenue) {
          setMonthlyAdvisorSeed(mvals.revenue);
          advisorSeededRef.current = true;
        }
      })
      .catch(() => {});
  }, [currentUser, curYear, curMonth, curWeek]);

  useEffect(() => {
    if (!selectedTeamId) return;
    api
      .get<GoalResponse[]>(`/goals?team_id=${selectedTeamId}&period_year=${curYear}`)
      .then((rows) => {
        const mvals: Record<string, string> = {};
        const wvals: Record<string, string> = {};
        rows.forEach((r) => {
          if (r.period_type === "monthly" && r.period_num === curMonth)
            mvals[r.kpi_type] = String(r.target_value);
          if (r.period_type === "weekly" && r.period_num === curWeek)
            wvals[r.kpi_type] = String(r.target_value);
        });
        setTeamMonthValues(mvals as Record<KpiType, string>);
        setTeamWeekValues(wvals as Record<KpiType, string>);
      })
      .catch(() => {});
  }, [selectedTeamId, curYear, curMonth, curWeek]);

  async function saveGoals(
    kpis: KpiType[],
    values: Record<KpiType, string>,
    periodType: PeriodType,
    periodNum: number,
    ownerId: number,
    ownerType: "user" | "team",
    setSaving: (v: boolean) => void,
    setSaved: (s: Set<KpiType>) => void,
  ) {
    setSaving(true);
    try {
      const saved = new Set<KpiType>();
      for (const kpi of kpis) {
        const raw = values[kpi];
        if (!raw && raw !== "0") continue;
        const val = parseFloat(raw);
        if (Number.isNaN(val)) continue;
        await api.post("/goals", {
          [ownerType === "user" ? "user_id" : "team_id"]: ownerId,
          period_type: periodType,
          period_year: periodType === "monthly" ? curYear : weekYear,
          period_num: periodNum,
          kpi_type: kpi,
          target_value: val,
        });
        saved.add(kpi);
      }
      setSaved(saved);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const selectedTeam = teams.find((t) => t.id === selectedTeamId) ?? null;
  const canEditTeam = isLeader(currentUser, selectedTeam);

  if (loading) {
    return (
      <PageLayout navKey="nav.goalSettings" subtitleKey="goals.subtitle">
        <div className="loading">{t("common.loading")}</div>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.goalSettings" subtitleKey="goals.subtitle">
      {error && <div className="error-message">{error}</div>}

      <GoalAdvisorPanel defaultMonthlyKgi={monthlyAdvisorSeed} t={t} />

      <div className="gs-layout">
        {/* ── 個人目標 ── */}
        <section className="gs-section">
          <h3 className="gs-section-title">{t("goals.individualTitle")}</h3>
          <GoalBlock
            title={t("goals.monthlyGoal", { month: curMonth })}
            kpis={INDIVIDUAL_KPIS}
            values={indivMonthValues}
            savedKeys={savedIndivMonth}
            onChange={(kpi, v) =>
              setIndivMonthValues((prev) => ({ ...prev, [kpi]: v }))
            }
            onSave={() =>
              saveGoals(
                INDIVIDUAL_KPIS,
                indivMonthValues,
                "monthly",
                curMonth,
                currentUser!.id,
                "user",
                setSavingIndivMonth,
                setSavedIndivMonth,
              )
            }
            saving={savingIndivMonth}
            t={t}
          />
          <GoalBlock
            title={t("goals.weeklyGoal", { week: curWeek })}
            kpis={INDIVIDUAL_KPIS}
            values={indivWeekValues}
            savedKeys={savedIndivWeek}
            onChange={(kpi, v) =>
              setIndivWeekValues((prev) => ({ ...prev, [kpi]: v }))
            }
            onSave={() =>
              saveGoals(
                INDIVIDUAL_KPIS,
                indivWeekValues,
                "weekly",
                curWeek,
                currentUser!.id,
                "user",
                setSavingIndivWeek,
                setSavedIndivWeek,
              )
            }
            saving={savingIndivWeek}
            t={t}
          />
        </section>

        {/* ── チーム目標（リーダー以上のみ） ── */}
        {teams.length > 0 && (
          <section className="gs-section">
            <h3 className="gs-section-title">{t("goals.teamTitle")}</h3>

            {/* チーム選択 */}
            <div className="gs-team-select-wrap">
              <label className="gs-label">{t("goals.selectTeam")}</label>
              <select
                className="gs-select"
                value={selectedTeamId ?? ""}
                onChange={(e) => setSelectedTeamId(Number(e.target.value))}
              >
                {teams.map((tm) => (
                  <option key={tm.id} value={tm.id}>
                    {tm.name}
                  </option>
                ))}
              </select>
            </div>

            {canEditTeam ? (
              <>
                <GoalBlock
                  title={t("goals.monthlyGoal", { month: curMonth })}
                  kpis={TEAM_KPIS}
                  values={teamMonthValues}
                  savedKeys={savedTeamMonth}
                  onChange={(kpi, v) =>
                    setTeamMonthValues((prev) => ({ ...prev, [kpi]: v }))
                  }
                  onSave={() =>
                    saveGoals(
                      TEAM_KPIS,
                      teamMonthValues,
                      "monthly",
                      curMonth,
                      selectedTeamId!,
                      "team",
                      setSavingTeamMonth,
                      setSavedTeamMonth,
                    )
                  }
                  saving={savingTeamMonth}
                  t={t}
                />
                <GoalBlock
                  title={t("goals.weeklyGoal", { week: curWeek })}
                  kpis={TEAM_KPIS}
                  values={teamWeekValues}
                  savedKeys={savedTeamWeek}
                  onChange={(kpi, v) =>
                    setTeamWeekValues((prev) => ({ ...prev, [kpi]: v }))
                  }
                  onSave={() =>
                    saveGoals(
                      TEAM_KPIS,
                      teamWeekValues,
                      "weekly",
                      curWeek,
                      selectedTeamId!,
                      "team",
                      setSavingTeamWeek,
                      setSavedTeamWeek,
                    )
                  }
                  saving={savingTeamWeek}
                  t={t}
                />
              </>
            ) : (
              <p className="gs-no-permission">{t("goals.noEditPermission")}</p>
            )}
          </section>
        )}
      </div>
    </PageLayout>
  );
}
