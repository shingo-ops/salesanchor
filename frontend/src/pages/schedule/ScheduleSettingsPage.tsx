import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { SectionCard } from "../../components/SectionCard";
import { SubMenu } from "../../components/SubMenu";
import { ColorSwatchPicker, type ColorSwatchOption } from "../../components/ColorSwatchPicker";
import { MultiSelect } from "../../components/MultiSelect";
import { SelectControl } from "../../components/Select";
import { TextFieldControl } from "../../components/TextField";
import { Toggle } from "../../components/Toggle";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import {
  categoryLabel,
  parseShare,
  useCalendarCategories,
  type CalendarCategory,
  type CalendarShare,
} from "../../features/schedule/useCalendarCategories";
import {
  DEFAULT_CALENDAR_PREFERENCES,
  normalizePreferences,
  PREFERENCE_EVENT_MINUTES,
  PREFERENCE_VIEWS,
  useCalendarPreferences,
  type ApiCalendarPreferences,
  type PreferenceOpenOwners,
  type PreferenceView,
} from "../../features/schedule/useCalendarPreferences";
import { teamIdsToValues, useCalendarTeams, valuesToTeamIds } from "../../features/schedule/useCalendarTeams";
import { usePermissions } from "../../hooks/usePermissions";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import {
  DEFAULT_OWNER_COLOR,
  normalizeOwner,
  type ApiCalendarOwnersResponse,
  type CalendarOwner,
} from "./schedule-owner";
import { LoadingBlock } from "../../components/loading";
import { EVENT_COLOR_KEYS, eventColorLabelKey, eventColorVar, isEventColorKey } from "./eventColors";
import { formatDateInput } from "./schedule-utils";

const EMPTY_OWNERS: CalendarOwner[] = [];

/** 種類 1 行の入力中の値（名前の空は「名前を付けない（7 種は元の名前に戻る）」） */
interface CategoryForm {
  name: string;
  colorKey: string | null;
  defaultShare: CalendarShare;
  /** defaultShare が team のときの初期のチーム */
  defaultTeamIds: number[];
  isActive: boolean;
}

const EMPTY_CATEGORY_FORMS: Record<string, CategoryForm> = {};
const NEW_CATEGORY_FORM: CategoryForm = { name: "", colorKey: null, defaultShare: "all", defaultTeamIds: [], isActive: true };
/** 足した種類の鍵の頭（裏側が決める。名前を空にできないのはこの種類だけ） */
const CUSTOM_CATEGORY_PREFIX = "custom_";

function toCategoryForm(category: CalendarCategory): CategoryForm {
  return {
    name: category.name ?? "",
    colorKey: isEventColorKey(category.color_key) ? category.color_key : null,
    defaultShare: category.default_share,
    defaultTeamIds: category.default_team_ids ?? [],
    isActive: category.is_active,
  };
}

function toCategoryForms(list: CalendarCategory[]): Record<string, CategoryForm> {
  return Object.fromEntries(list.map((category) => [category.key, toCategoryForm(category)]));
}

/** 失敗の状態の番号（ApiError でなくても読めるように形で見る） */
function errorStatus(error: unknown): number | null {
  const status = (error as { status?: unknown } | null)?.status;
  return typeof status === "number" ? status : null;
}

function OwnerBadge({ owner }: { owner: CalendarOwner }) {
  return (
    <span className="schedule-settings__account">
      <span
        className="schedule-settings__avatar schedule-settings__avatar--small"
        style={{ background: owner.color }}
        aria-hidden="true"
      >
        {owner.name.slice(0, 1) || "?"}
      </span>
      <span className="schedule-settings__account-email">
        {owner.name}
      </span>
    </span>
  );
}

type SectionKey = "personal" | "google" | "categories" | "self" | "others";

interface GoogleStatus {
  connected: boolean;
  connected_at?: string | null;
  /** 新しい予定に Google Meet を付けられるか（Google をつないだ本人だけ） */
  meet_available?: boolean;
}

export default function ScheduleSettingsPage() {
  const { t } = useTranslation();
  const { hasPermission, isTenantAdmin, loading: permsLoading } = usePermissions();
  const [searchParams, setSearchParams] = useSearchParams();
  const ownersEnabled = !permsLoading && hasPermission("staff.view");
  const ownersQ = useApiQuery<ApiCalendarOwnersResponse>("/calendar/owners", {
    enabled: ownersEnabled,
  });
  const { form: owners, setForm: setOwners, ready } = useSeededForm(
    "calendar/owners",
    ownersQ.data,
    (d) => d.owners.map(normalizeOwner),
    EMPTY_OWNERS,
  );
  const loading = ownersEnabled && !ready && !ownersQ.isError;
  const invalidate = useInvalidateApi();
  const [savingStaffId, setSavingStaffId] = useState<number | null>(null);
  const [savedStaffId, setSavedStaffId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const shownError = error ?? (ownersQ.error ? (ownersQ.error instanceof Error ? ownersQ.error.message : t("common.fetchError")) : null);

  // Google 連携の区画（管理者だけ）
  const gcalStatusQ = useApiQuery<GoogleStatus>("/google-calendar/status", {
    enabled: isTenantAdmin === true,
  });
  const gcalConnected = gcalStatusQ.data?.connected === true;
  const gcalConnectedAt = gcalStatusQ.data?.connected_at ?? null;
  const [connectNoticeOpen, setConnectNoticeOpen] = useState(false);
  const [disconnectOpen, setDisconnectOpen] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [activeSection, setActiveSection] = useState<SectionKey>("personal");

  // 予定の種類の区画（管理者だけ）。正本は GET /calendar/categories（useCalendarCategories）
  const { categories, query: categoriesQ } = useCalendarCategories();
  const { form: categoryForms, setForm: setCategoryForms } = useSeededForm(
    "calendar/categories",
    categoriesQ.data,
    toCategoryForms,
    EMPTY_CATEGORY_FORMS,
  );
  const [newCategory, setNewCategory] = useState<CategoryForm | null>(null);
  const [savingCategoryKey, setSavingCategoryKey] = useState<string | null>(null);
  const [savedCategoryKey, setSavedCategoryKey] = useState<string | null>(null);
  const [categoryError, setCategoryError] = useState<string | null>(null);
  const NEW_CATEGORY_KEY = "__new__";
  // 共有の初期値・開いたときのチームに選べるチーム（使っているものだけ。ログインしていれば誰でも読める）
  const { options: teamOptions } = useCalendarTeams();

  // ひとりひとりの初期値の区画（全員）。読めるまで保存ボタンは押せない（読めない・読み込み中に既定値で上書きしない）
  const { query: prefsQ } = useCalendarPreferences();
  const { form: prefForm, setForm: setPrefForm, ready: prefsReady } = useSeededForm(
    "calendar/preferences",
    prefsQ.data,
    (d: ApiCalendarPreferences) => normalizePreferences(d),
    DEFAULT_CALENDAR_PREFERENCES,
  );
  const [prefsSaving, setPrefsSaving] = useState(false);
  const [prefsSaved, setPrefsSaved] = useState(false);
  const [prefsError, setPrefsError] = useState<string | null>(null);
  const meetAvailable = gcalStatusQ.data?.meet_available === true;
  const canPickOwners = !permsLoading && hasPermission("staff.view");

  const savePrefs = async () => {
    if (!prefsReady) return;
    setPrefsSaving(true);
    setPrefsSaved(false);
    setPrefsError(null);
    try {
      // Meet の行が隠れているときも、読んだ auto_meet をそのまま送る（落とさない・戻さない）
      await api.put("/calendar/preferences", {
        ...prefForm,
        open_team_id: prefForm.open_owners === "team" ? prefForm.open_team_id : null,
      });
      await invalidate(["calendar", "preferences"]);
      setPrefsSaved(true);
    } catch (e) {
      setPrefsError(errorStatus(e) === 422 && e instanceof Error && e.message ? e.message : t("schedule.prefsSaveError"));
    } finally {
      setPrefsSaving(false);
    }
  };

  const categoryErrorText = (e: unknown): string => {
    const status = errorStatus(e);
    if (status === 409) return t("schedule.categoryErrorConflict");
    if (status === 422) return t("schedule.categoryErrorInvalid");
    return t("schedule.categoryErrorSave");
  };

  const updateCategoryForm = (key: string, patch: Partial<CategoryForm>) => {
    setCategoryForms((current) => {
      const base = current[key] ?? toCategoryForm(categories.find((category) => category.key === key) as CalendarCategory);
      return { ...current, [key]: { ...base, ...patch } };
    });
  };

  const saveCategory = async (key: string) => {
    const form = categoryForms[key];
    if (!form) return;
    if (key.startsWith(CUSTOM_CATEGORY_PREFIX) && form.name.trim() === "") {
      setCategoryError(t("schedule.categoryErrorNameRequired"));
      return;
    }
    if (form.defaultShare === "team" && form.defaultTeamIds.length === 0) {
      setCategoryError(t("schedule.shareTeamsRequired"));
      return;
    }
    setSavingCategoryKey(key);
    setSavedCategoryKey(null);
    setCategoryError(null);
    try {
      const saved = await api.patch<CalendarCategory>(`/calendar/categories/${key}`, {
        name: form.name.trim(),
        color_key: form.colorKey ?? "",
        default_share: form.defaultShare,
        ...(form.defaultShare === "team" ? { default_team_ids: form.defaultTeamIds } : {}),
        is_active: form.isActive,
      });
      if (saved && typeof saved === "object" && "key" in saved) {
        setCategoryForms((current) => ({ ...current, [key]: toCategoryForm(saved) }));
      }
      setSavedCategoryKey(key);
      void invalidate(["calendar", "categories"]);
    } catch (e) {
      setCategoryError(categoryErrorText(e));
    } finally {
      setSavingCategoryKey(null);
    }
  };

  const addCategory = async () => {
    if (!newCategory) return;
    if (newCategory.name.trim() === "") {
      setCategoryError(t("schedule.categoryErrorNameRequired"));
      return;
    }
    if (newCategory.defaultShare === "team" && newCategory.defaultTeamIds.length === 0) {
      setCategoryError(t("schedule.shareTeamsRequired"));
      return;
    }
    setSavingCategoryKey(NEW_CATEGORY_KEY);
    setSavedCategoryKey(null);
    setCategoryError(null);
    try {
      const created = await api.post<CalendarCategory>("/calendar/categories", {
        name: newCategory.name.trim(),
        color_key: newCategory.colorKey ?? "",
        default_share: newCategory.defaultShare,
        ...(newCategory.defaultShare === "team" ? { default_team_ids: newCategory.defaultTeamIds } : {}),
      });
      if (created && typeof created === "object" && "key" in created) {
        setCategoryForms((current) => ({ ...current, [created.key]: toCategoryForm(created) }));
        setSavedCategoryKey(created.key);
      }
      setNewCategory(null);
      void invalidate(["calendar", "categories"]);
    } catch (e) {
      setCategoryError(categoryErrorText(e));
    } finally {
      setSavingCategoryKey(null);
    }
  };

  // つないだ後・失敗した後の戻り（?connected=true|false&error=）を帯にする
  useEffect(() => {
    const connected = searchParams.get("connected");
    if (connected === "true") {
      setBanner({ type: "success", message: t("schedule.connectSuccess") });
    } else if (connected === "false") {
      const errorCode = searchParams.get("error");
      setBanner({
        type: "error",
        message: errorCode === "scope_missing" ? t("schedule.connectScopeMissing") : t("schedule.connectError"),
      });
    }
    if (connected) {
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selfOwner = useMemo(() => owners.find((owner) => owner.isSelf) ?? null, [owners]);
  const otherOwners = useMemo(() => owners.filter((owner) => !owner.isSelf), [owners]);

  const jumpToSection = (key: SectionKey) => {
    setActiveSection(key);
    document.getElementById(`schedule-settings-${key}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const startConnect = async () => {
    setConnectNoticeOpen(false);
    try {
      const { auth_url } = await api.get<{ auth_url: string }>("/google-calendar/connect/start");
      window.location.href = auth_url;
    } catch {
      setBanner({ type: "error", message: t("schedule.connectError") });
    }
  };

  const confirmDisconnect = async () => {
    setDisconnecting(true);
    try {
      await api.delete("/google-calendar/connect");
      setDisconnectOpen(false);
      await gcalStatusQ.refetch();
      setBanner({ type: "success", message: t("schedule.disconnectSuccess") });
    } catch {
      setDisconnectOpen(false);
      setBanner({ type: "error", message: t("schedule.disconnectError") });
    } finally {
      setDisconnecting(false);
    }
  };

  const updateOwner = (staffId: number, patch: Partial<CalendarOwner>) => {
    setOwners((current) => current.map((owner) => (
      owner.staffId === staffId ? { ...owner, ...patch } : owner
    )));
  };

  const saveOwner = async (owner: CalendarOwner) => {
    // PATCH のパスは users.id（ADR-1008）。user_id が無い名簿行は保存できない
    if (owner.userId == null) return;
    setSavingStaffId(owner.staffId);
    setSavedStaffId(null);
    setError(null);
    try {
      await api.patch(`/calendar/owners/${owner.userId}`, { color_key: owner.colorKey });
      setSavedStaffId(owner.staffId);
      void invalidate(["calendar", "owners"]);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSavingStaffId(null);
    }
  };

  if (permsLoading) {
    return <div className="page"><LoadingBlock /></div>;
  }

  const menuItems = [
    { key: "personal" as SectionKey, label: t("schedule.prefsTitle") },
    ...(isTenantAdmin ? [{ key: "google" as SectionKey, label: t("schedule.settingsGoogleTitle") }] : []),
    ...(isTenantAdmin ? [{ key: "categories" as SectionKey, label: t("schedule.categoriesTitle") }] : []),
    ...(ownersEnabled ? [{ key: "self" as SectionKey, label: t("schedule.myCalendars") }] : []),
    ...(ownersEnabled && otherOwners.length > 0
      ? [{ key: "others" as SectionKey, label: t("schedule.otherCalendars") }]
      : []),
  ];

  const ownerColorOptions: ColorSwatchOption[] = [
    { value: null, label: t("schedule.ownerColorDefault"), color: DEFAULT_OWNER_COLOR },
    ...EVENT_COLOR_KEYS.map((key) => ({ value: key, label: t(eventColorLabelKey(key)), color: eventColorVar(key) })),
  ];

  const categoryColorOptions: ColorSwatchOption[] = [
    { value: null, label: t("schedule.categoryNoColor"), color: "var(--border)" },
    ...EVENT_COLOR_KEYS.map((key) => ({ value: key, label: t(eventColorLabelKey(key)), color: eventColorVar(key) })),
  ];

  /** 種類 1 行（key が null の行は「種類を足す」の新しい行） */
  const renderCategoryRow = (
    rowKey: string,
    form: CategoryForm,
    onChange: (patch: Partial<CategoryForm>) => void,
    onSave: () => void,
    category: CalendarCategory | null,
  ) => {
    const fallbackName = category ? categoryLabel(category.key, null, t) : "";
    const keepsActive = category?.key === "meeting"; // meeting は使わなくできない
    return (
      <div key={rowKey} className="schedule-settings__calendar-row">
        <div className="schedule-settings__row-copy">
          <TextFieldControl
            value={form.name}
            aria-label={t("schedule.categoryName")}
            placeholder={category ? fallbackName : t("schedule.categoryNamePlaceholder")}
            onChange={(event) => onChange({ name: event.target.value })}
          />
          {category && form.name.trim() === "" && !category.key.startsWith(CUSTOM_CATEGORY_PREFIX) && (
            <span className="schedule-settings__description">{t("schedule.categoryNameBlankHint")}</span>
          )}
          {keepsActive && (
            <span className="schedule-settings__description">{t("schedule.categoryCannotDisable")}</span>
          )}
        </div>
        <div className="schedule-settings__calendar-actions">
          <ColorSwatchPicker
            label={t("schedule.categoryColor")}
            name={`schedule-category-color-${rowKey}`}
            options={categoryColorOptions}
            value={form.colorKey}
            onChange={(value) => onChange({ colorKey: isEventColorKey(value) ? value : null })}
          />
          <SelectControl
            size="sm"
            aria-label={t("schedule.categoryDefaultShare")}
            value={form.defaultShare}
            options={[
              { value: "self", label: t("schedule.shareSelf") },
              { value: "all", label: t("schedule.shareAll") },
              { value: "team", label: t("schedule.shareTeam") },
            ]}
            onChange={(event) => onChange({ defaultShare: parseShare(event.target.value) })}
          />
          {form.defaultShare === "team" && (
            <>
              <MultiSelect
                label={t("schedule.shareTeams")}
                options={teamOptions}
                selected={teamIdsToValues(form.defaultTeamIds)}
                onChange={(values) => onChange({ defaultTeamIds: valuesToTeamIds(values) })}
                clearLabel={t("schedule.shareTeamsClear")}
                allLabel={t("schedule.shareTeamsNone")}
                countLabel={(count) => t("schedule.shareTeamsCount", { count })}
                emptyLabel={t("schedule.noActiveTeams")}
                layout="popover"
                testId={`schedule-category-teams-${rowKey}`}
              />
              {form.defaultTeamIds.length === 0 && (
                <span className="schedule-settings__description">{t("schedule.shareTeamsRequired")}</span>
              )}
            </>
          )}
          {category && (
            <span className="schedule-settings__account">
              <span className="schedule-settings__description">{t("schedule.categoryActive")}</span>
              <Toggle
                checked={keepsActive ? true : form.isActive}
                disabled={keepsActive}
                aria-label={t("schedule.categoryActive")}
                onCheckedChange={(next) => onChange({ isActive: next })}
              />
            </span>
          )}
          <Button variant="secondary" onClick={onSave} loading={savingCategoryKey === rowKey}>
            {t("schedule.settingsSave")}
          </Button>
          {savedCategoryKey === rowKey && (
            <span className="schedule-settings__timestamp">
              <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> {t("schedule.settingsSaved")}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderOwnerRow = (owner: CalendarOwner, description: string | null) => (
    <div key={owner.staffId} className="schedule-settings__calendar-row">
      <div className="schedule-settings__row-copy">
        <OwnerBadge owner={owner} />
        {description && <span className="schedule-settings__description">{description}</span>}
      </div>
      <div className="schedule-settings__calendar-actions">
        <ColorSwatchPicker
          label={t("schedule.settingsCalendarColor")}
          name={`owner-color-${owner.staffId}`}
          options={ownerColorOptions}
          value={owner.colorKey}
          onChange={(value) => {
            const colorKey = isEventColorKey(value) ? value : null;
            updateOwner(owner.staffId, {
              colorKey,
              color: colorKey ? eventColorVar(colorKey) : DEFAULT_OWNER_COLOR,
            });
          }}
        />
        <Button
          variant="secondary"
          onClick={() => saveOwner(owner)}
          disabled={owner.userId == null}
          loading={savingStaffId === owner.staffId}
        >
          {t("schedule.settingsSave")}
        </Button>
        {savedStaffId === owner.staffId && (
          <span className="schedule-settings__timestamp">
            <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> {t("schedule.settingsSaved")}
          </span>
        )}
      </div>
    </div>
  );

  return (
    <PageLayout navKey="nav.scheduleSettings" subtitleKey="schedule.settingsSubtitle" noScroll>
      <div className="schedule-settings">
        {banner && (
          <div className={banner.type === "success" ? "success-message" : "error-message"} role="status">
            {banner.message}
          </div>
        )}
        {shownError && <div className="error-message">{shownError}</div>}
        <div className="schedule-settings__shell">
          <SubMenu
            variant="flat"
            groups={[{ items: menuItems }]}
            activeKey={activeSection}
            onChange={(key) => jumpToSection(key as SectionKey)}
            className="schedule-settings__nav"
          />

          <div className="schedule-settings__content">
            <section id="schedule-settings-personal" className="schedule-settings__section-anchor">
              <SectionCard title={t("schedule.prefsTitle")}>
                {prefsQ.isError && !prefsReady && <div className="error-message" role="alert">{t("schedule.prefsLoadError")}</div>}
                {prefsError && <div className="error-message" role="alert">{prefsError}</div>}
                <div className="schedule-settings__calendar-row">
                  <div className="schedule-settings__row-copy">
                    <span>{t("schedule.prefsFirstView")}</span>
                  </div>
                  <div className="schedule-settings__calendar-actions">
                    <SelectControl
                      size="sm"
                      aria-label={t("schedule.prefsFirstView")}
                      value={prefForm.default_view}
                      options={PREFERENCE_VIEWS.map((v) => ({ value: v, label: t(`schedule.${v}View`) }))}
                      onChange={(event) => setPrefForm((cur) => ({ ...cur, default_view: event.target.value as PreferenceView }))}
                    />
                  </div>
                </div>
                <div className="schedule-settings__calendar-row">
                  <div className="schedule-settings__row-copy">
                    <span>{t("schedule.prefsWeekStart")}</span>
                  </div>
                  <div className="schedule-settings__calendar-actions">
                    <SelectControl
                      size="sm"
                      aria-label={t("schedule.prefsWeekStart")}
                      value={String(prefForm.week_start)}
                      options={[
                        { value: "0", label: t("schedule.prefsWeekStartSunday") },
                        { value: "1", label: t("schedule.prefsWeekStartMonday") },
                      ]}
                      onChange={(event) => setPrefForm((cur) => ({ ...cur, week_start: event.target.value === "1" ? 1 : 0 }))}
                    />
                  </div>
                </div>
                <div className="schedule-settings__calendar-row">
                  <div className="schedule-settings__row-copy">
                    <span>{t("schedule.prefsEventMinutes")}</span>
                  </div>
                  <div className="schedule-settings__calendar-actions">
                    <SelectControl
                      size="sm"
                      aria-label={t("schedule.prefsEventMinutes")}
                      value={String(prefForm.event_minutes)}
                      options={PREFERENCE_EVENT_MINUTES.map((m) => ({ value: String(m), label: t("schedule.prefsMinutesValue", { count: m }) }))}
                      onChange={(event) => setPrefForm((cur) => ({ ...cur, event_minutes: Number(event.target.value) }))}
                    />
                  </div>
                </div>
                {meetAvailable && (
                  <div className="schedule-settings__calendar-row">
                    <div className="schedule-settings__row-copy">
                      <span>{t("schedule.prefsAutoMeet")}</span>
                    </div>
                    <div className="schedule-settings__calendar-actions">
                      <Toggle
                        checked={prefForm.auto_meet}
                        aria-label={t("schedule.prefsAutoMeet")}
                        onCheckedChange={(next) => setPrefForm((cur) => ({ ...cur, auto_meet: next }))}
                      />
                    </div>
                  </div>
                )}
                <div className="schedule-settings__calendar-row">
                  <div className="schedule-settings__row-copy">
                    <span>{t("schedule.prefsOpenOwners")}</span>
                  </div>
                  <div className="schedule-settings__calendar-actions">
                    <SelectControl
                      size="sm"
                      aria-label={t("schedule.prefsOpenOwners")}
                      value={prefForm.open_owners}
                      options={[
                        { value: "self", label: t("schedule.prefsOpenSelf") },
                        ...(canPickOwners
                          ? [
                              { value: "all", label: t("schedule.prefsOpenAll") },
                              { value: "team", label: t("schedule.prefsOpenTeam") },
                            ]
                          : []),
                      ]}
                      onChange={(event) => setPrefForm((cur) => ({ ...cur, open_owners: event.target.value as PreferenceOpenOwners }))}
                    />
                    {canPickOwners && prefForm.open_owners === "team" && (
                      <SelectControl
                        size="sm"
                        aria-label={t("schedule.prefsTeam")}
                        value={prefForm.open_team_id == null ? "" : String(prefForm.open_team_id)}
                        placeholder={t("schedule.prefsTeam")}
                        options={teamOptions}
                        onChange={(event) => setPrefForm((cur) => ({
                          ...cur,
                          open_team_id: event.target.value === "" ? null : Number(event.target.value),
                        }))}
                      />
                    )}
                  </div>
                </div>
                <div className="schedule-settings__calendar-row">
                  <div className="schedule-settings__calendar-actions">
                    <Button
                      variant="secondary"
                      onClick={() => void savePrefs()}
                      disabled={!prefsReady}
                      loading={prefsSaving}
                    >
                      {t("schedule.settingsSave")}
                    </Button>
                    {prefsSaved && (
                      <span className="schedule-settings__timestamp">
                        <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> {t("schedule.prefsSaved")}
                      </span>
                    )}
                  </div>
                </div>
              </SectionCard>
            </section>

            {isTenantAdmin && (
              <section id="schedule-settings-google" className="schedule-settings__section-anchor">
                <SectionCard title={t("schedule.settingsGoogleTitle")}>
                  {gcalConnected ? (
                    <div className="schedule-settings__calendar-row">
                      <div className="schedule-settings__row-copy">
                        <span>{t("schedule.statusConnected")}</span>
                        {gcalConnectedAt && !Number.isNaN(new Date(gcalConnectedAt).getTime()) && (
                          <span className="schedule-settings__description">
                            {t("schedule.settingsConnectedAtValue", { date: formatDateInput(new Date(gcalConnectedAt)) })}
                          </span>
                        )}
                      </div>
                      <div className="schedule-settings__calendar-actions">
                        <Button variant="danger" onClick={() => setDisconnectOpen(true)}>
                          {t("schedule.disconnect")}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="schedule-settings__calendar-row">
                      <div className="schedule-settings__row-copy">
                        <span className="schedule-settings__description">{t("schedule.settingsGoogleDesc")}</span>
                      </div>
                      <div className="schedule-settings__calendar-actions">
                        <Button variant="primary" onClick={() => setConnectNoticeOpen(true)}>
                          {t("schedule.connect")}
                        </Button>
                      </div>
                    </div>
                  )}
                </SectionCard>
              </section>
            )}

            {isTenantAdmin && (
              <section id="schedule-settings-categories" className="schedule-settings__section-anchor">
                <SectionCard
                  title={t("schedule.categoriesTitle")}
                  actions={
                    newCategory === null ? (
                      <Button variant="secondary" onClick={() => setNewCategory(NEW_CATEGORY_FORM)}>
                        {t("schedule.categoryAdd")}
                      </Button>
                    ) : null
                  }
                >
                  <p className="schedule-settings__description">{t("schedule.categoriesDesc")}</p>
                  {categoryError && <div className="error-message" role="alert">{categoryError}</div>}
                  {categories.map((category) =>
                    renderCategoryRow(
                      category.key,
                      categoryForms[category.key] ?? toCategoryForm(category),
                      (patch) => updateCategoryForm(category.key, patch),
                      () => void saveCategory(category.key),
                      category,
                    ),
                  )}
                  {newCategory !== null &&
                    renderCategoryRow(
                      NEW_CATEGORY_KEY,
                      newCategory,
                      (patch) => setNewCategory((current) => (current ? { ...current, ...patch } : current)),
                      () => void addCategory(),
                      null,
                    )}
                </SectionCard>
              </section>
            )}

            {ownersEnabled && (loading ? (
              <LoadingBlock />
            ) : (
              <>
                {selfOwner && (
                  <section id="schedule-settings-self" className="schedule-settings__card schedule-settings__section-anchor">
                    <div className="schedule-settings__card-title">{t("schedule.myCalendars")}</div>
                    <div className="schedule-settings__card-body">
                      {renderOwnerRow(selfOwner, null)}
                    </div>
                  </section>
                )}

                {otherOwners.length > 0 && (
                  <section id="schedule-settings-others" className="schedule-settings__card schedule-settings__section-anchor">
                    <div className="schedule-settings__card-title">{t("schedule.otherCalendars")}</div>
                    <div className="schedule-settings__card-body">
                      {otherOwners.map((owner) => renderOwnerRow(owner, owner.staffCode))}
                    </div>
                  </section>
                )}
              </>
            ))}
          </div>
        </div>
      </div>

      <ConfirmModal
        open={connectNoticeOpen}
        title={t("schedule.connectNoticeTitle")}
        message={
          <>
            <p style={{ margin: 0 }}>{t("schedule.connectNoticeBody")}</p>
            <ul style={{ marginTop: "var(--space-2)", marginBottom: 0, paddingLeft: "var(--space-5)" }}>
              <li>{t("schedule.connectNoticeItemEvents")}</li>
              <li>{t("schedule.connectNoticeItemColors")}</li>
            </ul>
            <p style={{ marginTop: "var(--space-2)", marginBottom: 0 }}>{t("schedule.connectNoticeStop")}</p>
          </>
        }
        confirmLabel={t("schedule.connectNoticeConfirm")}
        onConfirm={() => void startConnect()}
        onCancel={() => setConnectNoticeOpen(false)}
      />
      <ConfirmModal
        open={disconnectOpen}
        danger
        title={t("schedule.disconnectConfirm")}
        message={t("schedule.disconnectNotice")}
        confirmLabel={t("schedule.disconnect")}
        confirmLoading={disconnecting}
        onConfirm={() => void confirmDisconnect()}
        onCancel={() => setDisconnectOpen(false)}
      />
    </PageLayout>
  );
}
